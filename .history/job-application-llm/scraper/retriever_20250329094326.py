from autoscraper import AutoScraper
import requests

class DataRetriever:
    def __init__(self):
        self.scraper = AutoScraper()
        
    def scrape_job_posting(self, url):
        """Scrape job posting details from a given URL using AutoScraper."""
        try:
            # For job postings, we need to extract different elements
            job_title_model = AutoScraper()
            company_model = AutoScraper()
            desc_model = AutoScraper()
            req_model = AutoScraper()
            location_model = AutoScraper()
            
            # Get the page content
            response = requests.get(url)
            html_content = response.text
            
            # Build models for each component with sample data
            # These are common patterns - AutoScraper will find similar elements
            job_title_model.build(html_content, ['Software Engineer', 'Data Scientist', 'Product Manager'])
            company_model.build(html_content, ['Google', 'Microsoft', 'Amazon'])
            desc_model.build(html_content, ['Job Description', 'About the role', 'What you\'ll do'])
            req_model.build(html_content, ['Requirements', 'Qualifications', 'What you need'])
            location_model.build(html_content, ['Remote', 'San Francisco', 'New York'])
            
            # Extract data
            job_title = job_title_model.get_result(html_content)
            company_name = company_model.get_result(html_content)
            job_description = desc_model.get_result(html_content)
            requirements = req_model.get_result(html_content)
            location = location_model.get_result(html_content)
            
            # Format the results
            job_data = {
                'job_title': job_title[0] if job_title else "Unknown Job Title",
                'company_name': company_name[0] if company_name else "Unknown Company",
                'job_description': " ".join(job_description) if job_description else "No job description found",
                'requirements': " ".join(requirements) if requirements else "No specific requirements found",
                'location': location[0] if location else "Unknown Location",
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
            # For LinkedIn profiles, we need to extract different elements
            name_model = AutoScraper()
            title_model = AutoScraper()
            company_model = AutoScraper()
            
            # Get the page content
            response = requests.get(url)
            html_content = response.text
            
            # Build models for each component with sample data
            # These are common patterns - AutoScraper will find similar elements
            name_model.build(html_content, ['John Doe', 'Jane Smith', 'Alex Johnson'])
            title_model.build(html_content, ['Software Engineer', 'Data Scientist', 'Product Manager'])
            company_model.build(html_content, ['Google', 'Microsoft', 'Amazon'])
            
            # Extract data
            name = name_model.get_result(html_content)
            title = title_model.get_result(html_content)
            company = company_model.get_result(html_content)
            
            # Format the results
            profile_data = {
                'name': name[0] if name else "Unknown Name",
                'title': title[0] if title else "Unknown Title",
                'company': company[0] if company else "Unknown Company",
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
        self.scraper.save(filename)
        
    def load_models(self, filename):
        """Load scraper models from a file."""
        self.scraper.load(filename)