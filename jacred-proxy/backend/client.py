"""HTTP client for the torrent aggregator backend."""

from __future__ import annotations

from typing import Any

import requests

from jacred_proxy.config import Settings, get_settings
from jacred_proxy.log import get_logger

logger = get_logger()


def api_params(
    apikey: str | None = None, settings: Settings | None = None
) -> dict[str, str]:
    """Common query params including optional apikey."""
    settings = settings or get_settings()
    params: dict[str, str] = {}
    key = apikey or settings.apikey
    if key:
        params["apikey"] = key
    return params


def get_json(
    path: str,
    params: dict[str, Any],
    label: str,
    settings: Settings | None = None,
) -> Any | None:
    """GET backend JSON; log errors and return ``None`` on failure."""
    settings = settings or get_settings()
    url = f"{settings.base_url}{path}"
    log_params = {k: ("***" if k == "apikey" else v) for k, v in params.items()}
    logger.info("[BACKEND] %s: %s", label, url)
    logger.debug("[BACKEND] params: %s", log_params)
    try:
        resp = requests.get(url, params=params, timeout=settings.request_timeout)
        resp.raise_for_status()
        logger.info("[BACKEND] %s OK %d bytes", label, len(resp.content))
        return resp.json()
    except requests.exceptions.Timeout:
        logger.error("[BACKEND] %s timeout (%ds)", label, settings.request_timeout)
    except requests.exceptions.HTTPError as exc:
        status = getattr(exc.response, "status_code", "?")
        logger.error("[BACKEND] %s HTTP %s: %s", label, status, exc)
    except Exception as exc:
        logger.exception("[BACKEND] %s error: %s", label, exc)
    return None
