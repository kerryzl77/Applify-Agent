"""ATS job board scrapers for Greenhouse and Ashby."""

import hashlib
import json
import logging
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def compute_job_hash(job_data: Dict[str, Any]) -> str:
    """Compute a hash for job data to detect changes."""
    hash_input = json.dumps(
        {
            "title": job_data.get("title", ""),
            "location": job_data.get("location", ""),
            "team": job_data.get("team", ""),
        },
        sort_keys=True,
    )
    return hashlib.md5(hash_input.encode()).hexdigest()


class GreenhouseScraper:
    """Scraper for Greenhouse job boards using their Boards API."""

    # Greenhouse Boards API endpoint
    API_BASE = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        })

    def extract_board_token(self, board_root_url: str) -> Optional[str]:
        """Extract the board token from a Greenhouse job board URL.
        
        Examples:
            https://job-boards.greenhouse.io/alma -> alma
            https://boards.greenhouse.io/alma -> alma
        """
        parsed = urlparse(board_root_url)
        path = parsed.path.strip("/")
        
        # The token is the last segment of the path
        if path:
            parts = path.split("/")
            return parts[-1] if parts else None
        return None

    def fetch_jobs(self, board_root_url: str, company_name: str) -> List[Dict[str, Any]]:
        """Fetch all jobs from a Greenhouse job board.
        
        Args:
            board_root_url: The root URL of the Greenhouse board (e.g., https://job-boards.greenhouse.io/alma)
            company_name: Company name for logging
            
        Returns:
            List of normalized job dictionaries
        """
        board_token = self.extract_board_token(board_root_url)
        if not board_token:
            logger.error(f"Could not extract board token from {board_root_url}")
            return []

        api_url = f"{self.API_BASE}/{board_token}/jobs"
        
        try:
            logger.info(f"Fetching Greenhouse jobs for {company_name} from {api_url}")
            response = self.session.get(api_url, timeout=30)
            
            if response.status_code == 404:
                logger.warning(f"Greenhouse board not found for {company_name}: {board_token}")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            jobs = data.get("jobs", [])
            logger.info(f"Found {len(jobs)} jobs for {company_name}")
            
            return self._normalize_jobs(jobs, company_name, board_root_url)
            
        except requests.RequestException as e:
            logger.error(f"Error fetching Greenhouse jobs for {company_name}: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Greenhouse response for {company_name}: {e}")
            return []

    def _normalize_jobs(
        self, jobs: List[Dict], company_name: str, board_root_url: str
    ) -> List[Dict[str, Any]]:
        """Normalize Greenhouse job data to our standard format."""
        normalized = []
        
        for job in jobs:
            job_id = str(job.get("id", ""))
            title = job.get("title", "")
            
            # Get location from the location object
            location_obj = job.get("location", {})
            if isinstance(location_obj, dict):
                location = location_obj.get("name", "")
            else:
                location = str(location_obj) if location_obj else ""
            
            # Get department/team info
            departments = job.get("departments", [])
            team = departments[0].get("name", "") if departments else ""
            
            # Build job URL
            # Greenhouse job URLs are typically: https://job-boards.greenhouse.io/{board_token}/jobs/{job_id}
            job_url = job.get("absolute_url", "")
            if not job_url:
                board_token = self.extract_board_token(board_root_url)
                job_url = f"{board_root_url}/jobs/{job_id}"
            
            normalized_job = {
                "external_job_id": job_id,
                "title": title,
                "company_name": company_name,
                "location": location,
                "team": team,
                "employment_type": None,  # Not readily available from Greenhouse API
                "url": job_url,
                "ats_type": "greenhouse",
                "raw_json": job,
            }
            normalized_job["hash"] = compute_job_hash(normalized_job)
            normalized.append(normalized_job)
        
        return normalized


