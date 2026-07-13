"""Static, accessible renderer for the semantic ``pyramid`` component.

Layered priority with apex-first tiers. Produces a semantic <figure> with
caption, summary, width-enumerated tier blocks, and certainty/source notes.
"""
from __future__ import annotations

import html

from ..model import CanonicalSection, RenderManifest, RenderResult

from ..model import CERTAINTY_LABEL as _CERT_LABEL


def _esc(value: str) -> str:
    return html.escape(str(value))


def render_pyramid(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    pyramid = ir.pyramid
    assert pyramid is not None
    takeaway = set(ir.takeaway_target_ids)
    emphasis_by_id = {e.target_id: e.label for e in ir.emphasis}

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"
    count = len(pyramid.tiers)

    blocks: list[str] = []
    for index, tier in enumerate(pyramid.tiers, start=1):
        cls_parts = ["ve-pyramid-tier", f"ve-pyramid-index-{index}"]
        if index == 1:
            cls_parts.append("ve-pyramid-face-strong")
        else:
            cls_parts.append("ve-pyramid-face-dim")
        if tier.id in takeaway:
            cls_parts.append("ve-takeaway-target")
        takeaway_attr = ' data-ve-takeaway="true"' if tier.id in takeaway else ""
        emphasis_html = (
            f'<span class="ve-emphasis">{_esc(emphasis_by_id[tier.id])}</span>'
            if tier.id in emphasis_by_id else ""
        )
        sub_html = f'<span class="ve-pyramid-sub">{_esc(tier.sub)}</span>' if tier.sub else ""
        blocks.append(
            f'<li class="{" ".join(cls_parts)}" data-ve-semantic-id="{_esc(tier.id)}"{takeaway_attr}>'
            f'<span class="ve-pyramid-label">{_esc(tier.label)}</span>{sub_html}{emphasis_html}</li>'
        )

    list_markup = (
        f'<ul class="ve-pyramid-tiers ve-pyramid-count-{count}">'
        f'{"".join(blocks)}</ul>'
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
        f'<figure data-ve-component="pyramid" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-pyramid-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-pyramid-summary">{_esc(ir.accessibility.summary)}{annotation_note}</p>'
        f'{list_markup}'
        f'<ul class="ve-pyramid-notes">{"".join(notes)}</ul>'
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
