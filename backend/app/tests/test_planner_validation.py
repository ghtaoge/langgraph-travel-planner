"""Deterministic candidate validation tests."""

from app.modules.planner.validation import validate_candidates_node


def test_candidate_validation_adds_comparable_metrics_and_warnings():
    result = validate_candidates_node({
        "duration": 2,
        "research_result": {
            "_provider": {
                "pois": [{"name": "武侯祠"}, {"name": "杜甫草堂"}],
                "meta": {"provider": "mock", "estimated": True, "stale": False},
            }
        },
        "plans": [{
            "plan_id": 1,
            "title": "成都文化游",
            "style": "文化游",
            "highlights": ["武侯祠"],
            "daily_overview": ["第一天"],
            "estimated_budget": "约2000元",
        }],
    })

    plan = result["plans"][0]
    assert plan["metrics"]["day_count"] == 1
    assert plan["metrics"]["available_poi_count"] == 2
    assert plan["validation"]["valid"] is False
    assert "天数" in plan["validation"]["warnings"][0]
    assert result["provider_warnings"]
