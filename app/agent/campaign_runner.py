"""Campaign runner backed by durable runs and a worker queue."""

from __future__ import annotations

import datetime
import logging
import threading
import time
from typing import Any, Dict

from app.agent.draft_agent import DraftAgent
from app.agent.evidence_agent import EvidenceAgent
from app.agent.research_agent import ResearchAgent
from app.agent.scheduler_agent import SchedulerAgent
from app.run_queue import RunQueue
from app.utils.text import normalize_job_data
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class CampaignRunner:
    """Orchestrates campaign workflows using Postgres-backed run records."""

    STEP_ORDER = {
        "research": 1,
        "evidence": 2,
        "drafts": 3,
        "schedule": 4,
        "gmail": 5,
    }

    def __init__(self):
        self.db = DatabaseManager()
        self.queue = RunQueue()
        self.research_agent = ResearchAgent()
        self.evidence_agent = EvidenceAgent()
        self.draft_agent = DraftAgent()
        self.scheduler_agent = SchedulerAgent()

    def run_async(self, campaign_id: int, user_id: str, mode: str = "full") -> str:
        """Create a durable run and enqueue it for worker execution."""
        self._ensure_state_initialized(campaign_id, user_id)
        run_id = self.db.create_application_run(
            user_id=user_id,
            run_type="campaign",
            source_type="job_campaign",
            source_id=campaign_id,
            request_payload={"campaign_id": campaign_id, "mode": mode},
        )
        if not run_id:
            raise RuntimeError("Failed to create durable campaign run")

        for step_key, position in self.STEP_ORDER.items():
            self.db.upsert_run_step(run_id, step_key, position, status="queued")

        self.db.update_job_campaign_state(
            campaign_id,
            user_id,
            {
                "phase": "queued",
                "latest_run_id": run_id,
                "trace": [],
            },
        )
        self._emit_trace(campaign_id, user_id, {"type": "workflow_queued", "mode": mode, "run_id": run_id})

        if self.queue.enqueue(run_id):
            return run_id

        logger.warning("Run queue unavailable; falling back to inline execution for run %s", run_id)
        self._emit_trace(campaign_id, user_id, {"type": "workflow_inline_fallback", "run_id": run_id})
        self._start_inline_fallback(run_id, delay_seconds=0.0)
        return run_id

    def execute_run(self, run_id: str):
        """Execute a durable campaign run inside the worker process."""
        run = self.db.get_application_run(run_id)
        if not run:
            logger.error("Campaign run %s not found", run_id)
            return

        campaign_id = int(run["source_id"])
        user_id = run["user_id"]
        mode = (run.get("request_payload") or {}).get("mode", "full")

        try:
            if not self.db.claim_application_run(run_id):
                logger.info("Run %s already claimed or no longer queued; skipping duplicate execution", run_id)
                return
            self._ensure_state_initialized(campaign_id, user_id)
            self.db.update_job_campaign_state(campaign_id, user_id, {"trace": [], "phase": "running"})

            campaign = self.db.get_job_campaign_with_job(campaign_id, user_id)
            if not campaign:
                self.db.update_application_run(run_id, status="failed", error="Campaign not found", completed=True)
                self._emit_error(campaign_id, user_id, "Campaign not found")
                return

            state = campaign.get("state", {})
            job_data = self._get_job_data(campaign)
            candidate_data = self.db.get_candidate_data(user_id) or {}

            self._emit_trace(campaign_id, user_id, {"type": "workflow_start", "mode": mode, "run_id": run_id})

            if mode in ("full", "research_only"):
                self._run_research_step(run, campaign_id, user_id, job_data)
            else:
                self._mark_step_skipped(run_id, campaign_id, user_id, "research")

            campaign = self.db.get_job_campaign_with_job(campaign_id, user_id)
            state = campaign.get("state", {})

            if mode == "full":
                self._run_evidence_step(run, campaign_id, user_id, job_data, candidate_data)
            else:
                self._mark_step_skipped(run_id, campaign_id, user_id, "evidence")

            campaign = self.db.get_job_campaign_with_job(campaign_id, user_id)
            state = campaign.get("state", {})

            if mode in ("full", "draft_only"):
                selected_contacts = state.get("selected_contacts", {})
                if not selected_contacts and mode == "draft_only":
                    self._mark_step_failed(
                        run_id,
                        campaign_id,
                        user_id,
                        "drafts",
                        "No contacts selected for draft generation",
                    )
                    self.db.update_application_run(
                        run_id,
                        status="failed",
                        error="No contacts selected for draft generation",
                        completed=True,
                    )
                    self._emit_error(campaign_id, user_id, "No contacts selected for draft generation")
                    return

                if mode == "full" and not selected_contacts:
                    self._update_phase(campaign_id, user_id, "waiting_user")
                    self.db.update_application_run(
                        run_id,
                        status="waiting_user",
                        result_payload_patch={"waiting_for": "selected_contacts"},
                    )
                    self._update_step_status(run_id, campaign_id, user_id, "drafts", "waiting_user")
                    self._emit_trace(
                        campaign_id,
                        user_id,
                        {
                            "type": "waiting_user",
                            "need": "select_contacts",
                            "message": "Please select contacts for outreach",
                        },
                    )
                    return

                self._run_draft_step(run, campaign_id, user_id, job_data, candidate_data, state)
            else:
                self._mark_step_skipped(run_id, campaign_id, user_id, "drafts")
                self._mark_step_skipped(run_id, campaign_id, user_id, "schedule")

            self._update_phase(campaign_id, user_id, "waiting_user")
            self.db.update_application_run(
                run_id,
                status="completed",
                result_payload_patch={"mode": mode, "terminal_phase": "waiting_user"},
                completed=True,
            )
            self._mark_step_skipped(run_id, campaign_id, user_id, "gmail")
            self._emit_trace(campaign_id, user_id, {"type": "workflow_complete", "mode": mode, "run_id": run_id})
        except Exception as exc:
            logger.exception("Campaign workflow error: %s", exc)
            self.db.update_application_run(run_id, status="failed", error=str(exc), completed=True)
            self._emit_error(campaign_id, user_id, str(exc))

    def _start_inline_fallback(self, run_id: str, delay_seconds: float):
        def _runner():
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            self.execute_run(run_id)

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()

    def _ensure_state_initialized(self, campaign_id: int, user_id: str):
        campaign = self.db.get_job_campaign(campaign_id, user_id)
        if not campaign:
            return

        state = campaign.get("state", {})
        if state.get("steps"):
            return

        initial_state = {
            "phase": "idle",
            "steps": {
                "research": {"status": "queued"},
                "evidence": {"status": "queued"},
                "drafts": {"status": "queued"},
                "schedule": {"status": "queued"},
                "gmail": {"status": "queued"},
            },
            "selected_contacts": {},
            "feedback": {"global": [], "draft_specific": {}},
            "artifacts": {},
            "trace": [],
            "version": 2,
        }
        self.db.update_job_campaign_state(campaign_id, user_id, initial_state, merge=False)

    def _get_job_data(self, campaign: Dict[str, Any]) -> Dict[str, Any]:
        job = campaign.get("job", {})
        job_post = self.db.get_job_post_with_jd(campaign.get("job_post_id"))
        return normalize_job_data(
            {
                "job_title": job.get("title", ""),
                "company_name": job.get("company_name", ""),
                "location": job.get("location", ""),
                "team": job.get("team", ""),
                "employment_type": job.get("employment_type", ""),
                "url": job.get("url", ""),
                "job_description": job_post.get("raw_json", {}).get("job_description", "") if job_post else "",
                "requirements": job_post.get("raw_json", {}).get("requirements", "") if job_post else "",
            }
        )

    def _run_research_step(self, run: dict, campaign_id: int, user_id: str, job_data: Dict[str, Any]):
        run_id = run["id"]
        self._update_step_status(run_id, campaign_id, user_id, "research", "running", started=True)
        self._emit_trace(campaign_id, user_id, {"type": "step_start", "step": "research", "run_id": run_id})
        try:
            contacts = self.research_agent.discover_contacts(
                company_name=job_data.get("company_name", ""),
                job_title=job_data.get("job_title", ""),
                team=job_data.get("team"),
                location=job_data.get("location"),
                emit_trace=lambda event: self._emit_trace(campaign_id, user_id, event),
            )
            artifact_id = self._persist_json_artifact(
                run_id=run_id,
                user_id=user_id,
                campaign_id=campaign_id,
                step_key="research",
                artifact_key="contacts",
                artifact_type="contacts",
                payload=contacts,
            )
            self._update_step_status(
                run_id,
                campaign_id,
                user_id,
                "research",
                "done",
                completed=True,
                output_payload={"artifact_id": artifact_id, "count": len(contacts)},
            )
            self.db.update_application_run(run_id, result_payload_patch={"contacts_count": len(contacts)})
            self._emit_trace(campaign_id, user_id, {"type": "step_done", "step": "research", "summary": f"Found {len(contacts)} contacts", "run_id": run_id})
            self._emit_trace(campaign_id, user_id, {"type": "artifact", "artifact_type": "contacts", "data": contacts, "run_id": run_id})
        except Exception as exc:
            self._mark_step_failed(run_id, campaign_id, user_id, "research", str(exc))
            raise

    def _run_evidence_step(
        self,
        run: dict,
        campaign_id: int,
        user_id: str,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
    ):
        run_id = run["id"]
        self._update_step_status(run_id, campaign_id, user_id, "evidence", "running", started=True)
        self._emit_trace(campaign_id, user_id, {"type": "step_start", "step": "evidence", "run_id": run_id})
        try:
            evidence_pack = self.evidence_agent.build_evidence_pack(
                job_data=job_data,
                candidate_data=candidate_data,
                emit_trace=lambda event: self._emit_trace(campaign_id, user_id, event),
            )
            artifact_id = self._persist_json_artifact(
                run_id=run_id,
                user_id=user_id,
                campaign_id=campaign_id,
                step_key="evidence",
                artifact_key="evidence_pack",
                artifact_type="evidence_pack",
                payload=evidence_pack,
            )
            self._update_step_status(
                run_id,
                campaign_id,
                user_id,
                "evidence",
                "done",
                completed=True,
                output_payload={"artifact_id": artifact_id},
            )
            self._emit_trace(
                campaign_id,
                user_id,
                {
                    "type": "step_done",
                    "step": "evidence",
                    "summary": f"Generated {len(evidence_pack.get('why_me_bullets', []))} evidence bullets",
                    "run_id": run_id,
                },
            )
            self._emit_trace(campaign_id, user_id, {"type": "artifact", "artifact_type": "evidence_pack", "data": evidence_pack, "run_id": run_id})
        except Exception as exc:
            self._mark_step_failed(run_id, campaign_id, user_id, "evidence", str(exc))
            raise

    def _run_draft_step(
        self,
        run: dict,
        campaign_id: int,
        user_id: str,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        state: Dict[str, Any],
    ):
        run_id = run["id"]
        self._update_step_status(run_id, campaign_id, user_id, "drafts", "running", started=True)
        self._emit_trace(campaign_id, user_id, {"type": "step_start", "step": "drafts", "run_id": run_id})
        try:
            selected_contacts = state.get("selected_contacts", {})
            evidence_pack = state.get("artifacts", {}).get("evidence_pack", {})
            feedback = state.get("feedback", {})

            drafts = self.draft_agent.generate_drafts(
                job_data=job_data,
                candidate_data=candidate_data,
                selected_contacts=selected_contacts,
                evidence_pack=evidence_pack,
                feedback=feedback,
                emit_trace=lambda event: self._emit_trace(campaign_id, user_id, event),
            )
            followups = self.draft_agent.generate_followups(
                original_drafts=drafts,
                job_data=job_data,
                candidate_data=candidate_data,
                emit_trace=lambda event: self._emit_trace(campaign_id, user_id, event),
            )
            followup_queue = self.scheduler_agent.build_followup_queue(followups)

            drafts_artifact_id = self._persist_json_artifact(
                run_id=run_id,
                user_id=user_id,
                campaign_id=campaign_id,
                step_key="drafts",
                artifact_key="drafts",
                artifact_type="drafts",
                payload=drafts,
            )
            followups_artifact_id = self._persist_json_artifact(
                run_id=run_id,
                user_id=user_id,
                campaign_id=campaign_id,
                step_key="schedule",
                artifact_key="followups",
                artifact_type="followups",
                payload=followup_queue,
            )
            self._update_step_status(
                run_id,
                campaign_id,
                user_id,
                "drafts",
                "done",
                completed=True,
                output_payload={"artifact_id": drafts_artifact_id, "count": len(drafts)},
            )
            self._update_step_status(
                run_id,
                campaign_id,
                user_id,
                "schedule",
                "done",
                completed=True,
                output_payload={"artifact_id": followups_artifact_id, "count": len(followup_queue)},
            )
            self._emit_trace(
                campaign_id,
                user_id,
                {
                    "type": "step_done",
                    "step": "drafts",
                    "summary": f"Generated {len(drafts)} drafts and {len(followup_queue)} follow-ups",
                    "run_id": run_id,
                },
            )
            self._emit_trace(campaign_id, user_id, {"type": "artifact", "artifact_type": "drafts", "data": drafts, "run_id": run_id})
            self._emit_trace(campaign_id, user_id, {"type": "artifact", "artifact_type": "followups", "data": followup_queue, "run_id": run_id})
        except Exception as exc:
            self._mark_step_failed(run_id, campaign_id, user_id, "drafts", str(exc))
            self._mark_step_failed(run_id, campaign_id, user_id, "schedule", str(exc))
            raise

    def _persist_json_artifact(self, run_id: str, user_id: str, campaign_id: int, step_key: str, artifact_key: str, artifact_type: str, payload: Any) -> int | None:
        artifact_id = self.db.create_artifact(
            user_id=user_id,
            run_id=run_id,
            source_type="job_campaign",
            source_id=campaign_id,
            step_key=step_key,
            artifact_key=artifact_key,
            artifact_type=artifact_type,
            kind="json",
            payload_json=payload,
            metadata={"run_id": run_id},
        )
        self.db.update_job_campaign_state(campaign_id, user_id, {"artifacts": {artifact_key: payload}})
        return artifact_id

    def _update_phase(self, campaign_id: int, user_id: str, phase: str):
        self.db.update_job_campaign_state(campaign_id, user_id, {"phase": phase})

    def _update_step_status(
        self,
        run_id: str,
        campaign_id: int,
        user_id: str,
        step: str,
        status: str,
        started: bool = False,
        completed: bool = False,
        output_payload: dict | None = None,
    ):
        campaign_status = status if status != "done" else "done"
        self.db.update_job_campaign_state(
            campaign_id,
            user_id,
            {
                "steps": {
                    step: {
                        "status": campaign_status,
                        "updated_at": datetime.datetime.utcnow().isoformat(),
                    }
                }
            },
        )
        step_status = "completed" if status == "done" else status
        self.db.update_run_step(
            run_id,
            step,
            step_status,
            output_payload=output_payload,
            started=started,
            completed=completed,
        )

    def _mark_step_skipped(self, run_id: str, campaign_id: int, user_id: str, step_key: str):
        self.db.update_job_campaign_state(
            campaign_id,
            user_id,
            {
                "steps": {
                    step_key: {
                        "status": "skipped",
                        "updated_at": datetime.datetime.utcnow().isoformat(),
                    }
                }
            },
        )
        self.db.update_run_step(run_id, step_key, "skipped", completed=True)

    def _mark_step_failed(self, run_id: str, campaign_id: int, user_id: str, step_key: str, error: str):
        self.db.update_job_campaign_state(
            campaign_id,
            user_id,
            {
                "steps": {
                    step_key: {
                        "status": "failed",
                        "updated_at": datetime.datetime.utcnow().isoformat(),
                    }
                }
            },
        )
        self.db.update_run_step(run_id, step_key, "failed", error=error, completed=True)

    def _emit_trace(self, campaign_id: int, user_id: str, event: Dict[str, Any]):
        if "timestamp" not in event:
            event["timestamp"] = datetime.datetime.utcnow().isoformat()
        self.db.append_job_campaign_trace(campaign_id, user_id, event)

    def _emit_error(self, campaign_id: int, user_id: str, message: str):
        self._update_phase(campaign_id, user_id, "error")
        self._emit_trace(campaign_id, user_id, {"type": "error", "message": message})
