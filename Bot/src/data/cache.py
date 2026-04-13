"""Per-cycle in-memory cache. Created fresh each run_cycle(), discarded after."""

from __future__ import annotations

from typing import Any


class CycleCache:
    """Simple key-value cache that lives for one bot cycle."""

    def __init__(self):
        self._store: dict[str, Any] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        val = self._store.get(key)
        if val is not None:
            self.hits += 1
        else:
            self.misses += 1
        return val

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def clear(self) -> None:
        self._store.clear()
        self.hits = 0
        self.misses = 0
