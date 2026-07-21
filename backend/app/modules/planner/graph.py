"""PlanningGraph construction with provider validation and durable Trip persistence."""

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.core.checkpoint import get_checkpointer
from app.core.store import get_store
from app.modules.destination.graph import build_destination_graph
from app.modules.itinerary.graph import build_itinerary_graph
from app.modules.planner.conditions import route_after_approve
from app.modules.planner.nodes import (
    budget_calculator_node,
    format_output_node,
    intent_parser_node,
    persist_trip_node,
    plan_generator_node,
    save_summary_node,
    user_approve_node,
    user_select_node,
)
from app.modules.planner.provider_nodes import enrich_itinerary_node, provider_research_node
from app.modules.planner.state import TravelState, UserContext
from app.modules.planner.validation import validate_candidates_node

_graph_instance = None


def create_travel_planner_graph(checkpointer=None, store=None):
    """Create a compiled graph with injectable persistence for tests and production."""
    graph = StateGraph(TravelState, context_schema=UserContext)

    graph.add_node("intent_parser", intent_parser_node, retry_policy=RetryPolicy(max_attempts=3))
    graph.add_node("destination_research", build_destination_graph())
    graph.add_node("provider_research", provider_research_node)
    graph.add_node("plan_generator", plan_generator_node, retry_policy=RetryPolicy(max_attempts=3))
    graph.add_node("validate_candidates", validate_candidates_node)
    graph.add_node("user_select", user_select_node)
    graph.add_node("itinerary_refine", build_itinerary_graph())
    graph.add_node("enrich_itinerary", enrich_itinerary_node)
    graph.add_node("budget_calculator", budget_calculator_node, retry_policy=RetryPolicy(max_attempts=3))
    graph.add_node("user_approve", user_approve_node)
    graph.add_node("persist_trip", persist_trip_node)
    graph.add_node("format_output", format_output_node)
    graph.add_node("save_summary", save_summary_node)

    graph.add_edge(START, "intent_parser")
    graph.add_edge("intent_parser", "destination_research")
    graph.add_edge("destination_research", "provider_research")
    graph.add_edge("provider_research", "plan_generator")
    graph.add_edge("plan_generator", "validate_candidates")
    graph.add_edge("validate_candidates", "user_select")
    graph.add_edge("user_select", "itinerary_refine")
    graph.add_edge("itinerary_refine", "enrich_itinerary")
    graph.add_edge("enrich_itinerary", "budget_calculator")
    graph.add_edge("budget_calculator", "user_approve")
    graph.add_conditional_edges("user_approve", route_after_approve)
    graph.add_edge("persist_trip", "format_output")
    graph.add_edge("format_output", "save_summary")
    graph.add_edge("save_summary", END)

    return graph.compile(checkpointer=checkpointer, store=store)


async def build_travel_planner_graph():
    """Build and cache the production graph backed by PostgreSQL and Store."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = create_travel_planner_graph(
            checkpointer=await get_checkpointer(),
            store=get_store(),
        )
    return _graph_instance
