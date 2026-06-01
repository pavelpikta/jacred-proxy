"""Torznab season/episode filtering — JacRed ``info.seasons`` first, title regex fallback."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from jacred_proxy.log import get_logger
from jacred_proxy.utils import safe_get

logger = get_logger()

# S02E02, S2E2, s02.e02
SXXEXX_RE = re.compile(
    r"(?<![0-9])s(?P<season>\d{1,2})[\s._-]*e(?P<episode>\d{1,3})(?![0-9])",
    re.I,
)
# S02E01-10 season batch
SXXEXX_RANGE_RE = re.compile(
    r"(?<![0-9])s(?P<season>\d{1,2})[\s._-]*e(?P<ep_start>\d{1,3})\s*-\s*(?P<ep_end>\d{1,3})(?![0-9])",
    re.I,
)
# 2x02
NXNN_RE = re.compile(
    r"(?<![0-9])(?P<season>\d{1,2})x(?P<episode>\d{1,3})(?![0-9])",
    re.I,
)
# [S02] — common season-pack marker on RU trackers
BRACKET_SEASON_RE = re.compile(r"\[s(?P<season>\d{1,2})\]", re.I)
# Season 2 / Сезон 2
SEASON_WORD_RE = re.compile(r"(?:season|сезон)\s*(?P<season>\d{1,2})\b", re.I)
# S02 complete / S02 season pack (no episode digit after season)
SXX_PACK_RE = re.compile(
    r"(?<![0-9])s(?P<season>\d{1,2})(?!\d|\s*e)(?:\s|\.|\]|/|$|[\[(])",
    re.I,
)


@dataclass(frozen=True)
class ParsedRelease:
    """Season/episode info extracted from a release title."""

    season: int
    episode: int | None  # None = full-season pack or unknown episode
    is_season_pack: bool


def torrent_seasons_set(torrent: dict[str, Any]) -> set[int]:
    """Structured season numbers from JacRed v2 ``info.seasons`` or v1 ``seasons``."""
    seasons: set[int] = set()

    def add_values(raw: Any) -> None:
        if raw is None:
            return
        if isinstance(raw, (list, tuple, set)):
            for item in raw:
                try:
                    val = int(item)
                except (TypeError, ValueError):
                    continue
                if val > 0:
                    seasons.add(val)
        else:
            try:
                val = int(raw)
            except (TypeError, ValueError):
                return
            if val > 0:
                seasons.add(val)

    add_values(torrent.get("seasons"))
    info = torrent.get("info")
    if isinstance(info, dict):
        add_values(info.get("seasons"))

    return seasons


def parse_release_title(title: str) -> ParsedRelease | None:
    """Best-effort season/episode parse from a torrent release name."""
    if not title:
        return None

    match = SXXEXX_RANGE_RE.search(title)
    if match:
        return ParsedRelease(
            season=int(match.group("season")),
            episode=int(match.group("ep_start")),
            is_season_pack=True,
        )

    match = SXXEXX_RE.search(title)
    if match:
        return ParsedRelease(
            season=int(match.group("season")),
            episode=int(match.group("episode")),
            is_season_pack=False,
        )

    match = NXNN_RE.search(title)
    if match:
        return ParsedRelease(
            season=int(match.group("season")),
            episode=int(match.group("episode")),
            is_season_pack=False,
        )

    match = BRACKET_SEASON_RE.search(title)
    if match:
        return ParsedRelease(
            season=int(match.group("season")),
            episode=None,
            is_season_pack=True,
        )

    match = SEASON_WORD_RE.search(title)
    if match:
        return ParsedRelease(
            season=int(match.group("season")),
            episode=None,
            is_season_pack=True,
        )

    match = SXX_PACK_RE.search(title)
    if match:
        return ParsedRelease(
            season=int(match.group("season")),
            episode=None,
            is_season_pack=True,
        )

    return None


def _episode_in_range(title: str, season: int, episode: int) -> bool:
    """True when title contains SxxEyy-zz range covering *episode*."""
    for match in SXXEXX_RANGE_RE.finditer(title):
        if int(match.group("season")) != season:
            continue
        start = int(match.group("ep_start"))
        end = int(match.group("ep_end"))
        if start <= episode <= end:
            return True
    return False


def release_matches_season_episode(
    title: str,
    season: int,
    episode: int | None,
) -> bool:
    """Torznab-style match from release title text."""
    if episode is not None and _episode_in_range(title, season, episode):
        return True

    parsed = parse_release_title(title)
    if parsed is None:
        return False

    if parsed.season != season:
        return False

    if episode is None:
        return True

    if parsed.is_season_pack or parsed.episode is None:
        return True

    return parsed.episode == episode


def _title_candidates(torrent: dict[str, Any]) -> list[str]:
    """Primary title plus JacRed normalized names for regex fallback."""
    titles: list[str] = []
    primary = safe_get(torrent, "Title", "title", "name")
    if primary:
        titles.append(primary)
    info = torrent.get("info")
    if isinstance(info, dict):
        for key in ("name", "originalname"):
            alt = info.get(key)
            if alt and str(alt) not in titles:
                titles.append(str(alt))
    return titles


def torrent_matches_season_episode(
    torrent: dict[str, Any],
    season: int,
    episode: int | None,
) -> bool:
    """Match using JacRed ``seasons`` metadata when present, else title regex."""
    meta = torrent_seasons_set(torrent)

    if meta:
        if season not in meta:
            return False
        if episode is None:
            return True
        for title in _title_candidates(torrent):
            if release_matches_season_episode(title, season, episode):
                return True
        return False

    for title in _title_candidates(torrent):
        if release_matches_season_episode(title, season, episode):
            return True
    return False


def filter_results_by_season_episode(
    torrents: list[dict[str, Any]],
    season: int | None,
    episode: int | None,
) -> list[dict[str, Any]]:
    """Narrow results to Torznab ``season`` / ``ep`` when season is set (>0)."""
    if season is None or season <= 0:
        return torrents

    filtered = [
        t for t in torrents if torrent_matches_season_episode(t, season, episode)
    ]
    if len(filtered) < len(torrents):
        logger.info(
            "[TORZNAB] season/ep filter S%sE%s: %d -> %d",
            season,
            episode if episode is not None else "*",
            len(torrents),
            len(filtered),
        )
    return filtered
