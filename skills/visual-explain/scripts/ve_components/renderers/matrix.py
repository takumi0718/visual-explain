"""Static, accessible renderer for the semantic ``matrix`` component.

Two-axis classification and intersection comparison only. Supports dense
semantic tables and concept grids with short cell labels. Produces a visible
caption and summary, header cells carrying stable data-ve-semantic-id, body
cells carrying data-ve-row-id/data-ve-column-id, and visible certainty/source
references. All authored text is escaped. No scripts, no inline styles, no
external references; the DOM order matches the declared rows and columns exactly.
"""
from __future__ import annotations

import html

from ..model import CanonicalSection, RenderManifest, RenderResult

from ..model import CERTAINTY_LABEL as _CERT_LABEL


def _esc(value: str) -> str:
    return html.escape(str(value))


def _cell_refs_html(cell, cert_by_id, src_by_id) -> str:
    refs = []
    if cell.certainty_ref and cell.certainty_ref in cert_by_id:
        level = cert_by_id[cell.certainty_ref].level
        refs.append(
            f'<span class="ve-cert ve-cert-{_esc(level)}" data-ve-ref="{_esc(cell.certainty_ref)}">'
            f'{_esc(_CERT_LABEL.get(level, level))}</span>'
        )
    if cell.source_ref and cell.source_ref in src_by_id:
        refs.append(
            f'<span class="ve-src" data-ve-ref="{_esc(cell.source_ref)}">'
            f'{_esc(src_by_id[cell.source_ref].label)}</span>'
        )
    return f'<span class="ve-matrix-refs">{"".join(refs)}</span>' if refs else ""


def _render_dense_table(matrix, cert_by_id, src_by_id, cell_by_key, takeaway, emphasis_by_id, highlight_id):
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
                cells.append(
                    f'<td data-ve-row-id="{_esc(row.id)}" data-ve-column-id="{_esc(col.id)}"'
                    f' aria-label="該当なし">—</td>'
                )
                continue
            refs_html = _cell_refs_html(cell, cert_by_id, src_by_id)
            classes = []
            if cell.id in takeaway:
                classes.append("ve-takeaway-target")
            if cell.id == highlight_id:
                classes.append("ve-dg-highlight")
            cls_attr = f' class="{" ".join(classes)}"' if classes else ""
            takeaway_attr = ' data-ve-takeaway="true"' if cell.id in takeaway else ""
            emphasis_html = (
                f'<span class="ve-emphasis">{_esc(emphasis_by_id[cell.id])}</span>'
                if cell.id in emphasis_by_id else ""
            )
            cells.append(
                f'<td{cls_attr} data-ve-semantic-id="{_esc(cell.id)}" data-ve-row-id="{_esc(row.id)}"'
                f' data-ve-column-id="{_esc(col.id)}"{takeaway_attr}>{_esc(cell.content)}'
                f'{emphasis_html}{refs_html}</td>'
            )
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        f'<div class="ve-matrix-scroll">'
        f'<table><thead><tr><td class="ve-matrix-corner" aria-hidden="true"></td>{head_cells}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody></table></div>'
    )


def _render_concept_grid(matrix, cert_by_id, src_by_id, cell_by_key, takeaway, emphasis_by_id, highlight_id):
    ncol = len(matrix.columns)
    grid_classes = f"ve-mx-grid ve-mx-cols-{ncol}"
    parts = ['<div class="ve-matrix-corner" aria-hidden="true"></div>']
    for col in matrix.columns:
        parts.append(
            f'<div class="ve-mx-colhead" data-ve-semantic-id="{_esc(col.id)}">{_esc(col.label)}</div>'
        )
    hidden_relations: list[str] = []
    for row in matrix.rows:
        parts.append(
            f'<div class="ve-mx-rowhead" data-ve-semantic-id="{_esc(row.id)}">{_esc(row.label)}</div>'
        )
        for col in matrix.columns:
            cell = cell_by_key.get((row.id, col.id))
            if cell is None:
                parts.append(
                    f'<div class="ve-mx-cell" data-ve-row-id="{_esc(row.id)}"'
                    f' data-ve-column-id="{_esc(col.id)}" aria-label="該当なし">—</div>'
                )
                continue
            classes = ["ve-mx-cell"]
            if cell.id in takeaway:
                classes.append("ve-takeaway-target")
            if cell.id == highlight_id:
                classes.append("ve-dg-highlight")
            takeaway_attr = ' data-ve-takeaway="true"' if cell.id in takeaway else ""
            emphasis_html = (
                f'<span class="ve-emphasis">{_esc(emphasis_by_id[cell.id])}</span>'
                if cell.id in emphasis_by_id else ""
            )
            refs_html = _cell_refs_html(cell, cert_by_id, src_by_id)
            parts.append(
                f'<div class="{" ".join(classes)}" data-ve-semantic-id="{_esc(cell.id)}"'
                f' data-ve-row-id="{_esc(row.id)}" data-ve-column-id="{_esc(col.id)}"{takeaway_attr}>'
                f'{_esc(cell.content)}{emphasis_html}{refs_html}</div>'
            )
            hidden_relations.append(
                f'<li data-ve-semantic-id="{_esc(cell.id)}" data-ve-row-id="{_esc(row.id)}"'
                f' data-ve-column-id="{_esc(col.id)}">{_esc(row.label)} × {_esc(col.label)}: '
                f'{_esc(cell.content)}</li>'
            )
    hidden = (
        f'<ul class="ve-matrix-relations visually-hidden">{"".join(hidden_relations)}</ul>'
        if hidden_relations else ""
    )
    return f'<div class="{grid_classes}">{"".join(parts)}</div>{hidden}'


def render_matrix(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    matrix = ir.matrix
    assert matrix is not None
    cert_by_id = {c.id: c for c in ir.certainty}
    src_by_id = {s.id: s for s in ir.sources}
    cell_by_key = {(c.row_id, c.column_id): c for c in matrix.cells}
    takeaway = set(ir.takeaway_target_ids)
    emphasis_by_id = {e.target_id: e.label for e in ir.emphasis}
    highlight_id = matrix.highlight_id

    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"

    if matrix.presentation == "concept":
        body = _render_concept_grid(
            matrix, cert_by_id, src_by_id, cell_by_key, takeaway, emphasis_by_id, highlight_id,
        )
    else:
        body = _render_dense_table(
            matrix, cert_by_id, src_by_id, cell_by_key, takeaway, emphasis_by_id, highlight_id,
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
            f'<li data-ve-semantic-id="{_esc(src.id)}"><strong>出典 {_esc(src.label)}</strong>{detail}</li>'
        )

    annotation_note = ""
    if emphasis_by_id:
        joined = "、".join(f"注釈: {_esc(label)}" for label in emphasis_by_id.values())
        annotation_note = f" {joined}"

    markup = (
        f'<figure data-ve-component="matrix" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-matrix-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-matrix-summary">{_esc(ir.accessibility.summary)}{annotation_note}</p>'
        f'{body}'
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
