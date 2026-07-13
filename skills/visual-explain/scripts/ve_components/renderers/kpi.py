"""Static, accessible renderer for the semantic ``kpi`` component."""
from __future__ import annotations

import html

from ..model import CanonicalSection, RenderManifest, RenderResult

from ..model import CERTAINTY_LABEL as _CERT_LABEL


def _esc(value: str) -> str:
    return html.escape(str(value))


def render_kpi(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    kpi = ir.kpi
    assert kpi is not None

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"

    items: list[str] = []
    for item in kpi.items:
        unit_html = f"<small>{_esc(item.unit)}</small>" if item.unit else ""
        items.append(
            f'<div class="ve-kpi-item" data-ve-semantic-id="{_esc(item.id)}">'
            f'<div class="ve-kpi-ring"><span class="ve-kpi-num">{_esc(item.value)}{unit_html}</span></div>'
            f'<p class="ve-kpi-cap">{_esc(item.caption)}</p></div>'
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

    markup = (
        f'<figure data-ve-component="kpi" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-kpi-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-kpi-summary">{_esc(ir.accessibility.summary)}</p>'
        f'<div class="ve-kpi-list">{"".join(items)}</div>'
        f'<ul class="ve-kpi-notes">{"".join(notes)}</ul>'
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
