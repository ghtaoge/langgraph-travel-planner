"""日程细化子图测试 — create_react_agent, interrupt, ToolNode"""

from app.modules.itinerary.graph import build_itinerary_graph
from app.modules.itinerary.react_agent import build_travel_react_agent


def test_itinerary_graph_compiles():
    """ItinerarySubgraph 能正确编译"""
    graph = build_itinerary_graph()
    assert graph is not None


def test_itinerary_graph_nodes_registered():
    """ItinerarySubgraph 包含所有预期节点"""
    graph = build_itinerary_graph()
    node_names = set(graph.nodes.keys()) - {"__start__", "__end__"}
    assert "daily_planner" in node_names
    assert "travel_react_agent" in node_names
    assert "daily_confirm" in node_names
    assert "assemble" in node_names


def test_react_agent_compiles():
    """create_react_agent 能正确编译"""
    agent = build_travel_react_agent()
    assert agent is not None
    node_names = set(agent.nodes.keys()) - {"__start__", "__end__"}
    assert "agent" in node_names
    assert "tools" in node_names
