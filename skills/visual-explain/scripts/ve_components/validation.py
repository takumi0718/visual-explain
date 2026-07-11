"""Strict, standard-library validation of assembly requests and canonical IR.

Parsing turns raw JSON into typed model values only after rejecting
booleans-as-integers, unknown fields, blank IDs, duplicate IDs, bad references,
absent common slots, and renderer-shaped authoring fields. Relationship
direction and component choice are never inferred from prose.
"""
from __future__ import annotations

import json
from pathlib import Path

from .diagnostics import (
    DUPLICATE_SEMANTIC_ID,
    FORBIDDEN_AUTHORING_FIELD,
    INVALID_COMPATIBILITY_PROVENANCE,
    INVALID_COMPONENT_PAYLOAD,
    INVALID_FLOW_EDGE,
    INVALID_MATRIX_REFERENCE,
    INVALID_RELATIONSHIP_DECLARATION,
    MISSING_REQUIRED_SLOT,
    ContractError,
    DiagnosticCollector,
)
from .flow_layout import assign_rails, check_row_budget, check_topology, edge_spans, order_index
from .model import (
    AccessibilityInfo,
    AssemblyRequest,
    AxisEntry,
    CanonicalIR,
    CanonicalSection,
    CertaintyAssertion,
    CompatibilityProvenance,
    CompatibilitySection,
    DocumentMetadata,
    EmphasisAnnotation,
    ExplicitSelection,
    FlowEdge,
    FlowGroup,
    FlowNode,
    FlowPayload,
    MatrixCell,
    MatrixPayload,
    RelationshipDeclaration,
    Source,
)

_VOCAB_PATH = Path(__file__).resolve().parents[1].parent / "references" / "component-vocabulary.json"


def load_vocabulary() -> dict:
    return json.loads(_VOCAB_PATH.read_text("utf-8"))


VOCABULARY = load_vocabulary()
_COMPONENTS = VOCABULARY["components"]
_KIND_TO_COMPONENT = {c["relationshipKind"]: name for name, c in _COMPONENTS.items()}
_ALL_CAPABILITIES = {cap for c in _COMPONENTS.values() for cap in c["capabilities"]}
_COMPAT_SOURCES = set(VOCABULARY["compatibility"]["sources"])
_COMPAT_REASONS = set(VOCABULARY["compatibility"]["reasons"])

# Annotation limit constants (must stay in sync with component-ir.schema.json).
MAX_TAKEAWAY_TARGETS = 3
MAX_EMPHASIS_ITEMS = 3
MAX_EMPHASIS_LABEL_CHARS = 40

# Renderer / DOM / coordinate-shaped keys that must never appear in canonical IR.
FORBIDDEN_AUTHORING_KEYS = {
    "html", "markup", "innerhtml", "outerhtml", "template",
    "css", "style", "styles", "classname", "class",
    "script", "scripts", "js", "javascript", "onclick", "on",
    "x", "y", "z", "coord", "coords", "coordinate", "coordinates",
    "position", "top", "left", "right", "bottom", "width", "height",
    "dom", "svg", "path", "transform", "renderer",
}

