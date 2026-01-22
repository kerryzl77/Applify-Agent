"""Jobs discovery router."""

import asyncio
import hashlib
import json
import logging
import os
import threading
import time
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.schemas import (
    JobCard,
    JobDetailResponse,
    JobExtractRequest,
    JobExtractResponse,
    JobsFeedResponse,
    SaveJobResponse,
    StartCampaignResponse,
    SuccessResponse,
)
from app.dependencies import get_db, get_redis, get_current_user, TokenData
from database.db_manager import DatabaseManager
from app.redis_manager import RedisManager
from scraper.retriever import DataRetriever
from scraper.url_validator import URLValidator

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize shared components
data_retriever = DataRetriever()
url_validator = URLValidator()

# In-memory ingestion state (per-user)
# Format: {user_id: {"status": "running"|"completed"|"error", "progress": {...}, "started_at": timestamp}}
_ingestion_state = {}


@router.get("/feed", response_model=JobsFeedResponse)
async def get_jobs_feed(
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
    ats: str = Query("all", description="Filter by ATS type: all, greenhouse, ashby"),
    q: Optional[str] = Query(None, description="Search query for title/company"),
    location: Optional[str] = Query(None, description="Location filter"),
    company: Optional[str] = Query(None, description="Company name filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """Get paginated jobs feed with optional filters."""
    user_id = current_user.user_id
    
    result = db.get_job_posts_feed(
        user_id=user_id,
        ats_type=ats if ats != "all" else None,
        company=company,
        location=location,
        query=q,
        page=page,
        page_size=page_size,
    )
    
    # Convert to JobCard objects
    jobs = [JobCard(**job) for job in result.get("jobs", [])]
    
    return JobsFeedResponse(
        jobs=jobs,
        total=result.get("total", 0),
        page=result.get("page", 1),
        page_size=result.get("page_size", page_size),
        total_pages=result.get("total_pages", 0),
    )


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job_detail(
    job_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
    redis: RedisManager = Depends(get_redis),
    include_jd: bool = Query(False, description="Include extracted job description"),
):
    """Get job details, optionally with extracted JD."""
    user_id = current_user.user_id
    
    job = db.get_job_post_by_id(job_id, user_id=user_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    job_description = None
    requirements = None
    
    if include_jd and job.get("url"):
        # Try to get cached JD first
        job_hash = job.get("hash", "")
        cache_key = f"job_jd:{job_id}:{job_hash}"
        
        cached = redis.get(cache_key)
        if cached:
            job_description = cached.get("job_description")
            requirements = cached.get("requirements")
        else:
            # Extract JD using existing scraper
            try:
                job_data = data_retriever.scrape_job_posting(job.get("url"))
                if job_data and "error" not in job_data:
                    job_description = job_data.get("job_description", "")
                    requirements = job_data.get("requirements", "")
                    
                    # Cache for 1 hour
                    redis.set(cache_key, {
                        "job_description": job_description,
                        "requirements": requirements,
                    }, ttl=3600)
            except Exception as e:
                logger.error(f"Error extracting JD for job {job_id}: {e}")
    
    return JobDetailResponse(
        id=job["id"],
        source_type=job.get("source_type", ""),
        company_name=job.get("company_name", ""),
        ats_type=job.get("ats_type", ""),
        title=job.get("title", ""),
        location=job.get("location"),
        team=job.get("team"),
        employment_type=job.get("employment_type"),
        url=job.get("url", ""),
        last_seen_at=job.get("last_seen_at"),
        created_at=job.get("created_at"),
        saved_status=job.get("saved_status"),
        job_description=job_description,
        requirements=requirements,
    )


@router.post("/extract", response_model=JobExtractResponse)
async def extract_job(
    request: JobExtractRequest,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """Extract job from URL and persist as user-owned external job."""
    user_id = current_user.user_id
    url = request.url.strip()
    
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is required",
        )
    
    # Validate URL
    validation = url_validator.validate_and_parse_url(url)
    if not validation.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation.get("error", "Invalid URL"),
        )
    
    url = validation.get("url", url)
    
    # Check if job already exists
    existing_job_id = db.get_job_post_by_url(url)
    if existing_job_id:
        # Job exists, just return it and ensure it's saved for user
        db.save_job(user_id, existing_job_id, status="saved")
        job = db.get_job_post_by_id(existing_job_id, user_id=user_id)
        if job:
            return JobExtractResponse(
                success=True,
                job_id=existing_job_id,
                job=JobCard(**{k: v for k, v in job.items() if k in JobCard.model_fields}),
                message="Job already exists, saved to your list",
            )
    
    # Extract job data
    try:
        job_data = data_retriever.scrape_job_posting(url)
    except Exception as e:
        logger.error(f"Error extracting job from {url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to extract job: {str(e)}",
        )
    
    if not job_data or "error" in job_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=job_data.get("error", "Failed to extract job data"),
        )
    
    # Create hash from extracted data
    hash_input = f"{job_data.get('job_title', '')}:{job_data.get('company_name', '')}:{job_data.get('location', '')}"
    job_hash = hashlib.md5(hash_input.encode()).hexdigest()
    
    # Insert the job
    job_id = db.upsert_job_post(
        source_type="external",
        created_by_user_id=user_id,
        company_name=job_data.get("company_name", "Unknown Company"),
        ats_type="external",
        title=job_data.get("job_title", "Unknown Position"),
        url=url,
        location=job_data.get("location"),
        hash_value=job_hash,
        raw_json={
            "job_description": job_data.get("job_description"),
            "requirements": job_data.get("requirements"),
        },
    )
    
    if not job_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save job",
        )
    
    # Auto-save for the user
    db.save_job(user_id, job_id, status="saved")
    
    # Get the created job
    job = db.get_job_post_by_id(job_id, user_id=user_id)
    
    return JobExtractResponse(
        success=True,
        job_id=job_id,
        job=JobCard(**{k: v for k, v in job.items() if k in JobCard.model_fields}) if job else None,
        message="Job extracted and saved",
    )


@router.post("/{job_id}/save", response_model=SaveJobResponse)
async def save_job(
    job_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """Save a job to user's list."""
    user_id = current_user.user_id
    
    # Verify job exists
    job = db.get_job_post_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    result = db.save_job(user_id, job_id, status="saved")
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save job",
        )
    
    return SaveJobResponse(
        success=True,
        saved_job_id=result.get("id"),
        status=result.get("status"),
    )


@router.post("/{job_id}/start-campaign", response_model=StartCampaignResponse)
async def start_campaign(
    job_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """Start a campaign for a job."""
    user_id = current_user.user_id
    
    # Verify job exists
    job = db.get_job_post_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    # Update saved status to campaign_started
    db.save_job(user_id, job_id, status="campaign_started")
    
    # Create campaign
    campaign_id = db.create_job_campaign(
        user_id=user_id,
        job_post_id=job_id,
        initial_state={
            "started_at": None,  # Will be set by background process
            "steps_completed": [],
        },
    )
    
    if not campaign_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create campaign",
        )
    
    return StartCampaignResponse(
        success=True,
        campaign_id=campaign_id,
        message="Campaign started successfully",
    )


def _run_ingestion_with_progress(user_id: str):
    """Run ingestion and update progress state."""
    global _ingestion_state
    
    from pathlib import Path
    import json as json_module
    from app.jobs.ats_scrapers import get_scraper
    
    try:
        # Initialize state
        _ingestion_state[user_id] = {
            "status": "running",
            "progress": {
                "phase": "loading",
                "message": "Loading seed list...",
                "current": 0,
                "total": 0,
                "companies_processed": 0,
                "jobs_found": 0,
                "errors": 0,
            },
            "started_at": time.time(),
        }
        
        # Load seed list
        seed_file = Path(__file__).parent.parent.parent / "data" / "job_seeds.json"
        with open(seed_file, "r") as f:
            data = json_module.load(f)
        companies = data.get("companies", [])
        
        _ingestion_state[user_id]["progress"]["total"] = len(companies)
        _ingestion_state[user_id]["progress"]["phase"] = "upserting_sources"
        _ingestion_state[user_id]["progress"]["message"] = "Upserting company sources..."
        
        # Get database
        db = DatabaseManager()
        
        # Upsert company sources
        url_to_id = {}
        for company in companies:
            source_id = db.upsert_ats_company_source(
                company_name=company.get("company_name", ""),
                ats_type=company.get("ats_type", ""),
                board_root_url=company.get("board_root_url", ""),
            )
            if source_id:
                url_to_id[company.get("board_root_url", "")] = source_id
        
        # Scrape jobs
        _ingestion_state[user_id]["progress"]["phase"] = "scraping"
        total_jobs = 0
        
        for i, company in enumerate(companies):
            company_name = company.get("company_name", "")
            ats_type = company.get("ats_type", "")
            board_root_url = company.get("board_root_url", "")
            source_id = url_to_id.get(board_root_url)
            
            _ingestion_state[user_id]["progress"]["current"] = i + 1
            _ingestion_state[user_id]["progress"]["message"] = f"Scraping {company_name}..."
            
            if not source_id:
                _ingestion_state[user_id]["progress"]["errors"] += 1
                continue
            
            try:
                scraper = get_scraper(ats_type)
                jobs = scraper.fetch_jobs(board_root_url, company_name)
                
                for job in jobs:
                    job_id = db.upsert_job_post(
                        source_type="ats",
                        company_source_id=source_id,
                        company_name=company_name,
                        ats_type=ats_type,
                        title=job.get("title", ""),
                        url=job.get("url", ""),
                        external_job_id=job.get("external_job_id"),
                        location=job.get("location"),
                        team=job.get("team"),
                        employment_type=job.get("employment_type"),
                        hash_value=job.get("hash"),
                        raw_json=job.get("raw_json"),
                    )
                    if job_id:
                        total_jobs += 1
                
                if jobs:
                    db.update_ats_source_last_success(source_id)
                
                _ingestion_state[user_id]["progress"]["jobs_found"] = total_jobs
                _ingestion_state[user_id]["progress"]["companies_processed"] += 1
                
            except Exception as e:
                logger.error(f"Error scraping {company_name}: {e}")
                _ingestion_state[user_id]["progress"]["errors"] += 1
            
            # Small delay to be nice to APIs
            time.sleep(0.3)
        
        # Complete
        _ingestion_state[user_id]["status"] = "completed"
        _ingestion_state[user_id]["progress"]["phase"] = "completed"
        _ingestion_state[user_id]["progress"]["message"] = f"Done! Found {total_jobs} jobs from {_ingestion_state[user_id]['progress']['companies_processed']} companies."
        
    except Exception as e:
        logger.error(f"Ingestion failed for user {user_id}: {e}")
        _ingestion_state[user_id] = {
            "status": "error",
            "progress": {
                "phase": "error",
                "message": f"Error: {str(e)}",
                "current": 0,
                "total": 0,
            },
            "started_at": time.time(),
        }


@router.post("/refresh", response_model=SuccessResponse)
async def start_refresh_jobs(
    current_user: TokenData = Depends(get_current_user),
):
    """User-triggered endpoint to start job ingestion in background."""
    user_id = current_user.user_id
    
    # Check if ingestion is already running
    if user_id in _ingestion_state and _ingestion_state[user_id].get("status") == "running":
        # Check if it's been running for more than 10 minutes (stale)
        started_at = _ingestion_state[user_id].get("started_at", 0)
        if time.time() - started_at < 600:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Job refresh is already in progress",
            )
    
    # Start ingestion in background thread
    thread = threading.Thread(target=_run_ingestion_with_progress, args=(user_id,))
    thread.daemon = True
    thread.start()
    
    return SuccessResponse(
        success=True,
        message="Job refresh started",
    )


