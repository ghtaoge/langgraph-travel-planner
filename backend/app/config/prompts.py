"""Prompt 模板 — 所有 LLM 调用 prompt (中文)

注意: Python .format() 把 {} 当格式占位符, JSON 模板中的花括号必须用 {{ }} 转义
"""

INTENT_PARSE_PROMPT = """你是一个旅游意图解析助手。请根据用户输入解析旅行意图。

用户输入: {query}
用户历史偏好: {past_preference}

请严格按照以下 JSON 格式输出，不要输出任何其他内容：
{{"destination": "目的地城市名", "duration": 旅行天数整数, "travel_style": "旅行风格(文化游/美食游/自然游/混合)", "budget_level": "预算水平(经济/中等/高端)", "special_requests": ["特殊需求列表"]}}

如果用户没有明确指定某些字段, 请根据上下文推断合理的默认值。"""

DESTINATION_RESEARCH_PROMPT = """你是一个旅游目的地调研助手。请为以下城市提供详细的旅游调研报告。

目标城市: {city}
目的地: {destination}
旅行风格: {travel_style}
天数: {duration}

请提供:
1. 该城市的核心景点和特色 (包含名称、描述、时长、费用)
2. 当地美食特色
3. 住宿推荐区域
4. 交通方式建议
5. 最佳游览季节和注意事项"""

PLAN_GENERATE_PROMPT = """你是一个旅游行程规划助手。请生成一套详细的旅行方案。

目的地: {destination}
天数: {duration}
风格: {style}
调研结果: {research_result}

请严格按照以下 JSON 格式输出，不要输出任何其他内容：
{{"plan_id": 方案编号, "title": "方案标题", "style": "旅行风格", "highlights": ["亮点1", "亮点2"], "daily_overview": ["Day1概要", "Day2概要"], "estimated_budget": "约3000元"}}"""

DAILY_PLAN_PROMPT = """你是一个旅游日程细化助手。请为旅行方案的第 {day} 天安排详细行程。

目的地: {destination}
风格: {style}
当天概要: {overview}
日期: {date}

请严格按照以下 JSON 格式输出，不要输出任何其他内容：
{{"day": {day}, "date": "{date}", "activities": [{{"name": "活动名", "description": "活动详细描述", "time": "时段(如09:00-12:00)", "cost": 门票费用数字, "location": "地点"}}], "transport": "当天交通方式描述", "hotel_name": "推荐酒店名", "restaurant_names": ["推荐餐厅1", "推荐餐厅2"]}}"""

BUDGET_CALC_PROMPT = """你是一个旅游预算计算助手。请根据行程信息计算详细预算。

目的地: {destination}
天数: {duration}
行程概要: {itinerary_summary}
预算水平: {budget_level}

请严格按照以下 JSON 格式输出，不要输出任何其他内容：
{{"total_budget": 总预算金额, "accommodation_cost": 住宿费用, "food_cost": 餐饮费用, "transport_cost": 交通费用, "activity_cost": 门票活动费用, "budget_breakdown": {{\"day1\": 金额, \"day2\": 金额}}}}"""

QUALITY_CHECK_PROMPT = """你是一个旅游行程质量评审员。请评估以下行程的质量。

目的地: {destination}
天数: {duration}
行程内容: {itinerary_summary}
预算: {budget_summary}

请评估以下维度并给出综合评分 (0-10):
1. 行程合理性 (景点间距、时间安排)
2. 体验丰富度 (景点/美食/文化覆盖)
3. 预算合理性 (费用分配是否合理)
4. 可执行性 (交通、时间是否可行)

请严格按照以下 JSON 格式输出，不要输出任何其他内容：
{{"score": 评分数字0到10, "feedback": "改进建议"}}"""
