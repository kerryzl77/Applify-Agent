"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================
# Authentication Schemas
# ============================================================

class UserRegister(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Token refresh request."""
    refresh_token: str


class UserResponse(BaseModel):
    """User info response."""
    user_id: str
    email: str


class AuthCheckResponse(BaseModel):
    """Auth check response."""
    authenticated: bool
    user_id: Optional[str] = None
    email: Optional[str] = None


# ============================================================
# Content Generation Schemas
# ============================================================

class GenerateContentRequest(BaseModel):
    """Content generation request."""
    content_type: str  # cover_letter, linkedin_message, connection_email, hiring_manager_email
    input_type: str = "url"  # 'url' or 'manual'
    url: Optional[str] = None
    manual_text: Optional[str] = None
    person_name: Optional[str] = None
    person_position: Optional[str] = None
    linkedin_url: Optional[str] = None
    recipient_email: Optional[str] = None


class GenerateContentResponse(BaseModel):
    """Content generation response."""
    content: str
    content_id: Optional[int] = None
    file_info: Optional[Dict[str, Any]] = None
    cached: bool = False
    email_subject: Optional[str] = None
    email_html: Optional[str] = None
    recipient_email: Optional[str] = None


# ============================================================
# Resume Schemas
# ============================================================

class RefineResumeRequest(BaseModel):
    """Resume refinement request."""
    job_description: Optional[str] = None
    input_type: str = "manual"  # 'url' or 'manual'
    url: Optional[str] = None


class RefineResumeResponse(BaseModel):
    """Resume refinement response."""
    success: bool
    task_id: str
    status: str = "processing"
    message: str


class ResumeProgressResponse(BaseModel):
    """Resume progress response."""
    task_id: Optional[str] = None
    step: Optional[str] = None
    progress: int = 0
    message: str = ""
    status: str = "processing"
    timestamp: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class ResumeUploadResponse(BaseModel):
    """Resume upload response."""
    status: str
    message: str
    filename: Optional[str] = None
    size: Optional[int] = None


# ============================================================
# Profile/Candidate Data Schemas
# ============================================================

class PersonalInfo(BaseModel):
    """Personal information."""
    name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    linkedin: Optional[str] = ""
    github: Optional[str] = ""


class CandidateDataUpdate(BaseModel):
    """Candidate data update request."""
    personal_info: Optional[Dict[str, Any]] = None
    resume: Optional[Dict[str, Any]] = None
    story_bank: Optional[List[Dict[str, Any]]] = None
    templates: Optional[Dict[str, Any]] = None


class CandidateDataResponse(BaseModel):
    """Candidate data response."""
    personal_info: Optional[Dict[str, Any]] = None
    resume: Optional[Dict[str, Any]] = None
    story_bank: Optional[List[Dict[str, Any]]] = None
    templates: Optional[Dict[str, Any]] = None


# ============================================================
# Gmail Schemas
# ============================================================

class GmailStatusResponse(BaseModel):
    """Gmail status response."""
    availability: str  # 'authorized', 'configured', 'unavailable', 'unknown'
    authorized: bool = False
    email: Optional[str] = None
    error: Optional[str] = None


class GmailCreateDraftRequest(BaseModel):
    """Gmail create draft request."""
    recipient_email: EmailStr
    subject: str
    body: str
    cc: Optional[str] = None
    bcc: Optional[str] = None


class GmailCreateDraftResponse(BaseModel):
    """Gmail create draft response."""
    success: bool
    draft_id: Optional[str] = None


class GmailAuthUrlResponse(BaseModel):
    """Gmail auth URL response."""
    auth_url: str


# ============================================================
# URL Validation Schemas
# ============================================================

class ValidateUrlRequest(BaseModel):
    """URL validation request."""
    url: str


class ValidateUrlResponse(BaseModel):
    """URL validation response."""
    valid: bool
    url: Optional[str] = None
    type: Optional[str] = None
    error: Optional[str] = None
    warning: Optional[str] = None
    recommendations: Optional[List[str]] = None


# ============================================================
# Health Check Schemas
# ============================================================

class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    redis: str
    timestamp: str
    error: Optional[str] = None


# ============================================================
# Generic Response Schemas
# ============================================================

class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Generic error response."""
    error: str
    detail: Optional[str] = None


# ============================================================
# Jobs Discovery Schemas
# ============================================================

class JobCard(BaseModel):
    """Job card for feed display."""
    id: int
    source_type: str  # 'ats' or 'external'
    company_name: str
    ats_type: str  # 'greenhouse', 'ashby', or 'external'
    title: str
    location: Optional[str] = None
    team: Optional[str] = None
    employment_type: Optional[str] = None
    url: str
    last_seen_at: Optional[str] = None
    saved_status: Optional[str] = None  # 'saved', 'campaign_started', 'archived', or None


class JobsFeedResponse(BaseModel):
    """Paginated jobs feed response."""
    jobs: List[JobCard]
    total: int
    page: int
    page_size: int
    total_pages: int


class JobDetailResponse(BaseModel):
    """Full job detail response."""
    id: int
    source_type: str
    company_name: str
    ats_type: str
    title: str
    location: Optional[str] = None
    team: Optional[str] = None
    employment_type: Optional[str] = None
    url: str
    last_seen_at: Optional[str] = None
    created_at: Optional[str] = None
    saved_status: Optional[str] = None
    job_description: Optional[str] = None  # Extracted JD content
    requirements: Optional[str] = None


class JobExtractRequest(BaseModel):
    """Request to extract job from a URL."""
    url: str


class JobExtractResponse(BaseModel):
    """Response from job extraction."""
    success: bool
    job_id: Optional[int] = None
    job: Optional[JobCard] = None
    message: Optional[str] = None


class SaveJobResponse(BaseModel):
    """Response from saving a job."""
    success: bool
    saved_job_id: Optional[int] = None
    status: Optional[str] = None


class StartCampaignResponse(BaseModel):
    """Response from starting a campaign."""
    success: bool
    campaign_id: Optional[int] = None
    message: Optional[str] = None
