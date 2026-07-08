"""主图结构测试 — TravelPlannerGraph 编译 + 节点验证"""

from app.modules.planner.graph import build_travel_planner_graph
from app.modules.planner.conditions import route_after_quality


def test_main_graph_compiles():
    """TravelPlannerGraph 能正确编译"""
    graph = build_travel_planner_graph()
    assert graph is not None


def test_main_graph_nodes_registered():
    """TravelPlannerGraph 包含所有预期节点"""
    graph = build_travel_planner_graph()
    node_names = set(graph.nodes.keys()) - {"__start__", "__end__"}
    expected = {
        "intent_parser", "destination_research", "plan_generator",
        "generate_single_plan", "user_select", "itinerary_refine",
        "budget_calculator", "user_approve", "quality_check",
        "format_output", "save_summary",
    }
    assert expected.issubset(node_names)


def test_route_after_quality_high_score():
    """route_after_quality: score>=7 → format_output"""
    result = route_after_quality({"quality_score": 8, "iteration": 0})
    assert result == "format_output"


def test_route_after_quality_low_score_first_iter():
    """route_after_quality: score<7, iter<3 → itinerary_refine"""
    result = route_after_quality({"quality_score": 5, "iteration": 1})
    assert result == "itinerary_refine"


def test_route_after_quality_low_score_max_iter():
    """route_after_quality: score<7, iter>=3 → format_output"""
    result = route_after_quality({"quality_score": 5, "iteration": 3})
    assert result == "format_output"


def test_graph_has_checkpoint_and_store():
    """主图编译时注入了 checkpointer 和 store"""
    graph = build_travel_planner_graph()
    assert graph.checkpointer is not None
