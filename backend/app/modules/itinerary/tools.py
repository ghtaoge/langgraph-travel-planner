"""日程细化子图工具 — 引入共享工具供 create_react_agent 使用"""

from app.config.tools import weather_query, restaurant_search, hotel_search, attraction_search

ITINERARY_TOOLS = [weather_query, restaurant_search, hotel_search, attraction_search]
