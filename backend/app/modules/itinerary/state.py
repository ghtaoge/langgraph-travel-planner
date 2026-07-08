"""日程细化子图 State — ItineraryState (共享+私有 key)

注意: daily_plans 不再使用 operator.add reducer — 避免子图二次进入时日计划累积
"""

from typing import TypedDict


class ItineraryState(TypedDict):
    """日程细化子图状态

    共享 key:
    - selected_plan, itinerary

    私有 key:
    - daily_plans (纯 list, 不累积 — 每次进入子图时 daily_planner_node 返回完整列表覆盖旧值)
    - approval_comment (从父图传入的用户拒绝反馈, 供 daily_planner 调整行程)
    """

    # ── 共享 key ──
    selected_plan: dict
    itinerary: dict

    # ── 私有 key ──
    daily_plans: list[dict]          # 不再 Annotated[..., operator.add] — 避免二次进入累积
    confirmed_days: int
    approval_comment: str            # 用户拒绝反馈, 如 "价格贵了"
