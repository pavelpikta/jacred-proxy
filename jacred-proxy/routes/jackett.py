"""Jackett-compatible JSON API."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from jacred_proxy.backend.search import search_combined
from jacred_proxy.categories import filter_results_by_category
from jacred_proxy.config import get_settings
from jacred_proxy.formats.jackett_json import result_to_jackett_json
from jacred_proxy.log import get_logger
from jacred_proxy.request_params import categories_from_request, is_card_metadata_search

bp = Blueprint("jackett", __name__)
logger = get_logger()


@bp.route("/api/v2.0/indexers", methods=["GET"])
def jackett_indexers_list():
    """Jackett admin API: list of indexers (single aggregate entry)."""
    settings = get_settings()
    return jsonify(
        [
            {
                "id": "all",
                "name": "JacRed (all trackers)",
                "description": "JacRed torrent aggregator via jacred-proxy",
                "type": "public",
                "configured": True,
                "site_link": settings.base_url,
                "language": "ru-RU",
            }
        ]
    )


@bp.route("/api/v1/indexer", methods=["GET"])
def prowlarr_indexers_stub():
    """Minimal stub for clients that probe Prowlarr-style indexer list."""
    return jsonify(
        [
            {
                "id": 1,
                "name": "JacRed (all)",
                "enable": True,
                "protocol": "torrent",
                "supportsSearch": True,
            }
        ]
    )


@bp.route("/api/v2.0/indexers/<status>/results", methods=["GET"])
def jackett_results(status: str):
    """Jackett v2 JSON search (``Results`` array); main client entry point."""
    settings = get_settings()
    query = (
        request.args.get("Query") or request.args.get("q") or request.args.get("query")
    )
    title = request.args.get("title")
    title_original = request.args.get("title_original")
    year = request.args.get("year", type=int)
    apikey = request.args.get("apikey")
    tracker = request.args.get("Tracker") or request.args.get("tracker")

    if not query and not title and not title_original:
        logger.warning("[JACKETT] called without query/title")
        return jsonify({"Results": []})

    is_serial = -1
    if request.args.get("is_serial") is not None:
        try:
            is_serial = int(request.args.get("is_serial"))
        except (TypeError, ValueError):
            pass

    genres = request.args.get("genres")
    categories = categories_from_request(request)
    card_mode = is_card_metadata_search(
        title,
        title_original,
        is_serial if request.args.get("is_serial") is not None else None,
        categories,
        genres,
    )

    logger.info(
        "[JACKETT] mode=%s q=%r title=%r orig=%r year=%s is_serial=%s categories=%s",
        "card" if card_mode else "fuzzy",
        query,
        title,
        title_original,
        year,
        is_serial,
        categories,
    )
    torrents = search_combined(
        apikey=apikey,
        query=query,
        title=title,
        title_original=title_original,
        year=year,
        tracker=tracker,
        is_serial=is_serial,
        genres=genres,
        categories=categories,
        card_mode=card_mode,
        settings=settings,
    )
    cat_param = request.args.get("cat") or request.args.get("Category")
    if cat_param and not card_mode:
        torrents = filter_results_by_category(torrents, cat_param)

    results = [result_to_jackett_json(t) for t in torrents]
    logger.info("[JACKETT] returning %d results", len(results))
    return jsonify({"Results": results})
