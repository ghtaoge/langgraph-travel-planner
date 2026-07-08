"""基础设施测试 — Settings, LLM, Checkpoint, Store"""

from app.config.settings import Settings


def test_settings_loads_from_env():
    """Settings 能从 .env 加载"""
    s = Settings(LLM_MODEL="qwen-plus", LLM_API_KEY="test-key")
    assert s.LLM_MODEL == "qwen-plus"
    assert s.LLM_API_KEY == "test-key"
    assert s.CHECKPOINT_STORE == "memory"


def test_get_llm_returns_chat_openai():
    """get_llm 返回 ChatOpenAI 实例"""
    from app.core.llm import get_llm
    llm = get_llm()
    assert llm.model_name == "deepseek-chat"


def test_get_checkpointer_memory():
    """get_checkpointer 返回 MemorySaver"""
    from app.core.checkpoint import get_checkpointer
    from langgraph.checkpoint.memory import MemorySaver
    cp = get_checkpointer(store="memory")
    assert isinstance(cp, MemorySaver)


def test_get_store_returns_in_memory_store():
    """get_store 返回 InMemoryStore"""
    from app.core.store import get_store
    from langgraph.store.memory import InMemoryStore
    store = get_store()
    assert isinstance(store, InMemoryStore)
