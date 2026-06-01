"""Runtime configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class Settings:
    """Immutable proxy settings."""

    base_url: str
    apikey: str
    version: str
    strip_trailing_year: bool
    merge_v1: bool
    enrich_titles: bool
    request_timeout: int
    log_level: str
    log_file: str
    host: str
    port: int

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            base_url=os.environ.get("JACRED_BASE_URL", "http://127.0.0.1:9117"),
            apikey=os.environ.get("JACRED_APIKEY", ""),
            version="1.0.0",
            strip_trailing_year=_env_bool("JACRED_STRIP_YEAR", "false"),
            merge_v1=_env_bool("JACRED_MERGE_V1", "true"),
            enrich_titles=_env_bool("JACRED_ENRICH_TITLES", "true"),
            request_timeout=int(os.environ.get("JACRED_TIMEOUT", "20")),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            log_file=os.environ.get("LOG_FILE", "/tmp/jacred_proxy.log"),
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", "5002")),
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return active settings (lazy-load from env on first access)."""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def init_settings(settings: Settings) -> None:
    """Bind settings for the process (called from ``create_app``)."""
    global _settings
    _settings = settings
