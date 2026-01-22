"""Gmail integration router."""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse

from app.schemas import (
    GmailStatusResponse,
    GmailCreateDraftRequest,
    GmailCreateDraftResponse,
    GmailAuthUrlResponse,
    SuccessResponse,
)
from app.dependencies import get_current_user, get_redis, TokenData
from app.gmail_service import GmailService, GmailOAuthError
from app.redis_manager import RedisManager

logger = logging.getLogger(__name__)

router = APIRouter()


def get_frontend_redirect_url(fragment: str = "") -> str:
    """Get the frontend redirect URL."""
    base = os.environ.get("FRONTEND_ORIGIN") or os.environ.get("PUBLIC_URL")
    if not base:
        target = "/"
    else:
        target = base
    if fragment:
        target = f"{target}#{fragment}"
    return target


@router.get("/status", response_model=GmailStatusResponse)
async def gmail_status(
    current_user: TokenData = Depends(get_current_user),
):
    """Get Gmail connection status."""
    try:
        service = GmailService(current_user.user_id)
        status = service.get_status()
        return GmailStatusResponse(
            availability=status.get("availability", "unknown"),
            authorized=status.get("authorized", False),
            email=status.get("email"),
        )
    except GmailOAuthError as exc:
        return GmailStatusResponse(
            availability="unavailable",
            authorized=False,
            error=str(exc),
        )


@router.post("/disconnect", response_model=SuccessResponse)
async def gmail_disconnect(
    current_user: TokenData = Depends(get_current_user),
):
    """Disconnect Gmail account."""
    service = GmailService(current_user.user_id)
    service.disconnect()
    return SuccessResponse(success=True)


@router.get("/auth-url", response_model=GmailAuthUrlResponse)
async def gmail_auth_url(
    current_user: TokenData = Depends(get_current_user),
    redis: RedisManager = Depends(get_redis),
):
    """Get Gmail OAuth authorization URL."""
    try:
        service = GmailService(current_user.user_id)
        auth_url, state = service.get_authorization_url()
        
        # Store state in Redis for validation
        redis.set(
            f"gmail_oauth_state:{current_user.user_id}",
            {"state": state, "user_id": current_user.user_id},
            ttl=600,  # 10 minutes
        )
        
        return GmailAuthUrlResponse(auth_url=auth_url)
    except GmailOAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/oauth2callback")
async def gmail_oauth_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    redis: RedisManager = Depends(get_redis),
):
    """
    Gmail OAuth callback handler.
    
    Note: This callback is tricky with JWT auth since the user is redirected
    from Google and won't have the JWT in the request. We need to use the
    state parameter to identify the user.
    """
    if error:
        return RedirectResponse(url=get_frontend_redirect_url("gmail_error"))
    
    if not code or not state:
        return RedirectResponse(url=get_frontend_redirect_url("gmail_invalid_state"))
    
    # Find the user from the state - we need to look up all active states
    # In production, you might want to encode the user_id in the state
    # For now, we'll iterate through recent states
    user_id = None
    
    # Try to find the state in Redis
    # This is a simplified approach - in production, encode user_id in state
    for key in redis.scan_keys("gmail_oauth_state:*"):
        stored_data = redis.get(key)
        if stored_data and stored_data.get("state") == state:
            user_id = stored_data.get("user_id")
            redis.delete(key)  # Clean up
            break
    
    if not user_id:
        return RedirectResponse(url=get_frontend_redirect_url("gmail_invalid_state"))
    
    try:
        service = GmailService(user_id)
        service.exchange_code_for_tokens(code)
        return RedirectResponse(url=get_frontend_redirect_url("gmail_connected"))
    except GmailOAuthError:
        return RedirectResponse(url=get_frontend_redirect_url("gmail_error"))


@router.post("/create-draft", response_model=GmailCreateDraftResponse)
async def gmail_create_draft(
    payload: GmailCreateDraftRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Create a Gmail draft."""
    try:
        service = GmailService(current_user.user_id)
        draft = service.create_draft(
            to_email=payload.recipient_email,
            subject=payload.subject,
            body_html=payload.body,
            cc=payload.cc.split(",") if payload.cc else None,
            bcc=payload.bcc.split(",") if payload.bcc else None,
        )
        return GmailCreateDraftResponse(success=True, draft_id=draft.get("id"))
    except GmailOAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to create Gmail draft")
        raise HTTPException(status_code=500, detail="Failed to create draft")
