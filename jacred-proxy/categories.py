"""Torznab category parsing and post-filtering."""

from __future__ import annotations

from typing import Any

from jacred_proxy.log import get_logger
from jacred_proxy.utils import types_to_categories

logger = get_logger()


def normalize_category_id(value: Any) -> int | None:
    """Parse Torznab category id from string or list."""
    if isinstance(value, list):
        value = value[0] if value else ""
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1].strip()
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_torznab_categories(cat_param: str | None) -> set[int]:
    """Parse comma-separated Torznab ``cat`` into a set of ints."""
    cats: set[int] = set()
    if not cat_param:
        return cats
    for part in str(cat_param).split(","):
        cid = normalize_category_id(part.strip())
        if cid is not None:
            cats.add(cid)
    return cats


def is_serial_from_search(t: str | None, cat_param: str | None) -> int:
    """Map Torznab ``t`` to ``is_serial`` (moviesearch/tvsearch only; else -1 = wide)."""
    if t == "moviesearch":
        return 1
    if t == "tvsearch":
        return 2
    return -1


def torrent_matches_torznab_categories(
    torrent: dict[str, Any], wanted_cats: set[int]
) -> bool:
    """True if torrent Torznab categories overlap requested ``cat`` filter."""
    if not wanted_cats:
        return True

    has_movie = any(2000 <= c < 3000 for c in wanted_cats)
    has_tv = any(5000 <= c < 6000 for c in wanted_cats)
    if has_movie and has_tv:
        return True

    raw = torrent.get("Category") or torrent.get("category") or []
    if not isinstance(raw, list):
        raw = [raw]
    item_cats: list[int] = []
    for cat in raw:
        try:
            item_cats.append(int(cat))
        except (TypeError, ValueError):
            pass
    if not item_cats:
        return True

    for wanted in wanted_cats:
        base = (wanted // 1000) * 1000
        if any(base <= c < base + 1000 for c in item_cats):
            return True
    return False


def filter_results_by_category(
    torrents: list[dict[str, Any]], cat_param: str | None
) -> list[dict[str, Any]]:
    """Narrow merged results to Torznab category (skipped when both movie+tv requested)."""
    wanted = parse_torznab_categories(cat_param)
    if not wanted:
        return torrents
    filtered = [t for t in torrents if torrent_matches_torznab_categories(t, wanted)]
    if len(filtered) < len(torrents):
        logger.info(
            "[TORZNAB] category filter %s: %d -> %d",
            sorted(wanted),
            len(torrents),
            len(filtered),
        )
    return filtered


def category_params_from_list(category_value: Any) -> dict[str, str]:
    """Build ``Category[n]=id`` query keys for card-style requests."""
    if not category_value:
        return {}
    if isinstance(category_value, (list, tuple)):
        parts = [str(c).strip() for c in category_value if str(c).strip()]
    else:
        parts = [p.strip() for p in str(category_value).split(",") if p.strip()]
    return {f"Category[{i}]": part for i, part in enumerate(parts)}


def v1_item_to_result(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize v1 torrent dict to Jackett v2 ``Result`` fields."""
    return {
        "Tracker": item.get("tracker") or item.get("trackerName"),
        "Title": item.get("title"),
        "Size": int(item.get("size") or 0),
        "Seeders": int(item.get("sid") or 0),
        "Peers": int(item.get("pir") or 0),
        "MagnetUri": item.get("magnet"),
        "Details": item.get("url"),
        "Category": types_to_categories(item.get("types")),
        "info": {
            "name": item.get("name"),
            "originalname": item.get("originalname"),
            "voices": item.get("voices"),
            "types": item.get("types"),
            "seasons": item.get("seasons"),
            "relased": item.get("relased"),
        },
    }
