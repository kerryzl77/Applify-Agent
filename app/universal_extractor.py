import re
import json
import logging
from typing import Dict, Any, List, Optional
import os

import requests
from html_text import extract_text as html_extract_text
try:
    from readability import Document  # type: ignore
except Exception:  # pragma: no cover
    Document = None  # optional dependency
from bs4 import BeautifulSoup
from openai import OpenAI

try:
    from ddgs import DDGS
except Exception:
    DDGS = None

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _http_get(url: str) -> Optional[str]:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
            timeout=15,
            allow_redirects=True,
        )
        logger.debug(
            f"HTTP GET {url} returned status {resp.status_code}, content length: {len(resp.text) if resp.text else 0}"
        )
        # Accept 200 responses normally; accept 999 for LinkedIn which still returns HTML
        if resp.text and (resp.status_code == 200 or (resp.status_code == 999 and "linkedin" in url.lower())):
            if resp.status_code != 200:
                logger.info(
                    f"Accepting LinkedIn non-200 status {resp.status_code} with {len(resp.text)} chars of content"
                )
            return resp.text
        logger.warning(f"Non-200 status code {resp.status_code} for {url}")
    except Exception as exc:
        logger.warning(f"fetch error for {url}: {exc}")
    return None


def _extract_main_text(html: str, url: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {"title": "", "text": ""}
    try:
        # Primary: robust text extraction from HTML
        txt = html_extract_text(html) or ""
        data["text"] = txt.strip()
    except Exception:
        data["text"] = ""

    if Document is not None:
        try:
            doc = Document(html)
            if not data["text"]:
                summary_html = doc.summary(html_partial=True) or ""
                try:
                    data["text"] = (html_extract_text(summary_html) or "").strip()
                except Exception:
                    pass
            data["title"] = doc.short_title() or data.get("title") or ""
        except Exception:
            pass

    # As last resort, use <title>
    if not data.get("title"):
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if m:
            data["title"] = re.sub(r"\s+", " ", m.group(1)).strip()

    return data


def _extract_structured_data(html: str, url: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"json_ld": [], "og": {}, "meta": {}}
    try:
        soup = BeautifulSoup(html, 'html.parser')
        # JSON-LD script tags
        for tag in soup.find_all('script', attrs={'type': lambda v: v and 'ld+json' in v}):
            try:
                data = json.loads(tag.string or '{}')
                if isinstance(data, list):
                    result["json_ld"].extend(data)
                elif isinstance(data, dict):
                    result["json_ld"].append(data)
            except Exception:
                continue
        # OpenGraph and meta tags
        og: Dict[str, Any] = {}
        for meta in soup.find_all('meta'):
            key = meta.get('property') or meta.get('name')
            val = meta.get('content')
            if not key or not val:
                continue
            if key.startswith('og:'):
                og[key] = val
            if key in ("description", "og:description", "og:title", "twitter:title", "twitter:description"):
                result.setdefault("meta", {})[key] = val
        result["og"] = og
    except Exception:
        pass

    # Basic meta fallback
    try:
        for name in ["description", "og:description", "og:title", "twitter:title", "twitter:description"]:
            m = re.search(rf"<meta[^>]+(?:name|property)=\"{re.escape(name)}\"[^>]+content=\"([^\"]+)\"", html, re.IGNORECASE)
            if m:
                result.setdefault("meta", {})[name] = m.group(1)
    except Exception:
        pass

    return result


def duckduckgo_signals(query: str, max_n: int = 5) -> List[Dict[str, Any]]:
    signals: List[Dict[str, Any]] = []
    if not DDGS:
        logger.warning("DuckDuckGo search not available (DDGS not installed)")
        return signals
    
    # Retry configuration for rate limit handling
    max_retries = 3
    retry_delay = 2.0  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🔍 Searching DuckDuckGo for: {query} (attempt {attempt + 1}/{max_retries})")
            # Fix async event loop issue in gunicorn threads
            import asyncio
            import time
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Add delay between attempts to avoid rate limiting
            if attempt > 0:
                delay = retry_delay * (2 ** (attempt - 1))  # exponential backoff
                logger.info(f"  ⏳ Waiting {delay}s before retry...")
                time.sleep(delay)

            with DDGS(timeout=20) as ddgs:
                for r in ddgs.text(query, max_results=max_n):
                    signals.append({
                        "title": r.get("title"),
                        "href": r.get("href"),
                        "body": r.get("body"),
                        "source": r.get("source")
                    })
            
            logger.info(f"✅ DuckDuckGo returned {len(signals)} results")
            return signals  # Success - exit retry loop
            
        except Exception as exc:
            error_msg = str(exc)
            if "Ratelimit" in error_msg or "202" in error_msg:
                logger.warning(f"⚠️ Rate limit hit (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    continue  # Try again
                else:
                    logger.warning("⚠️ Max retries reached, returning empty results")
            else:
                logger.warning(f"⚠️ DuckDuckGo search failed: {exc}")
                break  # Non-rate-limit error, don't retry
    
    return signals


def _google_cse_search(query: str, num: int = 5) -> List[Dict[str, Any]]:
    """Search using Google Custom Search Engine if configured.

    Returns a list of result dicts with keys: title, href, body, source.
    """
    api_key = os.getenv("GOOGLE_CSE_API_KEY")
    cx = os.getenv("GOOGLE_CSE_CX")
    if not api_key or not cx:
        logger.info("⚠️ Google CSE not configured (missing API_KEY or CX)")
        return []
    try:
        logger.info(f"🔍 Searching Google CSE for: {query}")
        params = {"key": api_key, "cx": cx, "q": query, "num": min(num, 10)}
        resp = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"⚠️ Google CSE returned {resp.status_code} for query '{query}'")
            return []
        data = resp.json()
        results: List[Dict[str, Any]] = []
        for item in data.get("items", [])[:num]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "href": item.get("link", ""),
                    "body": item.get("snippet", ""),
                    "source": "google",
                }
            )
        logger.info(f"✅ Google CSE returned {len(results)} results")
        return results
    except Exception as exc:
        logger.warning(f"⚠️ Google CSE search failed: {exc}")
        return []


