"""LLM 初始化 — DeepSeek/Qwen, OpenAI SDK 兼容, streaming=True 启用逐 token 输出"""

from langchain_openai import ChatOpenAI

from app.config.settings import settings


def get_llm(temperature: float | None = None) -> ChatOpenAI:
    """获取 LLM 实例 — DeepSeek/Qwen 通过 OpenAI SDK 兼容接口调用

    Args:
        temperature: 生成温度, 默认从 Settings 读取

    Returns:
        ChatOpenAI 实例 (streaming=True, 逐 token 输出)
    """
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        temperature=temperature or settings.LLM_TEMPERATURE,
        streaming=True,  # 启用逐 token 流式输出 — 配合 get_stream_writer() 推送 SSE
    )
