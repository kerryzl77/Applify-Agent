"""Resume router for upload and refinement."""

import os
import logging
import datetime
import uuid
import threading
import tempfile
import shutil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from app.schemas import (
    RefineResumeRequest,
    RefineResumeResponse,
    ResumeProgressResponse,
    ResumeUploadResponse,
    SuccessResponse,
)
from app.dependencies import get_db, get_redis, get_current_user, TokenData
from database.db_manager import DatabaseManager
from app.redis_manager import RedisManager
from app.enhanced_resume_processor import enhanced_resume_processor
from app.resume_rewriter_vlm import ResumeRewriterVLM, TailoredResume
from app.one_page_fitter import OnePageFitter
from app.output_formatter import OutputFormatter
from app.utils.text import normalize_text
from scraper.retriever import DataRetriever
from scraper.url_validator import URLValidator

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize shared components
output_formatter = OutputFormatter()
data_retriever = DataRetriever()
url_validator = URLValidator()


def process_resume_refinement_background(
    task_id: str,
    job_description: str,
    candidate_data: dict,
    user_id: str,
    job_url: Optional[str],
    output_dir: str,
    redis_manager: RedisManager,
):
    """
    Background task for resume refinement using 2-tier VLM pipeline.
    
    Flow:
    1. Load cached extraction artifacts (page image) if available
    2. Call VLM to tailor resume to job description
    3. Apply one-page fitter constraints
    4. Generate PDF with FastPDFGenerator
    """
    progress_key = f"resume_refinement:{user_id}:{task_id}"
    
    def update_progress(step, progress, message, status="processing", data=None):
        """Update progress in Redis."""
        progress_data = {
            "task_id": task_id,
            "step": step,
            "progress": progress,
            "message": message,
            "status": status,
            "timestamp": datetime.datetime.now().isoformat(),
            "data": data or {},
        }
        redis_manager.set(progress_key, progress_data, ttl=1800)  # 30 min TTL
        logger.info(f"Resume refinement progress [{user_id}]: {step} - {progress}% - {message}")
    
    try:
        import time
        start_time = time.time()
        
        update_progress("initializing", 5, "Starting resume refinement...")
        
        # ================================================================
        # Step 1: Load cached extraction artifacts
        # ================================================================
        update_progress("loading_context", 10, "Loading resume context...")
        
        page_image_b64 = None
        extraction_cache = enhanced_resume_processor.get_user_extraction(user_id)
        if extraction_cache:
            page_image_b64 = extraction_cache.get("page_image")
            logger.info(f"Loaded cached extraction for user {user_id}")
        
        # ================================================================
        # Step 2: VLM Tailoring
        # ================================================================
        update_progress("tailoring", 30, "AI is tailoring your resume to the job...")
        
        rewriter = ResumeRewriterVLM()
        tailored_resume: TailoredResume = rewriter.tailor_resume(
            candidate_data=candidate_data,
            job_description=job_description,
            page_image_b64=page_image_b64,
        )
        
        # Convert to dict for processing
        tailored_dict = {
            "summary": tailored_resume.summary,
            "skills": tailored_resume.skills,
            "experience": [
                {
                    "title": exp.title,
                    "company": exp.company,
                    "location": exp.location,
                    "start_date": exp.start_date,
                    "end_date": exp.end_date,
                    "bullet_points": exp.bullet_points,
                }
                for exp in tailored_resume.experience
            ],
            "education": [
                {
                    "degree": edu.degree,
                    "institution": edu.institution,
                    "graduation_date": edu.graduation_date,
                }
                for edu in tailored_resume.education
            ],
            "edit_log": tailored_resume.edit_log,
        }
        
        logger.info(f"VLM tailoring complete: {len(tailored_dict['skills'])} skills, "
                   f"{len(tailored_dict['experience'])} experiences")
        
        # ================================================================
        # Step 3: One-Page Fitting
        # ================================================================
        update_progress("fitting", 60, "Optimizing for one-page format...")
        
        fitter = OnePageFitter()
        fitted_resume, fit_result = fitter.fit(tailored_dict)
        
        logger.info(f"One-page fitter: {fit_result.iterations} iterations, "
                   f"{len(fit_result.changes_made)} changes")
        
        # ================================================================
        # Step 4: PDF Generation
        # ================================================================
        update_progress("generating_pdf", 80, "Creating professional PDF...")
        
        # Build resume data structure for PDF generator
        resume_data = {
            "sections": {
                "professional_summary": fitted_resume.get("summary", ""),
                "skills": fitted_resume.get("skills", []),
                "experience": fitted_resume.get("experience", []),
                "education": fitted_resume.get("education", []),
            }
        }
        
        # Extract job title from job description (first line or extract)
        job_title = _extract_job_title(job_description)
        
        # Generate PDF
        pdf_result = output_formatter.create_resume_pdf_direct(
            resume_data, candidate_data, job_title
        )
        
        if not pdf_result:
            update_progress("error", 0, "Failed to create PDF resume", "error")
            return
        
        generation_time = time.time() - start_time
        
        # ================================================================
        # Complete
        # ================================================================
        update_progress(
            "completed",
            100,
            "Resume tailored successfully!",
            "completed",
            {
                "file_info": {
                    "filename": pdf_result["filename"],
                    "filepath": pdf_result["filepath"],
                },
                "metrics": {
                    "skills_count": len(fitted_resume.get("skills", [])),
                    "experience_count": len(fitted_resume.get("experience", [])),
                    "one_page_fitted": fit_result.fitted,
                    "fit_iterations": fit_result.iterations,
                    "generation_time": round(generation_time, 2),
                    "pipeline": "2-tier-vlm",
                },
                "edit_log": fitted_resume.get("edit_log", []),
                "recommendations": [
                    f"Resume tailored for: {job_title}",
                    f"Skills prioritized: {len(fitted_resume.get('skills', []))}",
                    f"Experience entries: {len(fitted_resume.get('experience', []))}",
                    f"Generated in {generation_time:.1f}s",
                    "Download your tailored resume below!",
                ],
            },
        )
        
    except Exception as e:
        logger.error(f"Resume refinement background error for user {user_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        update_progress("error", 0, f"Error: {str(e)}", "error")


def _extract_job_title(job_description: str) -> str:
    """Extract job title from job description (first line or default)."""
    if not job_description:
        return "Position"
    
    # Try to get first line as title
    lines = job_description.strip().split("\n")
    first_line = lines[0].strip() if lines else ""
    
    # Clean up and limit length
    if first_line and len(first_line) < 100:
        # Remove common prefixes
        for prefix in ["Job Title:", "Position:", "Role:", "Title:"]:
            if first_line.lower().startswith(prefix.lower()):
                first_line = first_line[len(prefix):].strip()
        return first_line[:50]
    
    return "Position"


def _save_uploaded_file(file_obj, filename: str) -> str:
    """Save uploaded file to temp directory and return path."""
    from werkzeug.utils import secure_filename
    
    temp_dir = tempfile.mkdtemp()
    upload_dir = os.path.join(temp_dir, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    
    safe_filename = secure_filename(filename)
    unique_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    with open(file_path, 'wb') as out_file:
        shutil.copyfileobj(file_obj, out_file)
    
    return file_path


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    resume: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
):
    """Enhanced resume upload with 2-tier pipeline processing."""
    user_id = current_user.user_id
    
    if not resume or resume.filename == "":
        raise HTTPException(status_code=400, detail="No file selected")
    
    # Validate file type
    allowed_extensions = {".pdf", ".docx"}
    file_ext = os.path.splitext(resume.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not supported. Please upload PDF or DOCX files only.",
        )
    
    # Read file content
    content = await resume.read()
    file_size = len(content)
    
    if file_size > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
    
    if file_size < 1000:  # 1KB minimum
        raise HTTPException(
            status_code=400, detail="File too small. Please upload a valid resume file."
        )
    
    # Save the uploaded file
    try:
        await resume.seek(0)
        file_path = _save_uploaded_file(resume.file, resume.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Start enhanced background processing (uses new 2-tier pipeline)
    enhanced_resume_processor.start_processing(file_path, user_id, resume.filename)
    
    return ResumeUploadResponse(
        status="queued",
        message="Resume queued for processing. Check progress with /api/resume/progress",
        filename=resume.filename,
        size=file_size,
    )


@router.get("/progress", response_model=ResumeProgressResponse)
async def get_resume_progress(
    current_user: TokenData = Depends(get_current_user),
):
    """Get detailed resume processing progress."""
    try:
        status = enhanced_resume_processor.get_status(current_user.user_id)
        return ResumeProgressResponse(**status)
    except Exception as e:
        logger.error(f"Progress check error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get progress")


@router.post("/clear-progress", response_model=SuccessResponse)
async def clear_resume_progress(
    current_user: TokenData = Depends(get_current_user),
):
    """Clear resume processing status."""
    try:
        enhanced_resume_processor.clear_status(current_user.user_id)
        return SuccessResponse(success=True)
    except Exception as e:
        logger.error(f"Clear progress error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear progress")


@router.post("/refine", response_model=RefineResumeResponse)
async def refine_resume(
    request: RefineResumeRequest,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
    redis: RedisManager = Depends(get_redis),
):
    """Refine resume based on job description using VLM tailoring."""
    user_id = current_user.user_id
    job_description = normalize_text(request.job_description).strip() if request.job_description else ""
    input_type = request.input_type
    url = request.url if input_type == "url" else None
    
    if not job_description and not url:
        raise HTTPException(status_code=400, detail="Job description or URL is required")
    
    # Get candidate data first to validate
    candidate_data = db.get_candidate_data(user_id)
    if not candidate_data or not candidate_data.get("resume"):
        raise HTTPException(
            status_code=400, detail="Please upload your resume first before refining it"
        )
    
    # Get job description from URL if needed
    if input_type == "url" and url:
        url_validation = url_validator.validate_and_parse_url(url)
        if not url_validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid URL: {url_validation['error']}",
            )
        
        job_data = data_retriever.scrape_job_posting(url)
        if "error" in job_data:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to fetch job description: {job_data['error']}",
            )
        job_description_text = normalize_text(job_data.get("job_description"))
        requirements_text = normalize_text(job_data.get("requirements"))
        if job_description_text and requirements_text:
            job_description = f"{job_description_text}\n\n{requirements_text}"
        else:
            job_description = job_description_text or requirements_text
        
        if not job_description:
            raise HTTPException(
                status_code=400,
                detail="Unable to extract job description from URL. Please paste it manually.",
            )
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Start background processing with new VLM pipeline
    thread = threading.Thread(
        target=process_resume_refinement_background,
        args=(
            task_id,
            job_description,
            candidate_data,
            user_id,
            url,
            output_formatter.output_dir,
            redis,
        ),
    )
    thread.daemon = True
    thread.start()
    
    return RefineResumeResponse(
        success=True,
        task_id=task_id,
        status="processing",
        message="Resume refinement started. Check progress with task_id.",
    )


