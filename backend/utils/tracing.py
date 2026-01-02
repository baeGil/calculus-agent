"""
LangSmith tracing configuration for agent observability.
Provides full tracking of all agent and tool calls.
"""
import os
from typing import Optional
from functools import wraps
import asyncio

# LangSmith environment variables
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "algebra-chatbot")
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "true").lower() == "true"


def setup_langsmith():
    """
    Configure LangSmith tracing.
    Call this at application startup.
    """
    if not LANGSMITH_API_KEY:
        print("⚠️ LANGSMITH_API_KEY not set - tracing disabled")
        return False
    
    # Set environment variables for LangChain tracing
    os.environ["LANGCHAIN_TRACING_V2"] = "true" if LANGSMITH_TRACING else "false"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    
    print(f"✅ LangSmith tracing enabled for project: {LANGSMITH_PROJECT}")
    return True


def get_langsmith_client():
    """Get LangSmith client for custom tracing if needed."""
    if not LANGSMITH_API_KEY:
        return None
    
    try:
        from langsmith import Client
        return Client(api_key=LANGSMITH_API_KEY)
    except ImportError:
        print("⚠️ langsmith package not installed")
        return None


def get_tracer_callbacks():
    """
    Get LangSmith tracer callbacks for use with LangChain/LangGraph.
    Returns empty list if LangSmith not configured.
    """
    if not LANGSMITH_API_KEY or not LANGSMITH_TRACING:
        return []
    
    try:
        from langchain_core.tracers import LangChainTracer
        tracer = LangChainTracer(project_name=LANGSMITH_PROJECT)
        return [tracer]
    except Exception as e:
        print(f"⚠️ Could not create LangSmith tracer: {e}")
        return []


def create_run_config(session_id: str, user_id: Optional[str] = None):
    """
    Create a run configuration dict with metadata for tracing.
    
    Args:
        session_id: Conversation session ID
        user_id: Optional user identifier
        
    Returns:
        Dict with callbacks and metadata for agent invocation
    """
    callbacks = get_tracer_callbacks()
    
    config = {
        "callbacks": callbacks,
        "metadata": {
            "session_id": session_id,
            "user_id": user_id or "anonymous",
        },
        "tags": ["algebra-chatbot", f"session:{session_id}"],
    }
    
    # Add run name for easy identification in LangSmith
    config["run_name"] = f"chat-{session_id[:8]}"
    
    return config


def get_tracing_status() -> dict:
    """Get current LangSmith tracing status."""
    return {
        "enabled": LANGSMITH_TRACING and bool(LANGSMITH_API_KEY),
        "project": LANGSMITH_PROJECT,
        "api_key_set": bool(LANGSMITH_API_KEY),
    }
