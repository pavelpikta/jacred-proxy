"""Small pure helpers (dict access, text, torrent keys)."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from jacred_proxy.constants import TYPE_TO_CATEGORY

CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
LATIN_RE = re.compile(r"[a-zA-Z]")


def safe_get(obj: dict[str, Any], *keys: str, default: str = "") -> str:
    """First non-empty value among keys in dict *obj*."""
    for key in keys:
        value = obj.get(key)
        if value:
            return str(value)
    return default


def strip_trailing_year(query: str | None, enabled: bool) -> str | None:
    """Remove trailing ``(19|20)xx`` from free-text query when enabled."""
    if not query or not enabled:
        return query
    cleaned = re.sub(r"\s*\b(19|20)\d{2}\b\s*$", "", query).strip()
    return cleaned or query


def has_cyrillic(text: str | None) -> bool:
    """True if text contains Cyrillic letters."""
    return bool(text and CYRILLIC_RE.search(text))


def has_latin(text: str | None) -> bool:
    """True if text contains Latin letters."""
    return bool(text and LATIN_RE.search(text))


def split_bilingual_query(query: str | None) -> tuple[str | None, str | None]:
    """Split ``local / original`` title into (cyrillic, latin) when detectable."""
    if not query:
        return None, None
    q = query.strip()
    if " / " not in q:
        return None, None
    left, right = q.split(" / ", 1)
    left, right = left.strip(), right.strip()
    if has_cyrillic(left) and has_latin(right):
        return left, right
    if has_latin(left) and has_cyrillic(right):
        return right, left
    return left, right


def infohash_from_torrent(torrent: dict[str, Any]) -> str | None:
    """Extract 40-char hex hash from fields or magnet URI."""
    ih = safe_get(torrent, "InfoHash", "Hash", default="")
    if ih:
        return ih.lower().strip()[:40]
    magnet = safe_get(
        torrent, "MagnetUri", "Magnet", "magnet", "Link", "link", default=""
    )
    match = re.search(r"btih:([a-fA-F0-9]{40})", magnet, re.I)
    return match.group(1).lower() if match else None


def torrent_dedupe_key(torrent: dict[str, Any]) -> str:
    """Stable dedupe key: infohash or hash(title|magnet)."""
    ih = infohash_from_torrent(torrent)
    if ih:
        return f"h:{ih}"
    title = safe_get(torrent, "Title", "title", "name")
    magnet = safe_get(torrent, "MagnetUri", "Magnet", "magnet", default="")
    return "x:" + hashlib.md5(f"{title}|{magnet}".encode()).hexdigest()


def merge_torrent_lists(*batches: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Merge result lists, drop duplicates by infohash."""
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for batch in batches:
        if not batch:
            continue
        for torrent in batch:
            key = torrent_dedupe_key(torrent)
            if key in seen:
                continue
            seen.add(key)
            merged.append(torrent)
    return merged


def types_to_categories(types: Any) -> list[int]:
    """Map internal type tags to Torznab category ids."""
    if not types:
        return []
    if isinstance(types, str):
        types = [types]
    cats: list[int] = []
    for tag in types:
        cid = TYPE_TO_CATEGORY.get(tag)
        if cid and cid not in cats:
            cats.append(cid)
    return cats or [2000]