@router.get("/refinement-progress/{task_id}", response_model=ResumeProgressResponse)
async def get_refinement_progress(
    task_id: str,
    current_user: TokenData = Depends(get_current_user),
    redis: RedisManager = Depends(get_redis),
):
    """Get progress of resume refinement task."""
    progress_key = f"resume_refinement:{current_user.user_id}:{task_id}"
    progress_data = redis.get(progress_key)
    
    if not progress_data:
        raise HTTPException(
            status_code=404, detail="No refinement task found with this ID"
        )
    
    return ResumeProgressResponse(**progress_data)


@router.post("/analysis")
async def analyze_resume(
    request: RefineResumeRequest,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """Analyze current resume against job description (lightweight, no refinement)."""
    job_description = normalize_text(request.job_description).strip() if request.job_description else ""
    
    if not job_description:
        raise HTTPException(status_code=400, detail="Job description is required")
    
    candidate_data = db.get_candidate_data(current_user.user_id)
    if not candidate_data or not candidate_data.get("resume"):
        raise HTTPException(status_code=400, detail="Please upload your resume first")
    
    # Simple local analysis without LLM calls
    resume_data = candidate_data.get("resume", {})
    candidate_skills = set(skill.lower() for skill in resume_data.get("skills", []))
    
    # Extract keywords from job description
    job_words = set(job_description.lower().split())
    common_skills = candidate_skills & job_words
    
    # Calculate simple match score
    match_score = min(100, 50 + len(common_skills) * 5)
    skills_match = "high" if len(common_skills) >= 5 else "medium" if len(common_skills) >= 2 else "low"
    
    return {
        "analysis": {
            "job_requirements": {
                "job_title": _extract_job_title(job_description),
                "detected_keywords": list(job_words)[:20],
            },
            "resume_assessment": {
                "current_skills": resume_data.get("skills", [])[:10],
                "matching_skills": list(common_skills)[:10],
                "skills_match": skills_match,
                "estimated_score": match_score,
            },
            "match_score": match_score,
            "recommendations": [
                f"Overall match score: {match_score}/100",
                f"Skills alignment: {skills_match}",
                "Use the resume refinement feature for AI-powered optimization",
            ],
        }
    }


@router.get("/download/{file_path:path}")
async def download_resume_file(
    file_path: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Download a generated resume file."""
    file_full_path = os.path.join(output_formatter.output_dir, file_path)
    
    if not os.path.exists(file_full_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    return FileResponse(
        path=file_full_path,
        filename=file_path,
        media_type="application/octet-stream",
    )
