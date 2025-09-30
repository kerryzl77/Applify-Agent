import re
from urllib.parse import urlparse

class URLValidator:
    """Enhanced URL validation and parsing for job-related websites."""
    
    def __init__(self):
        # Known job sites and their patterns
        self.job_sites = {
            'linkedin.com': {'type': 'linkedin_job', 'pattern': r'/jobs/view/'},
            'indeed.com': {'type': 'job_board', 'pattern': r'/viewjob'},
            'glassdoor.com': {'type': 'job_board', 'pattern': r'/job-listing/'},
            'monster.com': {'type': 'job_board', 'pattern': r'/job-openings/'},
            'ziprecruiter.com': {'type': 'job_board', 'pattern': r'/jobs/'},
            'dice.com': {'type': 'job_board', 'pattern': r'/jobs/detail/'},
            'careerbuilder.com': {'type': 'job_board', 'pattern': r'/job/'},
            'simplyhired.com': {'type': 'job_board', 'pattern': r'/job/'},
            'greenhouse.io': {'type': 'ats', 'pattern': r'/jobs/'},
            'lever.co': {'type': 'ats', 'pattern': r'/jobs/'},
            'workday.com': {'type': 'ats', 'pattern': r'/job/'},
            'jobvite.com': {'type': 'ats', 'pattern': r'/job/'},
            'smartrecruiters.com': {'type': 'ats', 'pattern': r'/jobs/'},
            'bamboohr.com': {'type': 'ats', 'pattern': r'/jobs/view/'},
            'breezy.hr': {'type': 'ats', 'pattern': r'/position/'},
            'recruitee.com': {'type': 'ats', 'pattern': r'/careers/'},
            'ashbyhq.com': {'type': 'ats', 'pattern': r'/jobs/'},
            'wellfound.com': {'type': 'startup_jobs', 'pattern': r'/jobs/'},
            'angel.co': {'type': 'startup_jobs', 'pattern': r'/jobs/'},
            'ycombinator.com': {'type': 'startup_jobs', 'pattern': r'/jobs/'},
            'jobs.': {'type': 'company_careers', 'pattern': r''},  # jobs.company.com
            'careers.': {'type': 'company_careers', 'pattern': r''},  # careers.company.com
        }
        
        # Company patterns for major employers
        self.company_patterns = {
            'google.com': ['careers', 'jobs'],
            'amazon.com': ['jobs', 'careers'],
            'microsoft.com': ['careers', 'jobs'],
            'apple.com': ['jobs', 'careers'],
            'facebook.com': ['careers', 'jobs'],
            'meta.com': ['careers', 'jobs'],
            'netflix.com': ['jobs', 'careers'],
            'tesla.com': ['careers', 'jobs'],
            'uber.com': ['careers', 'jobs'],
            'airbnb.com': ['careers', 'jobs'],
            'spotify.com': ['jobs', 'careers'],
            'salesforce.com': ['careers', 'jobs'],
        }
        
    def validate_and_parse_url(self, url):
        """Validate URL and determine its type for appropriate parsing."""
        try:
            # Normalize URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()
            
            # Remove www. prefix for matching
            domain = re.sub(r'^www\.', '', domain)
            
            # Basic URL validation
            if not domain or '.' not in domain:
                return {
                    'type': 'invalid', 
                    'url': url, 
                    'valid': False, 
                    'error': 'Invalid URL format. Please enter a complete URL (e.g., https://company.com/job)'
                }
            
            # Check for LinkedIn profile vs job posting
            if 'linkedin.com' in domain:
                return self._validate_linkedin_url(url, path)
            
            # Check known job sites
            for site, info in self.job_sites.items():
                if site in domain:
                    if info['pattern'] and not re.search(info['pattern'], path):
                        continue
                    return {
                        'type': info['type'], 
                        'url': url, 
                        'valid': True,
                        'message': f'Detected {info["type"].replace("_", " ").title()}'
                    }
            
            # Check for company career pages
            career_result = self._check_company_careers(url, domain, path)
            if career_result:
                return career_result
            
            # Check for general websites with warning
            warning_result = self._check_general_website(url, domain, path)
            if warning_result:
                return warning_result
            
            # Default: assume it's a general website that might contain job info
            return {
                'type': 'general_website', 
                'url': url, 
                'valid': True,
                'message': 'General website - will attempt to extract job information'
            }
            
        except Exception as e:
            return {
                'type': 'invalid', 
                'url': url, 
                'valid': False, 
                'error': f'Invalid URL format: {str(e)}'
            }
    
    def _validate_linkedin_url(self, url, path):
        """Validate LinkedIn URLs specifically."""
        if '/in/' in path:
            return {
                'type': 'linkedin_profile', 
                'url': url, 
                'valid': True,
                'message': 'LinkedIn Profile detected'
            }
        elif '/jobs/view/' in path or '/jobs/' in path:
            return {
                'type': 'linkedin_job', 
                'url': url, 
                'valid': True,
                'message': 'LinkedIn Job posting detected'
            }
        elif '/company/' in path:
            return {
                'type': 'linkedin_company', 
                'url': url, 
                'valid': True,
                'warning': 'LinkedIn company page detected. Please use a specific job posting or profile URL for better results.'
            }
        else:
            return {
                'type': 'unknown_linkedin', 
                'url': url, 
                'valid': False, 
                'error': 'LinkedIn URL should be a profile (/in/) or job posting (/jobs/). Company pages are not supported.'
            }
    
    def _check_company_careers(self, url, domain, path):
        """Check if URL is a company career page."""
        career_indicators = [
            'job', 'jobs', 'career', 'careers', 'opportunity', 'opportunities', 
            'opening', 'openings', 'position', 'positions', 'hiring', 'work',
            'employment', 'recruit', 'apply'
        ]
        
        # Check if domain starts with career indicators
        if any(domain.startswith(f'{indicator}.') for indicator in ['jobs', 'careers']):
            return {
                'type': 'company_careers', 
                'url': url, 
                'valid': True,
                'message': 'Company career page detected'
            }
        
        # Check if path contains career indicators
        if any(indicator in path for indicator in career_indicators):
            return {
                'type': 'company_careers', 
                'url': url, 
                'valid': True,
                'message': 'Company career page detected'
            }
        
        # Check for specific company patterns
        for company, patterns in self.company_patterns.items():
            if company in domain and any(pattern in path for pattern in patterns):
                return {
                    'type': 'company_careers', 
                    'url': url, 
                    'valid': True,
                    'message': f'{company.split(".")[0].title()} career page detected'
                }
        
        return None
    
    def _check_general_website(self, url, domain, path):
        """Check for general websites with appropriate warnings."""
        # Common non-job sites that users might accidentally enter
        common_sites = [
            'amazon.com', 'google.com', 'facebook.com', 'twitter.com', 
            'youtube.com', 'instagram.com', 'tiktok.com', 'reddit.com',
            'wikipedia.org', 'github.com', 'stackoverflow.com'
        ]
        
        # Check if it's a major site without job-related path
        for site in common_sites:
            if site in domain:
                career_indicators = ['job', 'career', 'hiring', 'work', 'employment']
                if not any(indicator in path for indicator in career_indicators):
                    return {
                        'type': 'warning', 
                        'url': url, 
                        'valid': True,
                        'warning': f'This appears to be a general {site} page. Please ensure this is a job posting or career page.'
                    }
        
        return None
    
    def get_url_recommendations(self, url_type):
        """Get recommendations based on URL type."""
        recommendations = {
            'invalid': [
                'Ensure the URL starts with https:// or http://',
                'Check for typos in the domain name',
                'Use complete URLs like https://company.com/jobs/position'
            ],
            'unknown_linkedin': [
                'For LinkedIn profiles: https://linkedin.com/in/username',
                'For LinkedIn jobs: https://linkedin.com/jobs/view/jobid',
                'Avoid company pages - use specific profiles or job postings'
            ],
            'warning': [
                'Navigate to the careers or jobs section of the website',
                'Look for specific job postings rather than general pages',
                'Ensure the URL contains job-related content'
            ],
            'general_website': [
                'The system will attempt to extract job information',
                'For better results, use direct links to job postings',
                'Consider using job boards or company career pages'
            ]
        }
        
        return recommendations.get(url_type, [])