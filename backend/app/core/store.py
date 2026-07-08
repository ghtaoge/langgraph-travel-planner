"""Store 配置 — PostgreSQL 持久化 (PostgresStore)"""

from contextlib import AbstractContextManager

from langgraph.store.postgres import PostgresStore

from app.config.settings import settings

_store: PostgresStore | None = None
_store_cm: AbstractContextManager[PostgresStore] | None = None


def get_store() -> PostgresStore:
    """获取 PostgresStore 实例 — lifespan 中初始化"""
    global _store, _store_cm
    if _store is None:
        _store_cm = PostgresStore.from_conn_string(settings.POSTGRES_URI)
        _store = _store_cm.__enter__()
        _store.setup()
    return _store


def init_store():
    """初始化 store — 在 lifespan startup 中调用"""
    get_store()


def close_store():
    """清理 store — 在 lifespan shutdown 中调用"""
    global _store, _store_cm
    if _store_cm is not None:
        _store_cm.__exit__(None, None, None)
    _store = None
    _store_cm = None