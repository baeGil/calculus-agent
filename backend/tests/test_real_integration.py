import asyncio
import sys
import os
import json
from dotenv import load_dotenv

# Load real environment variables (API Keys)
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.agent.state import create_initial_state
from backend.agent.nodes import planner_node, parallel_executor_node, synthetic_agent_node, reasoning_agent_node
from langchain_core.messages import HumanMessage

# Colors
GREEN = "\033[92m"
BLUE = "\033[94m"
RED = "\033[91m"
RESET = "\033[0m"

def log(msg, color=RESET):
    print(f"{color}{msg}{RESET}")

async def test_real_agent_flow():
    log("🚀 STARTING REAL AGENT INTEGRATION TEST (NO MOCKS)", BLUE)
    log("⚠️  This will consume real API credits (LLM + Wolfram) and generate LangSmith traces.", BLUE)
    
    # Complex query to trigger Planner -> Executor -> Wolfram
    user_query = "Hãy tính đạo hàm của sin(x) và giải phương trình x^2 - 5x + 6 = 0"
    log(f"\n📝 User Input: '{user_query}'", RESET)
    
    state = create_initial_state(session_id="integration_test_live")
    state["messages"] = [HumanMessage(content=user_query)]
    
    # 1. PLANNER NODE
    log("\n1️⃣  Running Planner Node (Real LLM)...", BLUE)
    try:
        state = await planner_node(state)
        plan = state.get("execution_plan")
        if plan:
            log(f"✅ Plan created: {json.dumps(plan, indent=2, ensure_ascii=False)}", GREEN)
        else:
            log("⚠️  No plan generated (Direct response mode?)", RED)
    except Exception as e:
        log(f"❌ Planner Error: {e}", RED)
        return

    # 2. EXECUTOR NODE (If plan exists)
    if state["current_agent"] == "executor":
        log("\n2️⃣  Running Parallel Executor (Real Wolfram/Code)...", BLUE)
        try:
            state = await parallel_executor_node(state)
            results = state.get("question_results", [])
            log(f"✅ Execution complete. Got {len(results)} results.", GREEN)
            for r in results:
                log(f"   - [{r['type'].upper()}] {r.get('content')[:30]}... -> {str(r.get('result'))[:50]}...", RESET)
        except Exception as e:
            log(f"❌ Executor Error: {e}", RED)
            return
            
        # 3. SYNTHESIZER
        log("\n3️⃣  Running Synthesizer (Real LLM)...", BLUE)
        try:
            state = await synthetic_agent_node(state)
            log("✅ Synthesis complete.", GREEN)
        except Exception as e:
            log(f"❌ Synthesizer Error: {e}", RED)
            return
            
    elif state["current_agent"] == "reasoning":
        # Fallback to direct reasoning
        log("\n2️⃣  Running Reasoning Agent (Direct LLM)...", BLUE)
        state = await reasoning_agent_node(state)
        
    log("\n🎯 FINAL AGENT RESPONSE:", BLUE)
    print("-" * 50)
    print(state.get("final_response"))
    print("-" * 50)
    log("\n✅ Test Finished. Check LangSmith for trace 'integration_test_live'.", GREEN)

if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY"):
        log("❌ GROQ_API_KEY not found in env. Cannot run real test.", RED)
    else:
        asyncio.run(test_real_agent_flow())
