"""Legacy v1 torrent API."""

from __future__ import annotations

from jacred_proxy.backend.client import api_params, get_json
from jacred_proxy.categories import v1_item_to_result
from jacred_proxy.config import Settings, get_settings
from jacred_proxy.log import get_logger

logger = get_logger()


def fetch_v1(
    *,
    apikey: str | None = None,
    search: str | None = None,
    altname: str | None = None,
    exact: bool = False,
    season: int | None = None,
    settings: Settings | None = None,
) -> list[dict]:
    """v1 ``/api/v1.0/torrents`` — broader DB key scan; fuzzy unless ``exact``."""
    if not search:
        return []
    settings = settings or get_settings()
    params = api_params(apikey, settings)
    params["search"] = search
    if altname:
        params["altname"] = altname
    if exact:
        params["exact"] = "true"
    if season is not None and season > 0:
        params["season"] = str(season)

    data = get_json("/api/v1.0/torrents", params, "v1", settings)
    if not isinstance(data, dict):
        return []
    results = [v1_item_to_result(v) for v in data.values() if isinstance(v, dict)]
    logger.info("[BACKEND] v1 -> %d items", len(results))
    return results
