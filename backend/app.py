"""
FastAPI main application with SSE streaming support.
"""
import os
import uuid
import base64
import json
from typing import Optional, List
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage, AIMessage

from backend.database.models import init_db, AsyncSessionLocal, Conversation, Message
from backend.agent.graph import agent_graph
from backend.agent.state import AgentState
from backend.utils.rate_limit import rate_limiter
from backend.utils.tracing import setup_langsmith, create_run_config, get_tracing_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and LangSmith on startup."""
    await init_db()
    setup_langsmith()  # Initialize LangSmith tracing
    yield


app = FastAPI(
    title="Algebra Chatbot API",
    description="AI-powered algebra tutor using LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Critical for frontend to read X-Session-Id
)


# Pydantic models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class UpdateConversationRequest(BaseModel):
    title: str


class ConversationResponse(BaseModel):
    id: str
    title: Optional[str]
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    image_data: Optional[str] = None  # Add this field
    created_at: str


class SearchResult(BaseModel):
    type: str  # 'conversation' or 'message'
    id: str
    title: Optional[str]  # Conversation title
    content: Optional[str] = None # Message content or snippet
    conversation_id: str
    created_at: str


# Database dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# API Routes
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "algebra-chatbot"}


@app.get("/api/conversations", response_model=list[ConversationResponse])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    """List all conversations."""
    result = await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()
    return [
        ConversationResponse(
            id=c.id,
            title=c.title,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in conversations
    ]


@app.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation(db: AsyncSession = Depends(get_db)):
    """Create a new conversation."""
    conversation = Conversation()
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
    )


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a conversation and reset its memory tracker."""
    # Reset memory tracker for this session
    from backend.utils.memory import memory_tracker
    memory_tracker.reset_usage(conversation_id)
    
    await db.execute(
        delete(Conversation).where(Conversation.id == conversation_id)
    )
    await db.commit()
    return {"status": "deleted"}


