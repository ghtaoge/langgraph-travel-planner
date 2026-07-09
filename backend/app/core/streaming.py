"""SSE 流式输出封装 — astream 逐节点 + 逐 token 流式 + DB 批次写入

核心改动:
1. 每个 SSE token 推送前端的同时，缓存到批次缓冲
2. 每 50 tokens 或 500ms → UPDATE chat_messages content (批次追加)
3. interrupt 事件 → 写入 metadata 到 chat_messages
4. completed 事件 → 写入最终完整 content + 更新 conversation.status
5. intent_parser node_end → 更新对话标题
"""

import json
import logging
import time

from langgraph.types import Command

from app.core.database import (
    insert_message,
    append_message_content,
    append_thinking_content,
    finalize_message,
    update_message_metadata,
    update_conversation_status,
    update_conversation_title,
)

logger = logging.getLogger("langgraph-travel-planner.streaming")


def _interrupt_value(raw_interrupt):
    """Extract interrupt payload from LangGraph Interrupt or dict-like values."""
    if hasattr(raw_interrupt, "value"):
        return raw_interrupt.value
    if isinstance(raw_interrupt, dict):
        return raw_interrupt.get("value", raw_interrupt)
    return raw_interrupt


def _extract_interrupts(node_output):
    """Return interrupt payloads from astream update output."""
    if isinstance(node_output, (list, tuple)):
        return [_interrupt_value(item) for item in node_output]
    if isinstance(node_output, dict) and "__interrupt__" in node_output:
        raw = node_output.get("__interrupt__") or []
        if not isinstance(raw, (list, tuple)):
            raw = [raw]
        return [_interrupt_value(item) for item in raw]
    if hasattr(node_output, "interrupts") and node_output.interrupts:
        return [_interrupt_value(item) for item in node_output.interrupts]
    return []




