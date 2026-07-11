"""Registry parsing with an explicit field allowlist and SHA-256 format checks.

The registry is pure capability metadata. It carries no ranking, heuristic,
theme, animation, or advanced-interaction fields; those are rejected. Candidate
matching is set containment over relationship kind and required capabilities and
never ranks. Resolution fails closed for unknown component, version, renderer,
dependency, asset hash, or checker rule.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .diagnostics import (
    INVALID_ASSET_DEFINITION,
    INVALID_REGISTRY_ENTRY,
    UNKNOWN_CHECKER_RULE,
    UNKNOWN_COMPONENT,
    UNKNOWN_DEPENDENCY,
    UNKNOWN_RENDERER,
    ContractError,
    DiagnosticCollector,
)
from .model import RendererFn
from .validation import VOCABULARY

_COMPONENTS = VOCABULARY["components"]
_ALL_CAPABILITIES = {cap for c in _COMPONENTS.values() for cap in c["capabilities"]}

# Closed set of checker rule names a registry entry may reference.
KNOWN_CHECKER_RULES = frozenset({
    "static-content",
    "semantic-ids",
    "provenance",
    "controlled-assets",
    "fixed-regions",
    "manifest-dom",
    "matrix-references",
    "flow-edges",
    "no-external-reference",
    "escaping",
    "responsive-order",
    "enumeration-structure",
    "chevron-structure",
    "pyramid-structure",
    "stairs-structure",
    "logic-tree-structure",
    "waterfall-consistency",
})

_ASSET_SLOTS = frozenset({"styles", "scripts"})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

_ENTRY_KEYS = {
    "id", "version", "relationshipKind", "capabilities", "semanticResponsibility",
    "requiredInputs", "optionalInputs", "behavior", "slots", "accessibility",
    "responsive", "dependencies", "fallback", "checkerRules", "renderer", "assets",
}
_ASSET_KEYS = {"id", "slot", "path", "digest", "dependency"}


@dataclass(frozen=True)
class AssetDefinition:
    id: str
    slot: str
    path: str
    digest: str
    dependency: Optional[str] = None


@dataclass(frozen=True)
class ComponentDefinition:
    id: str
    version: int
    relationship_kind: str
    capabilities: tuple[str, ...]
    semantic_responsibility: str
    required_inputs: tuple[str, ...]
    optional_inputs: tuple[str, ...]
    behavior: str
    slots: tuple[str, ...]
    accessibility: str
    responsive: bool
    dependencies: tuple[str, ...]
    fallback: str
    checker_rules: tuple[str, ...]
    renderer: str
    assets: tuple[AssetDefinition, ...]

    @property
    def key(self) -> str:
        return f"{self.id}@{self.version}"

    def asset_by_id(self, asset_id: str) -> Optional[AssetDefinition]:
        for asset in self.assets:
            if asset.id == asset_id:
                return asset
        return None


@dataclass(frozen=True)
class Registry:
    registry_version: int
    components: tuple[ComponentDefinition, ...]

    def find(self, component_id: str, version: int) -> Optional[ComponentDefinition]:
        for component in self.components:
            if component.id == component_id and component.version == version:
                return component
        return None


@dataclass(frozen=True)
class CandidateMatch:
    component: ComponentDefinition
    matched_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedComponent:
    component: ComponentDefinition
    renderer: RendererFn


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def load_registry(source: object) -> Registry:
    """Parse a registry dict or JSON file path into an immutable ``Registry``."""
    if isinstance(source, (str, Path)):
        source = json.loads(Path(source).read_text("utf-8"))
    col = DiagnosticCollector()
    if not isinstance(source, dict):
        raise ContractError.single(INVALID_REGISTRY_ENTRY, "registry はオブジェクトである必要があります", "registry")
    for key in source:
        if key not in {"registryVersion", "components"}:
            col.add(INVALID_REGISTRY_ENTRY, f"registry に不正なフィールド '{key}'", "registry")
    if source.get("registryVersion") != 1:
        col.add(INVALID_REGISTRY_ENTRY, f"未知の registryVersion '{source.get('registryVersion')}'", "registry")
    entries = source.get("components")
    components: list[ComponentDefinition] = []
    if not isinstance(entries, list):
        col.add(INVALID_REGISTRY_ENTRY, "components は配列である必要があります", "registry")
        entries = []
    for i, entry in enumerate(entries):
        component = _validate_entry(entry, f"registry.components[{i}]", col)
        if component is not None:
            components.append(component)
    col.raise_if_any()
    return Registry(registry_version=1, components=tuple(components))


def _validate_entry(raw: object, path: str, col: DiagnosticCollector) -> ComponentDefinition | None:
    if not isinstance(raw, dict):
        col.add(INVALID_REGISTRY_ENTRY, "component エントリはオブジェクトである必要があります", path)
        return None
    for key in raw:
        if key not in _ENTRY_KEYS:
            col.add(INVALID_REGISTRY_ENTRY, f"認可されないメタデータ '{key}' (ランキング等は禁止)", path)

    component_id = raw.get("id")
    version = raw.get("version")
    kind = raw.get("relationshipKind")
    caps = raw.get("capabilities")

    if component_id not in _COMPONENTS:
        col.add(INVALID_REGISTRY_ENTRY, f"未知のコンポーネント ID '{component_id}'", path)
    if not _is_int(version) or (component_id in _COMPONENTS and version != _COMPONENTS[component_id]["contractVersion"]):
        col.add(INVALID_REGISTRY_ENTRY, f"未知のバージョン '{version}'", path)
    if component_id in _COMPONENTS and kind != _COMPONENTS[component_id]["relationshipKind"]:
        col.add(INVALID_REGISTRY_ENTRY, f"relationshipKind '{kind}' が '{component_id}' と一致しません", path)
    clean_caps: list[str] = []
    if not isinstance(caps, list) or not caps:
        col.add(INVALID_REGISTRY_ENTRY, "capabilities は非空の配列である必要があります", path)
    else:
        allowed = set(_COMPONENTS.get(component_id, {}).get("capabilities", _ALL_CAPABILITIES))
        for cap in caps:
            if cap not in allowed:
                col.add(INVALID_REGISTRY_ENTRY, f"認可されない capability '{cap}'", path)
            else:
                clean_caps.append(cap)

    for slot, label in (("semanticResponsibility", "semanticResponsibility"), ("behavior", "behavior"),
                        ("accessibility", "accessibility"), ("fallback", "fallback"), ("renderer", "renderer")):
        if not isinstance(raw.get(slot), str) or not raw.get(slot).strip():
            col.add(INVALID_REGISTRY_ENTRY, f"{label} は空にできません", path)
    if not isinstance(raw.get("responsive"), bool) or raw.get("responsive") is not True:
        col.add(INVALID_REGISTRY_ENTRY, "responsive は true である必要があります", path)

    renderer = raw.get("renderer")
    if isinstance(renderer, str) and component_id in _COMPONENTS and _is_int(version):
        if renderer != f"{component_id}@{version}":
            col.add(INVALID_REGISTRY_ENTRY, f"renderer '{renderer}' が '{component_id}@{version}' と一致しません", path)

    checker_rules = raw.get("checkerRules")
    clean_rules: list[str] = []
    if not isinstance(checker_rules, list) or not checker_rules:
        col.add(INVALID_REGISTRY_ENTRY, "checkerRules は非空の配列である必要があります", path)
    else:
        for rule in checker_rules:
            if rule not in KNOWN_CHECKER_RULES:
                col.add(UNKNOWN_CHECKER_RULE, f"未知の checker rule '{rule}'", path)
            else:
                clean_rules.append(rule)

    assets = _validate_assets(raw.get("assets"), f"{path}.assets", col)
    asset_ids = {a.id for a in assets}

    dependencies = raw.get("dependencies", [])
    clean_deps: list[str] = []
    if not isinstance(dependencies, list):
        col.add(INVALID_REGISTRY_ENTRY, "dependencies は配列である必要があります", path)
        dependencies = []
    for dep in dependencies:
        if dep not in asset_ids:
            col.add(UNKNOWN_DEPENDENCY, f"未知の依存 '{dep}'", path)
        else:
            clean_deps.append(dep)
    for asset in assets:
        if asset.dependency is not None and asset.dependency not in asset_ids:
            col.add(UNKNOWN_DEPENDENCY, f"asset 依存 '{asset.dependency}' が存在しません", path)

    required_inputs = _string_tuple(raw.get("requiredInputs"), "requiredInputs", path, col, required=True)
    optional_inputs = _string_tuple(raw.get("optionalInputs", []), "optionalInputs", path, col, required=False)
    slots = _string_tuple(raw.get("slots"), "slots", path, col, required=True)

    if col:
        return None
    return ComponentDefinition(
        id=component_id, version=version, relationship_kind=kind, capabilities=tuple(clean_caps),
        semantic_responsibility=raw["semanticResponsibility"], required_inputs=required_inputs,
        optional_inputs=optional_inputs, behavior=raw["behavior"], slots=slots,
        accessibility=raw["accessibility"], responsive=True, dependencies=tuple(clean_deps),
        fallback=raw["fallback"], checker_rules=tuple(clean_rules), renderer=renderer,
        assets=assets,
    )


def _string_tuple(raw: object, label: str, path: str, col: DiagnosticCollector, *, required: bool) -> tuple[str, ...]:
    if not isinstance(raw, list):
        col.add(INVALID_REGISTRY_ENTRY, f"{label} は配列である必要があります", path)
        return ()
    if required and not raw:
        col.add(INVALID_REGISTRY_ENTRY, f"{label} は非空である必要があります", path)
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            col.add(INVALID_REGISTRY_ENTRY, f"{label} の要素は非空文字列である必要があります", path)
        else:
            out.append(item)
    return tuple(out)


def _validate_assets(raw: object, path: str, col: DiagnosticCollector) -> tuple[AssetDefinition, ...]:
    if not isinstance(raw, list):
        col.add(INVALID_ASSET_DEFINITION, "assets は配列である必要があります", path)
        return ()
    out: list[AssetDefinition] = []
    seen: set[str] = set()
    for i, item in enumerate(raw):
        p = f"{path}[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_ASSET_DEFINITION, "asset はオブジェクトである必要があります", p)
            continue
        for key in item:
            if key not in _ASSET_KEYS:
                col.add(INVALID_ASSET_DEFINITION, f"asset に不正なフィールド '{key}'", p)
        asset_id = item.get("id")
        slot = item.get("slot")
        asset_path = item.get("path")
        digest = item.get("digest")
        if not isinstance(asset_id, str) or not asset_id.strip():
            col.add(INVALID_ASSET_DEFINITION, "asset.id は空にできません", p)
        elif asset_id in seen:
            col.add(INVALID_ASSET_DEFINITION, f"asset.id '{asset_id}' が重複しています", p)
        seen.add(asset_id)
        if slot not in _ASSET_SLOTS:
            col.add(INVALID_ASSET_DEFINITION, f"未知の slot '{slot}'", p)
        if not isinstance(asset_path, str) or not asset_path.strip():
            col.add(INVALID_ASSET_DEFINITION, "asset.path は空にできません", p)
        if not isinstance(digest, str) or not _HEX64.match(digest):
            col.add(INVALID_ASSET_DEFINITION, "asset.digest は 64 桁の SHA-256 hex である必要があります", p)
        dep = item.get("dependency")
        if dep is not None and (not isinstance(dep, str) or not dep.strip()):
            col.add(INVALID_ASSET_DEFINITION, "asset.dependency は非空文字列である必要があります", p)
        out.append(AssetDefinition(id=asset_id, slot=slot, path=asset_path, digest=digest, dependency=dep))
    return tuple(out)


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def narrow_candidates(declaration, registry: Registry) -> list[CandidateMatch]:
    """Return components whose capabilities contain the declared requirements.

    The declaration is validated first; an under-specified declaration raises
    ``invalid_relationship_declaration`` before any matching. Registry order is
    preserved only for stable diagnostics — candidates are never ranked.
    """
    _validate_declaration(declaration)
    declared = set(declaration.capabilities)
    matches: list[CandidateMatch] = []
    for component in registry.components:
        if component.relationship_kind != declaration.kind:
            continue
        if declared <= set(component.capabilities):
            matches.append(CandidateMatch(component=component, matched_capabilities=tuple(declaration.capabilities)))
    return matches


def _validate_declaration(declaration) -> None:
    from .validation import _KIND_TO_COMPONENT  # local import to reuse vocab map
    if declaration.kind not in _KIND_TO_COMPONENT or not declaration.capabilities:
        raise ContractError.single(
            "invalid_relationship_declaration",
            "relationship 宣言が不完全です (kind と capabilities が必要)",
            "relationship",
        )
    for cap in declaration.capabilities:
        if cap not in _ALL_CAPABILITIES:
            raise ContractError.single(
                "invalid_relationship_declaration", f"未知の capability '{cap}'", "relationship")


def validate_explicit_selection(declaration, selection, candidates: list[CandidateMatch]) -> CandidateMatch:
    """Validate an explicit selection against the deterministic candidate set."""
    if not candidates:
        raise ContractError.single(
            "no_matching_component",
            "宣言に一致するコンポーネントがありません",
            "selection",
        )
    chosen = next((c for c in candidates if c.component.id == selection.component and c.component.version == selection.version), None)
    if chosen is None:
        raise ContractError.single(
            "selection_outside_candidate_set",
            f"'{selection.component}@{selection.version}' は候補集合に含まれません",
            "selection",
        )
    declared = set(declaration.capabilities)
    available = set(chosen.component.capabilities)
    matched = set(selection.matched_capabilities)
    if not matched or not (matched <= declared and matched <= available):
        raise ContractError.single(
            "selection_reason_mismatch",
            "matchedCapabilities が宣言とレジストリの両方に存在しません",
            "selection",
        )
    return CandidateMatch(component=chosen.component, matched_capabilities=tuple(selection.matched_capabilities))


def resolve_component(selection, registry: Registry, renderers=None) -> ResolvedComponent:
    """Resolve a validated selection to its component and trusted renderer."""
    if renderers is None:
        from .renderers import TRUSTED_RENDERERS
        renderers = TRUSTED_RENDERERS
    component = registry.find(selection.component, selection.version)
    if component is None:
        raise ContractError.single(
            UNKNOWN_COMPONENT,
            f"未知のコンポーネント '{selection.component}@{selection.version}'",
            "resolve",
        )
    renderer = renderers.get(component.renderer)
    if renderer is None:
        raise ContractError.single(
            UNKNOWN_RENDERER, f"信頼されていない renderer '{component.renderer}'", "resolve")
    return ResolvedComponent(component=component, renderer=renderer)
