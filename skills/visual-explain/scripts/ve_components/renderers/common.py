"""Shared renderer behavior for visual-stage markup and assets."""
from __future__ import annotations

import html
from collections.abc import Iterable

from ..model import CanonicalIR
from ..registry import AssetDefinition

_VISUAL_STAGE_ASSET_ID = "visual-stage"


def claim_before_body(ir: CanonicalIR, body_markup: str) -> str:
    """Return an optional escaped claim immediately before an unchanged body."""
    if ir.claim is None:
        return body_markup
    return f'<p class="ve-claim">{html.escape(ir.claim)}</p>{body_markup}'


def select_style_assets(
    ir: CanonicalIR,
    assets: Iterable[AssetDefinition],
) -> tuple[AssetDefinition, ...]:
    """Select style assets, gating only the shared visual-stage asset."""
    has_stage_fields = any(
        value is not None for value in (ir.claim, ir.sequence, ir.assertions)
    )
    return tuple(
        asset for asset in assets
        if asset.slot == "styles"
        and (asset.id != _VISUAL_STAGE_ASSET_ID or has_stage_fields)
    )
