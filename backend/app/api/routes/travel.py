"""旅游规划 API 路由 — SSE stream + resume + rollback"""

import json
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.api.schemas import ResumeRequest, RollbackRequest, TravelStreamRequest
from app.core.streaming import stream_graph_execution
from app.modules.planner.graph import build_travel_planner_graph

router = APIRouter(prefix="/api/travel", tags=["旅游规划"])

_graph_instance = None


def get_graph():
    """获取主图实例 (带 checkpointer + store)"""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_travel_planner_graph()
    return _graph_instance


@router.post("/stream")
async def travel_stream(request: TravelStreamRequest):
    """SSE 流式执行新对话"""
    graph = get_graph()
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {
        "configurable": {"thread_id": thread_id},
        "context": {"user_id": request.user_id},
    }

    input_data = {
        "query": request.query,
        "user_id": request.user_id,
        "thread_id": thread_id,
        "messages": [HumanMessage(content=request.query)],
        "plans": [],
        "research_result": {},
        "iteration": 0,
        "quality_score": 0,
        "summary_saved": False,
    }

    async def event_generator():
        # 1. 发送 thread_id (前端需要保存此 ID 用于 resume/rollback)
        yield f"data: {json.dumps({'type': 'thread_created', 'thread_id': thread_id})}\n\n"

        # 2. 发送图拓扑
        from app.api.routes.topology import get_topology
        topo = await get_topology()
        yield f"data: {json.dumps({'type': 'graph_topology', **topo})}\n\n"

        # 3. 流式执行
        async for event_json in stream_graph_execution(graph, input_data, config):
            yield f"data: {event_json}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/resume")
async def travel_resume(request: ResumeRequest):
    """恢复 interrupt — SSE 流式继续"""
    graph = get_graph()
    config = {"configurable": {"thread_id": request.thread_id}}

    resume_command = Command(resume=request.resume_data)

    async def event_generator():
        # 1. 发送 thread_id
        yield f"data: {json.dumps({'type': 'thread_created', 'thread_id': request.thread_id})}\n\n"

        # 2. 流式执行
        async for event_json in stream_graph_execution(graph, resume_command, config):
            yield f"data: {event_json}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/rollback")
async def travel_rollback(request: RollbackRequest):
    """回退到指定 checkpoint — SSE 流式重新执行"""
    graph = get_graph()
    config = {
        "configurable": {
            "thread_id": request.thread_id,
            "checkpoint_id": request.checkpoint_id,
        },
    }

    async def event_generator():
        async for event_json in stream_graph_execution(graph, None, config):
            yield f"data: {event_json}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
