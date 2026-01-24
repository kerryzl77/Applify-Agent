import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import trafilatura
from openai import OpenAI
import json
import re
import os
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import logging
import sys

# Add app directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.universal_extractor import extract_url, extract_linkedin_profile
from app.utils.text import normalize_job_data, normalize_text
from app.search.openai_web_search import openai_web_search

# Load environment variables
load_dotenv()

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

HTTP_SESSION = requests.Session()
HTTP_RETRY = Retry(
    total=3,
    backoff_factor=0.6,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=("GET",),
    raise_on_status=False,
)
HTTP_ADAPTER = HTTPAdapter(max_retries=HTTP_RETRY)
HTTP_SESSION.mount("https://", HTTP_ADAPTER)
HTTP_SESSION.mount("http://", HTTP_ADAPTER)


def _fetch_html(url: str, timeout: int = 20) -> str:
    try:
        resp = HTTP_SESSION.get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
        return resp.text or ""
    except Exception as exc:
        print(f"Error fetching HTML for {url}: {exc}")
    return ""


def _extract_text_from_html_fragment(html_fragment: str) -> str:
    if not html_fragment:
        return ""
    wrapped = f"<html><body>{html_fragment}</body></html>"
    text = trafilatura.extract(
        wrapped,
        include_comments=False,
        include_tables=True,
    )
    return (text or "").strip()


def fetch_clean_text(url: str, timeout: int = 20) -> str:
    """Fetch HTML and extract main text using trafilatura."""
    try:
        html = _fetch_html(url, timeout=timeout)
        if not html:
            return ""
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
        )
        return (text or "").strip()
    except Exception as exc:
        print(f"Error fetching HTML for {url}: {exc}")
        return ""


def _is_greenhouse_url(url: str) -> bool:
    parsed = urlparse(url)
    params = parse_qs(parsed.query or "")
    return "greenhouse.io" in parsed.netloc.lower() or "gh_jid" in params


def _extract_greenhouse_ids_from_url(url: str) -> tuple[str | None, str | None]:
    parsed = urlparse(url)
    params = parse_qs(parsed.query or "")
    job_id = params.get("gh_jid", [None])[0] or params.get("token", [None])[0]
    board_token = params.get("for", [None])[0]

    host = parsed.netloc.lower()
    parts = [p for p in parsed.path.split("/") if p]
    if host in ("boards.greenhouse.io", "job-boards.greenhouse.io"):
        if parts and parts[0] not in ("embed",):
            board_token = board_token or parts[0]
        if len(parts) >= 3 and parts[1] == "jobs":
            job_id = job_id or parts[2]

    return board_token, job_id


def _extract_greenhouse_ids_from_html(html: str) -> tuple[str | None, str | None]:
    patterns = [
        r"https?://boards\.greenhouse\.io/([^/\"'?#]+)/jobs/(\d+)",
        r"https?://job-boards\.greenhouse\.io/([^/\"'?#]+)/jobs/(\d+)",
        r"https?://boards\.greenhouse\.io/embed/job_app\?for=([^&\"']+)&token=(\d+)",
        r"https?://job-boards\.greenhouse\.io/embed/job_app\?for=([^&\"']+)&token=(\d+)",
    ]
    for pat in patterns:
        match = re.search(pat, html, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2)
    return None, None


def _find_greenhouse_board_token(url: str, job_id: str | None, company_name: str | None) -> str | None:
    if not os.getenv("OPENAI_API_KEY"):
        return None

    host_hint = urlparse(url).netloc.replace("www.", "").strip()
    company_hint = (company_name or "").strip()
    if not company_hint and host_hint:
        company_hint = host_hint.split(".")[0].replace("-", " ")

    query_parts = [p for p in [company_hint, job_id] if p]
    if not query_parts:
        return None
    query = " ".join(query_parts) + " site:boards.greenhouse.io OR site:job-boards.greenhouse.io"

    results = openai_web_search(query, num_results=5)
    for r in results:
        token, found_id = _extract_greenhouse_ids_from_url(r.get("url", ""))
        if token and (not job_id or not found_id or found_id == job_id):
            return token
    return None