_IR_KEYS = {
    "id", "relationship", "selection", "caption", "certainty", "sources", "accessibility", "matrix", "flow",
    "takeawayTargetIds", "takeawayScope", "emphasis",
}
_RELATIONSHIP_KEYS = {"kind", "capabilities"}
_SELECTION_KEYS = {"component", "version", "matchedCapabilities"}
_CERTAINTY_KEYS = {"id", "level", "statement"}
_SOURCE_KEYS = {"id", "label", "detail"}
_ACCESSIBILITY_KEYS = {"label", "summary"}
_AXIS_KEYS = {"id", "label"}
_CELL_KEYS = {"id", "rowId", "columnId", "content", "certaintyRef", "sourceRef"}
_MATRIX_KEYS = {"rows", "columns", "cells"}
_FLOW_KEYS = {"nodes", "edges", "groups", "startId", "readingOrder"}
_NODE_KEYS = {"id", "label", "group"}
_EDGE_KEYS = {"id", "from", "to", "relation", "label"}
_GROUP_KEYS = {"id", "label"}
_DOCUMENT_KEYS = {"id", "title", "summary"}
_ASSEMBLY_KEYS = {"schemaVersion", "document", "sections"}
_COMPAT_SECTION_KEYS = {"kind", "id", "markup", "provenance"}
_PROVENANCE_KEYS = {"source", "reason", "format"}
_CANONICAL_SECTION_KEYS = {"kind", "ir"}


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _nonblank_str(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _check_keys(obj: dict, allowed: set[str], path: str, col: DiagnosticCollector,
                payload_code: str = INVALID_COMPONENT_PAYLOAD) -> None:
    for key in obj:
        if key in allowed:
            continue
        if str(key).lower() in FORBIDDEN_AUTHORING_KEYS:
            col.add(FORBIDDEN_AUTHORING_FIELD, f"認可されない生成系フィールド '{key}'", path)
        else:
            col.add(payload_code, f"未知のフィールド '{key}'", path)


# ---------------------------------------------------------------------------
# Canonical IR
# ---------------------------------------------------------------------------


def validate_canonical_section(raw: object) -> CanonicalIR:
    col = DiagnosticCollector()
    ir = _validate_canonical_ir(raw, "ir", col)
    col.raise_if_any()
    assert ir is not None
    return ir


def _validate_canonical_ir(raw: object, path: str, col: DiagnosticCollector) -> CanonicalIR | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "canonical IR はオブジェクトである必要があります", path)
        return None

    _check_keys(raw, _IR_KEYS, path, col)

    # Required common slots.
    for slot in ("id", "caption", "certainty", "sources", "accessibility", "relationship", "selection"):
        if slot not in raw:
            col.add(MISSING_REQUIRED_SLOT, f"必須スロット '{slot}' がありません", path)

    section_id = raw.get("id")
    if "id" in raw and not _nonblank_str(section_id):
        col.add(INVALID_COMPONENT_PAYLOAD, "id は空にできません", path)

    caption = raw.get("caption")
    if "caption" in raw and not _nonblank_str(caption):
        col.add(MISSING_REQUIRED_SLOT, "caption は空にできません", path)

    relationship = _validate_relationship(raw.get("relationship"), f"{path}.relationship", col) if "relationship" in raw else None
    selection = _validate_selection(raw.get("selection"), f"{path}.selection", col) if "selection" in raw else None
    certainty = _validate_certainty(raw.get("certainty"), f"{path}.certainty", col) if "certainty" in raw else ()
    sources = _validate_sources(raw.get("sources"), f"{path}.sources", col) if "sources" in raw else ()
    accessibility = _validate_accessibility(raw.get("accessibility"), f"{path}.accessibility", col) if "accessibility" in raw else None

    matrix = None
    flow = None
    has_matrix = "matrix" in raw
    has_flow = "flow" in raw
    if has_matrix and has_flow:
        col.add(INVALID_COMPONENT_PAYLOAD, "matrix と flow を同時に指定できません", path)
    elif not has_matrix and not has_flow:
        col.add(INVALID_COMPONENT_PAYLOAD, "matrix か flow のいずれかのペイロードが必要です", path)
    elif has_matrix:
        matrix = _validate_matrix(raw.get("matrix"), f"{path}.matrix", col)
    else:
        acyclic = relationship is not None and "ordered-transition" in relationship.capabilities
        flow = _validate_flow(raw.get("flow"), f"{path}.flow", col, acyclic=acyclic)

    payload_kind = "matrix" if matrix is not None else "flow"
    cell_ids = {c.id for c in matrix.cells} if matrix is not None else set()
    node_ids = {n.id for n in flow.nodes} if flow is not None else set()
    edge_ids = {e.id for e in flow.edges} if flow is not None else set()
    takeaway_target_ids, takeaway_scope, emphasis = _validate_annotations(
        raw, path, col, caption, payload_kind, cell_ids, node_ids, edge_ids
    )

    # Cross-consistency: component choice must match the present payload and kind.
    if selection is not None:
        expected_component = "matrix" if has_matrix and not has_flow else ("flow" if has_flow and not has_matrix else None)
        if expected_component is not None and selection.component != expected_component:
            col.add(INVALID_COMPONENT_PAYLOAD,
                    f"selection.component '{selection.component}' がペイロード '{expected_component}' と一致しません", path)
        if relationship is not None and relationship.kind in _KIND_TO_COMPONENT:
            kind_component = _KIND_TO_COMPONENT[relationship.kind]
            if kind_component != selection.component:
                col.add(INVALID_RELATIONSHIP_DECLARATION,
                        f"relationship.kind '{relationship.kind}' が selection.component '{selection.component}' と矛盾します", path)

    _check_capability_scope(relationship, selection, col, path)
    _check_duplicate_ids(raw, path, col)

    if col:
        return None
    assert relationship and selection and accessibility is not None
    return CanonicalIR(
        id=section_id,
        relationship=relationship,
        selection=selection,
        caption=caption,
        certainty=certainty,
        sources=sources,
        accessibility=accessibility,
        matrix=matrix,
        flow=flow,
        takeaway_target_ids=takeaway_target_ids,
        takeaway_scope=takeaway_scope,
        emphasis=emphasis,
    )


