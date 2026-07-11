"""Static, accessible renderer for the semantic ``logic-tree`` component.

Hierarchical decomposition with root left and branches right. Renderer-owned
grid/border connectors (no flow relationship attributes).
"""
from __future__ import annotations

import html

from ..model import CanonicalSection, RenderManifest, RenderResult

_CERT_LABEL = {"confirmed": "確定", "inferred": "推定", "unverified": "未確認"}


def _esc(value: str) -> str:
    return html.escape(str(value))


def render_logic_tree(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    logic_tree = ir.logic_tree
    assert logic_tree is not None
    takeaway = set(ir.takeaway_target_ids)
    emphasis_by_id = {e.target_id: e.label for e in ir.emphasis}

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"
    count = len(logic_tree.branches)

    root = logic_tree.root
    root_cls = ["ve-logic-tree-root"]
    if root.id in takeaway:
        root_cls.append("ve-takeaway-target")
    root_takeaway = ' data-ve-takeaway="true"' if root.id in takeaway else ""
    root_emphasis = (
        f'<span class="ve-emphasis">{_esc(emphasis_by_id[root.id])}</span>'
        if root.id in emphasis_by_id else ""
    )
    root_markup = (
        f'<div class="{" ".join(root_cls)}" data-ve-semantic-id="{_esc(root.id)}"{root_takeaway}>'
        f'<span class="ve-logic-tree-root-label">{_esc(root.label)}</span>{root_emphasis}</div>'
    )

    branch_rows: list[str] = []
    for index, branch in enumerate(logic_tree.branches, start=1):
        cls_parts = ["ve-logic-tree-branch-row", f"ve-logic-tree-index-{index}"]
        branch_cls = ["ve-logic-tree-branch"]
        if branch.id in takeaway:
            branch_cls.append("ve-takeaway-target")
        branch_takeaway = ' data-ve-takeaway="true"' if branch.id in takeaway else ""
        branch_emphasis = (
            f'<span class="ve-emphasis">{_esc(emphasis_by_id[branch.id])}</span>'
            if branch.id in emphasis_by_id else ""
        )
        leaf_blocks: list[str] = []
        for leaf in branch.leaves:
            leaf_cls = ["ve-logic-tree-leaf"]
            if leaf.id in takeaway:
                leaf_cls.append("ve-takeaway-target")
            leaf_takeaway = ' data-ve-takeaway="true"' if leaf.id in takeaway else ""
            leaf_emphasis = (
                f'<span class="ve-emphasis">{_esc(emphasis_by_id[leaf.id])}</span>'
                if leaf.id in emphasis_by_id else ""
            )
            leaf_blocks.append(
                f'<li class="{" ".join(leaf_cls)}" data-ve-semantic-id="{_esc(leaf.id)}"{leaf_takeaway}>'
                f'<span class="ve-logic-tree-leaf-text">{_esc(leaf.text)}</span>{leaf_emphasis}</li>'
            )
        leaves_html = (
            f'<ul class="ve-logic-tree-leaves">{"".join(leaf_blocks)}</ul>'
            if leaf_blocks else ""
        )
        branch_rows.append(
            f'<li class="{" ".join(cls_parts)}">'
            f'<span class="ve-logic-tree-connector" aria-hidden="true"></span>'
            f'<div class="{" ".join(branch_cls)}" data-ve-semantic-id="{_esc(branch.id)}"{branch_takeaway}>'
            f'<span class="ve-logic-tree-branch-label">{_esc(branch.label)}</span>'
            f'{branch_emphasis}{leaves_html}</div></li>'
        )

    tree_markup = (
        f'<div class="ve-logic-tree-layout ve-logic-tree-layout-horizontal">'
        f'<div class="ve-logic-tree-root-cell">{root_markup}</div>'
        f'<ol class="ve-logic-tree-branches ve-logic-tree-count-{count}">'
        f'{"".join(branch_rows)}</ol></div>'
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
