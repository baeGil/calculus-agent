"""
State definitions for the LangGraph multi-agent system.
Includes tracking/tracing fields for observability.
"""
from typing import Annotated, Literal, TypedDict, Optional, List
from dataclasses import dataclass, field
from langgraph.graph.message import add_messages
import time


@dataclass
class ToolCall:
    """Record of a tool invocation."""
    tool: str
    input: str
    output: Optional[str] = None
    success: bool = False
    attempt: int = 1
    duration_ms: int = 0
    error: Optional[str] = None


@dataclass
class ModelCall:
    model: str
    agent: str
    tokens_in: int
    tokens_out: int
    duration_ms: int
    success: bool
    error: Optional[str] = None
    tool_calls: Optional[List[dict]] = None


class AgentState(TypedDict):
    """
    State for the multi-agent algebra chatbot.
    Includes user-facing data and tracking/tracing fields.
    """
    # Core messaging
    messages: Annotated[list, add_messages]
    session_id: str
    
    # Image handling (multi-image support)
    image_data: Optional[str]          # Legacy: single image (backward compat)
    image_data_list: List[str]         # NEW: List of base64 encoded images
    ocr_text: Optional[str]            # Legacy: single OCR result
    ocr_results: List[dict]            # NEW: List of {"image_index": int, "text": str}
    
    # Agent flow control
    current_agent: Literal["ocr", "planner", "executor", "synthetic", "wolfram", "code", "done"]
    should_use_tools: bool
    selected_tool: Optional[Literal["wolfram", "code"]]
    _tool_query: Optional[str]  # Internal field to pass query to tool nodes
    
    # Multi-question execution (NEW)
    execution_plan: Optional[dict]     # Planner output: {"questions": [...]}
    question_results: List[dict]       # Results per question: [{"id": 1, "result": "...", "error": None}]
    
    # Tool state
    wolfram_attempts: int      # Max 3 (1 initial + 2 retries)
    code_attempts: int         # Max 3 for codegen
    codefix_attempts: int      # Max 2 for fixing
    tool_result: Optional[str]
    tool_success: bool
    
    # Error handling
    error_message: Optional[str]
    
    # Tracking/Tracing (for observability)
    agents_used: List[str]
    tools_called: List[dict]   # List of ToolCall as dicts
    model_calls: List[dict]    # List of ModelCall as dicts
    total_tokens: int
    start_time: float
    
    # Memory management
    session_token_count: int   # Cumulative tokens used in this session
    context_status: Literal["ok", "warning", "blocked"]
    context_message: Optional[str]  # Warning or error message for UI
    
    # Final response
    final_response: Optional[str]


def create_initial_state(
    session_id: str, 
    image_data: Optional[str] = None,
    image_data_list: Optional[List[str]] = None
) -> AgentState:
    """Create initial state for a new conversation turn."""
    # Determine starting agent based on images
    has_images = bool(image_data) or bool(image_data_list)
    
    return AgentState(
        messages=[],
        session_id=session_id,
        image_data=image_data,
        image_data_list=image_data_list or [],
        ocr_text=None,
        ocr_results=[],
        current_agent="ocr" if has_images else "planner",
        should_use_tools=False,
        selected_tool=None,
        _tool_query=None,
        execution_plan=None,
        question_results=[],
        wolfram_attempts=0,
        code_attempts=0,
        codefix_attempts=0,
        tool_result=None,
        tool_success=False,
        error_message=None,
        agents_used=[],
        tools_called=[],
        model_calls=[],
        total_tokens=0,
        start_time=time.time(),
        session_token_count=0,
        context_status="ok",
        context_message=None,
        final_response=None,
    )


def add_agent_used(state: AgentState, agent_name: str) -> None:
    """Record that an agent was used."""
    if agent_name not in state["agents_used"]:
        state["agents_used"].append(agent_name)


def add_tool_call(state: AgentState, tool_call: ToolCall) -> None:
    """Record a tool call."""
    state["tools_called"].append({
        "tool": tool_call.tool,
        "input": tool_call.input,
        "output": tool_call.output,
        "success": tool_call.success,
        "attempt": tool_call.attempt,
        "duration_ms": tool_call.duration_ms,
        "error": tool_call.error,
    })


def add_model_call(state: AgentState, model_call: ModelCall) -> None:
    """Record a model call."""
    state["model_calls"].append({
        "model": model_call.model,
        "agent": model_call.agent,
        "tokens_in": model_call.tokens_in,
        "tokens_out": model_call.tokens_out,
        "duration_ms": model_call.duration_ms,
        "success": model_call.success,
        "error": model_call.error,
    })
    state["total_tokens"] += model_call.tokens_in + model_call.tokens_out


def get_total_duration_ms(state: AgentState) -> int:
    """Get total duration since start."""
    start_time = state.get("start_time")
    if start_time is None:
        return 0
    return int((time.time() - start_time) * 1000)