def _fetch_greenhouse_job_text(url: str, company_name: str | None) -> dict | None:
    if not _is_greenhouse_url(url):
        return None

    board_token, job_id = _extract_greenhouse_ids_from_url(url)

    if not board_token or not job_id:
        html = _fetch_html(url)
        if html:
            html_token, html_job_id = _extract_greenhouse_ids_from_html(html)
            board_token = board_token or html_token
            job_id = job_id or html_job_id

    if job_id and not board_token:
        board_token = _find_greenhouse_board_token(url, job_id, company_name)

    if not board_token or not job_id:
        return None

    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"
    try:
        resp = HTTP_SESSION.get(api_url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=20)
        if resp.status_code != 200:
            print(f"Greenhouse API error {resp.status_code} for {api_url}")
            return None
        data = resp.json()
    except Exception as exc:
        print(f"Greenhouse API fetch failed: {exc}")
        return None

    title = (data.get("title") or "").strip()
    loc = data.get("location")
    location = ""
    if isinstance(loc, dict):
        location = (loc.get("name") or "").strip()
    elif isinstance(loc, str):
        location = loc.strip()

    content_html = data.get("content") or ""
    content_text = _extract_text_from_html_fragment(content_html)
    text_content = "\n\n".join([p for p in [title, location, content_text] if p]).strip()

    if not text_content:
        return None

    return {
        "text": text_content,
        "job_title": title or None,
        "location": location or None,
        "company_name": company_name or None,
        "source": "greenhouse_api",
    }


def _is_ashby_url(url: str) -> bool:
    parsed = urlparse(url)
    params = parse_qs(parsed.query or "")
    return "ashbyhq.com" in parsed.netloc.lower() or "ashby_jid" in params or "ashby_job_id" in params


def _extract_ashby_ids_from_url(url: str) -> tuple[str | None, str | None]:
    parsed = urlparse(url)
    board = None
    job_slug = None

    if "ashbyhq.com" in parsed.netloc.lower():
        parts = [p for p in parsed.path.split("/") if p]
        board = parts[0] if parts else None
        job_slug = parts[1] if len(parts) > 1 else None

    params = parse_qs(parsed.query or "")
    job_slug = params.get("ashby_job_id", [job_slug])[0]
    job_slug = params.get("ashby_jid", [job_slug])[0]

    return board, job_slug


def _find_ashby_board(url: str, company_name: str | None) -> str | None:
    if not os.getenv("OPENAI_API_KEY"):
        return None

    host_hint = urlparse(url).netloc.replace("www.", "").strip()
    company_hint = (company_name or "").strip()
    if not company_hint and host_hint:
        company_hint = host_hint.split(".")[0].replace("-", " ")

    if not company_hint:
        return None

    results = openai_web_search(
        f"{company_hint} site:jobs.ashbyhq.com",
        num_results=5,
    )
    for r in results:
        parsed = urlparse(r.get("url", ""))
        if "ashbyhq.com" in parsed.netloc.lower():
            parts = [p for p in parsed.path.split("/") if p]
            if parts:
                return parts[0]
    return None


def _match_ashby_job(jobs: list, job_slug: str | None, url: str, job_title: str | None) -> dict | None:
    slug = (job_slug or "").strip().lower()
    url_lower = (url or "").strip().lower()

    if slug:
        for j in jobs:
            for key in ("id", "jobId", "slug", "shortcode"):
                val = str(j.get(key, "")).strip().lower()
                if val and val == slug:
                    return j
            for key in ("url", "applyUrl", "externalLink", "jobUrl", "postingUrl"):
                link = str(j.get(key, "")).strip().lower()
                if link and (link == url_lower or slug in link):
                    return j

    if job_title:
        title_matches = [
            j for j in jobs
            if str(j.get("title", "")).strip().lower() == job_title.strip().lower()
        ]
        if len(title_matches) == 1:
            return title_matches[0]

    return None


