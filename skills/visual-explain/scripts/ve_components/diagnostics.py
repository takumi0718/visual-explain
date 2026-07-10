"""Bounded diagnostics for the component foundation.

The diagnostic vocabulary is a small, closed set. Later tasks consume these
exact codes; nothing invents new ones. A ``ContractError`` carries one or more
diagnostics and is raised, never silently swallowed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Task 1 — contract / IR codes.
INVALID_RELATIONSHIP_DECLARATION = "invalid_relationship_declaration"
INVALID_COMPONENT_PAYLOAD = "invalid_component_payload"
DUPLICATE_SEMANTIC_ID = "duplicate_semantic_id"
INVALID_MATRIX_REFERENCE = "invalid_matrix_reference"
INVALID_FLOW_EDGE = "invalid_flow_edge"
MISSING_REQUIRED_SLOT = "missing_required_slot"
FORBIDDEN_AUTHORING_FIELD = "forbidden_authoring_field"
INVALID_COMPATIBILITY_PROVENANCE = "invalid_compatibility_provenance"

# Task 2 — selection codes.
NO_MATCHING_COMPONENT = "no_matching_component"
SELECTION_OUTSIDE_CANDIDATE_SET = "selection_outside_candidate_set"
SELECTION_REASON_MISMATCH = "selection_reason_mismatch"

# Task 2 — registry / fail-closed resolution codes.
INVALID_REGISTRY_ENTRY = "invalid_registry_entry"
UNKNOWN_COMPONENT = "unknown_component"
UNKNOWN_RENDERER = "unknown_renderer"
UNKNOWN_DEPENDENCY = "unknown_dependency"
UNKNOWN_CHECKER_RULE = "unknown_checker_rule"
INVALID_ASSET_DEFINITION = "invalid_asset_definition"

# Task 3 — skeleton / safety codes.
MISSING_CONTROLLED_MARKER = "missing_controlled_marker"
FIXED_REGION_MISMATCH = "fixed_region_mismatch"
FORBIDDEN_CONTENT_MARKUP = "forbidden_content_markup"
INVALID_CONTROLLED_ASSET = "invalid_controlled_asset"

# Task 4 — assembly / composition codes.
DUPLICATE_SECTION_ID = "duplicate_section_id"
RENDERER_FAILURE = "renderer_failure"
FINAL_CHECK_FAILURE = "final_check_failure"

# Task 7 — manifest-to-DOM / final provenance codes.
MANIFEST_DOM_MISMATCH = "manifest_dom_mismatch"
MISSING_PROVENANCE = "missing_provenance"

ALL_CODES = frozenset({
    INVALID_RELATIONSHIP_DECLARATION,
    INVALID_COMPONENT_PAYLOAD,
    DUPLICATE_SEMANTIC_ID,
    INVALID_MATRIX_REFERENCE,
    INVALID_FLOW_EDGE,
    MISSING_REQUIRED_SLOT,
    FORBIDDEN_AUTHORING_FIELD,
    INVALID_COMPATIBILITY_PROVENANCE,
    NO_MATCHING_COMPONENT,
    SELECTION_OUTSIDE_CANDIDATE_SET,
    SELECTION_REASON_MISMATCH,
    INVALID_REGISTRY_ENTRY,
    UNKNOWN_COMPONENT,
    UNKNOWN_RENDERER,
    UNKNOWN_DEPENDENCY,
    UNKNOWN_CHECKER_RULE,
    INVALID_ASSET_DEFINITION,
    MISSING_CONTROLLED_MARKER,
    FIXED_REGION_MISMATCH,
    FORBIDDEN_CONTENT_MARKUP,
    INVALID_CONTROLLED_ASSET,
    DUPLICATE_SECTION_ID,
    RENDERER_FAILURE,
    FINAL_CHECK_FAILURE,
    MANIFEST_DOM_MISMATCH,
    MISSING_PROVENANCE,
})


@dataclass(frozen=True)
class Diagnostic:
    """One bounded, human-readable finding."""

    code: str
    message: str
    path: str = ""

    def __post_init__(self) -> None:
        if self.code not in ALL_CODES:
            raise ValueError(f"unknown diagnostic code: {self.code}")

    def __str__(self) -> str:
        where = f" [{self.path}]" if self.path else ""
        return f"{self.code}: {self.message}{where}"


class ContractError(Exception):
    """Raised when authoring, registry, or checker contracts are violated."""

    def __init__(self, diagnostics: list[Diagnostic]):
        if not diagnostics:
            raise ValueError("ContractError requires at least one diagnostic")
        self.diagnostics = list(diagnostics)
        super().__init__("; ".join(str(d) for d in self.diagnostics))

    @classmethod
    def single(cls, code: str, message: str, path: str = "") -> "ContractError":
        return cls([Diagnostic(code, message, path)])

    @property
    def codes(self) -> set[str]:
        return {d.code for d in self.diagnostics}


@dataclass
class DiagnosticCollector:
    """Accumulates diagnostics so a validator can report several at once."""

    diagnostics: list[Diagnostic] = field(default_factory=list)

    def add(self, code: str, message: str, path: str = "") -> None:
        self.diagnostics.append(Diagnostic(code, message, path))

    def __bool__(self) -> bool:
        return bool(self.diagnostics)

    def raise_if_any(self) -> None:
        if self.diagnostics:
            raise ContractError(self.diagnostics)
