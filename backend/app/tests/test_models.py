"""State 模型测试 — reducers, Structured Output schemas"""

from app.modules.planner.state import (
    TravelState, IntentResult, BudgetResult, Plan, DailyPlan,
    Activity, Location, ItineraryResult, UserContext, merge_dicts,
)


def test_merge_dicts_reducer():
    """merge_dicts reducer 安全合并两个 dict"""
    result = merge_dicts({"city_a": "成都调研"}, {"city_b": "重庆调研"})
    assert result == {"city_a": "成都调研", "city_b": "重庆调研"}


def test_merge_dicts_empty_left():
    """merge_dicts 处理 left=None"""
    result = merge_dicts(None, {"city_b": "重庆调研"})
    assert result == {"city_b": "重庆调研"}


def test_merge_dicts_overwrite():
    """merge_dicts 右侧覆盖左侧同名 key"""
    result = merge_dicts({"city_a": "旧数据"}, {"city_a": "新数据"})
    assert result == {"city_a": "新数据"}


def test_intent_result_schema():
    """IntentResult 结构化输出字段验证"""
    intent = IntentResult(destination="成都", duration=3, travel_style="文化游", budget_level="中等")
    assert intent.destination == "成都"
    assert intent.duration == 3
    assert intent.special_requests == []


def test_budget_result_schema():
    """BudgetResult 结构化输出字段验证"""
    budget = BudgetResult(
        total_budget=3000, accommodation_cost=600, food_cost=900,
        transport_cost=500, activity_cost=400, budget_breakdown={"day1": 1000},
    )
    assert budget.total_budget == 3000


def test_plan_schema():
    """Plan 行程方案模型验证"""
    plan = Plan(
        plan_id=1, title="成都文化游", style="文化游",
        highlights=["武侯祠"], daily_overview=["Day1"], estimated_budget="3000元",
    )
    assert plan.plan_id == 1


def test_user_context_dataclass():
    """UserContext context_schema 验证"""
    ctx = UserContext(user_id="user_001")
    assert ctx.user_id == "user_001"
