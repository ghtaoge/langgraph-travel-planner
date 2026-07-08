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

## 系统架构

```
┌──────────────┐     SSE      ┌──────────────┐    asyncpg     ┌──────────────┐
│   Vue 3 SPA  │◄──────────► │   FastAPI     │◄──────────►  │  PostgreSQL   │
│  (Pinia+Router)│  /api/travel │  (LangGraph)  │              │   (WxMajor)   │
│              │              │              │◄──────────►  │              │
│  ┌─────────┐ │              │  ┌─────────┐ │  psycopg v3   │  ┌─────────┐ │
│  │AuthStore│ │  Authorization│  │JWT Auth │ │              │  │AsyncPG   │ │
│  │ConvsMgr │ │  Bearer token │  │bcrypt   │ │              │  │Saver     │ │
│  │ChatStore│ │              │  │PyJWT    │ │              │  │Store     │ │
│  └─────────┘ │              │  └─────────┘ │              │  └─────────┘ │
└──────────────┘              └──────────────┘              └──────────────┘
                                     │
                                     │ OpenAI SDK
                                     ▼
                              ┌──────────────┐
                              │  DeepSeek /   │
                              │  Qwen / OpenAI│
                              └──────────────┘
```

**数据流向：**
1. 用户登录 → JWT token → localStorage → 每次请求自动附加 `Authorization: Bearer <token>`
2. 发送消息 → 后端创建 conversation + 写 user 消息到 PG → SSE 流式执行 → token 批次写入 PG (50 tokens/500ms)
3. 切换对话 → 断开旧 SSE → 后端继续执行并写 PG → 切回时从 DB 拉取完整消息
4. 刷新页面 → Vue Router 加载 `/chat/:threadId` → 从 DB 恢复消息 + interrupt 状态

## 数据模型

```sql
-- 用户
users (id UUID, username, password_hash, created_at, updated_at)

-- 对话 (id = thread_id, 与 LangGraph checkpoint 关联)
conversations (id UUID, user_id, title, status[active/completed/interrupted], created_at, updated_at)

-- 聊天消息
chat_messages (id UUID, conversation_id, role[user/assistant/system], content, thinking_content, metadata JSONB, created_at)
```

**LangGraph 自动管理的表：** `checkpoints`、`checkpoint_writes`、`checkpoint_blobs`、`store`（由 AsyncPostgresSaver / PostgresStore 创建）

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
│   │   ├── api/
│   │   │   ├── routes/       # auth, conversations, travel, topology, history
│   │   │   ├── schemas/      # __init__.py, auth.py, conversation.py
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
├── docs/                     # 设计文档 + 实施计划
│   └── superpowers/
│       ├── specs/            # 设计规格文档
│       └── plans/            # 实施计划 (10 个任务)
│
├── docker-compose.yml        # PostgreSQL + backend + frontend
├── .env.example              # 环境变量模板
├── .gitignore
└── README.md
```

## 环境变量说明

| 变量 | 必填 | 说明 | 示例 |
|---|---|---|---|
| `LLM_API_KEY` | ✅ | DeepSeek/Qwen/OpenAI API Key | `sk-...` |
| `LLM_MODEL` | ❌ | LLM 模型名 | `deepseek-chat` (默认) |
| `LLM_BASE_URL` | ❌ | LLM API 地址 | `https://api.deepseek.com` (默认) |
| `POSTGRES_URI` | ✅ | PostgreSQL 连接串 | `postgresql://user:pass@host:5432/db` |
| `JWT_SECRET_KEY` | ✅ | JWT 签名密钥 (生产环境务必修改) | 随机字符串 |
| `JWT_EXPIRE_HOURS` | ❌ | Token 过期时间 | `24` (默认) |
| `LANGSMITH_API_KEY` | ❌ | LangSmith 追踪 Key | 可选，不填则关闭追踪 |

## 快速开始

### 方式一：Docker 一键部署 (推荐)

```bash
# 1. 克隆项目
git clone https://github.com/Gooeto/langgraph-travel-planner.git
cd langgraph-travel-planner

# 2. 配置环境变量
cp .env.example backend/.env
# 编辑 backend/.env, 修改:
#   LLM_API_KEY=你的 DeepSeek API Key
#   JWT_SECRET_KEY=随机密钥字符串

# 3. 启动
docker compose up --build

# 4. 打开 http://localhost → 登录页
```

Docker 方式会自动创建 PostgreSQL 容器，无需额外安装。

### 方式二：本地开发

#### 1. 准备 PostgreSQL

```bash
# 使用 Docker 启动 PG
docker compose up postgres -d

# 或使用已有的 PostgreSQL 实例, 创建数据库
createdb travel_planner   # 或用你已有的数据库
```

#### 2. 配置环境变量

```bash
cp .env.example backend/.env
# 编辑 backend/.env, 必填项:
#   LLM_API_KEY=你的 API Key
#   POSTGRES_URI=postgresql://travel_user:travel_pass_2026@localhost:5432/travel_planner
#   JWT_SECRET_KEY=随机密钥字符串
```

