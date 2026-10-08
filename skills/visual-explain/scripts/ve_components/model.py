"""Immutable typed model for the component foundation.

Every authoring value becomes a frozen dataclass only after validation. The
model never carries HTML, CSS, JavaScript, or coordinates; renderers turn these
semantic records into markup, and manifests record what was consumed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable, Optional, Tuple

CERTAINTY_LABEL = {"confirmed": "確認済み", "inferred": "推論", "unverified": "未確認"}

# ---------------------------------------------------------------------------
# Document + assembly envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DocumentMetadata:
    id: str
    title: str
    summary: str
    type: str
    profile: str


@dataclass(frozen=True)
class RelationshipDeclaration:
    kind: str
    capabilities: tuple[str, ...]


@dataclass(frozen=True)
class ExplicitSelection:
    component: str
    version: int
    matched_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class CertaintyAssertion:
    id: str
    level: str
    statement: str


@dataclass(frozen=True)
class Source:
    id: str
    label: str
    detail: str = ""


@dataclass(frozen=True)
class AccessibilityInfo:
    label: str
    summary: str


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AxisEntry:
    id: str
    label: str


@dataclass(frozen=True)
class MatrixCell:
    id: str
    row_id: str
    column_id: str
    content: str | tuple[str, ...]
    certainty_ref: Optional[str] = None
    source_ref: Optional[str] = None


@dataclass(frozen=True)
class MatrixPayload:
    rows: tuple[AxisEntry, ...]
    columns: tuple[AxisEntry, ...]
    cells: tuple[MatrixCell, ...]
    highlight_id: Optional[str] = None
    presentation: str = "dense"
    show_column_headers: bool = True


@dataclass(frozen=True)
class EmphasisAnnotation:
    target_id: str
    label: str


@dataclass(frozen=True)
class FlowNode:
    id: str
    label: str
    group: Optional[str] = None


@dataclass(frozen=True)
class FlowEdge:
    id: str
    source: str
    target: str
    relation: str
    label: str = ""


@dataclass(frozen=True)
class FlowGroup:
    id: str
    label: str


@dataclass(frozen=True)
class FlowPayload:
    nodes: tuple[FlowNode, ...]
    edges: tuple[FlowEdge, ...]
    groups: tuple[FlowGroup, ...] = ()
    start_id: Optional[str] = None
    reading_order: tuple[str, ...] = ()


@dataclass(frozen=True)
class EnumerationItem:
    id: str
    label: Optional[str] = None
    title: Optional[str] = None
    description: tuple[str, ...] = ()
    description_emphasis: Optional[str] = None


@dataclass(frozen=True)
class EnumerationPayload:
    items: tuple[EnumerationItem, ...]
    presentation: str = "list"
    block_content: str = "number"


@dataclass(frozen=True)
class ChevronStep:
    id: str
    label: Optional[str] = None
    title: Optional[str] = None
    description: tuple[str, ...] = ()
    description_emphasis: Optional[str] = None


@dataclass(frozen=True)
class ChevronPayload:
    steps: tuple[ChevronStep, ...]
    orientation: str = "vertical"
    block_content: str = "number"
    loop: bool = False


@dataclass(frozen=True)
class PyramidTier:
    id: str
    label: str
    sub: str = ""


@dataclass(frozen=True)
class PyramidPayload:
    tiers: tuple[PyramidTier, ...]


@dataclass(frozen=True)
class StairsStage:
    id: str
    label: str


@dataclass(frozen=True)
class StairsPayload:
    stages: tuple[StairsStage, ...]
    highlight_id: Optional[str] = None


@dataclass(frozen=True)
class WaterfallEndpoint:
    id: str
    label: str
    value: int | Decimal
    value_text: str


@dataclass(frozen=True)
class WaterfallStep:
    id: str
    label: str
    delta: int | Decimal
    value_text: str
    tone: str


@dataclass(frozen=True)
class WaterfallPayload:
    display_precision: int | Decimal
    start: WaterfallEndpoint
    steps: tuple[WaterfallStep, ...]
    end: WaterfallEndpoint
    title: str
    unit_label: str
    axis_ticks: tuple[str, ...]


@dataclass(frozen=True)
class LogicTreeLeaf:
    id: str
    text: str


@dataclass(frozen=True)
class LogicTreeBranch:
    id: str
    label: str
    leaves: tuple[LogicTreeLeaf, ...] = ()


@dataclass(frozen=True)
class LogicTreeRoot:
    id: str
    label: str


@dataclass(frozen=True)
class LogicTreePayload:
    root: LogicTreeRoot
    branches: tuple[LogicTreeBranch, ...]


@dataclass(frozen=True)
class SlopeAxes:
    from_label: str
    to_label: str


@dataclass(frozen=True)
class SlopeItem:
    id: str
    label: str
    from_value: int | Decimal
    to_value: int | Decimal
    from_value_text: str
    to_value_text: str
    tone: str


@dataclass(frozen=True)
class SlopePayload:
    axes: SlopeAxes
    items: tuple[SlopeItem, ...]
    title: str
    unit_label: str
    highlight_id: Optional[str] = None


@dataclass(frozen=True)
class BarsItem:
    id: str
    label: str
    value: int | Decimal
    value_text: str


@dataclass(frozen=True)
class BarsPayload:
    title: str
    unit_label: str
    items: tuple[BarsItem, ...]
    highlight_id: Optional[str] = None


@dataclass(frozen=True)
class KpiItem:
    id: str
    value: str
    unit: str
    caption: str


@dataclass(frozen=True)
class KpiPayload:
    items: tuple[KpiItem, ...]


@dataclass(frozen=True)
class EvidenceConclusion:
    id: str
    label: str


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    label: str
    certainty_ref: str
    source_ref: Optional[str] = None


@dataclass(frozen=True)
class EvidenceMapPayload:
    conclusion: EvidenceConclusion
    evidence: tuple[EvidenceItem, ...]


@dataclass(frozen=True)
class GridNode:
    """A labelled box placed on 1-based grid cells (col, row), spanning cells."""
    id: str
    label: str
    col: int
    row: int
    span_cols: int = 1
    span_rows: int = 1
    tone: str = "base"  # base | primary | warning


@dataclass(frozen=True)
class GridRegion:
    """A labelled enclosure covering the inclusive cell range from..to."""
    id: str
    label: str
    from_col: int
    from_row: int
    to_col: int
    to_row: int


@dataclass(frozen=True)
class GridEdge:
    id: str
    source: str
    target: str
    label: str = ""


@dataclass(frozen=True)
class GridMarker:
    """Overview number ``n`` drawn on node ``target``; ``ask`` optionally names the ask section."""
    n: int
    target: str
    ask: Optional[str] = None


@dataclass(frozen=True)
class GridDiagramPayload:
    cols: int
    rows: int
    nodes: tuple[GridNode, ...]
    regions: tuple[GridRegion, ...] = ()
    edges: tuple[GridEdge, ...] = ()
    markers: tuple[GridMarker, ...] = ()


# ---------------------------------------------------------------------------
# Stage-deck declarations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SequenceStep:
    id: str
    label: str
    target_ids: tuple[str, ...]


@dataclass(frozen=True)
class SequenceDeclaration:
    mode: str
    steps: tuple[SequenceStep, ...]


@dataclass(frozen=True)
class Assertion:
    id: str
    text: str
    cover_ids: tuple[str, ...]


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CanonicalIR:
    id: str
    relationship: RelationshipDeclaration
    selection: ExplicitSelection
    caption: str
    certainty: tuple[CertaintyAssertion, ...]
    sources: tuple[Source, ...]
    accessibility: AccessibilityInfo
    matrix: Optional[MatrixPayload] = None
    flow: Optional[FlowPayload] = None
    enumeration: Optional[EnumerationPayload] = None
    chevron: Optional[ChevronPayload] = None
    pyramid: Optional[PyramidPayload] = None
    stairs: Optional[StairsPayload] = None
    waterfall: Optional[WaterfallPayload] = None
    logic_tree: Optional[LogicTreePayload] = None
    slope: Optional[SlopePayload] = None
    bars: Optional[BarsPayload] = None
    kpi: Optional[KpiPayload] = None
    evidence_map: Optional[EvidenceMapPayload] = None
    grid_diagram: Optional[GridDiagramPayload] = None
    takeaway_target_ids: tuple[str, ...] = ()
    takeaway_scope: str = "targets"
    emphasis: tuple["EmphasisAnnotation", ...] = ()
    claim: Optional[str] = None
    sequence: Optional[SequenceDeclaration] = None
    assertions: Optional[Tuple[Assertion, ...]] = None

    @property
    def payload_kind(self) -> str:
        if self.matrix is not None:
            return "matrix"
        if self.flow is not None:
            return "flow"
        if self.enumeration is not None:
            return "enumeration"
        if self.chevron is not None:
            return "chevron"
        if self.pyramid is not None:
            return "pyramid"
        if self.stairs is not None:
            return "stairs"
        if self.waterfall is not None:
            return "waterfall"
        if self.logic_tree is not None:
            return "logic-tree"
        if self.slope is not None:
            return "slope"
        if self.bars is not None:
            return "bars"
        if self.kpi is not None:
            return "kpi"
        if self.evidence_map is not None:
            return "evidence-map"
        if self.grid_diagram is not None:
            return "grid-diagram"
        raise ValueError("canonical IR has no payload")

    def semantic_ids(self) -> tuple[str, ...]:
        ids: list[str] = [self.id]
        ids.extend(c.id for c in self.certainty)
        ids.extend(s.id for s in self.sources)
        if self.matrix is not None:
            ids.extend(r.id for r in self.matrix.rows)
            ids.extend(c.id for c in self.matrix.columns)
            ids.extend(c.id for c in self.matrix.cells)
        if self.flow is not None:
            ids.extend(n.id for n in self.flow.nodes)
            ids.extend(e.id for e in self.flow.edges)
            ids.extend(g.id for g in self.flow.groups)
        if self.enumeration is not None:
            ids.extend(item.id for item in self.enumeration.items)
        if self.chevron is not None:
            ids.extend(step.id for step in self.chevron.steps)
        if self.pyramid is not None:
            ids.extend(tier.id for tier in self.pyramid.tiers)
        if self.stairs is not None:
            ids.extend(stage.id for stage in self.stairs.stages)
        if self.waterfall is not None:
            ids.append(self.waterfall.start.id)
            ids.extend(step.id for step in self.waterfall.steps)
            ids.append(self.waterfall.end.id)
        if self.logic_tree is not None:
            ids.append(self.logic_tree.root.id)
            for branch in self.logic_tree.branches:
                ids.append(branch.id)
                ids.extend(leaf.id for leaf in branch.leaves)
        if self.slope is not None:
            ids.extend(item.id for item in self.slope.items)
        if self.bars is not None:
            ids.extend(item.id for item in self.bars.items)
        if self.kpi is not None:
            ids.extend(item.id for item in self.kpi.items)
        if self.evidence_map is not None:
            ids.append(self.evidence_map.conclusion.id)
            ids.extend(item.id for item in self.evidence_map.evidence)
        if self.grid_diagram is not None:
            ids.extend(node.id for node in self.grid_diagram.nodes)
            ids.extend(region.id for region in self.grid_diagram.regions)
            ids.extend(edge.id for edge in self.grid_diagram.edges)
        return tuple(ids)


@dataclass(frozen=True)
class CanonicalSection:
    ir: CanonicalIR


@dataclass(frozen=True)
class CompatibilityProvenance:
    source: str
    reason: str
    format: str


@dataclass(frozen=True)
class CompatibilitySection:
    id: str
    markup: str
    provenance: CompatibilityProvenance


@dataclass(frozen=True)
class NarrativeSection:
    id: str
    markup: str


@dataclass(frozen=True)
class OverviewMarker:
    n: int
    label: str
    target: str


@dataclass(frozen=True)
class Overview:
    section: str
    markers: tuple[OverviewMarker, ...]


@dataclass(frozen=True)
class FirstScreenSection:
    id: str
    conclusion: str                     # 1-3 sentences, each <= 80 chars
    overview: Optional[Overview] = None


@dataclass(frozen=True)
class ClosingBlock:
    heading: str
    items: tuple[str, ...]


@dataclass(frozen=True)
class ClosingSection:
    id: str
    blocks: tuple[ClosingBlock, ...]


@dataclass(frozen=True)
class AskOption:
    id: str
    label: str
    tradeoff: str
    benefit: str = ""
    withdrawn: bool = False
    figure: Optional[GridDiagramPayload] = None  # option picture: grid-diagram, 3x3 or smaller


@dataclass(frozen=True)
class AskStep:
    role: str
    role_label: str
    text: str


@dataclass(frozen=True)
class AskClaim:
    text: str
    certainty: str  # confirmed | inferred | unverified


@dataclass(frozen=True)
class AskSection:
    """Discriminated union over ask_type ∈ {decision, request, hypothesis}.

    decision: question + options + default_id (recommended) + evidence
    request: steps
    hypothesis: claim + verify
    Unused arms are None / empty.
    """
    id: str
    ask_type: str
    question: Optional[str] = None
    options: tuple[AskOption, ...] = ()
    default_id: Optional[str] = None
    steps: tuple[AskStep, ...] = ()
    claim: Optional[AskClaim] = None
    verify: Optional[str] = None
    evidence: str = ""


@dataclass(frozen=True)
class AssemblyRequest:
    schema_version: int
    document: DocumentMetadata
    sections: tuple[object, ...]  # CanonicalSection | NarrativeSection | CompatibilitySection, order preserved


# ---------------------------------------------------------------------------
# Render results and manifests
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RenderManifest:
    component_id: str
    component_version: int
    instance_id: str
    consumed_semantic_ids: tuple[str, ...]
    generated_relationship_ids: tuple[str, ...]
    generated_landmark_ids: tuple[str, ...]
    asset_ids: tuple[str, ...]
    asset_digests: tuple[str, ...]
    declared_dependencies: tuple[str, ...]
    fallback_mode: str
    svg_root_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RenderResult:
    markup: str
    style_asset_ids: tuple[str, ...]
    script_asset_ids: tuple[str, ...]
    manifest: RenderManifest
    diagnostics: tuple[object, ...] = ()


# A renderer turns a validated canonical section plus its resolved component
# definition into a RenderResult. Kept structural to avoid import cycles with
# the registry module.
RendererFn = Callable[..., RenderResult]
