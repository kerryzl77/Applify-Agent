"""Research Agent: discovers and ranks contacts for a job campaign."""

import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI
import os

from app.search.openai_web_search import find_contacts_via_web_search

logger = logging.getLogger(__name__)


class ResearchAgent:
    """Discovers hiring team contacts using web search and LLM."""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def discover_contacts(
        self,
        company_name: str,
        job_title: str,
        team: Optional[str] = None,
        location: Optional[str] = None,
        emit_trace: callable = None,
    ) -> List[Dict[str, Any]]:
        """
        Discover potential contacts for outreach using web search.
        
        Uses a simple one-shot approach: OpenAI web search finds and 
        synthesizes contact information directly. No page fetching needed.
        
        Returns list of contacts with: name, title, org, confidence, source_url, reason, tags
        """
        if emit_trace:
            emit_trace({'type': 'step_progress', 'step': 'research', 'message': 'Searching for hiring contacts...'})
        
        # Use the one-shot web search approach
        raw_contacts = find_contacts_via_web_search(company_name, job_title, team)
        
        if emit_trace:
            emit_trace({'type': 'step_progress', 'step': 'research', 'message': f'Found {len(raw_contacts)} contacts from web search'})
        
        if not raw_contacts:
            # Fallback: try a broader search
            if emit_trace:
                emit_trace({'type': 'step_progress', 'step': 'research', 'message': 'Trying broader search...'})
            raw_contacts = self._fallback_search(company_name, job_title)
        
        # Enrich contacts with tags
        contacts = []
        for c in raw_contacts:
            contact = {
                'name': c.get('name', ''),
                'title': c.get('title', ''),
                'org': company_name,
                'confidence': float(c.get('confidence', 0.5)),
                'source_url': c.get('source_url', ''),
                'reason': c.get('reason', f'Relevant for {job_title} at {company_name}'),
                'tags': self._infer_tags(c.get('title', '')),
            }
            contacts.append(contact)
        
        # Sort by confidence
        contacts.sort(key=lambda x: x['confidence'], reverse=True)
        
        if emit_trace:
            emit_trace({'type': 'step_progress', 'step': 'research', 'message': f'Found {len(contacts)} contacts'})
        
        return contacts[:15]  # Limit to 15 contacts
    
    def _fallback_search(self, company_name: str, job_title: str) -> List[Dict]:
        """Fallback: broader search if first attempt finds nothing."""
        try:
            # Try a more generic search for the company's hiring team
            prompt = f"""Search for the hiring team and recruiters at {company_name}.

Find anyone who works in recruiting, talent acquisition, HR, or hiring at {company_name}.
Also look for engineering managers or team leads at {company_name}.

Return ONLY valid JSON:
{{
    "contacts": [
        {{"name": "Person Name", "title": "Their Job Title", "source_url": "URL", "confidence": 0.7}}
    ]
}}

If no specific people found, return {{"contacts": []}}"""

            resp = self.client.responses.create(
                model="gpt-5.2",
                tools=[{"type": "web_search"}],
                tool_choice={"type": "web_search"},
                input=prompt,
            )
            
            text = (resp.output_text or "").strip()
            
            # Clean up response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                parts = text.split("```")
                if len(parts) >= 2:
                    text = parts[1].strip()
            
            # Extract JSON
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                text = text[json_start:json_end]
            
            data = json.loads(text)
            return data.get("contacts", [])
            
        except Exception as e:
            logger.warning(f"Fallback search failed: {e}")
            return []
    
    def _infer_tags(self, title: str) -> List[str]:
        """Infer contact tags from job title."""
        title_lower = title.lower()
        tags = []
        
        if any(kw in title_lower for kw in ['recruit', 'talent', 'hr', 'people']):
            tags.append('recruiter')
        if any(kw in title_lower for kw in ['manager', 'director', 'head', 'vp']):
            tags.append('hiring_manager')
        if any(kw in title_lower for kw in ['engineer', 'developer', 'scientist']):
            tags.append('engineer')
        if any(kw in title_lower for kw in ['lead', 'principal', 'staff', 'senior']):
            tags.append('leadership')
        if any(kw in title_lower for kw in ['product', 'pm']):
            tags.append('product')
        
        return tags
