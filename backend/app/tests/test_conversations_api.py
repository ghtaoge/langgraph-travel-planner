"""Conversations API schema 测试"""

from app.api.schemas.conversation import ConversationResponse, MessageResponse


def test_conversation_response_schema():
    """ConversationResponse 模型验证"""
    data = {
        "id": "uuid-123",
        "user_id": "user-456",
        "title": "成都3天美食之旅",
        "status": "active",
        "created_at": "2026-07-08",
        "updated_at": "2026-07-08",
    }
    resp = ConversationResponse(**data)
    assert resp.id == "uuid-123"
    assert resp.title == "成都3天美食之旅"
    assert resp.status == "active"


def test_message_response_schema():
    """MessageResponse 模型验证"""
    data = {
        "id": "msg-123",
        "conversation_id": "conv-456",
        "role": "assistant",
        "content": "成都3天美食之旅",
        "thinking_content": "思考过程...",
        "metadata": {"interrupt_type": "user_select", "plans": []},
        "created_at": "2026-07-08",
    }
    resp = MessageResponse(**data)
    assert resp.role == "assistant"
    assert resp.metadata["interrupt_type"] == "user_select"
