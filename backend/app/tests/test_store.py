"""Store 读写测试 — put/get/search"""

from langgraph.store.memory import InMemoryStore


def test_production_store_factory_is_importable_without_connecting():
    """导入生产 Store 工厂时不建立数据库连接。"""
    from app.core.store import get_store

    assert callable(get_store)


def test_store_put_and_get():
    """Store 能 put 和 get 数据"""
    store = InMemoryStore()
    store.put(("travel_profiles", "user_001"), "profile", {
        "preferred_style": "文化游",
        "budget_level": "中等",
        "past_trips": ["成都3日"],
    })
    item = store.get(("travel_profiles", "user_001"), "profile")
    assert item is not None
    assert item.value["preferred_style"] == "文化游"


def test_store_search():
    """Store search 能搜索 namespace 下的所有 item"""
    store = InMemoryStore()
    store.put(("conversation_summaries", "user_001"), "thread_1", {"destination": "成都"})
    store.put(("conversation_summaries", "user_001"), "thread_2", {"destination": "西安"})
    results = list(store.search(("conversation_summaries", "user_001")))
    assert len(results) == 2
