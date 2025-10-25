import requests
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
from app.linkedin_vision_scraper import LinkedInVisionScraper

# Load environment variables
load_dotenv()

class DataRetriever:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Initialize LinkedIn scraper with Vision API (simple and reliable)
        self.linkedin_scraper = LinkedInVisionScraper()
        
    def scrape_job_posting(self, url, job_title=None, company_name=None):
        """Scrape job posting details from a given URL using Jina Reader API."""
        try:
            # Prepare Jina Reader URL
            jina_url = f"https://r.jina.ai/{url}"
            
            # Get the page content in JSON format
            headers = {"Accept": "application/json"}
            response = requests.get(jina_url, headers=headers)
            
            # Check if the request was successful
            if response.status_code != 200:
                print(f"Failed to fetch URL: {url}, Status code: {response.status_code}")
                return {'error': f"Failed to fetch URL: Status code {response.status_code}"}
            
            # Parse the JSON response
            content_data = response.json()
            
            # Check response structure
            if content_data.get('code') != 200 or 'data' not in content_data:
                print(f"Unexpected API response structure: {content_data}")
                return {'error': "Unexpected API response structure"}
            
            # Extract content from the response
            if 'content' in content_data['data']:
                text_content = content_data['data']['content']
            else:
                print(f"No content found in API response: {content_data}")
                return {'error': "No content found in API response"}
            
            # Use GPT to extract structured information from the content
            extracted_data = self._extract_job_data_with_gpt(text_content, url, job_title, company_name)
            
            # Print confirmation with key info
            print(f"Scraped job posting: {extracted_data['company_name']} - {extracted_data['job_title']} - {extracted_data['location']}")
            
            return extracted_data
        except Exception as e:
            print(f"Error scraping job posting: {str(e)}")
            return {'error': str(e)}
    
    def scrape_linkedin_profile(self, url, job_title=None, company_name=None):
        """
        Scrape LinkedIn profile using Playwright + GPT-4 Vision.
        
        Simple, reliable approach:
        1. Screenshot the profile with Playwright
        2. Extract data with GPT-4 Vision API
        """
        try:
            print(f"🔄 Extracting LinkedIn profile: {url}")

            # Extract profile using Vision API
            profile = self.linkedin_scraper.extract_profile_data(url)
            
            if not profile or not profile.name:
                print(f"❌ LinkedIn scraping failed for {url}")
                return self._get_fallback_profile_data(url)
            
            # Convert LinkedInProfile to format expected by rest of application
            extracted_data = {
                'name': profile.name or "Unknown Name",
                'title': profile.current_position or "Unknown Title",
                'company': profile.current_company or "Unknown Company", 
                'location': profile.location or "Unknown Location",
                'about': profile.about or "",
                'experience': profile.experience[:3],  # Top 3 for context
                'education': profile.education[:2],   # Top 2 for context
                'skills': profile.skills[:10],        # Top 10 skills
                'url': url,
                'headline': profile.headline or "",
                'industry': profile.industry or "",
                'connections': profile.connections or "",
                'extracted_keywords': profile.extracted_keywords or [],
                'scraping_method': 'vision_api'
            }
            
            # Get job-relevant context if job info provided
            if job_title or company_name:
                job_context = f"{job_title or ''} at {company_name or ''}".strip()
                context = self.linkedin_scraper.get_job_relevant_context(profile, job_context)
                extracted_data['personalization_keywords'] = context.get('personalization_keywords', [])
            
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
                model="gpt-4o",
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
            
            # Format the results to match existing structure
            job_data = {
                'job_title': parsed_data.get('job_title', job_title or "Unknown Job Title"),
                'company_name': parsed_data.get('company_name', company_name or "Unknown Company"),
                'job_description': parsed_data.get('job_description', "No job description found"),
                'requirements': parsed_data.get('requirements', "No specific requirements found"),
                'location': parsed_data.get('location', "Unknown Location"),
                'url': url
            }
            
            return job_data
            
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
    
    def _filter_linkedin_content(self, content):
        """Minimal filter for LinkedIn content to extract just essential profile information."""
        try:
            # Extract just the title/name from the content (usually in the first few lines)
            lines = content.split('\n')
            
            # Get the first few relevant lines
            filtered_content = ""
            
            # Extract title line (usually contains "Name - Title | LinkedIn")
            title_line = next((line for line in lines if "LinkedIn" in line), "Unknown - Unknown | LinkedIn")
            filtered_content += f"Title: {title_line}\n"
            
            # Add minimal location information if present
            location_line = next((line for line in lines if "Area" in line or ", " in line and len(line) < 50), "")
            if location_line:
                filtered_content += f"Location: {location_line.strip()}\n"
            
            # Add minimal additional context (just to help GPT make sense of the data)
            filtered_content += "Profile Summary: LinkedIn profile extraction\n"
            
            return filtered_content
            
        except Exception as e:
            print(f"Error filtering LinkedIn content: {str(e)}")
            # Return just the first 100 characters as a fallback
            return content[:100] + "\n(Content truncated due to processing error)"

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
                model="gpt-4o",
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