def _validate_annotations(raw, path, col, caption, payload_kind, cell_ids, node_ids, edge_ids):
    # 注釈は opt-in: 3フィールドのいずれも無い既存 IR は無検査で通す（後方互換）。
    # いずれか1つでも指定されたら契約全体を検査する。
    if not ({"takeawayTargetIds", "takeawayScope", "emphasis"} & set(raw)):
        return (), "targets", ()
    scope = raw.get("takeawayScope", "targets")
    if scope not in ("targets", "whole"):
        col.add(INVALID_COMPONENT_PAYLOAD, f"takeawayScope '{scope}' は targets か whole のみ有効です", path)
    targets = raw.get("takeawayTargetIds", None)
    target_list = targets if isinstance(targets, list) else []
    if targets is not None and not isinstance(targets, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "takeawayTargetIds は配列が必要です", path)
    allowed = cell_ids if payload_kind == "matrix" else (node_ids | edge_ids)
    kind_label = "セル" if payload_kind == "matrix" else "ノード/エッジ"
    if scope == "targets" and len(target_list) == 0:
        col.add(INVALID_COMPONENT_PAYLOAD,
                "takeawayTargetIds が0件です (図全体が対象なら takeawayScope: \"whole\" を明示してください)", path)
    if scope == "whole" and target_list:
        col.add(INVALID_COMPONENT_PAYLOAD, "takeawayScope: whole と takeawayTargetIds は併用できません", path)
    if len(target_list) > MAX_TAKEAWAY_TARGETS:
        col.add(INVALID_COMPONENT_PAYLOAD, f"takeawayTargetIds は最大{MAX_TAKEAWAY_TARGETS}件です", path)
    seen: set[str] = set()
    for tid in target_list:
        if tid in seen:
            col.add(INVALID_COMPONENT_PAYLOAD, f"takeawayTargetIds '{tid}' が重複しています", path)
        seen.add(tid)
        if tid not in allowed:
            col.add(INVALID_COMPONENT_PAYLOAD, f"takeaway 対象 '{tid}' は {kind_label} ID ではありません", path)
    emphasis_raw = raw.get("emphasis", [])
    if not isinstance(emphasis_raw, list) or len(emphasis_raw) > MAX_EMPHASIS_ITEMS:
        col.add(INVALID_COMPONENT_PAYLOAD, f"emphasis は最大{MAX_EMPHASIS_ITEMS}件の配列が必要です", path)
        emphasis_raw = []
    result = []
    seen_emphasis: set[str] = set()
    for i, item in enumerate(emphasis_raw):
        if not isinstance(item, dict) or set(item) != {"targetId", "label"}:
            col.add(INVALID_COMPONENT_PAYLOAD, f"emphasis[{i}] は targetId と label のみを持つ必要があります", path)
            continue
        tid, label = item["targetId"], item["label"]
        if tid in seen_emphasis:
            col.add(INVALID_COMPONENT_PAYLOAD, f"emphasis 対象 '{tid}' が重複しています", path)
        seen_emphasis.add(tid)
        if tid not in allowed:
            col.add(INVALID_COMPONENT_PAYLOAD, f"emphasis 対象 '{tid}' は {kind_label} ID ではありません", path)
        if not isinstance(label, str) or not label.strip() or len(label) > MAX_EMPHASIS_LABEL_CHARS:
            col.add(INVALID_COMPONENT_PAYLOAD, f"emphasis[{i}].label は1〜{MAX_EMPHASIS_LABEL_CHARS}字が必要です", path)
        elif label == caption:
            col.add(INVALID_COMPONENT_PAYLOAD, "emphasis.label と caption の同文重複は禁止です", path)
        else:
            result.append(EmphasisAnnotation(target_id=str(tid), label=label))
    return tuple(str(t) for t in target_list), scope, tuple(result)


