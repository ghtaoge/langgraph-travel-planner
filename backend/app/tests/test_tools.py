"""工具测试 — mock 工具返回预期数据"""

from app.config.tools import weather_query, restaurant_search, hotel_search, attraction_search


def test_weather_query_known_city():
    """weather_query 返回已知城市的天气"""
    result = weather_query.invoke({"city": "成都", "date": "2026-07-08"})
    assert "28°C" in result or "28" in result


def test_weather_query_unknown_city():
    """weather_query 返回未知城市的默认天气"""
    result = weather_query.invoke({"city": "苏州", "date": "2026-07-08"})
    assert "25°C" in result


def test_restaurant_search_known():
    """restaurant_search 返回已知区域推荐"""
    result = restaurant_search.invoke({"city": "成都", "area": "宽窄巷子"})
    assert "小龙坎" in result


def test_hotel_search_known():
    """hotel_search 返回已知区域住宿"""
    result = hotel_search.invoke({"city": "成都", "area": "宽窄巷子"})
    assert "民宿" in result


def test_attraction_search_known():
    """attraction_search 返回已知城市景点"""
    result = attraction_search.invoke({"city": "成都", "style": "文化"})
    assert "武侯祠" in result
