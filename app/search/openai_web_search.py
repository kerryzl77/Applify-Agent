"""OpenAI Web Search: Uses Responses API with web_search tool."""

import json
import logging
from typing import List, Dict, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI()


def _get_value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _extract_tool_results(resp) -> Optional[List[Dict]]:
    """Prefer structured tool output when available."""
    raw = None
    if hasattr(resp, "model_dump"):
        try:
            raw = resp.model_dump()
        except Exception:
            raw = None
    if isinstance(raw, dict):
        for item in raw.get("output", []) or []:
            if isinstance(item, dict) and item.get("type") == "web_search_call":
                results = item.get("results")
                if isinstance(results, list):
                    return results

    output = getattr(resp, "output", None)
    if output:
        for item in output:
            item_type = _get_value(item, "type")
            if item_type == "web_search_call":
                results = _get_value(item, "results")
                if isinstance(results, list):
                    return results
    return None


def _extract_json_payload(text: str) -> str:
    if not text:
        return ""
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()

    return text.strip()


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
            model="gpt-4.1",
            tools=[{"type": "web_search"}],
            tool_choice={"type": "web_search"},
            input=prompt,
        )

        tool_results = _extract_tool_results(resp)
        if tool_results:
            return tool_results[:num_results]

        text = (resp.output_text or "").strip()
        
        # Try to extract JSON from response
        # Sometimes the model wraps in markdown code blocks
        text = _extract_json_payload(text)
        
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


def find_contacts_via_web_search(
    company_name: str,
    job_title: str,
    team: Optional[str] = None,
) -> List[Dict]:
    """
    Use OpenAI web search to find and synthesize hiring contacts directly.
    
    This is a one-shot approach: web search + synthesis in a single call.
    No page fetching needed - the model synthesizes from search results.
    
    Returns: [{"name": "...", "title": "...", "source_url": "...", "confidence": 0.8}]
    """
    team_hint = f" on the {team} team" if team else ""
    
    search_prompt = f"""Find people at {company_name} who might be involved in hiring for {job_title} roles{team_hint}.

Search for:
1. {company_name} recruiters or talent acquisition on LinkedIn
2. {company_name} hiring managers or engineering managers on LinkedIn  
3. {company_name} team leads for {job_title} related roles

For each person you find, extract:
- Their full name (from LinkedIn URL like linkedin.com/in/john-smith = John Smith)
- Their job title
- Their LinkedIn profile URL

Return ONLY valid JSON:
{{
    "contacts": [
        {{"name": "Full Name", "title": "Job Title", "source_url": "linkedin URL", "confidence": 0.9}}
    ]
}}

If you cannot find specific people with names, return {{"contacts": []}}
Only include people who clearly work at {company_name}."""

    try:
        logger.info(f"🔍 Searching for contacts at {company_name} for {job_title}")
        
        resp = client.responses.create(
            model="gpt-4.1",
            tools=[{"type": "web_search"}],
            tool_choice={"type": "web_search"},
            input=search_prompt,
        )

        text = (resp.output_text or "").strip()
        logger.info(f"📝 Web search response length: {len(text)} chars")
        
        # Clean up markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1].strip()
        
        # Find JSON object in response
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            text = text[json_start:json_end]
        
        try:
            data = json.loads(text)
            contacts = data.get("contacts", [])
            
            # Validate and normalize
            valid_contacts = []
            for c in contacts:
                name = c.get("name", "").strip()
                if name and name.lower() not in ["unknown", "n/a", ""]:
                    valid_contacts.append({
                        "name": name,
                        "title": c.get("title", "Unknown"),
                        "source_url": c.get("source_url", ""),
                        "confidence": float(c.get("confidence", 0.7)),
                        "reason": f"Found via web search for {company_name} hiring contacts",
                    })
            
            logger.info(f"✅ Found {len(valid_contacts)} contacts via web search")
            return valid_contacts
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse contacts JSON: {e}")
            logger.debug(f"Raw text: {text[:500]}")
            
    except Exception as e:
        logger.error(f"Contact web search failed: {e}")

    return []
