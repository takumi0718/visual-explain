"""Static, accessible renderer for the semantic ``flow`` component.

Explicit order, directed transition, and branch relationships only. Produces a
semantic <figure> that draws nodes and their connections in a single grid — a
vertical spine (DOM order == reading order == grid row) for adjacent
transitions, plus right-hand rails for skip/branch edges placed purely by
pre-generated ``ve-rail-{s}-{e}`` grid-row classes. No scripts, no inline
styles, no free coordinates: layout is entirely class-driven so the checker can
re-derive every node and edge from the DOM. A visually-hidden edge sentence list
(carrying no data attributes) keeps the relationships legible to assistive tech
without creating a second semantic layer.
"""
from __future__ import annotations

import html

from ..diagnostics import RENDERER_FAILURE, Diagnostic
from ..flow_layout import MAX_SPINE_ROWS, assign_rails, edge_spans, order_index
from ..model import CanonicalSection, RenderManifest, RenderResult

from ..model import CERTAINTY_LABEL as _CERT_LABEL
_RELATION_LABEL = {
    "ordered-transition": "順序遷移",
    "directed-transition": "有向遷移",
    "branching": "分岐",
}

# Row upper bound for the pre-generated ve-rail-{s}-{e} classes (bounds
# 1<=s<e<=MAX_SPINE_ROWS). validation.py's check_row_budget rejects any flow
# that would exceed this budget with flow_topology_too_complex before it ever
# reaches the renderer; this local alias plus the guard below is a defensive
# fail-closed backstop, not the primary enforcement point.
MAX_ROWS = MAX_SPINE_ROWS


def _esc(value: str) -> str:
    return html.escape(str(value))


