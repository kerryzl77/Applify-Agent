"""Background worker entrypoint for durable application runs."""

from __future__ import annotations

import logging
import sys
import time

from app.run_dispatcher import RunDispatcher
from app.run_queue import RunQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main():
    queue = RunQueue()
    dispatcher = RunDispatcher()

    logger.info("Application run worker started")
    while True:
        try:
            run_id = queue.dequeue()
            if not run_id:
                continue
            logger.info("Dequeued application run %s", run_id)
            dispatcher.execute(run_id)
        except Exception:
            logger.exception("Worker loop error")
            time.sleep(2)


if __name__ == "__main__":
    main()
