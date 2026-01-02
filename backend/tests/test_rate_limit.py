"""
Test cases for Rate Limiting module.
Tests GPT-OSS limits and Wolfram monthly limits.
"""
import pytest
import time
from backend.utils.rate_limit import (
    RateLimitTracker,
    SessionRateLimiter,
    WolframRateLimiter,
    QueryCache,
    RATE_LIMITS,
    WOLFRAM_MONTHLY_LIMIT,
)


class TestRateLimitTracker:
    """Test suite for session rate limit tracking."""

    def test_initial_state(self):
        """TC-RL-001: Initial tracker should allow requests."""
        tracker = RateLimitTracker()
        can_proceed, msg = tracker.can_make_request()
        assert can_proceed is True
        assert msg == ""

    def test_record_usage(self):
        """TC-RL-002: Recording usage should increment counters."""
        tracker = RateLimitTracker()
        tracker.record_usage(100)
        assert tracker.requests_this_minute == 1
        assert tracker.tokens_this_minute == 100

    def test_rpm_limit(self):
        """TC-RL-003: Should block after exceeding RPM limit."""
        tracker = RateLimitTracker()
        # Simulate 30 requests
        for _ in range(30):
            tracker.record_usage(10)
        
        can_proceed, msg = tracker.can_make_request()
        assert can_proceed is False
        assert "Rate limit" in msg or "wait" in msg.lower()

    def test_token_limit(self):
        """TC-RL-004: Should block after exceeding TPM limit."""
        tracker = RateLimitTracker()
        # Record close to 8000 tokens
        tracker.tokens_this_minute = 7500
        
        can_proceed, msg = tracker.can_make_request(estimated_tokens=1000)
        assert can_proceed is False
        assert "Token" in msg or "limit" in msg.lower()

    def test_daily_limit(self):
        """TC-RL-005: Should block after exceeding daily requests."""
        tracker = RateLimitTracker()
        tracker.requests_today = RATE_LIMITS["rpd"]
        
        can_proceed, msg = tracker.can_make_request()
        assert can_proceed is False
        assert "Daily" in msg or "tomorrow" in msg.lower()


class TestSessionRateLimiter:
    """Test suite for multi-session rate limiting."""

    def test_separate_sessions(self):
        """TC-RL-006: Different sessions should have independent limits."""
        limiter = SessionRateLimiter()
        
        # Record usage for session A
        limiter.record("session_a", 100)
        
        # Session B should still be clean
        tracker_b = limiter.get_tracker("session_b")
        assert tracker_b.requests_this_minute == 0

    def test_session_persistence(self):
        """TC-RL-007: Same session should accumulate usage."""
        limiter = SessionRateLimiter()
        
        limiter.record("session_x", 50)
        limiter.record("session_x", 50)
        
        tracker = limiter.get_tracker("session_x")
        assert tracker.requests_this_minute == 2
        assert tracker.tokens_this_minute == 100


class TestWolframRateLimiter:
    """Test suite for Wolfram Alpha monthly rate limiting."""

    def test_initial_usage(self):
        """TC-RL-008: Initial usage should be 0 or existing value."""
        limiter = WolframRateLimiter(cache_dir=".test_caches/wolfram_cache")
        status = limiter.get_status()
        assert status["limit"] == WOLFRAM_MONTHLY_LIMIT
        assert isinstance(status["used"], int)
        assert isinstance(status["remaining"], int)

    def test_can_make_request_initially(self):
        """TC-RL-009: Should allow requests when under limit."""
        limiter = WolframRateLimiter(cache_dir=".test_caches/wolfram_cache_2")
        can_proceed, msg, remaining = limiter.can_make_request()
        assert can_proceed is True

    def test_record_increments_usage(self):
        """TC-RL-010: Recording should increment usage counter."""
        limiter = WolframRateLimiter(cache_dir=".test_caches/wolfram_cache_3")
        initial = limiter.get_usage()
        limiter.record_usage()
        after = limiter.get_usage()
        assert after == initial + 1

    def test_month_key_format(self):
        """TC-RL-011: Month key should be in correct format."""
        limiter = WolframRateLimiter()
        key = limiter._get_month_key()
        assert key.startswith("wolfram_usage_")
        assert "2025" in key  # Current year


class TestQueryCache:
    """Test suite for query caching."""

    def test_cache_miss(self):
        """TC-RL-012: Non-existent query should return None."""
        cache = QueryCache(cache_dir=".test_caches/cache_1")
        result = cache.get("nonexistent_query_12345")
        assert result is None

    def test_cache_set_and_get(self):
        """TC-RL-013: Cached query should be retrievable."""
        cache = QueryCache(cache_dir=".test_caches/cache_2")
        cache.set("test_query", "test_response", context="test")
        result = cache.get("test_query", context="test")
        assert result == "test_response"

    def test_cache_context_separation(self):
        """TC-RL-014: Different contexts should have separate caches."""
        cache = QueryCache(cache_dir=".test_caches/cache_3")
        cache.set("query", "response_a", context="context_a")
        cache.set("query", "response_b", context="context_b")
        
        assert cache.get("query", context="context_a") == "response_a"
        assert cache.get("query", context="context_b") == "response_b"

    def test_cache_clear(self):
        """TC-RL-015: Clear should remove all cached entries."""
        cache = QueryCache(cache_dir=".test_caches/cache_4")
        cache.set("key1", "value1")
        cache.clear()
        assert cache.get("key1") is None
