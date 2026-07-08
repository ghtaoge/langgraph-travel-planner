"""图拓扑定义 API — 前端渲染拓扑图用

与 app/modules/planner/graph.py 对齐 — 10 个节点:
  intent_parser, destination_research, plan_generator, user_select,
  itinerary_refine, budget_calculator, user_approve, quality_check,
  format_output, save_summary
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/travel", tags=["图拓扑"])


@router.get("/topology")
async def get_topology():
    """返回主图 + 子图的拓扑定义 JSON

    前端使用此数据渲染 GraphTopology.vue 组件
    """
    nodes = [
        {"id": "intent_parser", "label": "意图解析", "type": "llm"},
        {"id": "destination_research", "label": "目的地研究", "type": "subgraph"},
        {"id": "plan_generator", "label": "方案生成", "type": "llm"},
        {"id": "user_select", "label": "用户选择", "type": "interrupt"},
        {"id": "itinerary_refine", "label": "日程细化", "type": "subgraph"},
        {"id": "budget_calculator", "label": "预算计算", "type": "llm"},
        {"id": "user_approve", "label": "最终审批", "type": "interrupt"},
        {"id": "quality_check", "label": "质量检查", "type": "llm"},
        {"id": "format_output", "label": "格式化输出", "type": "output"},
        {"id": "save_summary", "label": "保存摘要", "type": "store"},
    ]

    edges = [
        {"from": "START", "to": "intent_parser"},
        {"from": "intent_parser", "to": "destination_research"},
        {"from": "destination_research", "to": "plan_generator"},
        {"from": "plan_generator", "to": "user_select"},
        {"from": "user_select", "to": "itinerary_refine"},
        {"from": "itinerary_refine", "to": "budget_calculator"},
        {"from": "budget_calculator", "to": "user_approve"},
        {"from": "user_approve", "to": "format_output", "conditional": True, "label": "approved → 直接输出"},
        {"from": "user_approve", "to": "itinerary_refine", "conditional": True, "label": "rejected → 重新细化"},
        {"from": "quality_check", "to": "itinerary_refine", "conditional": True, "label": "score<7 iter<3"},
        {"from": "quality_check", "to": "format_output", "conditional": True, "label": "score>=7 or iter>=3"},
        {"from": "format_output", "to": "save_summary"},
        {"from": "save_summary", "to": "END"},
    ]

    subgraphs = [
        {
            "id": "destination_research",
            "parent_node": "destination_research",
            "nodes": [
                {"id": "city_research", "label": "城市调研", "type": "llm"},
                {"id": "synthesize_findings", "label": "合成调研", "type": "command"},
            ],
            "edges": [
                {"from": "START", "to": "city_research"},
                {"from": "city_research", "to": "synthesize_findings"},
                {"from": "synthesize_findings", "to": "PARENT:plan_generator"},
            ],
        },
        {
            "id": "itinerary_refine",
            "parent_node": "itinerary_refine",
            "nodes": [
                {"id": "daily_planner", "label": "逐天编排", "type": "llm"},
                {"id": "travel_react_agent", "label": "ReAct Agent", "type": "react_agent"},
                {"id": "daily_confirm", "label": "每日确认", "type": "interrupt"},
                {"id": "assemble", "label": "合并行程", "type": "output"},
            ],
            "edges": [
                {"from": "START", "to": "daily_planner"},
                {"from": "daily_planner", "to": "travel_react_agent"},
                {"from": "travel_react_agent", "to": "daily_confirm"},
                {"from": "daily_confirm", "to": "assemble"},
                {"from": "assemble", "to": "END"},
            ],
        },
    ]

    return {"nodes": nodes, "edges": edges, "subgraphs": subgraphs}
