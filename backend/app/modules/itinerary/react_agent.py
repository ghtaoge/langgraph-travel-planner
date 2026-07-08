"""create_react_agent 预构建 — LangGraph 知识点 #14"""

from langgraph.prebuilt import create_react_agent

from app.core.llm import get_llm
from app.modules.itinerary.tools import ITINERARY_TOOLS


def build_travel_react_agent():
    """构建旅游 ReAct Agent — 使用 LangGraph 预构建

    LangGraph 知识点 #14: create_react_agent (prebuilt)
    LangGraph 知识点 #12: ToolNode (内部由 react_agent 自动管理)

    Returns:
        编译后的 ReAct Agent 图
    """
    llm = get_llm(temperature=0.3)

    agent = create_react_agent(
        model=llm,
        tools=ITINERARY_TOOLS,
        prompt="你是一个旅游行程细化助手。使用工具查询天气、餐饮、住宿和景点信息来完善行程。请用中文回答。",
    )
    return agent
