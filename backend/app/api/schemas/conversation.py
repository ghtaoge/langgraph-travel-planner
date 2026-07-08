"""对话 + 消息 API 数据模型"""

from typing import Optional
from pydantic import BaseModel, Field


class ConversationResponse(BaseModel):
    """对话响应"""
    id: str
    user_id: str
    title: str
    status: str
    created_at: str
    updated_at: str = ""


class ConversationUpdateRequest(BaseModel):
    """更新对话请求"""
    title: Optional[str] = None
    status: Optional[str] = None


class MessageResponse(BaseModel):
    """消息响应"""
    id: str
    conversation_id: str
    role: str
    content: str
    thinking_content: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: str
