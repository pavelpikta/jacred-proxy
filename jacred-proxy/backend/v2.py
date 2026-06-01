"""Jackett v2 API."""

from __future__ import annotations

from typing import Any

from jacred_proxy.backend.client import api_params, get_json
from jacred_proxy.categories import category_params_from_list
from jacred_proxy.config import Settings, get_settings
from jacred_proxy.log import get_logger

logger = get_logger()


def parse_v2_results(data: Any) -> list[dict[str, Any]]:
    """Extract ``Results`` list from Jackett v2 JSON."""
    if isinstance(data, dict) and "Results" in data:
        return data["Results"]
    if isinstance(data, list):
        return data
    return []


def fetch_v2(
    *,
    apikey: str | None = None,
    query: str | None = None,
    title: str | None = None,
    title_original: str | None = None,
    year: int | None = None,
    tracker: str | None = None,
    is_serial: int = -1,
    genres: str | None = None,
    categories: list[str] | None = None,
    label: str = "v2",
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Jackett v2 ``/api/v2.0/indexers/all/results`` (Query and/or title metadata)."""
    settings = settings or get_settings()
    params: dict[str, Any] = api_params(apikey, settings)
    if tracker:
        params["Tracker"] = tracker
    if query:
        params["query"] = query
        params["Query"] = query
    if title:
        params["title"] = title
    if title_original is not None:
        params["title_original"] = title_original
    if year is not None and year > 0:
        params["year"] = year
    if genres:
        params["genres"] = genres
    params.update(category_params_from_list(categories))
    if is_serial >= 0:
        params["is_serial"] = is_serial

    if not params.get("query") and not params.get("Query") and "title" not in params:
        return []

    data = get_json("/api/v2.0/indexers/all/results", params, label, settings)
    results = parse_v2_results(data)
    logger.info("[BACKEND] %s -> %d items", label, len(results))
    return results


def fetch_v2_card(**kwargs: Any) -> list[dict[str, Any]]:
    """One v2 request with Query plus title/year/category params."""
    return fetch_v2(label="v2-card", **kwargs)
