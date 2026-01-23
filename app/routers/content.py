"""Content generation router."""

import logging
import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.schemas import (
    GenerateContentRequest,
    GenerateContentResponse,
    ValidateUrlRequest,
    ValidateUrlResponse,
    CandidateDataUpdate,
    SuccessResponse,
)
from app.dependencies import get_db, get_redis, get_current_user, TokenData
from database.db_manager import DatabaseManager
from app.redis_manager import RedisManager
from app.cached_llm import CachedLLMGenerator
from app.output_formatter import OutputFormatter
from app.utils.text import normalize_job_data
from scraper.retriever import DataRetriever
from scraper.url_validator import URLValidator

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize shared components
llm_generator = CachedLLMGenerator()
output_formatter = OutputFormatter()
data_retriever = DataRetriever()
url_validator = URLValidator()


@router.post("/generate", response_model=GenerateContentResponse)
async def generate_content(
    request: GenerateContentRequest,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
    redis: RedisManager = Depends(get_redis),
):
    """Generate content based on user input with Redis caching."""
    user_id = current_user.user_id
    
    # Get content type and input data
    content_type = request.content_type
    url = request.url
    linkedin_url = request.linkedin_url
    manual_text = request.manual_text
    input_type = request.input_type
    person_name = request.person_name or ""
    person_position = request.person_position or ""
    recipient_email = request.recipient_email or ""
    
    # Auto-detect input type for connection emails
    connection_types = ["linkedin_message", "connection_email", "hiring_manager_email"]
    if content_type in connection_types:
        if person_name or person_position or linkedin_url:
            input_type = "url"
            logger.info("Auto-detected input_type='url' for connection email with person fields")
    
    logger.info(f"Generate request: content_type={content_type}, input_type={input_type}")
    
    # Validate input
    needs_profile = content_type in connection_types
    
    if not content_type:
        raise HTTPException(status_code=400, detail="Missing content type")
    
    if needs_profile and input_type == "url":
        if not person_name or not person_position:
            raise HTTPException(
                status_code=400,
                detail="Person name and position are required for connection messages",
            )
    elif not needs_profile and not url and not manual_text:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    if content_type in ["connection_email", "hiring_manager_email"] and not recipient_email:
        raise HTTPException(
            status_code=400,
            detail="Recipient email is required for email workflows",
        )
    
    # Validate URL if provided
    if input_type == "url" and url:
        url_validation = url_validator.validate_and_parse_url(url)
        if not url_validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid URL: {url_validation['error']}",
            )
        if "warning" in url_validation:
            logger.warning(f"URL warning for {url}: {url_validation['warning']}")
        url = url_validation["url"]
    
    # Create cache key data
    temp_job_data = {
        "person_name": person_name,
        "person_position": person_position,
        "url": url or "manual_input",
    }
    
    # Check cache first
    cached_content = redis.get_cached_content(content_type, temp_job_data, user_id)
    if cached_content:
        logger.info(f"Cache hit for content generation: {content_type}")
        return GenerateContentResponse(
            content=cached_content["content"],
            cached=True,
        )
    
    # Get candidate data
    candidate_data = db.get_candidate_data(user_id)
    
    # Initialize job_data and profile_data
    job_data = None
    profile_data = None
    
    if input_type == "url":
        if needs_profile:
            # For connection messages: use manual person name/position
            position_parts = (
                person_position.split(" at ", 1)
                if person_position and " at " in person_position
                else [person_position or "", ""]
            )
            profile_data = {
                "name": person_name,
                "title": position_parts[0] if position_parts else person_position,
                "company": position_parts[1] if len(position_parts) > 1 else "",
                "location": "",
                "about": "",
                "experience": [],
                "education": [],
                "skills": [],
                "url": linkedin_url or "",
            }
            
            # Try to scrape LinkedIn if URL provided
            if linkedin_url and "linkedin.com/in/" in linkedin_url:
                try:
                    logger.info(f"Attempting to scrape LinkedIn: {linkedin_url}")
                    company_hint = profile_data.get("company") or None
                    scraped_profile = data_retriever.scrape_linkedin_profile(
                        linkedin_url,
                        name=person_name,
                        position=position_parts[0] if position_parts else person_position,
                        company=company_hint,
                    )
                    
                    if scraped_profile and "error" not in scraped_profile:
                        logger.info(f"LinkedIn scraping successful for {linkedin_url}")
                        profile_data["about"] = scraped_profile.get("about", "")
                        profile_data["experience"] = scraped_profile.get("experience", [])
                        profile_data["education"] = scraped_profile.get("education", [])
                        profile_data["skills"] = scraped_profile.get("skills", [])
                        if not profile_data["location"]:
                            profile_data["location"] = scraped_profile.get("location", "")
                    else:
                        logger.warning(
                            f"LinkedIn scraping failed: {scraped_profile.get('error', 'Unknown')}"
                        )
                except Exception as e:
                    logger.warning(f"LinkedIn scraping exception: {str(e)}")
            
            job_data = {
                "job_title": "the position",
                "company_name": profile_data.get("company") or "the company",
                "job_description": f'Opportunity at {profile_data.get("company") or "the company"}',
                "requirements": "",
                "url": linkedin_url or "",
            }
        else:
            # For cover letters: only need job posting
            if "linkedin.com" in (url or ""):
                raise HTTPException(
                    status_code=400,
                    detail="Cover letters require a job posting URL, not a LinkedIn profile",
                )
            job_data = data_retriever.scrape_job_posting(url)
            if "error" in job_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to get job posting: {job_data['error']}",
                )
    else:  # manual input
        if needs_profile:
            profile_data = data_retriever.parse_manual_linkedin_profile(manual_text)
            if "error" in profile_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to parse profile data: {profile_data['error']}",
                )
            
            if person_name:
                profile_data["name"] = person_name
            if person_position:
                position_parts = (
                    person_position.split(" at ", 1)
                    if " at " in person_position
                    else [person_position, ""]
                )
                profile_data["title"] = position_parts[0] if position_parts else person_position
                profile_data["company"] = position_parts[1] if len(position_parts) > 1 else ""
            
            job_data = {
                "job_title": "the position",
                "company_name": profile_data.get("company", "the company"),
                "job_description": f'Opportunity at {profile_data.get("company", "the company")}',
                "requirements": "",
                "url": "manual_input",
            }
        else:
            job_data = data_retriever.parse_manual_job_posting(manual_text)
            if "error" in job_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to parse job posting: {job_data['error']}",
                )
    
    job_data = normalize_job_data(job_data)

    # Generate content based on type
    if content_type == "linkedin_message":
        content = llm_generator.generate_linkedin_message(job_data, candidate_data, profile_data)
    elif content_type == "connection_email":
        content = llm_generator.generate_connection_email(job_data, candidate_data, profile_data)
    elif content_type == "hiring_manager_email":
        content = llm_generator.generate_hiring_manager_email(job_data, candidate_data, profile_data)
    elif content_type == "cover_letter":
        content = llm_generator.generate_cover_letter(job_data, candidate_data)
    else:
        raise HTTPException(status_code=400, detail="Invalid content type")
    
    # Format the content
    formatted_content = output_formatter.format_text(content, content_type)
    
    email_bundle = None
    if content_type in ["connection_email", "hiring_manager_email"]:
        email_bundle = {
            "subject": llm_generator.generate_email_subject(
                formatted_content, content_type.replace("_", " ")
            ),
            "body_html": llm_generator._convert_to_html(formatted_content),
        }
    
    # Cache the generated content
    redis.cache_generated_content(content_type, formatted_content, job_data, user_id)
    
    # Save generated content to database
    metadata = {
        "job_title": job_data.get("job_title", ""),
        "company_name": job_data.get("company_name", ""),
        "url": url,
        "generated_at": str(datetime.datetime.now()),
        "input_type": input_type,
    }
    if email_bundle:
        metadata.update({
            "email_subject": email_bundle.get("subject", ""),
            "email_html": email_bundle.get("body_html", ""),
            "recipient_email": recipient_email,
        })
    content_id = db.save_generated_content(content_type, formatted_content, metadata, user_id)
    
    # Create document file if needed
    file_info = None
    if content_type in ["cover_letter", "connection_email", "hiring_manager_email"]:
        try:
            file_info = output_formatter.create_docx(
                formatted_content, job_data, candidate_data, content_type
            )
            if file_info:
                logger.info(f"Document created: {file_info['filename']}")
        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
    
    # Build response
    response = GenerateContentResponse(
        content=formatted_content,
        content_id=content_id,
        file_info=file_info,
        cached=False,
    )
    
    if email_bundle:
        response.email_subject = email_bundle.get("subject")
        response.email_html = email_bundle.get("body_html")
        response.recipient_email = recipient_email
    
    return response


