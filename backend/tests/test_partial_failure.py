import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.agent.state import create_initial_state, AgentState
from backend.agent.nodes import planner_node, parallel_executor_node, synthetic_agent_node
from langchain_core.messages import AIMessage

async def test_partial_failure():
    print("🚀 Starting Partial Failure & Rate Limit Verification...")
    
    # 1. Setup Initial State
    state = create_initial_state(session_id="test_partial_fail")
    state["ocr_text"] = "Ảnh chứa 2 câu hỏi test."
    
    # 2. Mock Planner to return 2 questions (1 Direct, 1 Wolfram)
    print("\n1️⃣  Planner: Generating 2 questions...")
    state["execution_plan"] = {
        "questions": [
            {
                "id": 1, 
                "content": "Câu 1: 1+1=?", 
                "type": "direct", 
                "tool_input": None
            },
            {
                "id": 2, 
                "content": "Câu 2: Tích phân phức tạp", 
                "type": "wolfram", 
                "tool_input": "integrate complex function"
            }
        ]
    }
    state["current_agent"] = "executor"

    # 3. Mock Executor with FORCE FAILURE on Wolfram
    print("\n2️⃣  Executor: Simulating Rate Limit on Q2...")
    with patch("backend.agent.nodes.get_model") as mock_get_model, \
         patch("backend.agent.nodes.model_manager.check_rate_limit") as mock_rate_limit:
        
        # Mock LLM for Direct Question (Q1) - SUCCESS
        mock_llm = MagicMock()
        async def mock_direct_response(*args, **kwargs):
            return AIMessage(content="Đáp án câu 1 là 2.")
        mock_llm.ainvoke.side_effect = mock_direct_response
        mock_get_model.return_value = mock_llm
        
        # Mock Rate Limit Check:
        # We need check_rate_limit to return True for Q1 ("kimi-k2" used in direct)
        # BUT return False for Q2 ("wolfram")
        
        def rate_limit_side_effect(model_id):
            if "wolfram" in model_id:
                return False, "Rate limit exceeded for Wolfram"
            return True, None
            
        mock_rate_limit.side_effect = rate_limit_side_effect
        
        # Execute
        state = await parallel_executor_node(state)
        
        results = state.get("question_results", [])
        print(f"\n📊 Execution Results ({len(results)} items):")
        for res in results:
            status = "✅ SUCCEEDED" if res.get("result") else "❌ FAILED"
            error_msg = f" (Error: {res.get('error')})" if res.get("error") else ""
            print(f"   - Question {res['id']} [{res['type']}]: {status}{error_msg}")

    # 4. Verify Synthetic Output
    print("\n3️⃣  Synthesizer: Checking Final Output...")
    
    # Update current_agent manually as normally graph does this
    state["current_agent"] = "synthetic"
    
    with patch("backend.agent.nodes.get_model") as mock_get_model:
        # We don't expect actual LLM call if logic works (returns early), 
        # but mock it just in case logic falls through
        mock_llm = MagicMock()
        async def mock_synth_response(*args, **kwargs):
            return AIMessage(content="Should not be called if handling via list") 
        mock_get_model.return_value = mock_llm
        
        state = await synthetic_agent_node(state)
        
        final_resp = state.get("final_response")
        print("\n📝 FINAL RESPONSE TO USER:")
        print("=" * 50)
        print(final_resp)
        print("=" * 50)
        
        # Validation Logic
        q1_ok = "Đáp án câu 1 là 2" in final_resp or "## Bài 1" in final_resp
        q2_err = "Rate limit" in final_resp and "## Bài 2" in final_resp
        
        if q1_ok and q2_err:
            print("\n✅ TEST PASSED: Partial failure handled correctly! Valid answer + Error message present.")
        else:
            print("\n❌ TEST FAILED: Response did not match expected partial failure pattern.")

if __name__ == "__main__":
    asyncio.run(test_partial_failure())
