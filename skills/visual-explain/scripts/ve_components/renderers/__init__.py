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
from .logic_tree import render_logic_tree
from .pyramid import render_pyramid
from .stairs import render_stairs
from .waterfall import render_waterfall
from .slope import render_slope
from .evidence_map import render_evidence_map
from .bars import render_bars
from .kpi import render_kpi

TRUSTED_RENDERERS: dict[str, RendererFn] = {
    "matrix@2": render_matrix,
    "flow@2": render_flow,
    "enumeration@2": render_enumeration,
    "chevron@2": render_chevron,
    "pyramid@2": render_pyramid,
    "stairs@2": render_stairs,
    "logic-tree@2": render_logic_tree,
    "waterfall@2": render_waterfall,
    "slope@2": render_slope,
    "evidence-map@2": render_evidence_map,
    "bars@2": render_bars,
    "kpi@2": render_kpi,
}
