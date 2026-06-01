"""Post-search filters: year, limit/offset pagination."""

from __future__ import annotations

from typing import Any

from jacred_proxy.log import get_logger
from jacred_proxy.utils import safe_get

logger = get_logger()

DEFAULT_TORZNAB_LIMIT = 100
MAX_TORZNAB_LIMIT = 1000


def torrent_release_year(torrent: dict[str, Any]) -> int | None:
    """Release year from JacRed ``info.relased`` or v1 ``relased`` field."""
    info = torrent.get("info")
    if isinstance(info, dict):
        raw = info.get("relased")
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass
    raw = torrent.get("relased")
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    return None


def torrent_matches_year(torrent: dict[str, Any], year: int) -> bool:
    """Match Torznab ``year`` — movies ±1, serials same rule as JacRed card search."""
    rel = torrent_release_year(torrent)
    if rel is None:
        return True
    return rel == year or rel == (year - 1) or rel == (year + 1)


def filter_results_by_year(
    torrents: list[dict[str, Any]], year: int | None
) -> list[dict[str, Any]]:
    """Drop results outside requested release year (when ``year`` is set)."""
    if year is None or year <= 0:
        return torrents
    filtered = [t for t in torrents if torrent_matches_year(t, year)]
    if len(filtered) < len(torrents):
        logger.info(
            "[TORZNAB] year filter %s: %d -> %d",
            year,
            len(torrents),
            len(filtered),
        )
    return filtered


def paginate_results(
    torrents: list[dict[str, Any]],
    *,
    limit: int | None,
    offset: int | None,
    max_limit: int = MAX_TORZNAB_LIMIT,
) -> list[dict[str, Any]]:
    """Apply Torznab ``limit`` / ``offset`` when either is explicitly set."""
    off = max(0, offset or 0)
    if limit is None and off == 0:
        return torrents

    lim = DEFAULT_TORZNAB_LIMIT if limit is None else max(0, min(limit, max_limit))
    page = torrents[off : off + lim]
    if off > 0 or len(page) < len(torrents):
        logger.info(
            "[TORZNAB] pagination offset=%d limit=%d: %d -> %d",
            off,
            lim,
            len(torrents),
            len(page),
        )
    return page
