"""Static, accessible renderer for the semantic ``chevron`` component.

Linear ordered sequence with optional closed-loop return rail. Produces a
semantic <figure> with caption, summary, numbered or labeled steps, optional
loop rail (vertical only), and certainty/source notes.
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
    items: list[str] = []
    for line in lines:
        line_emphasis: str | None = None
        if emphasis and not emphasis_used and emphasis in line:
            line_emphasis = emphasis
            emphasis_used = True
        items.append(f"<li>{_desc_html(line, line_emphasis)}</li>")
    return f'<ul class="ve-chevron-description">{"".join(items)}</ul>'


def _step_endpoint_name(step, index: int) -> str:
    """Accessible loop endpoint: label, then title, then renderer ordinal."""
    if step.label and str(step.label).strip():
        return str(step.label).strip()
    if step.title and str(step.title).strip():
        return str(step.title).strip()
    return f"ステップ {index}"


def render_chevron(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    chevron = ir.chevron
    assert chevron is not None
    takeaway = set(ir.takeaway_target_ids)
    emphasis_by_id = {e.target_id: e.label for e in ir.emphasis}

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"

    blocks: list[str] = []
    for index, step in enumerate(chevron.steps, start=1):
        concept_classes = ["ve-chevron-concept", "ve-chv-box"]
        if step.id in takeaway:
            concept_classes.append("ve-takeaway-target")
        takeaway_attr = ' data-ve-takeaway="true"' if step.id in takeaway else ""
        emphasis_html = (
            f'<span class="ve-emphasis">{_esc(emphasis_by_id[step.id])}</span>'
            if step.id in emphasis_by_id else ""
        )
        if chevron.block_content == "label":
            heading = f'<span class="ve-chevron-label">{_esc(step.label or "")}</span>'
        else:
            heading = f'<span class="ve-chevron-number" aria-hidden="true">{index}</span>'
            if step.title:
                heading += f'<span class="ve-chevron-title">{_esc(step.title)}</span>'
        concept_html = f'<div class="{" ".join(concept_classes)}">{heading}</div>'
        description_html = ""
        if step.description:
            description_html = _description_html(
                step.description,
                step.description_emphasis,
            )
        blocks.append(
            f'<li class="ve-chevron-step" data-ve-semantic-id="{_esc(step.id)}"{takeaway_attr}>'
            f'{concept_html}{description_html}{emphasis_html}</li>'
        )

    layout_classes = ["ve-chevron-steps"]
    if chevron.orientation == "horizontal":
        layout_classes.append("ve-chevron-horizontal")
    else:
        layout_classes.append("ve-chevron-centered")
    if chevron.steps and chevron.steps[0].description:
        layout_classes.append("ve-chevron-has-description")
    list_markup = f'<ol class="{" ".join(layout_classes)}">{"".join(blocks)}</ol>'

    loop_rail = ""
    loop_tail = ""
    loop_sentence = ""
    body_inner = list_markup
    if chevron.loop and chevron.orientation == "vertical":
        loop_rail = '<div class="ve-chevron-loop-rail" aria-hidden="true"></div>'
        loop_tail = '<div class="ve-chevron-loop-tail" aria-hidden="true"></div>'
        last_name = _step_endpoint_name(chevron.steps[-1], len(chevron.steps))
        first_name = _step_endpoint_name(chevron.steps[0], 1)
        loop_sentence = (
            f'<ul class="ve-chevron-loop-sentence visually-hidden">'
            f'<li>最終段〈{_esc(last_name)}〉から先頭段〈{_esc(first_name)}〉へ戻る</li>'
            f'</ul>'
        )
        body_inner = (
            f'<div data-ve-loop="true">{loop_rail}{loop_tail}{list_markup}{loop_sentence}</div>'
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
        f'<figure data-ve-component="chevron" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-chevron-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-chevron-summary">{_esc(ir.accessibility.summary)}{annotation_note}</p>'
        f'<div class="ve-chevron-body">{body_inner}</div>'
        f'<ul class="ve-chevron-notes">{"".join(notes)}</ul>'
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
