"""Static, accessible renderer for the semantic ``evidence-map`` component.

Claim-support mapping with certainty-derived link styles and monochrome badges.
"""
from __future__ import annotations

import html

from ..model import CanonicalSection, RenderManifest, RenderResult

_CERT_LABEL = {"confirmed": "確定", "inferred": "推定", "unverified": "未確認"}
_LINK_CLASS = {"confirmed": "ve-em-link-confirmed", "inferred": "ve-em-link-inferred", "unverified": "ve-em-link-unverified"}


def _esc(value: str) -> str:
    return html.escape(str(value))


def render_evidence_map(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    em = ir.evidence_map
    assert em is not None
    takeaway = set(ir.takeaway_target_ids)
    emphasis_by_id = {e.target_id: e.label for e in ir.emphasis}
    cert_by_id = {c.id: c for c in ir.certainty}

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"
    conclusion = em.conclusion

    takeaway_cls = " ve-takeaway-target" if conclusion.id in takeaway else ""
    takeaway_attr = ' data-ve-takeaway="true"' if conclusion.id in takeaway else ""
    conclusion_emphasis = (
        f'<span class="ve-emphasis">{_esc(emphasis_by_id[conclusion.id])}</span>'
        if conclusion.id in emphasis_by_id else ""
    )
    conclusion_html = (
        f'<div class="ve-em-conclusion ve-em-border-strong{takeaway_cls}"'
        f' data-ve-semantic-id="{_esc(conclusion.id)}"{takeaway_attr}>'
        f'<span class="ve-em-conclusion-label">{_esc(conclusion.label)}</span>'
        f'{conclusion_emphasis}</div>'
    )

    evidence_blocks: list[str] = []
    for item in em.evidence:
        cert = cert_by_id[item.certainty_ref]
        link_cls = _LINK_CLASS.get(cert.level, "ve-em-link-unverified")
        takeaway_cls = " ve-takeaway-target" if item.id in takeaway else ""
        takeaway_attr = ' data-ve-takeaway="true"' if item.id in takeaway else ""
        source_attr = (
            f' data-ve-source-ref="{_esc(item.source_ref)}"'
            if item.source_ref else ""
        )
        emphasis_html = (
            f'<span class="ve-emphasis">{_esc(emphasis_by_id[item.id])}</span>'
            if item.id in emphasis_by_id else ""
        )
        evidence_blocks.append(
            f'<span class="ve-em-link {link_cls}" aria-hidden="true"></span>'
            f'<div class="ve-em-evidence-card{takeaway_cls}"'
            f' data-ve-semantic-id="{_esc(item.id)}"'
            f' data-ve-certainty-ref="{_esc(item.certainty_ref)}"{source_attr}{takeaway_attr}>'
            f'<span class="ve-cert ve-cert-{_esc(cert.level)}">{_esc(_CERT_LABEL.get(cert.level, cert.level))}</span>'
            f'<span class="ve-em-evidence-label">{_esc(item.label)}</span>'
            f'{emphasis_html}</div>'
        )

    map_html = (
        f'<div class="ve-em-layout ve-em-count-{len(em.evidence)}">'
        f'{conclusion_html}'
        f'<div class="ve-em-evidence-list">{"".join(evidence_blocks)}</div>'
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
        f'<figure data-ve-component="evidence-map" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-evidence-map-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-evidence-map-summary">'
        f'{_esc(ir.accessibility.summary)}{annotation_note}</p>'
        f'{map_html}'
        f'<ul class="ve-evidence-map-notes">{"".join(notes)}</ul>'
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