def _validate_relationship(raw: object, path: str, col: DiagnosticCollector) -> RelationshipDeclaration | None:
    if not isinstance(raw, dict):
        col.add(INVALID_RELATIONSHIP_DECLARATION, "relationship はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _RELATIONSHIP_KEYS, path, col, payload_code=INVALID_RELATIONSHIP_DECLARATION)
    kind = raw.get("kind")
    caps = raw.get("capabilities")
    if kind not in _KIND_TO_COMPONENT:
        col.add(INVALID_RELATIONSHIP_DECLARATION, f"未知の relationship.kind '{kind}'", path)
    if not isinstance(caps, list) or not caps:
        col.add(INVALID_RELATIONSHIP_DECLARATION, "capabilities は非空の配列である必要があります", path)
        caps = []
    clean: list[str] = []
    for cap in caps:
        if not isinstance(cap, str) or cap not in _ALL_CAPABILITIES:
            col.add(INVALID_RELATIONSHIP_DECLARATION, f"未知の capability '{cap}'", path)
        else:
            clean.append(cap)
    if kind not in _KIND_TO_COMPONENT:
        return None
    return RelationshipDeclaration(kind=kind, capabilities=tuple(clean))


def _validate_selection(raw: object, path: str, col: DiagnosticCollector) -> ExplicitSelection | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "selection はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _SELECTION_KEYS, path, col)
    component = raw.get("component")
    version = raw.get("version")
    matched = raw.get("matchedCapabilities")
    ok = True
    if component not in _COMPONENTS:
        col.add(INVALID_COMPONENT_PAYLOAD, f"未知のコンポーネント '{component}'", path)
        ok = False
    if not _is_int(version):
        col.add(INVALID_COMPONENT_PAYLOAD, "version は真偽値ではなく整数である必要があります", path)
        ok = False
    elif component in _COMPONENTS and version != _COMPONENTS[component]["contractVersion"]:
        col.add(INVALID_COMPONENT_PAYLOAD, f"未知のバージョン '{version}'", path)
        ok = False
    if not isinstance(matched, list) or not matched:
        col.add(INVALID_COMPONENT_PAYLOAD, "matchedCapabilities は非空の配列である必要があります", path)
        ok = False
        matched = []
    clean: list[str] = []
    for cap in matched:
        if not isinstance(cap, str) or cap not in _ALL_CAPABILITIES:
            col.add(INVALID_COMPONENT_PAYLOAD, f"未知の matchedCapability '{cap}'", path)
            ok = False
        else:
            clean.append(cap)
    if not ok or component not in _COMPONENTS or not _is_int(version):
        return None
    return ExplicitSelection(component=component, version=version, matched_capabilities=tuple(clean))


def _check_capability_scope(relationship: RelationshipDeclaration | None,
                            selection: ExplicitSelection | None,
                            col: DiagnosticCollector, path: str) -> None:
    if selection is None or selection.component not in _COMPONENTS:
        return
    allowed = set(_COMPONENTS[selection.component]["capabilities"])
    if relationship is not None:
        for cap in relationship.capabilities:
            if cap not in allowed:
                col.add(INVALID_RELATIONSHIP_DECLARATION,
                        f"capability '{cap}' は '{selection.component}' では宣言できません", path)
    declared = set(relationship.capabilities) if relationship else set()
    for cap in selection.matched_capabilities:
        if cap not in allowed:
            col.add(INVALID_COMPONENT_PAYLOAD, f"matchedCapability '{cap}' は '{selection.component}' では無効です", path)
        elif declared and cap not in declared:
            col.add(INVALID_COMPONENT_PAYLOAD, f"matchedCapability '{cap}' が relationship に宣言されていません", path)


def _validate_certainty(raw: object, path: str, col: DiagnosticCollector) -> tuple[CertaintyAssertion, ...]:
    if not isinstance(raw, list) or not raw:
        col.add(MISSING_REQUIRED_SLOT, "certainty は非空の配列である必要があります", path)
        return ()
    out: list[CertaintyAssertion] = []
    for i, item in enumerate(raw):
        p = f"{path}[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "certainty 要素はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _CERTAINTY_KEYS, p, col)
        if not _nonblank_str(item.get("id")):
            col.add(INVALID_COMPONENT_PAYLOAD, "certainty.id は空にできません", p)
        if item.get("level") not in {"confirmed", "inferred", "unverified"}:
            col.add(INVALID_COMPONENT_PAYLOAD, f"未知の certainty.level '{item.get('level')}'", p)
        if not _nonblank_str(item.get("statement")):
            col.add(MISSING_REQUIRED_SLOT, "certainty.statement は空にできません", p)
        out.append(CertaintyAssertion(id=item.get("id"), level=item.get("level"), statement=item.get("statement")))
    return tuple(out)


def _validate_sources(raw: object, path: str, col: DiagnosticCollector) -> tuple[Source, ...]:
    if not isinstance(raw, list) or not raw:
        col.add(MISSING_REQUIRED_SLOT, "sources は非空の配列である必要があります", path)
        return ()
    out: list[Source] = []
    for i, item in enumerate(raw):
        p = f"{path}[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "source 要素はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _SOURCE_KEYS, p, col)
        if not _nonblank_str(item.get("id")):
            col.add(INVALID_COMPONENT_PAYLOAD, "source.id は空にできません", p)
        if not _nonblank_str(item.get("label")):
            col.add(MISSING_REQUIRED_SLOT, "source.label は空にできません", p)
        detail = item.get("detail", "")
        if not isinstance(detail, str):
            col.add(INVALID_COMPONENT_PAYLOAD, "source.detail は文字列である必要があります", p)
            detail = ""
        out.append(Source(id=item.get("id"), label=item.get("label"), detail=detail))
    return tuple(out)


