"""Parse search parameters from Flask requests."""

from __future__ import annotations

from typing import Any

from flask import Request


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


def season_episode_from_request(req: Request) -> tuple[int | None, int | None]:
    """Read Torznab ``season`` and ``ep`` (``episode`` alias); ``ep=0`` → season-wide."""
    season_raw = req.args.get("season")
    ep_raw = req.args.get("ep")
    if ep_raw is None:
        ep_raw = req.args.get("episode")

    season: int | None = None
    episode: int | None = None

    if season_raw is not None and str(season_raw).strip() != "":
        try:
            season = int(season_raw)
        except (TypeError, ValueError):
            season = None

    if ep_raw is not None and str(ep_raw).strip() != "":
        try:
            ep_val = int(ep_raw)
            episode = None if ep_val == 0 else ep_val
        except (TypeError, ValueError):
            episode = None

    return season, episode


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
