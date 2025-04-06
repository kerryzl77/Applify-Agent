import os
from redis import Redis

# Redis configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Create Redis connection
redis_conn = Redis.from_url(REDIS_URL)

# RQ configuration
QUEUES = ['default']
DEFAULT_RESULT_TTL = 3600  # 1 hour
DEFAULT_TIMEOUT = 1800     # 30 minutes 