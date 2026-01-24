import redis
import ssl
import json
import os
import logging
import datetime
from typing import Optional, Any, Dict
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)

class RedisManager:
    _instance = None
    _redis_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisManager, cls).__new__(cls)
            cls._instance._initialize_redis()
        return cls._instance

    def _initialize_redis(self):
        """Initialize Redis connection with retry logic."""
        try:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            
            # Handle Heroku Redis SSL configuration
            if redis_url.startswith('rediss://'):
                # Use SSL with proper certificate verification for Heroku Redis
                self._redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30,
                    ssl_cert_reqs=ssl.CERT_NONE,  # Disable SSL cert verification for Heroku Redis
                    ssl_check_hostname=False
                )
            else:
                # Standard Redis connection for local development
                self._redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
            
            # Test connection
            self._redis_client.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Redis connection failed: {str(e)}")
            self._redis_client = None

    def is_available(self) -> bool:
        """Check if Redis is available."""
        try:
            return self._redis_client is not None and self._redis_client.ping()
        except:
            return False

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis with JSON deserialization."""
        try:
            if not self.is_available():
                return None
            value = self._redis_client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {str(e)}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in Redis with JSON serialization and TTL."""
        try:
            if not self.is_available():
                return False
            serialized = json.dumps(value, default=str)
            return self._redis_client.setex(key, ttl, serialized)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        try:
            if not self.is_available():
                return False
            return bool(self._redis_client.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {str(e)}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            if not self.is_available():
                return False
            return bool(self._redis_client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {str(e)}")
            return False

    def generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate consistent cache key from arguments."""
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        
        key_string = ":".join(key_parts)
        # Hash long keys to avoid Redis key length limits
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{prefix}:{key_hash}"
        return key_string

    def cache_generated_content(self, content_type: str, content: str, 
                              job_data: Dict, user_id: str, ttl: int = 1800) -> str:
        """Cache generated content with smart key generation."""
        cache_key = self.generate_cache_key(
            "content",
            content_type,
            user_id,
            job_data.get('company_name', ''),
            job_data.get('job_title', '')
        )
        
        cache_data = {
            'content': content,
            'content_type': content_type,
            'job_data': job_data,
            'generated_at': str(datetime.datetime.now())
        }
        
        self.set(cache_key, cache_data, ttl)
        return cache_key

    def get_cached_content(self, content_type: str, job_data: Dict, user_id: str) -> Optional[Dict]:
        """Retrieve cached generated content."""
        cache_key = self.generate_cache_key(
            "content",
            content_type,
            user_id,
            job_data.get('company_name', ''),
            job_data.get('job_title', '')
        )
        return self.get(cache_key)

    def invalidate_user_cache(self, user_id: str):
        """Invalidate all cached data for a user."""
        try:
            if not self.is_available():
                return
            
            # Get all patterns that contain user_id
            patterns = [
                f"*:{user_id}:*",  # Original pattern
                f"*:{user_id}",    # Pattern like candidate_data:user_id
                f"{user_id}:*",    # Pattern like user_id:something
                f"*{user_id}*"     # Any pattern containing user_id
            ]
            
            all_keys = []
            for pattern in patterns:
                keys = self._redis_client.keys(pattern)
                all_keys.extend(keys)
            
            # Remove duplicates
            unique_keys = list(set(all_keys))
            
            if unique_keys:
                self._redis_client.delete(*unique_keys)
                logger.info(f"Invalidated {len(unique_keys)} cache keys for user {user_id}: {unique_keys}")
        except Exception as e:
            logger.error(f"Error invalidating cache for user {user_id}: {str(e)}")

    def scan_keys(self, pattern: str) -> list:
        """Scan for keys matching pattern. Returns list of key names."""
        try:
            if not self.is_available():
                return []
            return self._redis_client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis SCAN error for pattern {pattern}: {str(e)}")
            return []


def cache_result(prefix: str, ttl: int = 3600):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            redis_manager = RedisManager()
            
            # Generate cache key from function name and arguments
            cache_key = redis_manager.generate_cache_key(prefix, func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_result = redis_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            redis_manager.set(cache_key, result, ttl)
            logger.debug(f"Cache miss, stored result for {func.__name__}")
            return result
        
        return wrapper
    return decorator