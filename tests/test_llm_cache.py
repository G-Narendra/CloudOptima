"""Tests for the in-memory LLM response cache."""

import time
import json
import os
import json
import tempfile

from src.core.llm_cache import (
    LLMCache,
    CacheEntry,
    get_cache,
    reset_cache,
    _hash_messages,
    _make_cache_key,
)


class TestHashFunctions:
    """Test cache key generation."""

    def test_hash_messages_deterministic(self):
        msgs = [{"role": "user", "content": "Hello"}]
        h1 = _hash_messages(msgs)
        h2 = _hash_messages(msgs)
        assert h1 == h2

    def test_hash_messages_different(self):
        msgs1 = [{"role": "user", "content": "Hello"}]
        msgs2 = [{"role": "user", "content": "World"}]
        assert _hash_messages(msgs1) != _hash_messages(msgs2)

    def test_hash_messages_key_order_independent(self):
        msgs1 = [{"role": "user", "content": "Hello", "extra": "data"}]
        msgs2 = [{"extra": "data", "content": "Hello", "role": "user"}]
        assert _hash_messages(msgs1) == _hash_messages(msgs2)

    def test_make_cache_key_includes_model_and_temp(self):
        msgs = [{"role": "user", "content": "Hi"}]
        key1 = _make_cache_key(msgs, "model-a", 0.2)
        key2 = _make_cache_key(msgs, "model-b", 0.2)
        key3 = _make_cache_key(msgs, "model-a", 0.5)
        assert key1 != key2
        assert key1 != key3


class TestLLMCache:
    """Test cache operations."""

    def setup_method(self):
        self.cache = LLMCache(ttl_seconds=3600, max_size=100)
        self.msgs = [{"role": "user", "content": "Test prompt"}]
        self.response = '{"result": "test"}'

    def test_get_miss_returns_none(self):
        result = self.cache.get(self.msgs, "test-model", 0.2)
        assert result is None

    def test_set_and_get(self):
        self.cache.set(self.msgs, "test-model", 0.2, self.response)
        result = self.cache.get(self.msgs, "test-model", 0.2)
        assert result == self.response

    def test_cache_miss_different_model(self):
        self.cache.set(self.msgs, "model-a", 0.2, self.response)
        result = self.cache.get(self.msgs, "model-b", 0.2)
        assert result is None

    def test_cache_miss_different_temperature(self):
        self.cache.set(self.msgs, "test-model", 0.2, self.response)
        result = self.cache.get(self.msgs, "test-model", 0.5)
        assert result is None

    def test_cache_expiry(self):
        short_cache = LLMCache(ttl_seconds=0.01, max_size=100)
        short_cache.set(self.msgs, "test-model", 0.2, self.response)
        time.sleep(0.02)
        result = short_cache.get(self.msgs, "test-model", 0.2)
        assert result is None

    def test_stats_tracking(self):
        self.cache.get(self.msgs, "test-model", 0.2)  # miss
        self.cache.get(self.msgs, "test-model", 0.5)  # miss
        self.cache.set(self.msgs, "test-model", 0.2, self.response)
        self.cache.get(self.msgs, "test-model", 0.2)  # hit
        self.cache.get(self.msgs, "test-model", 0.2)  # hit (second hit)

        stats = self.cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["hit_rate_percent"] == 50.0

    def test_clear_cache(self):
        self.cache.set(self.msgs, "test-model", 0.2, self.response)
        assert self.cache.get(self.msgs, "test-model", 0.2) is not None
        self.cache.clear()
        assert self.cache.get(self.msgs, "test-model", 0.2) is None
        stats = self.cache.get_stats()
        assert stats["size"] == 0
        assert stats["hits"] == 0

    def test_invalidate_specific_key(self):
        self.cache.set(self.msgs, "model-a", 0.2, self.response)
        self.cache.invalidate(self.msgs, "model-a", 0.2)
        assert self.cache.get(self.msgs, "model-a", 0.2) is None

    def test_invalidate_preserves_other_keys(self):
        self.cache.set(self.msgs, "model-a", 0.2, self.response)
        other_msgs = [{"role": "user", "content": "Other"}]
        self.cache.set(other_msgs, "model-b", 0.5, "other response")
        self.cache.invalidate(self.msgs, "model-a", 0.2)
        # Other entry should still exist
        result = self.cache.get(other_msgs, "model-b", 0.5)
        assert result == "other response"

    def test_lru_eviction(self):
        small_cache = LLMCache(ttl_seconds=3600, max_size=5)
        # Add 6 entries (exceeds max_size)
        for i in range(6):
            msgs = [{"role": "user", "content": f"Prompt {i}"}]
            small_cache.set(msgs, "model", 0.2, f"Response {i}")
        # Cache should have evicted at least 1 entry
        stats = small_cache.get_stats()
        assert stats["size"] <= 5
        assert stats["evictions"] >= 1

    def test_hit_rate_with_hits(self):
        """Hit rate should increase with repeated lookups."""
        self.cache.set(self.msgs, "test-model", 0.2, self.response)
        self.cache.get(self.msgs, "test-model", 0.2)  # hit
        self.cache.get(self.msgs, "test-model", 0.2)  # hit
        self.cache.get(self.msgs, "nonexistent", 0.2)  # miss
        stats = self.cache.get_stats()
        assert stats["hit_rate_percent"] == 66.7  # 2/3 hits

    def test_cache_stats_empty_after_clear(self):
        self.cache.set(self.msgs, "test-model", 0.2, self.response)
        self.cache.get(self.msgs, "test-model", 0.2)  # hit
        self.cache.clear()
        stats = self.cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0


