"""Adapters between legacy dict payloads and typed document-intelligence contracts."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

from app.document_intelligence_models import (
    ApplicationEvidencePack,
    ArtifactGrounding,
    ArtifactKind,
    CandidateContact,
    CandidateEvidenceLink,
    CandidateProfile,
    CandidateSkill,
    EducationEntry,
    ExperienceEntry,
    JobRequirement,
    JobRequirementProfile,
    ProjectEntry,
    Provenance,
    RequirementCoverage,
    RequirementPriority,
    RequirementEvidence,
    StoryEntry,
    WorkArrangement,
)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _split_lines(text: str) -> List[str]:
    return [line.strip(" -*\t") for line in re.split(r"[\n\r]+", text or "") if line.strip(" -*\t")]


def _extract_metrics(text: str) -> List[str]:
    return re.findall(r"\b\d[\d,\.%+\-]*\b", text or "")


def _infer_work_arrangement(location: str, text: str) -> WorkArrangement:
    haystack = f"{location} {text}".lower()
    if "remote" in haystack:
        return WorkArrangement.remote
    if "hybrid" in haystack:
        return WorkArrangement.hybrid
    if "onsite" in haystack or "on-site" in haystack:
        return WorkArrangement.onsite
    return WorkArrangement.unknown


def _extract_keywords(chunks: Iterable[str]) -> List[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9\+\#\./-]{1,}", chunk or ""):
            lowered = token.lower()
            if lowered in seen or len(token) < 3:
                continue
            seen.add(lowered)
            keywords.append(token)
            if len(keywords) >= 20:
                return keywords
    return keywords


def _build_requirement(requirement_id: str, text: str, priority: RequirementPriority) -> JobRequirement:
    normalized = _text(text)
    return JobRequirement(
        requirement_id=requirement_id,
        label=normalized[:160] or requirement_id,
        priority=priority,
        keywords=_extract_keywords([normalized]),
        evidence=[
            RequirementEvidence(
                evidence_id=f"{requirement_id}.source",
                source_section="job_description",
                text=normalized[:300] or requirement_id,
                provenance=[
                    Provenance(
                        source_kind="job_posting",
                        source_label="job_description",
                        excerpt=normalized[:300],
                    )
                ],
            )
        ] if normalized else [],
    )


def build_candidate_profile(candidate_data: Dict[str, Any]) -> CandidateProfile:
    personal_info = candidate_data.get("personal_info", {}) or {}
    resume = candidate_data.get("resume", {}) or {}
    story_bank = candidate_data.get("story_bank", []) or []

    skills = [
        CandidateSkill(
            name=_text(skill),
            highlighted=index < 5,
            evidence_ids=["skills"],
            provenance=[
                Provenance(
                    source_kind="uploaded_resume",
                    source_label="resume.skills",
                    locator=f"skill:{index}",
                    excerpt=_text(skill)[:120],
                )
            ],
        )
        for index, skill in enumerate(resume.get("skills", []) or [])
        if _text(skill)
    ]

    experiences: list[ExperienceEntry] = []
    for index, experience in enumerate(resume.get("experience", []) or []):
        title = _text(experience.get("title"))
        company = _text(experience.get("company"))
        summary = _text(experience.get("description"))
        raw_bullets = experience.get("bullet_points") or _split_lines(summary)
        bullets = []
        for bullet_index, bullet in enumerate(raw_bullets[:6]):
            normalized_bullet = _text(bullet)
            if not normalized_bullet:
                continue
            bullets.append(
                {
                    "bullet_id": f"exp_{index}.bullet_{bullet_index}",
                    "text": normalized_bullet[:240],
                    "metrics": _extract_metrics(normalized_bullet),
                    "skills": [skill.name for skill in skills if skill.name.lower() in normalized_bullet.lower()][:4],
                    "evidence_strength": 0.8 if _extract_metrics(normalized_bullet) else 0.6,
                    "provenance": [
                        Provenance(
                            source_kind="uploaded_resume",
                            source_label="resume.experience",
                            locator=f"experience:{index}:bullet:{bullet_index}",
                            excerpt=normalized_bullet[:240],
                        )
                    ],
                }
            )
        experiences.append(
            ExperienceEntry(
                experience_id=f"exp_{index}",
                employer=company,
                title=title,
                location=_text(experience.get("location")),
                start_date=_text(experience.get("start_date")),
                end_date=_text(experience.get("end_date")),
                is_current=bool(experience.get("current", False)),
                summary=summary[:500],
                bullets=bullets,
                skills=[skill.name for skill in skills if skill.name.lower() in summary.lower()][:6],
                domains=_extract_keywords([title, company, summary])[:5],
                relevance_score=0.5,
                provenance=[
                    Provenance(
                        source_kind="uploaded_resume",
                        source_label="resume.experience",
                        locator=f"experience:{index}",
                        excerpt=f"{title} {company} {summary}"[:300],
                    )
                ],
            )
        )

    education = [
        EducationEntry(
            education_id=f"edu_{index}",
            institution=_text(item.get("institution")),
            degree=_text(item.get("degree")),
            field_of_study=_text(item.get("field_of_study")),
            location=_text(item.get("location")),
            start_date=_text(item.get("start_date")),
            end_date=_text(item.get("end_date")),
            provenance=[
                Provenance(
                    source_kind="uploaded_resume",
                    source_label="resume.education",
                    locator=f"education:{index}",
                    excerpt=f"{_text(item.get('degree'))} {_text(item.get('institution'))}"[:300],
                )
            ],
        )
        for index, item in enumerate(resume.get("education", []) or [])
        if _text(item.get("institution")) or _text(item.get("degree"))
    ]

    projects = [
        ProjectEntry(
            project_id=f"project_{index}",
            name=_text(item.get("name")),
            role=_text(item.get("role")),
            summary=_text(item.get("summary"))[:500],
            technologies=[_text(tech) for tech in (item.get("technologies") or []) if _text(tech)],
            link=_text(item.get("link")),
            provenance=[
                Provenance(
                    source_kind="user_edit",
                    source_label="resume.projects",
                    locator=f"project:{index}",
                    excerpt=_text(item.get("summary"))[:300],
                )
            ],
        )
        for index, item in enumerate(resume.get("projects", []) or [])
        if _text(item.get("name")) or _text(item.get("summary"))
    ]

    stories = [
        StoryEntry(
            story_id=_text(item.get("story_id")) or f"story_{index}",
            title=_text(item.get("title")) or f"Story {index + 1}",
            situation=_text(item.get("situation")),
            task=_text(item.get("task")),
            action=_text(item.get("action")),
            result=_text(item.get("result")),
            tags=[_text(tag) for tag in (item.get("tags") or []) if _text(tag)],
            provenance=[
                Provenance(
                    source_kind="user_edit",
                    source_label="story_bank",
                    locator=f"story:{index}",
                    excerpt=" ".join(
                        part for part in [
                            _text(item.get("situation")),
                            _text(item.get("action")),
                            _text(item.get("result")),
                        ] if part
                    )[:300],
                )
            ],
        )
        for index, item in enumerate(story_bank)
    ]

    return CandidateProfile(
        contact=CandidateContact(
            full_name=_text(personal_info.get("name")),
            email=_text(personal_info.get("email")),
            phone=_text(personal_info.get("phone")),
            location=_text(personal_info.get("location")),
            linkedin_url=_text(personal_info.get("linkedin")),
            github_url=_text(personal_info.get("github")),
            provenance=[
                Provenance(
                    source_kind="uploaded_resume",
                    source_label="personal_info",
                    excerpt=_text(personal_info.get("name"))[:200],
                )
            ],
        ),
        headline=_text(resume.get("headline")),
        summary=_text(resume.get("summary")),
        core_skills=skills,
        experience=experiences,
        education=education,
        projects=projects,
        story_bank=stories,
        raw_resume_text="\n".join(
            part
            for part in [
                _text(resume.get("summary")),
                *[_text(exp.get("description")) for exp in (resume.get("experience", []) or [])],
            ]
            if part
        )[:4000],
    )


def build_job_profile(job_data: Dict[str, Any]) -> JobRequirementProfile:
    job_title = _text(job_data.get("job_title") or job_data.get("title"))
    company_name = _text(job_data.get("company_name"))
    location = _text(job_data.get("location"))
    job_description = _text(job_data.get("job_description"))
    requirements_text = _text(job_data.get("requirements"))

    qualifications = [
        _build_requirement(f"qual_{index}", line, RequirementPriority.must_have)
        for index, line in enumerate(_split_lines(requirements_text)[:6])
        if line
    ]
    responsibilities = [
        _build_requirement(f"resp_{index}", line, RequirementPriority.inferred)
        for index, line in enumerate(_split_lines(job_description)[:6])
        if line
    ]

    raw_job_text = "\n".join(part for part in [job_description, requirements_text] if part)
    missing_fields = [
        field_name
        for field_name, value in [
            ("job_title", job_title),
            ("company_name", company_name),
            ("job_description", job_description),
        ]
        if not value
    ]

    return JobRequirementProfile(
        job_title=job_title,
        company_name=company_name,
        location=location,
        work_arrangement=_infer_work_arrangement(location, raw_job_text),
        employment_type=_text(job_data.get("employment_type")),
        responsibilities=responsibilities,
        qualifications=qualifications,
        keywords=_extract_keywords([job_title, company_name, job_description, requirements_text]),
        tech_stack=_extract_keywords([requirements_text, job_description])[:10],
        normalized_summary=(job_description or requirements_text)[:600],
        raw_job_text=raw_job_text[:5000],
        fallback={
            "should_backfill": bool(missing_fields),
            "missing_fields": missing_fields,
            "assumptions": ["Used raw job text because no richer normalized brief exists yet"] if raw_job_text else [],
            "safe_defaults": ["Keep claims conservative when job brief is sparse"] if missing_fields else [],
        },
        provenance=[
            Provenance(
                source_kind="job_posting",
                source_label="job_data",
                excerpt=raw_job_text[:300],
            )
        ],
    )


def _coerce_pack(pack: Dict[str, Any] | ApplicationEvidencePack) -> ApplicationEvidencePack:
    if isinstance(pack, ApplicationEvidencePack):
        return pack
    return ApplicationEvidencePack.model_validate(pack)


def build_application_evidence_pack(
    job_data: Dict[str, Any],
    candidate_data: Dict[str, Any],
    evidence_hints: Dict[str, Any] | None = None,
) -> ApplicationEvidencePack:
    evidence_hints = evidence_hints or {}
    candidate_profile = build_candidate_profile(candidate_data)
    job_profile = build_job_profile(job_data)
    resume_snippets = evidence_hints.get("resume_snippets", {}) or {}

    coverages: list[RequirementCoverage] = []
    source_lines = [
        item.get("text", "")
        for key in ("why_me_bullets", "project_angles")
        for item in (evidence_hints.get(key) or [])
        if item.get("text")
    ]

    requirements = job_profile.qualifications or job_profile.responsibilities
    for requirement in requirements[:6]:
        selected_evidence: list[CandidateEvidenceLink] = []
        for citation_index, evidence in enumerate((requirement.evidence or [])[:2]):
            snippet_text = resume_snippets.get(evidence.evidence_id) or evidence.text
            selected_evidence.append(
                CandidateEvidenceLink(
                    evidence_id=evidence.evidence_id,
                    candidate_item_id=evidence.evidence_id,
                    candidate_item_type="resume_snippet",
                    snippet=snippet_text[:300],
                    reason=f"Supports requirement: {requirement.label[:120]}",
                    strength=0.7 if snippet_text else 0.4,
                )
            )
        if not selected_evidence and candidate_profile.experience:
            experience = candidate_profile.experience[0]
            fallback_snippet = experience.summary or (experience.bullets[0].text if experience.bullets else "")
            if fallback_snippet:
                selected_evidence.append(
                    CandidateEvidenceLink(
                        evidence_id=f"{experience.experience_id}.summary",
                        candidate_item_id=experience.experience_id,
                        candidate_item_type="experience",
                        snippet=fallback_snippet[:300],
                        reason=f"Closest available experience for {requirement.label[:120]}",
                        strength=0.5,
                    )
                )
        coverages.append(
            RequirementCoverage(
                requirement_id=requirement.requirement_id,
                coverage_label="covered" if selected_evidence else "partial",
                highlight=bool(selected_evidence),
                selected_evidence=selected_evidence,
                gap_note="" if selected_evidence else "Evidence is thin; keep copy conservative.",
            )
        )

    warnings = []
    if not candidate_profile.experience:
        warnings.append("Candidate profile has no structured experience entries.")
    if not job_profile.qualifications and not job_profile.responsibilities:
        warnings.append("Job profile has limited requirement extraction; avoid overly specific claims.")

    grounding = ArtifactGrounding(
        artifact_kind=ArtifactKind.evidence_pack,
        requirement_coverage=coverages,
        warnings=warnings + ([source_lines[0][:160]] if source_lines else []),
    )

    return ApplicationEvidencePack(
        candidate_profile=candidate_profile,
        job_profile=job_profile,
        resume_grounding=ArtifactGrounding(
            artifact_kind=ArtifactKind.tailored_resume,
            requirement_coverage=coverages,
            warnings=warnings,
        ),
        cover_letter_grounding=ArtifactGrounding(
            artifact_kind=ArtifactKind.cover_letter,
            requirement_coverage=coverages,
            warnings=warnings,
        ),
        outreach_grounding=ArtifactGrounding(
            artifact_kind=ArtifactKind.outreach,
            requirement_coverage=coverages,
            warnings=warnings,
        ),
    )


def coerce_application_evidence_pack(pack: Dict[str, Any] | ApplicationEvidencePack) -> ApplicationEvidencePack:
    return _coerce_pack(pack)


def summarize_candidate_profile(candidate_profile: CandidateProfile) -> str:
    top_skills = ", ".join(skill.name for skill in candidate_profile.core_skills[:6])
    lead_experience = candidate_profile.experience[0] if candidate_profile.experience else None
    lead_line = ""
    if lead_experience:
        lead_line = f"{lead_experience.title} at {lead_experience.employer}".strip()
    return "\n".join(
        line
        for line in [
            f"Candidate: {candidate_profile.contact.full_name or 'Candidate'}",
            f"Summary: {candidate_profile.summary}" if candidate_profile.summary else "",
            f"Top skills: {top_skills}" if top_skills else "",
            f"Recent experience: {lead_line}" if lead_line else "",
        ]
        if line
    )


def summarize_job_profile(job_profile: JobRequirementProfile) -> str:
    highlights = [req.label for req in (job_profile.qualifications or job_profile.responsibilities)[:4]]
    return "\n".join(
        line
        for line in [
            f"Role: {job_profile.job_title} at {job_profile.company_name}".strip(),
            f"Location: {job_profile.location}" if job_profile.location else "",
            f"Key requirements: {'; '.join(highlights)}" if highlights else "",
        ]
        if line
    )


def summarize_grounding(pack: Dict[str, Any] | ApplicationEvidencePack, artifact_kind: ArtifactKind) -> str:
    typed_pack = _coerce_pack(pack)
    if artifact_kind == ArtifactKind.cover_letter:
        grounding = typed_pack.cover_letter_grounding
    elif artifact_kind == ArtifactKind.outreach:
        grounding = typed_pack.outreach_grounding
    else:
        grounding = typed_pack.resume_grounding

    lines: list[str] = []
    for coverage in grounding.requirement_coverage[:4]:
        evidence_snippets = [link.snippet for link in coverage.selected_evidence[:2] if link.snippet]
        if evidence_snippets:
            lines.append(f"- {coverage.requirement_id}: {' | '.join(evidence_snippets)}")
        elif coverage.gap_note:
            lines.append(f"- {coverage.requirement_id}: {coverage.gap_note}")
    for warning in grounding.warnings[:2]:
        lines.append(f"- Warning: {warning}")
    return "\n".join(lines)