> **使用外部 PG 实例时**: 只需修改 `POSTGRES_URI` 指向你的数据库，首次启动后端会自动执行 `init.sql` 创建业务表。

#### 3. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# 首次启动会自动: 创建 PG 连接池 → 执行 init.sql → 初始化 AsyncPostgresSaver → 初始化 PostgresStore → 编译主图
```

#### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
# 打开 http://localhost:5173 → 自动跳转登录页
```

#### 5. 首次使用

1. 访问 `http://localhost:5173` → 自动跳转 `/login`
2. 点击「注册」 → 输入用户名密码 → 自动获得 JWT → 进入聊天页
3. 在左侧侧边栏点击「+ 新对话」 → 输入旅行需求 → AI 流式生成方案

## API 文档

启动后端后访问 `http://localhost:8000/docs` (Swagger UI)

### 认证 API

| 路径 | 方法 | 说明 | 认证 |
|---|---|---|---|
| `/api/auth/register` | POST | 注册新用户 → JWT | 不需要 |
| `/api/auth/login` | POST | 登录 → JWT | 不需要 |
| `/api/auth/me` | GET | 当前用户信息 | ✅ Bearer |

### 对话 API

| 路径 | 方法 | 说明 | 认证 |
|---|---|---|---|
| `/api/conversations` | GET | 用户对话列表 (分页) | ✅ |
| `/api/conversations` | POST | 创建新对话 | ✅ |
| `/api/conversations/:id` | PATCH | 更新标题/状态 | ✅ |
| `/api/conversations/:id` | DELETE | 删除对话及其消息 | ✅ |
| `/api/conversations/:id/messages` | GET | 获取对话消息 (含 thinking/metadata) | ✅ |

### 旅游规划 API

| 路径 | 方法 | 说明 | 认证 |
|---|---|---|---|
| `/api/travel/stream` | POST | SSE 流式执行新对话 | ✅ |
| `/api/travel/resume` | POST | 恢复 interrupt (SSE) | ✅ |
| `/api/travel/rollback` | POST | 回退到 checkpoint (SSE) | ✅ |
| `/api/travel/topology` | GET | 图拓扑定义 | ✅ |
| `/api/travel/history` | GET | 对话历史列表 | ✅ |
| `/api/travel/profile` | GET | 用户旅行画像 | ✅ |

### SSE 事件协议

所有 SSE 事件格式为 `data: {JSON}\n\n`：

| 事件类型 | 说明 |
|---|---|
| `thread_created` | 后端生成的 thread_id |
| `graph_topology` | 图拓扑定义 (节点/边/子图) |
| `node_start` | 节点开始执行 |
| `token` | LLM 逐 token 输出 (含 thinking/output 类型) |
| `interrupt` | human-in-the-loop 暂停 (含 plans/itinerary/budget 等结构化数据) |
| `custom` | 进度/状态更新 |
| `node_end` | 节点执行完成 |
| `completed` | 图执行完成 (含 final_plan) |

## 关键设计决策

### SSE 断开恢复策略

切换对话 A → B 时：
1. 前端断开 A 的 SSE 连接
2. 后端 A 的 graph 继续执行（AsyncPostgresSaver 自动持久化 checkpoint）
3. 用户切换回 A 时 → `GET /api/conversations/:id/messages` 从 DB 拉取完整消息
4. 如果 A 还是 interrupted 状态 → 从 metadata 恢复 PlanSelector / ApprovalDialog

### Token 批次写入

为避免逐 token 写 PG 的性能问题：
- 每 **50 tokens** 或 **500ms** 执行一次 `UPDATE chat_messages SET content = content || chunk`
- interrupt 事件 → 立即写入 metadata JSONB
- completed 事件 → 最终完整版本写入，conversation.status 更新为 completed
- intent_parser 完成 → 自动更新 conversation.title (如 "成都3天美食游")

### Interrupt 状态恢复

interrupt 信息存储在 `chat_messages.metadata` (JSONB)：

```json
{
  "interrupt_type": "user_select",
  "interrupt_value": {
    "question": "请从以下方案中选择一个",
    "plans": [{"plan_id": 1, "title": "美食文化之旅", "style": "文化探索"}]
  }
}
```

刷新后，前端从 DB 读取最后一条 assistant 消息的 metadata，自动恢复 PlanSelector / ApprovalDialog。

## 技术栈

**后端:** Python 3.11 · FastAPI 0.115 · LangGraph 0.4+ · PostgreSQL 16 · AsyncPostgresSaver · PostgresStore · asyncpg · PyJWT · bcrypt

**前端:** Vue 3.5 · Vue Router 4 · Vite 8 · TypeScript · Pinia 3 · Axios · Leaflet · html2canvas

**LLM:** DeepSeek / Qwen / OpenAI (OpenAI SDK 兼容，支持 reasoning_content 思考过程)

**可视化:** LangSmith · SSE 实时流 · 图拓扑可视化

## License

MIT License — Copyright (c) 2026 Gooeto
