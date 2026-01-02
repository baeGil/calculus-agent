import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.agent.state import create_initial_state
from backend.agent.nodes import parallel_executor_node
from langchain_core.messages import AIMessage

# Colors
GREEN = "\033[92m"
BLUE = "\033[94m"
RED = "\033[91m"
RESET = "\033[0m"

async def test_code_smart_retry():
    print(f"{BLUE}📌 TEST: Code Tool Smart Retry (Self-Correction){RESET}")
    
    state = create_initial_state(session_id="test_retry")
    state["execution_plan"] = {
        "questions": [
            {"id": 1, "type": "code", "content": "Fix me", "tool_input": "Run bad code"}
        ]
    }
    
    with patch("backend.agent.nodes.CodeTool") as mock_code_tool_cls:
        with patch("backend.agent.nodes.get_model") as mock_get_model:
            
            # --- MOCK LLM RESPONSES ---
            mock_llm = MagicMock()
            
            # Response 1: Bad Code
            # Response 2: Fixed Code
            async def mock_llm_call(messages):
                content = messages[0].content
                if "LỖI GẶP PHẢI" in content: # Check if it's the FIX prompt
                    print(f"   [LLM Input]: Received Error Feedback -> Generating Fix...")
                    return AIMessage(content="```python\nprint('Fixed')\n```")
                else:
                    print(f"   [LLM Input]: First Attempt -> Generating Bad Code...")
                    return AIMessage(content="```python\nprint(1/0)\n```")
                    
            mock_llm.ainvoke.side_effect = mock_llm_call
            mock_get_model.return_value = mock_llm
            
            # --- MOCK CODE EXECUTOR ---
            mock_tool_instance = MagicMock()
            
            async def mock_exec(code):
                if "1/0" in code:
                    return {"success": False, "error": "ZeroDivisionError"}
                else:
                    return {"success": True, "output": "Fixed Output"}
            
            mock_tool_instance.execute.side_effect = mock_exec
            mock_code_tool_cls.return_value = mock_tool_instance
            
            # --- RUN EXECUTOR ---
            state = await parallel_executor_node(state)
            
    # --- ASSERTIONS ---
    results = state.get("question_results", [])
    if not results:
        print(f"{RED}❌ No results found{RESET}")
        return False
        
    res = results[0]
    result_text = str(res.get("result"))
    
    if "Fixed Output" in result_text:
        print(f"{GREEN}✅ Code succeeded after retry{RESET}")
        return True
    else:
        print(f"{RED}❌ Failed to self-correct. Result: {result_text}, Error: {res.get('error')}{RESET}")
        return False

if __name__ == "__main__":
    asyncio.run(test_code_smart_retry())
