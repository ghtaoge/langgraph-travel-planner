"""PlanningGraph structure and routing tests."""

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from app.api.routes.topology import get_topology
from app.modules.planner.conditions import route_after_approve
from app.modules.planner.graph import create_travel_planner_graph


def test_planning_graph_registers_provider_and_persistence_nodes():
    graph = create_travel_planner_graph()
    node_names = set(graph.nodes) - {"__start__", "__end__"}

    assert node_names == {
        "intent_parser",
        "destination_research",
        "provider_research",
        "plan_generator",
        "validate_candidates",
        "user_select",
        "itinerary_refine",
        "enrich_itinerary",
        "budget_calculator",
        "user_approve",
        "persist_trip",
        "format_output",
        "save_summary",
    }


def test_planning_graph_accepts_explicit_checkpoint_and_store():
    checkpointer = MemorySaver()
    store = InMemoryStore()

    graph = create_travel_planner_graph(checkpointer=checkpointer, store=store)

    assert graph.checkpointer is checkpointer
    assert graph.store is store


def test_approved_plan_routes_to_durable_trip_persistence():
    assert route_after_approve({"approval_status": "approved"}) == "persist_trip"
    assert route_after_approve({"approval_status": "rejected"}) == "itinerary_refine"


@pytest.mark.asyncio
async def test_topology_api_matches_provider_aware_graph():
    topology = await get_topology()
    node_ids = {node["id"] for node in topology["nodes"]}
    edges = {(edge["from"], edge["to"]) for edge in topology["edges"]}

    assert {"provider_research", "validate_candidates", "enrich_itinerary", "persist_trip"} <= node_ids
    assert ("user_approve", "persist_trip") in edges
    assert ("persist_trip", "format_output") in edges
