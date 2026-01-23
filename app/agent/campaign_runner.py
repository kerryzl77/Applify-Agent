"""Campaign Runner: orchestrates the multi-step campaign workflow."""

import datetime
import logging
import threading
from typing import Any, Dict, Optional

from database.db_manager import DatabaseManager
from app.agent.research_agent import ResearchAgent
from app.agent.evidence_agent import EvidenceAgent
from app.agent.draft_agent import DraftAgent
from app.agent.scheduler_agent import SchedulerAgent
from app.utils.text import normalize_job_data

logger = logging.getLogger(__name__)


class CampaignRunner:
    """
    Orchestrates the campaign workflow with durable state.
    
    Phases:
        idle -> research -> evidence -> drafts -> waiting_user -> finalize -> done
        
    Steps can be run in different modes:
        - full: run all steps (research -> evidence -> drafts)
        - research_only: just research step
        - draft_only: just draft step (requires selected_contacts)
    """
    
    def __init__(self):
        self.db = DatabaseManager()
        self.research_agent = ResearchAgent()
        self.evidence_agent = EvidenceAgent()
        self.draft_agent = DraftAgent()
        self.scheduler_agent = SchedulerAgent()
    
    def run_async(
        self,
        campaign_id: int,
        user_id: str,
        mode: str = "full",
    ) -> str:
        """Start campaign workflow in background thread. Returns run_id."""
        run_id = f"{campaign_id}_{datetime.datetime.utcnow().timestamp()}"
        
        thread = threading.Thread(
            target=self._run_workflow,
            args=(campaign_id, user_id, mode, run_id),
            daemon=True
        )
        thread.start()
        
        return run_id
    
    def _run_workflow(
        self,
        campaign_id: int,
        user_id: str,
        mode: str,
        run_id: str,
    ):
        """Main workflow execution (runs in background thread)."""
        try:
            # Initialize state if needed
            self._ensure_state_initialized(campaign_id, user_id)
            
            # Get campaign and job data
            campaign = self.db.get_job_campaign_with_job(campaign_id, user_id)
            if not campaign:
                self._emit_error(campaign_id, user_id, "Campaign not found")
                return
            
            state = campaign.get('state', {})
            job_data = self._get_job_data(campaign)
            candidate_data = self.db.get_candidate_data(user_id) or {}
            
            # Emit workflow start
            self._emit_trace(campaign_id, user_id, {
                'type': 'workflow_start',
                'mode': mode,
                'run_id': run_id,
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
            
            # Update phase
            self._update_phase(campaign_id, user_id, 'running')
            
            # Execute steps based on mode
            if mode in ('full', 'research_only'):
                self._run_research_step(campaign_id, user_id, job_data, state)
            
            # Reload state after research
            campaign = self.db.get_job_campaign_with_job(campaign_id, user_id)
            state = campaign.get('state', {})
            
            if mode == 'full':
                self._run_evidence_step(campaign_id, user_id, job_data, candidate_data, state)
                
                # Reload state
                campaign = self.db.get_job_campaign_with_job(campaign_id, user_id)
                state = campaign.get('state', {})
            
            if mode in ('full', 'draft_only'):
                # For draft_only, we need selected_contacts
                selected_contacts = state.get('selected_contacts', {})
                if not selected_contacts and mode == 'draft_only':
                    self._emit_error(campaign_id, user_id, "No contacts selected for draft generation")
                    return
                
                # If full mode and no contacts selected yet, wait for user
                if mode == 'full' and not selected_contacts:
                    self._update_phase(campaign_id, user_id, 'waiting_user')
                    self._emit_trace(campaign_id, user_id, {
                        'type': 'waiting_user',
                        'need': 'select_contacts',
                        'message': 'Please select contacts for outreach',
                        'timestamp': datetime.datetime.utcnow().isoformat()
                    })
                    return
                
                self._run_draft_step(campaign_id, user_id, job_data, candidate_data, state)
            
            # Final state
            self._update_phase(campaign_id, user_id, 'waiting_user')
            self._emit_trace(campaign_id, user_id, {
                'type': 'workflow_complete',
                'mode': mode,
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.exception(f"Campaign workflow error: {e}")
            self._emit_error(campaign_id, user_id, str(e))
    
    def _ensure_state_initialized(self, campaign_id: int, user_id: str):
        """Initialize campaign state structure if empty."""
        campaign = self.db.get_job_campaign(campaign_id, user_id)
        if not campaign:
            return
        
        state = campaign.get('state', {})
        if not state.get('steps'):
            initial_state = {
                'phase': 'idle',
                'steps': {
                    'research': {'status': 'queued'},
                    'evidence': {'status': 'queued'},
                    'drafts': {'status': 'queued'},
                    'schedule': {'status': 'queued'},
                    'gmail': {'status': 'queued'},
                },
                'selected_contacts': {},
                'feedback': {'global': [], 'draft_specific': {}},
                'artifacts': {},
                'trace': [],
                'version': 1
            }
            self.db.update_job_campaign_state(campaign_id, user_id, initial_state, merge=False)
    
    def _get_job_data(self, campaign: Dict[str, Any]) -> Dict[str, Any]:
        """Extract job data from campaign."""
        job = campaign.get('job', {})
        job_post = self.db.get_job_post_with_jd(campaign.get('job_post_id'))
        
        job_data = {
            'job_title': job.get('title', ''),
            'company_name': job.get('company_name', ''),
            'location': job.get('location', ''),
            'team': job.get('team', ''),
            'employment_type': job.get('employment_type', ''),
            'url': job.get('url', ''),
            'job_description': job_post.get('raw_json', {}).get('job_description', '') if job_post else '',
            'requirements': job_post.get('raw_json', {}).get('requirements', '') if job_post else '',
        }
        return normalize_job_data(job_data)
    
    def _run_research_step(
        self,
        campaign_id: int,
        user_id: str,
        job_data: Dict[str, Any],
        state: Dict[str, Any],
    ):
        """Execute research step."""
        self._update_step_status(campaign_id, user_id, 'research', 'running')
        self._emit_trace(campaign_id, user_id, {
            'type': 'step_start',
            'step': 'research',
            'timestamp': datetime.datetime.utcnow().isoformat()
        })
        
        try:
            contacts = self.research_agent.discover_contacts(
                company_name=job_data.get('company_name', ''),
                job_title=job_data.get('job_title', ''),
                team=job_data.get('team'),
                location=job_data.get('location'),
                emit_trace=lambda e: self._emit_trace(campaign_id, user_id, e)
            )
            
            # Store contacts in artifacts
            self.db.update_job_campaign_state(campaign_id, user_id, {
                'artifacts': {'contacts': contacts}
            })
            
            self._update_step_status(campaign_id, user_id, 'research', 'done')
            self._emit_trace(campaign_id, user_id, {
                'type': 'step_done',
                'step': 'research',
                'summary': f'Found {len(contacts)} contacts',
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
            self._emit_trace(campaign_id, user_id, {
                'type': 'artifact',
                'artifact_type': 'contacts',
                'count': len(contacts),
                'data': contacts,
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.exception(f"Research step error: {e}")
            self._update_step_status(campaign_id, user_id, 'research', 'error')
            self._emit_trace(campaign_id, user_id, {
                'type': 'step_error',
                'step': 'research',
                'error': str(e),
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
    
    def _run_evidence_step(
        self,
        campaign_id: int,
        user_id: str,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        state: Dict[str, Any],
    ):
        """Execute evidence step."""
        self._update_step_status(campaign_id, user_id, 'evidence', 'running')
        self._emit_trace(campaign_id, user_id, {
            'type': 'step_start',
            'step': 'evidence',
            'timestamp': datetime.datetime.utcnow().isoformat()
        })
        
        try:
            evidence_pack = self.evidence_agent.build_evidence_pack(
                job_data=job_data,
                candidate_data=candidate_data,
                emit_trace=lambda e: self._emit_trace(campaign_id, user_id, e)
            )
            
            # Store evidence pack
            self.db.update_job_campaign_state(campaign_id, user_id, {
                'artifacts': {'evidence_pack': evidence_pack}
            })
            
            self._update_step_status(campaign_id, user_id, 'evidence', 'done')
            self._emit_trace(campaign_id, user_id, {
                'type': 'step_done',
                'step': 'evidence',
                'summary': f'Generated {len(evidence_pack.get("why_me_bullets", []))} evidence bullets',
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
            self._emit_trace(campaign_id, user_id, {
                'type': 'artifact',
                'artifact_type': 'evidence_pack',
                'data': evidence_pack,
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.exception(f"Evidence step error: {e}")
            self._update_step_status(campaign_id, user_id, 'evidence', 'error')
            self._emit_trace(campaign_id, user_id, {
                'type': 'step_error',
                'step': 'evidence',
                'error': str(e),
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
    
    def _run_draft_step(
        self,
        campaign_id: int,
        user_id: str,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        state: Dict[str, Any],
    ):
        """Execute draft generation step."""
        self._update_step_status(campaign_id, user_id, 'drafts', 'running')
        self._emit_trace(campaign_id, user_id, {
            'type': 'step_start',
            'step': 'drafts',
            'timestamp': datetime.datetime.utcnow().isoformat()
        })
        
        try:
            selected_contacts = state.get('selected_contacts', {})
            evidence_pack = state.get('artifacts', {}).get('evidence_pack', {})
            feedback = state.get('feedback', {})
            
            # Generate drafts
            drafts = self.draft_agent.generate_drafts(
                job_data=job_data,
                candidate_data=candidate_data,
                selected_contacts=selected_contacts,
                evidence_pack=evidence_pack,
                feedback=feedback,
                emit_trace=lambda e: self._emit_trace(campaign_id, user_id, e)
            )
            
            # Generate follow-ups
            followups = self.draft_agent.generate_followups(
                original_drafts=drafts,
                job_data=job_data,
                candidate_data=candidate_data,
                emit_trace=lambda e: self._emit_trace(campaign_id, user_id, e)
            )
            
            # Build follow-up queue with due dates
            followup_queue = self.scheduler_agent.build_followup_queue(followups)
            
            # Store drafts and followups
            self.db.update_job_campaign_state(campaign_id, user_id, {
                'artifacts': {
                    'drafts': drafts,
                    'followups': followup_queue
                }
            })
            
            self._update_step_status(campaign_id, user_id, 'drafts', 'done')
            self._update_step_status(campaign_id, user_id, 'schedule', 'done')
            
            self._emit_trace(campaign_id, user_id, {
                'type': 'step_done',
                'step': 'drafts',
                'summary': f'Generated {len(drafts)} drafts and {len(followup_queue)} follow-ups',
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
            self._emit_trace(campaign_id, user_id, {
                'type': 'artifact',
                'artifact_type': 'drafts',
                'data': drafts,
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
            self._emit_trace(campaign_id, user_id, {
                'type': 'artifact',
                'artifact_type': 'followups',
                'data': followup_queue,
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.exception(f"Draft step error: {e}")
            self._update_step_status(campaign_id, user_id, 'drafts', 'error')
            self._emit_trace(campaign_id, user_id, {
                'type': 'step_error',
                'step': 'drafts',
                'error': str(e),
                'timestamp': datetime.datetime.utcnow().isoformat()
            })
    
    def _update_phase(self, campaign_id: int, user_id: str, phase: str):
        """Update campaign phase."""
        self.db.update_job_campaign_state(campaign_id, user_id, {'phase': phase})
    
    def _update_step_status(self, campaign_id: int, user_id: str, step: str, status: str):
        """Update a specific step's status."""
        self.db.update_job_campaign_state(campaign_id, user_id, {
            'steps': {step: {'status': status, 'updated_at': datetime.datetime.utcnow().isoformat()}}
        })
    
    def _emit_trace(self, campaign_id: int, user_id: str, event: Dict[str, Any]):
        """Emit a trace event."""
        if 'timestamp' not in event:
            event['timestamp'] = datetime.datetime.utcnow().isoformat()
        self.db.append_job_campaign_trace(campaign_id, user_id, event)
    
    def _emit_error(self, campaign_id: int, user_id: str, message: str):
        """Emit an error and update phase."""
        self._update_phase(campaign_id, user_id, 'error')
        self._emit_trace(campaign_id, user_id, {
            'type': 'error',
            'message': message,
            'timestamp': datetime.datetime.utcnow().isoformat()
        })
