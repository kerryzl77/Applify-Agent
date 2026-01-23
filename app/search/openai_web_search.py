"""OpenAI Web Search: Uses Responses API with web_search tool."""

import json
import logging
from typing import List, Dict, Optional

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
            model="gpt-4o",
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
