"""SSE helpers for campaign event streaming."""

import asyncio
import json
import logging
from typing import AsyncGenerator

from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


async def generate_campaign_events(
    campaign_id: int,
    user_id: str,
    db: DatabaseManager,
    start_index: int = 0,
    poll_interval: float = 0.5,
    max_idle_seconds: int = 300,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events by polling the database for new trace entries.
    
    This approach is multi-worker safe since all state is in Postgres.
    """
    last_index = max(0, int(start_index or 0))
    idle_count = 0
    max_idle = int(max_idle_seconds / poll_interval)
    
    while idle_count < max_idle:
        try:
            new_events, phase, total_length = db.get_campaign_trace_from_index(
                campaign_id,
                user_id,
                last_index,
            )
            
            if new_events is None:
                # Campaign not found
                yield f"data: {json.dumps({'type': 'error', 'message': 'Campaign not found'})}\n\n"
                break

            if total_length is not None and last_index > total_length:
                last_index = total_length
                new_events = []
            
            if new_events:
                for event in new_events:
                    yield f"data: {json.dumps(event)}\n\n"
                last_index += len(new_events)
                idle_count = 0
                
                # Check if workflow completed
                if phase in ('done', 'error'):
                    yield f"data: {json.dumps({'type': 'workflow_complete', 'phase': phase})}\n\n"
                    break
            else:
                idle_count += 1
                
                # Send heartbeat every 10 seconds
                if idle_count % 20 == 0:
                    yield f"data: {json.dumps({'type': 'heartbeat', 'phase': phase})}\n\n"
            
            await asyncio.sleep(poll_interval)
            
        except Exception as e:
            logger.error(f"Error in SSE generator: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            break
    
    yield f"data: {json.dumps({'type': 'timeout'})}\n\n"
