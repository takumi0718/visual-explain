"""Static, accessible renderer for the semantic ``logic-tree`` component.

Hierarchical decomposition with root left and branches right. Produces nested
elbow connectors (flex + border, no flow attributes).
"""
from __future__ import annotations

import html

from ..model import CanonicalSection, RenderManifest, RenderResult

from ..model import CERTAINTY_LABEL as _CERT_LABEL


def _esc(value: str) -> str:
    return html.escape(str(value))


def _node_markup(
    *,
    kind: str,
    node_id: str,
    label: str,
    takeaway: set[str],
    emphasis_by_id: dict[str, str],
) -> str:
    cls_parts = ["ve-lt-node", f"ve-lt-{kind}"]
    if node_id in takeaway:
        cls_parts.append("ve-takeaway-target")
    takeaway_attr = f' data-ve-semantic-id="{_esc(node_id)}"'
    takeaway_attr += ' data-ve-takeaway="true"' if node_id in takeaway else ""
    emphasis = (
        f'<span class="ve-emphasis">{_esc(emphasis_by_id[node_id])}</span>'
        if node_id in emphasis_by_id else ""
    )
    return (
        f'<div class="{" ".join(cls_parts)}"{takeaway_attr}>'
        f'{_esc(label)}{emphasis}</div>'
    )


def _render_leaf(
    leaf,
    *,
    takeaway: set[str],
    emphasis_by_id: dict[str, str],
) -> str:
    node = _node_markup(
        kind="leaf",
        node_id=leaf.id,
        label=leaf.text,
        takeaway=takeaway,
        emphasis_by_id=emphasis_by_id,
    )
    return f'<div class="ve-lt-child">{node}</div>'


def _render_branch(
    branch,
    *,
    takeaway: set[str],
    emphasis_by_id: dict[str, str],
) -> str:
    node = _node_markup(
        kind="branch",
        node_id=branch.id,
        label=branch.label,
        takeaway=takeaway,
        emphasis_by_id=emphasis_by_id,
    )
    if not branch.leaves:
        return f'<div class="ve-lt-child">{node}</div>'
    leaf_blocks = [
        _render_leaf(leaf, takeaway=takeaway, emphasis_by_id=emphasis_by_id)
        for leaf in branch.leaves
    ]
    return (
        f'<div class="ve-lt-child">'
        f'{node}'
        f'<div class="ve-lt-stub"></div>'
        f'<div class="ve-lt-children">{"".join(leaf_blocks)}</div>'
        f'</div>'
    )


def render_logic_tree(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    logic_tree = ir.logic_tree
    assert logic_tree is not None
    takeaway = set(ir.takeaway_target_ids)
    emphasis_by_id = {e.target_id: e.label for e in ir.emphasis}

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"

    root = logic_tree.root
    root_markup = _node_markup(
        kind="root",
        node_id=root.id,
        label=root.label,
        takeaway=takeaway,
        emphasis_by_id=emphasis_by_id,
    )
    branch_blocks = [
        _render_branch(branch, takeaway=takeaway, emphasis_by_id=emphasis_by_id)
        for branch in logic_tree.branches
    ]
    tree_markup = (
        f'<div class="ve-lt">'
        f'{root_markup}'
        f'<div class="ve-lt-stub"></div>'
        f'<div class="ve-lt-children">{"".join(branch_blocks)}</div>'
        f'</div>'
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
        f'<figure data-ve-component="logic-tree" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-logic-tree-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-logic-tree-summary">{_esc(ir.accessibility.summary)}{annotation_note}</p>'
        f'{tree_markup}'
        f'<ul class="ve-logic-tree-notes">{"".join(notes)}</ul>'
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
