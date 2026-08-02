"""
Central configuration for CB Nest + PeopleOps Copilot.

All secrets and environment-specific values are read from environment
variables so nothing sensitive is committed to the repo.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "CB Nest PeopleOps Copilot"
    ENV: str = "development"

    # --- Auth ---
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./cb_nest.db"

    # --- AI / LLM provider ---
    # If ANTHROPIC_API_KEY is unset, the AI services fall back to
    # deterministic, rule-based behavior so the app is fully runnable
    # and testable without any external API key.
    ANTHROPIC_API_KEY: str | None = None
    LLM_MODEL: str = "claude-sonnet-4-6"

    # --- SQL Agent safety ---
    SQL_AGENT_MAX_ROWS: int = 200

    # --- Internal API base URL used by the action agent's tool calls.
    # Overridden in tests to point at a throwaway test server instead
    # of whatever's running on localhost:8000.
    API_TOOLS_BASE_URL: str = "http://localhost:8000"

    # --- Deployment ---
    # The deployed frontend's exact origin (e.g. "https://cb-nest.vercel.app"),
    # in addition to the localhost regex used for local dev. Unset by
    # default so local dev is unaffected; set this in production.
    FRONTEND_ORIGIN: str | None = None

    # --- Policy RAG ---
    POLICY_TOP_K: int = 3
    POLICY_MIN_SIMILARITY: float = 0.12  # below this -> "insufficient context"


@lru_cache
def get_settings() -> Settings:
    return Settings()
