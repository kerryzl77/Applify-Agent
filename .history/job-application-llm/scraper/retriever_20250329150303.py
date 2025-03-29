from autoscraper import AutoScraper
import requests
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DataRetriever:
    def __init__(self):
        self.job_scraper = AutoScraper()
        self.profile_scraper = AutoScraper()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def scrape_job_posting(self, url):
        """Scrape job posting details from a given URL using AutoScraper."""
        try:
            # Get the page content
            response = requests.get(url)
            
            # Check if the request was successful
            if response.status_code != 200:
                print(f"Failed to fetch URL: {url}, Status code: {response.status_code}")
                return {'error': f"Failed to fetch URL: Status code {response.status_code}"}
            
            # Instead of trying to build models on the fly with generic examples,
            # we'll use a simpler approach with wanted_list containing common patterns
            
            # First, try to get the job title
            wanted_list = ["Senior", "Engineer", "Manager", "Developer", "Director"]
            self.job_scraper.build(url, wanted_list)
            job_titles = self.job_scraper.get_result_similar(url)
            
            # Then try to get company name
            wanted_list = ["Google", "Uber", "Amazon", "Microsoft", "Company"]
            self.job_scraper.build(url, wanted_list)
            companies = self.job_scraper.get_result_similar(url)
            
            # Extract job description sections
            wanted_list = ["About the role", "Job Description", "Responsibilities"]
            self.job_scraper.build(url, wanted_list)
            descriptions = self.job_scraper.get_result_similar(url)
            
            # Extract requirements sections
            wanted_list = ["Requirements", "Qualifications", "What You'll Need"]
            self.job_scraper.build(url, wanted_list)
            requirements = self.job_scraper.get_result_similar(url)
            
            # Extract location
            wanted_list = ["Remote", "San Francisco", "New York", "Location"]
            self.job_scraper.build(url, wanted_list)
            locations = self.job_scraper.get_result_similar(url)
            
            # Format the results
            job_data = {
                'job_title': job_titles[0] if job_titles else "Unknown Job Title",
                'company_name': companies[0] if companies else "Unknown Company",
                'job_description': " ".join(descriptions) if descriptions else "No job description found",
                'requirements': " ".join(requirements) if requirements else "No specific requirements found",
                'location': locations[0] if locations else "Unknown Location",
                'url': url
            }
            
            # Print confirmation with key info
            print(f"Scraped job posting: {job_data['company_name']} - {job_data['job_title']} - {job_data['location']}")
            
            return job_data
        except Exception as e:
            print(f"Error scraping job posting: {str(e)}")
            return {'error': str(e)}
    
    def scrape_linkedin_profile(self, url):
        """Scrape LinkedIn profile details using AutoScraper."""
        try:
            # Get the page content
            response = requests.get(url)
            
            # Check if the request was successful
            if response.status_code != 200:
                print(f"Failed to fetch URL: {url}, Status code: {response.status_code}")
                return {'error': f"Failed to fetch URL: Status code {response.status_code}"}
            
            # Use similar approach as job scraping
            # Extract profile name
            wanted_list = ["John", "Jane", "Alex", "Name"]
            self.profile_scraper.build(url, wanted_list)
            names = self.profile_scraper.get_result_similar(url)
            
            # Extract profile title
            wanted_list = ["Engineer", "Manager", "Developer", "Title"]
            self.profile_scraper.build(url, wanted_list)
            titles = self.profile_scraper.get_result_similar(url)
            
            # Extract company
            wanted_list = ["Google", "Microsoft", "LinkedIn", "Company"]
            self.profile_scraper.build(url, wanted_list)
            companies = self.profile_scraper.get_result_similar(url)
            
            # Format the results
            profile_data = {
                'name': names[0] if names else "Unknown Name",
                'title': titles[0] if titles else "Unknown Title",
                'company': companies[0] if companies else "Unknown Company",
                'url': url
            }
            
            # Print confirmation with key info
            print(f"Scraped LinkedIn profile: {profile_data['name']} - {profile_data['title']} at {profile_data['company']}")
            
            return profile_data
        except Exception as e:
            print(f"Error scraping LinkedIn profile: {str(e)}")
            return {'error': str(e)}
    
    def save_models(self, filename):
        """Save the scraper models to a file."""
        self.job_scraper.save(f"{filename}_job")
        self.profile_scraper.save(f"{filename}_profile")
        
    def load_models(self, filename):
        """Load scraper models from a file."""
        self.job_scraper.load(f"{filename}_job")
        self.profile_scraper.load(f"{filename}_profile")

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
            parsed_data = eval(response.choices[0].message.content)
            
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
            # Create prompt for GPT-4
            prompt = f"""Extract key information from this LinkedIn profile. Return a JSON object with these fields:
            - name: The person's full name
            - title: Their current job title/role
            - company: Their current company
            - summary: A brief summary of their background or about section (if available)

            LinkedIn Profile:
            {text}
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
            parsed_data = eval(response.choices[0].message.content)
            
            # Format the results to match existing structure
            profile_data = {
                'name': parsed_data.get('name', "Unknown Name"),
                'title': parsed_data.get('title', "Unknown Title"),
                'company': parsed_data.get('company', "Unknown Company"),
                'summary': parsed_data.get('summary', "No summary found"),
                'url': None  # No URL for manual input
            }
            
            # Print confirmation
            print(f"Parsed LinkedIn profile: {profile_data['name']} - {profile_data['title']} at {profile_data['company']}")
            
            return profile_data
            
        except Exception as e:
            print(f"Error parsing LinkedIn profile: {str(e)}")
            return {'error': str(e)}