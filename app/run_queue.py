"""Redis-backed queue for durable application runs."""

from __future__ import annotations

import json
import logging
from typing import Optional

from app.config import get_settings
from app.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class RunQueue:
    """Queue run IDs in Redis while Postgres remains the durable record."""

    def __init__(self, redis_manager: Optional[RedisManager] = None):
        self.settings = get_settings()
        self.redis = redis_manager or RedisManager()
        self.queue_name = self.settings.run_queue_name

    def enqueue(self, run_id: str) -> bool:
        if not self.redis.is_available():
            logger.error("Run queue unavailable: Redis is not connected")
            return False
        payload = json.dumps({"run_id": run_id})
        return bool(self.redis._redis_client.lpush(self.queue_name, payload))

    def dequeue(self, timeout: Optional[int] = None) -> Optional[str]:
        if not self.redis.is_available():
            return None
        timeout = timeout if timeout is not None else self.settings.worker_poll_timeout_seconds
        item = self.redis._redis_client.brpop(self.queue_name, timeout=timeout)
        if not item:
            return None
        _, payload = item
        message = json.loads(payload)
        return message.get("run_id")