def _validate_accessibility(raw: object, path: str, col: DiagnosticCollector) -> AccessibilityInfo | None:
    if not isinstance(raw, dict):
        col.add(MISSING_REQUIRED_SLOT, "accessibility はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _ACCESSIBILITY_KEYS, path, col)
    if not _nonblank_str(raw.get("label")):
        col.add(MISSING_REQUIRED_SLOT, "accessibility.label は空にできません", path)
    if not _nonblank_str(raw.get("summary")):
        col.add(MISSING_REQUIRED_SLOT, "accessibility.summary は空にできません", path)
    return AccessibilityInfo(label=raw.get("label", ""), summary=raw.get("summary", ""))


def _validate_matrix(raw: object, path: str, col: DiagnosticCollector) -> MatrixPayload | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "matrix はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _MATRIX_KEYS, path, col)
    rows = _validate_axis(raw.get("rows"), f"{path}.rows", col)
    columns = _validate_axis(raw.get("columns"), f"{path}.columns", col)
    cells_raw = raw.get("cells")
    if not isinstance(cells_raw, list) or not cells_raw:
        col.add(INVALID_COMPONENT_PAYLOAD, "cells は非空の配列である必要があります", path)
        return None
    row_ids = {r.id for r in rows}
    col_ids = {c.id for c in columns}
    seen_intersections: set[tuple[str, str]] = set()
    cells: list[MatrixCell] = []
    for i, item in enumerate(cells_raw):
        p = f"{path}.cells[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "cell はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _CELL_KEYS, p, col)
        cid, rid, colid = item.get("id"), item.get("rowId"), item.get("columnId")
        if not _nonblank_str(item.get("content")):
            col.add(INVALID_COMPONENT_PAYLOAD, "cell.content は空にできません", p)
        if rid not in row_ids:
            col.add(INVALID_MATRIX_REFERENCE, f"cell.rowId '{rid}' が存在しません", p)
        if colid not in col_ids:
            col.add(INVALID_MATRIX_REFERENCE, f"cell.columnId '{colid}' が存在しません", p)
        if rid in row_ids and colid in col_ids:
            key = (rid, colid)
            if key in seen_intersections:
                col.add(INVALID_MATRIX_REFERENCE, f"交差 ({rid},{colid}) が重複しています", p)
            seen_intersections.add(key)
        cells.append(MatrixCell(
            id=cid, row_id=rid, column_id=colid, content=item.get("content"),
            certainty_ref=item.get("certaintyRef"), source_ref=item.get("sourceRef"),
        ))
    return MatrixPayload(rows=rows, columns=columns, cells=tuple(cells))


def _validate_axis(raw: object, path: str, col: DiagnosticCollector) -> tuple[AxisEntry, ...]:
    if not isinstance(raw, list) or not raw:
        col.add(INVALID_COMPONENT_PAYLOAD, "軸は非空の配列である必要があります", path)
        return ()
    out: list[AxisEntry] = []
    for i, item in enumerate(raw):
        p = f"{path}[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "軸要素はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _AXIS_KEYS, p, col)
        if not _nonblank_str(item.get("id")):
            col.add(INVALID_COMPONENT_PAYLOAD, "軸.id は空にできません", p)
        if not _nonblank_str(item.get("label")):
            col.add(INVALID_COMPONENT_PAYLOAD, "軸.label は空にできません", p)
        out.append(AxisEntry(id=item.get("id"), label=item.get("label")))
    return tuple(out)


