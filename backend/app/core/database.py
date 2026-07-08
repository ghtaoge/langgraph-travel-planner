"""PostgreSQL 连接池 + 业务 SQL 操作

核心职责:
1. 管理 asyncpg 连接池 (lifespan 中初始化/清理)
2. 提供消息写入/读取/批次追加的异步函数
3. 提供对话 CRUD 的异步函数
"""

import asyncpg
import json
import uuid
from typing import Optional

from app.config.settings import settings

_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """获取全局连接池 — 在 FastAPI lifespan 中初始化"""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.POSTGRES_URI,
            min_size=2,
            max_size=10,
        )
    return _pool


async def close_db_pool():
    """关闭连接池 — 在 FastAPI lifespan shutdown 中调用"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def init_schema():
    """初始化数据库表 — 从 init.sql 执行 DDL"""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        schema_path = "app/migrations/init.sql"
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                sql = f.read()
            await conn.execute(sql)
        except Exception as e:
            # 表可能已存在, 忽略
            print(f"Schema init warning: {e}")


# ── 用户操作 ──

async def create_user(pool: asyncpg.Pool, username: str, password_hash: str) -> dict:
    """创建用户"""
    row = await pool.fetchrow(
        "INSERT INTO users (username, password_hash) VALUES ($1, $2) RETURNING id, username, created_at",
        username, password_hash,
    )
    return {"id": str(row["id"]), "username": row["username"], "created_at": str(row["created_at"])}


async def get_user_by_username(pool: asyncpg.Pool, username: str) -> Optional[dict]:
    """按用户名查询"""
    row = await pool.fetchrow(
        "SELECT id, username, password_hash, created_at FROM users WHERE username = $1",
        username,
    )
    if not row:
        return None
    return {"id": str(row["id"]), "username": row["username"], "password_hash": row["password_hash"]}


async def get_user_by_id(pool: asyncpg.Pool, user_id: str) -> Optional[dict]:
    """按 ID 查询"""
    row = await pool.fetchrow(
        "SELECT id, username, created_at FROM users WHERE id = $1",
        uuid.UUID(user_id),
    )
    if not row:
        return None
    return {"id": str(row["id"]), "username": row["username"]}


# ── 对话操作 ──

async def create_conversation(pool: asyncpg.Pool, user_id: str, thread_id: str, title: str = "新对话") -> dict:
    """创建对话 — thread_id 作为 conversation.id"""
    row = await pool.fetchrow(
        "INSERT INTO conversations (id, user_id, title, status) VALUES ($1, $2, $3, 'active') "
        "RETURNING id, user_id, title, status, created_at",
        uuid.UUID(thread_id), uuid.UUID(user_id), title,
    )
    return {
        "id": str(row["id"]), "user_id": str(row["user_id"]),
        "title": row["title"], "status": row["status"],
        "created_at": str(row["created_at"]),
    }


async def fetch_conversations(pool: asyncpg.Pool, user_id: str, page: int = 1, per_page: int = 20) -> list:
    """获取用户对话列表 — 分页"""
    offset = (page - 1) * per_page
    rows = await pool.fetch(
        "SELECT id, title, status, created_at, updated_at FROM conversations "
        "WHERE user_id = $1 ORDER BY updated_at DESC LIMIT $2 OFFSET $3",
        uuid.UUID(user_id), per_page, offset,
    )
    return [
        {
            "id": str(r["id"]), "title": r["title"], "status": r["status"],
            "created_at": str(r["created_at"]), "updated_at": str(r["updated_at"]),
        }
        for r in rows
    ]


async def update_conversation_status(pool: asyncpg.Pool, conversation_id: str, status: str):
    """更新对话状态"""
    await pool.execute(
        "UPDATE conversations SET status = $1, updated_at = NOW() WHERE id = $2",
        status, uuid.UUID(conversation_id),
    )


async def update_conversation_title(pool: asyncpg.Pool, conversation_id: str, title: str):
    """更新对话标题"""
    await pool.execute(
        "UPDATE conversations SET title = $1, updated_at = NOW() WHERE id = $2",
        title, uuid.UUID(conversation_id),
    )


async def delete_conversation(pool: asyncpg.Pool, conversation_id: str):
    """删除对话及其所有消息 (CASCADE)"""
    await pool.execute(
        "DELETE FROM conversations WHERE id = $1",
        uuid.UUID(conversation_id),
    )


# ── 消息操作 ──

async def insert_message(
    pool: asyncpg.Pool,
    conversation_id: str,
    role: str,
    content: str = "",
    thinking_content: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> str:
    """插入消息 — 返回 msg_id"""
    msg_id = uuid.uuid4()
    meta_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
    await pool.execute(
        "INSERT INTO chat_messages (id, conversation_id, role, content, thinking_content, metadata) "
        "VALUES ($1, $2, $3, $4, $5, $6)",
        msg_id, uuid.UUID(conversation_id), role, content, thinking_content, meta_json,
    )
    return str(msg_id)


async def append_message_content(pool: asyncpg.Pool, msg_id: str, content_chunk: str):
    """追加 content — 批次写入 token 缓冲"""
    await pool.execute(
        "UPDATE chat_messages SET content = content || $1 WHERE id = $2",
        content_chunk, uuid.UUID(msg_id),
    )


async def append_thinking_content(pool: asyncpg.Pool, msg_id: str, thinking_chunk: str):
    """追加 thinking_content — 批次写入思考 token 缓冲"""
    await pool.execute(
        "UPDATE chat_messages SET thinking_content = COALESCE(thinking_content, '') || $1 WHERE id = $2",
        thinking_chunk, uuid.UUID(msg_id),
    )


async def finalize_message(
    pool: asyncpg.Pool,
    msg_id: str,
    full_content: str,
    thinking_content: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """最终写入 — 完整 content + thinking + metadata"""
    meta_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
    await pool.execute(
        "UPDATE chat_messages SET content = $1, thinking_content = $2, metadata = COALESCE(metadata, $3) WHERE id = $4",
        full_content, thinking_content, meta_json, uuid.UUID(msg_id),
    )


async def update_message_metadata(pool: asyncpg.Pool, msg_id: str, metadata: dict):
    """更新消息 metadata — interrupt 信息写入"""
    meta_json = json.dumps(metadata, ensure_ascii=False)
    await pool.execute(
        "UPDATE chat_messages SET metadata = $1 WHERE id = $2",
        meta_json, uuid.UUID(msg_id),
    )


async def fetch_messages(pool: asyncpg.Pool, conversation_id: str) -> list:
    """获取对话所有消息 — 按时间排序"""
    rows = await pool.fetch(
        "SELECT id, role, content, thinking_content, metadata, created_at FROM chat_messages "
        "WHERE conversation_id = $1 ORDER BY created_at ASC",
        uuid.UUID(conversation_id),
    )
    result = []
    for r in rows:
        msg = {
            "id": str(r["id"]),
            "role": r["role"],
            "content": r["content"],
            "thinking_content": r["thinking_content"],
            "metadata": json.loads(r["metadata"]) if r["metadata"] else None,
            "created_at": str(r["created_at"]),
        }
        result.append(msg)
    return result


async def get_conversation_status(pool: asyncpg.Pool, conversation_id: str) -> Optional[str]:
    """获取对话状态"""
    row = await pool.fetchrow(
        "SELECT status FROM conversations WHERE id = $1",
        uuid.UUID(conversation_id),
    )
    return row["status"] if row else None
