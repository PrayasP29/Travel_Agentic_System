"""Environment-driven project settings."""

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Centralized settings loaded from .env."""

    # API KEYS
    groq_api_key: str = ""
    tavily_api_key: str = ""

    # LANGCHAIN / LANGSMITH
    langchain_api_key: str = ""
    langchain_project: str = "TripPlanner"
    langchain_tracing: bool = True
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # MODELS
    groq_text_model: str = "openai/gpt-oss-20b"
    groq_transcription_model: str = "whisper-large-v3"

    # MCP SERVERS
    kiwi_mcp_server_url: str = "https://mcp.kiwi.com"
    weather_provider: str = "livedatalink" 
    weather_mcp_server_url: str = "https://livedatalink.ai/mcp"
    agentorist_mcp_server_url: str = "https://mcp.agentorist.com/mcp"

    # DIRECTORIES
    recordings_dir: str = "recordings"
    outputs_dir: str = "outputs"
    logs_dir: str = "logs"

    # REDIS
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_default_ttl: int = 1800
    redis_enabled: bool = True

    # RATE LIMITING
    rate_limit_enabled: bool = True
    login_max_attempts: int = 5
    login_lock_hours: int = 25
    register_max_attempts: int = 5
    register_lock_hours: int = 24
    trip_failure_max_attempts: int = 3
    trip_failure_lock_minutes: int = 20
    trip_success_daily_limit: int = 2
    trip_success_window_hours: int = 24

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache(maxsize=None)
def get_settings() -> Settings:
    """Return cached settings instance."""
    settings = Settings()

    os.environ["LANGCHAIN_TRACING_V2"] = str(settings.langchain_tracing).lower()
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint

    if settings.langchain_api_key:
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key

    return settings


settings = get_settings()