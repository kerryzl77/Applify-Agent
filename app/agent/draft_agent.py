"""Draft Agent: generates outreach drafts with feedback support."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


class DraftAgent:
    """Generates outreach drafts and follow-ups with additive feedback support."""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def generate_drafts(
        self,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        selected_contacts: Dict[str, Any],
        evidence_pack: Dict[str, Any],
        feedback: Optional[Dict[str, Any]] = None,
        emit_trace: callable = None,
    ) -> Dict[str, Any]:
        """
        Generate outreach drafts for selected contacts.
        
        Args:
            selected_contacts: {'recruiter': {...}, 'hiring_manager': {...}, 'warm_intro': {...}}
            feedback: {'global': [...], 'draft_specific': {'recruiter_email': [...]}}
        
        Returns:
            {
                'warm_intro': {'subject': ..., 'body': ...},
                'recruiter_email': {'subject': ..., 'body': ...},
                'hm_email': {'subject': ..., 'body': ...},
                'linkedin_note': {'body': ...}
            }
        """
        drafts = {}
        
        # Build feedback prompt section
        feedback_prompt = self._build_feedback_prompt(feedback)
        
        # Generate each draft type
        if selected_contacts.get('warm_intro'):
            if emit_trace:
                emit_trace({'type': 'step_progress', 'step': 'drafts', 'message': 'Generating warm intro draft...'})
            drafts['warm_intro'] = self._generate_warm_intro(
                job_data, candidate_data, selected_contacts['warm_intro'],
                evidence_pack, feedback_prompt, feedback.get('draft_specific', {}).get('warm_intro', []) if feedback else []
            )
        
        if selected_contacts.get('recruiter'):
            if emit_trace:
                emit_trace({'type': 'step_progress', 'step': 'drafts', 'message': 'Generating recruiter email...'})
            drafts['recruiter_email'] = self._generate_recruiter_email(
                job_data, candidate_data, selected_contacts['recruiter'],
                evidence_pack, feedback_prompt, feedback.get('draft_specific', {}).get('recruiter_email', []) if feedback else []
            )
        
        if selected_contacts.get('hiring_manager'):
            if emit_trace:
                emit_trace({'type': 'step_progress', 'step': 'drafts', 'message': 'Generating hiring manager email...'})
            drafts['hm_email'] = self._generate_hm_email(
                job_data, candidate_data, selected_contacts['hiring_manager'],
                evidence_pack, feedback_prompt, feedback.get('draft_specific', {}).get('hm_email', []) if feedback else []
            )
        
        # Optional LinkedIn note
        if emit_trace:
            emit_trace({'type': 'step_progress', 'step': 'drafts', 'message': 'Generating LinkedIn note...'})
        drafts['linkedin_note'] = self._generate_linkedin_note(
            job_data, candidate_data, evidence_pack, feedback_prompt
        )
        
        return drafts
    
    def _build_feedback_prompt(self, feedback: Optional[Dict[str, Any]]) -> str:
        """Build feedback section for prompts using additive approach."""
        if not feedback:
            return ""
        
        global_feedback = feedback.get('global', [])
        if not global_feedback:
            return ""
        
        # Sort by timestamp (newest first)
        sorted_feedback = sorted(
            global_feedback,
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )
        
        # Build prompt with newest as MUST, older as TRY
        must_items = []
        try_items = []
        
        for i, fb in enumerate(sorted_feedback):
            text = fb.get('text', '')
            if i < 2 or fb.get('must', False):
                must_items.append(f"- {text}")
            else:
                try_items.append(f"- {text}")
        
        sections = []
        if must_items:
            sections.append("USER FEEDBACK (MUST FOLLOW - newest is highest priority):\n" + "\n".join(must_items))
        if try_items:
            sections.append("USER FEEDBACK (TRY TO FOLLOW):\n" + "\n".join(try_items))
        
        return "\n\n".join(sections)
    
    def _build_draft_feedback_prompt(self, draft_feedback: List[Dict[str, Any]]) -> str:
        """Build draft-specific feedback section."""
        if not draft_feedback:
            return ""
        
        sorted_feedback = sorted(
            draft_feedback,
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )
        
        items = [f"- {fb.get('text', '')}" for fb in sorted_feedback[:3]]
        return "DRAFT-SPECIFIC FEEDBACK (MUST FOLLOW):\n" + "\n".join(items)
    
    def _generate_warm_intro(
        self,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        contact: Dict[str, Any],
        evidence_pack: Dict[str, Any],
        global_feedback: str,
        draft_feedback: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Generate warm intro ask email."""
        draft_fb = self._build_draft_feedback_prompt(draft_feedback)
        
        candidate_name = candidate_data.get('personal_info', {}).get('name', 'Candidate')
        job_title = job_data.get('job_title', job_data.get('title', ''))
        company = job_data.get('company_name', '')
        
        why_me = "\n".join([b.get('text', '') for b in evidence_pack.get('why_me_bullets', [])])
        
        prompt = f"""Write a warm introduction request email.

CONTEXT:
- Candidate: {candidate_name}
- Target Role: {job_title} at {company}
- Contact: {contact.get('name', 'Contact')} - {contact.get('title', '')}
- Contact is: {contact.get('reason', 'someone who might help with an intro')}

CANDIDATE STRENGTHS:
{why_me}

{global_feedback}

{draft_fb}

Write a brief, warm email asking for advice or introduction regarding the {job_title} role.
- Keep it under 150 words
- Be specific about why you're reaching out to THIS person
- Don't be pushy, focus on asking for advice/insights
- Professional but personable tone

Return JSON: {{"subject": "...", "body": "..."}}"""

        return self._call_llm_for_draft(prompt)
    
    def _generate_recruiter_email(
        self,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        contact: Dict[str, Any],
        evidence_pack: Dict[str, Any],
        global_feedback: str,
        draft_feedback: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Generate recruiter outreach email."""
        draft_fb = self._build_draft_feedback_prompt(draft_feedback)
        
        candidate_name = candidate_data.get('personal_info', {}).get('name', 'Candidate')
        candidate_email = candidate_data.get('personal_info', {}).get('email', '')
        job_title = job_data.get('job_title', job_data.get('title', ''))
        company = job_data.get('company_name', '')
        
        why_me = "\n".join([b.get('text', '') for b in evidence_pack.get('why_me_bullets', [])])
        
        prompt = f"""Write a recruiter outreach email.

CONTEXT:
- Candidate: {candidate_name} ({candidate_email})
- Target Role: {job_title} at {company}
- Recruiter: {contact.get('name', 'Recruiting Team')} - {contact.get('title', '')}

CANDIDATE STRENGTHS:
{why_me}

{global_feedback}

{draft_fb}

Write a professional email expressing interest in the {job_title} role.
- Keep it under 200 words
- Highlight 2-3 key qualifications
- Clear call to action (request to discuss)
- Professional, enthusiastic tone

Return JSON: {{"subject": "...", "body": "..."}}"""

        return self._call_llm_for_draft(prompt)
    
    def _generate_hm_email(
        self,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        contact: Dict[str, Any],
        evidence_pack: Dict[str, Any],
        global_feedback: str,
        draft_feedback: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Generate hiring manager email."""
        draft_fb = self._build_draft_feedback_prompt(draft_feedback)
        
        candidate_name = candidate_data.get('personal_info', {}).get('name', 'Candidate')
        candidate_email = candidate_data.get('personal_info', {}).get('email', '')
        job_title = job_data.get('job_title', job_data.get('title', ''))
        company = job_data.get('company_name', '')
        
        why_me = "\n".join([b.get('text', '') for b in evidence_pack.get('why_me_bullets', [])])
        project_angles = "\n".join([a.get('text', '') for a in evidence_pack.get('project_angles', [])])
        
        prompt = f"""Write a hiring manager outreach email.

CONTEXT:
- Candidate: {candidate_name} ({candidate_email})
- Target Role: {job_title} at {company}
- Hiring Manager: {contact.get('name', 'Hiring Manager')} - {contact.get('title', '')}

CANDIDATE STRENGTHS:
{why_me}

PROJECT ANGLES TO HIGHLIGHT:
{project_angles}

{global_feedback}

{draft_fb}

Write a compelling email directly to the hiring manager.
- Keep it under 200 words
- Show understanding of the role/team
- Highlight specific relevant experience
- Confident but not arrogant tone
- Clear ask for next steps

Return JSON: {{"subject": "...", "body": "..."}}"""

        return self._call_llm_for_draft(prompt)
    
    def _generate_linkedin_note(
        self,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        evidence_pack: Dict[str, Any],
        global_feedback: str,
    ) -> Dict[str, str]:
        """Generate LinkedIn connection note."""
        candidate_name = candidate_data.get('personal_info', {}).get('name', 'Candidate')
        job_title = job_data.get('job_title', job_data.get('title', ''))
        company = job_data.get('company_name', '')
        
        prompt = f"""Write a LinkedIn connection request note.

CONTEXT:
- Candidate: {candidate_name}
- Target: Someone at {company} regarding {job_title} role

{global_feedback}

Write a brief LinkedIn connection note (under 200 characters for LinkedIn limit).
- Personal, specific
- Mention the role
- No hard sell

Return JSON: {{"body": "..."}}"""

        result = self._call_llm_for_draft(prompt)
        return {'body': result.get('body', '')}
    
    def _call_llm_for_draft(self, prompt: str) -> Dict[str, str]:
        """Call LLM to generate a draft."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-5.2",
                messages=[
                    {"role": "system", "content": "You are an expert at writing professional outreach emails. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            text = response.choices[0].message.content.strip()
            return json.loads(text)
            
        except Exception as e:
            logger.error(f"Error generating draft: {e}")
            return {'subject': '', 'body': f'Error generating draft: {str(e)}'}
    
    def generate_followups(
        self,
        original_drafts: Dict[str, Any],
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        emit_trace: callable = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate follow-up variants for day 3, 7, 14.
        
        Returns:
            {
                'recruiter_email': [
                    {'day': 3, 'subject': ..., 'body': ...},
                    {'day': 7, 'subject': ..., 'body': ...},
                    {'day': 14, 'subject': ..., 'body': ...}
                ],
                ...
            }
        """
        followups = {}
        
        for draft_type in ['recruiter_email', 'hm_email']:
            if draft_type not in original_drafts:
                continue
            
            if emit_trace:
                emit_trace({'type': 'step_progress', 'step': 'drafts', 'message': f'Generating follow-ups for {draft_type}...'})
            
            original = original_drafts[draft_type]
            followups[draft_type] = self._generate_followup_sequence(
                original, job_data, candidate_data, draft_type
            )
        
        return followups
    
    def _generate_followup_sequence(
        self,
        original: Dict[str, str],
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        draft_type: str,
    ) -> List[Dict[str, Any]]:
        """Generate follow-up sequence for a single draft."""
        job_title = job_data.get('job_title', job_data.get('title', ''))
        company = job_data.get('company_name', '')
        candidate_name = candidate_data.get('personal_info', {}).get('name', 'Candidate')
        
        prompt = f"""Generate 3 follow-up emails for this original email.

ORIGINAL EMAIL:
Subject: {original.get('subject', '')}
Body: {original.get('body', '')}

CONTEXT:
- Candidate: {candidate_name}
- Role: {job_title} at {company}
- Email type: {draft_type}

Generate follow-ups for:
1. Day 3: Brief check-in, polite reminder
2. Day 7: Add new value (insight, article, idea)
3. Day 14: Final, shorter, offer to reconnect later

Each follow-up should be SHORTER than the previous.

Return JSON:
{{
    "followups": [
        {{"day": 3, "subject": "...", "body": "..."}},
        {{"day": 7, "subject": "...", "body": "..."}},
        {{"day": 14, "subject": "...", "body": "..."}}
    ]
}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-5.2",
                messages=[
                    {"role": "system", "content": "You are an expert at writing professional follow-up emails. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            text = response.choices[0].message.content.strip()
            data = json.loads(text)
            return data.get('followups', [])
            
        except Exception as e:
            logger.error(f"Error generating followups: {e}")
            return []
