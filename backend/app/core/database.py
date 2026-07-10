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
        "SELECT id, username, COALESCE(nickname, username) AS nickname, COALESCE(phone, '') AS phone, COALESCE(email, '') AS email, COALESCE(phone_verified, false) AS phone_verified, COALESCE(email_verified, false) AS email_verified, COALESCE(avatar_url, '') AS avatar_url, COALESCE(theme, 'dark') AS theme, phone_verified, email_verified, created_at, updated_at FROM users WHERE id = $1",
        uuid.UUID(user_id),
    )
    if not row:
        return None
    return {"id": str(row["id"]), "username": row["username"], "nickname": row["nickname"], "phone": row["phone"], "email": row["email"], "phone_verified": row["phone_verified"], "email_verified": row["email_verified"], "avatar_url": row["avatar_url"], "theme": row["theme"], "created_at": str(row["created_at"])}


# ── 对话操作 ──

async def create_conversation(pool: asyncpg.Pool, user_id: str, thread_id: str, title: str = "新对话") -> dict:
    """创建对话 — thread_id 作为 conversation.id"""
    row = await pool.fetchrow(
        "INSERT INTO conversations (id, user_id, title, status) VALUES ($1, $2, $3, 'active') "
        "ON CONFLICT (id) DO UPDATE SET user_id = EXCLUDED.user_id, updated_at = NOW() "
        "RETURNING id, user_id, title, status, created_at, updated_at",
        uuid.UUID(thread_id), uuid.UUID(user_id), title,
    )
    return {
        "id": str(row["id"]), "user_id": str(row["user_id"]),
        "title": row["title"], "status": row["status"],
        "created_at": str(row["created_at"]), "updated_at": str(row["updated_at"]),
    }


