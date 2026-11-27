from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OVAS_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://ovas:ovas@localhost:5432/ovas"
    runtime_url: str = "http://localhost:8100"
    tts_url: str = "http://localhost:8002"
    stt_url: str = "http://localhost:8003"
    # Browser origins allowed to make state-changing requests (MVP FR-3).
    allowed_origins: list[str] = ["http://localhost:5173"]
    # Set true behind HTTPS so the session cookie is only sent over TLS.
    cookie_secure: bool = False
    session_idle_days: int = 14
    # Encrypts stored secrets (LLM API keys). Required before saving any secret.
    secret_key: str | None = None
    # Shared with the runtime: signs session tokens and guards /internal endpoints.
    internal_key: str = "dev-internal-key-change-me"
    # Where browsers reach the runtime (the web proxy forwards /rt to it).
    runtime_public_path: str = "/rt"
    # LLM used until the workspace owner configures one in Settings.
    default_llm_url: str = "http://localhost:11434/v1"
    default_llm_model: str = "qwen3.5:9b"
    default_llm_reasoning_effort: str | None = "none"


@lru_cache
def get_settings() -> Settings:
    return Settings()
