"""旅游规划 API 路由 — SSE stream + resume + rollback (带认证 + DB 写入)"""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.api.schemas import ResumeRequest, RollbackRequest, TravelStreamRequest
from app.core.auth import get_current_user
from app.core.database import (
    create_conversation,
    get_conversation_status,
    get_db_pool,
    insert_message,
)
from app.core.streaming import stream_graph_execution
from app.modules.planner.graph import build_travel_planner_graph

router = APIRouter(prefix="/api/travel", tags=["旅游规划"])


async def get_graph():
    """获取主图实例 (async, PG-backed)"""
    return await build_travel_planner_graph()


@router.post("/stream")
async def travel_stream(
    request: TravelStreamRequest,
    current_user: dict = Depends(get_current_user),
):
    """SSE 流式执行新对话 — 带认证"""
    graph = await get_graph()
    pool = await get_db_pool()
    thread_id = request.thread_id or str(uuid.uuid4())

    if request.thread_id:
        status = await get_conversation_status(pool, thread_id)
        if status == "interrupted":
            raise HTTPException(
                status_code=409,
                detail="当前会话正在等待选择方案或审批，请先完成上方操作，或点击新对话重新开始。",
            )
        if status == "completed":
            raise HTTPException(
                status_code=409,
                detail="该会话已完成，请点击新对话开始新的旅行规划。",
            )

    # 创建对话记录
    await create_conversation(pool, current_user["id"], thread_id)

    # 写入 user 消息到 DB
    await insert_message(pool, thread_id, "user", request.query)

    config = {
        "configurable": {"thread_id": thread_id},
        "context": {"user_id": current_user["id"]},
    }

    input_data = {
        "query": request.query,
        "user_id": current_user["id"],
        "thread_id": thread_id,
        "messages": [HumanMessage(content=request.query)],
        "plans": [],
        "research_result": {},
        "provider_warnings": [],
        "iteration": 0,
        "quality_score": 0,
        "summary_saved": False,
        "trip_id": "",
        "trip_revision": 0,
        "trip_snapshot": {},
    }

    async def event_generator():
        yield f"data: {json.dumps({'type': 'thread_created', 'thread_id': thread_id})}\n\n"

        from app.api.routes.topology import get_topology
        topo = await get_topology()
        yield f"data: {json.dumps({'type': 'graph_topology', **topo})}\n\n"

        async for event_json in stream_graph_execution(graph, input_data, config, pool, thread_id):
            yield f"data: {event_json}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/resume")
async def travel_resume(
    request: ResumeRequest,
    current_user: dict = Depends(get_current_user),
):
    """恢复 interrupt — SSE 流式继续"""
    graph = await get_graph()
    pool = await get_db_pool()

    # 写入 resume 操作消息到 DB
    resume_summary = json.dumps(request.resume_data, ensure_ascii=False)[:200]
    await insert_message(pool, request.thread_id, "system", f"恢复操作: {resume_summary}")

    config = {"configurable": {"thread_id": request.thread_id}}
    resume_command = Command(resume=request.resume_data)

    async def event_generator():
        yield f"data: {json.dumps({'type': 'thread_created', 'thread_id': request.thread_id})}\n\n"

        async for event_json in stream_graph_execution(graph, resume_command, config, pool, request.thread_id):
            yield f"data: {event_json}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/rollback")
async def travel_rollback(
    request: RollbackRequest,
    current_user: dict = Depends(get_current_user),
):
    """回退到指定 checkpoint — SSE 流式重新执行"""
    graph = await get_graph()
    pool = await get_db_pool()

    config = {
        "configurable": {
            "thread_id": request.thread_id,
            "checkpoint_id": request.checkpoint_id,
        },
    }

    async def event_generator():
        async for event_json in stream_graph_execution(graph, None, config, pool, request.thread_id):
            yield f"data: {event_json}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
