"""Torznab RSS endpoints."""

from __future__ import annotations

from flask import Blueprint, Response, request

from jacred_proxy.backend.search import search_combined
from jacred_proxy.categories import filter_results_by_category, is_serial_from_search
from jacred_proxy.season_filter import filter_results_by_season_episode
from jacred_proxy.config import get_settings
from jacred_proxy.formats.torznab_xml import (
    get_caps_xml,
    get_indexers_xml,
    torrent_to_xml_item,
    wrap_in_xml,
)
from jacred_proxy.log import get_logger
from jacred_proxy.request_params import (
    categories_from_request,
    is_card_metadata_search,
    season_episode_from_request,
)

bp = Blueprint("torznab", __name__)
logger = get_logger()


def handle_torznab_request(indexer_id: str = "all") -> Response:
    """Torznab handler: caps, indexers list, or search → RSS XML."""
    settings = get_settings()
    t = request.args.get("t")
    apikey = request.args.get("apikey")
    cat_param = request.args.get("cat", "")

    logger.info(
        "[TORZNAB] indexer=%s t=%s apikey=%s path=%s",
        indexer_id,
        t,
        "yes" if apikey else "no",
        request.path,
    )
    logger.debug("[TORZNAB] args: %s", request.args.to_dict())

    if t == "caps":
        logger.info("Returning capabilities")
        return Response(get_caps_xml(), mimetype="application/xml")

    if t == "indexers":
        configured = request.args.get("configured", "").lower()
        if configured in ("", "true"):
            logger.info("Returning indexer list (configured)")
            return Response(get_indexers_xml(), mimetype="application/xml")
        logger.info("Returning empty indexer list (configured=false)")
        return Response(
            '<?xml version="1.0" encoding="UTF-8"?><indexers></indexers>',
            mimetype="application/xml",
        )

    assigned_cat = ""
    if t == "tvsearch":
        assigned_cat = "5000"
    elif t == "moviesearch":
        assigned_cat = "2000"
    elif cat_param:
        assigned_cat = str(cat_param).split(",")[0].strip()

    season, episode = season_episode_from_request(request)

    query = request.args.get("q") or request.args.get("Query")
    title = request.args.get("title")
    title_original = request.args.get("title_original")
    year = request.args.get("year", type=int)

    if not query and not title and not title_original:
        logger.warning("[TORZNAB] Search without query/title")
        return Response(wrap_in_xml(""), mimetype="application/xml")

    is_serial = is_serial_from_search(t, cat_param)
    if request.args.get("is_serial") is not None:
        try:
            is_serial = int(request.args.get("is_serial"))
        except (TypeError, ValueError):
            pass

    logger.info(
        "[TORZNAB] search t=%s q=%r title=%r orig=%r year=%s season=%s ep=%s is_serial=%s cat=%s",
        t,
        query,
        title,
        title_original,
        year,
        season,
        episode,
        is_serial,
        cat_param or "(none)",
    )
    genres = request.args.get("genres")
    categories = categories_from_request(request)
    card_mode = is_card_metadata_search(
        title,
        title_original,
        is_serial if request.args.get("is_serial") is not None else None,
        categories,
        genres,
    )

    torrents = search_combined(
        apikey=apikey,
        query=query,
        title=title,
        title_original=title_original,
        year=year,
        is_serial=is_serial,
        genres=genres,
        categories=categories,
        card_mode=card_mode,
        settings=settings,
    )
    if is_serial < 0 and cat_param and not card_mode:
        torrents = filter_results_by_category(torrents, cat_param)
    if season is not None:
        torrents = filter_results_by_season_episode(torrents, season, episode)
    logger.info("[TORZNAB] %d results after merge (+filters)", len(torrents))

    xml_items = [
        torrent_to_xml_item(tor, assigned_cat, cat_param=cat_param, settings=settings)
        for tor in torrents
    ]
    return Response(wrap_in_xml("".join(xml_items)), mimetype="application/xml")


@bp.route("/api")
def torznab_api():
    """Short Torznab path (``/api?t=…``)."""
    return handle_torznab_request()


@bp.route("/api/v2.0/indexers/<path:status>/results/torznab/api")
def jackett_torznab_api(status: str):
    """Jackett-style Torznab path (e.g. qBittorrent plugin)."""
    indexer_id = status.split("/")[0] if status else "all"
    return handle_torznab_request(indexer_id=indexer_id)
