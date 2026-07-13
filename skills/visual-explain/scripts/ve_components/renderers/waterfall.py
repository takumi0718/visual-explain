"""Static, accessible renderer for the semantic ``waterfall`` component (v2 SVG)."""
from __future__ import annotations

import html
import re
from decimal import Decimal

from ..model import CanonicalSection, RenderManifest, RenderResult
from ..numeric import to_decimal, waterfall_axis_max, waterfall_scale_values, waterfall_y

from ..model import CERTAINTY_LABEL as _CERT_LABEL

_CHART_LEFT = 70
_CHART_RIGHT = 620
_BASELINE_Y = 320
_AXIS_X = 70


def _esc(value: str) -> str:
    return html.escape(str(value))


def _triangle_value_text(value_text: str, delta: Decimal) -> str:
    if delta < 0:
        digits = re.sub(r"[^\d]", "", value_text)
        return f"▲{digits}" if digits else f"▲{abs(delta)}"
    return value_text


def _largest_decrease_step_id(steps) -> str | None:
    negatives = [(step.id, abs(to_decimal(step.delta))) for step in steps if to_decimal(step.delta) < 0]
    if not negatives:
        return None
    return max(negatives, key=lambda item: item[1])[0]


def render_waterfall(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    wf = ir.waterfall
    assert wf is not None

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"
    svg_id = f"{ir.id}-svg"

    scale_values, _, _ = waterfall_scale_values(wf)
    v_max = waterfall_axis_max(scale_values)

    bars: list[dict] = []
    bars.append({
        "semantic_id": wf.start.id,
        "label": wf.start.label,
        "value_text": wf.start.value_text,
        "kind": "total",
        "bottom": Decimal(0),
        "top": to_decimal(wf.start.value),
    })

    running = to_decimal(wf.start.value)
    running_levels: list[Decimal] = [running]
    largest_minus_id = _largest_decrease_step_id(wf.steps)

    for step in wf.steps:
        prev = running
        running = running + to_decimal(step.delta)
        running_levels.append(running)
        if to_decimal(step.delta) >= 0:
            kind = "plus"
        elif step.id == largest_minus_id:
            kind = "minus"
        else:
            kind = "minus-soft"
        bars.append({
            "semantic_id": step.id,
            "label": step.label,
            "value_text": _triangle_value_text(step.value_text, to_decimal(step.delta)),
            "kind": kind,
            "bottom": min(prev, running),
            "top": max(prev, running),
        })

    bars.append({
        "semantic_id": wf.end.id,
        "label": wf.end.label,
        "value_text": wf.end.value_text,
        "kind": "total",
        "bottom": Decimal(0),
        "top": to_decimal(wf.end.value),
    })

    n = len(bars)
    slot_w = 550 // n
    bar_w = min(70, slot_w - 20)

    svg_parts: list[str] = []

    svg_parts.append(
        f'<line class="ve-wf-axis" x1="{_AXIS_X}" y1="40" x2="{_AXIS_X}" y2="{_BASELINE_Y}"></line>'
    )
    svg_parts.append(
        f'<line class="ve-wf-axis" x1="{_AXIS_X - 6}" y1="46" x2="{_AXIS_X}" y2="40"></line>'
    )
    svg_parts.append(
        f'<line class="ve-wf-axis" x1="{_AXIS_X + 6}" y1="46" x2="{_AXIS_X}" y2="40"></line>'
    )
    svg_parts.append(
        f'<line class="ve-wf-axis" x1="{_CHART_LEFT}" y1="{_BASELINE_Y}"'
        f' x2="{_CHART_RIGHT}" y2="{_BASELINE_Y}"></line>'
    )

    for tick in wf.axis_ticks:
        tick_val = to_decimal(tick)
        y = waterfall_y(tick_val, v_max)
        svg_parts.append(
            f'<text class="ve-wf-tick" x="{_AXIS_X - 8}" y="{y + 4}" text-anchor="end">{_esc(tick)}</text>'
        )

    svg_parts.append(
        f'<text class="ve-wf-unit-label" x="{_AXIS_X - 8}" y="28" text-anchor="end">'
        f'{_esc(wf.unit_label)}</text>'
    )

    bar_centers: list[int] = []
    for index, bar in enumerate(bars):
        cx = _CHART_LEFT + index * slot_w + slot_w // 2
        bar_centers.append(cx)
        x = cx - bar_w // 2
        y_top = waterfall_y(bar["top"], v_max)
        y_bottom = waterfall_y(bar["bottom"], v_max)
        height = y_bottom - y_top
        if height < 1:
            height = 1
            y_top = y_bottom - 1

        kind = bar["kind"]
        if kind == "total":
            bar_cls = "ve-wf-bar ve-wf-total"
            value_cls = "ve-wf-value-on-fill"
        elif kind == "plus":
            bar_cls = "ve-wf-bar ve-wf-plus"
            value_cls = "ve-wf-value-plus"
        elif kind == "minus":
            bar_cls = "ve-wf-bar ve-wf-minus"
            value_cls = "ve-wf-value-on-fill"
        else:
            bar_cls = "ve-wf-bar ve-wf-minus-soft"
            value_cls = "ve-wf-value-minus-soft"

        value_y = y_top + max(12, height // 2 + 4)
        factor_y = y_top - 8 if kind == "plus" else y_bottom + 16

        svg_parts.append(
            f'<g data-ve-semantic-id="{_esc(bar["semantic_id"])}">'
            f'<rect class="{bar_cls}" x="{x}" y="{y_top}" width="{bar_w}" height="{height}"></rect>'
            f'<text class="{value_cls}" x="{cx}" y="{value_y}" text-anchor="middle">'
            f'{_esc(bar["value_text"])}</text>'
            f'<text class="ve-wf-factor" x="{cx}" y="{factor_y}" text-anchor="middle">'
            f'{_esc(bar["label"])}</text>'
            f'</g>'
        )

    for index in range(n - 1):
        level = running_levels[index]
        y = waterfall_y(level, v_max)
        x1 = bar_centers[index] + bar_w // 2
        x2 = bar_centers[index + 1] - bar_w // 2
        if x2 > x1:
            svg_parts.append(
                f'<line class="ve-wf-connector" x1="{x1}" y1="{y}" x2="{x2}" y2="{y}"></line>'
            )

    svg_markup = (
        f'<svg id="{_esc(svg_id)}" class="ve-wf-chart --fs-figure"'
        f' viewBox="0 0 640 360" preserveAspectRatio="xMidYMid meet"'
        f' role="img" aria-label="{_esc(ir.accessibility.label)}"'
        f' aria-describedby="{_esc(summary_id)}">'
        f'<title>{_esc(ir.caption)}</title>'
        f'<desc>{_esc(ir.accessibility.summary)}</desc>'
        f'{"".join(svg_parts)}'
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

    markup = (
        f'<figure data-ve-component="waterfall" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<p class="ve-fig-title">{_esc(wf.title)}</p>'
        f'<p class="ve-fig-unit">単位: {_esc(wf.unit_label)}</p>'
        f'<figcaption id="{_esc(caption_id)}" class="ve-waterfall-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-waterfall-summary">{_esc(ir.accessibility.summary)}</p>'
        f'{svg_markup}'
        f'<ul class="ve-waterfall-notes">{"".join(notes)}</ul>'
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
