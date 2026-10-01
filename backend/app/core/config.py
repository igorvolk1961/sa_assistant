"""Application configuration loaded from environment / .env."""

import secrets
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_SECRET = "change-me"
_DEFAULT_OWNER_PASSWORD = "admin12345"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "dev"
    secret_key: str = ""
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    database_url: str = "postgresql+asyncpg://sa:sa@localhost:5435/sa_assistant"

    # Reserved for M6/M7 (Redis: live STT sessions, pub/sub).
    redis_url: str = "redis://localhost:6380/0"

    # Reserved for S3/MinIO storage backend (currently using local_storage_path).
    s3_endpoint: str = "http://localhost:9005"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "sa-assistant"
    s3_region: str = "us-east-1"

    local_storage_path: str = "localdata"

    cors_origins: str = "http://localhost:5173"

    bootstrap_owner_login: str = "admin"
    bootstrap_owner_password: str = ""

    @model_validator(mode="after")
    def _secure_defaults(self) -> "Settings":
        if not self.secret_key or self.secret_key.startswith(_PLACEHOLDER_SECRET):
            if self.app_env == "production":
                raise ValueError("SECRET_KEY must be set in production")
            self.secret_key = secrets.token_urlsafe(32)
        if not self.bootstrap_owner_password or (
            self.bootstrap_owner_password == _DEFAULT_OWNER_PASSWORD
        ):
            if self.app_env == "production":
                raise ValueError("BOOTSTRAP_OWNER_PASSWORD must be set in production")
            self.bootstrap_owner_password = secrets.token_urlsafe(12)
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