class AshbyScraper:
    """Scraper for Ashby job boards using their GraphQL API."""

    API_ENDPOINT = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
    
    # GraphQL query for fetching jobs (similar to job-board-scraper)
    JOBS_QUERY = """
    query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
      jobBoard: jobBoardWithTeams(
        organizationHostedJobsPageName: $organizationHostedJobsPageName
      ) {
        teams {
          id
          name
          parentTeamId
        }
        jobPostings {
          id
          title
          teamId
          locationId
          locationName
          employmentType
          compensationTierSummary
          secondaryLocations {
            locationId
            locationName
          }
        }
      }
    }
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def extract_org_name(self, board_root_url: str) -> Optional[str]:
        """Extract the organization name from an Ashby job board URL.
        
        Examples:
            https://jobs.ashbyhq.com/openai -> openai
            https://jobs.ashbyhq.com/Applied%20Compute -> Applied%20Compute
        """
        parsed = urlparse(board_root_url)
        path = parsed.path.strip("/")
        
        if path:
            # URL decode for organization names with spaces
            parts = path.split("/")
            return parts[0] if parts else None
        return None

    def fetch_jobs(self, board_root_url: str, company_name: str) -> List[Dict[str, Any]]:
        """Fetch all jobs from an Ashby job board.
        
        Args:
            board_root_url: The root URL of the Ashby board (e.g., https://jobs.ashbyhq.com/openai)
            company_name: Company name for logging
            
        Returns:
            List of normalized job dictionaries
        """
        org_name = self.extract_org_name(board_root_url)
        if not org_name:
            logger.error(f"Could not extract org name from {board_root_url}")
            return []

        try:
            logger.info(f"Fetching Ashby jobs for {company_name} (org: {org_name})")
            
            payload = {
                "query": self.JOBS_QUERY,
                "variables": {"organizationHostedJobsPageName": org_name},
            }
            
            response = self.session.post(
                self.API_ENDPOINT,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            
            job_board = data.get("data", {}).get("jobBoard")
            if not job_board:
                logger.warning(f"No job board data found for {company_name}")
                return []
            
            job_postings = job_board.get("jobPostings", [])
            teams = job_board.get("teams", [])
            
            # Build team lookup
            team_lookup = {team["id"]: team["name"] for team in teams}
            
            logger.info(f"Found {len(job_postings)} jobs for {company_name}")
            
            return self._normalize_jobs(
                job_postings, team_lookup, company_name, board_root_url
            )
            
        except requests.RequestException as e:
            logger.error(f"Error fetching Ashby jobs for {company_name}: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Ashby response for {company_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching Ashby jobs for {company_name}: {e}")
            return []

    def _normalize_jobs(
        self,
        job_postings: List[Dict],
        team_lookup: Dict[str, str],
        company_name: str,
        board_root_url: str,
    ) -> List[Dict[str, Any]]:
        """Normalize Ashby job data to our standard format."""
        normalized = []
        
        for job in job_postings:
            job_id = job.get("id", "")
            title = job.get("title", "")
            location = job.get("locationName", "")
            
            # Get team name from lookup
            team_id = job.get("teamId")
            team = team_lookup.get(team_id, "") if team_id else ""
            
            # Get employment type
            employment_type = job.get("employmentType", "")
            
            # Build job URL
            job_url = f"{board_root_url}/{job_id}"
            
            # Handle secondary locations
            secondary_locations = job.get("secondaryLocations", [])
            if secondary_locations:
                secondary_names = [loc.get("locationName", "") for loc in secondary_locations]
                if location and secondary_names:
                    location = f"{location}; {'; '.join(secondary_names)}"
            
            normalized_job = {
                "external_job_id": job_id,
                "title": title,
                "company_name": company_name,
                "location": location,
                "team": team,
                "employment_type": employment_type,
                "url": job_url,
                "ats_type": "ashby",
                "raw_json": job,
            }
            normalized_job["hash"] = compute_job_hash(normalized_job)
            normalized.append(normalized_job)
        
        return normalized


def get_scraper(ats_type: str):
    """Get the appropriate scraper for an ATS type."""
    scrapers = {
        "greenhouse": GreenhouseScraper,
        "ashby": AshbyScraper,
    }
    scraper_class = scrapers.get(ats_type.lower())
    if scraper_class:
        return scraper_class()
    raise ValueError(f"Unknown ATS type: {ats_type}")
