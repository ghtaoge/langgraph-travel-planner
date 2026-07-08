# LangGraph Travel Planner

基于 LangGraph 的旅游规划助手 — 26 个 LangGraph 知识点全覆盖，开源演示项目。

![Vue 3](https://img.shields.io/badge/Vue-3-green) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-blue) ![LangGraph](https://img.shields.io/badge/LangGraph-0.4+-orange) ![Python](https://img.shields.io/badge/Python-3.11+-blue)

## 功能概览

- 🌍 **智能旅游规划** — 输入旅行需求，AI 生成多套行程方案
- ⏸️ **人机协同 (Human-in-the-loop)** — 方案选择、行程审批、逐日确认三重 interrupt
- ⚡ **实时 SSE 流式** — 逐 token 输出，节点执行进度可视化
- 🔙 **Checkpoint 回退** — 回退到任意 checkpoint 重新规划
- 💾 **跨对话记忆** — Store 保存用户画像 + 对话摘要，再次打开不失忆
- 🗺️ **Leaflet 地图** — 行程景点可视化标记
- 📸 **行程卡片导出** — html2canvas 截图保存
- 🔗 **LangSmith Trace** — 可视化追踪每次图执行

## 26 个 LangGraph 知识点

| # | 知识点 | 实现 |
|---|---|---|
| 1 | StateGraph | `build_travel_planner_graph()` |
| 2 | START / END | 主图 + 子图入口出口 |
| 3 | add_node | 11 个主图节点 + 5 个子图节点 |
| 4 | add_edge | 12 条主图边 + 5 条子图边 |
| 5 | add_conditional_edges | `route_after_quality` (score<7 循环 / score>=7 输出) |
| 6 | TypedDict State | `TravelState`, `DestinationState`, `ItineraryState` |
| 7 | Annotated reducers | `operator.add` (messages, plans), `merge_dicts` (research_result) |
| 8 | interrupt() | `user_select`, `user_approve`, `daily_confirm` 三级 |
| 9 | Command(resume=...) | POST /resume 恢复 interrupt |
| 10 | Command(goto=...) | 子图 `synthesize_findings` → Command.PARENT |
| 11 | Send | `plan_generator` (3 方案并行) + `city_research_fanout` (多城市并行) |
| 12 | Subgraph 嵌套 | destination_research + itinerary_refine 子图 |
| 13 | 共享 + 私有 State key | 子图 TravelState 共享 key + 子图私有 key |
| 14 | ToolNode | `create_react_agent` 带 4 个 @tool |
| 15 | Structured Output | `IntentResult`, `BudgetResult` + `with_structured_output` |
| 16 | RetryPolicy | `retry_policy=RetryPolicy(max_attempts=3)` |
| 17 | Checkpoint | MemorySaver (dev) / SqliteSaver (prod) |
| 18 | Store | InMemoryStore + namespace 用户画像/对话摘要 |
| 19 | get_stream_writer | `intent_parser_node` 自定义 SSE 进度事件 |
| 20 | astream_events v3 | `stream_graph_execution()` token 级流式 |
| 21 | MessagesState | `Annotated[list[BaseMessage], operator.add]` |
| 22 | context_schema | `UserContext(user_id)` 注入到每个节点 |
| 23 | SSE 事件协议 | node_start/end/token/interrupt/custom/completed |
| 24 | 多 Agent | 意图解析 + 目的地研究 + 方案生成 + ReAct Agent + 质量检查 |
| 25 | 分支循环 | quality<7 → itinerary_refine 循环 (max 3 次) |
| 26 | Store 跨对话 | 保存/加载用户画像 + 对话摘要 |

## 项目结构

```
langgraph-travel-planner/
├── backend/                  # FastAPI + LangGraph
│   ├── app/
│   │   ├── config/           # settings, tools, prompts
│   │   ├── core/             # llm, checkpoint, store, streaming
│   │   ├── modules/
│   │   │   ├── planner/      # 主图 (state, nodes, graph, conditions)
│   │   │   ├── destination/  # 子图A (state, nodes, graph, tools)
│   │   │   ├── itinerary/    # 子图B (state, nodes, graph, react_agent, tools)
│   │   ├── api/              # routes (travel, topology, history), schemas
│   │   ├── main.py           # FastAPI 入口
│   │   └── tests/            # 37 个 pytest 测试
│   ├── pyproject.toml
│   └── requirements.txt
│
├── frontend/                 # Vue 3 + Vite + TypeScript
│   ├── src/
│   │   ├── types/            # SSE, itinerary, graph 类型定义
│   │   ├── stores/           # Pinia (chat, graph, history)
│   │   ├── services/         # SSE service, API service
│   │   ├── components/       # 13 个 Vue 组件
│   │   ├── App.vue
│   │   └── main.ts
│   ├── vite.config.ts
│   └── package.json
│
├── docker-compose.yml
├── .env.example
├── LICENSE
└── .gitignore
```

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example backend/.env
# 编辑 backend/.env, 设置 LLM_API_KEY (DeepSeek/Qwen/OpenAI)
```

### 2. 本地开发 (推荐)

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
# 打开 http://localhost:5173
```

### 3. Docker 一键部署

```bash
cp .env.example backend/.env
# 编辑 backend/.env
docker-compose up --build
# 打开 http://localhost
```

### 4. 运行测试

```bash
cd backend
pytest app/tests/ -v
# 37 tests should pass
```

## API 文档

启动后端后访问 `http://localhost:8000/docs` (Swagger UI)

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/travel/stream` | POST | SSE 流式执行新对话 |
| `/api/travel/resume` | POST | 恢复 interrupt (SSE) |
| `/api/travel/rollback` | POST | 回退到 checkpoint (SSE) |
| `/api/travel/topology` | GET | 图拓扑定义 |
| `/api/travel/history` | GET | 对话摘要列表 |
| `/api/travel/profile` | GET | 用户旅行画像 |
| `/api/travel/conversation/{id}` | GET | 对话详情 |
| `/api/travel/states/{id}` | GET | Checkpoint 时间线 |

## 技术栈

**后端:** Python 3.11 · FastAPI 0.115 · LangGraph 0.4+ · LangChain · Pydantic · Uvicorn

**前端:** Vue 3 · Vite 6 · TypeScript · Pinia · Leaflet · html2canvas · Axios

**LLM:** DeepSeek / Qwen / OpenAI (OpenAI SDK 兼容)

**可视化:** LangSmith · SSE 实时流

## License

MIT License — Copyright (c) 2026 Gooeto
