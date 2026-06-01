"""Torznab RSS/XML builders."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any
from xml.sax.saxutils import escape

from flask import request

from jacred_proxy.config import Settings, get_settings
from jacred_proxy.utils import has_cyrillic, has_latin, safe_get


def proxy_base_url() -> str:
    """Public base URL of this proxy (for caps XML)."""
    return request.url_root.rstrip("/")


def wrap_in_xml(items_xml: str) -> str:
    """Wrap Torznab ``<item>`` block in RSS channel XML."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
    <channel>
        <title>JacRed Proxy</title>
        <description>Torznab wrapper</description>
        <link>http://localhost:5002/</link>
        <language>en-us</language>
        <category>search</category>
        {items_xml}
    </channel>
</rss>"""


def get_caps_xml() -> str:
    """Torznab capabilities document."""
    base = proxy_base_url()
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<caps>
  <server version="1.0" title="JacRed Proxy" strapline="Torznab wrapper for JacRed" email="info@localhost" url="{escape(base)}/api/v2.0/indexers/all/results/torznab/api"/>
  <limits max="1000" default="100"/>
  <searching>
    <search available="yes" supportedParams="q,imdbid"/>
    <tv-search available="yes" supportedParams="q,imdbid,tvdbid,season,ep"/>
    <movie-search available="yes" supportedParams="q,imdbid"/>
  </searching>
  <categories>
    <category id="2000" name="Movies"/>
    <category id="5000" name="TV"/>
    <category id="5070" name="TV/Anime"/>
  </categories>
</caps>'''


def get_indexers_xml() -> str:
    """Torznab ``t=indexers`` XML (single aggregate indexer)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<indexers>
  <indexer id="all" configured="true">
    <title>JacRed (all trackers)</title>
    <description>Aggregated JacRed search across all configured trackers</description>
    <link>https://github.com/jacred-fdb/jacred</link>
    <language>ru-RU</language>
    <type>public</type>
  </indexer>
</indexers>"""


def _resolve_item_category(
    torrent: dict[str, Any], assigned_cat: str, cat_param: str | None
) -> str:
    """Pick Torznab category id for one RSS item."""
    if assigned_cat:
        return assigned_cat
    cats = torrent.get("Category") or torrent.get("category")
    if isinstance(cats, list) and cats:
        return str(cats[0])
    if isinstance(cats, (int, str)) and cats:
        return str(cats)
    if cat_param:
        first = str(cat_param).split(",")[0].strip()
        if first:
            return first
    return "2000"


def _torrent_languages(torrent: dict[str, Any]) -> list[str]:
    """Language tags from result payload, if any."""
    langs = torrent.get("languages")
    if isinstance(langs, list):
        return [str(x).lower() for x in langs if x]
    return []


def _language_attrs(torrent: dict[str, Any], title: str) -> tuple[str, str]:
    """Torznab ``language`` / ``lang`` attribute values for one item."""
    langs = _torrent_languages(torrent)
    if "rus" in langs or has_cyrillic(title):
        return "ru-RU", "ru"
    if "eng" in langs or (has_latin(title) and not has_cyrillic(title)):
        return "en-US", "en"
    return "ru-RU", "ru"


def torrent_to_xml_item(
    torrent: dict[str, Any],
    assigned_cat: str,
    cat_param: str | None = None,
    settings: Settings | None = None,
) -> str:
    """Build one Torznab RSS ``<item>`` from a normalized result dict."""
    settings = settings or get_settings()
    title = safe_get(torrent, "Title", "title", "name", default="Unknown")

    voices_list: list[str] = []
    info_obj = torrent.get("info")
    if isinstance(info_obj, dict):
        voices = info_obj.get("voices")
        if isinstance(voices, list):
            voices_list = [str(v) for v in voices if v]
    if not voices_list and isinstance(torrent.get("voices"), list):
        voices_list = [str(v) for v in torrent["voices"] if v]

    if settings.enrich_titles:
        if voices_list:
            voices_str = " ".join(voices_list)
            display_title = f"{title} | [{voices_str}].rus"
        else:
            display_title = f"{title} | [].rus"
    else:
        display_title = title

    lang_tag, lang_code = _language_attrs(torrent, title)

    magnet_url = safe_get(torrent, "MagnetUri", "Magnet", "Link", default="")
    if not magnet_url:
        magnet_url = safe_get(torrent, "Details", default="")
    size = int(safe_get(torrent, "Size", default="0") or 0)
    indexer_name = safe_get(
        torrent, "Tracker", "TrackerId", "Indexer", default="JacRed"
    )
    seeders = int(safe_get(torrent, "Seeders", default="0") or 0)
    leechers = int(safe_get(torrent, "Peers", "Leechers", default="0") or 0)
    peers_total = seeders + leechers if leechers else seeders
    item_cat = _resolve_item_category(torrent, assigned_cat, cat_param)

    infohash = safe_get(torrent, "InfoHash", "Hash")
    if not infohash and "btih:" in magnet_url:
        match = re.search(r"btih:([a-fA-F0-9]+)", magnet_url)
        if match:
            infohash = match.group(1)

    safe_title = escape(str(display_title))
    safe_link = escape(str(magnet_url))
    safe_indexer = escape(str(indexer_name))

    return f'''
    <item>
        <title>{safe_title}</title>
        <guid isPermaLink="false">{infohash or hashlib.md5(safe_title.encode()).hexdigest()}</guid>
        <link>{safe_link}</link>
        <pubDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>
        <size>{size}</size>
        <enclosure url="{safe_link}" length="{size}" type="application/x-bittorrent" />
        
        <category>{item_cat}</category>
        <indexer id="{safe_indexer}">{safe_indexer}</indexer>
        <jackettindexer id="{safe_indexer}">{safe_indexer}</jackettindexer>
        
        <torznab:attr name="magneturl" value="{safe_link}" />
        <torznab:attr name="infohash" value="{infohash.upper() if infohash else ""}" />
        <torznab:attr name="seeders" value="{seeders}" />
        <torznab:attr name="peers" value="{peers_total}" />
        <torznab:attr name="site" value="{safe_indexer}" />
        <torznab:attr name="category" value="{item_cat}" />
        
        <torznab:attr name="language" value="{lang_tag}" />
        <torznab:attr name="lang" value="{lang_code}" />
    </item>'''
