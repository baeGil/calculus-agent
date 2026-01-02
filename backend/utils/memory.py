"""
Session Memory Management for Multi-Agent Chatbot.
Tracks token usage per session and enforces context length limits.
"""
import os
import time
from typing import Literal, Tuple, Optional
from dataclasses import dataclass
import diskcache

# Context length for kimi-k2-instruct-0905
KIMI_K2_CONTEXT_LENGTH = 262144  # 256K tokens

# Thresholds
WARNING_THRESHOLD = 0.80  # 80% - Show warning
BLOCK_THRESHOLD = 0.95   # 95% - Block requests

# Calculate actual token limits
WARNING_TOKENS = int(KIMI_K2_CONTEXT_LENGTH * WARNING_THRESHOLD)  # ~209,715
BLOCK_TOKENS = int(KIMI_K2_CONTEXT_LENGTH * BLOCK_THRESHOLD)      # ~249,037


@dataclass
class MemoryStatus:
    """Status of session memory usage."""
    session_id: str
    used_tokens: int
    max_tokens: int
    percentage: float
    status: Literal["ok", "warning", "blocked"]
    message: Optional[str] = None


def estimate_tokens(text: str) -> int:
    """
    Estimate number of tokens from text.
    Uses simple heuristic: ~4 characters per token for mixed Vietnamese/English.
    """
    if not text:
        return 0
    return len(text) // 4


def estimate_message_tokens(messages: list) -> int:
    """Estimate total tokens from a list of LangChain messages."""
    total = 0
    for msg in messages:
        if hasattr(msg, 'content'):
            content = msg.content
            if isinstance(content, str):
                total += estimate_tokens(content)
            elif isinstance(content, list):
                # For multimodal messages (text + image)
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        total += estimate_tokens(item.get("text", ""))
                    elif isinstance(item, dict) and item.get("type") == "image_url":
                        total += 500  # Estimate for image tokens
    return total


def truncate_history_to_fit(
    messages: list,
    system_tokens: int = 2000,
    current_tokens: int = 500,
    max_context_tokens: int = 200000,  # Leave room within 256K limit
    reserve_for_response: int = 4096
) -> list:
    """
    Truncate conversation history to fit within token limits.
    Keeps most recent messages, drops oldest first.
    
    Args:
        messages: List of LangChain messages (conversation history)
        system_tokens: Estimated tokens for system prompt
        current_tokens: Estimated tokens for current user request
        max_context_tokens: Maximum tokens available for context
        reserve_for_response: Tokens reserved for LLM response
        
    Returns:
        Truncated list of messages that fits within limits
    """
    available_tokens = max_context_tokens - system_tokens - current_tokens - reserve_for_response
    
    if available_tokens <= 0:
        return []  # No room for history
    
    if not messages:
        return []
    
    # Calculate tokens for each message from most recent to oldest
    truncated = []
    total = 0
    
    # Process from most recent to oldest (reversed iteration)
    for msg in reversed(messages):
        if hasattr(msg, 'content'):
            content = msg.content
            if isinstance(content, str):
                msg_tokens = estimate_tokens(content)
            elif isinstance(content, list):
                msg_tokens = sum(
                    estimate_tokens(item.get("text", "")) if item.get("type") == "text" else 500
                    for item in content if isinstance(item, dict)
                )
            else:
                msg_tokens = 100  # Fallback estimate
        else:
            msg_tokens = 100
        
        if total + msg_tokens <= available_tokens:
            truncated.insert(0, msg)  # Insert at beginning to maintain order
            total += msg_tokens
        else:
            break  # No more room
    
    return truncated


def get_conversation_summary(messages: list, max_messages: int = 20) -> str:
    """
    Get a summary of conversation for context.
    Returns a formatted string showing recent conversation turns.
    
    Args:
        messages: List of LangChain messages
        max_messages: Maximum number of messages to include
        
    Returns:
        Formatted conversation summary string
    """
    if not messages:
        return "(Chưa có lịch sử hội thoại)"
    
    recent = messages[-max_messages:]
    summary_parts = []
    
    for msg in recent:
        role = "Người dùng" if hasattr(msg, '__class__') and 'Human' in msg.__class__.__name__ else "Trợ lý"
        content = msg.content if hasattr(msg, 'content') else str(msg)
        if isinstance(content, str):
            # Truncate long messages
            if len(content) > 200:
                content = content[:200] + "..."
            summary_parts.append(f"[{role}]: {content}")
    
    return "\n".join(summary_parts)

