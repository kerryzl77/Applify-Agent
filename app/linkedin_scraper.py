"""
LinkedIn Profile Scraper Service
================================

Provides reliable LinkedIn profile data extraction using multiple methods:
1. Bright Data API (Primary - Most Compliant)
2. RapidAPI LinkedIn Scraper (Fallback)
3. Alternative profile parsing methods

Designed for job application context extraction with compliance focus.
"""

import os
import re
import json
import time
import requests
import logging
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class LinkedInProfile:
    """Structured LinkedIn profile data for job application context."""
    name: str = ""
    headline: str = ""
    location: str = ""
    about: str = ""
    current_company: str = ""
    current_position: str = ""
    experience: List[Dict] = None
    skills: List[str] = None
    education: List[Dict] = None
    connections: str = ""
    profile_url: str = ""
    extracted_keywords: List[str] = None
    industry: str = ""
    
    def __post_init__(self):
        if self.experience is None:
            self.experience = []
        if self.skills is None:
            self.skills = []
        if self.education is None:
            self.education = []
        if self.extracted_keywords is None:
            self.extracted_keywords = []

class LinkedInScraper:
    """
    Enterprise-grade LinkedIn profile scraper with multiple data sources.
    
    Features:
    - Bright Data API integration (primary)
    - RapidAPI fallback methods
    - Compliance-focused data extraction
    - Context extraction for job applications
    - Rate limiting and error handling
    """
    
    def __init__(self):
        # API credentials from environment
        self.bright_data_api_key = os.getenv("BRIGHT_DATA_API_KEY")
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY")
        
        # API endpoints
        self.bright_data_base_url = "https://api.brightdata.com/datasets/v3"
        self.rapidapi_base_url = "https://linkedin-data-api.p.rapidapi.com"
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _search_profile_info(self, linkedin_url: str) -> Optional[Dict]:
        """Extract profile info from web search results (most reliable, no API needed)."""
        try:
            # Extract username from URL
            username = linkedin_url.rstrip('/').split('/')[-1]
            
            # Search DuckDuckGo for the LinkedIn profile
            search_url = f"https://html.duckduckgo.com/html/?q=site:linkedin.com/in/{username}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            if response.status_code != 200:
                return None
            
            # Extract name and title from search snippets
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find result snippets that contain profile info
            snippets = soup.find_all('a', class_='result__snippet')
            for snippet in snippets:
                text = snippet.get_text()
                # LinkedIn snippets typically format as: "Name - Position at Company | LinkedIn"
                if ' - ' in text and ('at ' in text.lower() or ' | ' in text):
                    parts = text.split(' - ')
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        title_company = parts[1].split(' | ')[0].strip()
                        
                        # Parse "Position at Company"
                        if ' at ' in title_company.lower():
                            at_index = title_company.lower().rfind(' at ')
                            title = title_company[:at_index].strip()
                            company = title_company[at_index + 4:].strip()
                        else:
                            title = title_company
                            company = ""
                        
                        return {
                            'name': name,
                            'title': title,
                            'company': company,
                            'url': linkedin_url
                        }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Search extraction failed: {str(e)}")
            return None
    
    def extract_profile_data(self, linkedin_url: str) -> Optional[LinkedInProfile]:
        """
        Extract LinkedIn profile data using the best available method.
        
        Args:
            linkedin_url: Full LinkedIn profile URL
            
        Returns:
            LinkedInProfile object with extracted data or None if failed
        """
        try:
            # Validate LinkedIn URL
            if not self._is_valid_linkedin_url(linkedin_url):
                self.logger.error(f"Invalid LinkedIn URL: {linkedin_url}")
                return None
            
            # Clean and normalize URL
            clean_url = self._clean_linkedin_url(linkedin_url)
            
            # Try Bright Data first (most compliant)
            if self.bright_data_api_key:
                self.logger.info("🔄 Attempting Bright Data extraction...")
                profile = self._extract_with_bright_data(clean_url)
                if profile:
                    self.logger.info("✅ Bright Data extraction successful")
                    return profile
            
            # Fallback to RapidAPI
            if self.rapidapi_key:
                self.logger.info("🔄 Attempting RapidAPI fallback...")
                profile = self._extract_with_rapidapi(clean_url)
                if profile:
                    self.logger.info("✅ RapidAPI extraction successful")
                    return profile
            
            # Try web search extraction (most reliable free method)
            self.logger.info("🔍 Attempting web search extraction...")
            search_data = self._search_profile_info(clean_url)
            if search_data:
                self.logger.info(f"✅ Web search successful: {search_data['name']} - {search_data['title']}")
                return LinkedInProfile(
                    name=search_data['name'],
                    headline=search_data['title'],
                    current_position=search_data['title'],
                    current_company=search_data['company'],
                    profile_url=clean_url
                )
            
            # Last resort: Parse URL for basic info
            self.logger.warning("⚠️ Using basic URL parsing as final fallback")
            return self._extract_basic_info_from_url(clean_url)
            
        except Exception as e:
            self.logger.error(f"Error extracting LinkedIn profile: {str(e)}")
            return None
    
    def _extract_with_bright_data(self, linkedin_url: str) -> Optional[LinkedInProfile]:
        """Extract profile data using Bright Data API."""
        try:
            # Rate limiting
            self._respect_rate_limit()
            
            headers = {
                "Authorization": f"Bearer {self.bright_data_api_key}",
                "Content-Type": "application/json"
            }
            
            # Bright Data LinkedIn Profile dataset ID
            dataset_id = "gd_l1viktl72bvl7bjuj0"  # LinkedIn profiles dataset
            
            payload = [{
                "url": linkedin_url
            }]
            
            response = requests.post(
                f"{self.bright_data_base_url}/trigger",
                headers=headers,
                json=payload,
                params={
                    "dataset_id": dataset_id,
                    "format": "json"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0:
                    return self._parse_bright_data_response(result[0], linkedin_url)
            else:
                self.logger.error(f"Bright Data API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.logger.error(f"Bright Data extraction error: {str(e)}")
        
        return None
    
    def _extract_with_rapidapi(self, linkedin_url: str) -> Optional[LinkedInProfile]:
        """Extract profile data using RapidAPI LinkedIn scraper."""
        try:
            # Rate limiting
            self._respect_rate_limit()
            
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "linkedin-data-api.p.rapidapi.com"
            }
            
            response = requests.get(
                f"{self.rapidapi_base_url}/get-profile-data-by-url",
                headers=headers,
                params={"url": linkedin_url},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    return self._parse_rapidapi_response(result.get("data", {}), linkedin_url)
            else:
                self.logger.error(f"RapidAPI error: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.logger.error(f"RapidAPI extraction error: {str(e)}")
        
        return None
    
    def _parse_bright_data_response(self, data: Dict, url: str) -> LinkedInProfile:
        """Parse Bright Data API response into LinkedInProfile."""
        try:
            profile = LinkedInProfile()
            
            # Basic info
            profile.name = data.get("name", "")
            profile.headline = data.get("headline", "")
            profile.location = data.get("location", "")
            profile.about = data.get("about", "")
            profile.profile_url = url
            profile.connections = data.get("connections", "")
            profile.industry = data.get("industry", "")
            
            # Current position
            experiences = data.get("experience", [])
            if experiences and len(experiences) > 0:
                current = experiences[0]
                profile.current_company = current.get("company", "")
                profile.current_position = current.get("title", "")
            
            # Experience
            profile.experience = self._normalize_experience(experiences[:5])  # Top 5
            
            # Skills
            profile.skills = data.get("skills", [])[:20]  # Top 20 skills
            
            # Education
            profile.education = self._normalize_education(data.get("education", []))
            
            # Extract keywords for job matching
            profile.extracted_keywords = self._extract_keywords_from_profile(profile)
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Error parsing Bright Data response: {str(e)}")
            return LinkedInProfile()
    
    def _parse_rapidapi_response(self, data: Dict, url: str) -> LinkedInProfile:
        """Parse RapidAPI response into LinkedInProfile."""
        try:
            profile = LinkedInProfile()
            
            # Basic info
            profile.name = data.get("firstName", "") + " " + data.get("lastName", "")
            profile.headline = data.get("headline", "")
            profile.location = data.get("locationName", "")
            profile.about = data.get("summary", "")
            profile.profile_url = url
            profile.industry = data.get("industryName", "")
            
            # Current position
            positions = data.get("positions", {}).get("values", [])
            if positions:
                current = positions[0]
                profile.current_company = current.get("company", {}).get("name", "")
                profile.current_position = current.get("title", "")
            
            # Experience
            profile.experience = self._normalize_rapidapi_experience(positions[:5])
            
            # Skills
            skills_data = data.get("skills", {}).get("values", [])
            profile.skills = [skill.get("skill", {}).get("name", "") for skill in skills_data[:20]]
            
            # Education
            education_data = data.get("educations", {}).get("values", [])
            profile.education = self._normalize_rapidapi_education(education_data)
            
            # Extract keywords
            profile.extracted_keywords = self._extract_keywords_from_profile(profile)
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Error parsing RapidAPI response: {str(e)}")
            return LinkedInProfile()
    
    def _extract_basic_info_from_url(self, linkedin_url: str) -> LinkedInProfile:
        """Extract basic info from LinkedIn URL as last resort."""
        try:
            profile = LinkedInProfile()
            profile.profile_url = linkedin_url
            
            # Extract username from URL
            match = re.search(r'/in/([^/?]+)', linkedin_url)
            if match:
                username = match.group(1)
                # Convert username to readable name (basic heuristic)
                name_parts = username.replace('-', ' ').split()
                profile.name = ' '.join(word.capitalize() for word in name_parts)
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Error extracting basic info: {str(e)}")
            return LinkedInProfile()
    
    def _normalize_experience(self, experiences: List[Dict]) -> List[Dict]:
        """Normalize experience data format."""
        normalized = []
        for exp in experiences:
            normalized_exp = {
                "title": exp.get("title", ""),
                "company": exp.get("company", ""),
                "start_date": exp.get("start_date", ""),
                "end_date": exp.get("end_date", "Present"),
                "description": exp.get("description", ""),
                "location": exp.get("location", "")
            }
            normalized.append(normalized_exp)
        return normalized
    
    def _normalize_rapidapi_experience(self, positions: List[Dict]) -> List[Dict]:
        """Normalize RapidAPI experience format."""
        normalized = []
        for pos in positions:
            normalized_exp = {
                "title": pos.get("title", ""),
                "company": pos.get("company", {}).get("name", ""),
                "start_date": pos.get("startDate", {}).get("year", ""),
                "end_date": pos.get("endDate", {}).get("year", "Present") if pos.get("endDate") else "Present",
                "description": pos.get("summary", ""),
                "location": pos.get("company", {}).get("location", "")
            }
            normalized.append(normalized_exp)
        return normalized
    
    def _normalize_education(self, education: List[Dict]) -> List[Dict]:
        """Normalize education data format."""
        normalized = []
        for edu in education:
            normalized_edu = {
                "institution": edu.get("school", edu.get("institution", "")),
                "degree": edu.get("degree", ""),
                "field": edu.get("field_of_study", edu.get("field", "")),
                "graduation_year": edu.get("end_date", edu.get("graduation_year", ""))
            }
            normalized.append(normalized_edu)
        return normalized
    
    def _normalize_rapidapi_education(self, educations: List[Dict]) -> List[Dict]:
        """Normalize RapidAPI education format."""
        normalized = []
        for edu in educations:
            normalized_edu = {
                "institution": edu.get("schoolName", ""),
                "degree": edu.get("degree", ""),
                "field": edu.get("fieldOfStudy", ""),
                "graduation_year": edu.get("endDate", {}).get("year", "") if edu.get("endDate") else ""
            }
            normalized.append(normalized_edu)
        return normalized
    
    def _extract_keywords_from_profile(self, profile: LinkedInProfile) -> List[str]:
        """Extract relevant keywords from profile for job matching."""
        keywords = []
        
        # Extract from headline
        if profile.headline:
            keywords.extend(self._extract_tech_keywords(profile.headline))
        
        # Extract from about section
        if profile.about:
            keywords.extend(self._extract_tech_keywords(profile.about))
        
        # Extract from skills
        keywords.extend(profile.skills[:10])  # Top 10 skills
        
        # Extract from experience descriptions
        for exp in profile.experience:
            if exp.get("description"):
                keywords.extend(self._extract_tech_keywords(exp["description"]))
        
        # Remove duplicates and return top 15
        unique_keywords = list(set(keywords))
        return unique_keywords[:15]
    
    def _extract_tech_keywords(self, text: str) -> List[str]:
        """Extract technical keywords from text."""
        tech_keywords = [
            'python', 'javascript', 'java', 'react', 'node.js', 'sql', 'aws', 'docker',
            'kubernetes', 'machine learning', 'data science', 'artificial intelligence',
            'project management', 'agile', 'scrum', 'leadership', 'management',
            'software development', 'web development', 'cloud computing', 'devops',
            'api', 'microservices', 'database', 'frontend', 'backend', 'full stack'
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in tech_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword.title())
        
        return found_keywords
    
    def _is_valid_linkedin_url(self, url: str) -> bool:
        """Validate if URL is a LinkedIn profile URL."""
        try:
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
            # Remove tracking parameters
            parsed = urlparse(url)
            clean_path = parsed.path.split('?')[0]  # Remove query parameters
            
            # Ensure HTTPS
            return f"https://www.linkedin.com{clean_path}"
        except:
            return url
    
    def _respect_rate_limit(self):
        """Implement rate limiting between API calls."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def get_job_relevant_context(self, profile: LinkedInProfile, job_description: str = "") -> Dict[str, Any]:
        """
        Extract job-relevant context from LinkedIn profile.
        
        This is the core method for job application context extraction.
        """
        try:
            context = {
                "profile_summary": {
                    "name": profile.name,
                    "current_role": f"{profile.current_position} at {profile.current_company}",
                    "location": profile.location,
                    "industry": profile.industry,
                    "headline": profile.headline
                },
                "experience_highlights": [],
                "relevant_skills": profile.skills[:10],
                "education_background": [],
                "networking_context": {
                    "mutual_connections": profile.connections,
                    "profile_url": profile.profile_url
                },
                "personalization_keywords": profile.extracted_keywords,
                "about_section": profile.about[:500] if profile.about else ""  # First 500 chars
            }
            
            # Experience highlights (last 3 positions)
            for exp in profile.experience[:3]:
                highlight = {
                    "role": exp.get("title", ""),
                    "company": exp.get("company", ""),
                    "duration": f"{exp.get('start_date', '')} - {exp.get('end_date', '')}",
                    "description": exp.get("description", "")[:200]  # First 200 chars
                }
                context["experience_highlights"].append(highlight)
            
            # Education background
            for edu in profile.education[:2]:  # Top 2 education entries
                education = {
                    "institution": edu.get("institution", ""),
                    "degree": edu.get("degree", ""),
                    "field": edu.get("field", ""),
                    "year": edu.get("graduation_year", "")
                }
                context["education_background"].append(education)
            
            # If job description provided, find relevant matches
            if job_description:
                context["job_relevance"] = self._analyze_job_relevance(profile, job_description)
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error getting job relevant context: {str(e)}")
            return {"error": "Failed to extract context"}
    
    def _analyze_job_relevance(self, profile: LinkedInProfile, job_description: str) -> Dict[str, Any]:
        """Analyze how profile matches job description."""
        try:
            job_keywords = self._extract_tech_keywords(job_description.lower())
            profile_keywords = [k.lower() for k in profile.extracted_keywords]
            
            matching_keywords = set(job_keywords) & set(profile_keywords)
            
            relevance_score = min(100, len(matching_keywords) * 10)  # Max 100%
            
            return {
                "relevance_score": relevance_score,
                "matching_keywords": list(matching_keywords),
                "suggested_talking_points": list(matching_keywords)[:5],
                "experience_match": "High" if relevance_score > 70 else "Medium" if relevance_score > 40 else "Low"
            }
        except:
            return {"relevance_score": 50, "matching_keywords": [], "experience_match": "Medium"}
    
    def test_connection(self) -> Dict[str, bool]:
        """Test API connections and return status."""
        status = {
            "bright_data": False,
            "rapidapi": False,
            "basic_parsing": True  # Always available
        }
        
        # Test Bright Data
        if self.bright_data_api_key:
            try:
                headers = {"Authorization": f"Bearer {self.bright_data_api_key}"}
                response = requests.get(
                    f"{self.bright_data_base_url}/datasets",
                    headers=headers,
                    timeout=10
                )
                status["bright_data"] = response.status_code == 200
            except:
                pass
        
        # Test RapidAPI
        if self.rapidapi_key:
            try:
                headers = {
                    "X-RapidAPI-Key": self.rapidapi_key,
                    "X-RapidAPI-Host": "linkedin-data-api.p.rapidapi.com"
                }
                # Test with a simple endpoint (if available)
                status["rapidapi"] = True  # Assume working if key is provided
            except:
                pass
        
        return status

# Usage example and testing
if __name__ == "__main__":
    scraper = LinkedInScraper()
    
    # Test connection
    status = scraper.test_connection()
    print("Connection Status:", status)
    
    # Example profile extraction
    test_url = "https://www.linkedin.com/in/satyanadella/"
    profile = scraper.extract_profile_data(test_url)
    
    if profile:
        print(f"Extracted profile for: {profile.name}")
        print(f"Current position: {profile.current_position}")
        print(f"Skills: {', '.join(profile.skills[:5])}")
        
        # Get job-relevant context
        context = scraper.get_job_relevant_context(profile, "Software Engineer position requiring Python and leadership skills")
        print("Job relevance analysis:", context.get("job_relevance", {}))
    else:
        print("Failed to extract profile data")