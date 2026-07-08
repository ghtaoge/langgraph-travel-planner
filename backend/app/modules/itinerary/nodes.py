"""日程细化子图节点 — daily_planner + daily_confirm(interrupt) + assemble"""

import json
import logging

from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer
from langgraph.types import interrupt

from app.config.prompts import DAILY_PLAN_PROMPT
from app.core.llm import get_llm
from app.modules.planner.nodes import stream_llm
from app.modules.itinerary.state import ItineraryState

logger = logging.getLogger("langgraph-travel-planner.itinerary")


def _extract_json(text: str) -> dict | None:
    """从 LLM 回复中提取 JSON (处理 ```json 包裹 / list content 等)"""
    if isinstance(text, list):
        # ChatOpenAI 可能返回 list[content_block]
        text = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in text
        )
    # 去掉 ```json 包裹
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()
    # 找到第一个 { 和最后一个 }
    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        try:
            return json.loads(text[first:last + 1])
        except json.JSONDecodeError:
            pass
    return None


def daily_planner_node(state: ItineraryState) -> dict:
    """逐天编排日程 — LLM 生成每天详细行程并解析为结构化 JSON

    支持用户拒绝反馈: 如果 approval_comment 非空, 融入 prompt 让 LLM 调整行程
    """
    selected_plan = state.get("selected_plan", {})
    style = selected_plan.get("style", "文化游")
    destination = selected_plan.get("title", "").split("日")[0] if "日" in selected_plan.get("title", "") else "成都"
    approval_comment = state.get("approval_comment", "")

    # 如果有用户拒绝反馈, 加入调整提示
    feedback_hint = ""
    if approval_comment:
        feedback_hint = f"\n\n⚠️ 用户反馈调整要求: {approval_comment}\n请根据此反馈对行程做出针对性调整 (如降低费用、更换景点、优化节奏等)。"

    llm = get_llm()
    daily_overviews = selected_plan.get("daily_overview", [])

    daily_plans = []
    for i, overview in enumerate(daily_overviews):
        prompt = DAILY_PLAN_PROMPT.format(
            day=i + 1, destination=destination, style=style,
            overview=overview, date=f"第{i + 1}天",
        ) + feedback_hint
        try:
            content = stream_llm(llm, [HumanMessage(content=prompt)], f"daily_planner_day{i+1}")
            parsed = _extract_json(content)

            if parsed and parsed.get("activities"):
                # LLM 返回了完整的行程 JSON — 直接使用
                day_plan = {
                    "day": i + 1,
                    "date": parsed.get("date", f"第{i + 1}天"),
                    "activities": parsed.get("activities", []),
                    "transport": parsed.get("transport", ""),
                    "hotel_name": parsed.get("hotel_name", ""),
                    "restaurant_names": parsed.get("restaurant_names", []),
                }
            else:
                # LLM 返回无法解析 — 使用 overview 作为 fallback
                day_plan = {
                    "day": i + 1,
                    "date": f"第{i + 1}天",
                    "activities": [{"name": overview[:30], "description": overview, "time": "全天", "cost": 0, "location": destination}],
                    "transport": "",
                    "hotel_name": "",
                    "restaurant_names": [],
                }
            daily_plans.append(day_plan)
            logger.info(f"Day {i + 1} planned: {len(day_plan.get('activities', []))} activities")

        except Exception as e:
            logger.warning(f"Day {i + 1} plan generation failed: {e}")
            # fallback: 用 overview 填充
            daily_plans.append({
                "day": i + 1,
                "date": f"第{i + 1}天",
                "activities": [{"name": overview[:30], "description": overview, "time": "全天", "cost": 0, "location": destination}],
                "transport": "",
                "hotel_name": "",
                "restaurant_names": [],
            })

    return {"daily_plans": daily_plans}


def daily_confirm_node(state: ItineraryState) -> dict:
    """每日行程确认 — interrupt() 暂停等待用户确认

    LangGraph 知识点 #6: interrupt — 子图内部的 HITL 节点
    """
    daily_plans = state.get("daily_plans", [])
    confirmed = interrupt(
        {
            "question": "请确认每日行程安排是否满意",
            "daily_plans": daily_plans,
            "confirmed_days": state.get("confirmed_days", 0),
        }
    )
    return {"confirmed_days": confirmed.get("confirmed_days", len(daily_plans))}


def assemble_node(state: ItineraryState) -> dict:
    """合并所有天为完整行程"""
    daily_plans = state.get("daily_plans", [])
    selected_plan = state.get("selected_plan", {})
    destination = selected_plan.get("title", "成都")

    itinerary = {
        "destination": destination,
        "duration": len(daily_plans),
        "daily_plans": daily_plans,
        "total_budget": 0,
        "tips": ["建议提前预订热门景点门票", "注意当地天气变化"],
    }
    return {"itinerary": itinerary}
