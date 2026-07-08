"""Streaming 模块测试 — 函数签名验证"""

from app.core.streaming import stream_graph_execution, _summarize_output, _estimate_progress


def test_summarize_output():
    """节点输出摘要"""
    assert _summarize_output("intent_parser", {"destination": "成都", "duration": 3, "travel_style": "美食游"}) == "解析意图: 目标=成都, 3天, 风格=美食游"
    assert _summarize_output("plan_generator", {"plans": [1, 2, 3]}) == "生成 3 套旅行方案"
    assert _summarize_output("unknown_node", {}) == ""


def test_estimate_progress():
    """进度估算"""
    assert _estimate_progress("intent_parser") == 0.1
    assert _estimate_progress("format_output") == 0.9
    assert _estimate_progress("unknown_node") == 0.5


def test_stream_function_signature():
    """验证 stream_graph_execution 可导入"""
    assert stream_graph_execution is not None
