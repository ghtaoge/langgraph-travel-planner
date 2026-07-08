"""对话 + 消息 API 路由 — CRUD + 消息列表"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas.conversation import ConversationResponse, ConversationUpdateRequest, MessageResponse
from app.core.auth import get_current_user
from app.core.database import (
    get_db_pool,
    create_conversation,
    fetch_conversations,
    update_conversation_status,
    update_conversation_title,
    delete_conversation,
    fetch_messages,
)

router = APIRouter(prefix="/api/conversations", tags=["对话管理"])


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """获取用户对话列表 — 分页"""
    pool = await get_db_pool()
    conversations = await fetch_conversations(pool, current_user["id"], page, per_page)
    return [ConversationResponse(**c) for c in conversations]


@router.post("", response_model=ConversationResponse)
async def create_new_conversation(current_user: dict = Depends(get_current_user)):
    """创建新对话"""
    import uuid
    pool = await get_db_pool()
    thread_id = str(uuid.uuid4())
    conv = await create_conversation(pool, current_user["id"], thread_id)
    return ConversationResponse(**conv)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """更新对话标题/状态"""
    pool = await get_db_pool()
    if request.title:
        await update_conversation_title(pool, conversation_id, request.title)
    if request.status:
        await update_conversation_status(pool, conversation_id, request.status)
    # 返回更新后的数据
    rows = await pool.fetch(
        "SELECT id, user_id, title, status, created_at, updated_at FROM conversations WHERE id = $1",
        __import__("uuid").UUID(conversation_id),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="对话不存在")
    return ConversationResponse(
        id=str(rows[0]["id"]),
        user_id=str(rows[0]["user_id"]),
        title=rows[0]["title"],
        status=rows[0]["status"],
        created_at=str(rows[0]["created_at"]),
        updated_at=str(rows[0]["updated_at"]),
    )


@router.delete("/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """删除对话及其所有消息"""
    pool = await get_db_pool()
    await delete_conversation(pool, conversation_id)
    return {"message": "对话已删除"}


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """获取对话的所有消息 — 含 thinking_content 和 metadata"""
    pool = await get_db_pool()
    messages = await fetch_messages(pool, conversation_id)
    return [MessageResponse(**m) for m in messages]
