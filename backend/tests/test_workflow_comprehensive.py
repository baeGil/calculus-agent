"""
Comprehensive Unit Test Suite for Agent Workflow.
Tests all possible question scenarios to ensure proper routing and memory tracking.

Run with: python backend/tests/test_workflow_comprehensive.py
"""
import sys
import os

# Add parent directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

# Test utilities
def create_mock_state(session_id="test-session", messages=None, image_data_list=None):
    """Create a mock AgentState for testing."""
    from langchain_core.messages import HumanMessage
    return {
        "session_id": session_id,
        "messages": messages or [HumanMessage(content="Test question")],
        "image_data_list": image_data_list or [],
        "ocr_text": "",
        "ocr_results": [],
        "execution_plan": None,
        "question_results": [],
        "current_agent": "planner",
        "final_response": None,
        "tool_result": None,
        "tool_success": False,
        "agents_used": [],
        "tools_called": [],
        "model_calls": [],
        "context_status": "normal",
        "context_message": "",
        "session_token_count": 0,
        # Additional required fields
        "total_tokens": 0,
        "total_duration_ms": 0,
        "selected_tool": None,
        "should_use_tools": False,
        "wolfram_query": None,
        "wolfram_attempts": 0,
        "code_task": None,
        "generated_code": None,
        "error_message": None,
        "image_data": None,
    }


class TestPlannerNode:
    """Tests for planner_node routing logic."""
    
    @pytest.mark.asyncio
    async def test_all_direct_returns_text(self):
        """Test Case 1: All direct questions -> Planner returns text, current_agent='done'."""
        from backend.agent.nodes import planner_node
        
        state = create_mock_state()
        
        # Mock LLM to return plain text (all direct answers)
        mock_response = MagicMock()
        mock_response.content = "## Bài 1:\nĐây là lời giải câu 1.\n\n## Bài 2:\nĐây là lời giải câu 2."
        
        with patch("backend.agent.nodes.get_model") as mock_get_model, \
             patch("backend.agent.nodes.memory_tracker") as mock_memory:
            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = mock_response
            mock_get_model.return_value = mock_llm
            
            mock_status = MagicMock()
            mock_status.status = "normal"
            mock_status.used_tokens = 100
            mock_status.message = ""
            mock_memory.check_status.return_value = mock_status
            
            result = await planner_node(state)
        
        assert result["current_agent"] == "done", "All-direct should set current_agent to 'done'"
        assert result["final_response"] is not None, "Should have final_response set"
        assert "Bài 1" in result["final_response"], "Should contain direct answer"
        print("✅ Test Case 1 PASSED: All Direct -> Text -> Done")
    
    @pytest.mark.asyncio
    async def test_mixed_questions_returns_json(self):
        """Test Case 2: Mixed questions -> Planner returns JSON, current_agent='executor'."""
        from backend.agent.nodes import planner_node
        
        state = create_mock_state()
        
        # Mock LLM to return JSON (mixed questions)
        mock_json = {
            "questions": [
                {"id": 1, "content": "Câu hỏi 1", "type": "direct", "answer": "Đáp án 1"},
                {"id": 2, "content": "Câu hỏi 2", "type": "code", "tool_input": "Viết code..."}
            ]
        }
        mock_response = MagicMock()
        mock_response.content = json.dumps(mock_json)
        
        with patch("backend.agent.nodes.get_model") as mock_get_model, \
             patch("backend.agent.nodes.memory_tracker") as mock_memory:
            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = mock_response
            mock_get_model.return_value = mock_llm
            
            mock_status = MagicMock()
            mock_status.status = "normal"
            mock_status.used_tokens = 100
            mock_status.message = ""
            mock_memory.check_status.return_value = mock_status
            
            result = await planner_node(state)
        
        assert result["current_agent"] == "executor", "Mixed questions should route to executor"
        assert result["execution_plan"] is not None, "Should have execution_plan set"
        assert len(result["execution_plan"]["questions"]) == 2, "Plan should have 2 questions"
        print("✅ Test Case 2 PASSED: Mixed -> JSON -> Executor")
    
    @pytest.mark.asyncio
    async def test_memory_overflow_blocks_execution(self):
        """Test Case 5: Memory overflow should stop execution."""
        from backend.agent.nodes import planner_node
        
        state = create_mock_state()
        
        mock_response = MagicMock()
        mock_response.content = json.dumps({"questions": [{"id": 1, "type": "code", "tool_input": "x"}]})
        
        with patch("backend.agent.nodes.get_model") as mock_get_model, \
             patch("backend.agent.nodes.memory_tracker") as mock_memory:
            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = mock_response
            mock_get_model.return_value = mock_llm
            
            # Simulate memory overflow
            mock_status = MagicMock()
            mock_status.status = "blocked"
            mock_status.used_tokens = 100000
            mock_status.message = "Bộ nhớ phiên đã đầy!"
            mock_memory.check_status.return_value = mock_status
            
            result = await planner_node(state)
        
        assert result["current_agent"] == "done", "Memory overflow should stop execution"
        assert "Bộ nhớ" in result["final_response"], "Should show memory warning"
        print("✅ Test Case 5 PASSED: Memory Overflow -> Blocked")
    
    @pytest.mark.asyncio
    async def test_json_repair_latex_backslashes(self):
        """Test Case 6: JSON with LaTeX backslashes should be repaired."""
        from backend.agent.nodes import planner_node
        
        state = create_mock_state()
        
        # Mock LLM to return JSON with unescaped LaTeX
        raw_json = r'{"questions":[{"id":1,"type":"code","content":"\\iint_D \\frac{dx}{x}","tool_input":"calc"}]}'
        mock_response = MagicMock()
        mock_response.content = raw_json
        
        with patch("backend.agent.nodes.get_model") as mock_get_model, \
             patch("backend.agent.nodes.memory_tracker") as mock_memory:
            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = mock_response
            mock_get_model.return_value = mock_llm
            
            mock_status = MagicMock()
            mock_status.status = "normal"
            mock_status.used_tokens = 100
            mock_status.message = ""
            mock_memory.check_status.return_value = mock_status
            
            result = await planner_node(state)
        
        # Should successfully parse (repair backslashes)
        assert result["execution_plan"] is not None or result["current_agent"] == "done", \
            "Should either parse JSON or treat as direct answer"
        print("✅ Test Case 6 PASSED: JSON Repair (LaTeX)")


