"""Canonical document-intelligence contracts for candidate, job, and evidence data."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class SourceKind(str, Enum):
    uploaded_resume = "uploaded_resume"
    parsed_resume = "parsed_resume"
    user_edit = "user_edit"
    job_posting = "job_posting"
    recruiter_input = "recruiter_input"
    web_research = "web_research"
    system_inference = "system_inference"


class RequirementPriority(str, Enum):
    must_have = "must_have"
    preferred = "preferred"
    nice_to_have = "nice_to_have"
    inferred = "inferred"


class WorkArrangement(str, Enum):
    onsite = "onsite"
    hybrid = "hybrid"
    remote = "remote"
    unknown = "unknown"


class ArtifactKind(str, Enum):
    tailored_resume = "tailored_resume"
    cover_letter = "cover_letter"
    outreach = "outreach"
    evidence_pack = "evidence_pack"


class Provenance(BaseModel):
    """Trace where a normalized field or claim came from."""

    source_kind: SourceKind
    source_label: str = ""
    source_id: str = ""
    locator: str = Field(
        default="",
        description="Lightweight pointer such as page/bullet id, JD section, or URL fragment.",
    )
    excerpt: str = Field(default="", max_length=400)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    inferred: bool = False


class CandidateContact(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    website_url: str = ""
    portfolio_url: str = ""
    provenance: List[Provenance] = Field(default_factory=list)


class CandidateSkill(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    category: str = ""
    level: str = ""
    highlighted: bool = False
    evidence_ids: List[str] = Field(default_factory=list)
    provenance: List[Provenance] = Field(default_factory=list)


class AchievementBullet(BaseModel):
    bullet_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=240)
    metrics: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    evidence_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    provenance: List[Provenance] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    experience_id: str = Field(min_length=1, max_length=80)
    employer: str = ""
    title: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    is_current: bool = False
    summary: str = ""
    bullets: List[AchievementBullet] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    provenance: List[Provenance] = Field(default_factory=list)


class EducationEntry(BaseModel):
    education_id: str = Field(min_length=1, max_length=80)
    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""
    honors: List[str] = Field(default_factory=list)
    coursework: List[str] = Field(default_factory=list)
    provenance: List[Provenance] = Field(default_factory=list)


class ProjectEntry(BaseModel):
    project_id: str = Field(min_length=1, max_length=80)
    name: str = ""
    role: str = ""
    summary: str = ""
    bullets: List[AchievementBullet] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    link: str = ""
    provenance: List[Provenance] = Field(default_factory=list)


class StoryEntry(BaseModel):
    story_id: str = Field(min_length=1, max_length=80)
    title: str = ""
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""
    tags: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    provenance: List[Provenance] = Field(default_factory=list)


class CandidatePreferences(BaseModel):
    target_titles: List[str] = Field(default_factory=list)
    target_locations: List[str] = Field(default_factory=list)
    work_arrangement: WorkArrangement = WorkArrangement.unknown
    seniority: str = ""
    industries: List[str] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    """Uploaded-resume-grounded canonical profile."""

    profile_version: str = "2026-03-08"
    source_of_truth: str = "uploaded_resume"
    contact: CandidateContact = Field(default_factory=CandidateContact)
    headline: str = ""
    summary: str = ""
    core_skills: List[CandidateSkill] = Field(default_factory=list)
    experience: List[ExperienceEntry] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    story_bank: List[StoryEntry] = Field(default_factory=list)
    preferences: CandidatePreferences = Field(default_factory=CandidatePreferences)
    raw_resume_text: str = Field(
        default="",
        description="Optional normalized text snapshot from the uploaded resume.",
    )


class RequirementEvidence(BaseModel):
    evidence_id: str = Field(min_length=1, max_length=80)
    source_section: str = ""
    text: str = Field(min_length=1, max_length=300)
    provenance: List[Provenance] = Field(default_factory=list)


class JobRequirement(BaseModel):
    requirement_id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=160)
    priority: RequirementPriority = RequirementPriority.inferred
    category: str = ""
    rationale: str = ""
    keywords: List[str] = Field(default_factory=list)
    evidence: List[RequirementEvidence] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class CompensationRange(BaseModel):
    currency: str = ""
    min_amount: Optional[float] = Field(default=None, ge=0.0)
    max_amount: Optional[float] = Field(default=None, ge=0.0)
    interval: str = ""


class ThinJobFallback(BaseModel):
    should_backfill: bool = False
    missing_fields: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    safe_defaults: List[str] = Field(default_factory=list)


class JobRequirementProfile(BaseModel):
    """Normalized job brief derived from JD text, URL scrape, and optional research."""

    schema_version: str = "2026-03-08"
    job_title: str = ""
    company_name: str = ""
    company_summary: str = ""
    location: str = ""
    work_arrangement: WorkArrangement = WorkArrangement.unknown
    employment_type: str = ""
    seniority: str = ""
    compensation: CompensationRange = Field(default_factory=CompensationRange)
    responsibilities: List[JobRequirement] = Field(default_factory=list)
    qualifications: List[JobRequirement] = Field(default_factory=list)
    preferred_qualifications: List[JobRequirement] = Field(default_factory=list)
    domain_signals: List[str] = Field(default_factory=list)
    tech_stack: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    normalized_summary: str = ""
    raw_job_text: str = ""
    fallback: ThinJobFallback = Field(default_factory=ThinJobFallback)
    provenance: List[Provenance] = Field(default_factory=list)


class CandidateEvidenceLink(BaseModel):
    evidence_id: str = Field(min_length=1, max_length=80)
    candidate_item_id: str = Field(min_length=1, max_length=80)
    candidate_item_type: str = ""
    snippet: str = Field(min_length=1, max_length=300)
    reason: str = ""
    strength: float = Field(default=0.5, ge=0.0, le=1.0)


class RequirementCoverage(BaseModel):
    requirement_id: str = Field(min_length=1, max_length=80)
    coverage_label: str = Field(
        default="partial",
        description="covered, partial, adjacent, or uncovered",
    )
    highlight: bool = False
    selected_evidence: List[CandidateEvidenceLink] = Field(default_factory=list)
    gap_note: str = ""


class ArtifactGrounding(BaseModel):
    artifact_kind: ArtifactKind
    requirement_coverage: List[RequirementCoverage] = Field(default_factory=list)
    excluded_candidate_items: List[str] = Field(default_factory=list)
    excluded_reason: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ApplicationEvidencePack(BaseModel):
    candidate_profile: CandidateProfile
    job_profile: JobRequirementProfile
    resume_grounding: ArtifactGrounding = Field(
        default_factory=lambda: ArtifactGrounding(artifact_kind=ArtifactKind.tailored_resume)
    )
    cover_letter_grounding: ArtifactGrounding = Field(
        default_factory=lambda: ArtifactGrounding(artifact_kind=ArtifactKind.cover_letter)
    )
    outreach_grounding: ArtifactGrounding = Field(
        default_factory=lambda: ArtifactGrounding(artifact_kind=ArtifactKind.outreach)
    )

    @model_validator(mode="after")
    def validate_source_of_truth(self) -> "ApplicationEvidencePack":
        if self.candidate_profile.source_of_truth != "uploaded_resume":
            raise ValueError("candidate_profile.source_of_truth must remain 'uploaded_resume'")
        return self


class TailoringDecision(BaseModel):
    requirement_id: str = ""
    candidate_item_id: str = ""
    action: str = Field(
        default="keep",
        description="keep, rewrite, elevate, condense, drop, or mention_elsewhere",
    )
    reason: str = ""


class TailoringPlan(BaseModel):
    target_title: str = ""
    target_company: str = ""
    priorities: List[str] = Field(default_factory=list)
    decisions: List[TailoringDecision] = Field(default_factory=list)
    page_pressure: str = Field(
        default="normal",
        description="normal, moderate, or high based on one-page fit pressure.",
    )
    one_page_strategy: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class ResumeQualityScore(BaseModel):
    relevance: int = Field(ge=1, le=5)
    evidence: int = Field(ge=1, le=5)
    ats_safety: int = Field(ge=1, le=5)
    concision: int = Field(ge=1, le=5)
    one_page_fit: int = Field(ge=1, le=5)
    credibility: int = Field(ge=1, le=5)
    notes: List[str] = Field(default_factory=list)


class CoverLetterQualityScore(BaseModel):
    grounding: int = Field(ge=1, le=5)
    specificity: int = Field(ge=1, le=5)
    tone: int = Field(ge=1, le=5)
    concision: int = Field(ge=1, le=5)
    credibility: int = Field(ge=1, le=5)
    notes: List[str] = Field(default_factory=list)


class OutreachQualityScore(BaseModel):
    personalization: int = Field(ge=1, le=5)
    grounding: int = Field(ge=1, le=5)
    tone: int = Field(ge=1, le=5)
    clarity: int = Field(ge=1, le=5)
    non_cringe: int = Field(ge=1, le=5)
    notes: List[str] = Field(default_factory=list)
