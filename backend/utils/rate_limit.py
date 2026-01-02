"""
Rate limiting and caching utilities.
"""
import os
import time
import hashlib
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import diskcache


# Rate limit configuration from GPT-OSS API limits
RATE_LIMITS = {
    "rpm": 30,      # Requests per minute
    "rpd": 1000,    # Requests per day
    "tpm": 8000,    # Tokens per minute
    "tpd": 200000,  # Tokens per day
}

# Wolfram Alpha rate limit
WOLFRAM_MONTHLY_LIMIT = 2000


@dataclass
class RateLimitTracker:
    """Track rate limits per session."""
    requests_this_minute: int = 0
    requests_today: int = 0
    tokens_this_minute: int = 0
    tokens_today: int = 0
    minute_start: float = field(default_factory=time.time)
    day_start: float = field(default_factory=time.time)
    
    def reset_if_needed(self):
        """Reset counters if time window has passed."""
        now = time.time()
        
        # Reset minute counters
        if now - self.minute_start >= 60:
            self.requests_this_minute = 0
            self.tokens_this_minute = 0
            self.minute_start = now
        
        # Reset daily counters
        if now - self.day_start >= 86400:
            self.requests_today = 0
            self.tokens_today = 0
            self.day_start = now
    
    def can_make_request(self, estimated_tokens: int = 1000) -> tuple[bool, str]:
        """Check if a request can be made within rate limits."""
        self.reset_if_needed()
        
        if self.requests_this_minute >= RATE_LIMITS["rpm"]:
            wait_time = int(60 - (time.time() - self.minute_start))
            return False, f"Rate limit exceeded. Please wait {wait_time} seconds."
        
        if self.requests_today >= RATE_LIMITS["rpd"]:
            return False, "Daily request limit reached. Please try again tomorrow."
        
        if self.tokens_this_minute + estimated_tokens > RATE_LIMITS["tpm"]:
            wait_time = int(60 - (time.time() - self.minute_start))
            return False, f"Token limit exceeded. Please wait {wait_time} seconds."
        
        if self.tokens_today + estimated_tokens > RATE_LIMITS["tpd"]:
            return False, "Daily token limit reached. Please try again tomorrow."
        
        return True, ""
    
    def record_usage(self, tokens_used: int):
        """Record token usage."""
        self.requests_this_minute += 1
        self.requests_today += 1
        self.tokens_this_minute += tokens_used
        self.tokens_today += tokens_used


class SessionRateLimiter:
    """Manage rate limits across sessions."""
    
    def __init__(self):
        self._trackers: dict[str, RateLimitTracker] = defaultdict(RateLimitTracker)
    
    def get_tracker(self, session_id: str) -> RateLimitTracker:
        return self._trackers[session_id]
    
    def check_limit(self, session_id: str, estimated_tokens: int = 1000) -> tuple[bool, str]:
        return self._trackers[session_id].can_make_request(estimated_tokens)
    
    def record(self, session_id: str, tokens: int):
        self._trackers[session_id].record_usage(tokens)


# Global rate limiter instance
rate_limiter = SessionRateLimiter()


class WolframRateLimiter:
    """
    Track Wolfram Alpha API usage with 2000 requests/month limit.
    Uses persistent disk cache to survive restarts.
    """
    
    def __init__(self, cache_dir: str = ".wolfram_cache"):
        self.cache = diskcache.Cache(cache_dir)
        self.monthly_limit = WOLFRAM_MONTHLY_LIMIT
    
    def _get_month_key(self) -> str:
        """Get current month key for tracking."""
        now = datetime.now()
        return f"wolfram_usage_{now.year}_{now.month}"
    
    def get_usage(self) -> int:
        """Get current month's usage count."""
        key = self._get_month_key()
        return self.cache.get(key, 0)
    
    def can_make_request(self) -> tuple[bool, str, int]:
        """
        Check if Wolfram API can be called.
        Returns: (can_proceed, error_message, remaining_requests)
        """
        usage = self.get_usage()
        remaining = self.monthly_limit - usage
        
        if usage >= self.monthly_limit:
            return False, "Wolfram Alpha monthly limit (2000 requests) reached. Using fallback.", 0
        
        # Warn when close to limit
        if remaining <= 100:
            return True, f"Warning: Only {remaining} Wolfram requests remaining this month.", remaining
        
        return True, "", remaining
    
    def record_usage(self):
        """Record one API call."""
        key = self._get_month_key()
        current = self.cache.get(key, 0)
        # Set with 32-day TTL to auto-cleanup old months
        self.cache.set(key, current + 1, expire=86400 * 32)
    
    def get_status(self) -> dict:
        """Get current rate limit status."""
        usage = self.get_usage()
        return {
            "used": usage,
            "limit": self.monthly_limit,
            "remaining": max(0, self.monthly_limit - usage),
            "month": datetime.now().strftime("%Y-%m"),
        }


# Global Wolfram rate limiter
wolfram_limiter = WolframRateLimiter()


class QueryCache:
    """Cache for repeated queries to reduce API calls."""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache = diskcache.Cache(cache_dir)
        self.ttl = 3600 * 24 * 7  # 7 days TTL for math queries
    
    def _make_key(self, query: str, context: str = "") -> str:
        """Create cache key from query and context."""
        content = f"{query}:{context}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, query: str, context: str = "") -> Optional[str]:
        """Get cached response if available."""
        key = self._make_key(query, context)
        return self.cache.get(key)
    
    def set(self, query: str, response: str, context: str = ""):
        """Cache a response."""
        key = self._make_key(query, context)
        self.cache.set(key, response, expire=self.ttl)
    
    def clear(self):
        """Clear all cached responses."""
        self.cache.clear()


# Global cache instance
query_cache = QueryCache()

