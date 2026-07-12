"""Static, accessible renderer for the semantic ``slope`` component.

Two-point comparison with deterministic SVG geometry inside the renderer-svg gate.
"""
from __future__ import annotations

import html

from ..model import CanonicalSection, RenderManifest, RenderResult
from ..numeric import slope_scale_values, slope_y, to_decimal

_CERT_LABEL = {"confirmed": "確定", "inferred": "推定", "unverified": "未確認"}
_FROM_X = 120
_TO_X = 480


def _esc(value: str) -> str:
    return html.escape(str(value))


def render_slope(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    slope = ir.slope
    assert slope is not None
    takeaway = set(ir.takeaway_target_ids)
    emphasis_by_id = {e.target_id: e.label for e in ir.emphasis}

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"
    svg_id = f"{ir.id}-svg"
    lo, hi = slope_scale_values(slope)

    item_blocks: list[str] = []
    for index, item in enumerate(slope.items, start=1):
        y1 = slope_y(item.from_value, lo, hi)
        y2 = slope_y(item.to_value, lo, hi)
        label_y = min(y1, y2) - 12
        if label_y < 20:
            label_y = 20
        takeaway_cls = " ve-takeaway-target" if item.id in takeaway else ""
        takeaway_attr = ' data-ve-takeaway="true"' if item.id in takeaway else ""
        emphasis_html = (
            f'<title>{_esc(emphasis_by_id[item.id])}</title>'
            if item.id in emphasis_by_id else ""
        )
        item_blocks.append(
            f'<g class="ve-slope-row ve-slope-index-{index}{takeaway_cls}"'
            f' data-ve-semantic-id="{_esc(item.id)}"{takeaway_attr}>'
            f'<line class="ve-slope-item ve-slope-tone-{_esc(item.tone)}"'
            f' x1="{_FROM_X}" y1="{y1}" x2="{_TO_X}" y2="{y2}">{emphasis_html}</line>'
            f'<text class="ve-slope-value ve-slope-value-from" x="{_FROM_X}" y="{y1 - 8}"'
            f' text-anchor="end">{_esc(item.from_value_text)}</text>'
            f'<text class="ve-slope-value ve-slope-value-to" x="{_TO_X}" y="{y2 - 8}"'
            f' text-anchor="start">{_esc(item.to_value_text)}</text>'
            f'<text class="ve-slope-label" x="300" y="{label_y}" text-anchor="middle">'
            f'{_esc(item.label)}</text>'
            f'</g>'
        )

    svg_markup = (
        f'<svg id="{_esc(svg_id)}" class="ve-slope-chart --fs-figure"'
        f' viewBox="0 0 600 220" preserveAspectRatio="xMidYMid meet"'
        f' role="img" aria-label="{_esc(ir.accessibility.label)}"'
        f' aria-describedby="{_esc(summary_id)}">'
        f'<title>{_esc(ir.caption)}</title>'
        f'<desc>{_esc(ir.accessibility.summary)}</desc>'
        f'<text class="ve-slope-axis ve-slope-axis-from" x="{_FROM_X}" y="210"'
        f' text-anchor="middle">{_esc(slope.axes.from_label)}</text>'
        f'<text class="ve-slope-axis ve-slope-axis-to" x="{_TO_X}" y="210"'
        f' text-anchor="middle">{_esc(slope.axes.to_label)}</text>'
        f'{"".join(item_blocks)}'
        f'</svg>'
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

    annotation_note = ""
    if emphasis_by_id:
        joined = "、".join(f"注釈: {_esc(label)}" for label in emphasis_by_id.values())
        annotation_note = f" {joined}"

    markup = (
        f'<figure data-ve-component="slope" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-slope-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-slope-summary">'
        f'{_esc(ir.accessibility.summary)}（単位: {_esc(slope.unit)}）{annotation_note}</p>'
        f'{svg_markup}'
        f'<ul class="ve-slope-notes">{"".join(notes)}</ul>'
        f'</figure>'
    )

    style_assets = [a for a in definition.assets if a.slot == "styles"]
    manifest = RenderManifest(
        component_id=definition.id,
        component_version=definition.version,
        instance_id=ir.id,
        consumed_semantic_ids=ir.semantic_ids(),
        generated_relationship_ids=(),
        generated_landmark_ids=(caption_id, summary_id, svg_id),
        asset_ids=tuple(a.id for a in style_assets),
        asset_digests=tuple(a.digest for a in style_assets),
        declared_dependencies=tuple(definition.dependencies),
        fallback_mode=definition.fallback,
        svg_root_ids=(svg_id,),
    )
    return RenderResult(
        markup=markup,
        style_asset_ids=tuple(a.id for a in style_assets),
        script_asset_ids=(),
        manifest=manifest,
    )
