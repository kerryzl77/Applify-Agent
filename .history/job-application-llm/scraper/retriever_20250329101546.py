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
            
            # Split text into lines and clean
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Common job title keywords
            title_keywords = [
                "senior", "engineer", "manager", "developer", "director", "analyst",
                "scientist", "lead", "architect", "consultant", "specialist"
            ]
            
            # Look for job title - check first 5 lines more thoroughly
            for line in lines[:5]:
                # Check if line contains job title keywords
                if any(keyword.lower() in line.lower() for keyword in title_keywords):
                    # Clean up the title
                    title = line.strip().split("@")[0].split("|")[0].split("-")[0].strip()
                    job_titles.append(title)
                    break
            
            # Look for company name in first 10 lines
            company_indicators = ["at", "company:", "organization:", "@", "|"]
            for line in lines[:10]:
                line_lower = line.lower()
                if any(indicator in line_lower for indicator in company_indicators):
                    # Extract company name
                    for indicator in company_indicators:
                        if indicator in line_lower:
                            company = line.split(indicator)[-1].strip()
                            # Clean up common suffixes
                            company = company.split(",")[0].split("|")[0].strip()
                            companies.append(company)
                            break
                    if companies:  # If found, stop looking
                        break
            
            # Process sections
            current_section = None
            section_content = []
            
            # Section indicators
            description_indicators = [
                "about the role", "job description", "responsibilities",
                "what you'll do", "position summary", "overview"
            ]
            requirement_indicators = [
                "requirements", "qualifications", "what you'll need",
                "required skills", "minimum qualifications", "we're looking for"
            ]
            location_indicators = [
                "location:", "location", "based in", "position location",
                "remote", "hybrid", "on-site", "onsite"
            ]
            
            for line in lines:
                line_lower = line.lower()
                
                # Check for section headers
                if any(indicator in line_lower for indicator in description_indicators):
                    current_section = "description"
                    continue
                elif any(indicator in line_lower for indicator in requirement_indicators):
                    current_section = "requirements"
                    continue
                
                # Check for location
                if any(indicator in line_lower for indicator in location_indicators):
                    # Clean up location
                    location = line.replace("Location:", "").replace("Location", "").strip()
                    locations.append(location)
                    continue
                
                # Collect section content
                if current_section == "description":
                    descriptions.append(line)
                elif current_section == "requirements":
                    requirements.append(line)
            
            # Format the results
            job_data = {
                'job_title': job_titles[0] if job_titles else "Unknown Job Title",
                'company_name': companies[0] if companies else "Unknown Company",
                'job_description': " ".join(descriptions) if descriptions else "No job description found",
                'requirements': " ".join(requirements) if requirements else "No specific requirements found",
                'location': locations[0] if locations else "Unknown Location",
                'url': None  # No URL for manual input
            }
            
            # Print confirmation
            print(f"Parsed job posting: {job_data['company_name']} - {job_data['job_title']}")
            
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
            summary = []
            
            # Split text into lines and clean
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Look for name in first 3 lines
            for line in lines[:3]:
                # Name is usually short and doesn't contain special characters
                words = line.split()
                if 2 <= len(words) <= 4 and all(word.isalpha() for word in words):
                    names.append(line.strip())
                    break
            
            # Look for current position and company
            position_found = False
            for line in lines[:10]:  # Check first 10 lines for current position
                line_lower = line.lower()
                
                # Common position indicators
                if any(indicator in line_lower for indicator in ["current", "present", "working as", "at"]):
                    # Split by common separators
                    for separator in [" at ", " @ ", " | ", " - "]:
                        if separator in line:
                            parts = line.split(separator)
                            if len(parts) >= 2:
                                titles.append(parts[0].strip())
                                companies.append(parts[1].strip())
                                position_found = True
                                break
                    if position_found:
                        break
            
            # Look for summary/about section
            in_summary = False
            for line in lines:
                line_lower = line.lower()
                
                # Check for summary section indicators
                if any(indicator in line_lower for indicator in ["about", "summary", "overview"]):
                    in_summary = True
                    continue
                
                # Collect summary content
                if in_summary and line:
                    summary.append(line)
                    
                # Stop if we hit another section
                if in_summary and any(indicator in line_lower for indicator in ["experience", "education", "skills"]):
                    break
            
            # Format the results
            profile_data = {
                'name': names[0] if names else "Unknown Name",
                'title': titles[0] if titles else "Unknown Title",
                'company': companies[0] if companies else "Unknown Company",
                'summary': " ".join(summary) if summary else "No summary found",
                'url': None  # No URL for manual input
            }
            
            # Print confirmation
            print(f"Parsed LinkedIn profile: {profile_data['name']} - {profile_data['title']} at {profile_data['company']}")
            
            return profile_data
            
        except Exception as e:
            print(f"Error parsing LinkedIn profile: {str(e)}")
            return {'error': str(e)}