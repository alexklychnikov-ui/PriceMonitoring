from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", enable_decoding=False)

    DATABASE_URL: str
    REDIS_URL: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str
    TELEGRAM_CHANNEL_ID: str = ""
    FLOWER_USER: str = "admin"
    FLOWER_PASSWORD: str = ""
    DOMAIN_NAME: str = ""
    PUBLIC_SITE_URL: str = ""
    CORS_ORIGINS: str = "http://localhost:5173"
    TELEGRAM_BOT_USERNAME: str = ""
    SUBSCRIPTION_WEB_KEY: str = ""
    PROXY_LIST: list[str] = Field(default_factory=list)
    PARSE_INTERVAL_HOURS: int = 6
    PRICE_ALERT_THRESHOLD_PCT: float = 5.0
    PRUNE_PRODUCTS_INACTIVE_DAYS: int = 90
    LLM_PROVIDER: str = "openai"
    PROXY_API_KEY: str
    PROXY_BASE_URL: str = "https://openai.api.proxyapi.ru/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    @field_validator("PROXY_LIST", mode="before")
    @classmethod
    def split_proxy_list(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [item.strip() for item in value if item and item.strip()]
        return [item.strip() for item in value.split(",") if item and item.strip()]


settings = Settings()
