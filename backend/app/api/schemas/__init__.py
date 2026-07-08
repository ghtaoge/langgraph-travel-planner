"""API 请求/响应模型 — Pydantic 数据校验"""

from typing import Optional
from pydantic import BaseModel, Field


class TravelStreamRequest(BaseModel):
    """SSE 流式执行请求"""
    query: str = Field(..., description="用户旅行需求", min_length=1)
    thread_id: str = Field(default="", description="对话ID (空则自动生成)")
    # user_id removed — comes from JWT auth via Depends(get_current_user)


class ResumeRequest(BaseModel):
    """恢复 interrupt 请求"""
    thread_id: str = Field(..., description="对话 thread ID")
    resume_data: dict = Field(..., description="interrupt 恢复数据")


class RollbackRequest(BaseModel):
    """回退到指定 checkpoint 请求"""
    thread_id: str = Field(..., description="对话 thread ID")
    checkpoint_id: str = Field(..., description="目标 checkpoint ID")


class GraphRunResponse(BaseModel):
    """图运行响应 (非 SSE 场景)"""
    thread_id: Optional[str] = None
    completed: bool
    data: dict = Field(default_factory=dict)
