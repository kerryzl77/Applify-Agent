"""Resume router for upload and refinement."""

import os
import logging
import datetime
import uuid
import threading
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
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
from app.resume_parser import ResumeParser
from app.enhanced_resume_processor import enhanced_resume_processor
from app.resume_refiner import ResumeRefiner
from app.output_formatter import OutputFormatter
from app.utils.text import normalize_text
from scraper.retriever import DataRetriever
from scraper.url_validator import URLValidator

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize shared components
resume_parser = ResumeParser()
resume_refiner = ResumeRefiner()
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
    """Background task for resume refinement with progress tracking."""
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
        update_progress("initializing", 5, "Starting resume refinement...")
        
        # Use advanced multi-agent resume generation system
        from app.advanced_resume_generator import AdvancedResumeGenerator
        
        def progress_wrapper(step, progress, message):
            update_progress(step, progress, message)
        
        generator = AdvancedResumeGenerator()
        
        update_progress("initializing_ai", 10, "Initializing 5-Agent AI System...")
        optimized_resume, metrics = generator.generate_optimized_resume(
            candidate_data, job_description, progress_wrapper
        )
        
        update_progress("generating_pdf", 75, "Creating professional PDF (ultra-fast)...")
        
        # Extract job title from optimized resume metadata
        job_title = optimized_resume.get("metadata", {}).get("target_job", "Position")
        
        # Create PDF directly using fast generator
        pdf_result = output_formatter.create_resume_pdf_direct(
            optimized_resume, candidate_data, job_title
        )
        
        if not pdf_result:
            # Fallback to DOCX if PDF fails
            update_progress("formatting_docx", 80, "Creating DOCX as fallback...")
            formatted_resume = resume_refiner.create_formatted_resume_docx(
                optimized_resume, candidate_data, job_title, output_dir
            )
        else:
            formatted_resume = pdf_result
        
        if not formatted_resume:
            update_progress("error", 0, "Failed to create formatted resume", "error")
            return
        
        update_progress(
            "completed",
            100,
            "Advanced AI Resume Optimization Complete!",
            "completed",
            {
                "file_info": {
                    "filename": formatted_resume["filename"],
                    "filepath": formatted_resume["filepath"],
                },
                "advanced_metrics": {
                    "ats_score": metrics.ats_score,
                    "keyword_match_score": metrics.keyword_match_score,
                    "content_quality_score": metrics.content_quality_score,
                    "job_relevance_score": metrics.job_relevance_score,
                    "word_count": metrics.estimated_word_count,
                    "one_page_compliant": metrics.one_page_compliance,
                    "generation_time": optimized_resume["metadata"]["generation_time"],
                    "ai_agents_used": 5,
                },
                "optimization_details": {
                    "target_job": optimized_resume["metadata"]["target_job"],
                    "optimization_level": "Google-level Advanced",
                    "ats_version": "2025",
                    "strengths": metrics.strengths,
                    "improvement_areas": metrics.improvement_areas[:3],
                },
                "recommendations": [
                    f"Advanced AI Resume for: {optimized_resume['metadata']['target_job']}",
                    f"ATS Score: {metrics.ats_score}/100 (Target: 75+)",
                    f"Keyword Match: {metrics.keyword_match_score}/100",
                    f"Content Quality: {metrics.content_quality_score}/100",
                    f"Word Count: {metrics.estimated_word_count} "
                    f"({'One-page compliant' if metrics.one_page_compliance else 'May exceed one page'})",
                    f"Generated in {optimized_resume['metadata']['generation_time']:.1f}s using 5 AI agents",
                    "Download your ATS-optimized resume below!",
                ],
            },
        )
        
    except Exception as e:
        logger.error(f"Resume refinement background error for user {user_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        update_progress("error", 0, f"Error: {str(e)}", "error")


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    resume: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
):
    """Enhanced resume upload with progress tracking and caching."""
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
        # Reset file position and create a file-like object
        await resume.seek(0)
        file_path = resume_parser.save_uploaded_file(resume.file, resume.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Start enhanced background processing
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
    """Refine resume based on job description - starts background processing."""
    user_id = current_user.user_id
    job_description = normalize_text(request.job_description).strip()
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
    
    # Start background processing
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
    """Analyze current resume without refinement."""
    job_description = normalize_text(request.job_description).strip()
    
    if not job_description:
        raise HTTPException(status_code=400, detail="Job description is required")
    
    candidate_data = db.get_candidate_data(current_user.user_id)
    if not candidate_data or not candidate_data.get("resume"):
        raise HTTPException(status_code=400, detail="Please upload your resume first")
    
    # Analyze job requirements
    job_analysis = resume_refiner.quick_job_analysis(job_description)
    
    # Analyze current resume
    resume_analysis = resume_refiner.quick_resume_analysis(candidate_data, job_analysis)
    
    # Calculate match score
    match_score = resume_refiner._calculate_optimization_score(job_analysis, resume_analysis)
    
    return {
        "analysis": {
            "job_requirements": {
                "job_title": job_analysis.get("job_title"),
                "required_skills": job_analysis.get("required_skills", []),
                "preferred_skills": job_analysis.get("preferred_skills", []),
                "key_qualifications": job_analysis.get("key_qualifications", []),
                "important_keywords": job_analysis.get("important_keywords", []),
            },
            "resume_assessment": {
                "current_strengths": resume_analysis.get("current_strengths", []),
                "improvement_areas": resume_analysis.get("improvement_areas", []),
                "keyword_gaps": resume_analysis.get("keyword_gaps", []),
                "skills_match": resume_analysis.get("skills_match", "medium"),
                "ats_score": resume_analysis.get("ats_optimization_score", 70),
            },
            "match_score": match_score,
            "recommendations": [
                f"Overall match score: {match_score}/100",
                f"Skills alignment: {resume_analysis.get('skills_match', 'medium')}",
                "Consider using the resume refinement feature for optimization",
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
