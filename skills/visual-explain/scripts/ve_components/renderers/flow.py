"""Static, accessible renderer for the semantic ``flow`` component.

Explicit order, directed transition, and branch relationships only. Produces a
semantic <figure> with a visible caption/summary, an ordered node list, and a
visible edge list where every edge exposes data-ve-from/-to/-relation, a visible
direction indicator, and its semantic ID. All nodes and edges are present
without scripts; nothing requires interaction to reveal core relationships. The
reading order is deterministic and never reversed.
"""
from __future__ import annotations

import html

from ..model import CanonicalSection, RenderManifest, RenderResult

_CERT_LABEL = {"confirmed": "確定", "inferred": "推定", "unverified": "未確認"}
_RELATION_LABEL = {
    "ordered-transition": "順序遷移",
    "directed-transition": "有向遷移",
    "branching": "分岐",
}


def _esc(value: str) -> str:
    return html.escape(str(value))


def render_flow(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    flow = ir.flow
    assert flow is not None
    node_by_id = {n.id: n for n in flow.nodes}

    reading_order = list(flow.reading_order) if flow.reading_order else [n.id for n in flow.nodes]
    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"

    def node_li(nid: str) -> str:
        return (f'<li data-ve-semantic-id="{_esc(nid)}" data-ve-node-id="{_esc(nid)}">'
                f'{_esc(node_by_id[nid].label)}</li>')

    if flow.groups:
        # Emit the global reading order verbatim; contiguous runs of the same
        # group become a labelled group block. Validation guarantees each group's
        # nodes are contiguous, so a group appears exactly once and the declared
        # reading order is never reordered by group declaration order.
        group_label = {g.id: g.label for g in flow.groups}
        ordered = [nid for nid in reading_order if nid in node_by_id]
        blocks: list[str] = []
        i = 0
        while i < len(ordered):
            group_id = node_by_id[ordered[i]].group
            run: list[str] = []
            while i < len(ordered) and node_by_id[ordered[i]].group == group_id:
                run.append(ordered[i])
                i += 1
            inner = "".join(node_li(nid) for nid in run)
            if group_id is None:
                blocks.append(inner)
            else:
                blocks.append(
                    f'<li class="ve-flow-group" data-ve-semantic-id="{_esc(group_id)}">'
                    f'<span class="ve-flow-group-label">{_esc(group_label.get(group_id, group_id))}</span>'
                    f'<ol class="ve-flow-group-nodes">{inner}</ol></li>'
                )
        nodes_block = f'<ol class="ve-flow-nodes ve-flow-grouped">{"".join(blocks)}</ol>'
    else:
        node_items = "".join(node_li(nid) for nid in reading_order if nid in node_by_id)
        nodes_block = f'<ol class="ve-flow-nodes">{node_items}</ol>'

    edge_items = []
    for edge in flow.edges:
        source = node_by_id.get(edge.source)
        target = node_by_id.get(edge.target)
        source_label = _esc(source.label) if source else _esc(edge.source)
        target_label = _esc(target.label) if target else _esc(edge.target)
        relation = _RELATION_LABEL.get(edge.relation, edge.relation)
        label = f'<span class="ve-flow-edge-label">: {_esc(edge.label)}</span>' if edge.label else ""
        edge_items.append(
            f'<li data-ve-semantic-id="{_esc(edge.id)}" data-ve-from="{_esc(edge.source)}"'
            f' data-ve-to="{_esc(edge.target)}" data-ve-relation="{_esc(edge.relation)}">'
            f'{source_label}<span class="ve-flow-arrow" aria-hidden="true">→</span>{target_label}'
            f'<span class="ve-flow-rel">（{_esc(relation)}）</span>{label}'
            f'<span class="visually-hidden">{source_label} から {target_label} への{_esc(relation)}</span></li>'
        )

    notes = []
    for cert in ir.certainty:
        notes.append(f'<li data-ve-semantic-id="{_esc(cert.id)}"><strong>{_esc(_CERT_LABEL.get(cert.level, cert.level))}:</strong> {_esc(cert.statement)}</li>')
    for src in ir.sources:
        detail = f"（{_esc(src.detail)}）" if src.detail else ""
        notes.append(f'<li data-ve-semantic-id="{_esc(src.id)}"><strong>出典 {_esc(src.label)}</strong>{detail}</li>')

    markup = (
        f'<figure data-ve-component="flow" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-flow-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-flow-summary">{_esc(ir.accessibility.summary)}</p>'
        f'{nodes_block}'
        f'<ul class="ve-flow-edges">{"".join(edge_items)}</ul>'
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
    )
