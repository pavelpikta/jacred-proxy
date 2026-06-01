"""Health and backend metadata routes."""

from __future__ import annotations

import requests
from flask import Blueprint, jsonify

from jacred_proxy.config import get_settings
from jacred_proxy.log import get_logger

bp = Blueprint("system", __name__)
logger = get_logger()


@bp.route("/version", methods=["GET"])
def version():
    """Proxy version, or backend ``/version`` when reachable."""
    settings = get_settings()
    logger.info("Version endpoint called")
    try:
        resp = requests.get(f"{settings.base_url}/version", timeout=5)
        if resp.status_code == 200:
            logger.debug("Backend version: %s", resp.json())
            return jsonify(resp.json())
    except Exception as exc:
        logger.warning("Failed to get backend version: %s", exc)
    return jsonify({"version": settings.version})


@bp.route("/lastupdatedb", methods=["GET"])
def lastupdatedb():
    """Backend last DB update timestamp."""
    settings = get_settings()
    logger.info("Last update DB endpoint called")
    try:
        resp = requests.get(f"{settings.base_url}/lastupdatedb", timeout=5)
        if resp.status_code == 200:
            logger.debug("Backend last update: %s", resp.json())
            return jsonify(resp.json())
    except Exception as exc:
        logger.warning("Failed to get backend last update: %s", exc)
    return jsonify({"lastupdatedb": ""})
