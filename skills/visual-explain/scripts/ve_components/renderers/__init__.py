"""Trusted renderer allowlist.

Only renderers registered here may produce canonical markup. The mapping is a
closed allowlist keyed by ``"<component>@<version>"``; it starts empty and each
renderer is added atomically with its registry entry, CSS asset, digest, and
checker rules in Tasks 5-6.
"""
from __future__ import annotations

from ..model import RendererFn
from .chevron import render_chevron
from .enumeration import render_enumeration
from .flow import render_flow
from .matrix import render_matrix
from .pyramid import render_pyramid
from .stairs import render_stairs

TRUSTED_RENDERERS: dict[str, RendererFn] = {
    "matrix@1": render_matrix,
    "flow@1": render_flow,
    "enumeration@1": render_enumeration,
    "chevron@1": render_chevron,
    "pyramid@1": render_pyramid,
    "stairs@1": render_stairs,
}
