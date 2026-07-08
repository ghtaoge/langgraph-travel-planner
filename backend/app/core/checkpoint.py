"""Checkpoint 配置 — 支持 Memory/SQLite 两种持久化"""

import sqlite3

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from app.config.settings import settings


def get_checkpointer(store: str | None = None, db_path: str | None = None):
    """获取 Checkpointer 实例

    Args:
        store: 存储类型 "memory"/"sqlite", 默认从 Settings 读取
        db_path: SQLite 数据库路径, 默认从 Settings 读取

    Returns:
        MemorySaver 或 SqliteSaver 实例
    """
    store = store or settings.CHECKPOINT_STORE

    if store == "sqlite":
        path = db_path or settings.CHECKPOINT_DB_PATH
        conn = sqlite3.connect(path, check_same_thread=False)
        saver = SqliteSaver(conn)
        try:
            saver.setup()
        except Exception:
            pass
        return saver
    elif store == "memory":
        return MemorySaver()
    else:
        raise ValueError(f"不支持的 checkpoint 存储: {store}")
