"""Store 配置 — PostgreSQL 持久化 (PostgresStore)

从 InMemoryStore 切换到 PostgresStore:
- 用户画像和对话摘要持久化
- 服务重启后 Store 数据不丢失
"""

from langgraph.store.postgres import PostgresStore

from app.config.settings import settings

_store: PostgresStore | None = None


def get_store() -> PostgresStore:
    """获取 PostgresStore 实例 — lifespan 中初始化"""
    if _store is None:
        _store = PostgresStore.from_conn_string(settings.POSTGRES_URI)
        _store.setup()
    return _store


def init_store():
    """初始化 store — 在 lifespan startup 中调用"""
    global _store
    _store = PostgresStore.from_conn_string(settings.POSTGRES_URI)
    _store.setup()


def close_store():
    """清理 store — 在 lifespan shutdown 中调用"""
    global _store
    _store = None
