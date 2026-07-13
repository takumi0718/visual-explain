"""Static, accessible renderer for the semantic ``stairs`` component.

Staged maturity from low to high. Produces a semantic <figure> with caption,
summary, height-enumerated treads, highlight marker, and notes.
"""
from __future__ import annotations

import html

from ..model import CanonicalSection, RenderManifest, RenderResult

from ..model import CERTAINTY_LABEL as _CERT_LABEL


def _esc(value: str) -> str:
    return html.escape(str(value))


def render_stairs(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    stairs = ir.stairs
    assert stairs is not None
    takeaway = set(ir.takeaway_target_ids)
    emphasis_by_id = {e.target_id: e.label for e in ir.emphasis}

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"
    count = len(stairs.stages)
    highlight_id = stairs.highlight_id
    highlight_index: int | None = None
    if highlight_id is not None:
        for index, stage in enumerate(stairs.stages):
            if stage.id == highlight_id:
                highlight_index = index
                break

    blocks: list[str] = []
    for index, stage in enumerate(stairs.stages, start=1):
        cls_parts = ["ve-stairs-stage", f"ve-stairs-index-{index}"]
        if highlight_index is not None:
            if index - 1 < highlight_index:
                cls_parts.append("ve-stairs-done")
            elif index - 1 == highlight_index:
                cls_parts.append("ve-dg-highlight")
            else:
                cls_parts.append("ve-stairs-todo")
        if stage.id in takeaway:
            cls_parts.append("ve-takeaway-target")
        takeaway_attr = ' data-ve-takeaway="true"' if stage.id in takeaway else ""
        emphasis_html = (
            f'<span class="ve-emphasis">{_esc(emphasis_by_id[stage.id])}</span>'
            if stage.id in emphasis_by_id else ""
        )
        here_html = (
            '<span class="ve-stairs-here">← 現在地</span>'
            if stage.id == highlight_id else ""
        )
        blocks.append(
            f'<li class="{" ".join(cls_parts)}" data-ve-semantic-id="{_esc(stage.id)}"{takeaway_attr}>'
            f'<span class="ve-stairs-label">{_esc(stage.label)}</span>{here_html}{emphasis_html}</li>'
        )

    list_markup = (
        f'<ol class="ve-stairs-stages ve-stairs-count-{count}">'
        f'{"".join(blocks)}</ol>'
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
        f'<figure data-ve-component="stairs" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-stairs-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-stairs-summary">{_esc(ir.accessibility.summary)}{annotation_note}</p>'
        f'{list_markup}'
        f'<ul class="ve-stairs-notes">{"".join(notes)}</ul>'
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