@router.get("/refresh/status")
async def get_refresh_status(
    current_user: TokenData = Depends(get_current_user),
):
    """Get current ingestion progress status."""
    user_id = current_user.user_id
    
    if user_id not in _ingestion_state:
        return {
            "status": "idle",
            "progress": None,
        }
    
    state = _ingestion_state[user_id]
    return {
        "status": state.get("status", "idle"),
        "progress": state.get("progress"),
        "started_at": state.get("started_at"),
    }


async def _generate_sse_events(user_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE events for ingestion progress."""
    last_message = None
    idle_count = 0
    max_idle = 300  # 5 minutes max wait
    
    while idle_count < max_idle:
        if user_id in _ingestion_state:
            state = _ingestion_state[user_id]
            current_message = json.dumps({
                "status": state.get("status"),
                "progress": state.get("progress"),
            })
            
            if current_message != last_message:
                yield f"data: {current_message}\n\n"
                last_message = current_message
                idle_count = 0
            
            # If completed or error, send final message and exit
            if state.get("status") in ["completed", "error"]:
                await asyncio.sleep(0.5)
                break
        else:
            # No state yet, send idle
            idle_message = json.dumps({"status": "idle", "progress": None})
            if idle_message != last_message:
                yield f"data: {idle_message}\n\n"
                last_message = idle_message
        
        await asyncio.sleep(0.5)
        idle_count += 1
    
    yield f"data: {json.dumps({'status': 'timeout', 'progress': None})}\n\n"


@router.get("/refresh/stream")
async def stream_refresh_progress(
    current_user: TokenData = Depends(get_current_user),
):
    """SSE endpoint for streaming ingestion progress updates."""
    user_id = current_user.user_id
    
    return StreamingResponse(
        _generate_sse_events(user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
