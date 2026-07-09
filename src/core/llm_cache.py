"""
CloudOptima — In-Memory + Disk-Persisted LLM Response Cache

Caches LLM responses keyed by (messages_hash, model, temperature) to
avoid redundant API calls for identical prompts. Uses SHA256 hashing
of the serialized messages array as the primary cache key.

Persistence: saves to a JSON file on every write operation (set, invalidate,
clear) and loads on startup. Survives process restarts. Uses wall-clock
timestamps (time.time()) for expiry so TTLs work correctly across restarts.

Features:
- TTL-based expiry (configurable, default 1 hour)
- FIFO eviction when max size is exceeded (configurable, default 1000)
- Disk persistence via JSON file (configurable path)
- Hit/miss stats tracking (resets on restart)
- Thread-safe via threading.Lock
- Graceful degradation: disk I/O failures never break the cache
"""

from __future__ import annotations
import hashlib
import json
import logging
import time
from pathlib import Path
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

# Default cache configuration
DEFAULT_TTL_SECONDS = 3600  # 1 hour
DEFAULT_MAX_SIZE = 1000
DEFAULT_PERSIST_PATH = ".freebuff/llm_cache.json"


def _hash_messages(messages: list[dict]) -> str:
    """Create a deterministic SHA256 hash from a messages array."""
    serialized = json.dumps(messages, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _make_cache_key(messages: list[dict], model: str, temperature: float) -> str:
    """Generate a composite cache key from messages, model, and temperature."""
    msg_hash = _hash_messages(messages)
    return f"llm:{model}:{temperature:.1f}:{msg_hash}"


class CacheEntry:
    """A single cache entry with value and wall-clock expiry."""

    __slots__ = ("value", "expires_at", "hits", "created_at")

    def __init__(self, value: str, ttl_seconds: float):
        self.value = value
        self.expires_at = time.time() + ttl_seconds  # wall-clock timestamp
        self.hits = 0
        self.created_at = time.time()

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def record_hit(self):
        self.hits += 1

    def remaining_ttl(self) -> float:
        """Seconds until this entry expires. May be negative."""
        return self.expires_at - time.time()

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "expires_at": self.expires_at,
            "hits": self.hits,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CacheEntry:
        entry = cls.__new__(cls)
        entry.value = data["value"]
        entry.expires_at = data["expires_at"]
        entry.hits = data.get("hits", 0)
        entry.created_at = data.get("created_at", 0.0)
        return entry


class LLMCache:
    """Thread-safe in-memory cache for LLM responses with TTL and disk persistence.

    Saves to a JSON file on every write operation so the cache survives
    process restarts. Uses wall-clock timestamps (time.time()) so TTLs
    are correctly enforced across restarts.

    Uses time.time() for expiry checks (wall-clock, cross-restart compatible).
    Evicts oldest entries (by insertion/update order) when over max_size.
    """

    def __init__(
        self,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_size: int = DEFAULT_MAX_SIZE,
        persist_path: Optional[str] = None,
    ):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.persist_path = persist_path or DEFAULT_PERSIST_PATH
        self._data: dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._stats: dict[str, int] = {"hits": 0, "misses": 0, "evictions": 0}

        # Load persisted cache on startup
        self._load_from_disk()

    # ─── Public API (LLM Message-based) ──────────────────────────────

    def get(self, messages: list[dict], model: str, temperature: float) -> Optional[str]:
        """Look up a cached LLM response. Returns None on miss or expiry."""
        key = _make_cache_key(messages, model, temperature)
        return self._get_by_key(key)

    def set(self, messages: list[dict], model: str, temperature: float, value: str):
        """Store an LLM response in the cache and persist to disk."""
        key = _make_cache_key(messages, model, temperature)
        self._set_by_key(key, value)

    def invalidate(self, messages: list[dict], model: str, temperature: float):
        """Remove a specific LLM entry and persist to disk."""
        key = _make_cache_key(messages, model, temperature)
        self._invalidate_by_key(key)

    # ─── Public API (Raw Key-Value) ──────────────────────────────────

    RAW_KEY_PREFIX = "raw:"

    def get_raw(self, key: str) -> Optional[str]:
        """Look up a cached value by an arbitrary string key.

        Unlike get(), which hashes message arrays with model/temperature,
        get_raw() uses the key directly. Useful for caching non-LLM data
        like API responses, pricing queries, or precomputed results.

        Args:
            key: Arbitrary cache key (e.g. "azure_prices:centralindia:D4_v5")

        Returns:
            Cached value string, or None on miss/expiry.
        """
        raw_key = f"{self.RAW_KEY_PREFIX}{key}"
        return self._get_by_key(raw_key)

    def set_raw(self, key: str, value: str):
        """Store an arbitrary value in the cache with a string key.

        Like set() but accepts a plain string key instead of
        messages + model + temperature. Persists to disk.

        Args:
            key: Arbitrary cache key (e.g. "azure_prices:centralindia:D4_v5")
            value: String value to cache
        """
        raw_key = f"{self.RAW_KEY_PREFIX}{key}"
        self._set_by_key(raw_key, value)

    def invalidate_raw(self, key: str):
        """Remove a raw key-value entry and persist to disk."""
        raw_key = f"{self.RAW_KEY_PREFIX}{key}"
        self._invalidate_by_key(raw_key)

    def clear(self, clear_raw: bool = True):
        """Clear all cached entries and persist empty state to disk.

        Args:
            clear_raw: If True (default), also clears raw key-value entries.
                       If False, only clears LLM message-based entries.
        """
        with self._lock:
            if clear_raw:
                self._data.clear()
            else:
                # Only remove non-raw entries
                keys_to_remove = [k for k in self._data if not k.startswith(self.RAW_KEY_PREFIX)]
                for k in keys_to_remove:
                    del self._data[k]
            self._stats = {"hits": 0, "misses": 0, "evictions": 0}
        self._save_to_disk()

    def get_stats(self) -> dict:
        """Get cache performance statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0
            expired_count = sum(1 for e in self._data.values() if e.is_expired())
            return {
                "size": len(self._data),
                "max_size": self.max_size,
                "expired": expired_count,
                "ttl_seconds": self.ttl_seconds,
                "persist_path": str(self.persist_path),
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "hit_rate_percent": round(hit_rate, 1),
            }

    # ─── Internal (key-based helpers) ───────────────────────────────

    def _get_by_key(self, key: str) -> Optional[str]:
        """Internal: look up a value by its internal cache key."""
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return None

            if entry.is_expired():
                del self._data[key]
                self._stats["misses"] += 1
                return None

            entry.record_hit()
            self._stats["hits"] += 1
            return entry.value

    def _set_by_key(self, key: str, value: str):
        """Internal: store a value by its internal cache key and persist."""
        with self._lock:
            if len(self._data) >= self.max_size and key not in self._data:
                self._evict_oldest()

            self._data[key] = CacheEntry(value, self.ttl_seconds)
        self._save_to_disk()

    def _invalidate_by_key(self, key: str):
        """Internal: remove an entry by its internal cache key and persist."""
        with self._lock:
            self._data.pop(key, None)
        self._save_to_disk()

    # ─── Internal (eviction) ─────────────────────────────────────────

    def _evict_oldest(self):
        """Evict ~20% of oldest entries when cache is full.

        Uses Python dict insertion order (FIFO) as a proxy for LRU.
        """
        evict_count = max(1, self.max_size // 5)
        keys_to_evict = list(self._data.keys())[:evict_count]
        for key in keys_to_evict:
            del self._data[key]
        self._stats["evictions"] += len(keys_to_evict)
        logger.debug(f"Evicted {len(keys_to_evict)} entries from LLM cache")

    # ─── Disk Persistence ─────────────────────────────────────────────

    def _persist_path(self) -> Path:
        """Get the persist path as a Path, ensuring parent directory exists."""
        p = Path(self.persist_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _save_to_disk(self):
        """Write cache entries to disk as JSON (best-effort)."""
        try:
            with self._lock:
                serializable = {}
                for key, entry in self._data.items():
                    serializable[key] = entry.to_dict()

                payload = {
                    "version": 1,
                    "created_at": time.time(),
                    "ttl_seconds": self.ttl_seconds,
                    "max_size": self.max_size,
                    "entries": serializable,
                }

            path = self._persist_path()
            with open(path, "w") as f:
                json.dump(payload, f, indent=2)

            logger.debug(f"Saved {len(serializable)} cache entries to {path}")

        except Exception as e:
            logger.warning(f"Failed to persist LLM cache to disk: {e}")

    def _load_from_disk(self):
        """Load cache entries from disk JSON file (best-effort)."""
        path = self._persist_path()
        if not path.exists():
            logger.debug(f"No persisted cache file at {path}")
            return

        try:
            with open(path) as f:
                payload = json.load(f)

            entries = payload.get("entries", {})
            now = time.time()
            loaded = 0
            expired = 0

            with self._lock:
                for key, data in entries.items():
                    entry = CacheEntry.from_dict(data)
                    if entry.is_expired():
                        expired += 1
                        continue
                    self._data[key] = entry
                    loaded += 1

            logger.info(
                f"Loaded {loaded} cache entries from {path}"
                f"{' (skipped ' + str(expired) + ' expired)' if expired else ''}"
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to load persisted cache (corrupted file?): {e}")
            # Corrupted file — start fresh
            with self._lock:
                self._data.clear()
        except Exception as e:
            logger.warning(f"Unexpected error loading persisted cache: {e}")


# ─── Global Cache Instance ────────────────────────────────────────────

_cache: Optional[LLMCache] = None


def get_cache(persist_path: Optional[str] = None) -> LLMCache:
    """Get or create the global LLM cache instance.

    Args:
        persist_path: Optional path to persist cache to disk.
                      Defaults to .freebuff/llm_cache.json
    """
    global _cache
    if _cache is None:
        _cache = LLMCache(persist_path=persist_path)
    return _cache


def reset_cache():
    """Reset the global cache (useful for testing)."""
    global _cache
    _cache = None
