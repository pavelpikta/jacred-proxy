"""Shared constants."""

TORZNAB_NS = "http://torznab.com/schemas/2015/feed"

TYPE_TO_CATEGORY: dict[str, int] = {
    "movie": 2000,
    "multfilm": 2000,
    "documovie": 2000,
    "serial": 5000,
    "multserial": 5000,
    "docuserial": 5000,
    "tvshow": 5000,
    "anime": 5070,
}

DEFAULT_TRACKER_NAME = "JacRed"
