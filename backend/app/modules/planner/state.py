"""主图 State 定义 — TravelState + UserContext + merge_dicts reducer"""

import operator
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Optional, TypedDict

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


def merge_dicts(left: dict, right: dict) -> dict:
    """dict 合并 reducer — 并行 Agent 并发写 research_result 时安全合并"""
    result = dict(left or {})
    if right:
        result.update(right)
    return result


# ── Structured Output 模型 ──


class IntentResult(BaseModel):
    """意图解析结构化输出"""
    destination: str = Field(description="目的地城市名")
    duration: int = Field(description="旅行天数")
    travel_style: str = Field(description="旅行风格: 文化游/美食游/自然游/混合")
    budget_level: str = Field(description="预算水平: 经济/中等/高端")
    special_requests: list[str] = Field(default_factory=list, description="特殊需求")
    start_date: Optional[date] = Field(default=None, description="出发日期，未提供时为空")
    party_size: int = Field(default=1, ge=1, le=50, description="出行人数")
    budget_limit: Optional[float] = Field(default=None, ge=0, description="明确预算上限")


class BudgetResult(BaseModel):
    """预算计算结构化输出"""
    total_budget: float = Field(description="总预算金额(元)")
    accommodation_cost: float = Field(description="住宿费用")
    food_cost: float = Field(description="餐饮费用")
    transport_cost: float = Field(description="交通费用")
    activity_cost: float = Field(description="活动门票费用")
    budget_breakdown: dict = Field(description="每日预算明细")


# ── 行程数据模型 ──


class Location(BaseModel):
    """地理位置"""
    lat: float
    lng: float
    address: str


class Activity(BaseModel):
    """景点活动"""
    name: str
    description: str
    duration_hours: float
    cost: float
    location: Location


class Plan(BaseModel):
    """一套行程方案"""
    plan_id: int
    title: str
    style: str
    highlights: list[str]
    daily_overview: list[str]
    estimated_budget: str


class DailyPlan(BaseModel):
    """一天行程"""
    day: int
    date: str
    activities: list[Activity]
    transport: str
    hotel_name: str = ""
    restaurant_names: list[str] = Field(default_factory=list)


class ItineraryResult(BaseModel):
    """完整行程结果"""
    destination: str
    duration: int
    daily_plans: list[DailyPlan]
    total_budget: float
    tips: list[str]


# ── UserContext (context_schema) ──


@dataclass
class UserContext:
    """用户上下文 — 通过 context_schema 注入到每个节点"""
    user_id: str


# ── TravelState ──


class TravelState(TypedDict):
    """主图状态 — 旅游规划全流程"""

    # ── 对话 ──
    messages: Annotated[list[BaseMessage], operator.add]
    user_id: str
    thread_id: str

    # ── 意图 ──
    query: str
    intent: dict
    destination: str
    duration: int
    travel_style: str
    start_date: Optional[date]
    party_size: int

    # ── 调研 ──
    research_result: Annotated[dict, merge_dicts]
    provider_warnings: list[str]

    # ── 方案 ──
    plans: list[dict]
    selected_plan_id: int
    selected_plan: dict

    # ── 日程 ──
    itinerary: dict

    # ── 预算 ──
    budget: dict

    # ── 审批 ──
    approval_status: str
    approval_comment: str

    # ── 质量检查 ──
    quality_score: float
    quality_feedback: str
    iteration: int

    # ── 输出 ──
    final_plan: str
    summary_saved: bool
    trip_id: str
    trip_revision: int
    trip_snapshot: dict

    # ── 错误 ──
    error: Optional[str]
    error_node: Optional[str]
