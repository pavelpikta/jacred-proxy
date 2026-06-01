"""CLI entry: ``python -m jacred_proxy`` or ``jacred-proxy`` console script."""

from __future__ import annotations

from flask import Flask

from jacred_proxy import create_app
from jacred_proxy.config import get_settings
from jacred_proxy.log import get_logger


def main(app: Flask | None = None) -> None:
    """Run the development server."""
    app = app or create_app()
    settings = get_settings()
    logger = get_logger()
    logger.info("Starting Torznab proxy on %s:%s", settings.host, settings.port)
    logger.info("Backend URL: %s", settings.base_url)
    app.run(host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
