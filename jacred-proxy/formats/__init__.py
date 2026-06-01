"""Response format builders (Torznab XML, Jackett JSON)."""

from jacred_proxy.formats.jackett_json import result_to_jackett_json
from jacred_proxy.formats.torznab_xml import (
    get_caps_xml,
    get_indexers_xml,
    torrent_to_xml_item,
    wrap_in_xml,
)

__all__ = [
    "get_caps_xml",
    "get_indexers_xml",
    "torrent_to_xml_item",
    "wrap_in_xml",
    "result_to_jackett_json",
]
