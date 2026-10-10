"""
Application configuration and environment settings.
"""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    # FalkorDB settings
    FALKORDB_HOST: str = "localhost"
    FALKORDB_PORT: int = 6379
    FALKORDB_GRAPH: str = "trust"

    # SQLite operational store settings
    SQLITE_DB_PATH: str = "trust_operational.db"

    # API and server settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # LLM Settings
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    LLM_MODE: Literal["live", "replay", "mock"] = "replay"
    CACHE_DIR: str = "llm_cache"

    # Simulation & paths
    SCENARIOS_DIR: str = "scenarios"
    TELEMETRY_LOG_PATH: str = "telemetry.jsonl"
    PARALLEL_HYPOTHESES: bool = False


settings = Settings()
