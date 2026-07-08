"""Checkpoint 配置 — PostgreSQL 持久化 (AsyncPostgresSaver)"""

from contextlib import AbstractAsyncContextManager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config.settings import settings

_saver: AsyncPostgresSaver | None = None
_saver_cm: AbstractAsyncContextManager[AsyncPostgresSaver] | None = None


async def get_checkpointer() -> AsyncPostgresSaver:
    """获取 AsyncPostgresSaver 实例 — lifespan 中初始化"""
    global _saver, _saver_cm
    if _saver is None:
        _saver_cm = AsyncPostgresSaver.from_conn_string(settings.POSTGRES_URI)
        _saver = await _saver_cm.__aenter__()
        await _saver.setup()
    return _saver


async def init_checkpointer():
    """初始化 checkpointer — 在 lifespan startup 中调用"""
    await get_checkpointer()


async def close_checkpointer():
    """清理 checkpointer — 在 lifespan shutdown 中调用"""
    global _saver, _saver_cm
    if _saver_cm is not None:
        await _saver_cm.__aexit__(None, None, None)
    _saver = None
    _saver_cm = None