"""Strict, standard-library validation of assembly requests and canonical IR.

Parsing turns raw JSON into typed model values only after rejecting
booleans-as-integers, unknown fields, blank IDs, duplicate IDs, bad references,
absent common slots, and renderer-shaped authoring fields. Relationship
direction and component choice are never inferred from prose.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from .diagnostics import (
    CHEVRON_STRUCTURE_VIOLATION,
    DUPLICATE_SEMANTIC_ID,
    ENUMERATION_STRUCTURE_VIOLATION,
    ENUMERATION_EMPHASIS_NOT_FOUND,
    FORBIDDEN_AUTHORING_FIELD,
    INVALID_COMPATIBILITY_PROVENANCE,
    INVALID_COMPONENT_PAYLOAD,
    INVALID_FLOW_EDGE,
    INVALID_MATRIX_REFERENCE,
    INVALID_NARRATIVE_SECTION,
    INVALID_RELATIONSHIP_DECLARATION,
    LOGIC_TREE_STRUCTURE_VIOLATION,
    MATRIX_CONCEPT_LENGTH,
    MISSING_REQUIRED_SLOT,
    PYRAMID_STRUCTURE_VIOLATION,
    QUANTITATIVE_UNIT_REQUIRED,
    SLOPE_STRUCTURE_VIOLATION,
    EVIDENCE_MAP_STRUCTURE_VIOLATION,
    STAIRS_STRUCTURE_VIOLATION,
    WATERFALL_ARITHMETIC_MISMATCH,
    WATERFALL_STRUCTURE_VIOLATION,
    BARS_ITEM_LIMIT,
    KPI_ITEM_LIMIT,
    ContractError,
    DiagnosticCollector,
)
from .flow_layout import assign_rails, check_row_budget, check_topology, edge_spans, order_index
from .numeric import is_numeric, to_decimal, waterfall_axis_max, waterfall_scale_values
from .model import (
    AccessibilityInfo,
    AssemblyRequest,
    AxisEntry,
    CanonicalIR,
    CanonicalSection,
    CertaintyAssertion,
    ChevronPayload,
    ChevronStep,
    CompatibilityProvenance,
    CompatibilitySection,
    DocumentMetadata,
    EmphasisAnnotation,
    EnumerationItem,
    EnumerationPayload,
    ExplicitSelection,
    FlowEdge,
    FlowGroup,
    FlowNode,
    FlowPayload,
    LogicTreeBranch,
    LogicTreeLeaf,
    LogicTreePayload,
    LogicTreeRoot,
    EvidenceConclusion,
    EvidenceItem,
    EvidenceMapPayload,
    FirstScreenSection,
    ClosingBlock,
    ClosingSection,
    NarrativeSection,
    SlopeAxes,
    SlopeItem,
    SlopePayload,
    BarsItem,
    BarsPayload,
    KpiItem,
    KpiPayload,
    MatrixCell,
    MatrixPayload,
    PyramidPayload,
    PyramidTier,
    RelationshipDeclaration,
    Source,
    StairsPayload,
    StairsStage,
    WaterfallEndpoint,
    WaterfallPayload,
    WaterfallStep,
)

_VOCAB_PATH = Path(__file__).resolve().parents[1].parent / "references" / "component-vocabulary.json"


def load_vocabulary() -> dict:
    return json.loads(_VOCAB_PATH.read_text("utf-8"))


VOCABULARY = load_vocabulary()
_COMPONENTS = VOCABULARY["components"]
_PAYLOAD_KEYS = frozenset(_COMPONENTS.keys())
_KIND_TO_COMPONENT = {c["relationshipKind"]: name for name, c in _COMPONENTS.items()}
_ALL_CAPABILITIES = {cap for c in _COMPONENTS.values() for cap in c["capabilities"]}
_FLOW_RELATIONS = frozenset(_COMPONENTS["flow"]["capabilities"])
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
    "id", "relationship", "selection", "caption", "certainty", "sources", "accessibility",
    "matrix", "flow", "enumeration", "chevron", "pyramid", "stairs", "waterfall", "logic-tree",
    "slope", "bars", "kpi", "evidence-map",
    "takeawayTargetIds", "takeawayScope", "emphasis",
}
_RELATIONSHIP_KEYS = {"kind", "capabilities"}
_SELECTION_KEYS = {"component", "version", "matchedCapabilities"}
_CERTAINTY_KEYS = {"id", "level", "statement"}
_SOURCE_KEYS = {"id", "label", "detail"}
_ACCESSIBILITY_KEYS = {"label", "summary"}
_AXIS_KEYS = {"id", "label"}
_CELL_KEYS = {"id", "rowId", "columnId", "content", "certaintyRef", "sourceRef"}
_MATRIX_KEYS = {"rows", "columns", "cells", "highlightId", "presentation", "showColumnHeaders"}
_FLOW_KEYS = {"nodes", "edges", "groups", "startId", "readingOrder"}
_NODE_KEYS = {"id", "label", "group"}
_EDGE_KEYS = {"id", "from", "to", "relation", "label"}
_GROUP_KEYS = {"id", "label"}
_ENUMERATION_KEYS = {"items", "presentation", "blockContent"}
_ENUMERATION_ITEM_KEYS = {"id", "label", "title", "description", "descriptionEmphasis"}
_CHEVRON_KEYS = {"steps", "orientation", "blockContent", "loop"}
_CHEVRON_STEP_KEYS = {"id", "label", "title", "description", "descriptionEmphasis"}
_PYRAMID_KEYS = {"tiers"}
_PYRAMID_TIER_KEYS = {"id", "label", "sub"}
_STAIRS_KEYS = {"stages", "highlightId"}
_STAIRS_STAGE_KEYS = {"id", "label"}
_WATERFALL_KEYS = {"displayPrecision", "start", "steps", "end", "title", "unitLabel", "axisTicks"}
_WATERFALL_ENDPOINT_KEYS = {"id", "label", "value", "valueText"}
_WATERFALL_STEP_KEYS = {"id", "label", "delta", "valueText", "tone"}
_WATERFALL_TONES = frozenset({"positive", "warning", "neutral"})
_LOGIC_TREE_KEYS = {"root", "branches"}
_LOGIC_TREE_ROOT_KEYS = {"id", "label"}
_LOGIC_TREE_BRANCH_KEYS = {"id", "label", "leaves"}
_LOGIC_TREE_LEAF_KEYS = {"id", "text"}
_SLOPE_KEYS = {"axes", "items", "title", "unitLabel", "highlightId"}
_SLOPE_AXES_KEYS = {"fromLabel", "toLabel"}
_SLOPE_ITEM_KEYS = {"id", "label", "fromValue", "toValue", "fromValueText", "toValueText", "tone"}
_BARS_KEYS = {"title", "unitLabel", "items", "highlightId"}
_BARS_ITEM_KEYS = {"id", "label", "value", "valueText"}
_KPI_KEYS = {"items"}
_KPI_ITEM_KEYS = {"id", "value", "unit", "caption"}
_EVIDENCE_MAP_KEYS = {"conclusion", "evidence"}
_EVIDENCE_CONCLUSION_KEYS = {"id", "label"}
_EVIDENCE_ITEM_KEYS = {"id", "label", "certaintyRef", "sourceRef"}
_SLOPE_TONES = frozenset({"positive", "warning", "neutral"})
_DOCUMENT_KEYS = {"id", "title", "summary", "type", "profile"}
_DOCUMENT_TYPES = frozenset({"proposal", "system", "research"})
_DOCUMENT_PROFILES = frozenset({"strict", "extended"})
_ASSEMBLY_KEYS = {"schemaVersion", "document", "sections"}
_COMPAT_SECTION_KEYS = {"kind", "id", "markup", "provenance"}
_PROVENANCE_KEYS = {"source", "reason", "format"}
_CANONICAL_SECTION_KEYS = {"kind", "ir"}
_NARRATIVE_SECTION_KEYS = {"kind", "id", "markup"}
_FIRST_SCREEN_SECTION_KEYS = {"kind", "id", "decision", "conditions"}
_CLOSING_SECTION_KEYS = {"kind", "id", "blocks"}
_CLOSING_BLOCK_KEYS = {"heading", "items"}
_CLOSING_REQUIRED = {
    "proposal": ("リスクと弱い前提", "不確かな点"),
    "system": ("限界・確度",),
    "research": ("限界・反証・確度",),
}
_SENTENCE_TERMINATORS = frozenset("。！？!?")


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _nonblank_str(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_single_sentence(value: str) -> bool:
    """True iff value ends with a sentence terminator and contains exactly one."""
    if not value or value[-1] not in _SENTENCE_TERMINATORS:
        return False
    return sum(1 for ch in value if ch in _SENTENCE_TERMINATORS) == 1


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


_ANNOTATION_TARGET_LABELS = {
    "matrix": "セル",
    "flow": "ノード/エッジ",
    "enumeration": "項目",
    "chevron": "ステップ",
    "pyramid": "層",
    "stairs": "段",
    "waterfall": "開始/段/終了",
    "logic-tree": "枝/葉",
    "slope": "項目",
    "bars": "項目",
    "kpi": "項目",
    "evidence-map": "結論/根拠",
}


def _run_payload_validator(
    payload_kind: str,
    raw: dict,
    path: str,
    col: DiagnosticCollector,
    relationship: RelationshipDeclaration | None,
) -> object | None:
    validator = _PAYLOAD_VALIDATORS.get(payload_kind)
    if validator is None:
        col.add(INVALID_COMPONENT_PAYLOAD, f"未登録のペイロード種別 '{payload_kind}'", path)
        return None
    payload_path = f"{path}.{payload_kind}"
    payload_raw = raw.get(payload_kind)
    if payload_kind == "flow":
        acyclic = relationship is not None and "ordered-transition" in relationship.capabilities
        return validator(payload_raw, payload_path, col, acyclic=acyclic)
    if payload_kind == "chevron":
        return validator(payload_raw, payload_path, col, relationship=relationship)
    return validator(payload_raw, payload_path, col)


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
    enumeration = None
    chevron = None
    pyramid = None
    stairs = None
    waterfall = None
    logic_tree = None
    slope = None
    bars = None
    kpi = None
    evidence_map = None
    validated_payload = None
    present = [key for key in _PAYLOAD_KEYS if key in raw]
    if len(present) == 0:
        col.add(INVALID_COMPONENT_PAYLOAD, "コンポーネント ペイロードが必要です", path)
        payload_kind = "matrix"
    elif len(present) > 1:
        col.add(INVALID_COMPONENT_PAYLOAD,
                f"ペイロードは1つだけ指定できます ({', '.join(present)})", path)
        payload_kind = present[0]
    else:
        payload_kind = present[0]
        if payload_kind == "evidence-map":
            validated_payload = _validate_evidence_map(
                raw.get("evidence-map"),
                f"{path}.evidence-map",
                col,
                certainty_ids={c.id for c in certainty},
                source_ids={s.id for s in sources},
            )
            evidence_map = validated_payload
        else:
            validated_payload = _run_payload_validator(payload_kind, raw, path, col, relationship)
            if payload_kind == "matrix":
                matrix = validated_payload
            elif payload_kind == "flow":
                flow = validated_payload
            elif payload_kind == "enumeration":
                enumeration = validated_payload
            elif payload_kind == "chevron":
                chevron = validated_payload
            elif payload_kind == "pyramid":
                pyramid = validated_payload
            elif payload_kind == "stairs":
                stairs = validated_payload
            elif payload_kind == "waterfall":
                waterfall = validated_payload
            elif payload_kind == "logic-tree":
                logic_tree = validated_payload
            elif payload_kind == "slope":
                slope = validated_payload
            elif payload_kind == "bars":
                bars = validated_payload
            elif payload_kind == "kpi":
                kpi = validated_payload

    takeaway_target_ids, takeaway_scope, emphasis = _validate_annotations(
        raw, path, col, caption, payload_kind, validated_payload
    )

    # Cross-consistency: component choice must match the present payload and kind.
    if selection is not None and len(present) == 1:
        if selection.component != present[0]:
            col.add(INVALID_COMPONENT_PAYLOAD,
                    f"selection.component '{selection.component}' がペイロード '{present[0]}' と一致しません", path)
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
        enumeration=enumeration,
        chevron=chevron,
        pyramid=pyramid,
        stairs=stairs,
        waterfall=waterfall,
        logic_tree=logic_tree,
        slope=slope,
        bars=bars,
        kpi=kpi,
        evidence_map=evidence_map,
        takeaway_target_ids=takeaway_target_ids,
        takeaway_scope=takeaway_scope,
        emphasis=emphasis,
    )


def _validate_annotations(raw, path, col, caption, payload_kind, payload):
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
    target_extractor = ANNOTATION_TARGETS.get(payload_kind)
    if target_extractor is None:
        col.add(INVALID_COMPONENT_PAYLOAD, f"注釈対象が未登録のペイロード '{payload_kind}'", path)
        allowed: set[str] = set()
        kind_label = "項目"
    else:
        allowed = target_extractor(payload)
        kind_label = _ANNOTATION_TARGET_LABELS.get(payload_kind, "項目")
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
        content_raw = item.get("content")
        if isinstance(content_raw, list):
            if not content_raw or not all(_nonblank_str(x) for x in content_raw):
                col.add(INVALID_COMPONENT_PAYLOAD, "cell.content の配列要素は空にできません", p)
            content_val: object = tuple(x for x in content_raw if isinstance(x, str))
        elif _nonblank_str(content_raw):
            content_val = content_raw
        else:
            col.add(INVALID_COMPONENT_PAYLOAD, "cell.content は空にできません", p)
            content_val = content_raw
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
            id=cid, row_id=rid, column_id=colid, content=content_val,
            certainty_ref=item.get("certaintyRef"), source_ref=item.get("sourceRef"),
        ))
    highlight_id = raw.get("highlightId")
    if highlight_id is not None and not _nonblank_str(highlight_id):
        col.add(INVALID_COMPONENT_PAYLOAD, "highlightId は空にできません", path)
        highlight_id = None
    elif highlight_id is not None and highlight_id not in {c.id for c in cells}:
        col.add(INVALID_COMPONENT_PAYLOAD, f"highlightId '{highlight_id}' が cells に存在しません", path)
    presentation = raw.get("presentation", "dense")
    if presentation not in ("concept", "dense"):
        col.add(INVALID_COMPONENT_PAYLOAD, f"presentation '{presentation}' は concept か dense のみ有効です", path)
        presentation = "dense"
    if presentation == "concept":
        ncol = len(columns)
        if ncol < 2 or ncol > 4:
            col.add(INVALID_COMPONENT_PAYLOAD, f"concept では columns は2〜4件である必要があります (found {ncol})", path)
        for i, cell in enumerate(cells):
            if not isinstance(cell.content, str):
                col.add(
                    INVALID_COMPONENT_PAYLOAD,
                    "concept セルの content は文字列である必要があります",
                    f"{path}.cells[{i}].content",
                )
                continue
            if len(cell.content) >= 7:
                col.add(
                    MATRIX_CONCEPT_LENGTH,
                    f"concept セルの content は6文字以下である必要があります (found {len(cell.content)})",
                    f"{path}.cells[{i}].content",
                )
    show_column_headers = raw.get("showColumnHeaders", True)
    if not isinstance(show_column_headers, bool):
        col.add(INVALID_COMPONENT_PAYLOAD, "showColumnHeaders は真偽値である必要があります", path)
        show_column_headers = True
    if presentation == "concept" and show_column_headers is False:
        col.add(INVALID_COMPONENT_PAYLOAD, "showColumnHeaders=false は dense モードでのみ有効です", path)
        show_column_headers = True
    return MatrixPayload(
        rows=rows, columns=columns, cells=tuple(cells),
        highlight_id=highlight_id if isinstance(highlight_id, str) else None,
        presentation=presentation,
        show_column_headers=show_column_headers,
    )


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


def _validate_enumeration(raw: object, path: str, col: DiagnosticCollector) -> EnumerationPayload | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "enumeration はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _ENUMERATION_KEYS, path, col)
    presentation = raw.get("presentation", "list")
    block_content = raw.get("blockContent", "number")
    if presentation not in ("list", "columns"):
        col.add(INVALID_COMPONENT_PAYLOAD, f"presentation '{presentation}' は list か columns のみ有効です", path)
        presentation = "list"
    if block_content not in ("number", "label"):
        col.add(INVALID_COMPONENT_PAYLOAD, f"blockContent '{block_content}' は number か label のみ有効です", path)
        block_content = "number"

    items_raw = raw.get("items")
    if not isinstance(items_raw, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "items は配列である必要があります", path)
        return None
    count = len(items_raw)
    max_items = 4 if presentation == "columns" else 6
    if count < 2 or count > max_items:
        col.add(ENUMERATION_STRUCTURE_VIOLATION,
                f"items は2〜{max_items}件である必要があります (presentation={presentation})", path)

    desc_max_lines = 4 if presentation == "columns" else 3
    desc_max_chars = 40 if presentation == "columns" else 60

    items: list[EnumerationItem] = []
    has_description: list[bool] = []
    for i, item in enumerate(items_raw):
        p = f"{path}.items[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "item はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _ENUMERATION_ITEM_KEYS, p, col)
        iid = item.get("id")
        if not _nonblank_str(iid):
            col.add(INVALID_COMPONENT_PAYLOAD, "item.id は空にできません", p)
        label = item.get("label")
        title = item.get("title")
        desc_raw = item.get("description")
        desc_emphasis = item.get("descriptionEmphasis")
        desc_lines: list[str] = []
        if desc_raw is not None:
            if not isinstance(desc_raw, list) or not desc_raw:
                col.add(ENUMERATION_STRUCTURE_VIOLATION, "description は非空の配列である必要があります", p)
            else:
                if len(desc_raw) > desc_max_lines:
                    col.add(ENUMERATION_STRUCTURE_VIOLATION,
                            f"description は最大{desc_max_lines}行です", p)
                for j, line in enumerate(desc_raw):
                    if not isinstance(line, str) or not line.strip():
                        col.add(ENUMERATION_STRUCTURE_VIOLATION, f"description[{j}] は空にできません", p)
                    elif len(line) > desc_max_chars:
                        col.add(ENUMERATION_STRUCTURE_VIOLATION,
                                f"description[{j}] は{desc_max_chars}字以内です", p)
                    else:
                        desc_lines.append(line)
        has_description.append(bool(desc_lines))

        if block_content == "label":
            if not _nonblank_str(label):
                col.add(ENUMERATION_STRUCTURE_VIOLATION, "blockContent:label では label が必須です", p)
            elif len(str(label)) > 16:
                col.add(ENUMERATION_STRUCTURE_VIOLATION, "label は16字以内です", p)
            if title is not None:
                col.add(ENUMERATION_STRUCTURE_VIOLATION, "blockContent:label では title は禁止です", p)
        else:
            if label is not None:
                col.add(ENUMERATION_STRUCTURE_VIOLATION, "blockContent:number では label は禁止です", p)
            if not _nonblank_str(title):
                col.add(ENUMERATION_STRUCTURE_VIOLATION, "blockContent:number では title が必須です", p)
            elif len(str(title)) > 30:
                col.add(ENUMERATION_STRUCTURE_VIOLATION, "title は30字以内です", p)
        if desc_emphasis is not None and not _nonblank_str(desc_emphasis):
            col.add(ENUMERATION_STRUCTURE_VIOLATION, "descriptionEmphasis は空にできません", p)
        elif isinstance(desc_emphasis, str) and desc_lines:
            if not any(desc_emphasis in line for line in desc_lines):
                col.add(
                    ENUMERATION_EMPHASIS_NOT_FOUND,
                    "descriptionEmphasis は description の部分文字列である必要があります",
                    p,
                )

        items.append(EnumerationItem(
            id=iid, label=label if isinstance(label, str) else None,
            title=title if isinstance(title, str) else None,
            description=tuple(desc_lines),
            description_emphasis=desc_emphasis if isinstance(desc_emphasis, str) else None,
        ))

    if has_description and not all(has_description) and any(has_description):
        col.add(ENUMERATION_STRUCTURE_VIOLATION,
                "description は全 item で省略するか全 item で指定する必要があります", path)

    if col:
        return None
    return EnumerationPayload(items=tuple(items), presentation=presentation, block_content=block_content)


def _validate_chevron(raw: object, path: str, col: DiagnosticCollector,
                      relationship: RelationshipDeclaration | None = None) -> ChevronPayload | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "chevron はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _CHEVRON_KEYS, path, col)
    orientation = raw.get("orientation", "vertical")
    block_content = raw.get("blockContent", "number")
    loop = raw.get("loop", False)
    if orientation not in ("vertical", "horizontal"):
        col.add(INVALID_COMPONENT_PAYLOAD, f"orientation '{orientation}' は vertical か horizontal のみ有効です", path)
        orientation = "vertical"
    if block_content not in ("number", "label"):
        col.add(INVALID_COMPONENT_PAYLOAD, f"blockContent '{block_content}' は number か label のみ有効です", path)
        block_content = "number"
    if not isinstance(loop, bool):
        col.add(INVALID_COMPONENT_PAYLOAD, "loop は真偽値である必要があります", path)
        loop = False

    caps = set(relationship.capabilities) if relationship is not None else set()
    if "linear-sequence" not in caps:
        col.add(CHEVRON_STRUCTURE_VIOLATION, "linear-sequence capability は常に必須です", path)
    has_closed_loop = "closed-loop" in caps
    if loop and not has_closed_loop:
        col.add(CHEVRON_STRUCTURE_VIOLATION, "loop:true には closed-loop capability が必要です", path)
    if not loop and has_closed_loop:
        col.add(CHEVRON_STRUCTURE_VIOLATION, "closed-loop capability は loop:true と併用する必要があります", path)
    if loop and orientation == "horizontal":
        col.add(CHEVRON_STRUCTURE_VIOLATION, "loop:true は orientation:vertical のみ有効です", path)

    steps_raw = raw.get("steps")
    if not isinstance(steps_raw, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "steps は配列である必要があります", path)
        return None
    count = len(steps_raw)
    min_steps = 3 if orientation == "horizontal" else 2
    max_steps = 6
    if count < min_steps or count > max_steps:
        col.add(CHEVRON_STRUCTURE_VIOLATION,
                f"steps は{min_steps}〜{max_steps}件である必要があります (orientation={orientation})", path)

    desc_max_lines = 2 if orientation == "horizontal" else 3
    desc_max_chars = 30 if orientation == "horizontal" else 40

    steps: list[ChevronStep] = []
    has_description: list[bool] = []
    for i, item in enumerate(steps_raw):
        p = f"{path}.steps[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "step はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _CHEVRON_STEP_KEYS, p, col)
        sid = item.get("id")
        if not _nonblank_str(sid):
            col.add(INVALID_COMPONENT_PAYLOAD, "step.id は空にできません", p)
        label = item.get("label")
        title = item.get("title")
        desc_raw = item.get("description")
        desc_emphasis = item.get("descriptionEmphasis")
        desc_lines: list[str] = []
        if desc_raw is not None:
            if not isinstance(desc_raw, list) or not desc_raw:
                col.add(CHEVRON_STRUCTURE_VIOLATION, "description は非空の配列である必要があります", p)
            else:
                if len(desc_raw) > desc_max_lines:
                    col.add(CHEVRON_STRUCTURE_VIOLATION,
                            f"description は最大{desc_max_lines}行です", p)
                for j, line in enumerate(desc_raw):
                    if not isinstance(line, str) or not line.strip():
                        col.add(CHEVRON_STRUCTURE_VIOLATION, f"description[{j}] は空にできません", p)
                    elif len(line) > desc_max_chars:
                        col.add(CHEVRON_STRUCTURE_VIOLATION,
                                f"description[{j}] は{desc_max_chars}字以内です", p)
                    else:
                        desc_lines.append(line)
        has_description.append(bool(desc_lines))

        if block_content == "label":
            if not _nonblank_str(label):
                col.add(CHEVRON_STRUCTURE_VIOLATION, "blockContent:label では label が必須です", p)
            elif len(str(label)) > 16:
                col.add(CHEVRON_STRUCTURE_VIOLATION, "label は16字以内です", p)
            if title is not None:
                col.add(CHEVRON_STRUCTURE_VIOLATION, "blockContent:label では title は禁止です", p)
        else:
            if label is not None:
                col.add(CHEVRON_STRUCTURE_VIOLATION, "blockContent:number では label は禁止です", p)
            if not _nonblank_str(title):
                col.add(CHEVRON_STRUCTURE_VIOLATION, "blockContent:number では title が必須です", p)
            elif len(str(title)) > 30:
                col.add(CHEVRON_STRUCTURE_VIOLATION, "title は30字以内です", p)
        if desc_emphasis is not None and not _nonblank_str(desc_emphasis):
            col.add(CHEVRON_STRUCTURE_VIOLATION, "descriptionEmphasis は空にできません", p)

        steps.append(ChevronStep(
            id=sid, label=label if isinstance(label, str) else None,
            title=title if isinstance(title, str) else None,
            description=tuple(desc_lines),
            description_emphasis=desc_emphasis if isinstance(desc_emphasis, str) else None,
        ))

    if has_description and not all(has_description) and any(has_description):
        col.add(CHEVRON_STRUCTURE_VIOLATION,
                "description は全 step で省略するか全 step で指定する必要があります", path)

    if col:
        return None
    return ChevronPayload(steps=tuple(steps), orientation=orientation, block_content=block_content, loop=loop)


def _validate_pyramid(raw: object, path: str, col: DiagnosticCollector) -> PyramidPayload | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "pyramid はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _PYRAMID_KEYS, path, col)
    tiers_raw = raw.get("tiers")
    if not isinstance(tiers_raw, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "tiers は配列である必要があります", path)
        return None
    count = len(tiers_raw)
    if count < 3 or count > 4:
        col.add(PYRAMID_STRUCTURE_VIOLATION,
                f"tiers は3〜4件である必要があります (found {count})", path)

    tiers: list[PyramidTier] = []
    for i, item in enumerate(tiers_raw):
        p = f"{path}.tiers[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "tier はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _PYRAMID_TIER_KEYS, p, col)
        tid = item.get("id")
        if not _nonblank_str(tid):
            col.add(INVALID_COMPONENT_PAYLOAD, "tier.id は空にできません", p)
        label = item.get("label")
        if not _nonblank_str(label):
            col.add(PYRAMID_STRUCTURE_VIOLATION, "tier.label は空にできません", p)
        elif len(str(label)) > 12:
            col.add(PYRAMID_STRUCTURE_VIOLATION, "label は12字以内です", p)
        sub = item.get("sub", "")
        if sub is not None and sub != "":
            if not isinstance(sub, str) or not sub.strip():
                col.add(PYRAMID_STRUCTURE_VIOLATION, "sub は空にできません", p)
            elif len(sub) > 30:
                col.add(PYRAMID_STRUCTURE_VIOLATION, "sub は30字以内です", p)
        tiers.append(PyramidTier(
            id=tid, label=label if isinstance(label, str) else "",
            sub=sub if isinstance(sub, str) else "",
        ))

    if col:
        return None
    return PyramidPayload(tiers=tuple(tiers))


def _validate_stairs(raw: object, path: str, col: DiagnosticCollector) -> StairsPayload | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "stairs はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _STAIRS_KEYS, path, col)
    stages_raw = raw.get("stages")
    if not isinstance(stages_raw, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "stages は配列である必要があります", path)
        return None
    count = len(stages_raw)
    if count < 3 or count > 5:
        col.add(STAIRS_STRUCTURE_VIOLATION,
                f"stages は3〜5件である必要があります (found {count})", path)

    stages: list[StairsStage] = []
    for i, item in enumerate(stages_raw):
        p = f"{path}.stages[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "stage はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _STAIRS_STAGE_KEYS, p, col)
        sid = item.get("id")
        if not _nonblank_str(sid):
            col.add(INVALID_COMPONENT_PAYLOAD, "stage.id は空にできません", p)
        label = item.get("label")
        if not _nonblank_str(label):
            col.add(STAIRS_STRUCTURE_VIOLATION, "stage.label は空にできません", p)
        elif len(str(label)) > 14:
            col.add(STAIRS_STRUCTURE_VIOLATION, "label は14字以内です", p)
        stages.append(StairsStage(
            id=sid, label=label if isinstance(label, str) else "",
        ))

    highlight_id = raw.get("highlightId")
    if highlight_id is not None and not _nonblank_str(highlight_id):
        col.add(STAIRS_STRUCTURE_VIOLATION, "highlightId は空にできません", path)
        highlight_id = None
    elif highlight_id is not None and highlight_id not in {s.id for s in stages}:
        col.add(STAIRS_STRUCTURE_VIOLATION, f"highlightId '{highlight_id}' が stages に存在しません", path)

    if col:
        return None
    return StairsPayload(
        stages=tuple(stages),
        highlight_id=highlight_id if isinstance(highlight_id, str) else None,
    )


def _parse_numeric_field(raw: object, path: str, col: DiagnosticCollector) -> int | Decimal | None:
    if isinstance(raw, bool):
        col.add(WATERFALL_STRUCTURE_VIOLATION, "数値フィールドに bool は許可されません", path)
        return None
    if isinstance(raw, float):
        col.add(WATERFALL_STRUCTURE_VIOLATION, "数値フィールドに float は許可されません", path)
        return None
    if not is_numeric(raw):
        col.add(WATERFALL_STRUCTURE_VIOLATION, "数値フィールドは int または Decimal である必要があります", path)
        return None
    return raw


def _validate_waterfall_endpoint(
    raw: object, path: str, col: DiagnosticCollector,
) -> WaterfallEndpoint | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "endpoint はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _WATERFALL_ENDPOINT_KEYS, path, col, payload_code=WATERFALL_STRUCTURE_VIOLATION)
    eid = raw.get("id")
    if not _nonblank_str(eid):
        col.add(INVALID_COMPONENT_PAYLOAD, "id は空にできません", path)
    label = raw.get("label")
    if not _nonblank_str(label):
        col.add(WATERFALL_STRUCTURE_VIOLATION, "label は空にできません", path)
    elif len(str(label)) > 12:
        col.add(WATERFALL_STRUCTURE_VIOLATION, "label は12字以内です", path)
    value = _parse_numeric_field(raw.get("value"), f"{path}.value", col)
    value_text = raw.get("valueText")
    if not _nonblank_str(value_text):
        col.add(WATERFALL_STRUCTURE_VIOLATION, "valueText は空にできません", path)
    elif len(str(value_text)) > 16:
        col.add(WATERFALL_STRUCTURE_VIOLATION, "valueText は16字以内です", path)
    if value is None or not _nonblank_str(eid) or not _nonblank_str(label) or not _nonblank_str(value_text):
        return None
    return WaterfallEndpoint(
        id=eid, label=label, value=value, value_text=value_text,
    )


def _validate_waterfall(raw: object, path: str, col: DiagnosticCollector) -> WaterfallPayload | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "waterfall はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _WATERFALL_KEYS, path, col, payload_code=WATERFALL_STRUCTURE_VIOLATION)

    display_precision = _parse_numeric_field(raw.get("displayPrecision"), f"{path}.displayPrecision", col)
    if display_precision is not None:
        if to_decimal(display_precision) <= Decimal(0):
            col.add(WATERFALL_STRUCTURE_VIOLATION, "displayPrecision は正である必要があります", path)

    title = raw.get("title")
    if not _nonblank_str(title):
        col.add(WATERFALL_STRUCTURE_VIOLATION, "title は必須です", path)

    unit_label = raw.get("unitLabel")
    if not _nonblank_str(unit_label):
        col.add(QUANTITATIVE_UNIT_REQUIRED, "unitLabel は必須です", path)
    elif len(str(unit_label)) > 8:
        col.add(WATERFALL_STRUCTURE_VIOLATION, "unitLabel は8字以内です", path)

    axis_ticks_raw = raw.get("axisTicks")
    axis_ticks: list[str] = []
    if not isinstance(axis_ticks_raw, list) or not axis_ticks_raw:
        col.add(WATERFALL_STRUCTURE_VIOLATION, "axisTicks は非空の配列である必要があります", path)
    else:
        for i, tick in enumerate(axis_ticks_raw):
            tp = f"{path}.axisTicks[{i}]"
            if not isinstance(tick, str) or not tick.strip():
                col.add(WATERFALL_STRUCTURE_VIOLATION, "axisTicks の各要素は非空文字列である必要があります", tp)
                continue
            try:
                tick_val = to_decimal(tick.strip())
            except Exception:
                col.add(WATERFALL_STRUCTURE_VIOLATION, f"axisTicks '{tick}' は数値である必要があります", tp)
                continue
            if tick_val < Decimal(0):
                col.add(WATERFALL_STRUCTURE_VIOLATION, f"axisTicks '{tick}' は 0 以上である必要があります", tp)
            axis_ticks.append(tick.strip())

    start = _validate_waterfall_endpoint(raw.get("start"), f"{path}.start", col)
    end = _validate_waterfall_endpoint(raw.get("end"), f"{path}.end", col)

    steps_raw = raw.get("steps")
    if not isinstance(steps_raw, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "steps は配列である必要があります", path)
        return None

    step_count = len(steps_raw)
    if step_count < 1 or step_count > 5:
        col.add(WATERFALL_STRUCTURE_VIOLATION,
                f"steps は1〜5件である必要があります (found {step_count})", path)

    steps: list[WaterfallStep] = []
    for i, item in enumerate(steps_raw):
        p = f"{path}.steps[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "step はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _WATERFALL_STEP_KEYS, p, col, payload_code=WATERFALL_STRUCTURE_VIOLATION)
        sid = item.get("id")
        if not _nonblank_str(sid):
            col.add(INVALID_COMPONENT_PAYLOAD, "step.id は空にできません", p)
        label = item.get("label")
        if not _nonblank_str(label):
            col.add(WATERFALL_STRUCTURE_VIOLATION, "step.label は空にできません", p)
        elif len(str(label)) > 12:
            col.add(WATERFALL_STRUCTURE_VIOLATION, "label は12字以内です", p)
        delta = _parse_numeric_field(item.get("delta"), f"{p}.delta", col)
        tone = item.get("tone")
        if tone not in _WATERFALL_TONES:
            col.add(WATERFALL_STRUCTURE_VIOLATION, "tone は positive/warning/neutral である必要があります", p)
        value_text = item.get("valueText")
        if not _nonblank_str(value_text):
            col.add(WATERFALL_STRUCTURE_VIOLATION, "valueText は空にできません", p)
        elif len(str(value_text)) > 16:
            col.add(WATERFALL_STRUCTURE_VIOLATION, "valueText は16字以内です", p)
        if delta is None or not _nonblank_str(sid) or not _nonblank_str(label) or not _nonblank_str(value_text):
            continue
        steps.append(WaterfallStep(
            id=sid, label=label, delta=delta, value_text=value_text,
            tone=tone if isinstance(tone, str) else "",
        ))

    if display_precision is None or start is None or end is None:
        if col:
            return None
        col.add(WATERFALL_STRUCTURE_VIOLATION, "displayPrecision は必須です", path)
        return None

    if not _nonblank_str(title) or not _nonblank_str(unit_label) or not axis_ticks:
        if col:
            return None
        return None

    if col:
        return None

    payload = WaterfallPayload(
        display_precision=display_precision,
        start=start,
        steps=tuple(steps),
        end=end,
        title=str(title),
        unit_label=str(unit_label),
        axis_ticks=tuple(axis_ticks),
    )
    scale_values, lo, hi = waterfall_scale_values(payload)
    if lo == hi:
        col.add(WATERFALL_STRUCTURE_VIOLATION, "range が 0 のため描画できません", path)
        return None

    chart_v_max = waterfall_axis_max(scale_values)
    for i, tick in enumerate(axis_ticks):
        tick_val = to_decimal(tick)
        if tick_val < Decimal(0) or tick_val > chart_v_max:
            col.add(WATERFALL_STRUCTURE_VIOLATION,
                    f"axisTicks[{i}] '{tick}' は 0..{chart_v_max} の範囲である必要があります",
                    f"{path}.axisTicks[{i}]")

    total = to_decimal(start.value)
    for step in steps:
        total += to_decimal(step.delta)
    tolerance = to_decimal(display_precision) / Decimal(2)
    if abs(total - to_decimal(end.value)) > tolerance:
        col.add(WATERFALL_ARITHMETIC_MISMATCH,
                "start + Σdelta と end.value が displayPrecision/2 を超えて不一致です", path)
        return None

    return payload


def _validate_logic_tree(raw: object, path: str, col: DiagnosticCollector) -> LogicTreePayload | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "logic-tree はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _LOGIC_TREE_KEYS, path, col)

    root_raw = raw.get("root")
    if not isinstance(root_raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "root はオブジェクトである必要があります", path)
        root_raw = {}
    root_path = f"{path}.root"
    _check_keys(root_raw, _LOGIC_TREE_ROOT_KEYS, root_path, col)
    root_id = root_raw.get("id")
    if not _nonblank_str(root_id):
        col.add(INVALID_COMPONENT_PAYLOAD, "root.id は空にできません", root_path)
    root_label = root_raw.get("label")
    if not _nonblank_str(root_label):
        col.add(LOGIC_TREE_STRUCTURE_VIOLATION, "root.label は空にできません", root_path)
    elif len(str(root_label)) > 20:
        col.add(LOGIC_TREE_STRUCTURE_VIOLATION, "root.label は20字以内です", root_path)

    branches_raw = raw.get("branches")
    if not isinstance(branches_raw, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "branches は配列である必要があります", path)
        return None
    branch_count = len(branches_raw)
    if branch_count < 2 or branch_count > 4:
        col.add(LOGIC_TREE_STRUCTURE_VIOLATION,
                f"branches は2〜4件である必要があります (found {branch_count})", path)

    branches: list[LogicTreeBranch] = []
    for i, item in enumerate(branches_raw):
        p = f"{path}.branches[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "branch はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _LOGIC_TREE_BRANCH_KEYS, p, col)
        bid = item.get("id")
        if not _nonblank_str(bid):
            col.add(INVALID_COMPONENT_PAYLOAD, "branch.id は空にできません", p)
        label = item.get("label")
        if not _nonblank_str(label):
            col.add(LOGIC_TREE_STRUCTURE_VIOLATION, "branch.label は空にできません", p)
        elif len(str(label)) > 16:
            col.add(LOGIC_TREE_STRUCTURE_VIOLATION, "branch.label は16字以内です", p)

        leaves_raw = item.get("leaves", [])
        if leaves_raw is None:
            leaves_raw = []
        if not isinstance(leaves_raw, list):
            col.add(INVALID_COMPONENT_PAYLOAD, "leaves は配列である必要があります", p)
            leaves_raw = []
        leaf_count = len(leaves_raw)
        if leaf_count > 2:
            col.add(LOGIC_TREE_STRUCTURE_VIOLATION,
                    f"leaves は各 branch で0〜2件である必要があります (found {leaf_count})", p)

        leaves: list[LogicTreeLeaf] = []
        for j, leaf_item in enumerate(leaves_raw):
            lp = f"{p}.leaves[{j}]"
            if not isinstance(leaf_item, dict):
                col.add(INVALID_COMPONENT_PAYLOAD, "leaf はオブジェクトである必要があります", lp)
                continue
            _check_keys(leaf_item, _LOGIC_TREE_LEAF_KEYS, lp, col)
            lid = leaf_item.get("id")
            if not _nonblank_str(lid):
                col.add(INVALID_COMPONENT_PAYLOAD, "leaf.id は空にできません", lp)
            text = leaf_item.get("text")
            if not _nonblank_str(text):
                col.add(LOGIC_TREE_STRUCTURE_VIOLATION, "leaf.text は空にできません", lp)
            elif len(str(text)) > 40:
                col.add(LOGIC_TREE_STRUCTURE_VIOLATION, "leaf.text は40字以内です", lp)
            leaves.append(LogicTreeLeaf(
                id=lid, text=text if isinstance(text, str) else "",
            ))

        branches.append(LogicTreeBranch(
            id=bid, label=label if isinstance(label, str) else "",
            leaves=tuple(leaves),
        ))

    if col:
        return None
    return LogicTreePayload(
        root=LogicTreeRoot(
            id=root_id, label=root_label if isinstance(root_label, str) else "",
        ),
        branches=tuple(branches),
    )


def _parse_slope_numeric(raw: object, path: str, col: DiagnosticCollector) -> int | Decimal | None:
    if isinstance(raw, bool):
        col.add(SLOPE_STRUCTURE_VIOLATION, "数値フィールドに bool は許可されません", path)
        return None
    if isinstance(raw, float):
        col.add(SLOPE_STRUCTURE_VIOLATION, "数値フィールドに float は許可されません", path)
        return None
    if not is_numeric(raw):
        col.add(SLOPE_STRUCTURE_VIOLATION, "数値フィールドは int または Decimal である必要があります", path)
        return None
    return raw


def _validate_slope(raw: object, path: str, col: DiagnosticCollector) -> SlopePayload | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "slope はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _SLOPE_KEYS, path, col)

    axes_raw = raw.get("axes")
    if not isinstance(axes_raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "axes はオブジェクトである必要があります", path)
        axes_raw = {}
    axes_path = f"{path}.axes"
    _check_keys(axes_raw, _SLOPE_AXES_KEYS, axes_path, col)
    from_label = axes_raw.get("fromLabel")
    to_label = axes_raw.get("toLabel")
    if not _nonblank_str(from_label):
        col.add(SLOPE_STRUCTURE_VIOLATION, "axes.fromLabel は空にできません", axes_path)
    elif len(str(from_label)) > 8:
        col.add(SLOPE_STRUCTURE_VIOLATION, "axes.fromLabel は8字以内です", axes_path)
    if not _nonblank_str(to_label):
        col.add(SLOPE_STRUCTURE_VIOLATION, "axes.toLabel は空にできません", axes_path)
    elif len(str(to_label)) > 8:
        col.add(SLOPE_STRUCTURE_VIOLATION, "axes.toLabel は8字以内です", axes_path)

    title = raw.get("title")
    if not _nonblank_str(title):
        col.add(SLOPE_STRUCTURE_VIOLATION, "title は必須です", path)

    unit_label = raw.get("unitLabel")
    if not _nonblank_str(unit_label):
        col.add(QUANTITATIVE_UNIT_REQUIRED, "unitLabel は必須です", path)
    elif len(str(unit_label)) > 8:
        col.add(SLOPE_STRUCTURE_VIOLATION, "unitLabel は8字以内です", path)

    items_raw = raw.get("items")
    if not isinstance(items_raw, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "items は配列である必要があります", path)
        return None
    item_count = len(items_raw)
    if item_count < 1 or item_count > 5:
        col.add(SLOPE_STRUCTURE_VIOLATION,
                f"items は1〜5件である必要があります (found {item_count})", path)

    items: list[SlopeItem] = []
    for i, item in enumerate(items_raw):
        p = f"{path}.items[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "item はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _SLOPE_ITEM_KEYS, p, col)
        iid = item.get("id")
        if not _nonblank_str(iid):
            col.add(INVALID_COMPONENT_PAYLOAD, "item.id は空にできません", p)
        label = item.get("label")
        if not _nonblank_str(label):
            col.add(SLOPE_STRUCTURE_VIOLATION, "item.label は空にできません", p)
        elif len(str(label)) > 12:
            col.add(SLOPE_STRUCTURE_VIOLATION, "item.label は12字以内です", p)
        from_value = _parse_slope_numeric(item.get("fromValue"), f"{p}.fromValue", col)
        to_value = _parse_slope_numeric(item.get("toValue"), f"{p}.toValue", col)
        from_text = item.get("fromValueText")
        to_text = item.get("toValueText")
        if not _nonblank_str(from_text):
            col.add(SLOPE_STRUCTURE_VIOLATION, "fromValueText は空にできません", p)
        elif len(str(from_text)) > 12:
            col.add(SLOPE_STRUCTURE_VIOLATION, "fromValueText は12字以内です", p)
        if not _nonblank_str(to_text):
            col.add(SLOPE_STRUCTURE_VIOLATION, "toValueText は空にできません", p)
        elif len(str(to_text)) > 12:
            col.add(SLOPE_STRUCTURE_VIOLATION, "toValueText は12字以内です", p)
        tone = item.get("tone")
        if tone not in _SLOPE_TONES:
            col.add(SLOPE_STRUCTURE_VIOLATION, f"未知の tone '{tone}'", p)
        if from_value is None or to_value is None or not _nonblank_str(iid):
            continue
        items.append(SlopeItem(
            id=iid,
            label=label if isinstance(label, str) else "",
            from_value=from_value,
            to_value=to_value,
            from_value_text=from_text if isinstance(from_text, str) else "",
            to_value_text=to_text if isinstance(to_text, str) else "",
            tone=tone if isinstance(tone, str) else "neutral",
        ))

    if col or not _nonblank_str(from_label) or not _nonblank_str(to_label):
        return None
    if not _nonblank_str(title) or not _nonblank_str(unit_label):
        return None
    highlight_id = raw.get("highlightId")
    if highlight_id is not None and not _nonblank_str(highlight_id):
        col.add(SLOPE_STRUCTURE_VIOLATION, "highlightId は空にできません", path)
        highlight_id = None
    elif highlight_id is not None and highlight_id not in {item.id for item in items}:
        col.add(SLOPE_STRUCTURE_VIOLATION, f"highlightId '{highlight_id}' が items に存在しません", path)
    if col:
        return None
    return SlopePayload(
        axes=SlopeAxes(
            from_label=str(from_label),
            to_label=str(to_label),
        ),
        items=tuple(items),
        title=str(title),
        unit_label=str(unit_label),
        highlight_id=highlight_id if isinstance(highlight_id, str) else None,
    )


def _parse_bars_numeric(raw: object, path: str, col: DiagnosticCollector) -> int | Decimal | None:
    if isinstance(raw, bool):
        col.add(INVALID_COMPONENT_PAYLOAD, "数値フィールドに bool は許可されません", path)
        return None
    if isinstance(raw, float):
        col.add(INVALID_COMPONENT_PAYLOAD, "数値フィールドに float は許可されません", path)
        return None
    if is_numeric(raw):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return Decimal(raw.strip())
        except Exception:
            col.add(INVALID_COMPONENT_PAYLOAD, "数値フィールドは int、Decimal、または数値文字列である必要があります", path)
            return None
    col.add(INVALID_COMPONENT_PAYLOAD, "数値フィールドは int、Decimal、または数値文字列である必要があります", path)
    return None


def _validate_bars(raw: object, path: str, col: DiagnosticCollector) -> BarsPayload | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "bars はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _BARS_KEYS, path, col, payload_code=INVALID_COMPONENT_PAYLOAD)

    title = raw.get("title")
    if not _nonblank_str(title):
        col.add(INVALID_COMPONENT_PAYLOAD, "title は必須です", path)

    unit_label = raw.get("unitLabel")
    if not _nonblank_str(unit_label):
        col.add(QUANTITATIVE_UNIT_REQUIRED, "unitLabel は必須です", path)
    elif len(str(unit_label)) > 8:
        col.add(INVALID_COMPONENT_PAYLOAD, "unitLabel は8字以内です", path)

    items_raw = raw.get("items")
    if not isinstance(items_raw, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "items は配列である必要があります", path)
        return None
    item_count = len(items_raw)
    if item_count < 1 or item_count > 10:
        col.add(BARS_ITEM_LIMIT, f"items は1〜10件である必要があります (found {item_count})", path)

    items: list[BarsItem] = []
    for i, item in enumerate(items_raw):
        p = f"{path}.items[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "item はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _BARS_ITEM_KEYS, p, col, payload_code=INVALID_COMPONENT_PAYLOAD)
        iid = item.get("id")
        if not _nonblank_str(iid):
            col.add(INVALID_COMPONENT_PAYLOAD, "item.id は空にできません", p)
        label = item.get("label")
        if not _nonblank_str(label):
            col.add(INVALID_COMPONENT_PAYLOAD, "item.label は空にできません", p)
        value = _parse_bars_numeric(item.get("value"), f"{p}.value", col)
        value_text = item.get("valueText")
        if not _nonblank_str(value_text):
            col.add(INVALID_COMPONENT_PAYLOAD, "valueText は空にできません", p)
        if value is None or not _nonblank_str(iid):
            continue
        items.append(BarsItem(
            id=iid,
            label=label if isinstance(label, str) else "",
            value=value,
            value_text=value_text if isinstance(value_text, str) else "",
        ))

    if col:
        return None
    if not _nonblank_str(title) or not _nonblank_str(unit_label):
        return None

    highlight_id = raw.get("highlightId")
    if highlight_id is not None and not _nonblank_str(highlight_id):
        col.add(INVALID_COMPONENT_PAYLOAD, "highlightId は空にできません", path)
        highlight_id = None
    elif highlight_id is not None and highlight_id not in {item.id for item in items}:
        col.add(INVALID_COMPONENT_PAYLOAD, f"highlightId '{highlight_id}' が items に存在しません", path)
    if col:
        return None
    return BarsPayload(
        title=str(title),
        unit_label=str(unit_label),
        items=tuple(items),
        highlight_id=highlight_id if isinstance(highlight_id, str) else None,
    )


def _validate_kpi(raw: object, path: str, col: DiagnosticCollector) -> KpiPayload | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "kpi はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _KPI_KEYS, path, col, payload_code=INVALID_COMPONENT_PAYLOAD)

    items_raw = raw.get("items")
    if not isinstance(items_raw, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "items は配列である必要があります", path)
        return None
    item_count = len(items_raw)
    if item_count < 1 or item_count > 5:
        col.add(KPI_ITEM_LIMIT, f"items は1〜5件である必要があります (found {item_count})", path)

    items: list[KpiItem] = []
    for i, item in enumerate(items_raw):
        p = f"{path}.items[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "item はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _KPI_ITEM_KEYS, p, col, payload_code=INVALID_COMPONENT_PAYLOAD)
        iid = item.get("id")
        if not _nonblank_str(iid):
            col.add(INVALID_COMPONENT_PAYLOAD, "item.id は空にできません", p)
        value = item.get("value")
        if not _nonblank_str(value):
            col.add(INVALID_COMPONENT_PAYLOAD, "value は空にできません", p)
        unit = item.get("unit")
        if not _nonblank_str(unit):
            col.add(INVALID_COMPONENT_PAYLOAD, "unit は空にできません", p)
        elif len(str(unit)) > 8:
            col.add(INVALID_COMPONENT_PAYLOAD, "unit は8字以内です", p)
        caption = item.get("caption")
        if not _nonblank_str(caption):
            col.add(INVALID_COMPONENT_PAYLOAD, "caption は空にできません", p)
        if not _nonblank_str(iid):
            continue
        items.append(KpiItem(
            id=iid,
            value=value if isinstance(value, str) else "",
            unit=unit if isinstance(unit, str) else "",
            caption=caption if isinstance(caption, str) else "",
        ))

    if col:
        return None
    return KpiPayload(items=tuple(items))


def _validate_evidence_map(
    raw: object,
    path: str,
    col: DiagnosticCollector,
    *,
    certainty_ids: set[str] | None = None,
    source_ids: set[str] | None = None,
) -> EvidenceMapPayload | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "evidence-map はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _EVIDENCE_MAP_KEYS, path, col)

    conclusion_raw = raw.get("conclusion")
    if not isinstance(conclusion_raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "conclusion はオブジェクトである必要があります", path)
        conclusion_raw = {}
    conclusion_path = f"{path}.conclusion"
    _check_keys(conclusion_raw, _EVIDENCE_CONCLUSION_KEYS, conclusion_path, col)
    cid = conclusion_raw.get("id")
    if not _nonblank_str(cid):
        col.add(INVALID_COMPONENT_PAYLOAD, "conclusion.id は空にできません", conclusion_path)
    clabel = conclusion_raw.get("label")
    if not _nonblank_str(clabel):
        col.add(EVIDENCE_MAP_STRUCTURE_VIOLATION, "conclusion.label は空にできません", conclusion_path)
    elif len(str(clabel)) > 30:
        col.add(EVIDENCE_MAP_STRUCTURE_VIOLATION, "conclusion.label は30字以内です", conclusion_path)

    evidence_raw = raw.get("evidence")
    if not isinstance(evidence_raw, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "evidence は配列である必要があります", path)
        return None
    evidence_count = len(evidence_raw)
    if evidence_count < 2 or evidence_count > 4:
        col.add(EVIDENCE_MAP_STRUCTURE_VIOLATION,
                f"evidence は2〜4件である必要があります (found {evidence_count})", path)

    evidence: list[EvidenceItem] = []
    for i, item in enumerate(evidence_raw):
        p = f"{path}.evidence[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "evidence 要素はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _EVIDENCE_ITEM_KEYS, p, col)
        eid = item.get("id")
        if not _nonblank_str(eid):
            col.add(INVALID_COMPONENT_PAYLOAD, "evidence.id は空にできません", p)
        label = item.get("label")
        if not _nonblank_str(label):
            col.add(EVIDENCE_MAP_STRUCTURE_VIOLATION, "evidence.label は空にできません", p)
        elif len(str(label)) > 40:
            col.add(EVIDENCE_MAP_STRUCTURE_VIOLATION, "evidence.label は40字以内です", p)
        certainty_ref = item.get("certaintyRef")
        if not _nonblank_str(certainty_ref):
            col.add(EVIDENCE_MAP_STRUCTURE_VIOLATION, "certaintyRef は必須です", p)
        elif certainty_ids is not None and certainty_ref not in certainty_ids:
            col.add(EVIDENCE_MAP_STRUCTURE_VIOLATION,
                    f"certaintyRef '{certainty_ref}' が certainty[] に存在しません", p)
        source_ref = item.get("sourceRef")
        if source_ref is not None:
            if not isinstance(source_ref, str) or not source_ref.strip():
                col.add(EVIDENCE_MAP_STRUCTURE_VIOLATION, "sourceRef は空にできません", p)
            elif source_ids is not None and source_ref not in source_ids:
                col.add(EVIDENCE_MAP_STRUCTURE_VIOLATION,
                        f"sourceRef '{source_ref}' が sources[] に存在しません", p)
        evidence.append(EvidenceItem(
            id=eid if isinstance(eid, str) else "",
            label=label if isinstance(label, str) else "",
            certainty_ref=certainty_ref if isinstance(certainty_ref, str) else "",
            source_ref=source_ref if isinstance(source_ref, str) and source_ref.strip() else None,
        ))

    if col or not _nonblank_str(cid):
        return None
    return EvidenceMapPayload(
        conclusion=EvidenceConclusion(
            id=cid, label=clabel if isinstance(clabel, str) else "",
        ),
        evidence=tuple(evidence),
    )


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
        if rel not in _FLOW_RELATIONS:
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
    enumeration = raw.get("enumeration")
    if isinstance(enumeration, dict):
        collect(enumeration.get("items"))
    chevron = raw.get("chevron")
    if isinstance(chevron, dict):
        collect(chevron.get("steps"))
    pyramid = raw.get("pyramid")
    if isinstance(pyramid, dict):
        collect(pyramid.get("tiers"))
    stairs = raw.get("stairs")
    if isinstance(stairs, dict):
        collect(stairs.get("stages"))
    waterfall = raw.get("waterfall")
    if isinstance(waterfall, dict):
        start = waterfall.get("start")
        if isinstance(start, dict) and isinstance(start.get("id"), str):
            ids.append(start["id"])
        collect(waterfall.get("steps"))
        end = waterfall.get("end")
        if isinstance(end, dict) and isinstance(end.get("id"), str):
            ids.append(end["id"])
    logic_tree = raw.get("logic-tree")
    if isinstance(logic_tree, dict):
        root = logic_tree.get("root")
        if isinstance(root, dict) and isinstance(root.get("id"), str):
            ids.append(root["id"])
        branches = logic_tree.get("branches")
        if isinstance(branches, list):
            for branch in branches:
                if isinstance(branch, dict):
                    if isinstance(branch.get("id"), str):
                        ids.append(branch["id"])
                    for leaf in branch.get("leaves") or []:
                        if isinstance(leaf, dict) and isinstance(leaf.get("id"), str):
                            ids.append(leaf["id"])
    slope = raw.get("slope")
    if isinstance(slope, dict):
        collect(slope.get("items"))
    bars = raw.get("bars")
    if isinstance(bars, dict):
        collect(bars.get("items"))
    kpi = raw.get("kpi")
    if isinstance(kpi, dict):
        collect(kpi.get("items"))
    evidence_map = raw.get("evidence-map")
    if isinstance(evidence_map, dict):
        conclusion = evidence_map.get("conclusion")
        if isinstance(conclusion, dict) and isinstance(conclusion.get("id"), str):
            ids.append(conclusion["id"])
        collect(evidence_map.get("evidence"))
    seen: set[str] = set()
    for value in ids:
        if value in seen:
            col.add(DUPLICATE_SEMANTIC_ID, f"意味 ID '{value}' が重複しています", path)
        seen.add(value)


# ---------------------------------------------------------------------------
# Payload dispatch (S1 generalization)
# ---------------------------------------------------------------------------

_PAYLOAD_VALIDATORS = {
    "matrix": _validate_matrix,
    "flow": _validate_flow,
    "enumeration": _validate_enumeration,
    "chevron": _validate_chevron,
    "pyramid": _validate_pyramid,
    "stairs": _validate_stairs,
    "waterfall": _validate_waterfall,
    "logic-tree": _validate_logic_tree,
    "slope": _validate_slope,
    "bars": _validate_bars,
    "kpi": _validate_kpi,
}


def _annotation_targets_matrix(payload: MatrixPayload | None) -> set[str]:
    return {c.id for c in payload.cells} if payload is not None else set()


def _annotation_targets_flow(payload: FlowPayload | None) -> set[str]:
    if payload is None:
        return set()
    return {n.id for n in payload.nodes} | {e.id for e in payload.edges}


def _annotation_targets_enumeration(payload: EnumerationPayload | None) -> set[str]:
    return {item.id for item in payload.items} if payload is not None else set()


def _annotation_targets_chevron(payload: ChevronPayload | None) -> set[str]:
    return {step.id for step in payload.steps} if payload is not None else set()


def _annotation_targets_pyramid(payload: PyramidPayload | None) -> set[str]:
    return {tier.id for tier in payload.tiers} if payload is not None else set()


def _annotation_targets_stairs(payload: StairsPayload | None) -> set[str]:
    return {stage.id for stage in payload.stages} if payload is not None else set()


def _annotation_targets_waterfall(payload: WaterfallPayload | None) -> set[str]:
    if payload is None:
        return set()
    return {payload.start.id, payload.end.id, *(step.id for step in payload.steps)}


def _annotation_targets_logic_tree(payload: LogicTreePayload | None) -> set[str]:
    if payload is None:
        return set()
    targets = {payload.root.id}
    targets.update(branch.id for branch in payload.branches)
    for branch in payload.branches:
        targets.update(leaf.id for leaf in branch.leaves)
    return targets


def _annotation_targets_slope(payload: SlopePayload | None) -> set[str]:
    return {item.id for item in payload.items} if payload is not None else set()


def _annotation_targets_bars(payload: BarsPayload | None) -> set[str]:
    return {item.id for item in payload.items} if payload is not None else set()


def _annotation_targets_kpi(payload: KpiPayload | None) -> set[str]:
    return {item.id for item in payload.items} if payload is not None else set()


def _annotation_targets_evidence_map(payload: EvidenceMapPayload | None) -> set[str]:
    if payload is None:
        return set()
    return {payload.conclusion.id, *(item.id for item in payload.evidence)}


ANNOTATION_TARGETS = {
    "matrix": _annotation_targets_matrix,
    "flow": _annotation_targets_flow,
    "enumeration": _annotation_targets_enumeration,
    "chevron": _annotation_targets_chevron,
    "pyramid": _annotation_targets_pyramid,
    "stairs": _annotation_targets_stairs,
    "waterfall": _annotation_targets_waterfall,
    "logic-tree": _annotation_targets_logic_tree,
    "slope": _annotation_targets_slope,
    "bars": _annotation_targets_bars,
    "kpi": _annotation_targets_kpi,
    "evidence-map": _annotation_targets_evidence_map,
}


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
    # Empty sections allowed until Task 5 replaces this with structure invariants.
    if not isinstance(sections_raw, list):
        col.add(MISSING_REQUIRED_SLOT, "sections は非空の配列である必要があります", "assembly")
        sections_raw = []
    seen_section_ids: set[str] = set()
    doc_type = document.type if document is not None else ""
    for i, item in enumerate(sections_raw):
        p = f"assembly.sections[{i}]"
        section = _validate_section(item, p, col, seen_section_ids, doc_type)
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
    type_val = raw.get("type")
    if not isinstance(type_val, str) or type_val not in _DOCUMENT_TYPES:
        col.add(MISSING_REQUIRED_SLOT, "document.type は proposal / system / research のいずれかが必要です", path)
    profile_val = raw.get("profile")
    if not isinstance(profile_val, str) or profile_val not in _DOCUMENT_PROFILES:
        col.add(MISSING_REQUIRED_SLOT, "document.profile は strict / extended のいずれかが必要です", path)
    return DocumentMetadata(id=raw.get("id", ""), title=raw.get("title", ""), summary=raw.get("summary", ""),
                            type=raw.get("type", ""), profile=raw.get("profile", ""))


def _validate_section(raw: object, path: str, col: DiagnosticCollector, seen_ids: set[str],
                      document_type: str = "") -> object | None:
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
    if kind == "narrative":
        return _validate_narrative_section(raw, path, col, seen_ids)
    if kind == "first-screen":
        return _validate_first_screen_section(raw, path, col, seen_ids)
    if kind == "closing":
        return _validate_closing_section(raw, path, col, seen_ids, document_type)
    if kind == "compatibility":
        return _validate_compatibility_section(raw, path, col, seen_ids)
    col.add(INVALID_COMPONENT_PAYLOAD, f"未知の section.kind '{kind}'", path)
    return None


def _validate_closing_section(raw: dict, path: str, col: DiagnosticCollector, seen_ids: set[str],
                              document_type: str):
    before = len(col.diagnostics)
    _check_keys(raw, _CLOSING_SECTION_KEYS, path, col)
    sid = raw.get("id")
    if not _nonblank_str(sid):
        col.add(INVALID_COMPONENT_PAYLOAD, "closing.id は空にできません", path)
    blocks_raw = raw.get("blocks")
    blocks: list[ClosingBlock] = []
    if not isinstance(blocks_raw, list) or len(blocks_raw) == 0:
        col.add(INVALID_COMPONENT_PAYLOAD, "closing.blocks は非空の配列である必要があります", path)
    else:
        for i, block in enumerate(blocks_raw):
            bp = f"{path}.blocks[{i}]"
            if not isinstance(block, dict):
                col.add(INVALID_COMPONENT_PAYLOAD, "closing.blocks の各要素はオブジェクトである必要があります", bp)
                continue
            _check_keys(block, _CLOSING_BLOCK_KEYS, bp, col)
            heading = block.get("heading")
            if not _nonblank_str(heading):
                col.add(INVALID_COMPONENT_PAYLOAD, "closing.blocks[].heading は空にできません", bp)
            items_raw = block.get("items")
            if not isinstance(items_raw, list):
                col.add(INVALID_COMPONENT_PAYLOAD, "closing.blocks[].items は文字列配列である必要があります", bp)
            elif len(items_raw) == 0:
                col.add(INVALID_COMPONENT_PAYLOAD, "closing.blocks[].items は空にできません", bp)
            elif not all(isinstance(item, str) and item.strip() != "" for item in items_raw):
                col.add(INVALID_COMPONENT_PAYLOAD,
                        "closing.blocks[].items の各要素は非空文字列である必要があります", bp)
            elif _nonblank_str(heading):
                blocks.append(ClosingBlock(heading=heading, items=tuple(items_raw)))
    required = _CLOSING_REQUIRED.get(document_type, ())
    present = {b.heading for b in blocks}
    for heading in required:
        if heading not in present:
            col.add(INVALID_COMPONENT_PAYLOAD,
                    f"closing に必須見出し '{heading}' がありません（document.type={document_type}）", path)
    if len(col.diagnostics) > before:
        return None
    if sid in seen_ids:
        col.add(DUPLICATE_SEMANTIC_ID, f"section id '{sid}' が重複しています", path)
        return None
    seen_ids.add(sid)
    return ClosingSection(id=sid, blocks=tuple(blocks))


def _validate_first_screen_section(raw: dict, path: str, col: DiagnosticCollector, seen_ids: set[str]):
    before = len(col.diagnostics)
    _check_keys(raw, _FIRST_SCREEN_SECTION_KEYS, path, col)
    sid = raw.get("id")
    if not _nonblank_str(sid):
        col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.id は空にできません", path)
    decision = raw.get("decision")
    if not _nonblank_str(decision):
        col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.decision は空にできません", path)
    elif isinstance(decision, str) and not _is_single_sentence(decision):
        col.add(INVALID_COMPONENT_PAYLOAD,
                "first-screen.decision は1文（末尾の 。！？!? がちょうど1個）である必要があります", path)
    conditions_raw = raw.get("conditions", [])
    conditions: tuple[str, ...] = ()
    if not isinstance(conditions_raw, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.conditions は文字列配列である必要があります", path)
    elif len(conditions_raw) > 2:
        col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.conditions は最大2件です", path)
    elif not all(isinstance(c, str) and c.strip() != "" for c in conditions_raw):
        col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.conditions の各要素は非空文字列である必要があります", path)
    else:
        conditions = tuple(conditions_raw)
    if len(col.diagnostics) > before:
        return None
    if sid in seen_ids:
        col.add(DUPLICATE_SEMANTIC_ID, f"section id '{sid}' が重複しています", path)
        return None
    seen_ids.add(sid)
    return FirstScreenSection(id=sid, decision=decision, conditions=conditions)


def _validate_narrative_section(raw: dict, path: str, col: DiagnosticCollector, seen_ids: set[str]):
    # Narrative accepts only id and markup. Provenance, relationship, selection,
    # or asset fields are authoring violations.
    before = len(col.diagnostics)
    for key in raw:
        if key not in _NARRATIVE_SECTION_KEYS:
            col.add(INVALID_NARRATIVE_SECTION, f"narrative に不正なフィールド '{key}'", path)
    sid = raw.get("id")
    if not _nonblank_str(sid):
        col.add(INVALID_NARRATIVE_SECTION, "narrative.id は空にできません", path)
    if not _nonblank_str(raw.get("markup")):
        col.add(INVALID_NARRATIVE_SECTION, "narrative.markup は空にできません", path)
    if len(col.diagnostics) > before:
        return None
    if sid in seen_ids:
        col.add(DUPLICATE_SEMANTIC_ID, f"section id '{sid}' が重複しています", path)
        return None
    seen_ids.add(sid)
    return NarrativeSection(id=sid, markup=raw["markup"])


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
