from autoscraper import AutoScraper
import requests
from bs4 import BeautifulSoup
import re

class DataRetriever:
    def __init__(self):
        self.scraper = AutoScraper()
        
    def scrape_job_posting(self, url):
        """Scrape job posting details from a given URL."""
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract job details
            job_data = {
                'job_title': self._extract_job_title(soup),
                'company_name': self._extract_company_name(soup),
                'job_description': self._extract_job_description(soup),
                'requirements': self._extract_requirements(soup),
                'location': self._extract_location(soup),
                'url': url
            }
            
            return job_data
        except Exception as e:
            return {'error': str(e)}
    
    def scrape_linkedin_profile(self, url):
        """Scrape LinkedIn profile details."""
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract profile details
            profile_data = {
                'name': self._extract_linkedin_name(soup),
                'title': self._extract_linkedin_title(soup),
                'company': self._extract_linkedin_company(soup),
                'url': url
            }
            
            return profile_data
        except Exception as e:
            return {'error': str(e)}
    
    def _extract_job_title(self, soup):
        # Common job title selectors
        selectors = [
            'h1.job-title', '.posting-headline h2', 
            'h1.topcard__title', '.job-details-jobs-unified-top-card__job-title'
        ]
        
        for selector in selectors:
            title = soup.select_one(selector)
            if title:
                return title.text.strip()
        
        # Fallback to generic h1
        title = soup.find('h1')
        return title.text.strip() if title else "Unknown Job Title"
    
    def _extract_company_name(self, soup):
        # Common company name selectors
        selectors = [
            '.company-name', '.posting-headline h3', 
            '.topcard__org-name-link', '.job-details-jobs-unified-top-card__company-name'
        ]
        
        for selector in selectors:
            company = soup.select_one(selector)
            if company:
                return company.text.strip()
        
        return "Unknown Company"
    
    def _extract_job_description(self, soup):
        # Common job description selectors
        selectors = [
            '.job-description', '.description__text', 
            '.show-more-less-html__markup', '.job-details-jobs-unified-top-card__description-container'
        ]
        
        for selector in selectors:
            description = soup.select_one(selector)
            if description:
                return description.text.strip()
        
        return "No job description found"
    
    def _extract_requirements(self, soup):
        # Look for requirements section
        requirements_section = soup.find(lambda tag: tag.name in ['div', 'section'] and 
                                        re.search(r'requirements|qualifications', tag.text, re.I))
        
        if requirements_section:
            return requirements_section.text.strip()
        
        # Fallback: try to find a list in the job description
        lists = soup.find_all(['ul', 'ol'])
        for list_elem in lists:
            if re.search(r'requirements|qualifications', list_elem.text, re.I):
                return list_elem.text.strip()
        
        return "No specific requirements found"
    
    def _extract_location(self, soup):
        # Common location selectors
        selectors = [
            '.location', '.posting-location', 
            '.topcard__flavor--bullet', '.job-details-jobs-unified-top-card__workplace-type'
        ]
        
        for selector in selectors:
            location = soup.select_one(selector)
            if location:
                return location.text.strip()
        
        return "Unknown Location"
    
    def _extract_linkedin_name(self, soup):
        name = soup.select_one('.pv-top-card--list .text-heading-xlarge')
        return name.text.strip() if name else "Unknown Name"
    
    def _extract_linkedin_title(self, soup):
        title = soup.select_one('.pv-top-card--list .text-body-medium')
        return title.text.strip() if title else "Unknown Title"
    
    def _extract_linkedin_company(self, soup):
        company = soup.select_one('.pv-top-card--experience-list-item .pv-entity__secondary-title')
        return company.text.strip() if company else "Unknown Company"

def scrape_data(url):
    # existing code...
    
    # Replace Beautiful Soup scraping logic with AutoScraper
    wanted_list = ["desired_data"]  # Update this with the actual data you want to scrape
    scraper = AutoScraper()
    result = scraper.build(url, wanted_list)
    
    # Print the first line to confirm successful scraping
    print(result[0] if result else "No data found")
    
    # existing code... 