async def stream_graph_execution(graph, input_data: dict | Command, config: dict, pool, conversation_id: str):
    """SSE 流式执行 — 双模式推送 + DB 批次写入

    Args:
        graph: 编译后的 LangGraph 图实例
        input_data: 图输入数据或 Command(resume=...)
        config: LangGraph config (含 thread_id)
        pool: asyncpg 连接池
        conversation_id: 对话 ID (用于 DB 写入)
    """
    is_resume = isinstance(input_data, Command)

    # 创建空 assistant 消息行
    assistant_msg_id = await insert_message(pool, conversation_id, "assistant")
    thinking_buffer = []

    # 发送开始事件
    if not is_resume:
        yield json.dumps({"type": "custom", "data": {"status": "开始执行旅游规划图...", "progress": 0.05}})
    else:
        yield json.dumps({"type": "custom", "data": {"status": "恢复执行...", "progress": 0.5}})

    # Token 批次写入参数
    BATCH_SIZE = 50  # 每 50 tokens 写一次
    FLUSH_INTERVAL = 0.5  # 每 500ms 写一次
    content_buffer = []
    last_flush_time = time.time()

    # 意图解析结果 (用于标题更新)
    intent_result = None

    try:
        stream = graph.astream(input_data, config=config, stream_mode=["updates", "custom"])

        async for chunk in stream:
            mode, data = chunk

            if mode == "custom":
                # ── Token 级别流式事件 ──
                if isinstance(data, dict):
                    if "token" in data:
                        token_content = data["token"]
                        yield json.dumps({
                            "type": "token",
                            "node": data.get("node", ""),
                            "content": token_content,
                            "token_type": "output",
                        })
                        # Do not persist intermediate node JSON tokens into chat history.
                        # Final user-facing content is written on completion; interrupts write metadata.
                    elif "thinking_token" in data:
                        thinking_content = data["thinking_token"]
                        yield json.dumps({
                            "type": "token",
                            "node": data.get("node", ""),
                            "content": thinking_content,
                            "token_type": "thinking",
                        })
                        thinking_buffer.append(thinking_content)
                        # 思考 token 也做批次写入
                        if len(thinking_buffer) >= BATCH_SIZE or (time.time() - last_flush_time) >= FLUSH_INTERVAL:
                            chunk_thinking = "".join(thinking_buffer)
                            await append_thinking_content(pool, assistant_msg_id, chunk_thinking)
                            thinking_buffer.clear()

                    else:
                        yield json.dumps({"type": "custom", "data": data})

            elif mode == "updates":
                for node_name, node_output in data.items():

                    if isinstance(node_output, dict):
                        logger.info(f"astream chunk: node={node_name}, output_keys={list(node_output.keys())}")

                    # Interrupt handling: LangGraph may emit __interrupt__ as a node or inside node output.
                    interrupt_payloads = _extract_interrupts(node_output)
                    if node_name == "__interrupt__" and not interrupt_payloads:
                        state = await graph.aget_state(config)
                        for task in state.tasks:
                            if task.interrupts:
                                interrupt_payloads.append(_interrupt_value(task.interrupts[0]))
                                node_name = task.name
                                break

                    if interrupt_payloads:
                        interrupt_value = interrupt_payloads[0]
                        question_json = json.dumps(interrupt_value, ensure_ascii=False) if isinstance(interrupt_value, dict) else str(interrupt_value)
                        yield json.dumps({"type": "interrupt", "node": node_name, "question": question_json})
                        await update_message_metadata(pool, assistant_msg_id, {
                            "interrupt_type": node_name,
                            "interrupt_value": interrupt_value if isinstance(interrupt_value, dict) else {},
                        })
                        await update_conversation_status(pool, conversation_id, "interrupted")
                        if content_buffer:
                            await append_message_content(pool, assistant_msg_id, "".join(content_buffer))
                            content_buffer.clear()
                        if thinking_buffer:
                            await append_thinking_content(pool, assistant_msg_id, "".join(thinking_buffer))
                            thinking_buffer.clear()
                        return

                    # 正常节点
                    yield json.dumps({"type": "node_start", "node": node_name})

                    # intent_parser 完成后提取标题
                    if node_name == "intent_parser" and isinstance(node_output, dict):
                        destination = node_output.get("destination", "")
                        duration = node_output.get("duration", 0)
                        style = node_output.get("travel_style", "")
                        if destination:
                            title = f"{destination}{duration}天{style}"
                            await update_conversation_title(pool, conversation_id, title)

                    output_summary = _summarize_output(node_name, node_output)
                    if output_summary:
                        yield json.dumps({
                            "type": "custom",
                            "data": {"status": output_summary, "node": node_name, "progress": _estimate_progress(node_name)},
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

    # 最终 flush 所有未写入的缓冲
    if content_buffer:
        await append_message_content(pool, assistant_msg_id, "".join(content_buffer))
        content_buffer.clear()
    if thinking_buffer:
        await append_thinking_content(pool, assistant_msg_id, "".join(thinking_buffer))
        thinking_buffer.clear()

    # astream 结束 → 检查状态
    state = await graph.aget_state(config)

    # 检查 interrupt
    if state.tasks:
        for task in state.tasks:
            if task.interrupts:
                interrupt_value = task.interrupts[0].value
                question_json = json.dumps(interrupt_value, ensure_ascii=False) if isinstance(interrupt_value, dict) else str(interrupt_value)
                yield json.dumps({"type": "interrupt", "node": task.name, "question": question_json})
                await update_message_metadata(pool, assistant_msg_id, {
                    "interrupt_type": task.name,
                    "interrupt_value": interrupt_value if isinstance(interrupt_value, dict) else {},
                })
                await update_conversation_status(pool, conversation_id, "interrupted")
                return

    # 图正常完成
    final_state = state.values
    final_plan = final_state.get("final_plan", "")

    # 最终写入 — 完整 content + thinking_content
    # 从 DB 读取当前累积的 content 作为最终版本
    await finalize_message(pool, assistant_msg_id, final_plan if final_plan else "", None)
    await update_conversation_status(pool, conversation_id, "completed")
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
