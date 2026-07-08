"""主图节点函数 — intent_parser, plan_generator, quality_check, format_output, save_summary"""

import json
import logging
from datetime import date

from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer
from langgraph.store.base import BaseStore
from langgraph.types import Command, interrupt

from app.config.prompts import (
    BUDGET_CALC_PROMPT,
    INTENT_PARSE_PROMPT,
    QUALITY_CHECK_PROMPT,
    PLAN_GENERATE_PROMPT,
)
from app.config.settings import settings
from app.core.llm import get_llm
from app.modules.planner.state import BudgetResult, IntentResult, Plan, TravelState

logger = logging.getLogger("langgraph-travel-planner.planner")

# Database pool reference — set during lifespan
_db_pool = None


def set_db_pool(pool):
    """设置数据库连接池引用 — lifespan 中调用"""
    global _db_pool
    _db_pool = pool


def stream_llm(llm, messages, node_name: str) -> str:
    """流式调用 LLM — 逐 token 通过 get_stream_writer() 推送 SSE, 返回完整响应内容

    LangGraph 知识点:
    #24 get_stream_writer — writer({"token": ...}) → custom stream 事件 → SSE token 事件
    每个节点只需调用 stream_llm() 代替 llm.invoke(), 前端即可实时看到逐 token 输出

    ⚠️ 重要: LangChain ChatOpenAI._stream() 会丢弃 DeepSeek 的 reasoning_content
    因此改用 OpenAI SDK 直接流式, 确保 reasoning_content (思考 token) 正确捕获
    """
    import openai as _openai
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    writer = get_stream_writer()
    full_content = ""

    # 转换 LangChain messages → OpenAI format
    openai_messages = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            openai_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            openai_messages.append({"role": "assistant", "content": msg.content})
        elif isinstance(msg, SystemMessage):
            openai_messages.append({"role": "system", "content": msg.content})
        else:
            openai_messages.append({"role": "user", "content": str(msg)})

    # OpenAI SDK 直接流式 (捕获 LangChain 丢弃的 reasoning_content)
    client = _openai.OpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    )

    stream = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=openai_messages,
        stream=True,
        temperature=settings.LLM_TEMPERATURE,
    )

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        # DeepSeek reasoner: reasoning_content = 思考过程 (LangChain 不映射, 我们直接捕获)
        reasoning = getattr(delta, "reasoning_content", None) or ""
        content = delta.content or ""

        if reasoning:
            writer({"thinking_token": reasoning, "node": node_name})

        if content:
            full_content += content
            writer({"token": content, "node": node_name})

    return full_content


def _extract_json(content: str | list) -> str:
    """从 LLM 输出中提取 JSON — 支持 ```json 块、纯 JSON、混合文本、list content"""
    # ChatOpenAI 可能返回 list (多个 content blocks) 或 str
    if isinstance(content, list):
        # 合并所有 text content blocks
        content = "".join(
            block.get("text", str(block)) if isinstance(block, dict) else str(block)
            for block in content
        )
    if "```json" in content:
        return content.split("```json")[1].split("```")[0].strip()
    if "```" in content:
        return content.split("```")[1].split("```")[0].strip()
    # 找第一个 { 到最后一个 }
    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        return content[start:end]
    return content


