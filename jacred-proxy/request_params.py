"""Parse search parameters from Flask requests."""

from __future__ import annotations

from typing import Any

from flask import Request


def categories_from_request(req: Request) -> list[str] | None:
    """Read ``Category[]`` or ``cat`` from query args."""
    cats = req.args.getlist("Category[]")
    if not cats:
        for key, val in req.args.items():
            if key.startswith("Category[") and val:
                cats.append(val)
    if cats:
        return cats
    raw = req.args.get("cat") or req.args.get("Category")
    if raw:
        return [p.strip() for p in str(raw).split(",") if p.strip()]
    return None


def is_card_metadata_search(
    title: str | None,
    title_original: str | None,
    is_serial: int | None,
    categories: list[str] | None,
    genres: str | None,
) -> bool:
    """True when request carries title/year/category (not free-text-only)."""
    if title is not None or title_original is not None:
        return True
    if is_serial is not None and is_serial >= 0:
        return True
    if categories or genres:
        return True
    return False