class TestDiskPersistence:
    """Test disk persistence of cache entries."""

    def test_cache_saves_to_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "cache.json")
            cache = LLMCache(persist_path=path)
            msgs = [{"role": "user", "content": "test persist"}]
            cache.set(msgs, "model-a", 0.2, "saved response")

            # Verify file was written
            assert os.path.exists(path)
            with open(path) as f:
                data = json.load(f)
            assert data["version"] == 1
            assert len(data["entries"]) == 1
            # Key should contain model and temperature
            keys = list(data["entries"].keys())
            assert "model-a" in keys[0]
            assert "0.2" in keys[0]

    def test_cache_loads_from_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "cache.json")

            # Write cache in one instance
            cache1 = LLMCache(persist_path=path)
            msgs = [{"role": "user", "content": "hello"}]
            cache1.set(msgs, "model-b", 0.5, "persisted value")
            del cache1

            # Load in a new instance
            cache2 = LLMCache(persist_path=path)
            result = cache2.get(msgs, "model-b", 0.5)
            assert result == "persisted value"
            stats = cache2.get_stats()
            assert stats["size"] == 1

    def test_expired_entries_skipped_on_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "cache.json")

            # Create a cache with 0 TTL so entries expire immediately
            cache1 = LLMCache(ttl_seconds=0, persist_path=path)
            msgs = [{"role": "user", "content": "expired"}]
            cache1.set(msgs, "model", 0.2, "will expire")
            import time
            time.sleep(0.01)  # ensure TTL passes
            del cache1

            # Reload — expired entries should be skipped
            cache2 = LLMCache(ttl_seconds=3600, persist_path=path)
            result = cache2.get(msgs, "model", 0.2)
            assert result is None  # expired, not loaded
            stats = cache2.get_stats()
            assert stats["size"] == 0

    def test_corrupted_file_start_fresh(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "cache.json")
            # Write invalid JSON
            with open(path, "w") as f:
                f.write("not valid json at all")

            # Should not crash, should start fresh
            cache = LLMCache(persist_path=path)
            msgs = [{"role": "user", "content": "fresh"}]
            result = cache.get(msgs, "model", 0.2)
            assert result is None  # empty cache
            stats = cache.get_stats()
            assert stats["size"] == 0

    def test_invalidate_removes_from_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "cache.json")
            cache = LLMCache(persist_path=path)
            msgs = [{"role": "user", "content": "delete me"}]
            cache.set(msgs, "model", 0.2, "value")
            assert cache.get(msgs, "model", 0.2) is not None

            cache.invalidate(msgs, "model", 0.2)
            assert cache.get(msgs, "model", 0.2) is None

            # Reload — should still be gone
            cache2 = LLMCache(persist_path=path)
            assert cache2.get(msgs, "model", 0.2) is None

    def test_clear_removes_all_from_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "cache.json")
            cache = LLMCache(persist_path=path)
            cache.set([{"role": "user", "content": "a"}], "m", 0.2, "1")
            cache.set([{"role": "user", "content": "b"}], "m", 0.2, "2")
            assert cache.get_stats()["size"] == 2

            cache.clear()
            assert cache.get_stats()["size"] == 0

            # Reload — should be empty
            cache2 = LLMCache(persist_path=path)
            assert cache2.get_stats()["size"] == 0

    def test_cache_without_persist_path(self):
        """Legacy usage without persist_path should still work."""
        cache = LLMCache()  # no persist_path, uses default
        msgs = [{"role": "user", "content": "test"}]
        cache.set(msgs, "m", 0.2, "value")
        assert cache.get(msgs, "m", 0.2) == "value"
        cache.clear()


class TestCacheEntry:
    """Test CacheEntry serialization."""

    def test_to_dict_and_from_dict(self):
        entry = CacheEntry("test value", ttl_seconds=3600)
        d = entry.to_dict()
        assert d["value"] == "test value"
        assert d["hits"] == 0
        assert "expires_at" in d

        restored = CacheEntry.from_dict(d)
        assert restored.value == "test value"
        assert restored.hits == 0
        assert not restored.is_expired()

    def test_remaining_ttl(self):
        entry = CacheEntry("x", ttl_seconds=60)
        assert 0 < entry.remaining_ttl() <= 60


