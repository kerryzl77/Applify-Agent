"""OpenAI Web Search: Uses Responses API with web_search tool."""

import json
import logging
import re
from typing import List, Dict, Optional, Set

from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI()


def openai_web_search(
    query: str,
    num_results: int = 5,
    allowed_domains: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Search the web using OpenAI's Responses API with web_search tool.
    
    Returns: [{"title": "...", "url": "...", "snippet": "..."}]
    """
    domain_hint = ""
    if allowed_domains:
        domain_hint = f"\nPrefer results from these domains: {allowed_domains}"

    prompt = f"""Search the web for: {query}{domain_hint}

Return ONLY valid JSON: an array of up to {num_results} results.
Each item must have: title, url, snippet.
No extra keys, no commentary."""

    try:
        resp = client.responses.create(
            model="gpt-5.2",
            tools=[{"type": "web_search"}],
            tool_choice={"type": "web_search"},
            input=prompt,
        )

        text = (resp.output_text or "").strip()
        
        # Try to extract JSON from response
        # Sometimes the model wraps in markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data[:num_results]
            elif isinstance(data, dict) and "results" in data:
                return data["results"][:num_results]
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from web search: {text[:200]}")
            
    except Exception as e:
        logger.error(f"OpenAI web search failed: {e}")

    return []


def _parse_linkedin_title(title: str, company_name: str) -> Optional[Dict[str, str]]:
    """
    Parse a LinkedIn result title to extract name and job title.
    
    Common LinkedIn title patterns:
    - "John Smith - Software Engineer - Company | LinkedIn"
    - "John Smith | Software Engineer at Company | LinkedIn"
    - "John Smith - Company | LinkedIn"
    """
    if not title:
        return None
    
    # Remove " | LinkedIn" suffix
    title = re.sub(r'\s*\|\s*LinkedIn\s*$', '', title, flags=re.IGNORECASE)
    
    # Try pattern: "Name - Title - Company" or "Name - Title at Company"
    # Pattern 1: "Name - Title - Company"
    match = re.match(r'^([^-|]+)\s*[-–]\s*([^-|]+)\s*[-–]\s*(.+)$', title)
    if match:
        name = match.group(1).strip()
        job_title = match.group(2).strip()
        detected_company = match.group(3).strip()
        # Verify it's the right company
        if company_name.lower() in detected_company.lower() or detected_company.lower() in company_name.lower():
            return {"name": name, "title": job_title}
    
    # Pattern 2: "Name | Title at Company"
    match = re.match(r'^([^|]+)\s*\|\s*(.+?)\s+at\s+(.+)$', title, flags=re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        job_title = match.group(2).strip()
        detected_company = match.group(3).strip()
        if company_name.lower() in detected_company.lower() or detected_company.lower() in company_name.lower():
            return {"name": name, "title": job_title}
    
    # Pattern 3: "Name - Title at Company"
    match = re.match(r'^([^-]+)\s*[-–]\s*(.+?)\s+at\s+(.+)$', title, flags=re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        job_title = match.group(2).strip()
        detected_company = match.group(3).strip()
        if company_name.lower() in detected_company.lower() or detected_company.lower() in company_name.lower():
            return {"name": name, "title": job_title}
    
    # Pattern 4: Simple "Name - Company" (title unknown)
    match = re.match(r'^([^-|]+)\s*[-–]\s*(.+)$', title)
    if match:
        name = match.group(1).strip()
        detected_company = match.group(2).strip()
        if company_name.lower() in detected_company.lower() or detected_company.lower() in company_name.lower():
            return {"name": name, "title": "Unknown"}
    
    return None


def _extract_name_from_linkedin_url(url: str) -> Optional[str]:
    """Extract a name from a LinkedIn profile URL like linkedin.com/in/john-smith."""
    if not url:
        return None
    
    match = re.search(r'linkedin\.com/in/([a-zA-Z0-9-]+)', url, flags=re.IGNORECASE)
    if match:
        slug = match.group(1)
        # Convert slug to name: john-smith -> John Smith
        # Filter out numeric suffixes like john-smith-12345
        parts = slug.split('-')
        name_parts = []
        for part in parts:
            if part.isdigit():
                break  # Stop at numeric suffix
            if len(part) > 1:  # Skip single letters
                name_parts.append(part.capitalize())
        if len(name_parts) >= 2:
            return ' '.join(name_parts)
    
    return None


def _calculate_confidence(
    result: Dict,
    company_name: str,
    is_recruiter_query: bool = False,
    is_hiring_manager_query: bool = False,
) -> float:
    """Calculate confidence score for a search result."""
    confidence = 0.5
    
    url = result.get("url", "").lower()
    title = result.get("title", "").lower()
    snippet = result.get("snippet", "").lower()
    company_lower = company_name.lower()
    
    # Boost for LinkedIn profile URLs
    if "linkedin.com/in/" in url:
        confidence += 0.15
    
    # Boost for company name in title/snippet
    if company_lower in title:
        confidence += 0.1
    if company_lower in snippet:
        confidence += 0.05
    
    # Boost for recruiter/hiring keywords
    recruiter_keywords = ['recruiter', 'talent', 'hr', 'people', 'human resources', 'talent acquisition']
    hiring_keywords = ['hiring', 'manager', 'director', 'lead', 'head of', 'vp']
    
    text = f"{title} {snippet}"
    
    if is_recruiter_query:
        if any(kw in text for kw in recruiter_keywords):
            confidence += 0.1
    
    if is_hiring_manager_query:
        if any(kw in text for kw in hiring_keywords):
            confidence += 0.1
    
    return min(confidence, 0.95)


def find_contacts_via_web_search(
    company_name: str,
    job_title: str,
    team: Optional[str] = None,
    location: Optional[str] = None,
) -> List[Dict]:
    """
    Use OpenAI web search with multiple targeted queries to find hiring contacts.
    
    Uses a multi-query approach:
    1. Run several targeted LinkedIn searches
    2. Parse result titles/snippets to extract names and titles
    3. Dedupe and score results by confidence
    
    Returns: [{"name": "...", "title": "...", "source_url": "...", "confidence": 0.8}]
    """
    logger.info(f"🔍 Searching for contacts at {company_name} for {job_title}")
    
    # Build location hint
    location_hint = f" {location}" if location else ""
    team_hint = f" {team}" if team else ""
    
    # Define multiple search queries to maximize coverage
    queries = [
        # Recruiter search
        {
            "query": f'site:linkedin.com/in "{company_name}" (recruiter OR "talent acquisition" OR "technical recruiter"){location_hint}',
            "is_recruiter": True,
            "is_hiring_manager": False,
        },
        # Hiring manager / engineering manager search
        {
            "query": f'site:linkedin.com/in "{company_name}" ("hiring manager" OR "engineering manager" OR "team lead"){team_hint}{location_hint}',
            "is_recruiter": False,
            "is_hiring_manager": True,
        },
        # Role-specific search
        {
            "query": f'site:linkedin.com/in "{company_name}" "{job_title}"{location_hint}',
            "is_recruiter": False,
            "is_hiring_manager": False,
        },
        # HR / People team search
        {
            "query": f'site:linkedin.com/in "{company_name}" (HR OR "people operations" OR "head of people"){location_hint}',
            "is_recruiter": True,
            "is_hiring_manager": False,
        },
    ]
    
    all_contacts: List[Dict] = []
    seen_urls: Set[str] = set()
    seen_names: Set[str] = set()
    
    for query_info in queries:
        query = query_info["query"]
        is_recruiter = query_info["is_recruiter"]
        is_hiring_manager = query_info["is_hiring_manager"]
        
        logger.debug(f"Running search: {query}")
        
        try:
            # Use direct web search prompt for better results
            search_prompt = f"""Search LinkedIn for: {query}

Return ONLY valid JSON with an array of search results:
[
    {{"title": "Person Name - Job Title - Company | LinkedIn", "url": "https://linkedin.com/in/...", "snippet": "..."}}
]

Include up to 5 results. Each must have title, url, snippet."""

            resp = client.responses.create(
                model="gpt-5.2",
                tools=[{"type": "web_search"}],
                tool_choice={"type": "web_search"},
                input=search_prompt,
            )
            
            text = (resp.output_text or "").strip()
            
            # Parse JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                parts = text.split("```")
                if len(parts) >= 2:
                    text = parts[1].strip()
            
            # Find array in response
            json_start = text.find('[')
            json_end = text.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                text = text[json_start:json_end]
            
            try:
                results = json.loads(text)
                if not isinstance(results, list):
                    results = []
            except json.JSONDecodeError:
                logger.debug(f"Failed to parse results JSON: {text[:200]}")
                results = []
            
            # Process each result
            for result in results:
                url = result.get("url", "")
                title = result.get("title", "")
                
                # Skip non-LinkedIn profile URLs
                if "linkedin.com/in/" not in url.lower():
                    continue
                
                # Dedupe by URL
                url_lower = url.lower()
                if url_lower in seen_urls:
                    continue
                seen_urls.add(url_lower)
                
                # Try to extract name and title from the result title
                parsed = _parse_linkedin_title(title, company_name)
                name = None
                job_title_parsed = "Unknown"
                
                if parsed:
                    name = parsed["name"]
                    job_title_parsed = parsed["title"]
                else:
                    # Fallback: extract name from URL
                    name = _extract_name_from_linkedin_url(url)
                
                if not name:
                    continue
                
                # Dedupe by name (case-insensitive)
                name_lower = name.lower()
                if name_lower in seen_names:
                    continue
                seen_names.add(name_lower)
                
                # Calculate confidence
                confidence = _calculate_confidence(
                    result, company_name, is_recruiter, is_hiring_manager
                )
                
                contact = {
                    "name": name,
                    "title": job_title_parsed,
                    "source_url": url,
                    "confidence": confidence,
                    "reason": f"Found via LinkedIn search for {company_name} contacts",
                }
                all_contacts.append(contact)
                
        except Exception as e:
            logger.warning(f"Query failed: {query[:50]}... - {e}")
            continue
    
    # Sort by confidence
    all_contacts.sort(key=lambda x: x["confidence"], reverse=True)
    
    logger.info(f"✅ Found {len(all_contacts)} contacts via multi-query web search")
    
    return all_contacts[:15]  # Limit to 15 contacts