@router.get("/candidate-data")
async def get_candidate_data(
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
    redis: RedisManager = Depends(get_redis),
):
    """Get candidate data for the frontend with caching."""
    user_id = current_user.user_id
    cache_key = f"candidate_data:{user_id}"
    
    cached_data = redis.get(cache_key)
    if cached_data:
        return cached_data
    
    data = db.get_candidate_data(user_id)
    redis.set(cache_key, data, 300)  # Cache for 5 minutes
    return data or {}


@router.post("/candidate-data", response_model=SuccessResponse)
async def update_candidate_data(
    update_data: CandidateDataUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
    redis: RedisManager = Depends(get_redis),
):
    """Update candidate data and invalidate cache."""
    user_id = current_user.user_id
    incoming_data = update_data.model_dump(exclude_none=True)
    
    # Preserve existing data if request omits fields
    existing_data = db.get_candidate_data(user_id) or {}
    merged_data = existing_data.copy()
    
    if "personal_info" in incoming_data:
        merged_data["personal_info"] = {
            **existing_data.get("personal_info", {}),
            **incoming_data["personal_info"],
        }
    
    if "resume" in incoming_data:
        existing_resume = existing_data.get("resume", {})
        new_resume = incoming_data.get("resume") or {}
        merged_data["resume"] = {**existing_resume, **new_resume}
    elif "resume" not in merged_data:
        merged_data["resume"] = existing_data.get("resume", {})
    
    for key in ["story_bank", "templates"]:
        if key in incoming_data:
            merged_data[key] = incoming_data[key]
    
    db.update_candidate_data(merged_data, user_id)
    
    # Invalidate user cache
    redis.invalidate_user_cache(user_id)
    
    return SuccessResponse(success=True)