def _fetch_ashby_job_text(url: str, job_title: str | None, company_name: str | None) -> dict | None:
    if not _is_ashby_url(url):
        return None

    board, job_slug = _extract_ashby_ids_from_url(url)
    if not board:
        board = _find_ashby_board(url, company_name)

    if not board:
        return None

    api_url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
    try:
        resp = HTTP_SESSION.get(api_url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=20)
        if resp.status_code != 200:
            print(f"Ashby API error {resp.status_code} for {api_url}")
            return None
        data = resp.json()
    except Exception as exc:
        print(f"Ashby API fetch failed: {exc}")
        return None

    jobs = data.get("jobs") or data.get("jobPostings") or data.get("postings") or []
    if not isinstance(jobs, list) or not jobs:
        return None

    job = _match_ashby_job(jobs, job_slug, url, job_title)
    if not job:
        return None

    title = (job.get("title") or "").strip()
    loc = job.get("location")
    location = ""
    if isinstance(loc, dict):
        location = (loc.get("name") or "").strip()
    elif isinstance(loc, list):
        location = ", ".join([str(x.get("name", "")).strip() for x in loc if isinstance(x, dict)])
    elif isinstance(loc, str):
        location = loc.strip()

    content_text = (job.get("descriptionPlainText") or "").strip()
    if not content_text:
        html = job.get("descriptionHtml") or job.get("content") or ""
        content_text = _extract_text_from_html_fragment(html)

    text_content = "\n\n".join([p for p in [title, location, content_text] if p]).strip()
    if not text_content:
        return None

    return {
        "text": text_content,
        "job_title": title or None,
        "location": location or None,
        "company_name": (data.get("companyName") or data.get("jobBoardName") or company_name or None),
        "source": "ashby_api",
    }


def _is_workday_url(url: str) -> bool:
    parsed = urlparse(url)
    return "myworkdayjobs.com" in parsed.netloc.lower()


def _extract_workday_parts(url: str) -> tuple[str | None, str | None, str | None]:
    parsed = urlparse(url)
    host = parsed.netloc
    if not host:
        return None, None, None

    tenant = host.split(".")[0] if "myworkdayjobs.com" in host else None
    parts = [p for p in parsed.path.split("/") if p]
    if parts and re.match(r"^[a-z]{2}-[a-z]{2}$", parts[0], re.IGNORECASE):
        parts = parts[1:]

    if not parts:
        return tenant, None, None

    site = parts[0] if len(parts) >= 1 else None
    job_slug = None
    for marker in ("details", "job", "jobs"):
        if marker in parts:
            idx = parts.index(marker)
            if len(parts) > idx + 1:
                job_slug = parts[idx + 1]
                break
    if not job_slug and len(parts) >= 2:
        job_slug = parts[-1]

    return tenant, site, job_slug


def _normalize_workday_location(value) -> str:
    if isinstance(value, dict):
        for key in ("displayName", "descriptor", "name", "location"):
            candidate = value.get(key)
            if candidate:
                return str(candidate).strip()
        return ""
    if isinstance(value, list):
        parts = [p for p in (_normalize_workday_location(v) for v in value) if p]
        return ", ".join(parts)
    if isinstance(value, str):
        return value.strip()
    return ""