def render_flow(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    flow = ir.flow
    assert flow is not None
    node_by_id = {n.id: n for n in flow.nodes}
    takeaway = set(ir.takeaway_target_ids)
    emphasis_by_id = {e.target_id: e.label for e in ir.emphasis}

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"

    index = order_index(flow.nodes, list(flow.reading_order))
    ordered = sorted((nid for nid in index if nid in node_by_id), key=index.__getitem__)
    spans = edge_spans(flow.edges, index)
    rails, rail_diags = assign_rails(spans)
    diagnostics: list[Diagnostic] = list(rail_diags)  # validation済みだが防御的に載せる

    # Adjacent edges (source i -> target i+1) become inline spine links. Parallel
    # edges are forbidden by validation, so at most one edge lands on each source
    # position; the assert makes that invariant explicit.
    adjacent: dict[int, object] = {}
    for edge in flow.edges:
        s, t = index.get(edge.source), index.get(edge.target)
        if s is not None and t == s + 1:
            assert s not in adjacent, f"並行辺が検出されました: 位置 {s}"
            adjacent[s] = edge

    def annotate(nid: str) -> tuple[str, str, str]:
        cls = " ve-takeaway-target" if nid in takeaway else ""
        attr = ' data-ve-takeaway="true"' if nid in takeaway else ""
        emphasis = (f'<span class="ve-emphasis">{_esc(emphasis_by_id[nid])}</span>'
                    if nid in emphasis_by_id else "")
        return cls, attr, emphasis

    def station_li(nid: str, in_group: bool) -> str:
        cls, attr, emphasis = annotate(nid)
        group_cls = " in-group" if in_group else ""
        return (f'<li class="ve-flow-station{group_cls}">'
                f'<span class="ve-flow-node{cls}" data-ve-semantic-id="{_esc(nid)}"'
                f' data-ve-node-id="{_esc(nid)}"{attr}>{_esc(node_by_id[nid].label)}{emphasis}</span></li>')

    def link_li(edge) -> str:
        cls, attr, emphasis = annotate(edge.id)
        relation = _RELATION_LABEL.get(edge.relation, edge.relation)
        label = f'<span class="ve-flow-edge-label">{_esc(edge.label)}</span>' if edge.label else ""
        return (f'<li class="ve-flow-link{cls}" data-ve-semantic-id="{_esc(edge.id)}"'
                f' data-ve-from="{_esc(edge.source)}" data-ve-to="{_esc(edge.target)}"'
                f' data-ve-relation="{_esc(edge.relation)}"{attr}>'
                f'<span class="ve-flow-arrow" aria-hidden="true">↓</span>{label}'
                f'<span class="ve-flow-rel">{_esc(relation)}</span>{emphasis}</li>')

    # Spine assembly by row counter: DOM order becomes the grid row via
    # auto-placement, so we track the row each station lands on for the rails.
    group_label = {g.id: g.label for g in flow.groups}
    spine_items: list[str] = []
    station_row: dict[str, int] = {}
    row = 0
    current_group: object = object()  # 先頭比較用の番兵
    for nid in ordered:
        group = node_by_id[nid].group
        if group != current_group:
            current_group = group
            if group is not None:
                row += 1
                spine_items.append(
                    f'<li class="ve-flow-group-label" data-ve-semantic-id="{_esc(group)}">'
                    f'{_esc(group_label.get(group, group))}</li>')
        row += 1
        station_row[nid] = row
        spine_items.append(station_li(nid, in_group=group is not None))
        edge = adjacent.get(index[nid])
        if edge is not None:
            row += 1
            spine_items.append(link_li(edge))

    rail_items: list[str] = []
    for edge in flow.edges:
        if edge.id not in rails:
            # Not a rail and not an adjacent link means the edge fell through both
            # placement paths — fail closed rather than drop a relationship.
            if index[edge.target] - index[edge.source] != 1:
                diagnostics.append(Diagnostic(
                    RENDERER_FAILURE, f"辺 '{edge.id}' がspineにもレールにも割当てられていません"))
            continue
        rs, rt = station_row[edge.source], station_row[edge.target]
        if rt + 1 > MAX_ROWS:
            diagnostics.append(Diagnostic(
                RENDERER_FAILURE, f"レール '{edge.id}' が行上限 {MAX_ROWS} を超えます"))
            continue
        cls, attr, emphasis = annotate(edge.id)
        label = f'<span class="ve-flow-edge-label">{_esc(edge.label)}</span>' if edge.label else ""
        rail_items.append(
            f'<li class="ve-flow-rail{cls} ve-rail-lane-{rails[edge.id]} ve-rail-{rs}-{rt + 1}"'
            f' data-ve-semantic-id="{_esc(edge.id)}" data-ve-from="{_esc(edge.source)}"'
            f' data-ve-to="{_esc(edge.target)}" data-ve-relation="{_esc(edge.relation)}"{attr}>'
            f'{label}{emphasis}</li>')

    canvas = (f'<div class="ve-flow-scroll"><ol class="ve-flow-canvas">'
              f'{"".join(spine_items)}{"".join(rail_items)}</ol></div>')

    # Visually-hidden edge sentences carry NO data attributes: the visible spine
    # and rails are the single semantic layer.
    hidden_items = []
    for edge in flow.edges:
        source = node_by_id.get(edge.source)
        target = node_by_id.get(edge.target)
        source_label = _esc(source.label) if source else _esc(edge.source)
        target_label = _esc(target.label) if target else _esc(edge.target)
        relation = _RELATION_LABEL.get(edge.relation, edge.relation)
        label = f'（{_esc(edge.label)}）' if edge.label else ""
        hidden_items.append(
            f'<li>{source_label} から {target_label} への{_esc(relation)}{label}</li>')

    notes = []
    for cert in ir.certainty:
        notes.append(f'<li data-ve-semantic-id="{_esc(cert.id)}"><strong>{_esc(_CERT_LABEL.get(cert.level, cert.level))}:</strong> {_esc(cert.statement)}</li>')
    for src in ir.sources:
        detail = f"（{_esc(src.detail)}）" if src.detail else ""
        notes.append(f'<li data-ve-semantic-id="{_esc(src.id)}"><strong>出典 {_esc(src.label)}</strong>{detail}</li>')

    annotation_note = ""
    if emphasis_by_id:
        joined = "、".join(f"注釈: {_esc(label)}" for label in emphasis_by_id.values())
        annotation_note = f" {joined}"

    markup = (
        f'<figure data-ve-component="flow" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-flow-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-flow-summary">{_esc(ir.accessibility.summary)}{annotation_note}</p>'
        f'{canvas}'
        f'<ul class="ve-flow-edges visually-hidden">{"".join(hidden_items)}</ul>'
        f'<ul class="ve-flow-notes">{"".join(notes)}</ul>'
        f'</figure>'
    )

    style_assets = [a for a in definition.assets if a.slot == "styles"]
    manifest = RenderManifest(
        component_id=definition.id,
        component_version=definition.version,
        instance_id=ir.id,
        consumed_semantic_ids=ir.semantic_ids(),
        generated_relationship_ids=tuple(e.id for e in flow.edges),
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
