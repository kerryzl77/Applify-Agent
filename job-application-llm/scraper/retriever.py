import requests
from openai import OpenAI
import json
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DataRetriever:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def scrape_job_posting(self, url):
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
            extracted_data = self._extract_job_data_with_gpt(text_content, url)
            
            # Print confirmation with key info
            print(f"Scraped job posting: {extracted_data['company_name']} - {extracted_data['job_title']} - {extracted_data['location']}")
            
            return extracted_data
        except Exception as e:
            print(f"Error scraping job posting: {str(e)}")
            return {'error': str(e)}
    
    def scrape_linkedin_profile(self, url):
        """Scrape LinkedIn profile details using Jina Reader API with optimized processing."""
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
            
            # Pre-process the content to extract only the essential information
            filtered_content = self._filter_linkedin_content(text_content)
            
            # Use GPT to extract structured information from the filtered content
            extracted_data = self._extract_profile_data_with_gpt(filtered_content, url)
            
            # Print confirmation with key info
            print(f"Scraped LinkedIn profile: {extracted_data['name']} - {extracted_data['title']} at {extracted_data['company']}")
            
            return extracted_data
        except Exception as e:
            print(f"Error scraping LinkedIn profile: {str(e)}")
            return {'error': str(e)}
    
    def _filter_linkedin_content(self, content):
        """Filter LinkedIn content to remove login prompts, legal text, and keep only essential profile information."""
        # Patterns to remove
        patterns_to_remove = [
            # Login and sign-in related patterns
            r'Sign in to view.*?full profile',
            r'Welcome back.*?Email or phone.*?Password.*?Show',
            r'Forgot password\?.*?Sign in',
            r'New to LinkedIn\?.*?Join now',
            r'By clicking Continue to join or sign in.*?Cookie Policy',
            # Navigation and footers
            r'\[Skip to main content\].*?\[.*?\]',
            r'Report this profile',
            # Legal text
            r'User Agreement.*?Privacy Policy.*?Cookie Policy',
            # Repeated view profile prompts
            r'View Jerome\'s full experience.*?Sign in',
            r'Join to view profile',
            # Image references
            r'!\[Image \d+\].*?\)',
            # Hidden content markers
            r'\*\*\*\*'
        ]
        
        # Apply all pattern removals
        filtered_content = content
        for pattern in patterns_to_remove:
            filtered_content = re.sub(pattern, '', filtered_content, flags=re.DOTALL)
        
        # Extract core sections using positive patterns
        core_sections = {
            'name_title': r'^(.*?) - (.*?) \| LinkedIn',
            'location': r'San Francisco Bay Area|[A-Za-z]+ [A-Za-z]+ Area|[A-Za-z]+, [A-Za-z]+',
            'followers': r'(\d+[K]?) followers (\d+[K]?\+?) connections',
            'about': r'About\s+-+\s+(.*?)(?:see more|Experience)',
            'experience': r'Experience & Education\s+-+\s+(.*?)(?:View|Honors)',
            'education': r'University of.*?(\d{4} - \d{4})',
            'websites': r'Websites\s+-+\s+(.*?)(?:Report|About)'
        }
        
        # Build a structured profile with only the relevant sections
        structured_profile = "LinkedIn Profile Summary:\n\n"
        
        # Extract name and title
        name_match = re.search(core_sections['name_title'], filtered_content)
        if name_match:
            structured_profile += f"Name: {name_match.group(1)}\n"
            structured_profile += f"Current Company: {name_match.group(2)}\n"
        
        # Extract location
        location_match = re.search(core_sections['location'], filtered_content)
        if location_match:
            structured_profile += f"Location: {location_match.group(0)}\n"
        
        # Extract followers/connections
        followers_match = re.search(core_sections['followers'], filtered_content)
        if followers_match:
            structured_profile += f"Network: {followers_match.group(0)}\n"
        
        # Extract about section
        about_match = re.search(core_sections['about'], filtered_content, re.DOTALL)
        if about_match:
            structured_profile += f"About: {about_match.group(1).strip()}\n"
        
        # Extract experience section (simplified)
        experience_match = re.search(core_sections['experience'], filtered_content, re.DOTALL)
        if experience_match:
            experience_text = experience_match.group(1).strip()
            # Further clean experience section
            experience_text = re.sub(r'\n+', '\n', experience_text)
            structured_profile += f"Experience:\n{experience_text}\n"
        
        # Extract education
        education_match = re.search(core_sections['education'], filtered_content)
        if education_match:
            structured_profile += f"Education: University of {education_match.group(0)}\n"
        
        # Extract websites
        websites_match = re.search(core_sections['websites'], filtered_content, re.DOTALL)
        if websites_match:
            websites_text = websites_match.group(1).strip()
            # Further clean websites section
            websites_text = re.sub(r'\n+', '\n', websites_text)
            structured_profile += f"Websites:\n{websites_text}\n"
        
        print(f"Original content length: {len(content)} chars, Filtered content length: {len(structured_profile)} chars")
        return structured_profile
    
    def _extract_job_data_with_gpt(self, content_text, url):
        """Use GPT to extract structured job posting data from text content."""
        try:
            # Create prompt for GPT-4
            prompt = f"""Extract key information from this job posting. Return a JSON object with these fields:
            - job_title: The title of the position
            - company_name: The company offering the position
            - job_description: A summary of the main responsibilities and role
            - requirements: Key qualifications and requirements
            - location: Job location (including remote/hybrid if specified)

            Job Posting Content:
            {content_text[:8000]}  # Limit content length to avoid token limits
            """

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise job posting parser. Extract only the requested information and format it as JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }
            )

            # Parse the response
            parsed_data = json.loads(response.choices[0].message.content)
            
            # Format the results to match existing structure
            job_data = {
                'job_title': parsed_data.get('job_title', "Unknown Job Title"),
                'company_name': parsed_data.get('company_name', "Unknown Company"),
                'job_description': parsed_data.get('job_description', "No job description found"),
                'requirements': parsed_data.get('requirements', "No specific requirements found"),
                'location': parsed_data.get('location', "Unknown Location"),
                'url': url
            }
            
            return job_data
            
        except Exception as e:
            print(f"Error extracting job data with GPT: {str(e)}")
            return {
                'job_title': "Unknown Job Title",
                'company_name': "Unknown Company",
                'job_description': "Error extracting job description",
                'requirements': "Error extracting requirements",
                'location': "Unknown Location",
                'url': url,
                'error': str(e)
            }
    
    def _extract_profile_data_with_gpt(self, content_text, url):
        """Use GPT to extract structured LinkedIn profile data from text content."""
        try:
            # Create prompt for GPT-4
            prompt = f"""Extract key information from this LinkedIn profile. Return a JSON object with these fields:
            - name: The person's full name
            - title: Their current job title/role (based on the About section or Experience if available)
            - company: Their current company
            - location: Where they are based
            - summary: A brief summary of their background or about section (if available)

            LinkedIn Profile Content:
            {content_text}
            """

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise LinkedIn profile parser. Extract only the requested information and format it as JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }
            )

            # Parse the response
            parsed_data = json.loads(response.choices[0].message.content)
            
            # Format the results to match existing structure
            profile_data = {
                'name': parsed_data.get('name', "Unknown Name"),
                'title': parsed_data.get('title', "Unknown Title"),
                'company': parsed_data.get('company', "Unknown Company"),
                'location': parsed_data.get('location', "Unknown Location"),
                'summary': parsed_data.get('summary', "No summary found"),
                'url': url
            }
            
            return profile_data
            
        except Exception as e:
            print(f"Error extracting profile data with GPT: {str(e)}")
            return {
                'name': "Unknown Name",
                'title': "Unknown Title",
                'company': "Unknown Company",
                'location': "Unknown Location",
                'summary': "Error extracting summary",
                'url': url,
                'error': str(e)
            }
    
    def parse_manual_job_posting(self, text):
        """Parse job posting details from manually entered text using GPT-4."""
        try:
            # Create prompt for GPT-4
            prompt = f"""Extract key information from this job posting. Return a JSON object with these fields:
            - job_title: The title of the position
            - company_name: The company offering the position
            - job_description: A summary of the main responsibilities and role
            - requirements: Key qualifications and requirements
            - location: Job location (including remote/hybrid if specified)

            Job Posting:
            {text}
            """

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise job posting parser. Extract only the requested information and format it as JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }
            )

            # Parse the response
            parsed_data = json.loads(response.choices[0].message.content)
            
            # Format the results to match existing structure
            job_data = {
                'job_title': parsed_data.get('job_title', "Unknown Job Title"),
                'company_name': parsed_data.get('company_name', "Unknown Company"),
                'job_description': parsed_data.get('job_description', "No job description found"),
                'requirements': parsed_data.get('requirements', "No specific requirements found"),
                'location': parsed_data.get('location', "Unknown Location"),
                'url': None  # No URL for manual input
            }
            
            # Print confirmation
            print(f"Parsed job posting: {job_data['company_name']} - {job_data['job_title']}")
            
            return job_data
            
        except Exception as e:
            print(f"Error parsing manual job posting: {str(e)}")
            return {'error': str(e)}
            
    def parse_manual_linkedin_profile(self, text):
        """Parse LinkedIn profile details from manually entered text using GPT-4."""
        try:
            # Filter content first
            filtered_content = self._filter_linkedin_content(text)
            
            # Use the filtered content for extraction
            profile_data = self._extract_profile_data_with_gpt(filtered_content, None)
            
            # Print confirmation
            print(f"Parsed LinkedIn profile: {profile_data['name']} - {profile_data['title']} at {profile_data['company']}")
            
            return profile_data
            
        except Exception as e:
            print(f"Error parsing LinkedIn profile: {str(e)}")
            return {'error': str(e)}