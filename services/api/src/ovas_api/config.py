from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OVAS_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://ovas:ovas@localhost:5432/ovas"
    runtime_url: str = "http://localhost:8100"
    tts_url: str = "http://localhost:8002"
    # Browser origins allowed to make state-changing requests (MVP FR-3).
    allowed_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