@app.patch("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str, 
    request: UpdateConversationRequest, 
    db: AsyncSession = Depends(get_db)
):
    """Update a conversation title."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation.title = request.title
    await db.commit()
    await db.refresh(conversation)
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
    )


@app.get("/api/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get all messages in a conversation."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            image_data=m.image_data,  # Populate this field
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


@app.get("/api/search", response_model=list[SearchResult])
async def search(q: str, db: AsyncSession = Depends(get_db)):
    """
    Search conversations and messages.
    Query: q (string)
    """
    if not q or not q.strip():
        return []

    query = f"%{q.strip()}%"
    results = []

    # 1. Search Conversations
    conv_result = await db.execute(
        select(Conversation)
        .where(Conversation.title.ilike(query))
        .order_by(Conversation.updated_at.desc())
        .limit(10)
    )
    conversations = conv_result.scalars().all()
    for c in conversations:
        results.append(SearchResult(
            type="conversation",
            id=c.id,
            title=c.title,
            content=None,
            conversation_id=c.id,
            created_at=c.created_at.isoformat()
        ))

    # 2. Search Messages
    msg_result = await db.execute(
        select(Message, Conversation.title)
        .join(Conversation)
        .where(Message.content.ilike(query))
        .order_by(Message.created_at.desc())
        .limit(20)
    )
    messages = msg_result.all() # returns (Message, title) tuples
    
    for msg, title in messages:
        # Avoid duplicates if conversation is already found? 
        # Actually showing specific message matches is good even if conversation matches.
        
        # Smarter snippet generation to ensure the match is visible
        content = msg.content
        idx = content.lower().find(q.lower())
        if idx != -1:
            # If the match is beyond the first 40 chars, center it
            if idx > 40:
                start = max(0, idx - 40)
                end = min(len(content), idx + 60)
                content = "..." + content[start:end] + ("..." if end < len(msg.content) else "")
            elif len(content) > 100: # If match is found within first 40 chars, but content is still long
                content = content[:100] + "..."
        elif len(content) > 100: # If no match is found, just truncate if long
            content = content[:100] + "..."

        results.append(SearchResult(
             type="message",
             id=msg.id,
             title=title,
             content=content,
             conversation_id=msg.conversation_id,
             created_at=msg.created_at.isoformat()
        ))

    # Sort combined results by date (newest first)
    results.sort(key=lambda x: x.created_at, reverse=True)
    
    return results


@app.get("/api/conversations/{conversation_id}/memory")
async def get_session_memory(conversation_id: str):
    """Get memory usage status for a session."""
    from backend.utils.memory import memory_tracker, KIMI_K2_CONTEXT_LENGTH
    
    status = memory_tracker.check_status(conversation_id)
    return {
        "session_id": status.session_id,
        "used_tokens": status.used_tokens,
        "max_tokens": status.max_tokens,
        "percentage": round(status.percentage, 2),
        "status": status.status,
        "message": status.message,
        "remaining_tokens": memory_tracker.get_remaining_tokens(conversation_id),
    }


@app.post("/api/chat")
async def chat(
    message: Optional[str] = Form(None),  # Optional - can send image only
    session_id: Optional[str] = Form(None),
    images: List[UploadFile] = File([]),  # Support multiple images (max 5)
    db: AsyncSession = Depends(get_db),
):
    """
    Chat endpoint with streaming response.
    Supports text, images (up to 5), or both.
    """
    # Validate: need at least message or image
    if not message and len(images) == 0:
        raise HTTPException(status_code=400, detail="Phải gửi ít nhất tin nhắn hoặc hình ảnh")
    
    # Limit to 5 images
    if len(images) > 5:
        raise HTTPException(status_code=400, detail="Tối đa 5 ảnh mỗi tin nhắn")
    
    # Default message for image-only queries
    if not message:
        message = "Giải bài toán trong ảnh này"
    
    # Get or create session
    if not session_id:
        conversation = Conversation(title=message[:50] if message else "Ảnh")
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        session_id = conversation.id
    else:
        result = await db.execute(
            select(Conversation).where(Conversation.id == session_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Process all images into list
    image_data = None
    image_data_list = []
    if images:
        for img in images:
            content = await img.read()
            encoded = base64.b64encode(content).decode("utf-8")
            image_data_list.append(encoded)
        # Keep first image for backward compatibility (in memory only)
        image_data = image_data_list[0] if image_data_list else None
    
    # Prepare data for storage: save ALL images as JSON list string
    storage_image_data = None
    if image_data_list:
        storage_image_data = json.dumps(image_data_list)

    # Save user message
    user_msg = Message(
        conversation_id=session_id,
        role="user",
        content=message,
        image_data=storage_image_data,  # Store ALL images
    )
    db.add(user_msg)
    await db.commit()
    
    # Load conversation history
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == session_id)
        .order_by(Message.created_at)
    )
    history = result.scalars().all()
    
    # Build messages list
    messages = []
    for msg in history:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        else:
            messages.append(AIMessage(content=msg.content))
    
    # Create initial state for new multi-agent system
    import time
    from backend.agent.state import create_initial_state
    
    initial_state = create_initial_state(session_id, image_data, image_data_list)
    initial_state["messages"] = messages


    # Create Assistant Placeholder message (pending)
    assistant_msg = Message(
        conversation_id=session_id,
        role="assistant",
        content="", # Empty content marks it as "generating" or "pending"
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)
    assistant_msg_id = assistant_msg.id

    import asyncio
    queue = asyncio.Queue()

    async def run_agent_in_background():
        """Background task that drives the agent and pushes to queue/DB."""
        try:
            # 1. Initial status
            await queue.put({"type": "status", "status": "thinking"})
            
            run_config = create_run_config(session_id)
            final_state = None
            
            # Use astream_events to capture intermediate steps
            async for event in agent_graph.astream_events(initial_state, config=run_config, version="v1"):
                kind = event["event"]
                
                # Capture final_state from any node that returns a valid state
                if kind == "on_chain_end":
                    output = event["data"].get("output")
                    if isinstance(output, dict) and "messages" in output:
                        final_state = output
                              
                elif kind == "on_tool_end":
                    pass

            if not final_state:
                final_state = await agent_graph.ainvoke(initial_state, config=run_config)

            # Extract final response
            full_response = final_state.get("final_response", "")
            if not full_response:
                for msg in reversed(final_state.get("messages", [])):
                    if hasattr(msg, 'content') and isinstance(msg, AIMessage):
                        content = str(msg.content)
                        if content.strip().startswith('{') and '"questions"' in content:
                            continue
                        full_response = content
                        break
            
            if not full_response:
                 full_response = "Xin lỗi, tôi không thể xử lý yêu cầu này."

            # 2. Responding status
            await queue.put({"type": "status", "status": "responding"})

            # 3. Stream tokens to queue individually 
            chunk_size = 5
            for i in range(0, len(full_response), chunk_size):
                chunk = full_response[i:i+chunk_size]
                await queue.put({"type": "token", "content": chunk})
            
            # 4. Save FINAL response to database immediately (resilience!)
            async with AsyncSessionLocal() as save_db:
                from sqlalchemy import update
                await save_db.execute(
                    update(Message)
                    .where(Message.id == assistant_msg_id)
                    .values(content=full_response)
                )
                
                # Update conversation title if needed
                if len(history) <= 1:
                    result = await save_db.execute(
                        select(Conversation).where(Conversation.id == session_id)
                    )
                    conv = result.scalar_one_or_none()
                    if conv and (not conv.title or conv.title == "New Conversation"):
                        conv.title = message[:50] if message else "New Conversation"
                
                await save_db.commit()

            # 5. Done status and metadata
            from backend.agent.state import get_total_duration_ms
            tracking_data = {
                'type': 'done',
                'metadata': {
                    'session_id': session_id,
                    'agents_used': final_state.get('agents_used', []),
                    'tools_called': final_state.get('tools_called', []),
                    'model_calls': final_state.get('model_calls', []),
                    'total_tokens': final_state.get('total_tokens', 0),
                    'total_duration_ms': get_total_duration_ms(final_state),
                    'error': final_state.get('error_message'),
                },
                'memory': {
                    'session_token_count': final_state.get('session_token_count', 0),
                    'context_status': final_state.get('context_status', 'ok'),
                    'context_message': final_state.get('context_message'),
                }
            }
            await queue.put(tracking_data)

        except Exception as e:
            error_msg = f"Xin lỗi, đã có lỗi xảy ra: {str(e)}"
            await queue.put({"type": "token", "content": error_msg})
            await queue.put({"type": "done", "error": str(e)})
            
            # Save error as partially result if needed
            async with AsyncSessionLocal() as save_db:
                from sqlalchemy import update
                await save_db.execute(
                    update(Message)
                    .where(Message.id == assistant_msg_id)
                    .values(content=f"Error: {str(e)}")
                )
                await save_db.commit()
        finally:
            # Signal end of stream
            await queue.put(None)

    # Start the agent task in the background (will continue even if client leaves)
    asyncio.create_task(run_agent_in_background())

    async def stream_from_queue():
        """Generator that reads from the queue and yields to StreamingResponse."""
        while True:
            item = await queue.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(
        stream_from_queue(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-Id": session_id,
        },
    )


@app.get("/api/rate-limit/{session_id}")
async def get_rate_limit_status(session_id: str):
    """Get current rate limit status for a session."""
    tracker = rate_limiter.get_tracker(session_id)
    tracker.reset_if_needed()
    
    return {
        "requests_this_minute": tracker.requests_this_minute,
        "requests_today": tracker.requests_today,
        "tokens_this_minute": tracker.tokens_this_minute,
        "tokens_today": tracker.tokens_today,
        "limits": {
            "rpm": 30,
            "rpd": 1000,
            "tpm": 8000,
            "tpd": 200000,
        }
    }


@app.get("/api/wolfram-status")
async def get_wolfram_status():
    """Get Wolfram Alpha API usage status (2000 req/month limit)."""
    from backend.tools.wolfram import get_wolfram_status
    return get_wolfram_status()


@app.get("/api/tracing-status")
async def tracing_status():
    """Get LangSmith tracing status."""
    return get_tracing_status()


# Serve static files (frontend) in production
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
