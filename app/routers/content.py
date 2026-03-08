"""Content generation router."""

import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.cached_llm import CachedLLMGenerator
from app.dependencies import TokenData, get_current_user, get_db, get_redis
from app.document_intelligence import build_application_evidence_pack
from app.object_storage import ObjectStorage
from app.output_formatter import OutputFormatter
from app.redis_manager import RedisManager
from app.schemas import (
    CandidateDataUpdate,
    GenerateContentRequest,
    GenerateContentResponse,
    SuccessResponse,
    ValidateUrlRequest,
    ValidateUrlResponse,
)
from app.utils.text import normalize_job_data
from database.db_manager import DatabaseManager
from scraper.retriever import DataRetriever
from scraper.url_validator import URLValidator

logger = logging.getLogger(__name__)

router = APIRouter()

llm_generator = CachedLLMGenerator()
output_formatter = OutputFormatter()
object_storage = ObjectStorage()
data_retriever = DataRetriever()
url_validator = URLValidator()


def _build_cache_context(
    request: GenerateContentRequest,
    input_type: str,
    candidate_data: dict,
    normalized_url: str,
    recipient_email: str,
) -> dict:
    return {
        "input_type": input_type,
        "url": normalized_url,
        "linkedin_url": request.linkedin_url or "",
        "manual_text": request.manual_text or "",
        "person_name": request.person_name or "",
        "person_position": request.person_position or "",
        "recipient_email": recipient_email,
        "candidate_data": candidate_data,
    }


def _persist_rendered_artifacts(
    db: DatabaseManager,
    candidate_data: dict,
    artifact,
    user_id: str,
    content_id: int,
    content_type: str,
) -> Optional[dict]:
    if not artifact:
        return None

    file_info = output_formatter.render_artifact_bundle(
        artifact=artifact,
        candidate_data=candidate_data,
        user_id=user_id,
        artifact_id=content_id,
    )
    if not file_info:
        return None

    for fmt in file_info.get("available_formats", []):
        local_path = output_formatter.get_artifact_download_path(user_id, content_id, fmt)
        if not local_path:
            continue
        stored = object_storage.store_file(
            local_path,
            object_key=f"generated-content/{user_id}/{content_id}/artifact.{fmt}",
            metadata={"content_id": content_id, "content_type": content_type, "format": fmt},
        )
        db.create_artifact(
            user_id=user_id,
            run_id=None,
            source_type="generated_content",
            source_id=content_id,
            step_key=None,
            artifact_key=f"generated_content.{fmt}",
            artifact_type=content_type,
            kind="file",
            format=fmt,
            storage_backend=stored.get("storage_backend"),
            bucket_name=stored.get("bucket_name"),
            object_key=stored.get("object_key"),
            filename=stored.get("filename"),
            content_type=stored.get("content_type"),
            size_bytes=stored.get("size_bytes"),
            metadata={"content_id": content_id, "content_type": content_type},
        )
    logger.info("Structured artifacts created for content_id=%s", content_id)
    return file_info