def _web_search_candidates(
    name_hint: str,
    position: Optional[str],
    company: Optional[str],
    target_url: str,
    max_total: int = 6,
) -> Dict[str, List[Dict[str, Any]]]:
    """Collect minimal web search results for candidate identification.

    Returns a dict with keys:
      - candidates: prioritized list of results (dict with title, href, body, source)
      - extra: additional results for context building
    """
    queries: List[str] = []
    safe_name = name_hint.strip()
    if safe_name:
        queries.append(f'"{safe_name}" site:linkedin.com/in')
        if position or company:
            ctx = " ".join([x for x in [position, company] if x])
            queries.append(f'"{safe_name}" {ctx}'.strip())
        queries.append(f'"{safe_name}" (github OR "about" OR resume OR cv)')
    else:
        queries.append(target_url)

    seen: set[str] = set()
    merged: List[Dict[str, Any]] = []
    logger.info(f"🔎 Running {len(queries)} search queries for candidate discovery")
    for i, q in enumerate(queries, 1):
        logger.info(f"  Query {i}/{len(queries)}: {q}")
        g = _google_cse_search(q, num=5)
        results = g
        if not results:
            logger.info(f"  → Google CSE returned 0 results, trying DDG...")
            results = duckduckgo_signals(q, max_n=5)
        logger.info(f"  → Got {len(results)} results from this query")
        for r in results:
            href = r.get("href") or ""
            if not href or href in seen:
                continue
            seen.add(href)
            merged.append(r)
        # Don't break early - we need Query 3 (github/resume/cv) for non-LinkedIn sources!

    def _priority(u: str) -> int:
        u_low = u.lower()
        if "linkedin.com/in/" in u_low:
            return 0
        if "github.com/" in u_low or "about" in u_low:
            return 1
        return 2

    merged.sort(key=lambda r: _priority(r.get("href", "")))
    candidates = merged[: min(3, len(merged))]
    extra = merged[min(3, len(merged)) : min(max_total, len(merged))]
    logger.info(f"✅ Collected {len(candidates)} candidates and {len(extra)} extra results from web search")
    if candidates:
        for i, c in enumerate(candidates, 1):
            logger.info(f"   Candidate {i}: {c.get('title', 'No title')[:60]} - {c.get('href', '')}")
    return {"candidates": candidates, "extra": extra}