@router.post("/validate-url", response_model=ValidateUrlResponse)
async def validate_url(
    request: ValidateUrlRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Validate URL and provide feedback to user."""
    url = request.url.strip()
    
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    validation_result = url_validator.validate_and_parse_url(url)
    
    recommendations = None
    if not validation_result["valid"] or "warning" in validation_result:
        recommendations = url_validator.get_url_recommendations(validation_result["type"])
    
    return ValidateUrlResponse(
        valid=validation_result["valid"],
        url=validation_result.get("url"),
        type=validation_result.get("type"),
        error=validation_result.get("error"),
        warning=validation_result.get("warning"),
        recommendations=recommendations,
    )


@router.get("/download/{file_path:path}")
async def download_file(
    file_path: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Download a generated file."""
    import os
    
    file_full_path = os.path.join(output_formatter.output_dir, file_path)
    
    if not os.path.exists(file_full_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    return FileResponse(
        path=file_full_path,
        filename=file_path,
        media_type="application/octet-stream",
    )


@router.get("/convert-to-pdf/{file_path:path}")
async def convert_to_pdf(
    file_path: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Convert a DOCX file to PDF and download it."""
    import os
    
    docx_path = os.path.join(output_formatter.output_dir, file_path)
    
    if not os.path.exists(docx_path):
        raise HTTPException(status_code=404, detail=f"Source file not found: {file_path}")
    
    docx_info = {"filename": file_path, "filepath": docx_path}
    pdf_info = output_formatter.convert_to_pdf(docx_info)
    
    if pdf_info and os.path.exists(pdf_info["filepath"]):
        return FileResponse(
            path=pdf_info["filepath"],
            filename=pdf_info["filename"],
            media_type="application/pdf",
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="PDF conversion failed. Please try downloading the DOCX file instead.",
        )
