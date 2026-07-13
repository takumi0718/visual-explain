"""Static, accessible renderer for the semantic ``bars`` component."""
from __future__ import annotations

import html
from decimal import ROUND_HALF_UP, Decimal

from ..model import CanonicalSection, RenderManifest, RenderResult
from ..numeric import to_decimal

from ..model import CERTAINTY_LABEL as _CERT_LABEL


def _esc(value: str) -> str:
    return html.escape(str(value))


def _bar_width_pct(value: int | Decimal, v_max: Decimal) -> int:
    if v_max <= 0:
        return 0
    pct = (to_decimal(value) / v_max * Decimal(100)).to_integral_value(rounding=ROUND_HALF_UP)
    return int(pct)


def render_bars(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    bars = ir.bars
    assert bars is not None

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"
    highlight_id = bars.highlight_id

    values = [to_decimal(item.value) for item in bars.items]
    v_max = max(values) if values else Decimal(0)

    rows: list[str] = []
    for item in bars.items:
        width_pct = _bar_width_pct(item.value, v_max)
        fill_classes = ["ve-bars-fill", f"ve-bars-w-{width_pct}"]
        if highlight_id is not None and item.id == highlight_id:
            fill_classes.append("ve-dg-highlight")
        rows.append(
            f'<div class="ve-bars-row" data-ve-semantic-id="{_esc(item.id)}">'
            f'<span class="ve-bars-label">{_esc(item.label)}</span>'
            f'<span class="ve-bars-track">'
            f'<span class="{" ".join(fill_classes)}"></span>'
            f'<span class="ve-bars-value">{_esc(item.value_text)}</span>'
            f'</span></div>'
        )

    notes = []
    for cert in ir.certainty:
        notes.append(
            f'<li data-ve-semantic-id="{_esc(cert.id)}">'
            f'<strong>{_esc(_CERT_LABEL.get(cert.level, cert.level))}:</strong> {_esc(cert.statement)}</li>'
        )
    for src in ir.sources:
        detail = f"（{_esc(src.detail)}）" if src.detail else ""
        notes.append(
            f'<li data-ve-semantic-id="{_esc(src.id)}">'
            f'<strong>出典 {_esc(src.label)}</strong>{detail}</li>'
        )

    markup = (
        f'<figure data-ve-component="bars" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<p class="ve-fig-title">{_esc(bars.title)}</p>'
        f'<p class="ve-fig-unit">単位: {_esc(bars.unit_label)}</p>'
        f'<figcaption id="{_esc(caption_id)}" class="ve-bars-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-bars-summary">{_esc(ir.accessibility.summary)}</p>'
        f'<div class="ve-bars-list">{"".join(rows)}</div>'
        f'<ul class="ve-bars-notes">{"".join(notes)}</ul>'
        f'</figure>'
    )

    style_assets = [a for a in definition.assets if a.slot == "styles"]
    manifest = RenderManifest(
        component_id=definition.id,
        component_version=definition.version,
        instance_id=ir.id,
        consumed_semantic_ids=ir.semantic_ids(),
        generated_relationship_ids=(),
        generated_landmark_ids=(caption_id, summary_id),
        asset_ids=tuple(a.id for a in style_assets),
        asset_digests=tuple(a.digest for a in style_assets),
        declared_dependencies=tuple(definition.dependencies),
        fallback_mode=definition.fallback,
    )
    return RenderResult(
        markup=markup,
        style_asset_ids=tuple(a.id for a in style_assets),
        script_asset_ids=(),
        manifest=manifest,
    )
