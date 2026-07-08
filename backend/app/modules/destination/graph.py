"""目的地研究子图 — 简化版 (不用 Send fan-out)

图结构:
START → city_research → synthesize_findings → Command.PARENT

LangGraph 知识点:
#1 StateGraph, #2 Annotated reducer (merge_dicts), #8 Command(goto), #9 Command.PARENT
"""

from langgraph.graph import END, START, StateGraph

from app.modules.destination.nodes import (
    city_research_node,
    synthesize_findings_node,
)
from app.modules.destination.state import DestinationState


def build_destination_graph():
    """构建目的地研究子图 (简化版)"""
    graph = StateGraph(DestinationState)

    graph.add_node("city_research", city_research_node)
    graph.add_node("synthesize_findings", synthesize_findings_node)

    graph.add_edge(START, "city_research")
    graph.add_edge("city_research", "synthesize_findings")

    return graph.compile()
