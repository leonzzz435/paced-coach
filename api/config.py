from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_async_database_url(value: str) -> str:
    """Normalize sync Postgres URLs for SQLAlchemy's async engine.

    Managed Postgres providers often expose `postgresql://...` connection strings.
    """
    s = (value or "").strip()
    if not s:
        return s
    if s.startswith("postgresql+asyncpg://"):
        return s
    if s.startswith("postgresql://"):
        return "postgresql+asyncpg://" + s.removeprefix("postgresql://")
    if s.startswith("postgres://"):
        return "postgresql+asyncpg://" + s.removeprefix("postgres://")
    return s


def _is_loopback_host(raw_host: str | None) -> bool:
    host = (raw_host or "").strip().lower().strip("[]")
    if not host:
        return False
    return host in {"localhost", "127.0.0.1", "::1"}


def _url_host(raw_url: str | None) -> str:
    parsed = urlparse((raw_url or "").strip())
    return parsed.hostname or ""


class Settings(BaseSettings):
    app_name: str = "paced.coach API"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/paced_coach"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Encryption
    fernet_key: str = ""

    # Auth
    app_env: str = Field(default="local", validation_alias="APP_ENV")
    auth_mode: str = Field(default="local", validation_alias="AUTH_MODE")
    local_owner_user_id: str = Field(default="", validation_alias="LOCAL_OWNER_USER_ID")
    local_owner_email: str = Field(default="local-owner@paced.local", validation_alias="LOCAL_OWNER_EMAIL")
    local_owner_key: str = Field(default="local-owner", validation_alias="LOCAL_OWNER_KEY")
    allow_local_auth_public_access: bool = Field(default=False, validation_alias="ALLOW_LOCAL_AUTH_PUBLIC_ACCESS")
    allow_local_data_delete: bool = Field(default=False, validation_alias="ALLOW_LOCAL_DATA_DELETE")
    local_usage_safety_bypass: bool = Field(default=False, validation_alias="LOCAL_USAGE_SAFETY_BYPASS")

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Local usage limits
    local_usage_dev_bypass: bool = Field(default=False, validation_alias="LOCAL_USAGE_DEV_BYPASS")
    web_app_url: str = Field(default="http://localhost:3000", validation_alias="WEB_APP_URL")

    # Coach chat
    coach_thread_iteration_limit: int = Field(default=15, validation_alias="COACH_THREAD_ITERATION_LIMIT")

    # Whoop OAuth 2.0 (live)
    whoop_oauth_enabled: bool = False
    whoop_oauth_client_id: str = ""
    whoop_oauth_client_secret: str = ""
    # This should point to the web callback route (e.g. https://app.example.com/app/api/oauth/whoop/callback),
    # not the API callback URL, since the browser redirect will not include an Authorization header.
    whoop_oauth_redirect_uri: str = ""

    # Strava OAuth 2.0 (live)
    strava_oauth_enabled: bool = False
    strava_oauth_client_id: str = ""
    strava_oauth_client_secret: str = ""
    # This should point to the web callback route (e.g. https://app.example.com/app/api/oauth/strava/callback),
    # not the API callback URL, since the browser redirect will not include an Authorization header.
    strava_oauth_redirect_uri: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_prefix="")

    @field_validator("debug", mode="before")
    @classmethod
    def _coerce_debug(cls, value: object) -> object:
        # Some environments set DEBUG to non-boolean strings like "release".
        # Treat these as False instead of crashing at import time.
        if isinstance(value, str) and value.strip().lower() in {"release", "prod", "production", "staging"}:
            return False
        return value

    @field_validator("auth_mode", mode="before")
    @classmethod
    def _normalize_auth_mode(cls, value: object) -> str:
        normalized = str(value or "local").strip().lower()
        if normalized != "local":
            raise ValueError("AUTH_MODE must be 'local'. Hosted auth providers have been removed.")
        return normalized

    @field_validator("app_env", mode="before")
    @classmethod
    def _normalize_app_env(cls, value: object) -> str:
        normalized = str(value or "local").strip().lower()
        return normalized or "local"

    @property
    def local_auth_context_is_safe(self) -> bool:
        if self.allow_local_auth_public_access:
            return True
        if self.app_env in {"prod", "production", "staging", "preview"}:
            return False
        return _is_loopback_host(_url_host(self.web_app_url))

    @property
    def database_url_async(self) -> str:
        return _normalize_async_database_url(self.database_url)

    @field_validator("web_app_url", mode="before")
    @classmethod
    def _normalize_web_app_url(cls, value: object) -> str:
        normalized = str(value or "http://localhost:3000").strip().rstrip("/")
        return normalized or "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
