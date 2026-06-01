"""Flask application factory."""

from __future__ import annotations

from flask import Flask

from jacred_proxy.config import Settings, get_settings, init_settings
from jacred_proxy.log import setup_logging
from jacred_proxy.routes import register_routes


def create_app(settings: Settings | None = None) -> Flask:
    """Build and configure the WSGI application."""
    settings = settings or Settings.from_env()
    init_settings(settings)
    setup_logging(settings)

    app = Flask(__name__)
    app.config["SETTINGS"] = settings
    register_routes(app)
    return app
