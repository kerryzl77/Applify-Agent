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