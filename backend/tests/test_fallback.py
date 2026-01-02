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

async def test_wolfram_fallback():
    print(f"{BLUE}📌 TEST: Wolfram -> Code Fallback{RESET}")
    
    # Setup State with 1 Wolfram Question
    state = create_initial_state(session_id="test_fallback")
    state["execution_plan"] = {
        "questions": [
            {"id": 1, "type": "wolfram", "content": "Hard Math", "tool_input": "integrate hard"}
        ]
    }
    
    # Mocking
    with patch("backend.agent.nodes.query_wolfram_alpha", new_callable=MagicMock) as mock_wolfram:
        with patch("backend.agent.nodes.CodeTool") as mock_code_tool_cls:
            with patch("backend.agent.nodes.get_model") as mock_get_model:
                
                # 1. Wolfram Fails (success=False)
                # It is an async function, so side_effect should return a coroutine or be an AsyncMock
                # But here we mocked the function directly. Let's use AsyncMock.
                async def mock_wolfram_fail(*args):
                    return False, "Rate Limit Exceeded"
                mock_wolfram.side_effect = mock_wolfram_fail
                
                # 2. Code Tool Succeeds
                mock_tool_instance = MagicMock()
                async def mock_exec(*args):
                    return {"success": True, "output": "Code Result: 42"}
                mock_tool_instance.execute.side_effect = mock_exec
                mock_code_tool_cls.return_value = mock_tool_instance
                
                # 3. LLM for Code Gen (Mocked)
                mock_llm = MagicMock()
                mock_llm.ainvoke.return_value = AIMessage(content="```python\nprint(42)\n```")
                # Async ainvoke
                async def mock_ainvoke(*args): return AIMessage(content="```python\nprint(42)\n```")
                mock_llm.ainvoke.side_effect = mock_ainvoke
                mock_get_model.return_value = mock_llm
                
                # Run Executor
                state = await parallel_executor_node(state)
                
    # Checks
    results = state.get("question_results", [])
    if not results:
        print(f"{RED}❌ No results found{RESET}")
        return False
        
    res = results[0]
    print(f"   [Type]: {res.get('type')}")
    print(f"   [Result]: {res.get('result')}")
    print(f"   [Error]: {res.get('error')}")
    
    # Assertions
    if res.get("type") == "wolfram+code":
        print(f"{GREEN}✅ Fallback triggered (Type changed to wolfram+code){RESET}")
    else:
        print(f"{RED}❌ Fallback logic skipped (Type is {res.get('type')}){RESET}")
        return False
        
    if "Wolfram failed, tried Code fallback" in str(res.get("result")):
        print(f"{GREEN}✅ Fallback note present in result{RESET}")
    else:
        print(f"{RED}❌ Fallback note missing{RESET}")
        return False

    if "Code Result: 42" in str(res.get("result")):
        print(f"{GREEN}✅ Code execution successful{RESET}")
        return True
    
    return False

if __name__ == "__main__":
    asyncio.run(test_wolfram_fallback())
