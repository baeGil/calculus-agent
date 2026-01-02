"""
Test cases for Wolfram Alpha tool.
Tests API integration, caching, and rate limiting.
"""
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from backend.tools.wolfram import query_wolfram_alpha, get_wolfram_status


class TestWolframStatus:
    """Test suite for Wolfram status function."""

    def test_get_status_structure(self):
        """TC-WA-001: Status should have correct structure."""
        status = get_wolfram_status()
        assert "used" in status
        assert "limit" in status
        assert "remaining" in status
        assert "month" in status

    def test_status_limit_value(self):
        """TC-WA-002: Limit should be 2000."""
        status = get_wolfram_status()
        assert status["limit"] == 2000


@pytest.mark.asyncio
class TestWolframQuery:
    """Test suite for Wolfram Alpha queries."""

    async def test_missing_app_id(self):
        """TC-WA-003: Should fail gracefully without APP_ID."""
        with patch.dict("os.environ", {}, clear=True):
            # Remove WOLFRAM_ALPHA_APP_ID
            with patch("os.getenv", return_value=None):
                success, result = await query_wolfram_alpha("2+2")
                # Should either use cache or fail gracefully
                assert isinstance(success, bool)
                assert isinstance(result, str)

    async def test_cache_hit(self):
        """TC-WA-004: Cached query should return cached result."""
        from backend.utils.rate_limit import query_cache
        
        # Pre-populate cache
        query_cache.set("test_cached_query", "cached_result", context="wolfram")
        
        success, result = await query_wolfram_alpha("test_cached_query")
        assert success is True
        assert "cached_result" in result
        
        # Cleanup
        query_cache.cache.delete(query_cache._make_key("test_cached_query", "wolfram"))


class TestWolframRateLimitIntegration:
    """Test Wolfram rate limit integration."""

    def test_rate_limit_blocks_when_exceeded(self):
        """TC-WA-005: Should block requests when limit exceeded."""
        from backend.utils.rate_limit import WolframRateLimiter
        
        # Create a test limiter with very low limit
        limiter = WolframRateLimiter(cache_dir=".test_caches/wolfram_limit")
        
        # Manually set usage to limit
        key = limiter._get_month_key()
        limiter.cache.set(key, 2000, expire=86400)
        
        can_proceed, msg, remaining = limiter.can_make_request()
        assert can_proceed is False
        assert "limit" in msg.lower() or "2000" in msg
        assert remaining == 0
        
        # Cleanup
        limiter.cache.clear()

    def test_warning_when_low(self):
        """TC-WA-006: Should warn when quota is low."""
        from backend.utils.rate_limit import WolframRateLimiter
        
        limiter = WolframRateLimiter(cache_dir=".test_caches/wolfram_warn")
        
        # Set usage to 1950 (50 remaining)
        key = limiter._get_month_key()
        limiter.cache.set(key, 1950, expire=86400)
        
        can_proceed, msg, remaining = limiter.can_make_request()
        assert can_proceed is True
        assert "Warning" in msg or "50" in msg
        assert remaining == 50
        
        # Cleanup
        limiter.cache.clear()
