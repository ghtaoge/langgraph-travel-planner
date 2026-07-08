"""历史对话 + 用户画像 + Checkpoint 时间线 API"""

from fastapi import APIRouter

from app.api.routes.travel import get_graph
from app.core.store import get_store

router = APIRouter(prefix="/api/travel", tags=["历史与记忆"])


@router.get("/history")
async def get_history(user_id: str = "default_user"):
    """Store search — 对话摘要列表"""
    store = get_store()
    summaries = store.search(("conversation_summaries", user_id))
    return {"history": [{"thread_id": item.key, **item.value} for item in summaries]}


@router.get("/profile")
async def get_profile(user_id: str = "default_user"):
    """Store get — 用户旅行画像"""
    store = get_store()
    profile = store.get(("travel_profiles", user_id), "profile")
    if profile:
        return {"profile": profile.value}
    return {"profile": {}}


@router.get("/conversation/{thread_id}")
async def get_conversation(thread_id: str):
    """Checkpoint — 加载某对话 state"""
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = await graph.aget_state(config)
    return {"thread_id": thread_id, "values": state.values, "next": list(state.next) if state.next else []}


@router.get("/states/{thread_id}")
async def list_states(thread_id: str):
    """Checkpoint list_state — 时间线 (回退用)"""
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    states = []
    for state in graph.get_state_history(config):
        states.append({
            "checkpoint_id": state.config["configurable"].get("checkpoint_id", ""),
            "next_node": list(state.next) if state.next else [],
            "timestamp": str(state.created_at) if state.created_at else "",
            "metadata": state.metadata or {},
        })
    return {"states": states}
