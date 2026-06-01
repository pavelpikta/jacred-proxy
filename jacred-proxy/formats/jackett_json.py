"""Jackett v2 JSON result mapping."""

from __future__ import annotations

from typing import Any

from jacred_proxy.constants import DEFAULT_TRACKER_NAME
from jacred_proxy.utils import safe_get, types_to_categories


def result_to_jackett_json(torrent: dict[str, Any]) -> dict[str, Any]:
    """One torrent as Jackett v2 ``Results[]`` element."""
    title = safe_get(torrent, "Title", "title", "name")
    info_obj = torrent.get("info") if isinstance(torrent.get("info"), dict) else {}
    return {
        "Tracker": safe_get(
            torrent,
            "Tracker",
            "TrackerId",
            "tracker",
            default=DEFAULT_TRACKER_NAME,
        ),
        "Details": safe_get(torrent, "Details", "url", default="") or None,
        "Title": title,
        "Size": int(safe_get(torrent, "Size", "size", default="0") or 0),
        "PublishDate": torrent.get("PublishDate") or torrent.get("createTime"),
        "Category": torrent.get("Category")
        or types_to_categories(info_obj.get("types") or torrent.get("types")),
        "CategoryDesc": torrent.get("CategoryDesc"),
        "Seeders": int(safe_get(torrent, "Seeders", "sid", default="0") or 0),
        "Peers": int(safe_get(torrent, "Peers", "pir", default="0") or 0),
        "MagnetUri": safe_get(torrent, "MagnetUri", "Magnet", "magnet", default=""),
        "languages": torrent.get("languages"),
        "info": info_obj or None,
    }
