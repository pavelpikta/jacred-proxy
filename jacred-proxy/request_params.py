"""Parse search parameters from Flask requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import Request

from jacred_proxy.log import get_logger

logger = get_logger()


def categories_from_request(req: Request) -> list[str] | None:
    """Read ``Category[]`` or ``cat`` from query args."""
    cats = req.args.getlist("Category[]")
    if not cats:
        for key, val in req.args.items():
            if key.startswith("Category[") and val:
                cats.append(val)
    if cats:
        return cats
    raw = req.args.get("cat") or req.args.get("Category")
    if raw:
        return [p.strip() for p in str(raw).split(",") if p.strip()]
    return None


def _optional_int(raw: str | None) -> int | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def season_episode_from_request(req: Request) -> tuple[int | None, int | None]:
    """Read Torznab ``season`` / ``ep``; ``0`` disables that filter (AIOStreams default)."""
    season = _optional_int(req.args.get("season"))
    ep_raw = req.args.get("ep")
    if ep_raw is None:
        ep_raw = req.args.get("episode")
    episode = _optional_int(ep_raw)

    if season is not None and season <= 0:
        season = None
    if episode is not None and episode <= 0:
        episode = None

    return season, episode


def limit_offset_from_request(req: Request) -> tuple[int | None, int | None]:
    """Torznab ``limit`` and ``offset`` (pagination)."""
    limit = _optional_int(req.args.get("limit"))
    offset = _optional_int(req.args.get("offset"))
    if offset is not None and offset < 0:
        offset = 0
    if limit is not None and limit <= 0:
        limit = None
    return limit, offset


def year_from_request(req: Request) -> int | None:
    """Torznab ``year`` advanced param (movies / optional TV narrowing)."""
    year = _optional_int(req.args.get("year"))
    if year is not None and year <= 0:
        return None
    return year


def normalize_imdb_id(raw: str) -> str | None:
    """Normalize to JacRed v1 ``tt…`` / ``kp…`` search token."""
    value = raw.strip()
    if not value:
        return None
    if value.startswith(("tt", "kp")):
        return value
    if value.isdigit():
        return f"tt{value}"
    return value


def resolve_torznab_query(req: Request) -> str | None:
    """Build backend search string from ``q``, ``Query``, or ``imdbid`` (JacRed resolves tt/kp)."""
    query = req.args.get("q") or req.args.get("Query")
    if query and str(query).strip():
        return str(query).strip()

    imdbid = req.args.get("imdbid")
    if imdbid:
        normalized = normalize_imdb_id(str(imdbid))
        if normalized:
            logger.info("[TORZNAB] resolved imdbid=%r -> q=%r", imdbid, normalized)
            return normalized

    return None


@dataclass(frozen=True)
class TorznabSearchParams:
    """Parsed Torznab search query parameters (excluding ``t``, ``cat``, ``apikey``)."""

    query: str | None
    season: int | None
    episode: int | None
    year: int | None
    limit: int | None
    offset: int | None
    tvdbid: int | None
    imdbid: str | None
    tvdbid_only: bool


def torznab_search_params_from_request(req: Request) -> TorznabSearchParams:
    """Parse Torznab client params used by Sonarr/Radarr/AIOStreams/qBittorrent."""
    season, episode = season_episode_from_request(req)
    limit, offset = limit_offset_from_request(req)
    year = year_from_request(req)
    query = resolve_torznab_query(req)

    imdbid_raw = req.args.get("imdbid")
    imdbid = normalize_imdb_id(str(imdbid_raw)) if imdbid_raw else None
    tvdbid = _optional_int(req.args.get("tvdbid") or req.args.get("rid"))

    has_q_like = bool(query)
    tvdbid_only = bool(tvdbid and not has_q_like)

    if tvdbid_only:
        logger.warning(
            "[TORZNAB] tvdbid=%s without q/imdbid — JacRed has no TVDB lookup; empty result",
            tvdbid,
        )

    return TorznabSearchParams(
        query=query,
        season=season,
        episode=episode,
        year=year,
        limit=limit,
        offset=offset,
        tvdbid=tvdbid,
        imdbid=imdbid,
        tvdbid_only=tvdbid_only,
    )


def is_card_metadata_search(
    title: str | None,
    title_original: str | None,
    is_serial: int | None,
    categories: list[str] | None,
    genres: str | None,
) -> bool:
    """True when request carries title/year/category (not free-text-only)."""
    if title is not None or title_original is not None:
        return True
    if is_serial is not None and is_serial >= 0:
        return True
    if categories or genres:
        return True
    return False
