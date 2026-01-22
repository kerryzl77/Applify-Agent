"""Jobs ingestion module for ATS job boards."""

from app.jobs.ats_scrapers import GreenhouseScraper, AshbyScraper

__all__ = ["GreenhouseScraper", "AshbyScraper"]
