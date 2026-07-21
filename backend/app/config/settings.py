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
    POSTGRES_URI: str = "postgresql://travel_user:travel_pass_2026@localhost:5432/travel_planner"

    # ── Travel data providers ──
    AMAP_API_KEY: str = ""
    AMAP_BASE_URL: str = "https://restapi.amap.com"
    PROVIDER_TIMEOUT_SECONDS: float = 8.0
    PROVIDER_CACHE_TTL_SECONDS: int = 3600
    WEATHER_CACHE_TTL_SECONDS: int = 1800

    # ── JWT Auth ──
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_EXPIRE_HOURS: int = 24
    JWT_ALGORITHM: str = "HS256"

    # ── Account verification ──
    # phone | email | both. Controls which bound account can be used for password reset.
    PASSWORD_RESET_CHANNEL: str = "both"
    VERIFICATION_CODE_EXPIRE_MINUTES: int = 10
    DEV_RETURN_VERIFICATION_CODE: bool = True

    # ── LangSmith (可选) ──
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "langgraph-travel-planner"
    LANGCHAIN_TRACING_V2: bool = False

    # ── Server ──
    HOST: str = "0.0.0.0"
    PORT: int = 8000


settings = Settings()
