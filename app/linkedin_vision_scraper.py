"""
LinkedIn Profile Scraper - Vision API Approach
==============================================

PRODUCTION-READY LinkedIn scraper using Playwright + GPT-4 Vision.

Simple, clean approach:
1. Navigate to LinkedIn profile with Playwright
2. Close any sign-in popups
3. Scroll to load content
4. Take full-page screenshot
5. Send to GPT-4 Vision API to extract structured data

No DOM parsing, no fighting with selectors. Just works.
"""

import os
import re
import time
import base64
import logging
import tempfile
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
from openai import OpenAI
from app.redis_manager import RedisManager
from io import BytesIO
from PIL import Image
import hashlib
import random

try:
    from playwright_stealth import stealth_sync  # type: ignore
except Exception:  # pragma: no cover
    def stealth_sync(page: Page):  # type: ignore
        return None

@dataclass
class LinkedInProfile:
    """Structured LinkedIn profile data."""
    name: str = ""
    headline: str = ""
    location: str = ""
    about: str = ""
    current_company: str = ""
    current_position: str = ""
    experience: List[Dict] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    education: List[Dict] = field(default_factory=list)
    connections: str = ""
    profile_url: str = ""
    extracted_keywords: List[str] = field(default_factory=list)
    industry: str = ""


