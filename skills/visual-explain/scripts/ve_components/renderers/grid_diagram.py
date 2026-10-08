"""Static, accessible renderer for the semantic ``grid-diagram`` component.

The author places nodes, regions and markers on grid cells; every coordinate,
route and colour comes from ``grid_layout`` and the component CSS. The SVG
uses only the renderer-svg allowlist (svg / g / rect / line / circle / text /
title), and a visually hidden list repeats the picture as text.
"""
from __future__ import annotations

import html

from ..grid_layout import (
    MARKER_R,
    arrow_lines,
    marker_position,
    node_cells,
    node_label_lines,
    node_label_positions,
    node_rect,
    region_cells,
    region_label_position,
    region_rect,
    route_edges,
    viewbox,
)
from ..model import CERTAINTY_LABEL, CanonicalSection, GridDiagramPayload, RenderManifest, RenderResult
from .common import claim_before_body, select_style_assets

_MARKER_DIGITS = "①②③④⑤"


def _esc(value: object) -> str:
    return html.escape(str(value))


def render_grid_svg(payload: GridDiagramPayload, *, svg_id: str, label: str,
                    described_by: str, semantic: bool = True) -> str:
    """Draw one validated payload. ``semantic`` adds data-ve-semantic-id to each part."""

    def sid(item_id: str) -> str:
        return f' data-ve-semantic-id="{_esc(item_id)}"' if semantic else ""

    rects = {node.id: node_rect(node) for node in payload.nodes}
    parts: list[str] = []
    for region in payload.regions:
        rect = region_rect(region)
        lx, ly = region_label_position(region)
        parts.append(
            f'<g class="ve-gd-region"{sid(region.id)}>'
            f'<rect class="ve-gd-region-frame" x="{rect.x0}" y="{rect.y0}"'
            f' width="{rect.width}" height="{rect.height}"></rect>'
            f'<text class="ve-gd-region-label" x="{lx}" y="{ly}" text-anchor="start">{_esc(region.label)}</text>'
            f'</g>'
        )
    for edge, route in zip(payload.edges, route_edges(payload)):
        assert not isinstance(route, str), route  # validation already ran check_layout
        lines = [
            f'<line class="ve-gd-edge-line" x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}"></line>'
            for a, b in zip(route.points, route.points[1:])
        ]
        lines.extend(
            f'<line class="ve-gd-edge-arrow" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"></line>'
            for x1, y1, x2, y2 in arrow_lines(route.points)
        )
        if route.label_at is not None:
            tx, ty, anchor = route.label_at
            lines.append(
                f'<text class="ve-gd-edge-label" x="{tx}" y="{ty}" text-anchor="{anchor}">{_esc(edge.label)}</text>'
            )
        parts.append(f'<g class="ve-gd-edge"{sid(edge.id)}>{"".join(lines)}</g>')
    for node in payload.nodes:
        rect = rects[node.id]
        label_lines = node_label_lines(node)
        assert label_lines is not None
        texts = "".join(
            f'<text class="ve-gd-node-label" x="{x}" y="{y}" text-anchor="middle">{_esc(line)}</text>'
            for line, (x, y) in zip(label_lines, node_label_positions(node, label_lines))
        )
        parts.append(
            f'<g class="ve-gd-node ve-gd-tone-{node.tone}"{sid(node.id)}>'
            f'<rect class="ve-gd-node-box" x="{rect.x0}" y="{rect.y0}"'
            f' width="{rect.width}" height="{rect.height}"></rect>{texts}</g>'
        )
    by_id = {node.id: node for node in payload.nodes}
    for marker in sorted(payload.markers, key=lambda m: m.n):
        cx, cy = marker_position(by_id[marker.target])
        parts.append(
            f'<g class="ve-gd-marker">'
            f'<circle class="ve-gd-marker-dot" cx="{cx}" cy="{cy}" r="{MARKER_R}"></circle>'
            f'<text class="ve-gd-marker-n" x="{cx}" y="{cy + 4}" text-anchor="middle">{marker.n}</text>'
            f'</g>'
        )
    return (
        f'<svg id="{_esc(svg_id)}" class="ve-gd-svg ve-gd-cols-{payload.cols}"'
        f' viewBox="{viewbox(payload.cols, payload.rows)}" preserveAspectRatio="xMidYMid meet"'
        f' role="img" aria-label="{_esc(label)}" aria-describedby="{_esc(described_by)}">'
        f'<title>{_esc(label)}</title>{"".join(parts)}</svg>'
    )


