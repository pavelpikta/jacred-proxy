"""Register HTTP blueprints."""

from __future__ import annotations

from flask import Flask

from jacred_proxy.routes.jackett import bp as jackett_bp
from jacred_proxy.routes.system import bp as system_bp
from jacred_proxy.routes.torznab import bp as torznab_bp


def register_routes(app: Flask) -> None:
    """Attach all route blueprints to *app*."""
    app.register_blueprint(system_bp)
    app.register_blueprint(torznab_bp)
    app.register_blueprint(jackett_bp)
