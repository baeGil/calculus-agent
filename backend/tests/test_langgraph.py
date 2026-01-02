"""
Test cases for LangGraph agent workflow.
Tests state, graph compilation, and routing logic.
"""
import pytest
from backend.agent.state import AgentState
from backend.agent.graph import build_graph, agent_graph
from backend.agent.nodes import should_use_tool


class TestAgentState:
    """Test suite for agent state definitions."""

    def test_state_structure(self):
        """TC-LG-001: AgentState should have all required fields."""
        state: AgentState = {
            "messages": [],
            "session_id": "test-session",
            "current_model": "openai/gpt-oss-120b",
            "tool_retry_count": 0,
            "code_correction_count": 0,
            "wolfram_retry_count": 0,
            "error_message": None,
            "should_fallback": False,
            "image_data": None,
        }
        assert state["session_id"] == "test-session"
        assert state["current_model"] == "openai/gpt-oss-120b"

    def test_state_model_options(self):
        """TC-LG-002: Model should be one of the allowed values."""
        valid_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
        state: AgentState = {
            "messages": [],
            "session_id": "test",
            "current_model": "openai/gpt-oss-120b",
            "tool_retry_count": 0,
            "code_correction_count": 0,
            "wolfram_retry_count": 0,
            "error_message": None,
            "should_fallback": False,
            "image_data": None,
        }
        assert state["current_model"] in valid_models


class TestGraphCompilation:
    """Test suite for LangGraph compilation."""

    def test_graph_compiles(self):
        """TC-LG-003: Graph should compile without errors."""
        graph = build_graph()
        assert graph is not None

    def test_agent_graph_exists(self):
        """TC-LG-004: Pre-compiled agent_graph should exist."""
        assert agent_graph is not None


class TestRoutingLogic:
    """Test suite for graph routing decisions."""

    def test_route_to_fallback_when_should_fallback(self):
        """TC-LG-005: Should route to fallback when flag is set."""
        state: AgentState = {
            "messages": [],
            "session_id": "test",
            "current_model": "openai/gpt-oss-120b",
            "tool_retry_count": 0,
            "code_correction_count": 0,
            "wolfram_retry_count": 0,
            "error_message": "Test error",
            "should_fallback": True,
            "image_data": None,
        }
        result = should_use_tool(state)
        assert result == "fallback"

    def test_route_to_tool_when_pending(self):
        """TC-LG-006: Should route to tool when pending tool exists."""
        state: AgentState = {
            "messages": [],
            "session_id": "test",
            "current_model": "openai/gpt-oss-120b",
            "tool_retry_count": 0,
            "code_correction_count": 0,
            "wolfram_retry_count": 0,
            "error_message": None,
            "should_fallback": False,
            "image_data": None,
            "_pending_tool": "wolfram",
        }
        result = should_use_tool(state)
        assert result == "tool"

    def test_route_to_format_when_tool_result(self):
        """TC-LG-007: Should route to format when tool result exists."""
        state: AgentState = {
            "messages": [],
            "session_id": "test",
            "current_model": "openai/gpt-oss-120b",
            "tool_retry_count": 0,
            "code_correction_count": 0,
            "wolfram_retry_count": 0,
            "error_message": None,
            "should_fallback": False,
            "image_data": None,
            "_tool_result": "x = 5",
        }
        result = should_use_tool(state)
        assert result == "format"

    def test_route_to_end_when_complete(self):
        """TC-LG-008: Should route to end when no pending actions."""
        state: AgentState = {
            "messages": [],
            "session_id": "test",
            "current_model": "openai/gpt-oss-120b",
            "tool_retry_count": 0,
            "code_correction_count": 0,
            "wolfram_retry_count": 0,
            "error_message": None,
            "should_fallback": False,
            "image_data": None,
        }
        result = should_use_tool(state)
        assert result == "end"
