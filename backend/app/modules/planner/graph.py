"""主图构建 — TravelPlannerGraph + AsyncPostgresSaver + PostgresStore + RetryPolicy"""

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.core.checkpoint import get_checkpointer
from app.core.store import get_store
from app.modules.destination.graph import build_destination_graph
from app.modules.itinerary.graph import build_itinerary_graph
from app.modules.planner.conditions import route_after_quality, route_after_approve
from app.modules.planner.nodes import (
    budget_calculator_node,
    format_output_node,
    intent_parser_node,
    plan_generator_node,
    quality_check_node,
    save_summary_node,
    user_approve_node,
    user_select_node,
)
from app.modules.planner.state import TravelState, UserContext

_graph_instance = None


async def build_travel_planner_graph():
    """构建主图 — async 版本, 使用 PG checkpointer + store

    在 FastAPI lifespan 中首次调用时初始化,
    后续调用返回缓存的编译图实例。
    """
    global _graph_instance
    if _graph_instance is not None:
        return _graph_instance

    cp = await get_checkpointer()
    st = get_store()

    graph = StateGraph(TravelState, context_schema=UserContext)

    # ── 主图节点 ──
    graph.add_node("intent_parser", intent_parser_node, retry_policy=RetryPolicy(max_attempts=3))
    graph.add_node("destination_research", build_destination_graph())
    graph.add_node("plan_generator", plan_generator_node, retry_policy=RetryPolicy(max_attempts=3))
    graph.add_node("user_select", user_select_node)
    graph.add_node("itinerary_refine", build_itinerary_graph())
    graph.add_node("budget_calculator", budget_calculator_node, retry_policy=RetryPolicy(max_attempts=3))
    graph.add_node("user_approve", user_approve_node)
    graph.add_node("quality_check", quality_check_node, retry_policy=RetryPolicy(max_attempts=3))
    graph.add_node("format_output", format_output_node)
    graph.add_node("save_summary", save_summary_node)

    # ── 主图边 ──
    graph.add_edge(START, "intent_parser")
    graph.add_edge("intent_parser", "destination_research")
    graph.add_edge("destination_research", "plan_generator")
    graph.add_edge("plan_generator", "user_select")
    graph.add_edge("user_select", "itinerary_refine")
    graph.add_edge("itinerary_refine", "budget_calculator")
    graph.add_edge("budget_calculator", "user_approve")
    graph.add_conditional_edges("user_approve", route_after_approve)
    graph.add_conditional_edges("quality_check", route_after_quality)
    graph.add_edge("format_output", "save_summary")
    graph.add_edge("save_summary", END)

    _graph_instance = graph.compile(checkpointer=cp, store=st)
    return _graph_instance