async def fetch_conversations(pool: asyncpg.Pool, user_id: str, page: int = 1, per_page: int = 20) -> list:
    """获取用户对话列表 — 分页"""
    offset = (page - 1) * per_page
    rows = await pool.fetch(
        "SELECT id, user_id, title, status, created_at, updated_at FROM conversations "
        "WHERE user_id = $1 ORDER BY updated_at DESC LIMIT $2 OFFSET $3",
        uuid.UUID(user_id), per_page, offset,
    )
    return [
        {
            "id": str(r["id"]), "user_id": str(r["user_id"]), "title": r["title"], "status": r["status"],
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
        "SELECT id, conversation_id, role, content, thinking_content, metadata, created_at FROM chat_messages "
        "WHERE conversation_id = $1 ORDER BY created_at ASC",
        uuid.UUID(conversation_id),
    )
    result = []
    for r in rows:
        msg = {
            "id": str(r["id"]),
            "conversation_id": str(r["conversation_id"]),
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
async def get_user_by_account(pool: asyncpg.Pool, account: str) -> Optional[dict]:
    """按手机号/邮箱查询登录账号"""
    row = await pool.fetchrow(
        "SELECT id, username, password_hash, COALESCE(nickname, username) AS nickname, "
        "COALESCE(phone, '') AS phone, COALESCE(email, '') AS email, "
        "COALESCE(phone_verified, false) AS phone_verified, COALESCE(email_verified, false) AS email_verified, "
        "COALESCE(avatar_url, '') AS avatar_url, COALESCE(theme, 'dark') AS theme "
        "FROM users WHERE phone = $1 OR email = $1",
        account,
    )
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "username": row["username"],
        "password_hash": row["password_hash"],
        "nickname": row["nickname"],
        "phone": row["phone"],
        "email": row["email"],
        "phone_verified": row["phone_verified"],
        "email_verified": row["email_verified"],
        "avatar_url": row["avatar_url"],
        "theme": row["theme"],
    }


async def create_account_user(
    pool: asyncpg.Pool,
    username: str,
    password_hash: str,
    nickname: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
) -> dict:
    """创建带资料字段的用户"""
    # 注意：不要在 SQL 中直接写 "$4 IS NOT NULL" 来推导验证状态。
    # asyncpg 在 prepare 阶段无法从 IS NOT NULL 表达式里稳定推断参数类型，
    # 会抛出 AmbiguousParameterError。这里先在 Python 层计算布尔值，再作为
    # 明确的 $6/$7 参数传给 PostgreSQL，既避免类型歧义，也让注册逻辑更直观。
    phone_verified = phone is not None
    email_verified = email is not None
    row = await pool.fetchrow(
        "INSERT INTO users (username, password_hash, nickname, phone, email, phone_verified, email_verified) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7) "
        "RETURNING id, username, COALESCE(nickname, username) AS nickname, "
        "COALESCE(phone, '') AS phone, COALESCE(email, '') AS email, phone_verified, email_verified, "
        "COALESCE(avatar_url, '') AS avatar_url, COALESCE(theme, 'dark') AS theme, created_at, updated_at",
        username, password_hash, nickname, phone, email, phone_verified, email_verified,
    )
    return {
        "id": str(row["id"]),
        "username": row["username"],
        "nickname": row["nickname"],
        "phone": row["phone"],
        "email": row["email"],
        "phone_verified": row["phone_verified"],
        "email_verified": row["email_verified"],
        "avatar_url": row["avatar_url"],
        "theme": row["theme"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


async def update_user_profile(
    pool: asyncpg.Pool,
    user_id: str,
    nickname: Optional[str] = None,
    avatar_url: Optional[str] = None,
    theme: Optional[str] = None,
) -> dict:
    """更新用户资料"""
    row = await pool.fetchrow(
        "UPDATE users SET "
        "nickname = COALESCE($2, nickname), "
        "avatar_url = COALESCE($3, avatar_url), "
        "theme = COALESCE($4, theme), "
        "updated_at = NOW() WHERE id = $1 "
        "RETURNING id, username, COALESCE(nickname, username) AS nickname, "
        "COALESCE(phone, '') AS phone, COALESCE(email, '') AS email, phone_verified, email_verified, "
        "COALESCE(avatar_url, '') AS avatar_url, COALESCE(theme, 'dark') AS theme, created_at, updated_at",
        uuid.UUID(user_id), nickname, avatar_url, theme,
    )
    return {
        "id": str(row["id"]),
        "username": row["username"],
        "nickname": row["nickname"],
        "phone": row["phone"],
        "email": row["email"],
        "phone_verified": row["phone_verified"],
        "email_verified": row["email_verified"],
        "avatar_url": row["avatar_url"],
        "theme": row["theme"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


async def update_user_password(pool: asyncpg.Pool, user_id: str, password_hash: str):
    """更新用户密码"""
    await pool.execute(
        "UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2",
        password_hash, uuid.UUID(user_id),
    )
async def create_verification_code(
    pool: asyncpg.Pool,
    target_type: str,
    target: str,
    purpose: str,
    code: str,
    expires_at,
    user_id: Optional[str] = None,
):
    """创建验证码记录"""
    await pool.execute(
        "INSERT INTO verification_codes (user_id, target_type, target, purpose, code, expires_at) "
        "VALUES ($1, $2, $3, $4, $5, $6)",
        uuid.UUID(user_id) if user_id else None, target_type, target, purpose, code, expires_at,
    )


async def consume_verification_code(
    pool: asyncpg.Pool,
    target_type: str,
    target: str,
    purpose: str,
    code: str,
    user_id: Optional[str] = None,
) -> bool:
    """消费未过期验证码"""
    row = await pool.fetchrow(
        "SELECT id FROM verification_codes WHERE target_type = $1 AND target = $2 AND purpose = $3 "
        "AND code = $4 AND consumed_at IS NULL AND expires_at > NOW() "
        "AND ($5::uuid IS NULL OR user_id = $5::uuid) "
        "ORDER BY created_at DESC LIMIT 1",
        target_type, target, purpose, code, uuid.UUID(user_id) if user_id else None,
    )
    if not row:
        return False
    await pool.execute("UPDATE verification_codes SET consumed_at = NOW() WHERE id = $1", row["id"])
    return True


async def bind_user_account(pool: asyncpg.Pool, user_id: str, target_type: str, target: str) -> dict:
    """绑定手机号或邮箱"""
    if target_type == "phone":
        row = await pool.fetchrow(
            "UPDATE users SET phone = $2, phone_verified = TRUE, updated_at = NOW() WHERE id = $1 "
            "RETURNING id, username, COALESCE(nickname, username) AS nickname, "
            "COALESCE(phone, '') AS phone, COALESCE(email, '') AS email, phone_verified, email_verified, "
            "COALESCE(avatar_url, '') AS avatar_url, COALESCE(theme, 'dark') AS theme, created_at, updated_at",
            uuid.UUID(user_id), target,
        )
    else:
        row = await pool.fetchrow(
            "UPDATE users SET email = $2, email_verified = TRUE, updated_at = NOW() WHERE id = $1 "
            "RETURNING id, username, COALESCE(nickname, username) AS nickname, "
            "COALESCE(phone, '') AS phone, COALESCE(email, '') AS email, phone_verified, email_verified, "
            "COALESCE(avatar_url, '') AS avatar_url, COALESCE(theme, 'dark') AS theme, created_at, updated_at",
            uuid.UUID(user_id), target,
        )
    return {
        "id": str(row["id"]), "username": row["username"], "nickname": row["nickname"],
        "phone": row["phone"], "email": row["email"], "phone_verified": row["phone_verified"],
        "email_verified": row["email_verified"], "avatar_url": row["avatar_url"],
        "theme": row["theme"], "created_at": str(row["created_at"]), "updated_at": str(row["updated_at"]),
    }
