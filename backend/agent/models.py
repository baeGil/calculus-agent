"""
Model configurations for the multi-agent algebra chatbot.
Includes rate limits, model parameters, and factory functions.
"""
import os
import time
import asyncio
from typing import Optional, Dict, Any, Callable, TypeVar
from functools import wraps
from dataclasses import dataclass, field
from langchain_groq import ChatGroq


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    id: str
    temperature: float = 0.6
    max_tokens: int = 4096
    context_length: int = 128000  # Default context window
    top_p: float = 1.0
    streaming: bool = True
    # Rate limits
    rpm: int = 30  # Requests per minute
    rpd: int = 1000  # Requests per day
    tpm: int = 10000  # Tokens per minute
    tpd: int = 300000  # Tokens per day


# Model configurations based on rate limit table
MODEL_CONFIGS: Dict[str, ModelConfig] = {
    "kimi-k2": ModelConfig(
        id="moonshotai/kimi-k2-instruct-0905",
        temperature=0.0,
        max_tokens=16384,
        context_length=262144,  # 256K tokens
        top_p=1.0,
        rpm=60, rpd=1000, tpm=10000, tpd=300000
    ),
    "llama-4-maverick": ModelConfig(
        id="meta-llama/llama-4-maverick-17b-128e-instruct",
        temperature=0.0,
        max_tokens=8192,
        context_length=128000,
        rpm=30, rpd=1000, tpm=6000, tpd=500000
    ),
    "llama-4-scout": ModelConfig(
        id="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0.0,
        max_tokens=8192,
        context_length=128000,
        rpm=30, rpd=1000, tpm=30000, tpd=500000
    ),
    "qwen3-32b": ModelConfig(
        id="qwen/qwen3-32b",
        temperature=0.0,
        max_tokens=8192,
        context_length=32768,  # 32K tokens
        rpm=60, rpd=1000, tpm=6000, tpd=500000
    ),
    "gpt-oss-120b": ModelConfig(
        id="openai/gpt-oss-120b",
        temperature=0.0,
        max_tokens=8192,
        context_length=128000,
        rpm=30, rpd=1000, tpm=8000, tpd=200000
    ),
    "wolfram": ModelConfig(
        id="wolfram-alpha-api",
        temperature=0.0,
        max_tokens=0,
        context_length=0,
        rpm=30, rpd=2000, tpm=100000, tpd=1000000
    ),
}


@dataclass
class ModelRateLimitTracker:
    """Track rate limits for a specific model."""
    model_name: str
    config: ModelConfig
    minute_requests: int = 0
    minute_tokens: int = 0
    day_requests: int = 0
    day_tokens: int = 0
    last_minute_reset: float = field(default_factory=time.time)
    last_day_reset: float = field(default_factory=time.time)
    
    def _reset_if_needed(self):
        """Reset counters if time windows have passed."""
        now = time.time()
        if now - self.last_minute_reset >= 60:
            self.minute_requests = 0
            self.minute_tokens = 0
            self.last_minute_reset = now
        if now - self.last_day_reset >= 86400:
            self.day_requests = 0
            self.day_tokens = 0
            self.last_day_reset = now
    
    def can_request(self, estimated_tokens: int = 100) -> tuple[bool, str]:
        """Check if a request can be made within rate limits."""
        self._reset_if_needed()
        
        if self.minute_requests >= self.config.rpm:
            return False, f"Rate limit: {self.model_name} exceeded {self.config.rpm} RPM"
        if self.day_requests >= self.config.rpd:
            return False, f"Rate limit: {self.model_name} exceeded {self.config.rpd} RPD"
        if self.minute_tokens + estimated_tokens > self.config.tpm:
            return False, f"Rate limit: {self.model_name} would exceed {self.config.tpm} TPM"
        if self.day_tokens + estimated_tokens > self.config.tpd:
            return False, f"Rate limit: {self.model_name} would exceed {self.config.tpd} TPD"
        
        return True, ""
    
    def record_request(self, tokens_used: int):
        """Record a completed request."""
        self._reset_if_needed()
        self.minute_requests += 1
        self.day_requests += 1
        self.minute_tokens += tokens_used
        self.day_tokens += tokens_used


class ModelManager:
    """Manages model instances and rate limiting."""
    
    def __init__(self):
        self.trackers: Dict[str, ModelRateLimitTracker] = {}
        self._api_key = os.getenv("GROQ_API_KEY")
    
    def _get_tracker(self, model_name: str) -> ModelRateLimitTracker:
        """Get or create a rate limit tracker for a model."""
        if model_name not in self.trackers:
            config = MODEL_CONFIGS.get(model_name)
            if not config:
                raise ValueError(f"Unknown model: {model_name}")
            self.trackers[model_name] = ModelRateLimitTracker(model_name, config)
        return self.trackers[model_name]
    
    def get_model(self, model_name: str) -> ChatGroq:
        """Get a ChatGroq instance for the specified model."""
        config = MODEL_CONFIGS.get(model_name)
        if not config:
            raise ValueError(f"Unknown model: {model_name}")
        
        return ChatGroq(
            api_key=self._api_key,
            model=config.id,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            streaming=config.streaming,
            max_retries=3, # Retry network errors
        )
    
    def check_rate_limit(self, model_name: str, estimated_tokens: int = 100) -> tuple[bool, str]:
        """Check if a model can handle a request."""
        tracker = self._get_tracker(model_name)
        return tracker.can_request(estimated_tokens)
    
    def record_usage(self, model_name: str, tokens_used: int):
        """Record token usage for a model."""
        tracker = self._get_tracker(model_name)
        tracker.record_request(tokens_used)
    
    async def invoke_with_fallback(
        self,
        primary_model: str,
        fallback_model: Optional[str],
        messages: list,
        estimated_tokens: int = 100
    ) -> tuple[str, str, int]:
        """
        Invoke a model with optional fallback on rate limit or error.
        Returns: (response_content, model_used, tokens_used)
        """
        # Try primary model
        can_use, error = self.check_rate_limit(primary_model, estimated_tokens)
        if can_use:
            try:
                llm = self.get_model(primary_model)
                response = await llm.ainvoke(messages)
                tokens = len(response.content) // 4  # Rough estimate
                self.record_usage(primary_model, tokens)
                return response.content, primary_model, tokens
            except Exception as e:
                if fallback_model:
                    pass  # Try fallback
                else:
                    raise e
        
        # Try fallback if available
        if fallback_model:
            can_use, error = self.check_rate_limit(fallback_model, estimated_tokens)
            if can_use:
                llm = self.get_model(fallback_model)
                response = await llm.ainvoke(messages)
                tokens = len(response.content) // 4
                self.record_usage(fallback_model, tokens)
                return response.content, fallback_model, tokens
        
        raise Exception(error or "All models rate limited")


# Global model manager instance
model_manager = ModelManager()


def get_model(model_name: str) -> ChatGroq:
    """Convenience function to get a model instance."""
    return model_manager.get_model(model_name)
