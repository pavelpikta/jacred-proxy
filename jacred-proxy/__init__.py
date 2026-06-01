"""Torznab/Jackett proxy package."""

from jacred_proxy.app import create_app
from jacred_proxy.config import Settings

__version__ = "1.0.0"
__all__ = ["create_app", "Settings", "__version__"]
