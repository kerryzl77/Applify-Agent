"""Research Agent: discovers and ranks contacts for a job campaign."""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI
import os

from app.universal_extractor import _http_get, _extract_main_text
from app.search.openai_web_search import openai_web_search

logger = logging.getLogger(__name__)


class ResearchAgent:
    """Discovers hiring team contacts using web search and LLM ranking."""
    
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
        Discover potential contacts for outreach.
        
        Returns list of contacts with: name, title, org, confidence, source_url, reason, tags
        """
        if emit_trace:
            emit_trace({'type': 'step_progress', 'step': 'research', 'message': 'Building search queries...'})
        
        # Build search queries
        queries = self._build_search_queries(company_name, job_title, team)
        
        if emit_trace:
            emit_trace({'type': 'step_progress', 'step': 'research', 'message': f'Searching with {len(queries)} queries...'})
        
        # Collect search results using OpenAI web search
        all_results = []
        for query in queries[:4]:  # Limit to 4 queries for speed
            results = openai_web_search(query, num_results=5)
            # Normalize to existing schema (href, title, body)
            for r in results:
                all_results.append({
                    "href": r.get("url", ""),
                    "title": r.get("title", ""),
                    "body": r.get("snippet", ""),
                })
        
        if emit_trace:
            emit_trace({'type': 'step_progress', 'step': 'research', 'message': f'Found {len(all_results)} search results, extracting contacts...'})
        
        # Dedupe by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            url = r.get('href', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
        
        # Fetch and extract page content for top results
        page_contents = []
        for result in unique_results[:8]:  # Limit fetches
            url = result.get('href', '')
            if not url:
                continue
            try:
                html = _http_get(url)
                if html:
                    main = _extract_main_text(html, url)
                    text = main.get('text', '')[:3000]  # Limit text
                    page_contents.append({
                        'url': url,
                        'title': result.get('title', ''),
                        'snippet': result.get('body', ''),
                        'text': text
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}")
        
        if emit_trace:
            emit_trace({'type': 'step_progress', 'step': 'research', 'message': f'Extracted content from {len(page_contents)} pages, analyzing for contacts...'})
        
        # Use LLM to extract and rank contacts
        contacts = self._extract_contacts_with_llm(
            company_name, job_title, team, page_contents
        )
        
        if emit_trace:
            emit_trace({'type': 'step_progress', 'step': 'research', 'message': f'Found {len(contacts)} potential contacts'})
        
        return contacts
    
    def _build_search_queries(
        self,
        company_name: str,
        job_title: str,
        team: Optional[str] = None,
    ) -> List[str]:
        """Build search queries for contact discovery."""
        queries = []
        
        # Try to infer company domain
        company_slug = re.sub(r'[^a-z0-9]', '', company_name.lower())
        
        # Team/leadership pages
        queries.append(f'"{company_name}" team OR leadership OR about us')
        
        # Recruiting/talent
        queries.append(f'"{company_name}" recruiter OR "talent acquisition" OR "people operations"')
        
        # Role-specific hiring manager
        job_function = self._extract_job_function(job_title)
        if job_function:
            queries.append(f'"{company_name}" "{job_function}" manager OR director OR lead')
        
        # Team-specific if available
        if team:
            queries.append(f'"{company_name}" "{team}" team')
        
        # GitHub for tech companies
        queries.append(f'site:github.com "{company_name}" OR "{company_slug}"')
        
        return queries
    
    def _extract_job_function(self, job_title: str) -> Optional[str]:
        """Extract the main function from job title."""
        title_lower = job_title.lower()
        
        functions = [
            'engineering', 'product', 'design', 'data', 'machine learning',
            'marketing', 'sales', 'operations', 'finance', 'hr', 'legal'
        ]
        
        for func in functions:
            if func in title_lower:
                return func
        
        # Try to extract first word if it looks like a function
        words = job_title.split()
        if words and len(words[0]) > 3:
            return words[0]
        
        return None
    
    def _extract_contacts_with_llm(
        self,
        company_name: str,
        job_title: str,
        team: Optional[str],
        page_contents: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Use LLM to extract structured contact candidates from page contents."""
        if not page_contents:
            return []
        
        # Build context from pages
        context_parts = []
        for page in page_contents[:6]:
            context_parts.append(
                f"URL: {page['url']}\n"
                f"Title: {page['title']}\n"
                f"Snippet: {page['snippet']}\n"
                f"Content: {page['text'][:2000]}\n---"
            )
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""Analyze the following web pages to identify potential contacts at {company_name} 
who might be relevant for someone applying for a {job_title} role{f' on the {team} team' if team else ''}.

Look for:
1. Recruiters / Talent Acquisition specialists at {company_name}
2. Hiring managers (engineering managers, directors, leads in relevant areas)
3. Team members who could provide warm introductions
4. Leaders mentioned on team/about pages

Web Page Contents:
{context}

Return a JSON array of contacts found. Each contact should have:
- name: Full name
- title: Job title/role
- org: Team or department if known
- confidence: 0.0-1.0 score for how relevant this person is
- source_url: URL where found
- reason: Why this person is relevant (1 sentence)
- tags: Array of tags like ["recruiter", "hiring_manager", "engineer", "product", "leadership"]

Only include people who are clearly at {company_name}. Return 5-15 contacts, ranked by relevance.
Return ONLY valid JSON array, no other text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "You are an expert at identifying relevant professional contacts from web content. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            text = response.choices[0].message.content.strip()
            data = json.loads(text)
            
            # Handle both array and object with 'contacts' key
            if isinstance(data, list):
                contacts = data
            elif isinstance(data, dict) and 'contacts' in data:
                contacts = data['contacts']
            else:
                contacts = []
            
            # Validate and normalize
            valid_contacts = []
            for c in contacts[:15]:
                if c.get('name') and c.get('title'):
                    valid_contacts.append({
                        'name': c.get('name', ''),
                        'title': c.get('title', ''),
                        'org': c.get('org', ''),
                        'confidence': float(c.get('confidence', 0.5)),
                        'source_url': c.get('source_url', ''),
                        'reason': c.get('reason', ''),
                        'tags': c.get('tags', [])
                    })
            
            # Sort by confidence
            valid_contacts.sort(key=lambda x: x['confidence'], reverse=True)
            
            return valid_contacts
            
        except Exception as e:
            logger.error(f"Error extracting contacts with LLM: {e}")
            return []
