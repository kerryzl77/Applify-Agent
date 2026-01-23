"""Scheduler Agent: manages follow-up queue and due dates."""

import datetime
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SchedulerAgent:
    """Manages follow-up scheduling and due dates."""
    
    def build_followup_queue(
        self,
        followups: Dict[str, List[Dict[str, Any]]],
        start_date: datetime.datetime = None,
    ) -> List[Dict[str, Any]]:
        """
        Build a queue of scheduled follow-ups with due dates.
        
        Args:
            followups: Output from DraftAgent.generate_followups()
            start_date: When the initial emails are sent (defaults to now)
        
        Returns:
            List of follow-up items with due_at timestamps
        """
        if start_date is None:
            start_date = datetime.datetime.utcnow()
        
        queue = []
        
        for draft_type, items in followups.items():
            for item in items:
                day = item.get('day', 3)
                due_at = start_date + datetime.timedelta(days=day)
                
                queue.append({
                    'draft_type': draft_type,
                    'day': day,
                    'due_at': due_at.isoformat(),
                    'status': 'pending',
                    'subject': item.get('subject', ''),
                    'body': item.get('body', ''),
                })
        
        # Sort by due date
        queue.sort(key=lambda x: x['due_at'])
        
        return queue
    
    def get_due_followups(
        self,
        queue: List[Dict[str, Any]],
        as_of: datetime.datetime = None,
    ) -> List[Dict[str, Any]]:
        """Get follow-ups that are due."""
        if as_of is None:
            as_of = datetime.datetime.utcnow()
        
        due = []
        for item in queue:
            if item.get('status') == 'pending':
                due_at = datetime.datetime.fromisoformat(item['due_at'])
                if due_at <= as_of:
                    due.append(item)
        
        return due
    
    def mark_followup_status(
        self,
        queue: List[Dict[str, Any]],
        draft_type: str,
        day: int,
        new_status: str,
    ) -> List[Dict[str, Any]]:
        """Update status of a specific follow-up."""
        for item in queue:
            if item['draft_type'] == draft_type and item['day'] == day:
                item['status'] = new_status
                break
        return queue