def _fetch_workday_job_text(url: str, company_name: str | None) -> dict | None:
    if not _is_workday_url(url):
        return None

    parsed = urlparse(url)
    tenant, site, job_slug = _extract_workday_parts(url)
    if not tenant or not site or not job_slug:
        return None

    api_url = f"{parsed.scheme or 'https'}://{parsed.netloc}/wday/cxs/{tenant}/{site}/{job_slug}"
    try:
        resp = HTTP_SESSION.get(
            api_url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=20,
        )
        if resp.status_code != 200:
            print(f"Workday API error {resp.status_code} for {api_url}")
            return None
        data = resp.json()
    except Exception as exc:
        print(f"Workday API fetch failed: {exc}")
        return None

    posting = data.get("jobPostingInfo") or data.get("jobPosting") or data.get("job_posting") or {}
    if isinstance(posting, list):
        posting = posting[0] if posting else {}

    title = (posting.get("jobTitle") or posting.get("title") or data.get("jobTitle") or data.get("title") or "").strip()
    location = _normalize_workday_location(
        posting.get("location")
        or posting.get("jobLocation")
        or posting.get("primaryLocation")
        or data.get("location")
    )

    desc_html = (
        posting.get("jobDescription")
        or posting.get("jobDescriptionHtml")
        or posting.get("description")
        or data.get("jobDescription")
        or data.get("description")
    )
    req_html = (
        posting.get("jobQualifications")
        or posting.get("jobRequirements")
        or posting.get("requirements")
        or data.get("requirements")
    )

    description_text = _extract_text_from_html_fragment(desc_html) if desc_html else ""
    requirements_text = _extract_text_from_html_fragment(req_html) if req_html else ""
    text_content = "\n\n".join(
        [p for p in [title, location, description_text, requirements_text] if p]
    ).strip()

    if not text_content:
        return None

    return {
        "text": text_content,
        "job_title": title or None,
        "location": location or None,
        "company_name": company_name or tenant or None,
        "source": "workday_api",
    }


def _build_job_search_query(url: str, job_title: str | None, company_name: str | None) -> str:
    parts = []
    if company_name:
        parts.append(company_name)
    if job_title:
        parts.append(job_title)
    parsed = urlparse(url)
    if parsed.netloc:
        parts.append(parsed.netloc)
    params = parse_qs(parsed.query or "")
    if params.get("gh_jid"):
        parts.append(params["gh_jid"][0])
        parts.append("site:boards.greenhouse.io OR site:job-boards.greenhouse.io")
    if not parts:
        return url
    return " ".join(parts) + " job description"


def _should_relax_search_domain(url: str) -> bool:
    """Avoid restricting search domains for ATS pointers."""
    return _is_greenhouse_url(url) or _is_ashby_url(url) or _is_workday_url(url)


def search_job_posting_text(
    url: str,
    job_title: str | None,
    company_name: str | None,
    min_chars: int = 200,
) -> str:
    """Try to find an alternate job posting source via web search."""
    if not os.getenv("OPENAI_API_KEY"):
        return ""

    parsed = urlparse(url)
    query = _build_job_search_query(url, job_title, company_name)
    allowed = [parsed.netloc] if parsed.netloc else None
    if _should_relax_search_domain(url):
        allowed = None

    results = openai_web_search(query, num_results=4, allowed_domains=allowed)
    if not results and parsed.netloc:
        results = openai_web_search(f"{query} {parsed.netloc}", num_results=4)

    for r in results:
        candidate_url = (r.get("url") or "").strip()
        if not candidate_url:
            continue
        candidate_text = fetch_clean_text(candidate_url)
        if candidate_text and len(candidate_text) >= min_chars:
            return candidate_text

    snippets = [r.get("snippet", "").strip() for r in results if r.get("snippet")]
    return "\n".join(s for s in snippets if s).strip()