def intent_parser_node(state: TravelState, store: BaseStore) -> dict:
    """意图解析节点 — Structured Output (prompt-based JSON) + Store 读取偏好 + get_stream_writer

    LangGraph 知识点:
    #13 Structured Output (JSON prompt 解析 — DeepSeek 不支持 json_schema response_format)
    #21 节点签名注入 store (store: BaseStore 参数)
    #18/#19 Store (读取用户偏好辅助解析)
    #24 get_stream_writer (发送进度事件)
    """
    writer = get_stream_writer()
    writer({"status": "解析意图中...", "progress": 0.1})

    # 从 Store 读取用户历史偏好
    user_id = state.get("user_id", "default_user")
    profile = store.get(("travel_profiles", user_id), "profile")
    if profile:
        past_style = profile.value.get("preferred_style", "")
        home_city = profile.value.get("home_city", "")
        past_preference = f"用户历史偏好: {past_style}, 出发城市: {home_city}"
    else:
        past_preference = "无"

    llm = get_llm()
    # DeepSeek 不支持 json_schema response_format, 使用 prompt + JSON 解析
    prompt = INTENT_PARSE_PROMPT.format(query=state["query"], past_preference=past_preference)
    # stream_llm: 逐 token 推送 SSE + 返回完整内容
    content = stream_llm(llm, [HumanMessage(content=prompt)], "intent_parser")

    try:
        # 尝试从 LLM 输出中提取 JSON (可能包含在 ```json 块中)
        json_str = _extract_json(content)
        result_dict = json.loads(json_str)
        # 清理键名中多余的引号
        result_dict = {k.strip('"'): v for k, v in result_dict.items()}
        result = IntentResult(**result_dict)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Intent parse failed: {e}, content: {content[:200]}")
        result = IntentResult(
            destination="成都",
            duration=3,
            travel_style="混合游",
            budget_level="中等",
        )

    # 更新 Store 中的偏好
    store.put(("travel_profiles", user_id), "profile", {
        "preferred_style": result.travel_style,
        "budget_level": result.budget_level,
    })

    writer({"status": "意图解析完成", "progress": 0.2})
    return {
        "intent": result.model_dump(),
        "destination": result.destination,
        "duration": result.duration,
        "travel_style": result.travel_style,
    }