def _llm_choose_candidate(
    target_url: str,
    candidates: List[Dict[str, Any]],
    name_hint: str,
    position: Optional[str],
    company: Optional[str],
) -> int:
    """Use LLM to select which candidate corresponds to the target person.

    Returns 1-based index of the best candidate, or 0 if none.
    """
    if not candidates:
        logger.info("⚠️ No candidates to match (skipping LLM selection)")
        return 0

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("⚠️ OpenAI API key not configured (skipping LLM matching)")
        return 0

    logger.info(f"🤖 Running LLM candidate matching for {len(candidates)} candidates")
    client = OpenAI(api_key=api_key)

    lines: List[str] = []
    for i, c in enumerate(candidates, start=1):
        lines.append(f"{i}. URL: {c.get('href','')}")
        if c.get("title"):
            lines.append(f"   Title: {c.get('title','')}")
        if c.get("body"):
            lines.append(f"   Snippet: {c.get('body','')}")
    candidates_text = "\n".join(lines)

    hints: List[str] = []
    if name_hint:
        hints.append(f"Target name: {name_hint}")
    if position:
        hints.append(f"Position: {position}")
    if company:
        hints.append(f"Company: {company}")
    hints_text = "\n".join(hints) if hints else "(none)"

    system_prompt = (
        "You are an expert at matching people to their online profiles. "
        "Identify which candidate corresponds to the same person as the provided LinkedIn URL. "
        "Consider name matching, role/company hints, and URL/domain relevance. "
        "Return ONLY JSON with fields: matched_index (number 1-N or 0), confidence (0-1), reasoning (short)."
    )
    user_prompt = (
        f"LinkedIn URL: {target_url}\n\n"
        f"Hints:\n{hints_text}\n\n"
        f"Candidates:\n{candidates_text}\n\n"
        "Which index best matches the target person?"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        text = (resp.choices[0].message.content or "").strip()
        data = json.loads(text)
        idx = int(data.get("matched_index", 0) or 0)
        conf = float(data.get("confidence", 0) or 0)
        reasoning = data.get("reasoning", "")
        if 1 <= idx <= len(candidates) and conf >= 0.5:
            logger.info(f"✅ LLM matched candidate #{idx} (confidence: {conf:.2f})")
            logger.info(f"   Reasoning: {reasoning}")
            logger.info(f"   Matched URL: {candidates[idx-1].get('href', '')}")
            return idx
        else:
            logger.info(f"⚠️ LLM match unsuccessful (idx={idx}, conf={conf:.2f})")
            return 0
    except Exception as exc:
        logger.warning(f"⚠️ LLM choose candidate failed: {exc}")
        return 0


def _fetch_docs(urls: List[str]) -> List[Dict[str, Any]]:
    """Fetch and extract a small set of documents (title + text)."""
    logger.info(f"📄 Fetching up to 3 documents from {len(urls)} candidate URLs")
    docs: List[Dict[str, Any]] = []
    for i, u in enumerate(urls, 1):
        logger.info(f"  Fetching doc {i}/{len(urls)}: {u}")
        html = _http_get(u)
        if not html:
            logger.info(f"   → Failed to fetch (no HTML)")
            continue
        main = _extract_main_text(html, u)
        text = (main.get("text") or "").strip()
        if not text:
            logger.info(f"   → No text content extracted")
            continue
        logger.info(f"   → ✅ Extracted {len(text)} chars")
        docs.append({"url": u, "title": main.get("title", ""), "text": text})
        if len(docs) >= 3:
            break
    logger.info(f"✅ Fetched {len(docs)} documents for LLM aggregation")
    return docs


def _llm_profile_from_docs(
    docs: List[Dict[str, Any]],
    name_hint: str,
    position: Optional[str],
    company: Optional[str],
    target_url: str,
) -> Optional[Dict[str, Any]]:
    """Aggregate a few public documents and extract a concise professional profile."""
    logger.info(f"🤖 Running LLM profile extraction from {len(docs)} documents")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("⚠️ OpenAI API key not configured (skipping LLM extraction)")
        return None
    client = OpenAI(api_key=api_key)

    # Build compact context
    parts: List[str] = []
    for d in docs[:3]:
        title = d.get("title", "").strip()
        text = (d.get("text", "") or "").strip()
        if not text:
            continue
        snippet = text[:4000]
        parts.append(
            f"URL: {d.get('url','')}\nTITLE: {title}\nCONTENT:\n{snippet}\n\n---"
        )

    if not parts:
        return None

    hints: List[str] = []
    if name_hint:
        hints.append(f"Expected name: {name_hint}")
    if position:
        hints.append(f"Expected position: {position}")
    if company:
        hints.append(f"Expected company: {company}")
    hints_text = "\n".join(hints)

    system_prompt = (
        "You are an elite information extraction model. "
        "Synthesize a professional profile from the provided web snippets. "
        "Only use facts explicitly supported by the context. If a field is unknown, use empty string or empty array. "
        "Be concise and accurate; deduplicate entities and normalize names. Return ONLY valid JSON."
    )
    user_prompt = (
        "Extract this JSON schema: {\n"
        "  name, headline, title, company, location, about,\n"
        "  skills (<=10),\n"
        "  experience (<=3 items with title, company, start_date, end_date, description),\n"
        "  education (<=2 items with institution, degree),\n"
        "  industry, connections\n}.\n"
        f"Fallback name (if absent): {name_hint}\n\n"
        f"Target LinkedIn URL: {target_url}\n"
        f"Context hints:\n{hints_text}\n\n"
        f"Context documents:\n{''.join(parts)}"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=900,
            response_format={"type": "json_object"},
        )
        text = (resp.choices[0].message.content or "").strip()
        profile = json.loads(text)
        logger.info(f"✅ LLM extracted profile: name={profile.get('name', 'N/A')}, title={profile.get('title', 'N/A')}")
        logger.info(f"   Skills: {len(profile.get('skills', []))} | Experience: {len(profile.get('experience', []))} | Education: {len(profile.get('education', []))}")
        return profile
    except Exception as exc:
        logger.warning(f"⚠️ LLM profile-from-docs failed: {exc}")
        return None


def parse_linkedin_slug(url: str) -> str:
    m = re.search(r"/in/([^/?#]+)", url)
    if not m:
        return ""
    slug = m.group(1)
    name = re.sub(r"[-_]+", " ", slug).strip()
    name = " ".join(w.capitalize() for w in name.split())
    return name


def build_profile_from_signals(signals: List[Dict[str, Any]], fallback_name: str) -> Dict[str, Any]:
    name = fallback_name
    headline = ""
    company = ""
    location = ""

    for s in signals:
        title = (s.get("title") or "").strip()
        body = (s.get("body") or "").strip()
        line = f"{title} - {body}".lower()
        if not name and title:
            # Heuristic: names at start of titles
            parts = title.split("|")
            if parts:
                maybe = parts[0].strip()
                if 2 <= len(maybe.split()) <= 4:
                    name = maybe
        if not headline and title and "linkedin" not in (s.get("source") or "").lower():
            headline = title[:120]
        if not company:
            m = re.search(r" at ([A-Z][A-Za-z0-9& .-]{2,})", title)
            if m:
                company = m.group(1).strip()
        if not location:
            m = re.search(r"\b([A-Z][A-Za-z .-]{2,}),\s*([A-Z][A-Za-z .-]{2,})\b", line)
            if m:
                location = f"{m.group(1)} {m.group(2)}".strip()

    return {
        "name": name or fallback_name,
        "headline": headline,
        "company": company,
        "location": location,
        "experience": [],
    }


def extract_url(url: str) -> Dict[str, Any]:
    html = _http_get(url) or ""
    if not html:
        return {"url": url, "title": "", "text": "", "json_ld": [], "og": {}, "meta": {}}

    main = _extract_main_text(html, url)
    structured = _extract_structured_data(html, url)

    site_type = "generic"
    if "linkedin.com" in url:
        site_type = "linkedin"

    return {
        "url": url,
        "site": site_type,
        "title": main.get("title", ""),
        "text": main.get("text", ""),
        "json_ld": structured.get("json_ld", []),
        "og": structured.get("og", {}),
        "meta": structured.get("meta", {}),
    }


def extract_linkedin_profile(
    url: str,
    name: Optional[str] = None,
    position: Optional[str] = None,
    company: Optional[str] = None,
) -> Dict[str, Any]:
    """Robust, minimal-search LinkedIn enrichment pipeline.

    Steps:
      1) Try to parse whatever HTML we can get from the LinkedIn URL (handles 999).
      2) Perform minimal web searches to collect up to 3 candidates + a few extras.
      3) Use LLM to choose the best candidate based on the LinkedIn URL and hints.
      4) Fetch a few public documents and perform LLM extraction of a concise profile.
    """
    # Step 0: Hints and slug
    name_hint = (name or "").strip() or parse_linkedin_slug(url)

    # Step 1: Attempt direct context extraction from LinkedIn HTML if available
    base = extract_url(url)
    text_len = len((base.get("text") or "").strip())
    has_json_ld = bool(base.get("json_ld"))
    logger.info(
        f"Base extraction: text_len={text_len}, has_json_ld={has_json_ld}, title='{base.get('title', '')}'"
    )

    llm_profile: Optional[Dict[str, Any]] = None
    try:
        context_text = (base.get("text") or "").strip()
        title = (base.get("title") or "").strip()
        meta_desc = (
            base.get("meta", {}).get("description")
            or base.get("meta", {}).get("og:description")
            or ""
        ).strip()
        combined = "\n\n".join(x for x in [title, meta_desc, context_text] if x)
        if combined:
            llm_profile = _llm_profile_from_context(combined[:6000], title)
    except Exception:
        llm_profile = None

    # Check if we have EXCEPTIONALLY RICH profile data that makes search unnecessary
    # We require MULTIPLE strong signals to skip the search enrichment pipeline
    has_exceptional_data = llm_profile and (
        # Need at least 3 experiences AND (education OR 10+ skills OR 200+ char about)
        (len(llm_profile.get("experience", [])) >= 3 and (
            len(llm_profile.get("education", [])) >= 1
            or len(llm_profile.get("skills", [])) >= 10
            or len(llm_profile.get("about", "")) >= 200
        ))
    )

    if has_exceptional_data:
        logger.info(f"✅ Step 1 found exceptional profile data - returning early (text_llm)")
        return {
            "name": llm_profile.get("name") or name_hint or "LinkedIn Profile",
            "title": llm_profile.get("title") or "",
            "company": llm_profile.get("company") or "",
            "location": llm_profile.get("location") or "",
            "about": llm_profile.get("about") or "",
            "experience": llm_profile.get("experience", [])[:3],
            "education": llm_profile.get("education", [])[:2],
            "skills": llm_profile.get("skills", [])[:10],
            "url": url,
            "headline": llm_profile.get("headline") or llm_profile.get("title") or "",
            "industry": llm_profile.get("industry") or "",
            "connections": llm_profile.get("connections") or "",
            "extracted_keywords": llm_profile.get("skills", [])[:10],
            "scraping_method": "text_llm",
        }

    # Proceed to enrichment pipeline with Google CSE/DuckDuckGo search + LLM matching + doc fetch
    # This provides better data quality and cross-source verification
    logger.info(f"🔍 Step 1 data insufficient - activating Google CSE/DuckDuckGo enrichment pipeline")

    # Step 2: Minimal web search for candidates
    buckets = _web_search_candidates(name_hint, position, company, url, max_total=6)
    candidates = buckets.get("candidates", [])
    extra = buckets.get("extra", [])

    # Step 3: LLM choose the best candidate
    idx = _llm_choose_candidate(url, candidates, name_hint, position, company)
    chosen_url = candidates[idx - 1]["href"] if (idx > 0 and idx <= len(candidates)) else None

    # Step 4: Fetch documents from NON-LinkedIn sources for rich profile data
    # LinkedIn URLs work for LLM matching, but fail to scrape (999 error with no content)
    # Instead, fetch from GitHub, personal sites, Medium, etc. found in search results
    doc_urls: List[str] = []

    # Prioritize non-LinkedIn sources from all search results
    all_results = candidates + extra
    for r in all_results:
        h = r.get("href") or ""
        if not h:
            continue
        # Skip LinkedIn URLs - they can't be scraped (999 error)
        if "linkedin.com/" in h.lower():
            logger.debug(f"  Skipping LinkedIn URL for document fetch: {h}")
            continue
        doc_urls.append(h)
        if len(doc_urls) >= 3:
            break

    docs = _fetch_docs(doc_urls)
    profile = _llm_profile_from_docs(docs, name_hint, position, company, url) if docs else None

    if profile:
        profile.setdefault("name", name_hint or "")
        profile.setdefault("skills", [])
        profile.setdefault("experience", [])
        profile.setdefault("education", [])
        profile.setdefault("headline", profile.get("title", ""))
        profile.setdefault("industry", "")
        profile.setdefault("connections", "")
        profile.setdefault("about", "")
        profile["url"] = url
        profile["extracted_keywords"] = profile.get("skills", [])[:10]
        profile["scraping_method"] = "multi_source_llm"
        return profile

    # Final fallback: Use UI hints if provided, otherwise minimal search-based enrichment
    fallback_name = name_hint or parse_linkedin_slug(url)

    # If we have strong hints from UI, use them directly (Google-quality UX: trust user input)
    if name_hint and (position or company):
        logger.info(f"Using UI hints as primary source: {name_hint}, {position or ''}, {company or ''}")
        return {
            "name": name_hint,
            "title": position or "",
            "company": company or "",
            "location": "",
            "about": "",
            "experience": [],
            "education": [],
            "skills": [],
            "url": url,
            "headline": position or "",
            "industry": "",
            "connections": "",
            "extracted_keywords": [],
            "scraping_method": "ui_hints_primary",
        }

    # Otherwise try DDG search as final fallback
    signals = duckduckgo_signals(fallback_name or url, max_n=5)
    enriched = build_profile_from_signals(signals, fallback_name)
    return {
        "name": enriched.get("name") or fallback_name or "LinkedIn Profile",
        "title": enriched.get("headline") or "",
        "company": enriched.get("company") or "",
        "location": enriched.get("location") or "",
        "about": "",
        "experience": [],
        "education": [],
        "skills": [],
        "url": url,
        "headline": enriched.get("headline") or "",
        "industry": "",
        "connections": "",
        "extracted_keywords": [],
        "scraping_method": "search_fallback",
    }


def _llm_profile_from_context(context: str, title: str = "") -> Optional[Dict[str, Any]]:
    """Use LLM to extract a LinkedIn-like profile from page context."""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        client = OpenAI(api_key=api_key)
        prompt = (
            "Extract the following fields as a compact JSON object for a person's professional profile. "
            "Fields: name, headline, title, company, location, about, skills (array up to 10), "
            "experience (array of up to 3 objects with title, company, start_date, end_date, description), "
            "education (array up to 2 with institution, degree), industry, connections. "
            "If unknown, use empty string or empty array. Return ONLY valid JSON."
        )
        messages = [
            {"role": "system", "content": "You are a precise information extractor."},
            {"role": "user", "content": f"Title: {title}\n\nContext:\n{context}"}
        ]
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
            max_tokens=700,
            response_format={"type": "json_object"}
        )
        text = (resp.choices[0].message.content or "").strip()
        return json.loads(text)
    except Exception:
        return None
