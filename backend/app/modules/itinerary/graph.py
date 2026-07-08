"""日程细化子图 — ItinerarySubgraph 构建"""

from langgraph.graph import END, START, StateGraph

from app.modules.itinerary.nodes import assemble_node, daily_confirm_node, daily_planner_node
from app.modules.itinerary.react_agent import build_travel_react_agent
from app.modules.itinerary.state import ItineraryState


def build_itinerary_graph():
    """构建日程细化子图

    图结构:
    START → daily_planner → travel_react_agent (create_react_agent 预构建)
    → daily_confirm (interrupt) → assemble → END

    LangGraph 知识点:
    #1 StateGraph, #14 create_react_agent, #12 ToolNode (react_agent 内置), #6 interrupt
    #11 Subgraph (private state key: daily_plans, confirmed_days)
    """
    graph = StateGraph(ItineraryState)

    graph.add_node("daily_planner", daily_planner_node)
    graph.add_node("travel_react_agent", build_travel_react_agent())
    graph.add_node("daily_confirm", daily_confirm_node)
    graph.add_node("assemble", assemble_node)

    graph.add_edge(START, "daily_planner")
    graph.add_edge("daily_planner", "travel_react_agent")
    graph.add_edge("travel_react_agent", "daily_confirm")
    graph.add_edge("daily_confirm", "assemble")
    graph.add_edge("assemble", END)

    return graph.compile()