def _validate_flow(raw: object, path: str, col: DiagnosticCollector, acyclic: bool = False) -> FlowPayload | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "flow はオブジェクトである必要があります", path)
        return None
    start_len = len(col.diagnostics)
    _check_keys(raw, _FLOW_KEYS, path, col)
    nodes_raw = raw.get("nodes")
    edges_raw = raw.get("edges")
    if not isinstance(nodes_raw, list) or not nodes_raw:
        col.add(INVALID_COMPONENT_PAYLOAD, "nodes は非空の配列である必要があります", path)
        nodes_raw = []
    nodes: list[FlowNode] = []
    node_ids: set[str] = set()
    for i, item in enumerate(nodes_raw):
        p = f"{path}.nodes[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "node はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _NODE_KEYS, p, col)
        if not _nonblank_str(item.get("id")):
            col.add(INVALID_COMPONENT_PAYLOAD, "node.id は空にできません", p)
        if not _nonblank_str(item.get("label")):
            col.add(INVALID_COMPONENT_PAYLOAD, "node.label は空にできません", p)
        node_ids.add(item.get("id"))
        nodes.append(FlowNode(id=item.get("id"), label=item.get("label"), group=item.get("group")))

    groups = _validate_groups(raw.get("groups"), f"{path}.groups", col) if "groups" in raw else ()
    group_ids = {g.id for g in groups}
    for node in nodes:
        if node.group is not None and node.group not in group_ids:
            col.add(INVALID_COMPONENT_PAYLOAD, f"node.group '{node.group}' が存在しません", path)

    if not isinstance(edges_raw, list) or not edges_raw:
        col.add(INVALID_COMPONENT_PAYLOAD, "edges は非空の配列である必要があります", path)
        edges_raw = []
    edges: list[FlowEdge] = []
    for i, item in enumerate(edges_raw):
        p = f"{path}.edges[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_FLOW_EDGE, "edge はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _EDGE_KEYS, p, col)
        eid, frm, to, rel = item.get("id"), item.get("from"), item.get("to"), item.get("relation")
        if not _nonblank_str(eid):
            col.add(INVALID_FLOW_EDGE, "edge.id は空にできません", p)
        if not _nonblank_str(frm):
            col.add(INVALID_FLOW_EDGE, "edge.from が必要です", p)
        elif frm not in node_ids:
            col.add(INVALID_FLOW_EDGE, f"edge.from '{frm}' が存在しません", p)
        if not _nonblank_str(to):
            col.add(INVALID_FLOW_EDGE, "edge.to が必要です", p)
        elif to not in node_ids:
            col.add(INVALID_FLOW_EDGE, f"edge.to '{to}' が存在しません", p)
        if _nonblank_str(frm) and frm == to:
            col.add(INVALID_FLOW_EDGE, "自己ループは許可されていません", p)
        if rel not in _ALL_CAPABILITIES:
            col.add(INVALID_FLOW_EDGE, f"未知の relation '{rel}'", p)
        edges.append(FlowEdge(id=eid, source=frm, target=to, relation=rel, label=item.get("label", "")))

    start_id = raw.get("startId")
    if start_id is not None and start_id not in node_ids:
        col.add(INVALID_COMPONENT_PAYLOAD, f"startId '{start_id}' が存在しません", path)
    # Absent readingOrder means "use the renderer's node-order fallback". An
    # explicitly present readingOrder (including []) is a claim about the order
    # and must be a unique permutation of exactly the declared node IDs — no
    # unknown, duplicate, or missing IDs — so the rendered order can never
    # silently drop, repeat, or reorder-away a node.
    has_reading_order = "readingOrder" in raw
    reading_order = raw.get("readingOrder", [])
    if has_reading_order and not isinstance(reading_order, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "readingOrder は配列である必要があります", path)
        reading_order = []
    elif has_reading_order:
        seen_order: set[str] = set()
        for rid in reading_order:
            if rid not in node_ids:
                col.add(INVALID_COMPONENT_PAYLOAD, f"readingOrder '{rid}' が存在しません", path)
            elif rid in seen_order:
                col.add(INVALID_COMPONENT_PAYLOAD, f"readingOrder '{rid}' が重複しています", path)
            seen_order.add(rid)
        missing = node_ids - seen_order
        if missing:
            col.add(INVALID_COMPONENT_PAYLOAD,
                    f"readingOrder に欠けているノードがあります: {sorted(missing)}", path)

    # Graph-integrity checks only when the structure is otherwise sound, so a
    # single dangling edge does not cascade into confusing reachability noise.
    if len(col.diagnostics) == start_len:
        _check_flow_integrity(node_ids, edges, start_id, list(reading_order), acyclic, path, col)
        if groups:
            order = list(reading_order) if reading_order else [n.id for n in nodes]
            _check_group_reading_order(nodes, order, path, col)

    # v1 drawable topology: forward-only edges, no self-loops/parallel edges,
    # bounded fan-out/fan-in, and skip edges must fit in the rail cap. Checked
    # unconditionally (independent of the block above) because check_topology
    # and edge_spans tolerate edges whose endpoints are unknown IDs (already
    # reported separately as invalid_flow_edge) by skipping them.
    topo = check_topology(nodes, edges, list(reading_order))
    for diag in topo:
        col.add(diag.code, diag.message, path)
    if not topo:
        index = order_index(nodes, list(reading_order))
        _, rail_diags = assign_rails(edge_spans(edges, index))
        for diag in rail_diags:
            col.add(diag.code, diag.message, path)
        budget_diags = check_row_budget(nodes, edges, list(reading_order))
        for diag in budget_diags:
            col.add(diag.code, diag.message, path)

    return FlowPayload(
        nodes=tuple(nodes), edges=tuple(edges), groups=groups,
        start_id=start_id, reading_order=tuple(reading_order),
    )


