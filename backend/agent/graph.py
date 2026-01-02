"""
LangGraph definition for the multi-agent algebra chatbot.
Flow: OCR (if image) -> Planner -> Executor -> Synthetic
"""
from langgraph.graph import StateGraph, END
from backend.agent.state import AgentState
from backend.agent.nodes import (
    ocr_agent_node,
    planner_node,
    parallel_executor_node,
    synthetic_agent_node,
    wolfram_tool_node,
    code_tool_node,
    route_agent,
)


def build_graph() -> StateGraph:
    """Build and compile the LangGraph for the multi-agent algebra chatbot."""
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add all nodes (NO reasoning_agent - deprecated)
    workflow.add_node("ocr_agent", ocr_agent_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", parallel_executor_node)
    workflow.add_node("synthetic_agent", synthetic_agent_node)
    workflow.add_node("wolfram_tool", wolfram_tool_node)
    workflow.add_node("code_tool", code_tool_node)
    
    # Set entry point - OCR first (will pass through if no images)
    workflow.set_entry_point("ocr_agent")
    
    # OCR -> Always route to Planner
    workflow.add_conditional_edges(
        "ocr_agent",
        route_agent,
        {
            "planner": "planner",
            "done": END,
            "end": END,
        }
    )
    
    # Planner -> Executor (if tools needed) OR Done (if all direct answered)
    workflow.add_conditional_edges(
        "planner",
        route_agent,
        {
            "executor": "executor",
            "done": END,  # All-direct case: planner answered directly
            "end": END,
        }
    )
    
    # Executor -> Synthetic (combine results)
    workflow.add_conditional_edges(
        "executor",
        route_agent,
        {
            "synthetic_agent": "synthetic_agent",
            "done": END,
            "end": END,
        }
    )
    
    # Wolfram -> retry, fallback to code, or go to synthetic
    workflow.add_conditional_edges(
        "wolfram_tool",
        route_agent,
        {
            "wolfram_tool": "wolfram_tool",  # Retry
            "code_tool": "code_tool",        # Fallback
            "synthetic_agent": "synthetic_agent",
            "end": END,
        }
    )
    
    # Code -> go to synthetic (after execution/fixes)
    workflow.add_conditional_edges(
        "code_tool",
        route_agent,
        {
            "synthetic_agent": "synthetic_agent",
            "end": END,
        }
    )
    
    # Synthetic -> end
    workflow.add_edge("synthetic_agent", END)
    
    return workflow.compile()


# Create the compiled graph
agent_graph = build_graph()