class SessionMemoryTracker:
    """
    Track and manage memory (token usage) for each session.
    Uses persistent disk cache to survive restarts.
    """
    
    def __init__(self, cache_dir: str = ".session_memory"):
        self.cache = diskcache.Cache(cache_dir)
        self.max_tokens = KIMI_K2_CONTEXT_LENGTH
        self.warning_tokens = WARNING_TOKENS
        self.block_tokens = BLOCK_TOKENS
    
    def _get_key(self, session_id: str) -> str:
        """Generate cache key for a session."""
        return f"session_tokens:{session_id}"
    
    def get_usage(self, session_id: str) -> int:
        """Get current token usage for a session."""
        key = self._get_key(session_id)
        return self.cache.get(key, 0)
    
    def set_usage(self, session_id: str, tokens: int):
        """Set token usage for a session."""
        key = self._get_key(session_id)
        # No expiry - session tokens persist until session is deleted
        self.cache.set(key, tokens)
    
    def add_usage(self, session_id: str, tokens: int) -> int:
        """Add tokens to session usage. Returns new total."""
        current = self.get_usage(session_id)
        new_total = current + tokens
        self.set_usage(session_id, new_total)
        return new_total
    
    def reset_usage(self, session_id: str):
        """Reset token usage for a session (when session is deleted)."""
        key = self._get_key(session_id)
        self.cache.delete(key)
    
    def check_status(self, session_id: str, additional_tokens: int = 0) -> MemoryStatus:
        """
        Check memory status for a session.
        
        Args:
            session_id: The session ID to check
            additional_tokens: Estimated tokens for the upcoming request
            
        Returns:
            MemoryStatus with current state and appropriate message
        """
        current_tokens = self.get_usage(session_id)
        projected_tokens = current_tokens + additional_tokens
        percentage = (projected_tokens / self.max_tokens) * 100
        
        if projected_tokens >= self.block_tokens:
            return MemoryStatus(
                session_id=session_id,
                used_tokens=current_tokens,
                max_tokens=self.max_tokens,
                percentage=percentage,
                status="blocked",
                message="Session đã hết dung lượng bộ nhớ. Vui lòng tạo session mới để tiếp tục."
            )
        elif projected_tokens >= self.warning_tokens:
            return MemoryStatus(
                session_id=session_id,
                used_tokens=current_tokens,
                max_tokens=self.max_tokens,
                percentage=percentage,
                status="warning",
                message="Session sắp đầy bộ nhớ. Bạn nên tạo session mới sớm để tránh bị gián đoạn."
            )
        else:
            return MemoryStatus(
                session_id=session_id,
                used_tokens=current_tokens,
                max_tokens=self.max_tokens,
                percentage=percentage,
                status="ok",
                message=None
            )
    
    def will_overflow(self, session_id: str, additional_tokens: int) -> bool:
        """Check if adding tokens will cause overflow (exceed block threshold)."""
        current = self.get_usage(session_id)
        return (current + additional_tokens) >= self.block_tokens
    
    def get_remaining_tokens(self, session_id: str) -> int:
        """Get remaining tokens before hitting block threshold."""
        current = self.get_usage(session_id)
        return max(0, self.block_tokens - current)


class TokenOverflowError(Exception):
    """Raised when session token limit is exceeded."""
    
    def __init__(self, session_id: str, used_tokens: int, max_tokens: int):
        self.session_id = session_id
        self.used_tokens = used_tokens
        self.max_tokens = max_tokens
        percentage = (used_tokens / max_tokens) * 100
        super().__init__(
            f"Session {session_id} has exceeded token limit: "
            f"{used_tokens:,}/{max_tokens:,} ({percentage:.1f}%)"
        )


# Global memory tracker instance
memory_tracker = SessionMemoryTracker()


def check_and_update_memory(
    session_id: str,
    input_tokens: int,
    output_tokens: int
) -> MemoryStatus:
    """
    Check memory status and update usage after a successful request.
    
    Args:
        session_id: The session ID
        input_tokens: Tokens used for input (messages + prompt)
        output_tokens: Tokens generated in response
        
    Returns:
        Updated MemoryStatus
        
    Raises:
        TokenOverflowError: If session has exceeded block threshold
    """
    total_tokens = input_tokens + output_tokens
    
    # Check before updating
    status = memory_tracker.check_status(session_id, total_tokens)
    
    if status.status == "blocked":
        raise TokenOverflowError(
            session_id=session_id,
            used_tokens=status.used_tokens,
            max_tokens=status.max_tokens
        )
    
    # Update usage
    new_total = memory_tracker.add_usage(session_id, total_tokens)
    
    # Return updated status
    return memory_tracker.check_status(session_id)