def _check_group_reading_order(nodes: list[FlowNode], order: list[str], path: str, col: DiagnosticCollector) -> None:
    """Each group's nodes must be contiguous in the reading order.

    The promoted flow contract renders groups as contiguous blocks. If the global
    reading order interleaves two groups, the grouped rendering cannot honor it
    without reordering, so such a combination is rejected rather than silently
    reordered. Ungrouped runs may repeat freely.
    """
    group_of = {n.id: n.group for n in nodes}
    unset = object()
    prev: object = unset
    closed: set[str] = set()
    for nid in order:
        group = group_of.get(nid)
        if group == prev:
            continue
        if isinstance(group, str) and group in closed:
            col.add(INVALID_COMPONENT_PAYLOAD,
                    f"group '{group}' のノードが readingOrder 上で不連続です (group と readingOrder が両立しません)", path)
            return
        if isinstance(prev, str):
            closed.add(prev)
        prev = group


def _check_flow_integrity(node_ids: set[str], edges: list[FlowEdge], start_id, reading_order: list[str],
                          acyclic: bool, path: str, col: DiagnosticCollector) -> None:
    adjacency: dict[str, list[str]] = {n: [] for n in node_ids}
    indegree: dict[str, int] = {n: 0 for n in node_ids}
    for edge in edges:
        adjacency[edge.source].append(edge.target)
        indegree[edge.target] += 1

    roots = [n for n in node_ids if indegree[n] == 0]
    origin = start_id or (roots[0] if len(roots) == 1 else (reading_order[0] if reading_order else None))
    if origin is None:
        col.add(INVALID_COMPONENT_PAYLOAD, "開始ノードが曖昧です (startId か readingOrder を指定してください)", path)
    else:
        seen: set[str] = set()
        stack = [origin]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(adjacency.get(node, []))
        unreachable = node_ids - seen
        if unreachable:
            col.add(INVALID_COMPONENT_PAYLOAD, f"到達不能なノードがあります: {sorted(unreachable)}", path)

    if acyclic and _has_cycle(node_ids, adjacency):
        col.add(INVALID_FLOW_EDGE, "順序関係 (ordered-transition) に循環があります", path)


def _has_cycle(node_ids: set[str], adjacency: dict[str, list[str]]) -> bool:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in node_ids}

    def visit(node: str) -> bool:
        color[node] = GRAY
        for nxt in adjacency.get(node, []):
            if color.get(nxt) == GRAY:
                return True
            if color.get(nxt) == WHITE and visit(nxt):
                return True
        color[node] = BLACK
        return False

    return any(color[n] == WHITE and visit(n) for n in node_ids)


def _validate_groups(raw: object, path: str, col: DiagnosticCollector) -> tuple[FlowGroup, ...]:
    if not isinstance(raw, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "groups は配列である必要があります", path)
        return ()
    out: list[FlowGroup] = []
    for i, item in enumerate(raw):
        p = f"{path}[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "group はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _GROUP_KEYS, p, col)
        if not _nonblank_str(item.get("id")):
            col.add(INVALID_COMPONENT_PAYLOAD, "group.id は空にできません", p)
        out.append(FlowGroup(id=item.get("id"), label=item.get("label", "")))
    return tuple(out)


def _check_duplicate_ids(raw: dict, path: str, col: DiagnosticCollector) -> None:
    ids: list[str] = []

    def collect(container: object, key: str = "id") -> None:
        if isinstance(container, list):
            for item in container:
                if isinstance(item, dict) and isinstance(item.get(key), str):
                    ids.append(item[key])

    if isinstance(raw.get("id"), str):
        ids.append(raw["id"])
    collect(raw.get("certainty"))
    collect(raw.get("sources"))
    matrix = raw.get("matrix")
    if isinstance(matrix, dict):
        collect(matrix.get("rows"))
        collect(matrix.get("columns"))
        collect(matrix.get("cells"))
    flow = raw.get("flow")
    if isinstance(flow, dict):
        collect(flow.get("nodes"))
        collect(flow.get("edges"))
        collect(flow.get("groups"))
    seen: set[str] = set()
    for value in ids:
        if value in seen:
            col.add(DUPLICATE_SEMANTIC_ID, f"意味 ID '{value}' が重複しています", path)
        seen.add(value)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def validate_assembly(raw: object) -> AssemblyRequest:
    col = DiagnosticCollector()
    if not isinstance(raw, dict):
        raise ContractError.single(INVALID_COMPONENT_PAYLOAD, "assembly はオブジェクトである必要があります", "assembly")
    _check_keys(raw, _ASSEMBLY_KEYS, "assembly", col)
    if raw.get("schemaVersion") != 1:
        col.add(INVALID_COMPONENT_PAYLOAD, f"未知の schemaVersion '{raw.get('schemaVersion')}'", "assembly")
    document = _validate_document(raw.get("document"), "assembly.document", col)
    sections_raw = raw.get("sections")
    sections: list[object] = []
    if not isinstance(sections_raw, list) or not sections_raw:
        col.add(MISSING_REQUIRED_SLOT, "sections は非空の配列である必要があります", "assembly")
        sections_raw = []
    seen_section_ids: set[str] = set()
    for i, item in enumerate(sections_raw):
        p = f"assembly.sections[{i}]"
        section = _validate_section(item, p, col, seen_section_ids)
        if section is not None:
            sections.append(section)
    col.raise_if_any()
    assert document is not None
    return AssemblyRequest(schema_version=1, document=document, sections=tuple(sections))


