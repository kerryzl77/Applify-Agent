"""Dispatch durable application runs to the appropriate executor."""

from __future__ import annotations

import logging

from app.agent.campaign_runner import CampaignRunner
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class RunDispatcher:
    """Look up a durable run and execute it with the correct handler."""

    def __init__(self):
        self.db = DatabaseManager()
        self.campaign_runner = CampaignRunner()

    def execute(self, run_id: str) -> bool:
        run = self.db.get_application_run(run_id)
        if not run:
            logger.error("Run %s not found", run_id)
            return False

        if run["run_type"] == "campaign":
            self.campaign_runner.execute_run(run_id)
            return True

        self.db.update_application_run(
            run_id,
            status="failed",
            error=f"Unsupported run type: {run['run_type']}",
            completed=True,
        )
        logger.error("Unsupported run type %s for run %s", run["run_type"], run_id)
        return False
