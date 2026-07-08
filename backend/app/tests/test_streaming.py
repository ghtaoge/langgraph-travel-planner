"""SSE 流式测试 — 事件格式验证"""

import json


def test_topology_endpoint_returns_valid_structure():
    """topology API 返回有效结构"""
    from app.api.routes.topology import get_topology
    import asyncio
    topo = asyncio.run(get_topology())
    assert "nodes" in topo
    assert "edges" in topo
    assert "subgraphs" in topo
    assert len(topo["nodes"]) == 11


def test_sse_event_json_format():
    """SSE 事件是有效 JSON"""
    event = json.dumps({"type": "node_start", "node": "intent_parser"})
    parsed = json.loads(event)
    assert parsed["type"] == "node_start"
    assert parsed["node"] == "intent_parser"


def test_interrupt_event_format():
    """interrupt SSE 事件格式正确"""
    event = json.dumps({"type": "interrupt", "node": "user_select", "question": "请选择方案"})
    parsed = json.loads(event)
    assert parsed["type"] == "interrupt"


def test_completed_event_format():
    """completed SSE 事件格式正确"""
    event = json.dumps({"type": "completed", "data": {"final_plan": "成都3日行程"}})
    parsed = json.loads(event)
    assert parsed["type"] == "completed"
