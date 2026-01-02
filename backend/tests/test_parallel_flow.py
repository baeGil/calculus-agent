import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.agent.state import create_initial_state, AgentState
from backend.agent.nodes import planner_node, parallel_executor_node, synthetic_agent_node
from langchain_core.messages import AIMessage

async def test_parallel_flow():
    print("🚀 Starting Parallel Flow Verification...")
    
    # 1. Setup Initial State with Mock OCR Text (Simulating 2 images processed)
    state = create_initial_state(session_id="test_session")
    state["ocr_text"] = "[Ảnh 1]: Bài toán đạo hàm...\n\n[Ảnh 2]: Bài toán tích phân..."
    state["messages"] = []  # No user text, just images
    
    print("\n1️⃣  Testing Planner Node...")
    # Mock LLM for Planner to return 2 questions
    with patch("backend.agent.nodes.get_model") as mock_get_model:
        mock_llm = MagicMock()
        async def mock_planner_response(*args, **kwargs):
            return AIMessage(content="""
        ```json
        {
            "questions": [
                {
                    "id": 1,
                    "content": "Tính đạo hàm của x^2",
                    "type": "direct",
                    "tool_input": null
                },
                {
                    "id": 2,
                    "content": "Tính tích phân của sin(x)",
                    "type": "wolfram",
                    "tool_input": "integrate sin(x)"
                }
            ]
        }
        ```
        """)
        mock_llm.ainvoke.side_effect = mock_planner_response
        mock_get_model.return_value = mock_llm
        
        state = await planner_node(state)
        
        if state.get("execution_plan"):
            print("✅ Planner identified questions:", len(state["execution_plan"]["questions"]))
            print("   Plan:", state["execution_plan"])
        else:
            print("❌ Planner failed to generate plan")
            return

    print("\n2️⃣  Testing Parallel Executor Node...")
    # Mock LLM and Wolfram for Executor
    with patch("backend.agent.nodes.get_model") as mock_get_model, \
         patch("backend.agent.nodes.query_wolfram_alpha", new_callable=MagicMock) as mock_wolfram:
        
        # Mock LLM for Direct Question
        mock_llm = MagicMock()
        async def mock_direct_response(*args, **kwargs):
            return AIMessage(content="Đạo hàm của x^2 là 2x")
        mock_llm.ainvoke.side_effect = mock_direct_response
        mock_get_model.return_value = mock_llm
        
        # Mock Wolfram for Wolfram Question
        # Note: query_wolfram_alpha is an async function
        async def mock_wolfram_call(query):
            return True, "integral of sin(x) = -cos(x) + C"
        mock_wolfram.side_effect = mock_wolfram_call
        
        state = await parallel_executor_node(state)
        
        results = state.get("question_results", [])
        print(f"✅ Executed {len(results)} questions")
        for res in results:
            status = "✅" if res.get("result") else "❌"
            print(f"   - Question {res['id']} ({res['type']}): {status} Result: {res.get('result')}")

    print("\n3️⃣  Testing Synthetic Node...")
    # Mock LLM for Synthesizer
    with patch("backend.agent.nodes.get_model") as mock_get_model:
        mock_llm = MagicMock()
        async def mock_synth_response(*args, **kwargs):
            return AIMessage(content="## Bài 1: Đạo hàm... \n\n Result \n\n---\n\n## Bài 2: Tích phân... \n\n Result")
        mock_llm.ainvoke.side_effect = mock_synth_response
        mock_get_model.return_value = mock_llm
        
        state = await synthetic_agent_node(state)
        
        final_resp = state.get("final_response")
        # In multi-question mode, synthetic node MIGHT just format headers if we didn't force LLM usage for synthesis?
        # Actually in my code:
        # if question_results:
        #    combined_response.append(...)
        #    final_response = "\n\n---\n\n".join(...)
        #    return state (IT RETURNS EARLY without calling LLM!)
        
        print("✅ Final Response generated:")
        print("-" * 40)
        print(final_resp)
        print("-" * 40)
        
        if "## Bài 1" in final_resp and "## Bài 2" in final_resp:
             print("✅ Output format is CORRECT (Contains '## Bài 1', '## Bài 2')")
        else:
             print("❌ Output format is INCORRECT")

if __name__ == "__main__":
    asyncio.run(test_parallel_flow())
