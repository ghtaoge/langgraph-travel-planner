"""Deterministic validation and comparison metrics for candidate plans."""

from copy import deepcopy


def validate_candidates_node(state: dict) -> dict:
    duration = state.get("duration", 1)
    provider_data = (state.get("research_result") or {}).get("_provider") or {}
    pois = provider_data.get("pois") or []
    meta = provider_data.get("meta") or {}
    plans = []

    for raw_plan in state.get("plans") or []:
        plan = deepcopy(raw_plan)
        day_count = len(plan.get("daily_overview") or [])
        warnings = []
        if day_count != duration:
            warnings.append(f"方案天数为{day_count}，与需求{duration}天不一致")
        if not plan.get("highlights"):
            warnings.append("方案缺少可比较的核心亮点")
        plan["metrics"] = {
            "day_count": day_count,
            "highlight_count": len(plan.get("highlights") or []),
            "available_poi_count": len(pois),
            "data_provider": meta.get("provider", "unknown"),
            "estimated_data": bool(meta.get("estimated", False)),
            "stale_data": bool(meta.get("stale", False)),
        }
        plan["validation"] = {"valid": not warnings, "warnings": warnings}
        plans.append(plan)

    provider_warnings = list(state.get("provider_warnings") or [])
    if meta.get("estimated"):
        provider_warnings.append("候选方案基于估算 POI 数据")
    if meta.get("stale"):
        provider_warnings.append("候选方案使用了过期 POI 数据")
    return {
        "plans": plans,
        "provider_warnings": list(dict.fromkeys(provider_warnings)),
    }
