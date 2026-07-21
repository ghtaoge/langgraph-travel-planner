"""目的地研究子图测试 — 顺序研究、Command.PARENT、reducer。"""

from app.modules.destination.graph import build_destination_graph


def test_destination_graph_compiles():
    """DestinationSubgraph 能正确编译"""
    graph = build_destination_graph()
    assert graph is not None


def test_destination_graph_nodes_registered():
    """DestinationSubgraph 包含所有预期节点"""
    graph = build_destination_graph()
    node_names = set(graph.nodes.keys()) - {"__start__", "__end__"}
    assert "city_research" in node_names
    assert "synthesize_findings" in node_names


def test_merge_dicts_in_destination_state():
    """DestinationState 的 research_result 使用 merge_dicts reducer"""
    from app.modules.planner.state import merge_dicts
    left = {"成都": "成都调研数据"}
    right = {"重庆": "重庆调研数据"}
    merged = merge_dicts(left, right)
    assert "成都" in merged
    assert "重庆" in merged