def relation_items(payload: GridDiagramPayload) -> list[str]:
    """Text twin of the picture: one item per node, region, edge and marker, in that order."""
    names = {node.id: node.label for node in payload.nodes}
    items: list[str] = []
    for node in payload.nodes:
        inside = [r.label for r in payload.regions if node_cells(node) <= region_cells(r)]
        where = f"（{'・'.join(inside)}）" if inside else ""
        items.append(f'<li class="ve-gd-rel-node">{_esc(node.label)}{_esc(where)}</li>')
    for region in payload.regions:
        members = [n.label for n in payload.nodes if node_cells(n) <= region_cells(region)]
        content = "・".join(members) if members else "中は空"
        items.append(f'<li class="ve-gd-rel-region">{_esc(region.label)}: {_esc(content)}</li>')
    for edge in payload.edges:
        tail = f"（{edge.label}）" if edge.label else ""
        items.append(
            f'<li class="ve-gd-rel-edge">{_esc(names[edge.source])} → {_esc(names[edge.target])}{_esc(tail)}</li>'
        )
    for marker in sorted(payload.markers, key=lambda m: m.n):
        items.append(
            f'<li class="ve-gd-rel-marker">番号 {_MARKER_DIGITS[marker.n - 1]}: {_esc(names[marker.target])}</li>'
        )
    return items


def render_option_figure(payload: GridDiagramPayload, *, id_base: str, label: str) -> str:
    """Small picture inside a decision option; no semantic ids (it is not a canonical figure)."""
    relations_id = f"{id_base}-relations"
    svg = render_grid_svg(payload, svg_id=f"{id_base}-svg", label=label,
                          described_by=relations_id, semantic=False)
    return (
        f'<figure data-ve-component="grid-diagram" class="ve-gd ve-gd-thumb" data-ve-thumb'
        f' data-ve-grid="{payload.cols}x{payload.rows}" aria-label="{_esc(label)}">{svg}'
        f'<ul id="{_esc(relations_id)}" class="ve-gd-relations visually-hidden">'
        f'{"".join(relation_items(payload))}</ul></figure>'
    )


def render_grid_diagram(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    payload = ir.grid_diagram
    assert payload is not None
    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"
    relations_id = f"{ir.id}-relations"
    svg_id = f"{ir.id}-svg"
    svg_markup = render_grid_svg(payload, svg_id=svg_id, label=ir.accessibility.label,
                                 described_by=relations_id)
    notes = []
    for cert in ir.certainty:
        notes.append(
            f'<li data-ve-semantic-id="{_esc(cert.id)}">'
            f'<strong>{_esc(CERTAINTY_LABEL.get(cert.level, cert.level))}:</strong> {_esc(cert.statement)}</li>'
        )
    for src in ir.sources:
        detail = f"（{_esc(src.detail)}）" if src.detail else ""
        notes.append(
            f'<li data-ve-semantic-id="{_esc(src.id)}"><strong>出典 {_esc(src.label)}</strong>{detail}</li>'
        )
    body_markup = (
        f'<figure data-ve-component="grid-diagram" class="ve-gd"'
        f' data-ve-grid="{payload.cols}x{payload.rows}" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-gd-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-gd-summary">{_esc(ir.accessibility.summary)}</p>'
        f'<div class="ve-gd-canvas">{svg_markup}</div>'
        f'<ul id="{_esc(relations_id)}" class="ve-gd-relations visually-hidden">'
        f'{"".join(relation_items(payload))}</ul>'
        f'<ul class="ve-grid-diagram-notes">{"".join(notes)}</ul>'
        f'</figure>'
    )
    markup = claim_before_body(ir, body_markup)
    style_assets = select_style_assets(ir, definition.assets)
    manifest = RenderManifest(
        component_id=definition.id,
        component_version=definition.version,
        instance_id=ir.id,
        consumed_semantic_ids=ir.semantic_ids(),
        generated_relationship_ids=(),
        generated_landmark_ids=(caption_id, summary_id, relations_id, svg_id),
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
