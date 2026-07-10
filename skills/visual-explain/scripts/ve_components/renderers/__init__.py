"""Trusted renderer allowlist.

Only renderers registered here may produce canonical markup. The mapping is a
closed allowlist keyed by ``"<component>@<version>"``; it starts empty and each
renderer is added atomically with its registry entry, CSS asset, digest, and
checker rules in Tasks 5-6.
"""
from __future__ import annotations

from ..model import RendererFn

TRUSTED_RENDERERS: dict[str, RendererFn] = {}
