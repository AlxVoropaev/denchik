from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "denchik"
    database_url: str = "sqlite+aiosqlite:///./data/denchik.db"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    cookie_name: str = "denchik_session"
    cookie_secure: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]
    attachments_dir: str = "./data/attachments"
    max_attachment_bytes: int = 10 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
