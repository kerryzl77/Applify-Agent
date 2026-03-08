"""Evidence Agent: builds grounded evidence pack matching resume to JD."""

import json
import logging
import re
from typing import Any, Dict

from app.document_intelligence import build_application_evidence_pack
from app.llm_service import LLMService
from app.utils.text import normalize_job_data

logger = logging.getLogger(__name__)


class EvidenceAgent:
    """Builds a shared evidence pack for cover letters and outreach drafts."""

    def __init__(self):
        llm = LLMService()
        self.client = llm.client
        self.model = llm.model

    def build_evidence_pack(
        self,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        emit_trace: callable = None,
    ) -> Dict[str, Any]:
        if emit_trace:
            emit_trace({"type": "step_progress", "step": "evidence", "message": "Building resume snippet index..."})

        job_data = normalize_job_data(job_data)
        snippets = self._build_snippet_index(candidate_data)

        if emit_trace:
            emit_trace(
                {
                    "type": "step_progress",
                    "step": "evidence",
                    "message": f"Indexed {len(snippets)} resume snippets, matching to job requirements...",
                }
            )

        requirements = job_data.get("requirements", "") or job_data.get("job_description", "")[:2000]
        evidence_summary = self._generate_evidence_with_llm(
            job_data.get("job_title", job_data.get("title", "")),
            job_data.get("company_name", ""),
            requirements,
            snippets,
            candidate_data,
        )

        typed_pack = build_application_evidence_pack(job_data, candidate_data, evidence_hints={**evidence_summary, "resume_snippets": snippets})
        payload = typed_pack.model_dump(mode="json")
        payload["resume_snippets"] = snippets
        payload["why_me_bullets"] = evidence_summary.get("why_me_bullets", [])
        payload["project_angles"] = evidence_summary.get("project_angles", [])

        if emit_trace:
            emit_trace(
                {
                    "type": "step_progress",
                    "step": "evidence",
                    "message": f"Generated {len(payload.get('why_me_bullets', []))} evidence bullets",
                }
            )
        return payload

    def _build_snippet_index(self, candidate_data: Dict[str, Any]) -> Dict[str, str]:
        snippets = {}
        resume = candidate_data.get("resume", {})

        experiences = resume.get("experience", [])
        for index, experience in enumerate(experiences):
            exp_id = f"exp_{index}"
            description = experience.get("description", "")
            if description:
                snippets[f"{exp_id}.desc"] = f"{experience.get('title', '')} at {experience.get('company', '')}: {description}"
            bullets = experience.get("bullet_points", [])
            if bullets:
                for bullet_index, bullet in enumerate(bullets):
                    snippets[f"{exp_id}.bullet_{bullet_index}"] = bullet
            elif description:
                for sentence_index, sentence in enumerate(re.split(r"[.;]", description)[:5]):
                    cleaned = sentence.strip()
                    if len(cleaned) > 20:
                        snippets[f"{exp_id}.sent_{sentence_index}"] = cleaned

        skills = resume.get("skills", [])
        if skills:
            snippets["skills"] = ", ".join(skills[:20])

        summary = resume.get("summary", "")
        if summary:
            snippets["summary"] = summary

        education = resume.get("education", [])
        for index, item in enumerate(education):
            degree = item.get("degree", "")
            institution = item.get("institution", "")
            if degree or institution:
                snippets[f"edu_{index}"] = f"{degree} from {institution}"

        return snippets

    def _generate_evidence_with_llm(
        self,
        job_title: str,
        company_name: str,
        requirements: str,
        snippets: Dict[str, str],
        candidate_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        snippet_lines = [f"[{sid}]: {text}" for sid, text in snippets.items()]
        prompt = f"""You are helping a candidate prepare evidence for a job application.

JOB:
- Title: {job_title}
- Company: {company_name}
- Requirements/Description:
{requirements[:3000]}

CANDIDATE RESUME SNIPPETS (with IDs for citation):
{chr(10).join(snippet_lines)}

CANDIDATE NAME: {candidate_data.get('personal_info', {}).get('name', 'Candidate')}

Generate:
1. THREE "why me" bullets
2. TWO project angles

Each item MUST cite specific resume snippets using their IDs.

Return JSON:
{{
    "why_me_bullets": [
        {{"text": "...", "citations": ["exp_0.desc", "skills"]}}
    ],
    "project_angles": [
        {{"text": "...", "citations": ["exp_1.bullet_0"]}}
    ]
}}

Return ONLY valid JSON."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert career coach creating compelling job application evidence. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_completion_tokens=1000,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content.strip())
            return {
                "why_me_bullets": data.get("why_me_bullets", []),
                "project_angles": data.get("project_angles", []),
            }
        except Exception as exc:
            logger.error("Error generating evidence with LLM: %s", exc)
            return {"why_me_bullets": [], "project_angles": []}
