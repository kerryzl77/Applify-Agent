"""Daily job ingestion entrypoint.

Run with: python -m app.jobs.ingest_daily

This script:
1. Loads the seed list from data/job_seeds.json
2. Upserts ATS company sources into the database
3. Fetches jobs from each source using the appropriate scraper
4. Upserts job posts into the database
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from database.db_manager import DatabaseManager
from app.jobs.ats_scrapers import get_scraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def load_seed_list() -> List[Dict[str, Any]]:
    """Load the job seeds from the JSON file."""
    seed_file = Path(__file__).parent.parent.parent / "data" / "job_seeds.json"
    
    if not seed_file.exists():
        logger.error(f"Seed file not found: {seed_file}")
        return []
    
    try:
        with open(seed_file, "r") as f:
            data = json.load(f)
        
        companies = data.get("companies", [])
        logger.info(f"Loaded {len(companies)} companies from seed list")
        return companies
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing seed file: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading seed file: {e}")
        return []


def upsert_company_sources(db: DatabaseManager, companies: List[Dict[str, Any]]) -> Dict[str, int]:
    """Upsert company sources and return a mapping of board_root_url -> source_id."""
    url_to_id = {}
    
    for company in companies:
        company_name = company.get("company_name", "")
        ats_type = company.get("ats_type", "")
        board_root_url = company.get("board_root_url", "")
        
        if not all([company_name, ats_type, board_root_url]):
            logger.warning(f"Skipping incomplete company entry: {company}")
            continue
        
        source_id = db.upsert_ats_company_source(
            company_name=company_name,
            ats_type=ats_type,
            board_root_url=board_root_url,
        )
        
        if source_id:
            url_to_id[board_root_url] = source_id
            logger.debug(f"Upserted source: {company_name} (ID: {source_id})")
        else:
            logger.warning(f"Failed to upsert source: {company_name}")
    
    logger.info(f"Upserted {len(url_to_id)} company sources")
    return url_to_id


def ingest_jobs_for_source(
    db: DatabaseManager,
    company: Dict[str, Any],
    source_id: int,
) -> int:
    """Ingest jobs for a single company source.
    
    Returns:
        Number of jobs upserted
    """
    company_name = company.get("company_name", "")
    ats_type = company.get("ats_type", "")
    board_root_url = company.get("board_root_url", "")
    
    try:
        scraper = get_scraper(ats_type)
    except ValueError as e:
        logger.error(f"Unknown ATS type for {company_name}: {e}")
        return 0
    
    try:
        jobs = scraper.fetch_jobs(board_root_url, company_name)
    except Exception as e:
        logger.error(f"Error fetching jobs for {company_name}: {e}")
        return 0
    
    if not jobs:
        logger.info(f"No jobs found for {company_name}")
        return 0
    
    jobs_upserted = 0
    for job in jobs:
        job_id = db.upsert_job_post(
            source_type="ats",
            company_source_id=source_id,
            company_name=company_name,
            ats_type=ats_type,
            title=job.get("title", ""),
            url=job.get("url", ""),
            external_job_id=job.get("external_job_id"),
            location=job.get("location"),
            team=job.get("team"),
            employment_type=job.get("employment_type"),
            hash_value=job.get("hash"),
            raw_json=job.get("raw_json"),
        )
        
        if job_id:
            jobs_upserted += 1
    
    # Update last_success_at for the source
    if jobs_upserted > 0:
        db.update_ats_source_last_success(source_id)
    
    logger.info(f"Upserted {jobs_upserted} jobs for {company_name}")
    return jobs_upserted


def run_ingestion(ats_filter: str = None, company_filter: str = None):
    """Run the full ingestion pipeline.
    
    Args:
        ats_filter: Optional ATS type to filter (greenhouse or ashby)
        company_filter: Optional company name substring to filter
    """
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("Starting daily job ingestion")
    logger.info("=" * 60)
    
    # Initialize database
    try:
        db = DatabaseManager()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)
    
    # Load seed list
    companies = load_seed_list()
    if not companies:
        logger.error("No companies to process. Exiting.")
        sys.exit(1)
    
    # Apply filters
    if ats_filter:
        companies = [c for c in companies if c.get("ats_type") == ats_filter.lower()]
        logger.info(f"Filtered to {len(companies)} {ats_filter} companies")
    
    if company_filter:
        companies = [
            c for c in companies
            if company_filter.lower() in c.get("company_name", "").lower()
        ]
        logger.info(f"Filtered to {len(companies)} companies matching '{company_filter}'")
    
    # Upsert company sources
    url_to_id = upsert_company_sources(db, companies)
    
    # Ingest jobs for each company
    total_jobs = 0
    successful_sources = 0
    failed_sources = 0
    
    for company in companies:
        board_root_url = company.get("board_root_url", "")
        source_id = url_to_id.get(board_root_url)
        
        if not source_id:
            logger.warning(f"No source ID for {company.get('company_name')}, skipping")
            failed_sources += 1
            continue
        
        try:
            jobs_count = ingest_jobs_for_source(db, company, source_id)
            total_jobs += jobs_count
            successful_sources += 1
        except Exception as e:
            logger.error(f"Error processing {company.get('company_name')}: {e}")
            failed_sources += 1
        
        # Small delay to be nice to APIs
        time.sleep(0.5)
    
    elapsed = time.time() - start_time
    
    logger.info("=" * 60)
    logger.info("Ingestion complete")
    logger.info(f"  Companies processed: {successful_sources}/{len(companies)}")
    logger.info(f"  Total jobs upserted: {total_jobs}")
    logger.info(f"  Failed sources: {failed_sources}")
    logger.info(f"  Elapsed time: {elapsed:.1f}s")
    logger.info("=" * 60)


def main():
    """Main entrypoint with argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Daily job ingestion from ATS boards"
    )
    parser.add_argument(
        "--ats",
        choices=["greenhouse", "ashby"],
        help="Filter to specific ATS type",
    )
    parser.add_argument(
        "--company",
        help="Filter to companies matching this substring",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making changes",
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - no database changes will be made")
        companies = load_seed_list()
        
        if args.ats:
            companies = [c for c in companies if c.get("ats_type") == args.ats]
        if args.company:
            companies = [
                c for c in companies
                if args.company.lower() in c.get("company_name", "").lower()
            ]
        
        logger.info(f"Would process {len(companies)} companies:")
        for c in companies:
            logger.info(f"  - {c.get('company_name')} ({c.get('ats_type')})")
        return
    
    run_ingestion(ats_filter=args.ats, company_filter=args.company)


if __name__ == "__main__":
    main()
