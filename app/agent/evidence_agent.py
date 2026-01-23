"""Evidence Agent: builds grounded evidence pack matching resume to JD."""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


class EvidenceAgent:
    """Builds evidence pack grounding resume experience to job requirements."""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def build_evidence_pack(
        self,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        emit_trace: callable = None,
    ) -> Dict[str, Any]:
        """
        Build evidence pack with grounded 'why me' bullets and project angles.
        
        Returns:
            {
                'why_me_bullets': [{'text': ..., 'citations': [...]}],
                'project_angles': [{'text': ..., 'citations': [...]}],
                'resume_snippets': {snippet_id: text}
            }
        """
        if emit_trace:
            emit_trace({'type': 'step_progress', 'step': 'evidence', 'message': 'Building resume snippet index...'})
        
        # Build stable snippet IDs from resume
        snippets = self._build_snippet_index(candidate_data)
        
        if emit_trace:
            emit_trace({'type': 'step_progress', 'step': 'evidence', 'message': f'Indexed {len(snippets)} resume snippets, matching to job requirements...'})
        
        # Extract requirements from JD
        requirements = job_data.get('requirements', '') or job_data.get('job_description', '')[:2000]
        job_title = job_data.get('job_title', job_data.get('title', ''))
        company_name = job_data.get('company_name', '')
        
        # Use LLM to generate grounded evidence
        evidence = self._generate_evidence_with_llm(
            job_title, company_name, requirements, snippets, candidate_data
        )
        
        if emit_trace:
            emit_trace({'type': 'step_progress', 'step': 'evidence', 'message': f'Generated {len(evidence.get("why_me_bullets", []))} evidence bullets'})
        
        evidence['resume_snippets'] = snippets
        return evidence
    
    def _build_snippet_index(self, candidate_data: Dict[str, Any]) -> Dict[str, str]:
        """Build stable ID -> text mapping for resume snippets."""
        snippets = {}
        
        resume = candidate_data.get('resume', {})
        
        # Index experience
        experiences = resume.get('experience', [])
        for i, exp in enumerate(experiences):
            exp_id = f"exp_{i}"
            
            # Add overall description
            desc = exp.get('description', '')
            if desc:
                snippets[f"{exp_id}.desc"] = f"{exp.get('title', '')} at {exp.get('company', '')}: {desc}"
            
            # Add bullet points if available
            bullets = exp.get('bullet_points', [])
            if bullets:
                for j, bullet in enumerate(bullets):
                    snippets[f"{exp_id}.bullet_{j}"] = bullet
            elif desc:
                # Split description into sentences as fallback
                sentences = re.split(r'[.;]', desc)
                for j, sent in enumerate(sentences[:5]):
                    sent = sent.strip()
                    if len(sent) > 20:
                        snippets[f"{exp_id}.sent_{j}"] = sent
        
        # Index skills
        skills = resume.get('skills', [])
        if skills:
            snippets['skills'] = ', '.join(skills[:20])
        
        # Index summary
        summary = resume.get('summary', '')
        if summary:
            snippets['summary'] = summary
        
        # Index education
        education = resume.get('education', [])
        for i, edu in enumerate(education):
            degree = edu.get('degree', '')
            institution = edu.get('institution', '')
            if degree or institution:
                snippets[f"edu_{i}"] = f"{degree} from {institution}"
        
        return snippets
    
    def _generate_evidence_with_llm(
        self,
        job_title: str,
        company_name: str,
        requirements: str,
        snippets: Dict[str, str],
        candidate_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Use LLM to generate grounded evidence pack."""
        
        # Format snippets for prompt
        snippet_lines = []
        for sid, text in snippets.items():
            snippet_lines.append(f"[{sid}]: {text}")
        snippets_text = "\n".join(snippet_lines)
        
        prompt = f"""You are helping a candidate prepare evidence for a job application.

JOB:
- Title: {job_title}
- Company: {company_name}
- Requirements/Description:
{requirements[:3000]}

CANDIDATE RESUME SNIPPETS (with IDs for citation):
{snippets_text}

CANDIDATE NAME: {candidate_data.get('personal_info', {}).get('name', 'Candidate')}

Generate:
1. THREE "why me" bullets - concise statements explaining why this candidate is a great fit
2. TWO project angles - specific projects/experiences to highlight when talking to a hiring manager

Each item MUST cite specific resume snippets using their IDs.

Return JSON:
{{
    "why_me_bullets": [
        {{"text": "...", "citations": ["exp_0.desc", "skills"]}}
    ],
    "project_angles": [
        {{"text": "If discussing X, I would highlight my work on Y...", "citations": ["exp_1.bullet_0"]}}
    ]
}}

Make bullets specific, quantified where possible, and directly tied to job requirements.
Return ONLY valid JSON."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert career coach creating compelling job application evidence. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            text = response.choices[0].message.content.strip()
            data = json.loads(text)
            
            return {
                'why_me_bullets': data.get('why_me_bullets', []),
                'project_angles': data.get('project_angles', [])
            }
            
        except Exception as e:
            logger.error(f"Error generating evidence with LLM: {e}")
            return {
                'why_me_bullets': [],
                'project_angles': []
            }