def _validate_document(raw: object, path: str, col: DiagnosticCollector) -> DocumentMetadata | None:
    if not isinstance(raw, dict):
        col.add(MISSING_REQUIRED_SLOT, "document はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _DOCUMENT_KEYS, path, col)
    for slot in ("id", "title", "summary"):
        if not _nonblank_str(raw.get(slot)):
            col.add(MISSING_REQUIRED_SLOT, f"document.{slot} は空にできません", path)
    return DocumentMetadata(id=raw.get("id", ""), title=raw.get("title", ""), summary=raw.get("summary", ""))


def _validate_section(raw: object, path: str, col: DiagnosticCollector, seen_ids: set[str]) -> object | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "section はオブジェクトである必要があります", path)
        return None
    kind = raw.get("kind")
    if kind == "canonical":
        _check_keys(raw, _CANONICAL_SECTION_KEYS, path, col)
        ir = _validate_canonical_ir(raw.get("ir"), f"{path}.ir", col)
        if ir is None:
            return None
        if ir.id in seen_ids:
            col.add(DUPLICATE_SEMANTIC_ID, f"section id '{ir.id}' が重複しています", path)
        seen_ids.add(ir.id)
        return CanonicalSection(ir=ir)
    if kind == "compatibility":
        return _validate_compatibility_section(raw, path, col, seen_ids)
    col.add(INVALID_COMPONENT_PAYLOAD, f"未知の section.kind '{kind}'", path)
    return None


def _validate_compatibility_section(raw: dict, path: str, col: DiagnosticCollector, seen_ids: set[str]):
    # Compatibility accepts only id, markup, and provenance. Any relationship,
    # selection, renderer, style, or script field is a provenance violation.
    for key in raw:
        if key not in _COMPAT_SECTION_KEYS:
            col.add(INVALID_COMPATIBILITY_PROVENANCE, f"compatibility に不正なフィールド '{key}'", path)
    sid = raw.get("id")
    if not _nonblank_str(sid):
        col.add(INVALID_COMPATIBILITY_PROVENANCE, "compatibility.id は空にできません", path)
    if not _nonblank_str(raw.get("markup")):
        col.add(INVALID_COMPATIBILITY_PROVENANCE, "compatibility.markup は空にできません", path)
    prov = raw.get("provenance")
    provenance = None
    if not isinstance(prov, dict):
        col.add(INVALID_COMPATIBILITY_PROVENANCE, "provenance はオブジェクトである必要があります", path)
    else:
        for key in prov:
            if key not in _PROVENANCE_KEYS:
                col.add(INVALID_COMPATIBILITY_PROVENANCE, f"provenance に不正なフィールド '{key}'", path)
        source = prov.get("source")
        reason = prov.get("reason")
        fmt = prov.get("format")
        if source not in _COMPAT_SOURCES:
            col.add(INVALID_COMPATIBILITY_PROVENANCE, f"未知の compatibility source '{source}'", path)
        if reason not in _COMPAT_REASONS:
            col.add(INVALID_COMPATIBILITY_PROVENANCE, f"未知の compatibility reason '{reason}'", path)
        if not _nonblank_str(fmt):
            col.add(INVALID_COMPATIBILITY_PROVENANCE, "provenance.format は空にできません", path)
        if source in _COMPAT_SOURCES and reason in _COMPAT_REASONS and _nonblank_str(fmt):
            provenance = CompatibilityProvenance(source=source, reason=reason, format=fmt)
    if isinstance(sid, str) and sid in seen_ids:
        col.add(DUPLICATE_SEMANTIC_ID, f"section id '{sid}' が重複しています", path)
    if isinstance(sid, str):
        seen_ids.add(sid)
    if provenance is None or not _nonblank_str(sid) or not _nonblank_str(raw.get("markup")):
        return None
    return CompatibilitySection(id=sid, markup=raw.get("markup"), provenance=provenance)
