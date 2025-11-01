"""
SearXNG Search Wrapper
Production-ready search using public SearXNG instances with fallback and retry logic.
"""
import os
import logging
import time
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from collections import OrderedDict
from threading import Lock
import requests

logger = logging.getLogger(__name__)

# Public SearXNG instances (updated for better reliability)
# NOTE: Public instances may have rate limits or availability issues.
# For production (1k+ queries/day), deploy your own SearXNG instance.
# See: https://github.com/searxng/searxng-docker
DEFAULT_SEARXNG_INSTANCES = [
    "https://searx.tiekoetter.com",
    "https://searx.be",
    "https://search.ononoki.org",
    "https://searx.fmac.xyz",
    "https://search.blitzw.in",
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class LRUCache:
    """Thread-safe LRU cache with TTL support."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 600):
        self.cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.lock = Lock()

    def _make_key(self, query: str, language: str, time_range: Optional[str]) -> str:
        """Generate cache key from search parameters."""
        parts = [query.lower().strip(), language, time_range or ""]
        return hashlib.md5("|".join(parts).encode()).hexdigest()

    def get(self, query: str, language: str, time_range: Optional[str]) -> Optional[List[Dict[str, Any]]]:
        """Get cached results if valid."""
        key = self._make_key(query, language, time_range)
        with self.lock:
            if key in self.cache:
                results, timestamp = self.cache[key]
                # Check if expired
                if time.time() - timestamp < self.ttl_seconds:
                    # Move to end (LRU)
                    self.cache.move_to_end(key)
                    logger.debug(f"Cache HIT for query: {query[:50]}")
                    return results
                else:
                    # Expired
                    del self.cache[key]
                    logger.debug(f"Cache EXPIRED for query: {query[:50]}")
            return None

    def set(self, query: str, language: str, time_range: Optional[str], results: List[Dict[str, Any]]) -> None:
        """Cache search results."""
        key = self._make_key(query, language, time_range)
        with self.lock:
            # Evict oldest if at capacity
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
            self.cache[key] = (results, time.time())
            logger.debug(f"Cache SET for query: {query[:50]}")


class SearXNGSearch:
    """
    Production-ready SearXNG search client with:
    - Multiple instance fallback
    - Retry logic with exponential backoff
    - Request timeout handling
    - LRU caching with TTL
    - Detailed logging
    """

    def __init__(
        self,
        instances: Optional[List[str]] = None,
        timeout: int = 15,
        max_retries: int = 2,
        enable_cache: bool = True,
        cache_size: int = 100,
        cache_ttl: int = 600,
    ):
        """
        Initialize SearXNG search client.

        Args:
            instances: List of SearXNG instance URLs (uses defaults if None)
            timeout: Request timeout in seconds
            max_retries: Number of retry attempts per instance
            enable_cache: Enable LRU caching (default: True)
            cache_size: Max cache entries (default: 100)
            cache_ttl: Cache TTL in seconds (default: 600)
        """
        # Priority: SEARXNG_URL > SEARXNG_INSTANCES > instances > DEFAULT
        custom_instance = os.getenv("SEARXNG_URL")
        instances_csv = os.getenv("SEARXNG_INSTANCES")

        if custom_instance:
            self.instances = [custom_instance]
            logger.info(f"Using custom SearXNG instance from SEARXNG_URL: {custom_instance}")
        elif instances_csv:
            # Parse CSV of instances
            self.instances = [url.strip() for url in instances_csv.split(",") if url.strip()]
            logger.info(f"Using {len(self.instances)} SearXNG instances from SEARXNG_INSTANCES")
        else:
            self.instances = instances or DEFAULT_SEARXNG_INSTANCES
            logger.info(f"Using {len(self.instances)} default SearXNG instances")

        # Config from env vars or defaults
        self.timeout = int(os.getenv("SEARXNG_TIMEOUT", str(timeout)))
        self.max_retries = int(os.getenv("SEARXNG_MAX_RETRIES", str(max_retries)))

        # Setup session
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

        # Setup cache
        self.cache = LRUCache(cache_size, cache_ttl) if enable_cache else None
        if self.cache:
            logger.info(f"Cache enabled: max_size={cache_size}, ttl={cache_ttl}s")

    def _search_instance(
        self,
        instance_url: str,
        query: str,
        num_results: int = 5,
        language: str = "en",
        time_range: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search a single SearXNG instance with retry logic.

        Args:
            instance_url: Base URL of SearXNG instance
            query: Search query
            num_results: Max number of results to return
            language: Search language (e.g., 'en', 'de')
            time_range: Time filter (None, 'day', 'week', 'month', 'year')

        Returns:
            List of search results or None on failure
        """
        # Build SearXNG API params
        params = {
            "q": query,
            "format": "json",
            "language": language,
            "pageno": 1,
        }
        if time_range:
            params["time_range"] = time_range

        endpoint = f"{instance_url.rstrip('/')}/search"

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    f"SearXNG request to {instance_url} (attempt {attempt + 1}/{self.max_retries + 1}): {query}"
                )

                response = self.session.get(
                    endpoint,
                    params=params,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    data = response.json()
                    raw_results = data.get("results", [])

                    # Normalize to standard format
                    results = []
                    for r in raw_results[:num_results]:
                        results.append({
                            "title": r.get("title", ""),
                            "href": r.get("url", ""),
                            "body": r.get("content", ""),
                            "source": "searxng",
                            "engine": r.get("engine", ""),
                        })

                    logger.info(
                        f"✅ SearXNG ({instance_url}) returned {len(results)} results for: {query}"
                    )
                    return results

                else:
                    logger.warning(
                        f"⚠️ SearXNG ({instance_url}) returned status {response.status_code}"
                    )

            except requests.exceptions.Timeout:
                logger.warning(
                    f"⚠️ SearXNG ({instance_url}) timeout (attempt {attempt + 1}/{self.max_retries + 1})"
                )
            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"⚠️ SearXNG ({instance_url}) request error: {e}"
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ SearXNG ({instance_url}) unexpected error: {e}"
                )

            # Exponential backoff before retry
            if attempt < self.max_retries:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait_time)

        return None

    def search(
        self,
        query: str,
        num_results: int = 5,
        language: str = "en",
        time_range: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search across all configured SearXNG instances with fallback.

        Args:
            query: Search query
            num_results: Max number of results to return
            language: Search language
            time_range: Time filter (None, 'day', 'week', 'month', 'year')

        Returns:
            List of search results (empty list on complete failure)
        """
        if not query or not query.strip():
            logger.warning("Empty search query provided")
            return []

        # Check cache first
        if self.cache:
            cached = self.cache.get(query, language, time_range)
            if cached is not None:
                logger.info(f"🔍 SearXNG cache hit: {query[:60]}")
                return cached[:num_results]  # Respect num_results

        logger.info(f"🔍 Searching SearXNG: {query}")

        # Try each instance until one succeeds
        for instance in self.instances:
            results = self._search_instance(
                instance,
                query,
                num_results,
                language,
                time_range,
            )

            if results is not None:
                # Cache successful results
                if self.cache:
                    self.cache.set(query, language, time_range, results)
                return results

            logger.debug(f"Trying next SearXNG instance...")

        # All instances failed
        logger.error(f"❌ All SearXNG instances failed for query: {query}")
        return []


# Global singleton instance
_searxng_client: Optional[SearXNGSearch] = None


def get_searxng_client() -> SearXNGSearch:
    """Get or create the global SearXNG client instance."""
    global _searxng_client
    if _searxng_client is None:
        _searxng_client = SearXNGSearch()
    return _searxng_client


def searxng_search(
    query: str,
    num_results: int = 5,
    language: str = "en",
    time_range: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Convenience function for SearXNG search.

    Args:
        query: Search query
        num_results: Max number of results to return
        language: Search language (default: 'en')
        time_range: Time filter (None, 'day', 'week', 'month', 'year')

    Returns:
        List of dicts with keys: title, href, body, source, engine

    Example:
        >>> results = searxng_search('python tutorials', num_results=5)
        >>> for r in results:
        ...     print(f"{r['title']}: {r['href']}")
    """
    client = get_searxng_client()
    return client.search(query, num_results, language, time_range)
