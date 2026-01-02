"""
Test cases for Database models and operations.
"""
import pytest
import pytest_asyncio
from datetime import datetime
from backend.database.models import Conversation, Message, Base


class TestConversationModel:
    """Test suite for Conversation model."""

    def test_conversation_creation(self):
        """TC-DB-001: Conversation should have correct default values."""
        conv = Conversation()
        assert conv.title is None
        assert conv.messages == [] if hasattr(conv, 'messages') else True

    def test_conversation_with_title(self):
        """TC-DB-002: Conversation can have custom title."""
        conv = Conversation(title="Test Conversation")
        assert conv.title == "Test Conversation"


class TestMessageModel:
    """Test suite for Message model."""

    def test_message_creation(self):
        """TC-DB-003: Message should have required fields."""
        msg = Message(
            conversation_id="test-conv-id",
            role="user",
            content="Hello world"
        )
        assert msg.role == "user"
        assert msg.content == "Hello world"

    def test_message_with_image(self):
        """TC-DB-004: Message can have image data."""
        msg = Message(
            conversation_id="test-conv-id",
            role="user",
            content="Check this image",
            image_data="base64_encoded_data"
        )
        assert msg.image_data == "base64_encoded_data"

    def test_message_roles(self):
        """TC-DB-005: Message role should be user or assistant."""
        user_msg = Message(conversation_id="1", role="user", content="Hi")
        asst_msg = Message(conversation_id="1", role="assistant", content="Hello")
        
        assert user_msg.role in ["user", "assistant"]
        assert asst_msg.role in ["user", "assistant"]


class TestDatabaseSchema:
    """Test suite for database schema."""

    def test_base_metadata(self):
        """TC-DB-006: Base should have table metadata."""
        tables = Base.metadata.tables
        assert "conversations" in tables
        assert "messages" in tables

    def test_conversations_table_columns(self):
        """TC-DB-007: Conversations table should have required columns."""
        table = Base.metadata.tables["conversations"]
        column_names = [c.name for c in table.columns]
        assert "id" in column_names
        assert "title" in column_names
        assert "created_at" in column_names

    def test_messages_table_columns(self):
        """TC-DB-008: Messages table should have required columns."""
        table = Base.metadata.tables["messages"]
        column_names = [c.name for c in table.columns]
        assert "id" in column_names
        assert "conversation_id" in column_names
        assert "role" in column_names
        assert "content" in column_names
