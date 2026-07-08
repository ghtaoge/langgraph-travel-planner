"""Database helpers 测试 — 使用本地 PostgreSQL 连接"""

import pytest
import asyncio
import asyncpg

# 注意: 这些测试需要实际的 PostgreSQL 连接
# 在 CI 环境中使用 docker-compose 提供的 PG
# 本地开发时需要先运行 init.sql 创建表

SKIP_IF_NO_PG = True  # 没有 PG 时跳过

@pytest.fixture
async def pool():
    """测试连接池"""
    try:
        p = await asyncpg.create_pool(
            "postgresql://travel_user:password@localhost:5432/travel_planner_test",
            min_size=1, max_size=2,
        )
        yield p
        await p.close()
    except Exception:
        pytest.skip("PostgreSQL not available")


@pytest.mark.asyncio
async def test_create_and_fetch_user():
    """测试用户创建和查询"""
    if SKIP_IF_NO_PG:
        pytest.skip("PG not available")
    pool_conn = await asyncpg.connect(
        "postgresql://travel_user:password@localhost:5432/travel_planner_test"
    )
    try:
        # 创建用户
        row = await pool_conn.fetchrow(
            "INSERT INTO users (username, password_hash) VALUES ($1, $2) RETURNING id, username",
            "test_user_db", "hash123",
        )
        assert row["username"] == "test_user_db"

        # 查询用户
        found = await pool_conn.fetchrow(
            "SELECT id, username FROM users WHERE username = $1",
            "test_user_db",
        )
        assert found is not None
        assert found["username"] == "test_user_db"

        # 清理
        await pool_conn.execute("DELETE FROM users WHERE username = $1", "test_user_db")
    finally:
        await pool_conn.close()


@pytest.mark.asyncio
async def test_conversation_and_messages():
    """测试对话 + 消息 CRUD"""
    if SKIP_IF_NO_PG:
        pytest.skip("PG not available")
    pool_conn = await asyncpg.connect(
        "postgresql://travel_user:password@localhost:5432/travel_planner_test"
    )
    try:
        # 创建用户
        user_row = await pool_conn.fetchrow(
            "INSERT INTO users (username, password_hash) VALUES ($1, $2) RETURNING id",
            "conv_test_user", "hash456",
        )
        user_id = user_row["id"]

        # 创建对话
        import uuid
        thread_id = uuid.uuid4()
        conv_row = await pool_conn.fetchrow(
            "INSERT INTO conversations (id, user_id, title, status) VALUES ($1, $2, $3, 'active') RETURNING id, title, status",
            thread_id, user_id, "测试对话",
        )
        assert conv_row["title"] == "测试对话"

        # 写入消息
        msg_id = uuid.uuid4()
        await pool_conn.execute(
            "INSERT INTO chat_messages (id, conversation_id, role, content) VALUES ($1, $2, 'user', '我想去成都')",
            msg_id, thread_id,
        )

        # 追加 assistant 消息 content
        msg_id2 = uuid.uuid4()
        await pool_conn.execute(
            "INSERT INTO chat_messages (id, conversation_id, role, content) VALUES ($1, $2, 'assistant', '')",
            msg_id2, thread_id,
        )
        await pool_conn.execute(
            "UPDATE chat_messages SET content = content || $1 WHERE id = $2",
            "成都3天", msg_id2,
        )
        await pool_conn.execute(
            "UPDATE chat_messages SET content = content || $1 WHERE id = $2",
            "美食之旅", msg_id2,
        )

        # 查询消息
        msgs = await pool_conn.fetch(
            "SELECT role, content FROM chat_messages WHERE conversation_id = $1 ORDER BY created_at",
            thread_id,
        )
        assert len(msgs) == 2
        assert msgs[0]["content"] == "我想去成都"
        assert msgs[1]["content"] == "成都3天美食之旅"

        # 清理
        await pool_conn.execute("DELETE FROM conversations WHERE id = $1", thread_id)
        await pool_conn.execute("DELETE FROM users WHERE id = $1", user_id)
    finally:
        await pool_conn.close()