class LinkedInVisionScraper:
    """
    Production-ready LinkedIn scraper using Playwright + GPT-4 Vision.
    
    This is the simplest and most reliable approach:
    - Use Playwright to navigate and screenshot
    - Use GPT-4 Vision to extract structured data from the image
    - No DOM parsing, no brittle selectors
    """

    def __init__(self, api_key: str = None, redis_manager: Optional[RedisManager] = None):
        """Initialize the scraper with OpenAI API key and optional Redis for session persistence."""
        self.logger = logging.getLogger(__name__)
        self.openai_client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.last_request_time = 0
        self.min_request_interval = 3.0  # 3 seconds between requests
        self.session_dir = "./playwright-data"
        self.session_file = os.path.join(self.session_dir, "linkedin_session.json")
        self.redis = redis_manager or RedisManager()
        self.linkedin_email = os.getenv("LINKEDIN_EMAIL", "public")
        self._session_redis_key = self._make_session_key(self.linkedin_email)

    def extract_profile_data(self, linkedin_url: str) -> Optional[LinkedInProfile]:
        """
        Extract LinkedIn profile data using Playwright + GPT-4 Vision.
        
        Args:
            linkedin_url: LinkedIn profile URL (e.g., https://www.linkedin.com/in/username/)
            
        Returns:
            LinkedInProfile object with extracted data, or None if extraction fails
        """
        try:
            # Validate and clean URL
            if not self._is_valid_linkedin_url(linkedin_url):
                self.logger.error(f"❌ Invalid LinkedIn URL: {linkedin_url}")
                return None

            clean_url = self._clean_linkedin_url(linkedin_url)
            self._respect_rate_limit()

            self.logger.info(f"🔄 Extracting profile: {clean_url}")

            # Step 1: Navigate and screenshot(s)
            screenshot_paths = self._capture_profile_screenshots(clean_url)
            if not screenshot_paths:
                self.logger.error("❌ Failed to capture screenshot")
                return None

            self.logger.info(f"📸 Captured {len(screenshot_paths)} screenshot segment(s)")

            # Step 2: Extract data using GPT-4 Vision
            profile = self._extract_with_vision_api(screenshot_paths, clean_url)
            
            # Cleanup screenshot
            try:
                for p in screenshot_paths:
                    try:
                        os.remove(p)
                    except Exception:
                        pass
            except:
                pass

            if profile and profile.name:
                self.logger.info(f"✅ Successfully extracted: {profile.name}")
                return profile
            else:
                self.logger.warning("⚠️  Failed to extract profile data")
                return self._create_fallback_profile(clean_url)

        except Exception as e:
            self.logger.error(f"❌ Error extracting profile: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _capture_profile_screenshots(self, url: str) -> Optional[List[str]]:
        """
        Navigate to LinkedIn profile and capture segmented, compressed screenshots to minimize memory.

        Handles:
        - Browser launch with persistent session
        - LinkedIn login if needed
        - Navigation
        - Content scrolling
        - Segmented viewport screenshots (JPEG, compressed)
        """
        try:
            with sync_playwright() as p:
                # Launch browser with stealth settings
                self.logger.info("🚀 Launching browser with stealth mode...")
                browser = p.chromium.launch(
                    headless=os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true",
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-gpu'
                    ]
                )

                # Load or create session with stealth settings
                context = self._load_or_create_session(browser)
                page = context.new_page()
                page.set_default_timeout(30000)  # Increased timeout

                # Apply stealth JS shims when available
                try:
                    stealth_sync(page)
                except Exception:
                    pass

                # Set realistic user agent
                page.set_extra_http_headers({
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Referer': 'https://www.google.com/'
                })

                # Navigate to profile with retry logic
                self.logger.info(f"🌐 Navigating to {url}...")
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        time.sleep(2.0 + random.uniform(0.2, 0.8))  # Let page settle
                        break
                    except Exception as nav_error:
                        if attempt < max_retries - 1:
                            self.logger.warning(f"⚠️ Navigation attempt {attempt + 1} failed, retrying... ({nav_error})")
                            time.sleep(2)
                        else:
                            raise
                
                # Check if login is required
                if self._is_login_required(page):
                    self.logger.info("🔐 Login required, authenticating...")
                    if self._login_to_linkedin(page):
                        # Navigate to profile again after login with retry
                        self.logger.info(f"🔄 Re-navigating to profile after login...")
                        for attempt in range(3):
                            try:
                                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                                time.sleep(1.5 + random.uniform(0.1, 0.4))
                                break
                            except Exception as nav_error:
                                if attempt < 2:
                                    self.logger.warning(f"⚠️ Post-login navigation attempt {attempt + 1} failed, retrying...")
                                    time.sleep(2)
                                else:
                                    self.logger.error(f"❌ Failed to navigate after login: {nav_error}")
                                    raise
                        # Save session
                        self._save_session(context)
                    else:
                        self.logger.warning("⚠️  Login failed, continuing with public view")
                
                # Close sign-in popup if present
                self._close_signin_popup(page)
                
                # Scroll to load all content
                self.logger.info("📜 Scrolling to load content...")
                self._scroll_page(page)
                
                # Capture segmented screenshots to limit memory pressure
                segments = self._capture_segmented_screenshots(page, max_segments=5)

                context.close()
                browser.close()
                return segments

        except Exception as e:
            self.logger.error(f"❌ Screenshot capture failed: {str(e)}")
            return None

    def _load_or_create_session(self, browser):
        """Load existing session or create new context with stealth settings."""
        # Stealth context options
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'locale': 'en-US',
            'timezone_id': 'America/Los_Angeles',
            'permissions': [],
            'geolocation': None,
            'color_scheme': 'light',
            'java_script_enabled': True,
        }

        try:
            # Load from Redis if available
            if self.redis and self.redis.is_available():
                state = self.redis.get(self._session_redis_key)
                if state:
                    self.logger.info("📂 Loading LinkedIn session from Redis")
                    context_options['storage_state'] = state
                    return browser.new_context(**context_options)
            if os.path.exists(self.session_file):
                self.logger.info("📂 Loading existing LinkedIn session...")
                context_options['storage_state'] = self.session_file
                return browser.new_context(**context_options)
        except Exception as e:
            self.logger.debug(f"Could not load session: {e}")

        self.logger.info("🆕 Creating new browser session with stealth settings")
        return browser.new_context(**context_options)

    def _save_session(self, context):
        """Save browser session for future use."""
        try:
            os.makedirs(self.session_dir, exist_ok=True)
            state = context.storage_state(path=self.session_file)
            self.logger.info("💾 Saved LinkedIn session to file")
            if self.redis and self.redis.is_available():
                self.redis.set(self._session_redis_key, state, ttl=7*24*3600)
                self.logger.info("💾 Saved LinkedIn session to Redis")
        except Exception as e:
            self.logger.debug(f"Could not save session: {e}")

    def _is_login_required(self, page: Page) -> bool:
        """Check if LinkedIn is requiring login."""
        try:
            # Check for login/signup prompts
            login_indicators = [
                'form.login-form',
                'input[name="session_key"]',
                'button:has-text("Sign in")',
                'a:has-text("Join now")',
            ]
            
            for selector in login_indicators:
                if page.query_selector(selector):
                    return True
            
            # Check if we see "Sign in to view" message
            if "sign in" in page.content().lower() and "view" in page.content().lower():
                return True
                
            return False
        except:
            return False

    def _login_to_linkedin(self, page: Page) -> bool:
        """Login to LinkedIn using credentials from environment."""
        try:
            email = os.getenv("LINKEDIN_EMAIL")
            password = os.getenv("LINKEDIN_PASSWORD")
            
            if not email or not password:
                self.logger.warning("⚠️  LINKEDIN_EMAIL or LINKEDIN_PASSWORD not set in .env")
                return False
            
            self.logger.info("🔐 Logging in to LinkedIn...")

            # Go to login page with retry
            for attempt in range(3):
                try:
                    page.goto("https://www.linkedin.com/login", wait_until='domcontentloaded', timeout=30000)
                    time.sleep(2)
                    break
                except Exception as nav_error:
                    if attempt < 2:
                        self.logger.warning(f"⚠️ Login page navigation attempt {attempt + 1} failed, retrying...")
                        time.sleep(2)
                    else:
                        self.logger.error(f"❌ Failed to reach login page: {nav_error}")
                        return False
            
            # Enter credentials robustly
            try:
                page.wait_for_selector('input[name="session_key"]', state='visible', timeout=15000)
                page.wait_for_selector('input[name="session_password"]', state='visible', timeout=15000)
            except Exception:
                self.logger.error("❌ Could not find login form")
                return False

            page.locator('input[name="session_key"]').fill(email)
            time.sleep(0.2 + random.uniform(0.05, 0.2))
            page.locator('input[name="session_password"]').fill(password)
            time.sleep(0.2 + random.uniform(0.05, 0.2))
            page.locator('button[type="submit"]').click()

            try:
                page.wait_for_load_state('domcontentloaded', timeout=20000)
            except Exception:
                pass

            success = False
            for _ in range(10):
                current_url = page.url
                content_lower = page.content().lower()
                if ("/feed/" in current_url) or ("/in/" in current_url and "sign in" not in content_lower):
                    success = True
                    break
                time.sleep(0.5)

            if success:
                self.logger.info("✅ Successfully logged in to LinkedIn")
                return True
            else:
                self.logger.warning("⚠️  Login may have failed - unexpected page")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ Login error: {str(e)}")
            return False

    def _close_signin_popup(self, page: Page):
        """Close LinkedIn sign-in popup if it appears."""
        try:
            # Common selectors for sign-in popup close buttons
            close_selectors = [
                'button[aria-label="Dismiss"]',
                'button[data-tracking-control-name="public_profile_contextual-sign-in-modal_modal_dismiss"]',
                '.contextual-sign-in-modal__modal-dismiss',
                'button.contextual-sign-in-modal__modal-dismiss-icon',
            ]
            
            for selector in close_selectors:
                try:
                    close_button = page.query_selector(selector)
                    if close_button:
                        close_button.click()
                        self.logger.info("✅ Closed sign-in popup")
                        time.sleep(1)
                        return
                except:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"No sign-in popup to close: {e}")

    def _scroll_page(self, page: Page):
        """Scroll page to load lazy-loaded content."""
        try:
            for _ in range(5):  # Scroll 5 times
                page.evaluate("window.scrollBy(0, 800)")
                time.sleep(0.5)
        except:
            pass

    def _extract_with_vision_api(self, screenshot_paths: List[str], url: str) -> Optional[LinkedInProfile]:
        """
        Extract LinkedIn profile data from screenshot using GPT-4 Vision API.
        
        This is the magic - let AI read the profile like a human would.
        """
        try:
            self.logger.info("🤖 Analyzing screenshot with GPT-4 Vision...")
            
            # Read and encode all screenshots
            images_base64 = []
            for path in screenshot_paths:
                with open(path, 'rb') as image_file:
                    images_base64.append(base64.b64encode(image_file.read()).decode('utf-8'))

            # Vision API prompt
            prompt = """Analyze this LinkedIn profile screenshot and extract the following information as a JSON object:

{
  "name": "Full name of the person",
  "headline": "Professional headline/tagline",
  "location": "Location/city",
  "about": "About/summary section (first 500 chars)",
  "current_position": "Current job title",
  "current_company": "Current company name",
  "connections": "Number of connections",
  "industry": "Industry/field",
  "experience": [
    {
      "title": "Job title",
      "company": "Company name",
      "start_date": "Start date",
      "end_date": "End date (or 'Present')",
      "description": "Brief description"
    }
  ],
  "skills": ["Skill 1", "Skill 2", ...],
  "education": [
    {
      "institution": "School/university name",
      "degree": "Degree name",
      "field": "Field of study",
      "graduation_year": "Year"
    }
  ]
}

Rules:
- Extract top 3 experience entries
- Extract top 10 skills
- Extract top 2 education entries
- If a field is not visible, use empty string or empty array
- Return ONLY valid JSON, no markdown or explanations"""

            # Call GPT-4 Vision API
            response = self.openai_client.chat.completions.create(
                model="gpt-5.2",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            *[
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{img}"
                                    }
                                } for img in images_base64
                            ]
                        ]
                    }
                ],
                max_completion_tokens=1500,
                temperature=0.2,  # Low temperature for accuracy
                response_format={"type": "json_object"}
            )

            # Parse response
            response_text = response.choices[0].message.content.strip()
            
            import json
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                # Clean JSON from markdown if present
                response_text = re.sub(r'^```json\s*', '', response_text)
                response_text = re.sub(r'\s*```$', '', response_text)
                data = json.loads(response_text)
            
            # Convert to LinkedInProfile
            profile = LinkedInProfile(
                name=data.get('name', ''),
                headline=data.get('headline', ''),
                location=data.get('location', ''),
                about=data.get('about', ''),
                current_position=data.get('current_position', ''),
                current_company=data.get('current_company', ''),
                connections=data.get('connections', ''),
                industry=data.get('industry', ''),
                experience=data.get('experience', []),
                skills=data.get('skills', []),
                education=data.get('education', []),
                profile_url=url
            )
            
            # Extract keywords
            profile.extracted_keywords = self._extract_keywords_from_profile(profile)
            
            return profile

        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Failed to parse Vision API response: {e}")
            self.logger.error(f"Response: {response_text[:500]}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Vision API error: {str(e)}")
            return None

    def _extract_keywords_from_profile(self, profile: LinkedInProfile) -> List[str]:
        """Extract relevant keywords from profile for job matching."""
        keywords = set()
        
        # Add skills directly
        keywords.update(profile.skills[:10])
        
        # Extract tech keywords from headline and about
        tech_terms = [
            'python', 'javascript', 'java', 'react', 'node.js', 'sql', 'aws', 'docker',
            'kubernetes', 'machine learning', 'data science', 'artificial intelligence',
            'project management', 'agile', 'scrum', 'leadership', 'management'
        ]
        
        text_to_search = f"{profile.headline} {profile.about}".lower()
        for term in tech_terms:
            if term in text_to_search:
                keywords.add(term.title())
        
        return list(keywords)[:15]

    def _create_fallback_profile(self, linkedin_url: str) -> LinkedInProfile:
        """Create basic fallback profile from URL when extraction fails."""
        profile = LinkedInProfile()
        profile.profile_url = linkedin_url
        
        # Try to extract name from URL
        match = re.search(r'/in/([^/?]+)', linkedin_url)
        if match:
            username = match.group(1)
            name_parts = username.replace('-', ' ').split()
            profile.name = ' '.join(word.capitalize() for word in name_parts)
        
        return profile

    def _is_valid_linkedin_url(self, url: str) -> bool:
        """Validate LinkedIn profile URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return (
                parsed.netloc in ['linkedin.com', 'www.linkedin.com'] and
                '/in/' in parsed.path
            )
        except:
            return False

    def _clean_linkedin_url(self, url: str) -> str:
        """Clean and normalize LinkedIn URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            clean_path = parsed.path.split('?')[0]
            return f"https://www.linkedin.com{clean_path}"
        except:
            return url

    def _respect_rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            self.logger.info(f"⏳ Rate limiting: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def _make_session_key(self, email: str) -> str:
        base = (email or "public").strip().lower()
        h = hashlib.sha256(base.encode()).hexdigest()[:16]
        return f"playwright:linkedin:session:{h}"

    def _capture_segmented_screenshots(self, page: Page, max_segments: int = 5) -> List[str]:
        """Capture multiple viewport screenshots as compressed JPEG segments."""
        try:
            page.set_viewport_size({"width": 1200, "height": 1100})
        except Exception:
            pass

        segments: List[str] = []
        try:
            total_height = page.evaluate("document.body.scrollHeight")
        except Exception:
            total_height = 5000

        viewport = page.viewport_size or {"height": 1100}
        viewport_h = viewport.get("height", 1100)
        steps = min(max_segments, max(1, int(total_height / max(800, viewport_h - 100))))

        for i in range(steps):
            y = int((total_height - viewport_h) * (i / max(1, steps - 1))) if steps > 1 else 0
            try:
                page.evaluate(f"window.scrollTo(0, {y})")
                time.sleep(0.4 + random.uniform(0.05, 0.15))
            except Exception:
                pass

            png_bytes = page.screenshot(full_page=False)
            try:
                img = Image.open(BytesIO(png_bytes)).convert("RGB")
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=70, optimize=True)
                jpeg_bytes = buf.getvalue()
            except Exception:
                jpeg_bytes = png_bytes

            fpath = tempfile.mktemp(suffix='.jpg')
            with open(fpath, 'wb') as f:
                f.write(jpeg_bytes)
            segments.append(fpath)

        return segments

    def get_job_relevant_context(self, profile: LinkedInProfile, job_description: str = "") -> Dict[str, Any]:
        """
        Extract job-relevant context from profile for application generation.
        
        This formats the profile data for use in cover letters, emails, etc.
        """
        return {
            "profile_summary": {
                "name": profile.name,
                "current_role": f"{profile.current_position} at {profile.current_company}",
                "location": profile.location,
                "headline": profile.headline
            },
            "experience_highlights": profile.experience[:3],
            "relevant_skills": profile.skills[:10],
            "education_background": profile.education[:2],
            "personalization_keywords": profile.extracted_keywords,
            "about_section": profile.about[:500] if profile.about else ""
        }

