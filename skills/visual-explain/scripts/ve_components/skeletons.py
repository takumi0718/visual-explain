"""Versioned skeleton resolution.

A generated document declares the skeleton version it was built from on its
``<html>`` start tag (``data-ve-skeleton``). Documents without the attribute
are version 1. The checker compares fixed regions against the declared version.
"""
from __future__ import annotations

import re
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
LATEST_SKELETON_VERSION = 3

_HTML_TAG_RE = re.compile(r"<html\b[^>]*>", re.IGNORECASE)
_VERSION_ATTR_RE = re.compile(r'\sdata-ve-skeleton="([0-9]+)"')


def declared_skeleton_version(markup: str) -> int:
    tag = _HTML_TAG_RE.search(markup)
    if tag is None:
        return 1
    match = _VERSION_ATTR_RE.search(tag.group(0))
    return int(match.group(1)) if match else 1


def skeleton_file(version: int, assets_dir: Path = ASSETS_DIR) -> Path:
    if version == LATEST_SKELETON_VERSION:
        return assets_dir / "skeleton.html"
    return assets_dir / f"skeleton-v{version}.html"


def resolve_skeleton(candidate: str, skeleton: str, assets_dir: Path = ASSETS_DIR) -> str | None:
    """Return the skeleton text the candidate must match, or None if unknown."""
    wanted = declared_skeleton_version(candidate)
    if wanted == declared_skeleton_version(skeleton):
        return skeleton
    if not 1 <= wanted <= LATEST_SKELETON_VERSION:
        return None
    try:
        return skeleton_file(wanted, assets_dir).read_text("utf-8")
    except OSError:
        return None
