from autoscraper import AutoScraper
import requests

class DataRetriever:
    def __init__(self):
        self.job_scraper = AutoScraper()
        self.profile_scraper = AutoScraper()
        
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
        """Parse job posting details from manually entered text."""
        try:
            # Initialize empty results
            job_titles = []
            companies = []
            descriptions = []
            requirements = []
            locations = []
            
            # Split text into lines for analysis
            lines = text.split('\n')
            
            # Look for job title in first few lines
            for line in lines[:3]:
                if any(keyword in line.lower() for keyword in ["senior", "engineer", "manager", "developer", "director"]):
                    job_titles.append(line.strip())
                    break
            
            # Look for company name
            for line in lines[:5]:
                if any(keyword in line.lower() for keyword in ["at", "company:", "organization:"]):
                    companies.append(line.replace("at", "").replace("Company:", "").replace("Organization:", "").strip())
                    break
            
            # Look for description and requirements
            in_description = False
            in_requirements = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check section headers
                if any(keyword.lower() in line.lower() for keyword in ["about the role", "job description", "responsibilities"]):
                    in_description = True
                    in_requirements = False
                    continue
                elif any(keyword.lower() in line.lower() for keyword in ["requirements", "qualifications", "what you'll need"]):
                    in_description = False
                    in_requirements = True
                    continue
                
                # Collect content
                if in_description:
                    descriptions.append(line)
                elif in_requirements:
                    requirements.append(line)
                
                # Look for location
                if any(keyword.lower() in line.lower() for keyword in ["location:", "remote", "hybrid"]):
                    locations.append(line.replace("Location:", "").strip())
            
            # Format the results
            job_data = {
                'job_title': job_titles[0] if job_titles else "Unknown Job Title",
                'company_name': companies[0] if companies else "Unknown Company",
                'job_description': " ".join(descriptions) if descriptions else "No job description found",
                'requirements': " ".join(requirements) if requirements else "No specific requirements found",
                'location': locations[0] if locations else "Unknown Location",
                'url': None  # No URL for manual input
            }
            
            return job_data
            
        except Exception as e:
            print(f"Error parsing manual job posting: {str(e)}")
            return {'error': str(e)}
            
    def parse_manual_linkedin_profile(self, text):
        """Parse LinkedIn profile details from manually entered text."""
        try:
            # Initialize empty results
            names = []
            titles = []
            companies = []
            
            # Split text into lines for analysis
            lines = text.split('\n')
            
            # Look for name in first few lines
            for line in lines[:2]:
                if len(line.split()) <= 4 and not any(keyword in line.lower() for keyword in ["at", "company", "profile"]):
                    names.append(line.strip())
                    break
            
            # Look for title and company
            for line in lines[:5]:
                if "at" in line.lower():
                    parts = line.split("at")
                    if len(parts) == 2:
                        titles.append(parts[0].strip())
                        companies.append(parts[1].strip())
            
            # Format the results
            profile_data = {
                'name': names[0] if names else "Unknown Name",
                'title': titles[0] if titles else "Unknown Title",
                'company': companies[0] if companies else "Unknown Company",
                'url': None  # No URL for manual input
            }
            
            return profile_data
            
        except Exception as e:
            print(f"Error parsing manual LinkedIn profile: {str(e)}")
            return {'error': str(e)}