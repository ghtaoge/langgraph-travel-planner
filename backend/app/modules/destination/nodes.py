"""目的地研究子图节点 — 顺序调研 + Command.PARENT 路由回主图

简化版: 不使用 Send fan-out (LangGraph v1.x 子图内 Send 不兼容)
改为顺序调研每个城市, 然后合成结果。
"""

import logging

from langchain_core.messages import HumanMessage
from langgraph.types import Command, Send

from app.config.prompts import DESTINATION_RESEARCH_PROMPT
from app.core.llm import get_llm
from app.modules.destination.state import DestinationState
from app.modules.planner.nodes import stream_llm

logger = logging.getLogger("langgraph-travel-planner.destination")


def city_research_node(state: DestinationState) -> dict:
    """城市调研节点 — LLM 生成综合调研报告

    顺序调研 (简化版, 不用 Send fan-out):
    为主要目的地生成综合调研报告
    """
    destination = state.get("destination", "成都")
    travel_style = state.get("travel_style", "文化游")
    duration = state.get("duration", 3)

    llm = get_llm()
    prompt = DESTINATION_RESEARCH_PROMPT.format(
        city=destination, destination=destination, travel_style=travel_style, duration=duration,
    )
    content = stream_llm(llm, [HumanMessage(content=prompt)], "city_research")

    return {"research_result": {destination: content}, "city_details": {destination: content}}


def synthesize_findings_node(state: DestinationState) -> Command:
    """合成调研结果 + Command.PARENT 路由回主图

    LangGraph 知识点 #8/#9: Command(goto=...) + Command.PARENT
    合成调研结果, 然后跳回主图的 plan_generator 节点
    """
    research = state.get("research_result", {})

    # 合成摘要
    summary_parts = []
    for city, data in research.items():
        summary_text = str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
        summary_parts.append(f"【{city}】{summary_text}")
    combined = "\n".join(summary_parts)

    return Command(
        update={"research_result": {**research, "_summary": combined}},
        goto="plan_generator",
        graph=Command.PARENT,
    )
