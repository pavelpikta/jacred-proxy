"""Combined v2 + v1 search with card/fuzzy modes."""

from __future__ import annotations

from typing import Any

from jacred_proxy.backend.v1 import fetch_v1
from jacred_proxy.backend.v2 import fetch_v2, fetch_v2_card
from jacred_proxy.config import Settings, get_settings
from jacred_proxy.log import get_logger
from jacred_proxy.request_params import is_card_metadata_search
from jacred_proxy.utils import (
    merge_torrent_lists,
    split_bilingual_query,
    strip_trailing_year,
)

logger = get_logger()


def build_query_variants(
    query: str | None,
    title_ru: str | None = None,
    title_en: str | None = None,
    settings: Settings | None = None,
) -> list[str]:
    """Distinct query strings for cyrillic/latin fastdb keys."""
    settings = settings or get_settings()
    variants: list[str] = []
    if query:
        if settings.strip_trailing_year:
            stripped = strip_trailing_year(query, True)
            if stripped:
                variants.append(stripped)
            if query not in variants:
                variants.append(query)
        else:
            variants.append(query)
    for term in (title_ru, title_en):
        if term and term not in variants:
            variants.append(term)
    return variants


def v1_search_pairs(
    query: str | None,
    title_ru: str | None,
    title_en: str | None,
    settings: Settings | None = None,
) -> list[tuple[str, str | None]]:
    """(search, altname) pairs for v1 bilingual coverage."""
    settings = settings or get_settings()
    pairs: list[tuple[str, str | None]] = []
    seen: set[tuple[str, str]] = set()

    def add(search: str | None, altname: str | None = None) -> None:
        if not search:
            return
        key = (search, altname or "")
        if key in seen:
            return
        seen.add(key)
        pairs.append((search, altname))

    if title_ru and title_en:
        add(title_en, title_ru)
        add(title_ru, title_en)
    elif title_ru:
        add(title_ru, title_en)
    elif title_en:
        add(title_en, title_ru)

    for term in build_query_variants(query, title_ru, title_en, settings):
        add(term)
        if title_ru and title_ru not in term:
            add(term, title_ru)
        if title_en and title_en not in term:
            add(term, title_en)

    return pairs


def search_combined(
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
    merge_v1: bool | None = None,
    card_mode: bool | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Merge v2 + optional v1: card (one v2 call) or fuzzy (query variants); dedupe by infohash."""
    settings = settings or get_settings()
    merge_v1 = settings.merge_v1 if merge_v1 is None else merge_v1
    if card_mode is None:
        card_mode = is_card_metadata_search(
            title,
            title_original,
            is_serial if is_serial >= 0 else None,
            categories,
            genres,
        )

    title_ru = title
    title_en = title_original
    if not title_ru and not title_en:
        title_ru, title_en = split_bilingual_query(query)

    batches: list[list[dict[str, Any]]] = []

    if card_mode:
        batches.append(
            fetch_v2_card(
                apikey=apikey,
                query=query,
                title=title_ru,
                title_original=title_en or "",
                year=year,
                tracker=tracker,
                is_serial=is_serial,
                genres=genres,
                categories=categories,
                settings=settings,
            )
        )
    else:
        for term in build_query_variants(query, title_ru, title_en, settings):
            batches.append(
                fetch_v2(
                    apikey=apikey,
                    query=term,
                    tracker=tracker,
                    is_serial=is_serial,
                    label=f"v2-fuzzy:{term[:32]}",
                    settings=settings,
                )
            )

    if merge_v1:
        for search, altname in v1_search_pairs(query, title_ru, title_en, settings):
            batches.append(
                fetch_v1(
                    apikey=apikey,
                    search=search,
                    altname=altname,
                    exact=False,
                    settings=settings,
                )
            )

    merged = merge_torrent_lists(*batches)
    logger.info(
        "[BACKEND] combined %d unique (mode=%s v1=%s)",
        len(merged),
        "card" if card_mode else "fuzzy",
        merge_v1,
    )
    return merged
