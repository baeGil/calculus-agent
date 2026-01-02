"""
LangGraph node implementations for the multi-agent algebra chatbot.
Agents: ocr_agent, planner, parallel_executor, synthetic_agent
Tools: wolfram_tool_node, code_tool_node
"""
import os
import time
import json
import re
import asyncio
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from backend.agent.state import (
    AgentState, ToolCall, ModelCall,
    add_agent_used, add_tool_call, add_model_call
)
from backend.agent.models import model_manager, get_model
from backend.tools.wolfram import query_wolfram_alpha
from backend.tools.code_executor import CodeTool
from backend.utils.memory import (
    memory_tracker, estimate_tokens, estimate_message_tokens,
    TokenOverflowError, truncate_history_to_fit
)


from backend.agent.prompts import (
    OCR_PROMPT,
    SYNTHETIC_PROMPT,
    CODEGEN_PROMPT,
    CODEGEN_FIX_PROMPT,
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_PROMPT
)


# ============================================================================
# HELPER FUNCTIONS FOR OUTPUT FORMATTING
# ============================================================================

def format_latex_for_markdown(text: str) -> str:
    """
    Format LaTeX content for proper Markdown rendering.
    
    Key principle: 
    - Add paragraph breaks (double newlines) OUTSIDE of $$...$$ blocks
    - NEVER modify content INSIDE $$...$$ blocks (preserves aligned, matrix, etc.)
    - Ensure $$ is on its own line for block rendering
    
    Args:
        text: Raw text containing LaTeX expressions
        
    Returns:
        Formatted text suitable for Markdown rendering
    """
    if not text:
        return text
    
    # Split by $$ to separate math blocks from text
    parts = text.split('$$')
    
    formatted_parts = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # OUTSIDE math block (text content)
            # Add paragraph spacing for better readability
            # But be careful not to add excessive whitespace
            formatted_parts.append(part)
        else:
            # INSIDE math block - preserve exactly as-is
            # Just wrap with $$ and ensure it's on its own line
            formatted_parts.append(f'\n$$\n{part.strip()}\n$$\n')
    
    # Rejoin: even parts are text, odd parts are already formatted with $$
    result = ''
    for i, part in enumerate(formatted_parts):
        if i % 2 == 0:
            result += part
        else:
            # This is the formatted math block, append directly
            result += part
    
    # Clean up excessive whitespace (more than 2 consecutive newlines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result.strip()



# ============================================================================
# AGENT NODES
# ============================================================================