@router.post("/generate", response_model=GenerateContentResponse)
async def generate_content(
    request: GenerateContentRequest,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
    redis: RedisManager = Depends(get_redis),
):
    """Generate content based on user input with Redis caching."""
    user_id = current_user.user_id
    content_type = request.content_type
    url = request.url
    linkedin_url = request.linkedin_url
    manual_text = request.manual_text
    input_type = request.input_type
    person_name = request.person_name or ""
    person_position = request.person_position or ""
    recipient_email = request.recipient_email or ""

    connection_types = ["linkedin_message", "connection_email", "hiring_manager_email"]
    if content_type in connection_types and (person_name or person_position or linkedin_url):
        input_type = "url"
        logger.info("Auto-detected input_type='url' for connection workflow")

    logger.info("Generate request: content_type=%s, input_type=%s", content_type, input_type)

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

    if input_type == "url" and url:
        url_validation = url_validator.validate_and_parse_url(url)
        if not url_validation["valid"]:
            raise HTTPException(status_code=400, detail=f"Invalid URL: {url_validation['error']}")
        if "warning" in url_validation:
            logger.warning("URL warning for %s: %s", url, url_validation["warning"])
        url = url_validation["url"]

    candidate_data = db.get_candidate_data(user_id) or {}
    cache_context = _build_cache_context(
        request=request,
        input_type=input_type,
        candidate_data=candidate_data,
        normalized_url=url or "",
        recipient_email=recipient_email,
    )
    cached_content = redis.get_cached_content(content_type, user_id, cache_context)
    if cached_content:
        logger.info("Cache hit for content generation: %s", content_type)
        return GenerateContentResponse(**cached_content["response"], cached=True)

    job_data = None
    profile_data = None

    if input_type == "url":
        if needs_profile:
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
            if linkedin_url and "linkedin.com/in/" in linkedin_url:
                try:
                    scraped_profile = data_retriever.scrape_linkedin_profile(
                        linkedin_url,
                        name=person_name,
                        position=position_parts[0] if position_parts else person_position,
                        company=profile_data.get("company") or None,
                    )
                    if scraped_profile and "error" not in scraped_profile:
                        profile_data["about"] = scraped_profile.get("about", "")
                        profile_data["experience"] = scraped_profile.get("experience", [])
                        profile_data["education"] = scraped_profile.get("education", [])
                        profile_data["skills"] = scraped_profile.get("skills", [])
                        if not profile_data["location"]:
                            profile_data["location"] = scraped_profile.get("location", "")
                except Exception as exc:
                    logger.warning("LinkedIn scraping exception: %s", str(exc))

            job_data = {
                "job_title": "the position",
                "company_name": profile_data.get("company") or "the company",
                "job_description": f"Opportunity at {profile_data.get('company') or 'the company'}",
                "requirements": "",
                "url": linkedin_url or "",
            }
        else:
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
    else:
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
                position_parts = person_position.split(" at ", 1) if " at " in person_position else [person_position, ""]
                profile_data["title"] = position_parts[0] if position_parts else person_position
                profile_data["company"] = position_parts[1] if len(position_parts) > 1 else ""
            job_data = {
                "job_title": "the position",
                "company_name": profile_data.get("company", "the company"),
                "job_description": f"Opportunity at {profile_data.get('company', 'the company')}",
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
    evidence_pack = build_application_evidence_pack(job_data, candidate_data)

    artifact = None
    try:
        if content_type == "linkedin_message":
            content = llm_generator.generate_linkedin_message(
                job_data,
                candidate_data,
                profile_data,
                evidence_pack=evidence_pack,
            )
        elif content_type == "connection_email":
            artifact = llm_generator.generate_connection_email_artifact(
                job_data,
                candidate_data,
                profile_data,
                evidence_pack=evidence_pack,
            )
            content = artifact.to_plain_text()
        elif content_type == "hiring_manager_email":
            artifact = llm_generator.generate_hiring_manager_email_artifact(
                job_data,
                candidate_data,
                profile_data,
                evidence_pack=evidence_pack,
            )
            content = artifact.to_plain_text()
        elif content_type == "cover_letter":
            artifact = llm_generator.generate_cover_letter_artifact(
                job_data,
                candidate_data,
                evidence_pack=evidence_pack,
            )
            content = artifact.to_plain_text()
        else:
            raise HTTPException(status_code=400, detail="Invalid content type")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Structured content generation failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Content generation failed: {str(exc)}",
        ) from exc

    formatted_content = output_formatter.format_text(content, content_type)
    email_bundle = None
    if content_type in ["connection_email", "hiring_manager_email"]:
        email_bundle = {
            "subject": artifact.subject if artifact else llm_generator.generate_email_subject(
                formatted_content,
                content_type.replace("_", " "),
            ),
            "body_html": llm_generator._convert_to_html(formatted_content),
        }

    metadata = {
        "job_title": job_data.get("job_title", ""),
        "company_name": job_data.get("company_name", ""),
        "url": url,
        "generated_at": str(datetime.datetime.now()),
        "input_type": input_type,
        "evidence_pack": evidence_pack.model_dump(mode="json"),
    }
    if artifact:
        metadata["artifact"] = artifact.model_dump(mode="json")
    if email_bundle:
        metadata.update(
            {
                "email_subject": email_bundle.get("subject", ""),
                "email_html": email_bundle.get("body_html", ""),
                "recipient_email": recipient_email,
            }
        )

    content_id = db.save_generated_content(content_type, formatted_content, metadata, user_id)
    file_info = None
    if content_type in ["cover_letter", "connection_email", "hiring_manager_email"]:
        try:
            file_info = _persist_rendered_artifacts(
                db=db,
                candidate_data=candidate_data,
                artifact=artifact,
                user_id=user_id,
                content_id=content_id,
                content_type=content_type,
            )
        except Exception as exc:
            logger.error("Error creating document: %s", str(exc))

    response_payload = {
        "content": formatted_content,
        "content_id": content_id,
        "file_info": file_info,
        "email_subject": email_bundle.get("subject") if email_bundle else None,
        "email_html": email_bundle.get("body_html") if email_bundle else None,
        "recipient_email": recipient_email if email_bundle else None,
    }
    redis.cache_generated_content(content_type, user_id, cache_context, response_payload)
    return GenerateContentResponse(**response_payload, cached=False)


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
    redis.set(cache_key, data, 300)
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


@router.get("/download/{content_id:int}/{fmt}")
async def download_file(
    content_id: int,
    fmt: str,
    current_user: TokenData = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db),
):
    """Download a generated file owned by the current user."""
    record = db.get_generated_content(content_id, current_user.user_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {content_id}")

    artifact = db.get_latest_artifact(
        source_type="generated_content",
        source_id=content_id,
        format=fmt,
        user_id=current_user.user_id,
    )
    if artifact:
        body = object_storage.download_bytes(artifact)
        filename = artifact.get("filename") or f"{record['content_type']}_{content_id}.{fmt}"
        media_type = artifact.get("content_type") or (
            "application/pdf"
            if fmt == "pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        return Response(
            content=body,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    file_full_path = output_formatter.get_artifact_download_path(current_user.user_id, content_id, fmt)
    if not file_full_path:
        raise HTTPException(status_code=404, detail=f"File format not found: {fmt}")
    with open(file_full_path, "rb") as infile:
        body = infile.read()
    filename = f"{record['content_type']}_{content_id}.{fmt}"
    media_type = "application/pdf" if fmt == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/convert-to-pdf/{file_path:path}")
async def convert_to_pdf(
    file_path: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Legacy endpoint retained for backwards compatibility."""
    raise HTTPException(
        status_code=410,
        detail="DOCX conversion endpoint retired; request the PDF artifact directly.",
    )
