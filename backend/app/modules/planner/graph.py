"""主图构建 — TravelPlannerGraph + Checkpoint + Store + RetryPolicy"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore
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


def build_travel_planner_graph(checkpointer=None, store=None):
    """构建主图 TravelPlannerGraph — 编译时注入 Checkpoint + Store

    LangGraph 知识点覆盖:
    #1 StateGraph, #2 reducer (operator.add, merge_dicts), #3 START/END
    #4 add_node/edge, #5 add_conditional_edges, #6 interrupt
    #7 Command(resume + goto), #10 Send, #11 Subgraph 嵌套
    #13 Structured Output, #15 RetryPolicy, #16 Checkpoint
    #18/#19/#20/#21 Store, #24 get_stream_writer
    #25 MessagesState, #26 context_schema

    Args:
        checkpointer: Checkpointer 实例, 默认使用 MemorySaver
        store: Store 实例, 默认使用 InMemoryStore

    Returns:
        编译后的 TravelPlannerGraph
    """
    cp = checkpointer or get_checkpointer(store="memory")
    st = store or get_store()

    graph = StateGraph(TravelState, context_schema=UserContext)

    # ── 主图节点 ──
    graph.add_node("intent_parser", intent_parser_node, retry_policy=RetryPolicy(max_attempts=3))
    graph.add_node("destination_research", build_destination_graph())  # 子图A
    graph.add_node("plan_generator", plan_generator_node, retry_policy=RetryPolicy(max_attempts=3))
    graph.add_node("user_select", user_select_node)  # interrupt
    graph.add_node("itinerary_refine", build_itinerary_graph())  # 子图B
    graph.add_node("budget_calculator", budget_calculator_node, retry_policy=RetryPolicy(max_attempts=3))
    graph.add_node("user_approve", user_approve_node)  # interrupt
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
    # user_approve 条件路由:
    #   approved → quality_check (正常流程)
    #   rejected → itinerary_refine (重新细化, 带 approval_comment 反馈)
    graph.add_conditional_edges("user_approve", route_after_approve)
    graph.add_conditional_edges("quality_check", route_after_quality)
    graph.add_edge("format_output", "save_summary")
    graph.add_edge("save_summary", END)

    return graph.compile(checkpointer=cp, store=st)
