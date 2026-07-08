"""Pydantic Settings — LLM、Checkpoint、Store 配置"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置 — 从 .env 文件加载"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── LLM ──
    LLM_MODEL: str = "deepseek-chat"
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_API_KEY: str = "your-api-key-here"
    LLM_TEMPERATURE: float = 0.7

    # ── Checkpoint ──
    CHECKPOINT_STORE: str = "memory"
    CHECKPOINT_DB_PATH: str = "checkpoints.db"

    # ── Store ──
    STORE_TYPE: str = "memory"

    # ── LangSmith (可选) ──
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "langgraph-travel-planner"
    LANGCHAIN_TRACING_V2: bool = False

    # ── Server ──
    HOST: str = "0.0.0.0"
    PORT: int = 8000


settings = Settings()
