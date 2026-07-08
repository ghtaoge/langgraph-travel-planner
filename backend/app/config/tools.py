"""工具定义 — 天气/餐饮/住宿/景点查询 (模拟数据)"""

from langchain_core.tools import tool


@tool
def weather_query(city: str, date: str) -> str:
    """查询某城市某天的天气情况

    Args:
        city: 城市名, 如 "成都"
        date: 日期, 如 "2026-07-08"

    Returns:
        天气描述文本
    """
    weather_data = {
        "成都": "多云转晴, 28°C, 偶有阵雨, 适合室内+户外混合活动",
        "西安": "晴, 32°C, 干燥炎热, 建议早晚出行",
        "重庆": "阵雨, 30°C, 湿热, 建议室内活动为主",
        "北京": "晴, 33°C, 炎热, 注意防晒",
    }
    return weather_data.get(city, f"{city} {date}: 晴, 25°C, 适合户外活动")


@tool
def restaurant_search(city: str, area: str, cuisine_type: str = "本地特色") -> str:
    """搜索某城市某区域的餐厅推荐

    Args:
        city: 城市名
        area: 区域名, 如 "宽窄巷子"
        cuisine_type: 餐饮类型, 默认 "本地特色"

    Returns:
        餐厅推荐文本
    """
    restaurant_data = {
        ("成都", "宽窄巷子"): "推荐: 小龙坎火锅(正宗川味)、宽窄巷子小吃街(三大炮、糖油果子)、陈麻婆豆腐(百年老字号)",
        ("成都", "春熙路"): "推荐: 串串香老店、龙抄手总店、春熙路美食城",
        ("西安", "回民街"): "推荐: 老孙家羊肉泡馍、贾三灌汤包、回民街肉夹馍",
    }
    return restaurant_data.get((city, area), f"{city} {area} {cuisine_type}: 推荐老字号餐厅、本地特色小吃")


@tool
def hotel_search(city: str, area: str, hotel_type: str = "民宿") -> str:
    """搜索某城市某区域的住宿推荐

    Args:
        city: 城市名
        area: 区域名
        hotel_type: 住宿类型, 默认 "民宿"

    Returns:
        住宿推荐文本
    """
    hotel_data = {
        ("成都", "宽窄巷子"): "推荐: 宽窄巷子旁民宿(约200元/晚, 位置极佳)、青旅客栈(约80元/晚)",
        ("成都", "春熙路"): "推荐: 春熙路精品酒店(约350元/晚)、如家快捷(约150元/晚)",
    }
    return hotel_data.get((city, area), f"{city} {area} {hotel_type}: 推荐{hotel_type}, 约200元/晚")


@tool
def attraction_search(city: str, style: str = "文化") -> str:
    """搜索某城市某风格的景点

    Args:
        city: 城市名
        style: 景点风格, 如 "文化"/"自然"/"美食"

    Returns:
        景点推荐文本
    """
    attraction_data = {
        ("成都", "文化"): "武侯祠(三国文化, 2h, 50元)、杜甫草堂(诗歌文化, 1.5h, 40元)、金沙遗址(古蜀文明, 2h, 70元)",
        ("成都", "自然"): "大熊猫繁育研究基地(3h, 55元)、青城山(5h, 80元)、都江堰(3h, 80元)",
        ("成都", "美食"): "宽窄巷子(美食街, 2h)、锦里古街(小吃, 1.5h)、春熙路(商圈, 2h)",
        ("西安", "文化"): "秦始皇兵马俑(3h, 120元)、大雁塔(1.5h, 40元)、陕西历史博物馆(2h, 免费)",
    }
    return attraction_data.get((city, style), f"{city} {style}: 推荐当地知名景点")
