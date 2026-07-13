"""Static, accessible renderer for the semantic ``enumeration`` component.

Parallel itemization without implied order. Produces a semantic <figure> with
caption, summary, numbered or labeled blocks per item, and certainty/source
notes. Numbers are assigned by the renderer (1..n), never authored in IR.
"""
from __future__ import annotations

import html

from ..model import CanonicalSection, RenderManifest, RenderResult

from ..model import CERTAINTY_LABEL as _CERT_LABEL


def _esc(value: str) -> str:
    return html.escape(str(value))


def _desc_html(text: str, emphasis: str | None) -> str:
    escaped = _esc(text)
    if emphasis:
        needle = _esc(emphasis)
        escaped = escaped.replace(needle, f'<strong class="dg-em">{needle}</strong>', 1)
    return escaped


def _description_html(lines: tuple[str, ...], emphasis: str | None) -> str:
    emphasis_used = False
    parts: list[str] = []
    for line in lines:
        line_emphasis: str | None = None
        if emphasis and not emphasis_used and emphasis in line:
            line_emphasis = emphasis
            emphasis_used = True
        parts.append(
            f'<p class="ve-enum-description ve-enum-desc">'
            f'{_desc_html(line, line_emphasis)}</p>'
        )
    return "".join(parts)


def render_enumeration(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    enumeration = ir.enumeration
    assert enumeration is not None
    takeaway = set(ir.takeaway_target_ids)
    emphasis_by_id = {e.target_id: e.label for e in ir.emphasis}

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"

    blocks: list[str] = []
    for index, item in enumerate(enumeration.items, start=1):
        concept_classes = ["ve-enum-concept", "ve-enum-box"]
        if item.id in takeaway:
            concept_classes.append("ve-takeaway-target")
        takeaway_attr = ' data-ve-takeaway="true"' if item.id in takeaway else ""
        emphasis_html = (
            f'<span class="ve-emphasis">{_esc(emphasis_by_id[item.id])}</span>'
            if item.id in emphasis_by_id else ""
        )
        if enumeration.block_content == "label":
            heading = f'<span class="ve-enum-label">{_esc(item.label or "")}</span>'
        else:
            heading = f'<span class="ve-enum-number" aria-hidden="true">{index}</span>'
            if item.title:
                heading += f'<span class="ve-enum-title">{_esc(item.title)}</span>'
        concept_html = f'<div class="{" ".join(concept_classes)}">{heading}</div>'
        description_html = ""
        if item.description:
            description_html = _description_html(
                item.description,
                item.description_emphasis,
            )
        blocks.append(
            f'<li class="ve-enum-block" data-ve-semantic-id="{_esc(item.id)}"{takeaway_attr}>'
            f'{concept_html}{description_html}{emphasis_html}</li>'
        )

    layout_classes = ["ve-enum-items"]
    if enumeration.presentation == "columns":
        layout_classes.append("ve-enum-columns")
    if enumeration.items and enumeration.items[0].description:
        layout_classes.append("ve-enum-has-description")
    list_markup = f'<ul class="{" ".join(layout_classes)}">{"".join(blocks)}</ul>'

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
        f'<figure data-ve-component="enumeration" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-enumeration-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-enumeration-summary">{_esc(ir.accessibility.summary)}{annotation_note}</p>'
        f'{list_markup}'
        f'<ul class="ve-enumeration-notes">{"".join(notes)}</ul>'
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