async def ocr_agent_node(state: AgentState) -> AgentState:
    """
    OCR Agent: Extract text from images using vision model.
    Supports multiple images with parallel processing.
    Primary: llama-4-maverick, Fallback: llama-4-scout
    """
    import asyncio
    add_agent_used(state, "ocr_agent")
    
    # Check for images (new list or legacy single image)
    image_list = state.get("image_data_list", [])
    if not image_list and state.get("image_data"):
        image_list = [state["image_data"]]  # Backward compatibility
    
    if not image_list:
        # No images - proceed directly to planner (OCR skipped)
        state["current_agent"] = "planner"
        return state
    
    start_time = time.time()
    primary_model = "llama-4-maverick"
    fallback_model = "llama-4-scout"
    
    async def ocr_single_image(image_data: str, index: int) -> dict:
        """Process a single image and return result dict."""
        content = [
            {"type": "text", "text": OCR_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
        ]
        messages = [HumanMessage(content=content)]
        
        model_used = primary_model
        try:
            # Check rate limit for primary
            can_use, error = model_manager.check_rate_limit(primary_model)
            if not can_use:
                model_used = fallback_model
                can_use, error = model_manager.check_rate_limit(fallback_model)
                if not can_use:
                    return {"image_index": index + 1, "text": None, "error": error}
            
            llm = get_model(model_used)
            response = await llm.ainvoke(messages)
            return {"image_index": index + 1, "text": response.content, "error": None}
            
        except Exception as e:
            return {"image_index": index + 1, "text": None, "error": str(e)}
    
    # Process all images in parallel
    tasks = [ocr_single_image(img, i) for i, img in enumerate(image_list)]
    results = await asyncio.gather(*tasks)
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Store results
    state["ocr_results"] = results
    
    # Build combined OCR text for backward compatibility
    successful_texts = []
    for r in results:
        if r["text"]:
            if len(image_list) > 1:
                successful_texts.append(f"[Ảnh {r['image_index']}]:\n{r['text']}")
            else:
                successful_texts.append(r["text"])
    
    state["ocr_text"] = "\n\n".join(successful_texts) if successful_texts else None
    
    # Log model calls
    add_model_call(state, ModelCall(
        model=primary_model,
        agent="ocr_agent",
        tokens_in=500 * len(image_list),
        tokens_out=sum(len(r.get("text", "") or "") // 4 for r in results),
        duration_ms=duration_ms,
        success=any(r["text"] for r in results)
    ))
    
    # Report any errors but continue
    errors = [f"Ảnh {r['image_index']}: {r['error']}" for r in results if r["error"]]
    if errors and not successful_texts:
        state["error_message"] = "OCR failed: " + "; ".join(errors)
    
    # Route to planner for multi-question analysis
    state["current_agent"] = "planner"
    return state


async def planner_node(state: AgentState) -> AgentState:
    """
    Planner Node: Analyze all content (text + OCR) and identify individual questions.
    Creates an execution plan for parallel processing.
    NOW WITH FULL CONVERSATION HISTORY FOR MEMORY!
    """
    import asyncio
    add_agent_used(state, "planner")
    
    start_time = time.time()
    model_name = "kimi-k2"
    
    # Get user text from last message
    user_text = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_text = msg.content if isinstance(msg.content, str) else str(msg.content)
            break
    
    ocr_text = state.get("ocr_text") or "(Không có ảnh)"
    
    # Build user prompt for current request
    current_prompt = PLANNER_USER_PROMPT.format(
        user_text=user_text or "(Không có text)",
        ocr_text=ocr_text
    )
    
    # ========================================
    # NEW: Build messages WITH conversation history
    # ========================================
    llm_messages = []
    
    # 1. Add system prompt with memory-awareness instructions
    llm_messages.append(SystemMessage(content=PLANNER_SYSTEM_PROMPT))
    
    # 2. Add truncated conversation history (smart token management)
    history_messages = state.get("messages", [])
    # Exclude the last message since we'll add current_prompt separately
    if history_messages:
        history_to_include = history_messages[:-1] if len(history_messages) > 1 else []
    else:
        history_to_include = []
    
    # Truncate history to fit within token limits
    system_tokens = estimate_tokens(PLANNER_SYSTEM_PROMPT)
    current_tokens = estimate_tokens(current_prompt)
    truncated_history = truncate_history_to_fit(
        history_to_include,
        system_tokens=system_tokens,
        current_tokens=current_tokens,
        max_context_tokens=200000  # Leave room within 256K limit
    )
    
    # Add history messages
    for msg in truncated_history:
        llm_messages.append(msg)
    
    # 3. Add current user request as last message
    llm_messages.append(HumanMessage(content=current_prompt))
    
    # Calculate total input tokens for tracking
    total_input_tokens = system_tokens + estimate_message_tokens(truncated_history) + current_tokens
    
    try:
        llm = get_model(model_name)
        response = await llm.ainvoke(llm_messages)
        content = response.content.strip()
        
        duration_ms = int((time.time() - start_time) * 1000)
        add_model_call(state, ModelCall(
            model=model_name,
            agent="planner",
            tokens_in=total_input_tokens,
            tokens_out=len(content) // 4,
            duration_ms=duration_ms,
            success=True
        ))
        
        # Parse JSON from response
        # Handle markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        try:
            # Try to parse JSON (Mixed/Tool Case)
            plan = json.loads(content)
        except json.JSONDecodeError:
            try:
                # Try repair: Fix invalid escapes for LaTeX (e.g., \frac -> \\frac)
                # Matches backslash NOT followed by valid JSON escape chars (excluding \\ itself)
                fixed_content = re.sub(r'\\(?![unrtbf"\/])', r'\\\\', content)
                plan = json.loads(fixed_content)
            except Exception:
                # If JSON parsing fails completely, try Regex Fallback
                # This catches cases where LLM returns valid-looking JSON but with syntax errors
                if content.strip().startswith("{") and '"questions"' in content:
                    # Attempt to extract answers using Regex
                    # Pattern: "answer": "..." (handling escaped quotes is hard in regex, simplified)
                    import re
                    # Extract individual question blocks (simplified assumption)
                    # Use a rough scan for "answer": "..."
                    # Find all "answer": "(.*?)" where content is non-greedy until next quote
                    # Note: this is fragile but better than raw JSON
                    
                    # Better fallback: Just treat it as raw text but tell user format error
                    pass

                # If JSON fails, it means Planner returned Direct Text Answer (All Direct Case)
                # OR malformed JSON that looks like text.
                
                # Check directly if it looks like the raw JSON output
                if content.strip().startswith('{') and '"type": "direct"' in content:
                     # This is likely the malformed JSON case the user saw
                     # Use Regex to extract answers
                     answers = re.findall(r'"answer":\s*"(.*?)(?<!\\)"', content, re.DOTALL)
                     if answers:
                         # Unescape the extracted string somewhat
                         final_parts = []
                         for i, ans in enumerate(answers):
                             # excessive backslashes might be present
                             clean_ans = ans.replace('\\"', '"').replace('\\n', '\n')
                             # Use helper to properly format LaTeX for Markdown
                             formatted_answer = format_latex_for_markdown(clean_ans)
                             final_parts.append(f"## Bài {i+1}:\n{formatted_answer}\n")
                         
                         final_response = "\n".join(final_parts)
                         
                         # Update memory & return
                         session_id = state["session_id"]
                         tokens_in = total_input_tokens
                         tokens_out = len(content) // 4
                         total_turn_tokens = tokens_in + tokens_out
                         memory_tracker.add_usage(session_id, total_turn_tokens)
                         new_status = memory_tracker.check_status(session_id)
                         state["session_token_count"] = new_status.used_tokens
                         state["context_status"] = new_status.status
                         state["context_message"] = new_status.message
                         
                         state["execution_plan"] = None
                         state["final_response"] = final_response
                         state["messages"].append(AIMessage(content=final_response))
                         state["current_agent"] = "done"
                         return state

                # Update memory tracking (consistent with other agents)
                session_id = state["session_id"]
                tokens_in = total_input_tokens
                tokens_out = len(content) // 4
                total_turn_tokens = tokens_in + tokens_out
                memory_tracker.add_usage(session_id, total_turn_tokens)
                new_status = memory_tracker.check_status(session_id)
                state["session_token_count"] = new_status.used_tokens
                state["context_status"] = new_status.status
                state["context_message"] = new_status.message
                
                # Check for memory overflow
                if new_status.status == "blocked":
                    state["final_response"] = new_status.message
                    state["current_agent"] = "done"
                    return state
                
                # CRITICAL: Check if content looks like JSON with tool questions
                # If so, try to route to executor instead of displaying raw JSON
                if content.strip().startswith('{') and '"questions"' in content:
                    # This is JSON that failed parsing but contains questions
                    # Try one more time with aggressive repair
                    try:
                        # Remove control characters and fix common issues
                        import re as regex_module
                        aggressive_fix = content
                        # Fix unescaped backslashes in LaTeX (including doubling existing ones)
                        aggressive_fix = regex_module.sub(r'\\(?![unrtbf"\/])', r'\\\\', aggressive_fix)
                        # Try parsing
                        parsed_plan = json.loads(aggressive_fix)
                        if parsed_plan.get("questions"):
                            # Success! Route to executor
                            state["execution_plan"] = parsed_plan
                            state["current_agent"] = "executor"
                            return state
                    except:
                        pass
                    
                    # If still unparseable, try manual extraction
                    # Extract questions array manually with regex
                    try:
                        # Find id, content, type, tool_input for each question
                        q_matches = re.findall(r'"id"\s*:\s*(\d+).*?"content"\s*:\s*"([^"]*)".*?"type"\s*:\s*"(direct|wolfram|code)"', content, re.DOTALL)
                        if q_matches:
                            manual_plan = {"questions": []}
                            for q_id, q_content, q_type in q_matches:
                                q_entry = {"id": int(q_id), "content": q_content, "type": q_type, "answer": None}
                                if q_type in ["wolfram", "code"]:
                                    q_entry["tool_input"] = q_content
                                manual_plan["questions"].append(q_entry)
                            
                            state["execution_plan"] = manual_plan
                            state["current_agent"] = "executor"
                            return state
                    except:
                        pass
                    
                    # Last resort: Show error message instead of raw JSON
                    state["execution_plan"] = None
                    state["final_response"] = "Xin lỗi, hệ thống gặp lỗi khi phân tích câu hỏi. Vui lòng thử lại hoặc diễn đạt câu hỏi khác đi."
                    state["current_agent"] = "done"
                    return state
                
                # Treat as final answer (only if NOT JSON)
                state["execution_plan"] = None
                state["final_response"] = content
                state["messages"].append(AIMessage(content=content))
                state["current_agent"] = "done"
                return state

        # If JSON Valid -> Check if all questions are direct (LLM didn't follow prompt correctly)
        all_direct = all(q.get("type") == "direct" for q in plan.get("questions", []))
        
        if all_direct:
            # LLM returned JSON for all-direct case (should have returned text)
            # Check if answers are provided
            questions = plan.get("questions", [])
            has_valid_answers = all(q.get("answer") for q in questions)
            
            if has_valid_answers:
                # Answers are in the JSON, extract them
                final_parts = []
                for q in questions:
                    q_id = q.get("id", "?") 
                    q_answer = q.get("answer", "")
                    # Use helper to properly format LaTeX for Markdown
                    formatted_answer = format_latex_for_markdown(q_answer)
                    final_parts.append(f"## Bài {q_id}:\n{formatted_answer}\n")
                final_response = "\n".join(final_parts)
            else:
                # No answers provided - LLM didn't follow prompt correctly
                # Route to executor to re-process these as direct questions
                # For now, mark as needing tool (wolfram) so they get solved
                for q in questions:
                    if not q.get("answer"):
                        q["type"] = "wolfram"  # Force tool use
                        if not q.get("tool_input"):
                            q["tool_input"] = q.get("content", "")
                
                state["execution_plan"] = plan
                state["current_agent"] = "executor"
                
                # Update memory tracking
                session_id = state["session_id"]
                tokens_in = total_input_tokens
                tokens_out = len(content) // 4
                total_turn_tokens = tokens_in + tokens_out
                memory_tracker.add_usage(session_id, total_turn_tokens)
                new_status = memory_tracker.check_status(session_id)
                state["session_token_count"] = new_status.used_tokens
                state["context_status"] = new_status.status
                state["context_message"] = new_status.message
                return state
            
            state["execution_plan"] = None
            state["final_response"] = final_response
            state["messages"].append(AIMessage(content=final_response))
            state["current_agent"] = "done"
            
            # Update memory tracking
            session_id = state["session_id"]
            tokens_in = total_input_tokens
            tokens_out = len(content) // 4
            total_turn_tokens = tokens_in + tokens_out
            memory_tracker.add_usage(session_id, total_turn_tokens)
            new_status = memory_tracker.check_status(session_id)
            state["session_token_count"] = new_status.used_tokens
            state["context_status"] = new_status.status
            state["context_message"] = new_status.message
            
            return state
        
        # Mixed/Tool Case -> Route to Executor
        state["execution_plan"] = plan
        state["current_agent"] = "executor"
        
        # Update memory tracking (consistent with other agents)
        session_id = state["session_id"]
        tokens_in = total_input_tokens
        tokens_out = len(content) // 4
        total_turn_tokens = tokens_in + tokens_out
        memory_tracker.add_usage(session_id, total_turn_tokens)
        new_status = memory_tracker.check_status(session_id)
        state["session_token_count"] = new_status.used_tokens
        state["context_status"] = new_status.status
        state["context_message"] = new_status.message
        
        # Check for memory overflow
        if new_status.status == "blocked":
            state["final_response"] = new_status.message
            state["current_agent"] = "done"
    except Exception as e:
        add_model_call(state, ModelCall(
            model=model_name,
            agent="planner",
            tokens_in=0,
            tokens_out=0,
            duration_ms=int((time.time() - start_time) * 1000),
            success=False,
            error=str(e)
        ))
        # Fallback: Planner failed, return error to user
        error_msg = str(e)
        user_friendly_msg = "Xin lỗi, đã có lỗi xảy ra khi phân tích câu hỏi."
        
        if "413" in error_msg or "Request too large" in error_msg:
            user_friendly_msg = "Nội dung lịch sử trò chuyện vượt quá giới hạn mô hình. Vui lòng tạo hội thoại mới để tiếp tục."
        elif "rate_limit" in error_msg or "TPM" in error_msg:
            user_friendly_msg = "Hệ thống đang quá tải (Rate Limit). Bạn vui lòng đợi khoảng 10-20 giây rồi thử lại nhé!"
        elif "context_length_exceeded" in error_msg:
            user_friendly_msg = "Hội thoại đã quá dài. Vui lòng tạo hội thoại mới để tiếp tục."
        else:
            user_friendly_msg = f"Xin lỗi, đã có lỗi kỹ thuật: {error_msg}."

        state["execution_plan"] = None
        state["final_response"] = user_friendly_msg
        state["current_agent"] = "done"
    
    return state


async def parallel_executor_node(state: AgentState) -> AgentState:
    """
    Parallel Executor: Execute multiple questions in parallel.
    - Direct questions: Process with kimi-k2
    - Wolfram questions: Call API in parallel
    - Code questions: Execute code in parallel
    """
    import asyncio
    add_agent_used(state, "parallel_executor")
    
    plan = state.get("execution_plan")
    if not plan or not plan.get("questions"):
        # No plan - planner should have handled this, go to done
        state["current_agent"] = "done"
        return state
    
    questions = plan["questions"]
    start_time = time.time()
    
    async def execute_single_question(q: dict) -> dict:
        """Execute a single question and return result."""
        q_id = q.get("id", 0)
        q_type = q.get("type", "direct")
        q_content = q.get("content", "")
        q_tool_input = q.get("tool_input", "")
        
        result = {
            "id": q_id,
            "content": q_content,
            "type": q_type,
            "result": None,
            "error": None
        }
        
        async def solve_with_code(task_description: str, retries: int = 3) -> dict:
            """Helper to run code tool with retries."""
            code_tool = CodeTool()
            out = {"result": None, "error": None}
            last_code = ""
            last_error = ""
            
            for attempt in range(retries):
                try:
                    llm = get_model("qwen3-32b")
                    
                    # SMART RETRY: If we have an error, ask LLM to FIX it
                    if attempt > 0 and last_error:
                        code_prompt = CODEGEN_FIX_PROMPT.format(code=last_code, error=last_error)
                    else:
                        code_prompt = CODEGEN_PROMPT.format(task=task_description)
                        
                    code_response = await llm.ainvoke([HumanMessage(content=code_prompt)])
                    
                    # Extract code
                    code = code_response.content
                    if "```python" in code:
                        code = code.split("```python")[1].split("```")[0]
                    elif "```" in code:
                        code = code.split("```")[1].split("```")[0]
                    
                    last_code = code # Save for next retry if needed
                    
                    # Execute
                    exec_result = code_tool.execute(code)
                    if exec_result.get("success"):
                        out["result"] = exec_result.get("output", "")
                        return out
                    else:
                        last_error = exec_result.get("error", "Unknown error")
                        if attempt == retries - 1:
                            out["error"] = last_error
                except Exception as e:
                    last_error = str(e)
                    if attempt == retries - 1:
                        out["error"] = str(e)
            return out
        
        try:
            if q_type == "wolfram":
                wolfram_done = False
                # Call Wolfram Alpha (with retry logic)
                # Call Wolfram Alpha (1 attempt only)
                for attempt in range(1):
                    try:
                        can_use, err = model_manager.check_rate_limit("wolfram")
                        if not can_use:
                            if attempt == 0: break 
                            await asyncio.sleep(1)
                            continue
                        
                        wolfram_success, wolfram_result = await query_wolfram_alpha(q_tool_input)
                        if wolfram_success:
                            result["result"] = wolfram_result
                            wolfram_done = True
                            break
                        else:
                            # Treat logical failure as exception to trigger retry/fallback
                            if attempt == 0: raise Exception(wolfram_result)
                    except Exception as e:
                        if attempt == 0:
                            result["error"] = f"Wolfram failed: {str(e)}"
                        await asyncio.sleep(0.5)
                
                # --- FALLBACK TO CODE IF WOLFRAM FAILED ---
                if not wolfram_done:
                    # Append status to result
                    fallback_note = f"\n(Wolfram failed, tried Code fallback)"
                    
                    code_out = await solve_with_code(q_tool_input)
                    if code_out["result"]:
                        result["result"] = code_out["result"] + fallback_note
                        result["error"] = None # Clear error if fallback succeeded
                        result["type"] = "wolfram+code" # Indicate hybrid path
                    else:
                        result["error"] += f" | Code Fallback also failed: {code_out['error']}"

            elif q_type == "code":
                # Execute code directly
                code_out = await solve_with_code(q_tool_input)
                result["result"] = code_out["result"]
                result["error"] = code_out["error"]

            else:  # direct
                # User Optimization: If planner provided answer, use it directly (Save API)
                if q.get("answer"):
                    result["result"] = q.get("answer")
                else:
                    # Fallback: Solve directly with kimi-k2 (if planner forgot answer)
                    llm = get_model("kimi-k2")
                    solve_prompt = f"Giải bài toán sau một cách chi tiết:\n{q_content}"
                    response = await llm.ainvoke([
                        SystemMessage(content="Bạn là chuyên gia giải toán. Trả lời ngắn gọn, đúng trọng tâm."),
                        HumanMessage(content=solve_prompt)
                    ])
                    result["result"] = format_latex_for_markdown(response.content) # Direct result
                
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    # Execute all questions in parallel
    tasks = [execute_single_question(q) for q in questions]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results and collect metrics
    question_results = []
    total_tokens_in = 0
    total_tokens_out = 0
    
    for i, r in enumerate(results):
        q = questions[i]
        q_type = q.get("type", "direct")
        
        # Prepare result entry
        res_entry = {
            "id": q.get("id", i+1),
            "content": q.get("content", ""),
            "result": None,
            "error": None,
            "type": q_type
        }

        if isinstance(r, Exception):
            error_msg = str(r)
            if "413" in error_msg or "Request too large" in error_msg:
                friendly = "Nội dung quá dài, vui lòng gửi ngắn hơn."
            elif "rate_limit" in error_msg or "TPM" in error_msg:
                friendly = "Rate Limit (Quá tải), vui lòng đợi giây lát."
            else:
                friendly = f"Lỗi kỹ thuật: {error_msg}"
            
            res_entry["error"] = friendly
            success = False
            r_content = friendly
        else:
            # r is the result dict from execute_single_question
            res_entry.update(r)
            success = not bool(r.get("error"))
            r_content = str(r.get("result", ""))
            
            # Use friendly error if present in result dict
            raw_err = r.get("error")
            if raw_err:
                error_msg = str(raw_err)
                if "413" in error_msg or "Request too large" in error_msg:
                    friendly = "Nội dung quá dài, vui lòng gửi ngắn hơn."
                elif "rate_limit" in error_msg or "TPM" in error_msg:
                    friendly = "Rate Limit (Quá tải), vui lòng đợi giây lát."
                else:
                    friendly = f"Lỗi kỹ thuật: {error_msg}"
                
                res_entry["error"] = friendly
                r_content = friendly

        question_results.append(res_entry)
        
        # Add individual model call trace for each parallel task
        # This allows the frontend to show "Wolfram", "Code", "Kimi" calls clearly
        
        # Estimate tokens for metrics (rough check)
        t_in = len(q.get("content", "")) // 4
        t_out = len(r_content) // 4
        total_tokens_in += t_in
        total_tokens_out += t_out
        
        model_name_trace = "unknown"
        if q_type == "wolfram": model_name_trace = "wolfram-alpha"
        elif q_type == "code": model_name_trace = "python-code-executor"
        else: model_name_trace = "kimi-k2"

        add_model_call(state, ModelCall(
            model=model_name_trace,
            agent=f"parallel_executor_q{res_entry['id']}",
            tokens_in=t_in,
            tokens_out=t_out,
            duration_ms=int((time.time() - start_time) * 1000), # Approx sharing total time
            success=success,
            tool_calls=[{
                "tool": q_type,
                "input": q.get("tool_input") or q.get("content"),
                "output": r_content[:200] + "..." if len(r_content) > 200 else r_content
            }]
        ))
    
    state["question_results"] = question_results
    
    # --- UI COMPATIBILITY FIX ---
    # Populate legacy fields so the Tracing UI (which expects single tool per turn) shows SOMETHING.
    # We aggregate all parallel results into a single string.
    
    start_time_ms = int(start_time * 1000)
    
    # 1. Selected Tool
    tool_names = list(set(r["type"] for r in question_results))
    state["selected_tool"] = f"parallel({','.join(tool_names)})"
    state["should_use_tools"] = True
    
    # 2. Tool Result (Aggregated)
    agg_result = []
    for r in question_results:
         status = "✅" if not r.get("error") else "❌"
         val = r.get("result") or r.get("error")
         agg_result.append(f"[{status} {r['type'].upper()}]: {str(val)[:100]}...")
    state["tool_result"] = "\n".join(agg_result)
    
    
    # 3. Tools Called (List of ToolCall objects)
    tools_called_list = []
    for r in question_results:
        tools_called_list.append({
             "tool": r["type"],
             "tool_input": str(questions[next((i for i, q in enumerate(questions) if q.get("id") == r["id"]), 0)].get("tool_input", "") or r.get("content")),
             "tool_output": str(r.get("result") or r.get("error"))
        })
    state["tools_called"] = tools_called_list
    state["tool_success"] = any(not r.get("error") for r in question_results)
    
    # ---------------------------
    
    duration_ms = int((time.time() - start_time) * 1000)
    add_model_call(state, ModelCall(
        model="parallel_orchestrator",
        agent="parallel_executor",
        tokens_in=total_tokens_in,
        tokens_out=total_tokens_out,
        duration_ms=duration_ms,
        success=state["tool_success"]
    ))
    
    # Go to synthesizer to combine results
    state["current_agent"] = "synthetic"
    return state


# NOTE: reasoning_agent_node has been DEPRECATED and REMOVED.
# The workflow now flows: OCR -> Planner -> Executor -> Synthetic
# (See user's workflow diagram for reference)

async def synthetic_agent_node(state: AgentState) -> AgentState:
    """
    Synthetic Agent: Synthesize tool results into final response.
    Handles both single-tool results and multi-question parallel results.
    Uses kimi-k2.
    """
    add_agent_used(state, "synthetic_agent")
    
    start_time = time.time()
    model_name = "kimi-k2"
    session_id = state["session_id"]
    
    # Check memory status before processing
    mem_status = memory_tracker.check_status(session_id)
    if mem_status.status == "blocked":
        state["context_status"] = "blocked"
        state["context_message"] = mem_status.message
        state["final_response"] = mem_status.message
        state["current_agent"] = "done"
        return state
    
    # Check if we have multi-question results from parallel executor
    question_results = state.get("question_results", [])
    
    if question_results:
        # Multi-question mode: combine all results
        # Use LLM to synthesize a natural response instead of raw concatenation
        
        # Prepare context for synthesis
        results_context = []
        for r in question_results:
             q_id = r.get("id", 0)
             q_content = r.get("content", "")
             q_result = r.get("result", "Không có kết quả")
             q_error = r.get("error")
             
             status = "Thành công" if not q_error else f"Lỗi: {q_error}"
             results_context.append(f"--- BÀI TOÁN {q_id} ---\nNội dung: {q_content}\nTrạng thái: {status}\nKết quả gốc:\n{q_result}\n\n")
             
        combined_context = "".join(results_context)
        
        # Get original question text for context
        original_q_text = "Nhiều câu hỏi (xem chi tiết bên trên)"
        if state.get("ocr_text"):
             original_q_text = f"[OCR]: {state['ocr_text']}"
        elif state["messages"]:
             for m in reversed(state["messages"]):
                  if isinstance(m, HumanMessage):
                       original_q_text = str(m.content)
                       break

        # Use Standard SYNTHETIC_PROMPT
        synth_prompt = SYNTHETIC_PROMPT.format(
            tool_result=combined_context,
            original_question=original_q_text
        )
        
        # ========================================
        # NEW: Include recent conversation history for contextual synthesis
        # ========================================
        llm_messages = [
            SystemMessage(content="""Bạn là chuyên gia toán học Việt Nam. Hãy giải thích lời giải một cách sư phạm, dễ hiểu.
            
VỀ BỘ NHỚ HỘI THOẠI:
- Bạn có thể tham chiếu đến các câu hỏi trước đó trong hội thoại.
- Nếu người dùng đề cập đến "bài trước", "câu đó", hãy hiểu ngữ cảnh.
- Trả lời tự nhiên như một cuộc trò chuyện liên tục."""),
        ]
        
        # Add recent conversation history (last 3 turns = 6 messages)
        recent_history = state.get("messages", [])[-6:]
        for msg in recent_history:
            llm_messages.append(msg)
        
        # Add synthesis prompt
        llm_messages.append(HumanMessage(content=synth_prompt))
        
        try:
             llm = get_model("kimi-k2")
             response = await llm.ainvoke(llm_messages)
             final_response = format_latex_for_markdown(response.content)
        except Exception as e:
             # Fallback manual synthesis if LLM fails
             error_msg = str(e)
             if "413" in error_msg or "Request too large" in error_msg:
                 friendly_err = "Nội dung quá dài để tổng hợp."
             elif "rate_limit" in error_msg or "TPM" in error_msg:
                 friendly_err = "Hệ thống đang bận (Rate Limit)."
             else:
                 friendly_err = f"Lỗi kỹ thuật: {error_msg}"
                 
             final_response = f"**Kết quả (Tổng hợp tự động thất bại do {friendly_err}):**\n\n" + combined_context

        state["final_response"] = final_response
        state["messages"].append(AIMessage(content=final_response))
        state["current_agent"] = "done"
        
        # Update memory
        tokens_out = len(final_response) // 4
        memory_tracker.add_usage(session_id, tokens_out)
        new_status = memory_tracker.check_status(session_id)
        state["session_token_count"] = new_status.used_tokens
        state["context_status"] = new_status.status
        state["context_message"] = new_status.message
        
        return state
    
    # Single-question mode: original logic
    # Get original question
    original_question = ""
    if state["messages"]:
        for msg in state["messages"]:
            if hasattr(msg, "content") and isinstance(msg, HumanMessage):
                original_question = msg.content if isinstance(msg.content, str) else str(msg.content)
                break
    
    # Add OCR context if available
    if state.get("ocr_text"):
        original_question = f"[Từ ảnh]: {state['ocr_text']}\n\n{original_question}"
    
    # Build prompt
    tool_result = state.get("tool_result", "Không có kết quả")
    if not state.get("tool_success"):
        tool_result = f"[Công cụ thất bại]: {state.get('error_message', 'Unknown error')}\n\nHãy cố gắng trả lời dựa trên kiến thức của bạn."
    
    prompt = SYNTHETIC_PROMPT.format(
        tool_result=tool_result,
        original_question=original_question
    )
    
    messages = [HumanMessage(content=prompt)]
    tokens_in = estimate_tokens(prompt)
    
    try:
        llm = get_model(model_name)
        response = await llm.ainvoke(messages)
        
        duration_ms = int((time.time() - start_time) * 1000)
        tokens_out = len(response.content) // 4
        
        add_model_call(state, ModelCall(
            model=model_name,
            agent="synthetic_agent",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duration_ms=duration_ms,
            success=True
        ))
        
        # Update session memory tracker
        total_turn_tokens = tokens_in + tokens_out
        memory_tracker.add_usage(session_id, total_turn_tokens)
        new_status = memory_tracker.check_status(session_id)
        state["session_token_count"] = new_status.used_tokens
        state["context_status"] = new_status.status
        state["context_message"] = new_status.message
        
        # Format the synthesis with standard helper
        formatted_response = format_latex_for_markdown(response.content)
        
        state["final_response"] = formatted_response
        state["messages"].append(AIMessage(content=formatted_response))
        state["current_agent"] = "done"
        
    except Exception as e:
        # Fallback to raw tool result if synthesis fails
        fallback_response = f"**Kết quả tính toán:**\n{state.get('tool_result', 'Không có kết quả')}"
        state["final_response"] = fallback_response
        state["messages"].append(AIMessage(content=fallback_response))
        state["current_agent"] = "done"
    
    return state


# ============================================================================
# TOOL NODES
# ============================================================================

async def wolfram_tool_node(state: AgentState) -> AgentState:
    """
    Wolfram Tool: Query Wolfram Alpha.
    Max 3 attempts (1 initial + 2 retries).
    """
    add_agent_used(state, "wolfram_tool")
    
    query = state.get("_tool_query", "")
    state["wolfram_attempts"] += 1
    
    start_time = time.time()
    success, result = await query_wolfram_alpha(query)
    duration_ms = int((time.time() - start_time) * 1000)
    
    tool_call = ToolCall(
        tool="wolfram",
        input=query,
        output=result if success else None,
        success=success,
        attempt=state["wolfram_attempts"],
        duration_ms=duration_ms,
        error=None if success else result
    )
    add_tool_call(state, tool_call)
    
    if success:
        state["tool_result"] = result
        state["tool_success"] = True
        state["current_agent"] = "synthetic"
    else:
        if state["wolfram_attempts"] < 1:
            # Retry
            state["current_agent"] = "wolfram"
        else:
            # Fallback to code tool
            state["selected_tool"] = "code"
            state["current_agent"] = "code"
    
    return state


async def code_tool_node(state: AgentState) -> AgentState:
    """
    Code Tool: Generate and execute Python code.
    codegen_agent: qwen3-32b
    codefix_agent: gpt-oss-120b (max 2 fixes)
    """
    add_agent_used(state, "code_tool")
    
    task = state.get("_tool_query", "")
    state["code_attempts"] += 1
    
    code_tool = CodeTool()
    
    start_time = time.time()
    
    # Generate code using qwen3-32b
    codegen_start = time.time()
    try:
        llm = get_model("qwen3-32b")
        prompt = CODEGEN_PROMPT.format(task=task)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        code = _extract_code(response.content)
        
        add_model_call(state, ModelCall(
            model="qwen3-32b",
            agent="codegen_agent",
            tokens_in=len(prompt) // 4,
            tokens_out=len(response.content) // 4,
            duration_ms=int((time.time() - codegen_start) * 1000),
            success=True
        ))
    except Exception as e:
        add_model_call(state, ModelCall(
            model="qwen3-32b",
            agent="codegen_agent",
            tokens_in=0,
            tokens_out=0,
            duration_ms=int((time.time() - codegen_start) * 1000),
            success=False,
            error=str(e)
        ))
        state["error_message"] = f"Code generation failed: {str(e)}"
        state["tool_success"] = False
        state["current_agent"] = "synthetic"
        return state
    
    # Execute code with correction loop (max 2 fixes)
    exec_result = code_tool.execute(code)
    
    while not exec_result["success"] and state["codefix_attempts"] < 2:
        state["codefix_attempts"] += 1
        
        # Fix code using gpt-oss-120b
        fix_start = time.time()
        try:
            llm = get_model("gpt-oss-120b")
            fix_prompt = CODEGEN_FIX_PROMPT.format(code=code, error=exec_result["error"])
            response = await llm.ainvoke([HumanMessage(content=fix_prompt)])
            code = _extract_code(response.content)
            
            add_model_call(state, ModelCall(
                model="gpt-oss-120b",
                agent="codefix_agent",
                tokens_in=len(fix_prompt) // 4,
                tokens_out=len(response.content) // 4,
                duration_ms=int((time.time() - fix_start) * 1000),
                success=True
            ))
            
            exec_result = code_tool.execute(code)
            
        except Exception as e:
            add_model_call(state, ModelCall(
                model="gpt-oss-120b",
                agent="codefix_agent",
                tokens_in=0,
                tokens_out=0,
                duration_ms=int((time.time() - fix_start) * 1000),
                success=False,
                error=str(e)
            ))
            break
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    tool_call = ToolCall(
        tool="code",
        input=task,
        output=exec_result.get("output") if exec_result["success"] else None,
        success=exec_result["success"],
        attempt=state["code_attempts"],
        duration_ms=duration_ms,
        error=exec_result.get("error") if not exec_result["success"] else None
    )
    add_tool_call(state, tool_call)
    
    if exec_result["success"]:
        state["tool_result"] = exec_result["output"]
        state["tool_success"] = True
    else:
        state["tool_result"] = f"Code execution failed after {state['codefix_attempts']} fixes: {exec_result.get('error')}"
        state["tool_success"] = False
        state["error_message"] = exec_result.get("error")
    
    state["current_agent"] = "synthetic"
    return state


def _extract_code(response: str) -> str:
    """Extract Python code from LLM response."""
    if "```python" in response:
        return response.split("```python")[1].split("```")[0].strip()
    elif "```" in response:
        return response.split("```")[1].split("```")[0].strip()
    return response.strip()


# ============================================================================
# ROUTER
# ============================================================================

def route_agent(state: AgentState) -> str:
    """Route to the next agent/node based on current state."""
    current = state.get("current_agent", "done")
    
    if current == "ocr":
        return "ocr_agent"
    elif current == "planner":
        return "planner"
    elif current == "executor":
        return "executor"
    elif current == "wolfram":
        return "wolfram_tool"
    elif current == "code":
        return "code_tool"
    elif current == "synthetic":
        return "synthetic_agent"
    elif current == "done":
        return "done"
    else:
        return "end"
