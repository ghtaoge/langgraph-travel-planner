"""Checkpoint 配置 — PostgreSQL 持久化 (AsyncPostgresSaver)

从 MemorySaver 切换到 AsyncPostgresSaver:
- 服务重启后 checkpoint 数据不丢失
- 连接池由 psycopg 管理
- 必须在 FastAPI lifespan 中初始化 (async with)
"""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config.settings import settings

_saver: AsyncPostgresSaver | None = None


async def get_checkpointer() -> AsyncPostgresSaver:
    """获取 AsyncPostgresSaver 实例 — lifespan 中初始化"""
    if _saver is None:
        _saver = AsyncPostgresSaver.from_conn_string(settings.POSTGRES_URI)
        await _saver.setup()
    return _saver


async def init_checkpointer():
    """初始化 checkpointer — 在 lifespan startup 中调用"""
    global _saver
    _saver = AsyncPostgresSaver.from_conn_string(settings.POSTGRES_URI)
    await _saver.setup()


async def close_checkpointer():
    """清理 checkpointer — 在 lifespan shutdown 中调用"""
    # AsyncPostgresSaver 使用 from_conn_string 内部管理连接池
    # 不需要显式关闭
    global _saver
    _saver = None
