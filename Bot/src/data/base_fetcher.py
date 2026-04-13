"""Base class for all sport data fetchers. Provides caching + retry."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from src.data.cache import CycleCache
from src.scanner.odds_fetcher import api_call_with_retry

logger = logging.getLogger(__name__)


class BaseFetcher:
    """Base class with cached HTTP GET and retry logic."""

    def __init__(self, cache: CycleCache):
        self.cache = cache
        self.session = requests.Session()

    def _cached_get(
        self,
        cache_key: str,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        delay: float = 0.0,
    ) -> Any | None:
        """GET with cache-first, retry, and optional rate-limit delay."""
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        if delay > 0:
            time.sleep(delay)

        try:
            kwargs: dict = {"params": params, "timeout": 15}
            if headers:
                kwargs["headers"] = headers

            resp = api_call_with_retry(
                self.session.get, url, **kwargs, retries=2, backoff=2,
            )
            resp.raise_for_status()
            data = resp.json()
            self.cache.set(cache_key, data)
            return data
        except Exception as e:
            logger.warning("%s fetch failed: %s", self.__class__.__name__, e)
            return None
