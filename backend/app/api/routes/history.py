"""历史对话 + 用户画像 API — PG-backed"""

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.database import get_db_pool, fetch_conversations
from app.core.store import get_store

router = APIRouter(prefix="/api/travel", tags=["历史与记忆"])


@router.get("/history")
async def get_history(current_user: dict = Depends(get_current_user)):
    """对话历史列表 — 从 conversations 表查询"""
    pool = await get_db_pool()
    conversations = await fetch_conversations(pool, current_user["id"])
    return {"history": conversations}


@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """用户旅行画像 — 从 PostgresStore 查询"""
    store = get_store()
    profile = store.get(("travel_profiles", current_user["id"]), "profile")
    if profile:
        return {"profile": profile.value}
    return {"profile": {}}