class DataRetriever:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Text-first extractor for LinkedIn profiles
        
    def scrape_job_posting(self, url, job_title=None, company_name=None):
        """Scrape job posting details from a given URL using direct HTTP + local extraction."""
        try:
            text_content = ""

            ats_result = (
                _fetch_greenhouse_job_text(url, company_name)
                or _fetch_ashby_job_text(url, job_title, company_name)
                or _fetch_workday_job_text(url, company_name)
            )
            if ats_result:
                text_content = ats_result.get("text", "")
                if not job_title and ats_result.get("job_title"):
                    job_title = ats_result["job_title"]
                if not company_name and ats_result.get("company_name"):
                    company_name = ats_result["company_name"]
            force_search = _should_relax_search_domain(url) and not ats_result

            if not text_content:
                text_content = fetch_clean_text(url)

            if text_content and "job description is loading or not available" in text_content.lower():
                text_content = ""

            # Fallback to alternate extraction if content is empty/short
            if not text_content or len(text_content.strip()) < 200:
                fallback = extract_url(url)
                fallback_text = normalize_text(fallback.get("text")).strip()
                if fallback_text and len(fallback_text) > len(text_content.strip()):
                    text_content = fallback_text

            # Secondary fallback: use OpenAI web search to find an alternate source
            if force_search or not text_content or len(text_content.strip()) < 200:
                search_text = search_job_posting_text(url, job_title, company_name, min_chars=200)
                if search_text and (force_search or len(search_text) > len(text_content.strip())):
                    text_content = search_text

            text_content = normalize_text(text_content).strip()

            if not text_content:
                return {'error': "No content found from page extraction"}
            
            # Use GPT to extract structured information from the content
            extracted_data = self._extract_job_data_with_gpt(text_content, url, job_title, company_name)
            
            # Print confirmation with key info
            print(f"Scraped job posting: {extracted_data['company_name']} - {extracted_data['job_title']} - {extracted_data['location']}")
            
            return extracted_data
        except Exception as e:
            print(f"Error scraping job posting: {str(e)}")
            return {'error': str(e)}
    
    def scrape_linkedin_profile(self, url, name=None, position=None, company=None, job_title=None, company_name=None):
        """Scrape LinkedIn profile using text-first extraction with search fallback.

        Args:
            url: LinkedIn profile URL
            name: Person's name (UI hint for better matching)
            position: Person's position/title (UI hint for better matching)
            company: Person's company (UI hint for better matching)
            job_title: (Legacy) Job title context
            company_name: (Legacy) Company name context
        """
        try:
            print(f"🔄 Extracting LinkedIn profile: {url}")
            if name or position or company:
                print(f"📝 Using UI hints - Name: {name}, Position: {position}, Company: {company}")

            # Pass hints to universal extractor for better candidate matching
            profile_data = extract_linkedin_profile(url, name=name, position=position, company=company)
            
            if not profile_data or not profile_data.get('name'):
                print(f"❌ LinkedIn extraction failed for {url}")
                return self._get_fallback_profile_data(url)
            
            # Convert to format expected by rest of application
            extracted_data = {
                'name': profile_data.get('name') or "Unknown Name",
                'title': profile_data.get('title') or "Unknown Title",
                'company': profile_data.get('company') or "Unknown Company", 
                'location': profile_data.get('location') or "Unknown Location",
                'about': profile_data.get('about') or "",
                'experience': profile_data.get('experience', [])[:3],
                'education': profile_data.get('education', [])[:2],
                'skills': profile_data.get('skills', [])[:10],
                'url': url,
                'headline': profile_data.get('headline') or "",
                'industry': profile_data.get('industry') or "",
                'connections': profile_data.get('connections') or "",
                'extracted_keywords': profile_data.get('extracted_keywords', []),
                'scraping_method': profile_data.get('scraping_method', 'text_first')
            }
            
            # Get job-relevant context if job info provided
            if job_title or company_name:
                # Minimal personalization keywords based on title/company tokens
                tokens = re.findall(r"[A-Za-z0-9]+", f"{job_title or ''} {company_name or ''}")
                extracted_data['personalization_keywords'] = tokens[:10]
            
            print(f"✅ Successfully scraped LinkedIn profile: {extracted_data['name']} - {extracted_data['title']} at {extracted_data['company']}")
            
            return extracted_data
            
        except Exception as e:
            print(f"❌ Error in LinkedIn profile extraction: {str(e)}")
            logging.error(f"LinkedIn scraping error for {url}: {str(e)}")
            return self._get_fallback_profile_data(url, str(e))
    
    def _get_fallback_profile_data(self, url, error_msg="Scraping failed"):
        """Return fallback profile data when scraping fails."""
        return {
            'name': "LinkedIn Profile",
            'title': "Professional", 
            'company': "Company",
            'location': "Location",
            'about': "Professional with experience in the industry.",
            'experience': [],
            'education': [],
            'skills': [],
            'url': url,
            'headline': "",
            'industry': "",
            'connections': "",
            'extracted_keywords': [],
            'error': error_msg,
            'scraping_method': 'fallback'
        }
    
    def parse_manual_job_posting(self, text, job_title=None, company_name=None):
        """Parse job posting details from manually entered text."""
        try:
            # Use GPT to extract structured information from the content
            extracted_data = self._extract_job_data_with_gpt(text, None, job_title, company_name)
            
            # Print confirmation with key info
            print(f"Parsed job posting: {extracted_data['company_name']} - {extracted_data['job_title']}")
            
            return extracted_data
            
        except Exception as e:
            print(f"Error parsing manual job posting: {str(e)}")
            return {'error': str(e)}
            
    def parse_manual_linkedin_profile(self, text, job_title=None, company_name=None):
        """Parse LinkedIn profile details from manually entered text."""
        try:
            # Use GPT to extract structured information from the content
            extracted_data = self._extract_profile_data_with_gpt(text, None, job_title, company_name)
            
            # Print confirmation with key info
            print(f"Parsed LinkedIn profile: {extracted_data['name']} - {extracted_data['title']} at {extracted_data['company']}")
            
            return extracted_data
            
        except Exception as e:
            print(f"Error parsing manual LinkedIn profile: {str(e)}")
            return {'error': str(e)}
    
    def _extract_job_data_with_gpt(self, content_text, url, job_title=None, company_name=None):
        """Use GPT to extract structured job posting data from text content."""
        try:
            # Create prompt for GPT-5
            prompt = f"""Extract key information from this job posting. Return ONLY a valid JSON object with these fields:
            - job_title: The title of the position
            - company_name: The company offering the position
            - job_description: A summary of the main responsibilities and role
            - requirements: Key qualifications and requirements
            - location: Job location (including remote/hybrid if specified)

            Job Posting Content:
            {content_text[:8000]}  # Limit content length to avoid token limits
            """
            
            # Add user-provided information to the prompt if available
            if job_title:
                prompt += f"\n\nUser-provided job title: {job_title}"
            if company_name:
                prompt += f"\nUser-provided company name: {company_name}"
            
            prompt += "\n\nReturn ONLY a valid JSON object. Do not include any other text or explanation.\nIf a field is not found, use null or an empty string as appropriate."

            response = self.client.chat.completions.create(
                model="gpt-5.2",
                messages=[
                    {"role": "system", "content": "You are a precise job posting parser. Your response must be a valid JSON object containing only the requested fields. Do not include any explanatory text or markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3  # Lower temperature for more consistent output
            )

            # Parse the response
            try:
                response_text = response.choices[0].message.content.strip()
                response_text = re.sub(r'```json\s*', '', response_text)
                response_text = re.sub(r'```\s*$', '', response_text)
                parsed_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"Error parsing GPT response as JSON: {str(e)}")
                print(f"Raw response: {response.choices[0].message.content}")
                raise
            
            invalid_details = {
                "",
                "n/a",
                "na",
                "none",
                "null",
                "not available",
                "not provided",
                "unknown",
                "no job description found",
                "no specific requirements found",
                "nah",
            }

            def _clean_detail(value):
                text = normalize_text(value).strip()
                if not text:
                    return ""
                if text.lower() in invalid_details:
                    return ""
                return text

            # Format the results to match existing structure
            job_data = {
                'job_title': normalize_text(parsed_data.get('job_title') or job_title or "Unknown Job Title"),
                'company_name': normalize_text(parsed_data.get('company_name') or company_name or "Unknown Company"),
                'job_description': _clean_detail(parsed_data.get('job_description')),
                'requirements': _clean_detail(parsed_data.get('requirements')),
                'location': normalize_text(parsed_data.get('location') or "Unknown Location"),
                'url': url
            }

            fallback_text = normalize_text(content_text).strip()
            if fallback_text and not job_data.get("job_description") and not job_data.get("requirements"):
                # Fallback to raw text when extraction is empty.
                job_data["job_description"] = fallback_text[:8000]

            return normalize_job_data(job_data)
            
        except Exception as e:
            print(f"Error extracting job data with GPT: {str(e)}")
            return {
                'job_title': job_title or "Unknown Job Title",
                'company_name': company_name or "Unknown Company",
                'job_description': "Error extracting job description",
                'requirements': "Error extracting requirements",
                'location': "Unknown Location",
                'url': url,
                'error': str(e)
            }

    def _extract_profile_data_with_gpt(self, content_text, url, job_title=None, company_name=None):
        """Use GPT to extract structured LinkedIn profile data from text content."""
        try:
            # Create prompt for GPT-5
            prompt = f"""Extract key information from this LinkedIn profile. Return a JSON object with these fields:
            - name: The person's full name
            - title: Their current job title/role
            - company: Their current company
            - location: Where they are based
            - about: Their about section or summary (if available)
            - experience: A list of their most recent experiences (up to 3) with:
              - title: Job title
              - company: Company name
              - duration: Time period (if available)
              - location: Location (if available)
              - description: Brief description of role (if available)
            - education: A list of their education with:
              - school: Institution name
              - degree: Degree name
              - years: Time period (if available)
            - skills: List of key skills mentioned

            Profile Content:
            {content_text[:8000]}  # Limit content length to avoid token limits
            """
            
            # Add user-provided information to the prompt if available
            if job_title:
                prompt += f"\n\nUser-provided job title: {job_title}"
            if company_name:
                prompt += f"\nUser-provided company name: {company_name}"
            
            prompt += "\n\nReturn ONLY a valid JSON object with these fields. Do not include any other text or explanation.\nIf a field is not found, use null or an empty string as appropriate."

            response = self.client.chat.completions.create(
                model="gpt-5.2",
                messages=[
                    {"role": "system", "content": "You are a precise LinkedIn profile parser. Extract only the requested information and format it as a valid JSON object. Do not include any explanatory text or markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3  # Lower temperature for more consistent output
            )

            # Parse the response
            try:
                # Clean the response to ensure it's valid JSON
                response_text = response.choices[0].message.content.strip()
                # Remove any markdown code block markers
                response_text = re.sub(r'```json\s*', '', response_text)
                response_text = re.sub(r'```\s*$', '', response_text)
                
                parsed_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"Error parsing GPT response as JSON: {str(e)}")
                print(f"Raw response: {response_text}")
                raise
            
            # Validate and format the results
            profile_data = {
                'name': parsed_data.get('name', "Unknown Name"),
                'title': parsed_data.get('title', job_title or "Unknown Title"),
                'company': parsed_data.get('company', company_name or "Unknown Company"),
                'location': parsed_data.get('location', "Unknown Location"),
                'about': parsed_data.get('about', ""),
                'experience': parsed_data.get('experience', []),
                'education': parsed_data.get('education', []),
                'skills': parsed_data.get('skills', []),
                'url': url
            }
            
            return profile_data
            
        except Exception as e:
            print(f"Error extracting profile data with GPT: {str(e)}")
            return {
                'name': "Unknown Name",
                'title': job_title or "Unknown Title",
                'company': company_name or "Unknown Company",
                'location': "Unknown Location",
                'about': "",
                'experience': [],
                'education': [],
                'skills': [],
                'url': url,
                'error': str(e)
            }