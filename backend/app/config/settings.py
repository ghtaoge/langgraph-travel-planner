"""Pydantic Settings — LLM、PostgreSQL、JWT、Store 配置"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置 — 从 .env 文件加载"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── LLM ──
    LLM_MODEL: str = "deepseek-chat"
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_API_KEY: str = "your-api-key-here"
    LLM_TEMPERATURE: float = 0.7

    # ── PostgreSQL ──
    POSTGRES_URI: str = "postgresql://travel_user:password@localhost:5432/travel_planner"

    # ── JWT Auth ──
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_EXPIRE_HOURS: int = 24
    JWT_ALGORITHM: str = "HS256"

    # ── LangSmith (可选) ──
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "langgraph-travel-planner"
    LANGCHAIN_TRACING_V2: bool = False

    # ── Server ──
    HOST: str = "0.0.0.0"
    PORT: int = 8000


settings = Settings()
