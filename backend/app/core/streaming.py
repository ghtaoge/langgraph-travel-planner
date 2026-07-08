"""SSE 流式输出封装 — astream 逐节点 + 逐 token 流式

LangGraph v1.x 知识点:
#22 Streaming — astream(stream_mode=["updates", "custom"]) 逐节点推送 + token 级别推送
#24 get_stream_writer — 节点内 writer({"token": ...}) → custom stream 事件
"""

import json
import logging

from langgraph.types import Command

logger = logging.getLogger("langgraph-travel-planner.streaming")


async def stream_graph_execution(graph, input_data: dict | Command, config: dict):
    """SSE 流式执行 — astream(stream_mode=["updates", "custom"]) 双模式推送

    策略:
    1. "custom" 模式: 捕获 get_stream_writer() 逐 token 事件 — 实时推送 LLM 输出
    2. "updates" 模式: 捕获节点完成事件 — 推送 node_start/node_end + 进度
    3. __interrupt__ chunk → 发送 interrupt 事件
    4. 图完成后 yield completed 事件
    """
    is_resume = isinstance(input_data, Command)

    # 发送开始事件
    if not is_resume:
        yield json.dumps({"type": "custom", "data": {"status": "开始执行旅游规划图...", "progress": 0.05}})
    else:
        yield json.dumps({"type": "custom", "data": {"status": "恢复执行...", "progress": 0.5}})

    try:
        # 双模式流式: updates (节点完成) + custom (token 级别 / get_stream_writer)
        stream = graph.astream(input_data, config=config, stream_mode=["updates", "custom"])

        async for chunk in stream:
            mode, data = chunk

            if mode == "custom":
                # ── Token 级别流式事件 ──
                if isinstance(data, dict):
                    if "token" in data:
                        # LLM 输出 token → 逐 token 推送前端
                        yield json.dumps({
                            "type": "token",
                            "node": data.get("node", ""),
                            "content": data["token"],
                            "token_type": "output",
                        })
                    elif "thinking_token" in data:
                        # DeepSeek reasoning_content (思考 token) → 推送前端
                        yield json.dumps({
                            "type": "token",
                            "node": data.get("node", ""),
                            "content": data["thinking_token"],
                            "token_type": "thinking",
                        })
                    else:
                        # 其他 custom 事件 (status, progress, 等) — 保持原格式
                        yield json.dumps({"type": "custom", "data": data})

            elif mode == "updates":
                # ── Node 级别更新 ──
                for node_name, node_output in data.items():

                    # Debug: 记录每个 astream chunk
                    if isinstance(node_output, dict):
                        logger.info(f"astream chunk: node={node_name}, output_keys={list(node_output.keys())}, approval_status={node_output.get('approval_status')}")

                    # __interrupt__ 是 LangGraph 特殊标记
                    if node_name == "__interrupt__":
                        state = await graph.aget_state(config)
                        for task in state.tasks:
                            if task.interrupts:
                                interrupt_value = task.interrupts[0].value
                                question_json = json.dumps(interrupt_value, ensure_ascii=False) if isinstance(interrupt_value, dict) else str(interrupt_value)
                                yield json.dumps({"type": "interrupt", "node": task.name, "question": question_json})
                                return
                        yield json.dumps({"type": "interrupt", "node": "unknown", "question": json.dumps(node_output, ensure_ascii=False, default=str)})
                        return

                    # 正常节点: node_start → custom(进度) → node_end
                    yield json.dumps({"type": "node_start", "node": node_name})

                    # 详细日志
                    if node_name in ("user_approve", "quality_check", "itinerary_refine") and isinstance(node_output, dict):
                        logger.info(f"  {node_name} output: {json.dumps(node_output, ensure_ascii=False, default=str)[:300]}")

                    output_summary = _summarize_output(node_name, node_output)
                    if output_summary:
                        yield json.dumps({
                            "type": "custom",
                            "data": {
                                "status": output_summary,
                                "node": node_name,
                                "progress": _estimate_progress(node_name),
                            },
                        })

                    yield json.dumps({"type": "node_end", "node": node_name})

    except Exception as e:
        logger.error(f"Graph streaming error: {e}")
        yield json.dumps({"type": "custom", "data": {"status": f"执行错误: {str(e)[:200]}", "progress": 0}})
        try:
            state = await graph.aget_state(config)
            final_state = state.values
            yield json.dumps({"type": "completed", "data": {"final_plan": final_state.get("final_plan", "")}})
        except:
            yield json.dumps({"type": "completed", "data": {"final_plan": ""}})
        return

    # astream 结束 → 检查是否正常完成或有 interrupt
    state = await graph.aget_state(config)

    # 检查 interrupt
    if state.tasks:
        for task in state.tasks:
            if task.interrupts:
                interrupt_value = task.interrupts[0].value
                question_json = json.dumps(interrupt_value, ensure_ascii=False) if isinstance(interrupt_value, dict) else str(interrupt_value)
                yield json.dumps({"type": "interrupt", "node": task.name, "question": question_json})
                return

    # 图正常完成
    final_state = state.values
    final_plan = final_state.get("final_plan", "")
    yield json.dumps({"type": "completed", "data": {"final_plan": final_plan}})


def _summarize_output(node_name: str, output: dict) -> str:
    """从节点输出中提取简短描述"""
    if not output or not isinstance(output, dict):
        return ""

    if node_name == "destination_research":
        research = output.get("research_result", {})
        if isinstance(research, dict) and research.get("_summary"):
            return f"调研完成: {str(research['_summary'])[:80]}"
        return "完成目的地调研"

    if node_name == "itinerary_refine":
        itinerary = output.get("itinerary", {})
        if isinstance(itinerary, dict) and itinerary.get("daily_plans"):
            return f"行程细化: {len(itinerary['daily_plans'])}天安排"
        return "完成行程细化"

    summaries = {
        "intent_parser": lambda o: f"解析意图: 目标={o.get('destination', '?')}, {o.get('duration', '?')}天, 风格={o.get('travel_style', '?')}",
        "plan_generator": lambda o: f"生成 {len(o.get('plans', []))} 套旅行方案",
        "budget_calculator": lambda o: f"计算预算: 约{o.get('budget', {}).get('total_budget', '?')}元" if isinstance(o.get('budget'), dict) else "计算预算...",
        "quality_check": lambda o: f"质量评分: {o.get('quality_score', '?')}分",
        "format_output": lambda o: "格式化最终行程...",
        "save_summary": lambda o: "保存对话摘要",
        "user_select": lambda o: "等待用户选择方案",
        "user_approve": lambda o: "等待用户审批",
    }

    fn = summaries.get(node_name)
    if fn:
        try:
            return fn(output)
        except:
            return ""

    return ""


def _estimate_progress(node_name: str) -> float:
    """估算节点执行进度"""
    progress_map = {
        "intent_parser": 0.1,
        "destination_research": 0.2,
        "plan_generator": 0.3,
        "user_select": 0.35,
        "itinerary_refine": 0.5,
        "budget_calculator": 0.6,
        "user_approve": 0.7,
        "quality_check": 0.8,
        "format_output": 0.9,
        "save_summary": 0.95,
    }
    return progress_map.get(node_name, 0.5)