class TestRawKeyValue:
    """Test get_raw/set_raw key-value API."""

    def setup_method(self):
        self.cache = LLMCache(ttl_seconds=3600, max_size=100)

    def test_set_raw_and_get_raw(self):
        self.cache.set_raw("mykey", "myvalue")
        result = self.cache.get_raw("mykey")
        assert result == "myvalue"

    def test_get_raw_miss(self):
        result = self.cache.get_raw("nonexistent")
        assert result is None

    def test_raw_key_isolation_from_llm(self):
        """Raw keys should not interfere with LLM message keys and vice versa."""
        msgs = [{"role": "user", "content": "hello"}]
        self.cache.set(msgs, "model", 0.2, "llm_value")
        self.cache.set_raw("prices:test", "raw_value")

        # Both should be retrievable independently
        assert self.cache.get(msgs, "model", 0.2) == "llm_value"
        assert self.cache.get_raw("prices:test") == "raw_value"

    def test_raw_key_with_special_chars(self):
        """Raw keys should handle special characters."""
        key = "azure_prices:centralindia:Standard_D4_v5:Consumption"
        self.cache.set_raw(key, '{"price": 0.176}')
        result = self.cache.get_raw(key)
        assert result == '{"price": 0.176}'

    def test_invalidate_raw(self):
        self.cache.set_raw("temp_key", "temp_value")
        assert self.cache.get_raw("temp_key") is not None
        self.cache.invalidate_raw("temp_key")
        assert self.cache.get_raw("temp_key") is None

    def test_invalidate_raw_preserves_others(self):
        self.cache.set_raw("key_a", "value_a")
        self.cache.set_raw("key_b", "value_b")
        self.cache.invalidate_raw("key_a")
        assert self.cache.get_raw("key_b") == "value_b"

    def test_raw_expiry(self):
        short_cache = LLMCache(ttl_seconds=0.01)
        short_cache.set_raw("ephemeral", "gone_soon")
        time.sleep(0.02)
        result = short_cache.get_raw("ephemeral")
        assert result is None

    def test_raw_stats_tracking(self):
        self.cache.get_raw("miss1")  # miss
        self.cache.set_raw("hit_key", "value")
        self.cache.get_raw("hit_key")  # hit
        self.cache.get_raw("hit_key")  # hit

        stats = self.cache.get_stats()
        assert stats["hits"] >= 2
        assert stats["misses"] >= 1

    def test_clear_removes_raw_by_default(self):
        self.cache.set_raw("my_key", "my_val")
        self.cache.clear()  # clear_raw=True by default
        assert self.cache.get_raw("my_key") is None

    def test_clear_preserves_raw_when_clear_raw_false(self):
        msgs = [{"role": "user", "content": "test"}]
        self.cache.set(msgs, "m", 0.2, "llm_val")
        self.cache.set_raw("preserved", "still_here")

        self.cache.clear(clear_raw=False)

        # LLM entry should be gone
        assert self.cache.get(msgs, "m", 0.2) is None
        # Raw entry should survive
        assert self.cache.get_raw("preserved") == "still_here"

    def test_raw_disk_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "cache.json")

            # Write raw entry
            cache1 = LLMCache(persist_path=path)
            cache1.set_raw("disk_key", "disk_value")
            del cache1

            # Reload and verify
            cache2 = LLMCache(persist_path=path)
            result = cache2.get_raw("disk_key")
            assert result == "disk_value"

    def test_raw_eviction_with_llm_entries(self):
        """Raw entries should count toward max_size and be evictable."""
        small_cache = LLMCache(max_size=5)
        # Add 3 LLM entries
        for i in range(3):
            msgs = [{"role": "user", "content": f"llm_{i}"}]
            small_cache.set(msgs, "m", 0.2, f"llm_{i}")
        # Add 3 raw entries (total would be 6 > max_size 5)
        for i in range(3):
            small_cache.set_raw(f"raw:{i}", f"raw_{i}")

        stats = small_cache.get_stats()
        assert stats["size"] <= 5
        # At least one eviction should have occurred
        assert stats["evictions"] >= 1


class TestGlobalCache:
    """Test the global cache singleton."""

    def teardown_method(self):
        reset_cache()

    def test_get_cache_singleton(self):
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2

    def test_reset_cache(self):
        c1 = get_cache()
        reset_cache()
        c2 = get_cache()
        assert c1 is not c2

    def test_cache_persistence_across_calls(self):
        cache = get_cache()
        msgs = [{"role": "user", "content": "Hello"}]
        cache.set(msgs, "model", 0.2, "world")
        result = cache.get(msgs, "model", 0.2)
        assert result == "world"
        reset_cache()
