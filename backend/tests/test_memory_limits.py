import asyncio
import httpx
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.utils.memory import memory_tracker, WARNING_TOKENS, BLOCK_TOKENS, KIMI_K2_CONTEXT_LENGTH

async def get_latest_session_id():
    """Fetch the most recent conversation ID from the database."""
    try:
        import sqlite3
        conn = sqlite3.connect("algebra_chat.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM conversations ORDER BY created_at DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error fetching latest session: {e}")
        return None

async def test_memory_limits():
    """Test memory warning and blocking behavior."""
    # Try to get latest session if not specified
    session_id = await get_latest_session_id()
    
    if not session_id:
        session_id = "test_memory_session_v1"
        print(f"! Không tìm thấy session nào trong DB, sử dụng ID mặc định: {session_id}")
    else:
        print(f"✨ Đã tìm thấy session mới nhất: {session_id}")
    
    print(f"\n--- Testing Memory Limits for Session: {session_id} ---")
    print(f"Max Tokens: {KIMI_K2_CONTEXT_LENGTH}")
    print(f"Warning Threshold: {WARNING_TOKENS} (80%)")
    print(f"Block Threshold: {BLOCK_TOKENS} (95%)")
    
    # 1. Create a new session (implicitly via chat or explicit reset)
    print("\n1. Resetting session memory...")
    memory_tracker.reset_usage(session_id)
    current = memory_tracker.get_usage(session_id)
    print(f"Current Usage: {current}")
    
    # 2. Test Normal State
    print("\n2. Testing Normal State...")
    print("Simulating 1000 tokens usage...")
    memory_tracker.set_usage(session_id, 1000)
    
    status = memory_tracker.check_status(session_id)
    print(f"Status: {status.status}, Percentage: {status.percentage:.2f}%")
    if status.status != "ok":
        print("❌ FAILED: Should be 'ok'")
    else:
        print("✅ PASSED: Status is 'ok'")

    # 3. Test Warning State
    print("\n3. Testing Warning State (81%)...")
    # Set usage to just above warning threshold
    warning_val = int(KIMI_K2_CONTEXT_LENGTH * 0.81)
    memory_tracker.set_usage(session_id, warning_val)
    
    status = memory_tracker.check_status(session_id)
    print(f"Current Usage: {warning_val}")
    print(f"Status: {status.status}, Percentage: {status.percentage:.2f}%")
    print(f"Message: {status.message}")
    
    if status.status != "warning":
        print("❌ FAILED: Should be 'warning'")
    else:
        print("✅ PASSED: Status is 'warning'")

    # 4. Test Blocked State
    print("\n4. Testing Blocked State (96%)...")
    # Set usage to above block threshold
    block_val = int(KIMI_K2_CONTEXT_LENGTH * 0.96)
    memory_tracker.set_usage(session_id, block_val)
    
    status = memory_tracker.check_status(session_id)
    print(f"Current Usage: {block_val}")
    print(f"Status: {status.status}, Percentage: {status.percentage:.2f}%")
    print(f"Message: {status.message}")
    
    if status.status != "blocked":
        print("❌ FAILED: Should be 'blocked'")
    else:
        print("✅ PASSED: Status is 'blocked'")
        
    # 5. Verify API Response (Logic simulation)
    # We can't easily call the running API from here without successful auth/db setup
    # unless we run this script in the same environment. 
    # But since we share the memory_tracker instance if running locally with same cache dir,
    # we can verify the logic directly.
    
    print("\n--- Test Complete ---")
    print("To verify in UI:")
    print(f"1. Start the app")
    print(f"2. Send a message to session '{session_id}' (or any session)")
    print(f"3. Use this script to set usage for that session ID high")
    print(f"4. Refresh or send another message to see the effect")

if __name__ == "__main__":
    asyncio.run(test_memory_limits())
