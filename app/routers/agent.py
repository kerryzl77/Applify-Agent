"""Agent router for campaign workflow."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.dependencies import get_db, get_current_user, TokenData
from database.db_manager import DatabaseManager
from app.agent.campaign_runner import CampaignRunner
from app.agent.sse import generate_campaign_events
from app.gmail_service import GmailService, GmailOAuthError

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize campaign runner
campaign_runner = CampaignRunner()


# ============================================================
# Request/Response Schemas
# ============================================================

class RunCampaignRequest(BaseModel):
    """Request to run campaign workflow."""
    mode: str = "full"  # full | research_only | draft_only


class RunCampaignResponse(BaseModel):
    """Response from starting a campaign run."""
    success: bool
    run_id: str


class FeedbackRequest(BaseModel):
    """Request to add feedback."""
    scope: str = "global"  # global | recruiter_email | hm_email | warm_intro
    text: str
    must: bool = False


class ConfirmRequest(BaseModel):
    """Request to confirm selections and optionally create Gmail drafts."""
    selected_contacts: Optional[dict] = None
    create_gmail_drafts: bool = False
    schedule_followups: bool = True


class CampaignViewModel(BaseModel):
    """Campaign view model for UI."""
    id: int
    job_post_id: int
    job: dict
    state: dict
    created_at: Optional[str]
    updated_at: Optional[str]


# ============================================================
# Endpoints
# ============================================================

@router.get("/campaigns/{campaign_id}", response_model=CampaignViewModel)
async def get_campaign(
    campaign_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """Get campaign view model with full state and artifacts."""
    campaign = db.get_job_campaign_with_job(campaign_id, current_user.user_id)
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    return CampaignViewModel(
        id=campaign['id'],
        job_post_id=campaign['job_post_id'],
        job=campaign.get('job', {}),
        state=campaign.get('state', {}),
        created_at=campaign.get('created_at'),
        updated_at=campaign.get('updated_at'),
    )


@router.post("/campaigns/{campaign_id}/run", response_model=RunCampaignResponse)
async def run_campaign(
    campaign_id: int,
    request: RunCampaignRequest,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """Start campaign workflow in background."""
    # Verify campaign exists and belongs to user
    campaign = db.get_job_campaign(campaign_id, current_user.user_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    # Validate mode
    if request.mode not in ('full', 'research_only', 'draft_only'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mode. Use: full, research_only, or draft_only"
        )
    
    # Start async run
    run_id = campaign_runner.run_async(
        campaign_id=campaign_id,
        user_id=current_user.user_id,
        mode=request.mode,
    )
    
    return RunCampaignResponse(success=True, run_id=run_id)


@router.get("/campaigns/{campaign_id}/events")
async def stream_campaign_events(
    campaign_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """SSE endpoint for streaming campaign progress events."""
    # Verify campaign exists
    campaign = db.get_job_campaign(campaign_id, current_user.user_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    return StreamingResponse(
        generate_campaign_events(campaign_id, current_user.user_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/campaigns/{campaign_id}/feedback")
async def add_campaign_feedback(
    campaign_id: int,
    request: FeedbackRequest,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """Add feedback to campaign for draft regeneration."""
    # Verify campaign exists
    campaign = db.get_job_campaign(campaign_id, current_user.user_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    success = db.add_job_campaign_feedback(
        campaign_id=campaign_id,
        user_id=current_user.user_id,
        scope=request.scope,
        text=request.text,
        must=request.must,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add feedback"
        )
    
    return {"success": True, "message": "Feedback added"}


@router.post("/campaigns/{campaign_id}/confirm")
async def confirm_campaign(
    campaign_id: int,
    request: ConfirmRequest,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """
    Confirm campaign selections.
    
    This can:
    - Set selected contacts (for draft generation)
    - Create Gmail drafts from generated drafts
    - Schedule follow-ups
    """
    # Verify campaign exists
    campaign = db.get_job_campaign_with_job(campaign_id, current_user.user_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    state = campaign.get('state', {})
    
    # Update selected contacts if provided
    if request.selected_contacts:
        db.set_job_campaign_selected_contacts(
            campaign_id=campaign_id,
            user_id=current_user.user_id,
            selected_contacts=request.selected_contacts,
        )
    
    gmail_draft_ids = []
    
    # Create Gmail drafts if requested
    if request.create_gmail_drafts:
        drafts = state.get('artifacts', {}).get('drafts', {})
        
        if not drafts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No drafts available to create Gmail drafts from"
            )
        
        try:
            gmail_service = GmailService(current_user.user_id)
            gmail_status = gmail_service.get_status()
            
            if not gmail_status.get('authorized'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Gmail not authorized. Please connect Gmail first."
                )
            
            # Create drafts for each draft type
            for draft_type, draft in drafts.items():
                if draft_type == 'linkedin_note':
                    continue  # Skip LinkedIn notes for Gmail
                
                subject = draft.get('subject', '')
                body = draft.get('body', '')
                
                if not subject or not body:
                    continue
                
                # Convert body to HTML
                body_html = body.replace('\n', '<br>')
                
                try:
                    result = gmail_service.create_draft(
                        to_email="",  # User will fill in recipient
                        subject=subject,
                        body_html=f"<html><body>{body_html}</body></html>",
                    )
                    gmail_draft_ids.append({
                        'type': draft_type,
                        'draft_id': result.get('id'),
                    })
                except Exception as e:
                    logger.error(f"Failed to create Gmail draft for {draft_type}: {e}")
            
            # Store Gmail draft IDs
            db.update_job_campaign_state(campaign_id, current_user.user_id, {
                'artifacts': {'gmail_draft_ids': gmail_draft_ids}
            })
            
            # Update Gmail step status
            db.update_job_campaign_state(campaign_id, current_user.user_id, {
                'steps': {'gmail': {'status': 'done'}}
            })
            
        except GmailOAuthError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Gmail error: {str(e)}"
            )
    
    # Mark campaign as done if Gmail drafts created or just confirming
    if request.create_gmail_drafts or not request.selected_contacts:
        db.update_job_campaign_state(campaign_id, current_user.user_id, {
            'phase': 'done'
        })
    
    return {
        "success": True,
        "gmail_drafts_created": len(gmail_draft_ids),
        "gmail_draft_ids": gmail_draft_ids,
    }
