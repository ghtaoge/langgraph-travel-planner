"""FastAPI 应用入口 — 注册所有路由 + CORS + lifespan"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import history, travel, topology


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期 — 初始化 Store + Checkpointer"""
    # Store + Checkpointer 在 build_travel_planner_graph() 中初始化
    yield


app = FastAPI(
    title="LangGraph Travel Planner",
    description="基于 LangGraph 的旅游规划助手 — 26 个知识点全覆盖",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(travel.router)
app.include_router(topology.router)
app.include_router(history.router)


@app.get("/")
async def root():
    """根路径 — 项目信息"""
    return {
        "name": "LangGraph Travel Planner",
        "version": "0.1.0",
        "description": "基于 LangGraph 的旅游规划助手",
        "langgraph_knowledge_points": 26,
        "docs": "/docs",
    }
