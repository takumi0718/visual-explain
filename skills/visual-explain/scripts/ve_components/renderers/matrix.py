"""Static, accessible renderer for the semantic ``matrix`` component.

Two-axis classification and intersection comparison only. Produces a semantic
<figure>/<table> with a visible caption and summary, header cells carrying stable
data-ve-semantic-id, body cells carrying data-ve-row-id/data-ve-column-id, and
visible certainty/source references. All authored text is escaped. No scripts,
no inline styles, no external references; the DOM order matches the declared
rows and columns exactly.
"""
from __future__ import annotations

import html

from ..model import CanonicalSection, RenderManifest, RenderResult

_CERT_LABEL = {"confirmed": "確定", "inferred": "推定", "unverified": "未確認"}


def _esc(value: str) -> str:
    return html.escape(str(value))


def render_matrix(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    matrix = ir.matrix
    assert matrix is not None
    cert_by_id = {c.id: c for c in ir.certainty}
    src_by_id = {s.id: s for s in ir.sources}
    cell_by_key = {(c.row_id, c.column_id): c for c in matrix.cells}

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"

    head_cells = "".join(
        f'<th scope="col" data-ve-semantic-id="{_esc(col.id)}">{_esc(col.label)}</th>'
        for col in matrix.columns
    )
    body_rows = []
    for row in matrix.rows:
        cells = [f'<th scope="row" data-ve-semantic-id="{_esc(row.id)}">{_esc(row.label)}</th>']
        for col in matrix.columns:
            cell = cell_by_key.get((row.id, col.id))
            if cell is None:
                cells.append(f'<td data-ve-row-id="{_esc(row.id)}" data-ve-column-id="{_esc(col.id)}" aria-label="該当なし">—</td>')
                continue
            refs = []
            if cell.certainty_ref and cell.certainty_ref in cert_by_id:
                level = cert_by_id[cell.certainty_ref].level
                refs.append(f'<span class="ve-cert ve-cert-{_esc(level)}" data-ve-ref="{_esc(cell.certainty_ref)}">{_esc(_CERT_LABEL.get(level, level))}</span>')
            if cell.source_ref and cell.source_ref in src_by_id:
                refs.append(f'<span class="ve-src" data-ve-ref="{_esc(cell.source_ref)}">{_esc(src_by_id[cell.source_ref].label)}</span>')
            refs_html = f'<span class="ve-matrix-refs">{"".join(refs)}</span>' if refs else ""
            cells.append(
                f'<td data-ve-semantic-id="{_esc(cell.id)}" data-ve-row-id="{_esc(row.id)}"'
                f' data-ve-column-id="{_esc(col.id)}">{_esc(cell.content)}{refs_html}</td>'
            )
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    notes = []
    for cert in ir.certainty:
        notes.append(f'<li data-ve-semantic-id="{_esc(cert.id)}"><strong>{_esc(_CERT_LABEL.get(cert.level, cert.level))}:</strong> {_esc(cert.statement)}</li>')
    for src in ir.sources:
        detail = f"（{_esc(src.detail)}）" if src.detail else ""
        notes.append(f'<li data-ve-semantic-id="{_esc(src.id)}"><strong>出典 {_esc(src.label)}</strong>{detail}</li>')

    markup = (
        f'<figure data-ve-component="matrix" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-matrix-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-matrix-summary">{_esc(ir.accessibility.summary)}</p>'
        f'<div class="ve-matrix-scroll">'
        f'<table><thead><tr><td class="ve-matrix-corner"></td>{head_cells}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody></table></div>'
        f'<ul class="ve-matrix-notes">{"".join(notes)}</ul>'
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
