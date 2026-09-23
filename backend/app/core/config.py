from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    #: Comma-separated. Kept as a string because pydantic-settings would try to
    #: JSON-decode a list-typed field coming from the environment.
    cors_origins: str = ""

    auth_mode: Literal["dev", "max"] = "dev"
    dev_user_id: int = 1

    postgres_user: str = "trip"
    postgres_password: str = "trip"
    postgres_db: str = "trip"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    redis_url: str = "redis://redis:6379/0"

    gigachat_auth_key: str = ""
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat"
    gigachat_verify_ssl: bool = True

    #: Internal Docker DNS by default; override for local runs outside compose.
    searxng_url: str = "http://searxng:8080"
    #: When false, trip generation skips live web search (DB memory still used).
    searxng_enabled: bool = True

    opentripmap_api_key: str = ""
    opentripmap_lang: str = "ru"
    opentripmap_daily_limit: int = 1000
    #: Seconds between OpenTripMap requests. The free tier answers 429 to a
    #: burst of detail lookups; set to 0 in tests.
    opentripmap_min_interval: float = 0.12

    #: openrouteservice. Free tier: 2000 directions/day, 40/min. Preferred over
    #: the public OSRM demo servers, which carry no availability promise.
    ors_api_key: str = ""
    #: Stay under the 40/min ceiling; ORS answers 429 the moment a burst lands.
    ors_min_interval: float = 1.6

    #: Enrichment sources. Both are free and keyless, so they are on by default
    #: and can be switched off if an upstream starts misbehaving mid-demo.
    kudago_enabled: bool = True
    weather_enabled: bool = True

    max_bot_enabled: bool = False
    max_bot_token: str = ""
    max_bot_webhook_secret: str = ""
    #: Public HTTPS URL of POST /api/v1/bot/webhook. Required for webhook mode.
    max_bot_webhook_url: str = ""
    #: auto — webhook if URL set, otherwise long polling; webhook | polling | off.
    max_bot_mode: Literal["auto", "webhook", "polling", "off"] = "auto"
    max_webapp_url: str = "https://2-rist.ru"

    #: Fixed-window request limit for /api/v1. Fails open when Redis is down.
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = 60
    rate_limit_max_requests: int = 120
    #: Stricter buckets for expensive endpoints.
    rate_limit_trip_max: int = 10
    rate_limit_geo_max: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def gigachat_configured(self) -> bool:
        return bool(self.gigachat_auth_key)

    @property
    def opentripmap_configured(self) -> bool:
        return bool(self.opentripmap_api_key)

    @property
    def ors_configured(self) -> bool:
        return bool(self.ors_api_key)

    @property
    def max_bot_configured(self) -> bool:
        return bool(self.max_bot_token)

    @property
    def max_bot_active(self) -> bool:
        return self.max_bot_enabled and self.max_bot_configured



@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
