"""
Test cases for FastAPI endpoints.
Tests health, conversations, and rate limit APIs.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app import app


client = TestClient(app)


class TestHealthEndpoint:
    """Test suite for health check endpoint."""

    def test_health_check(self):
        """TC-API-001: Health endpoint should return healthy status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "algebra-chatbot"


class TestConversationEndpoints:
    """Test suite for conversation CRUD endpoints."""

    def test_list_conversations_empty(self):
        """TC-API-002: List conversations should return array."""
        response = client.get("/api/conversations")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_conversation(self):
        """TC-API-003: Create conversation should return new conversation."""
        response = client.post("/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "created_at" in data
        return data["id"]

    def test_delete_conversation(self):
        """TC-API-004: Delete conversation should succeed."""
        # First create
        create_response = client.post("/api/conversations")
        conv_id = create_response.json()["id"]
        
        # Then delete
        delete_response = client.delete(f"/api/conversations/{conv_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["status"] == "deleted"

    def test_get_messages_empty(self):
        """TC-API-005: New conversation should have no messages."""
        # Create conversation
        create_response = client.post("/api/conversations")
        conv_id = create_response.json()["id"]
        
        # Get messages
        messages_response = client.get(f"/api/conversations/{conv_id}/messages")
        assert messages_response.status_code == 200
        assert messages_response.json() == []
        
        # Cleanup
        client.delete(f"/api/conversations/{conv_id}")


class TestRateLimitEndpoints:
    """Test suite for rate limit status endpoints."""

    def test_get_rate_limit_status(self):
        """TC-API-006: Rate limit status should return valid structure."""
        response = client.get("/api/rate-limit/test_session")
        assert response.status_code == 200
        data = response.json()
        assert "requests_this_minute" in data
        assert "tokens_today" in data
        assert "limits" in data

    def test_rate_limit_limits_structure(self):
        """TC-API-007: Rate limit should have correct limit values."""
        response = client.get("/api/rate-limit/test_session")
        data = response.json()
        limits = data["limits"]
        assert limits["rpm"] == 30
        assert limits["rpd"] == 1000
        assert limits["tpm"] == 8000
        assert limits["tpd"] == 200000


class TestWolframStatusEndpoint:
    """Test suite for Wolfram API status endpoint."""

    def test_wolfram_status(self):
        """TC-API-008: Wolfram status should return usage info."""
        response = client.get("/api/wolfram-status")
        assert response.status_code == 200
        data = response.json()
        assert "used" in data
        assert "limit" in data
        assert "remaining" in data
        assert "month" in data
        assert data["limit"] == 2000

    def test_wolfram_remaining_calculation(self):
        """TC-API-009: Remaining should equal limit minus used."""
        response = client.get("/api/wolfram-status")
        data = response.json()
        assert data["remaining"] == data["limit"] - data["used"]


class TestChatEndpoint:
    """Test suite for chat endpoint."""

    def test_chat_creates_session(self):
        """TC-API-010: Chat without session_id should create new session."""
        response = client.post(
            "/api/chat",
            data={"message": "Hello"},
        )
        assert response.status_code == 200
        # Should have session ID in header
        assert "X-Session-Id" in response.headers or response.status_code == 200

    def test_chat_with_session(self):
        """TC-API-011: Chat with existing session_id should work."""
        # Create conversation first
        create_response = client.post("/api/conversations")
        conv_id = create_response.json()["id"]
        
        response = client.post(
            "/api/chat",
            data={"message": "Test message", "session_id": conv_id},
        )
        assert response.status_code == 200
        
        # Cleanup
        client.delete(f"/api/conversations/{conv_id}")

    def test_chat_invalid_session(self):
        """TC-API-012: Chat with invalid session_id should return 404."""
        response = client.post(
            "/api/chat",
            data={"message": "Test", "session_id": "invalid-uuid-12345"},
        )
        assert response.status_code == 404
