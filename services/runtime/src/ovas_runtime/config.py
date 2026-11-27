from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OVAS_", env_file=".env", extra="ignore")

    api_url: str = "http://localhost:8000"
    internal_key: str = "dev-internal-key-change-me"


@lru_cache
def get_settings() -> Settings:
    return Settings()
