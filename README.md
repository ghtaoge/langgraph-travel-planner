# LangGraph Travel Planner

基于 LangGraph 的旅游规划助手 — 企业级持久化 + 多对话并发 + JWT 认证。

![Vue 3](https://img.shields.io/badge/Vue-3-green) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-blue) ![LangGraph](https://img.shields.io/badge/LangGraph-0.4+-orange) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue) ![JWT](https://img.shields.io/badge/JWT-Auth-green) ![Python](https://img.shields.io/badge/Python-3.11+-blue)

## 功能概览

- 🌍 **智能旅游规划** — 输入旅行需求，AI 生成多套行程方案
- ⏸️ **人机协同 (Human-in-the-loop)** — 方案选择、行程审批、逐日确认三重 interrupt
- ⚡ **实时 SSE 流式** — 逐 token 输出，节点执行进度可视化
- 🔙 **Checkpoint 回退** — 回退到任意 checkpoint 重新规划
- 💾 **PostgreSQL 持久化** — 聊天记录、checkpoint、用户画像全部存 PG，刷新不丢失
- 🔑 **JWT 认证** — 独立用户系统，注册/登录，所有 API 需认证
- 📂 **多对话并发** — DeepSeek 风格侧边栏，切换对话后台继续执行
- 🔄 **刷新恢复** — 刷新页面自动恢复聊天记录 + interrupt 状态
- 🗺️ **Leaflet 地图** — 行程景点可视化标记
- 📸 **行程卡片导出** — html2canvas 截图保存
- 🔗 **LangSmith Trace** — 可视化追踪每次图执行

## 项目结构

```
langgraph-travel-planner/
├── backend/                  # FastAPI + LangGraph + PostgreSQL
│   ├── app/
│   │   ├── config/           # settings, tools, prompts
│   │   ├── core/             # llm, auth, database, checkpoint, store, streaming
│   │   ├── modules/
│   │   │   ├── planner/      # 主图 (state, nodes, graph, conditions)
│   │   │   ├── destination/  # 子图A (state, nodes, graph, tools)
│   │   │   ├── itinerary/    # 子图B (state, nodes, graph, react_agent, tools)
│   │   ├── api/              # routes (auth, travel, topology, history, conversations), schemas
│   │   ├── migrations/       # init.sql (DDL)
│   │   ├── main.py           # FastAPI 入口 + lifespan PG 初始化
│   │   └── tests/            # pytest 测试
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                 # Vue 3 + Vue Router + Pinia + TypeScript
│   ├── src/
│   │   ├── types/            # SSE, itinerary, graph 类型定义
│   │   ├── stores/           # Pinia (chat, graph, auth, conversations)
│   │   ├── router/           # Vue Router + 认证守卫
│   │   ├── views/            # ChatView, LoginView, RegisterView
│   │   ├── services/         # SSE service, API service (JWT interceptor)
│   │   ├── components/       # Vue 组件 (MessageList, PlanSelector, etc.)
│   │   ├── App.vue           # DeepSeek 风格侧边栏 + router-view
│   │   └── main.ts
│   ├── vite.config.ts
│   └── package.json
│
├── docker-compose.yml        # PostgreSQL + backend + frontend
├── .env.example
└── README.md
```

## 快速开始

### 1. 启动 PostgreSQL

```bash
# 使用 Docker
docker compose up postgres -d

# 或本地安装 PostgreSQL 16, 创建数据库
createdb travel_planner
```

### 2. 配置环境变量

```bash
cp .env.example backend/.env
# 编辑 backend/.env, 必填:
#   LLM_API_KEY=your-deepseek-key
#   POSTGRES_URI=postgresql://travel_user:travel_pass_2026@localhost:5432/travel_planner
#   JWT_SECRET_KEY=your-random-secret-string
```

### 3. 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
# 打开 http://localhost:5173 → 自动跳转登录页
```

### 4. Docker 一键部署

```bash
cp .env.example backend/.env
# 编辑 backend/.env (设置 LLM_API_KEY + JWT_SECRET_KEY)
docker compose up --build
# 打开 http://localhost → 登录页
```

## API 文档

启动后端后访问 `http://localhost:8000/docs` (Swagger UI)

### 认证 API

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/auth/register` | POST | 注册新用户 → JWT |
| `/api/auth/login` | POST | 登录 → JWT |
| `/api/auth/me` | GET | 当前用户信息 (需认证) |

### 对话 API

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/conversations` | GET | 用户对话列表 (分页) |
| `/api/conversations` | POST | 创建新对话 |
| `/api/conversations/:id` | PATCH | 更新标题/状态 |
| `/api/conversations/:id` | DELETE | 删除对话 |
| `/api/conversations/:id/messages` | GET | 获取对话消息 (含 thinking/metadata) |

### 旅游规划 API (需认证)

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/travel/stream` | POST | SSE 流式执行新对话 |
| `/api/travel/resume` | POST | 恢复 interrupt (SSE) |
| `/api/travel/rollback` | POST | 回退到 checkpoint (SSE) |
| `/api/travel/topology` | GET | 图拓扑定义 |
| `/api/travel/history` | GET | 对话历史列表 |
| `/api/travel/profile` | GET | 用户旅行画像 |

## 技术栈

**后端:** Python 3.11 · FastAPI 0.115 · LangGraph 0.4+ · PostgreSQL 16 · AsyncPostgresSaver · PostgresStore · asyncpg · PyJWT · bcrypt

**前端:** Vue 3 · Vue Router 4 · Vite 8 · TypeScript · Pinia · Axios · Leaflet · html2canvas

**LLM:** DeepSeek / Qwen / OpenAI (OpenAI SDK 兼容)

**可视化:** LangSmith · SSE 实时流

## License

MIT License — Copyright (c) 2026 Gooeto
