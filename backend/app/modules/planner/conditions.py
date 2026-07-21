"""条件路由函数 — quality_check 循环路由 + user_approve 拒绝路由"""

import logging

logger = logging.getLogger("langgraph-travel-planner.conditions")


def route_after_quality(state: dict) -> str:
    """质量检查后路由

    LangGraph 知识点 #5: add_conditional_edges

    路由逻辑:
    - score >= 7 → format_output (质量达标)
    - score < 7 且 iteration < 3 → itinerary_refine (循环重试)
    - score < 7 且 iteration >= 3 → format_output (放弃重试)
    """
    score = state.get("quality_score", 0)
    iteration = state.get("iteration", 0)

    if score >= 7:
        return "format_output"
    elif iteration < 3:
        return "itinerary_refine"
    else:
        return "format_output"


def route_after_approve(state: dict) -> str:
    """用户审批后路由 — 批准后直接输出, 拒绝时回到细化

    LangGraph 知识点 #5: add_conditional_edges + 用户反馈驱动循环

    路由逻辑:
    - approved → persist_trip (先保存不可变业务版本, 再输出)
    - rejected → itinerary_refine (根据 approval_comment 反馈调整行程)

    注意: 之前 approved → quality_check 可能得分低 → itinerary_refine → 再次 interrupt
    造成反复弹框的糟糕体验, 改为批准后直接输出。
    """
    approval = state.get("approval_status", "approved")
    logger.info(f"route_after_approve: approval_status={approval}")
    if approval == "approved":
        return "persist_trip"
    else:
        return "itinerary_refine"
