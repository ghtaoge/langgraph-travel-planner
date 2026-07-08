"""Store 配置 — 跨对话持久记忆"""

from langgraph.store.memory import InMemoryStore

from app.config.settings import settings


def get_store():
    """获取 Store 实例 — InMemoryStore (开发环境)

    Returns:
        InMemoryStore 实例
    """
    if settings.STORE_TYPE == "memory":
        return InMemoryStore()
    else:
        raise ValueError(f"不支持的 store 类型: {settings.STORE_TYPE}")