def plan_generator_node(state: TravelState) -> dict:
    """生成3套方案 — 顺序调用 (简化版, 不用 Send fan-out)

    在主图直接生成 3 个方案, 不再需要 generate_single_plan 节点
    """
    styles = ["文化游", "美食游", "混合游"]
    destination = state.get("destination", "成都")
    duration = state.get("duration", 3)
    research = state.get("research_result", {})
    research_summary = ""
    if isinstance(research, dict):
        research_summary = str(research.get("_summary", ""))[:500]

    llm = get_llm()
    all_plans = []

    for i, style in enumerate(styles):
        prompt = PLAN_GENERATE_PROMPT.format(
            destination=destination, duration=duration, style=style, research_result=research_summary,
        )
        content = stream_llm(llm, [HumanMessage(content=prompt)], f"plan_generator_{style}")

        try:
            plan_dict = json.loads(_extract_json(content))
            plan = Plan(
                plan_id=i + 1,
                title=plan_dict.get("title", f"{destination}{duration}日{style}"),
                style=style,
                highlights=plan_dict.get("highlights", ["当地知名景点"]),
                daily_overview=plan_dict.get("daily_overview", ["Day1: 核心景点游览"]),
                estimated_budget=plan_dict.get("estimated_budget", "约3000元"),
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            plan = Plan(
                plan_id=i + 1, title=f"{destination}{duration}日{style}", style=style,
                highlights=["当地知名景点"], daily_overview=["Day1: 核心景点游览"],
                estimated_budget="约3000元",
            )
        all_plans.append(plan.model_dump())

    return {"plans": all_plans}


def user_select_node(state: TravelState) -> dict:
    """用户选择方案 — interrupt() 暂停等待用户选择

    LangGraph 知识点 #6: interrupt — 主图层面的 HITL
    """
    plans = state.get("plans", [])
    decision = interrupt({
        "question": "请从以下方案中选择一个",
        "plans": plans,
        "interrupt_type": "select",
    })

    selected_id = decision.get("selected_plan_id", 1)
    selected_plan = plans[selected_id - 1] if selected_id <= len(plans) else plans[0]

    return {"selected_plan_id": selected_id, "selected_plan": selected_plan}


def budget_calculator_node(state: TravelState) -> dict:
    """预算计算节点 — Structured Output (prompt-based JSON)"""
    llm = get_llm()

    itinerary = state.get("itinerary", {})
    destination = state.get("destination", "成都")
    duration = state.get("duration", 3)
    budget_level = "中等"

    prompt = BUDGET_CALC_PROMPT.format(
        destination=destination, duration=duration,
        itinerary_summary=str(itinerary)[:500], budget_level=budget_level,
    )
    content = stream_llm(llm, [HumanMessage(content=prompt)], "budget_calculator")

    try:
        result_dict = json.loads(_extract_json(content))
        result_dict = {k.strip('"'): v for k, v in result_dict.items()}
        result = BudgetResult(**result_dict)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Budget parse failed: {e}")
        result = BudgetResult(
            total_budget=3000,
            accommodation_cost=800,
            food_cost=600,
            transport_cost=500,
            activity_cost=400,
            budget_breakdown={},
        )

    return {"budget": result.model_dump()}


def user_approve_node(state: TravelState) -> dict:
    """最终审批节点 — interrupt() 暂停等待用户确认

    LangGraph 知识点:
    #6 interrupt — 最终审批 HITL
    拒绝时通过 add_conditional_edges(route_after_approve) 路由回 itinerary_refine
    """
    decision = interrupt({
        "question": "请确认最终行程和预算",
        "itinerary": state.get("itinerary", {}),
        "budget": state.get("budget", {}),
        "daily_plans": (state.get("itinerary", {}) or {}).get("daily_plans", []),
        "interrupt_type": "approve",
    })

    # Debug: 记录 resume decision
    logger.info(f"user_approve_node: decision={decision}, approval_status={decision.get('approval_status')}")

    return {
        "approval_status": decision.get("approval_status", "approved"),
        "approval_comment": decision.get("approval_comment", decision.get("comment", "")),
    }


def quality_check_node(state: TravelState) -> dict:
    """质量检查节点 — LLM 评估行程质量"""
    llm = get_llm()
    itinerary = state.get("itinerary", {})
    budget = state.get("budget", {})
    destination = state.get("destination", "成都")
    duration = state.get("duration", 3)

    prompt = QUALITY_CHECK_PROMPT.format(
        destination=destination, duration=duration,
        itinerary_summary=str(itinerary)[:500], budget_summary=str(budget)[:300],
    )
    content = stream_llm(llm, [HumanMessage(content=prompt)], "quality_check")

    try:
        result = json.loads(content)
        score = float(result.get("score", 5))
        feedback = result.get("feedback", "")
    except (json.JSONDecodeError, KeyError):
        score = 5.0
        feedback = "无法解析质量评分"

    iteration = state.get("iteration", 0) + 1
    return {"quality_score": score, "quality_feedback": feedback, "iteration": iteration}


def format_output_node(state: TravelState) -> dict:
    """格式化输出节点 — 生成最终行程文本"""
    itinerary = state.get("itinerary", {})
    budget = state.get("budget", {})
    destination = state.get("destination", "成都")

    lines = [f"🧳 {destination} 旅行规划"]
    lines.append(f"预算: 约{budget.get('total_budget', 3000)}元")

    daily_plans = itinerary.get("daily_plans", [])
    for dp in daily_plans:
        day = dp.get("day", 1)
        lines.append(f"\n📅 第{day}天:")
        activities = dp.get("activities", [])
        for act in activities:
            lines.append(f"  - {act.get('name', '景点')}: {act.get('description', '')}")

    lines.append(f"\n💡 小贴士:")
    for tip in itinerary.get("tips", ["提前预订门票", "注意天气变化"]):
        lines.append(f"  - {tip}")

    return {"final_plan": "\n".join(lines)}


def save_summary_node(state: TravelState, store: BaseStore) -> dict:
    """对话结束自动摘要 — Store 写入画像 + 摘要

    LangGraph 知识点:
    #18/#19 Store — 写入对话摘要和用户画像
    #20 namespace 分层 — ("conversation_summaries", user_id) / ("travel_profiles", user_id)
    """
    user_id = state.get("user_id", "default_user")
    thread_id = state.get("thread_id", "default_thread")
    destination = state.get("destination", "成都")
    duration = state.get("duration", 3)
    selected_plan = state.get("selected_plan", {})
    budget = state.get("budget", {})

    summary_text = f"{destination} {duration}天旅行, 选择了{selected_plan.get('title', '')}, 预算约{budget.get('total_budget', 0)}元"

    # 写入对话摘要
    store.put(
        ("conversation_summaries", user_id),
        key=thread_id,
        value={
            "destination": destination,
            "duration": duration,
            "selected_plan": selected_plan.get("title", ""),
            "summary": summary_text,
            "total_budget": budget.get("total_budget", 0),
            "created_at": str(date.today()),
        },
    )

    # 更新用户画像中的 past_trips
    profile = store.get(("travel_profiles", user_id), "profile")
    past_trips = profile.value.get("past_trips", []) if profile else []
    past_trips.append(f"{destination}{duration}日")
    store.put(("travel_profiles", user_id), "profile", {
        "past_trips": past_trips,
    })

    return {"summary_saved": True}
