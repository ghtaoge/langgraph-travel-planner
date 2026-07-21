"""基础设施测试 — Settings, LLM, Checkpoint, Store"""

from app.config.settings import Settings


def test_settings_loads_from_env():
    """Settings 能从 .env 加载"""
    s = Settings(LLM_MODEL="qwen-plus", LLM_API_KEY="test-key")
    assert s.LLM_MODEL == "qwen-plus"
    assert s.LLM_API_KEY == "test-key"
    assert s.POSTGRES_URI.startswith("postgresql://")
    assert s.AMAP_BASE_URL == "https://restapi.amap.com"


def test_get_llm_returns_chat_openai():
    """get_llm 返回 ChatOpenAI 实例"""
    from app.core.llm import get_llm
    llm = get_llm()
    assert llm.model_name == "deepseek-chat"


def test_get_checkpointer_factory_is_async():
    """生产 Checkpointer 工厂可导入，测试不连接 PostgreSQL。"""
    import inspect

    from app.core.checkpoint import get_checkpointer

    assert inspect.iscoroutinefunction(get_checkpointer)


def test_get_store_factory_is_callable():
    """生产 Store 工厂可导入，测试不连接 PostgreSQL。"""
    from app.core.store import get_store

    assert callable(get_store)
