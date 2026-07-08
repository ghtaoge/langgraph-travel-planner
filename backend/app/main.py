"""FastAPI 应用入口 — 注册所有路由 + CORS + lifespan (PG 初始化)"""

from contextlib import asynccontextmanager

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, conversations, history, travel, topology
from app.core.checkpoint import init_checkpointer, close_checkpointer
from app.core.database import get_db_pool, close_db_pool, init_schema
from app.core.store import init_store, close_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期 — 初始化 PG 连接池 + Checkpointer + Store + Schema"""
    # 1. 初始化 PG 连接池
    pool = await get_db_pool()

    # 2. 初始化数据库表
    await init_schema()

    # 3. 初始化 LangGraph checkpointer (AsyncPostgresSaver)
    await init_checkpointer()

    # 4. 初始化 LangGraph store (PostgresStore)
    init_store()

    # 5. 预构建主图 (compile with PG checkpointer + store)
    from app.modules.planner.graph import build_travel_planner_graph
    await build_travel_planner_graph()

    # 6. 设置 nodes 的 DB pool 引用
    from app.modules.planner.nodes import set_db_pool
    set_db_pool(pool)

    yield

    # Shutdown: 清理连接池 + checkpointer + store
    await close_db_pool()
    await close_checkpointer()
    close_store()


app = FastAPI(
    title="LangGraph Travel Planner",
    description="基于 LangGraph 的旅游规划助手 — 企业级持久化 + 多对话并发",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(travel.router)
app.include_router(topology.router)
app.include_router(history.router)


@app.get("/")
async def root():
    """根路径 — 项目信息"""
    return {
        "name": "LangGraph Travel Planner",
        "version": "1.0.0",
        "description": "基于 LangGraph 的旅游规划助手 — 企业级持久化 + 多对话并发",
        "docs": "/docs",
    }
