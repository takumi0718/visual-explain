"""Static, accessible renderer for the semantic ``waterfall`` component.

Additive bridge with bars or columns orientation. Layout uses pre-generated
``ve-wf-start-{0..100}`` / ``ve-wf-len-{0..100}`` classes only — no inline
styles. Geometry is quantized from Decimal scale math; valueText is primary.
"""
from __future__ import annotations

import html
import re
from decimal import Decimal

from ..diagnostics import RENDERER_FAILURE, Diagnostic
from ..model import CanonicalSection, RenderManifest, RenderResult, WaterfallPayload
from ..numeric import quantize_percent, to_decimal, waterfall_scale_values

from ..model import CERTAINTY_LABEL as _CERT_LABEL
_WF_CLASS_RE = re.compile(r"^ve-wf-(start|len)-(\d+)$")


def _esc(value: str) -> str:
    return html.escape(str(value))


def _bar_geometry(from_val, to_val, lo, hi) -> tuple[int, int] | None:
    p_from = quantize_percent(from_val, lo, hi)
    p_to = quantize_percent(to_val, lo, hi)
    start = min(p_from, p_to)
    length = abs(p_to - p_from)
    if start < 0 or start > 100 or length < 0 or length > 100 or start + length > 100:
        return None
    return start, length


def _class_pair(start: int, length: int) -> str:
    return f"ve-wf-start-{start} ve-wf-len-{length}"


def _render_bar(
    semantic_id: str,
    label: str,
    value_text: str,
    from_val,
    to_val,
    lo,
    hi,
    *,
    tone: str | None = None,
    takeaway: bool = False,
    emphasis: str = "",
) -> tuple[str, Diagnostic | None]:
    geom = _bar_geometry(from_val, to_val, lo, hi)
    if geom is None:
        return "", Diagnostic(RENDERER_FAILURE, f"棒 '{semantic_id}' の百分率が域外です")
    start, length = geom
    tone_cls = f" ve-wf-tone-{tone}" if tone else ""
    takeaway_cls = " ve-takeaway-target" if takeaway else ""
    takeaway_attr = ' data-ve-takeaway="true"' if takeaway else ""
    emphasis_html = f'<span class="ve-emphasis">{_esc(emphasis)}</span>' if emphasis else ""
    markup = (
        f'<div class="ve-waterfall-row">'
        f'<span class="ve-waterfall-label">{_esc(label)}</span>'
        f'<div class="ve-waterfall-track">'
        f'<div class="ve-waterfall-bar {_class_pair(start, length)}{tone_cls}{takeaway_cls}"'
        f' data-ve-semantic-id="{_esc(semantic_id)}"{takeaway_attr}>'
        f'<span class="ve-waterfall-value">{_esc(value_text)}</span>{emphasis_html}'
        f'</div></div></div>'
    )
    return markup, None


def _render_connector(from_val, to_val, lo, hi) -> tuple[str, Diagnostic | None]:
    geom = _bar_geometry(from_val, to_val, lo, hi)
    if geom is None:
        return "", Diagnostic(RENDERER_FAILURE, "コネクタの百分率が域外です")
    start, length = geom
    return (
        f'<div class="ve-waterfall-connector-track">'
        f'<span class="ve-waterfall-connector {_class_pair(start, length)}" aria-hidden="true"></span>'
        f'</div>',
        None,
    )


def render_waterfall(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    wf = ir.waterfall
    assert wf is not None
    takeaway = set(ir.takeaway_target_ids)
    emphasis_by_id = {e.target_id: e.label for e in ir.emphasis}
    diagnostics: list[Diagnostic] = []

    _, lo, hi = waterfall_scale_values(wf)
    orientation = wf.orientation
    container_cls = "ve-wf-columns" if orientation == "columns" else "ve-wf-bars"

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"

    items: list[str] = []
    running = to_decimal(wf.start.value)

    bar_html, diag = _render_bar(
        wf.start.id, wf.start.label, wf.start.value_text,
        Decimal(0), running, lo, hi,
        takeaway=wf.start.id in takeaway,
        emphasis=emphasis_by_id.get(wf.start.id, ""),
    )
    if diag:
        diagnostics.append(diag)
    items.append(bar_html)

    prev = running
    for step in wf.steps:
        conn_html, conn_diag = _render_connector(prev, running, lo, hi)
        if conn_diag:
            diagnostics.append(conn_diag)
        else:
            items.append(conn_html)
        nxt = running + to_decimal(step.delta)
        bar_html, diag = _render_bar(
            step.id, step.label, step.value_text,
            prev, nxt, lo, hi,
            tone=step.tone,
            takeaway=step.id in takeaway,
            emphasis=emphasis_by_id.get(step.id, ""),
        )
        if diag:
            diagnostics.append(diag)
        items.append(bar_html)
        prev = nxt
        running = nxt

    conn_html, conn_diag = _render_connector(prev, to_decimal(wf.end.value), lo, hi)
    if conn_diag:
        diagnostics.append(conn_diag)
    else:
        items.append(conn_html)

    bar_html, diag = _render_bar(
        wf.end.id, wf.end.label, wf.end.value_text,
        Decimal(0), to_decimal(wf.end.value), lo, hi,
        takeaway=wf.end.id in takeaway,
        emphasis=emphasis_by_id.get(wf.end.id, ""),
    )
    if diag:
        diagnostics.append(diag)
    items.append(bar_html)

    scroll_open = '<div class="ve-waterfall-scroll">' if orientation == "columns" else ""
    scroll_close = "</div>" if orientation == "columns" else ""
    bridge = (
        f'{scroll_open}<div class="ve-waterfall-bridge {container_cls}">'
        f'{"".join(items)}</div>{scroll_close}'
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
        f'<figure data-ve-component="waterfall" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-waterfall-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-waterfall-summary">{_esc(ir.accessibility.summary)}{annotation_note}</p>'
        f'{bridge}'
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
        diagnostics=tuple(diagnostics),
    )