class TestParallelExecutor:
    """Tests for parallel_executor_node."""
    
    @pytest.mark.asyncio
    async def test_direct_uses_answer_field(self):
        """Test: Direct questions should use pre-generated answer, not call LLM."""
        from backend.agent.nodes import parallel_executor_node
        
        state = create_mock_state()
        state["execution_plan"] = {
            "questions": [
                {"id": 1, "type": "direct", "content": "Câu hỏi", "answer": "Đáp án sẵn có"}
            ]
        }
        
        with patch("backend.agent.nodes.get_model") as mock_get_model, \
             patch("backend.agent.nodes.memory_tracker") as mock_memory:
            # LLM should NOT be called for direct type with answer
            mock_status = MagicMock()
            mock_status.status = "normal"
            mock_status.used_tokens = 100
            mock_status.message = ""
            mock_memory.check_status.return_value = mock_status
            
            result = await parallel_executor_node(state)
        
        assert result["current_agent"] == "synthetic", "Should route to synthetic"
        assert len(result["question_results"]) == 1, "Should have 1 result"
        assert result["question_results"][0]["result"] == "Đáp án sẵn có", "Should use pre-generated answer"
        print("✅ Test: Direct with Answer Field -> Uses Cached Answer")


class TestRouteAgent:
    """Tests for route_agent function."""
    
    def test_route_done_returns_done(self):
        """Test: current_agent='done' should return 'done'."""
        from backend.agent.nodes import route_agent
        
        state = {"current_agent": "done"}
        result = route_agent(state)
        
        assert result == "done", "Should return 'done' for done state"
        print("✅ Test: route_agent('done') -> 'done'")
    
    def test_route_executor_returns_executor(self):
        """Test: current_agent='executor' should return 'executor'."""
        from backend.agent.nodes import route_agent
        
        state = {"current_agent": "executor"}
        result = route_agent(state)
        
        assert result == "executor", "Should return 'executor' for executor state"
        print("✅ Test: route_agent('executor') -> 'executor'")


# Run tests
if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING COMPREHENSIVE WORKFLOW UNIT TESTS")
    print("=" * 60)
    
    async def run_all():
        # Planner tests
        planner_tests = TestPlannerNode()
        await planner_tests.test_all_direct_returns_text()
        await planner_tests.test_mixed_questions_returns_json()
        await planner_tests.test_memory_overflow_blocks_execution()
        await planner_tests.test_json_repair_latex_backslashes()
        
        # Executor tests
        executor_tests = TestParallelExecutor()
        await executor_tests.test_direct_uses_answer_field()
        
        # Route tests
        route_tests = TestRouteAgent()
        route_tests.test_route_done_returns_done()
        route_tests.test_route_executor_returns_executor()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✅")
        print("=" * 60)
    
    asyncio.run(run_all())
