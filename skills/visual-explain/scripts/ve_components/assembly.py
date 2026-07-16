"""One order-preserving composition route for canonical and compatibility sections.

Canonical sections go through validate → narrow → explicit-select → resolve →
render. Compatibility sections bypass all of that: they are content-safety
validated and wrapped, then enter the very same composer and flattener. The
composer may scope IDs and deduplicate identical assets; it never infers
relationships, chooses components, merges graphs, or creates connectors.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass

from .checker import extract_flow_dom, validate_content_markup, RENDERER_SVG_ALLOWLIST
from .diagnostics import DUPLICATE_SECTION_ID, RENDERER_FAILURE, ContractError, Diagnostic
from .model import CanonicalSection, CompatibilitySection, NarrativeSection, RenderManifest
from .registry import (
    AssetDefinition,
    Registry,
    narrow_candidates,
    resolve_component,
    validate_explicit_selection,
)
from .validation import validate_canonical_section  # noqa: F401  (spy target: never used on compat)


@dataclass(frozen=True)
class AssetRef:
    component_id: str
    version: int
    asset: AssetDefinition


@dataclass(frozen=True)
class RenderedCanonical:
    instance_id: str
    markup: str
    style_assets: tuple[AssetRef, ...]
    script_assets: tuple[AssetRef, ...]
    manifest: RenderManifest


@dataclass(frozen=True)
class WrappedCompatibility:
    instance_id: str
    markup: str
    source: str
    reason: str


@dataclass(frozen=True)
class WrappedNarrative:
    instance_id: str
    markup: str


@dataclass(frozen=True)
class CompositionResult:
    sections_markup: tuple[str, ...]
    style_assets: tuple[AssetRef, ...]
    script_assets: tuple[AssetRef, ...]
    manifests: tuple[RenderManifest, ...]
    compatibility: tuple[WrappedCompatibility, ...]
    narrative: tuple[WrappedNarrative, ...]


def _attr(value: str) -> str:
    return html.escape(str(value), quote=True)


_SVG_OPEN_RE = re.compile(r"<svg\b([^>]*)>", re.IGNORECASE)


def _svg_open_tags(markup: str) -> tuple[str | None, ...]:
    """Return the id attribute value for every ``<svg>`` open tag (``None`` if absent)."""
    roots: list[str | None] = []
    for match in _SVG_OPEN_RE.finditer(markup):
        attrs = match.group(1)
        id_match = re.search(r'\bid="([^"]+)"', attrs)
        roots.append(id_match.group(1) if id_match else None)
    return tuple(roots)


def render_canonical(section: CanonicalSection, resolved) -> RenderedCanonical:
    """Render one canonical section, verifying the renderer at the trust boundary.

    Renderer-reported diagnostics, undeclared emitted assets, and any manifest
    claim that disagrees with the resolved component (id/version/instance, asset
    ids/digests, fallback) are canonical-render failures — never silently
    filtered or trusted.
    """
    component = resolved.component
    result = resolved.renderer(section, component)
    failures: list[Diagnostic] = []

    if result.diagnostics:
        for item in result.diagnostics:
            failures.append(item if isinstance(item, Diagnostic)
                            else Diagnostic(RENDERER_FAILURE, f"renderer '{component.key}' が診断を報告: {item}"))
    if not isinstance(result.markup, str) or not result.markup.strip():
        failures.append(Diagnostic(RENDERER_FAILURE, f"renderer '{component.key}' が空の markup を返しました"))

    manifest = result.manifest
    if (manifest.component_id != component.id or manifest.component_version != component.version
            or manifest.instance_id != section.ir.id):
        failures.append(Diagnostic(RENDERER_FAILURE, f"renderer '{component.key}' の manifest identity が不一致です"))
    if not isinstance(manifest.fallback_mode, str) or not manifest.fallback_mode.strip():
        failures.append(Diagnostic(RENDERER_FAILURE, f"renderer '{component.key}' の fallback が未宣言です"))

    style_ids = {a.id for a in component.assets if a.slot == "styles"}
    script_ids = {a.id for a in component.assets if a.slot == "scripts"}
    declared = set(result.style_asset_ids) | set(result.script_asset_ids)
    if not set(result.style_asset_ids) <= style_ids or not set(result.script_asset_ids) <= script_ids:
        failures.append(Diagnostic(RENDERER_FAILURE, f"renderer '{component.key}' が未宣言のアセットを出力しました"))
    if set(manifest.asset_ids) != declared:
        failures.append(Diagnostic(RENDERER_FAILURE, f"renderer '{component.key}' の manifest asset ids が宣言と不一致です"))
    if len(manifest.asset_ids) != len(manifest.asset_digests):
        failures.append(Diagnostic(RENDERER_FAILURE, f"renderer '{component.key}' の asset ids と digests が1対1ではありません"))
    digest_by_id = {a.id: a.digest for a in component.assets}
    for aid, adig in zip(manifest.asset_ids, manifest.asset_digests):
        if digest_by_id.get(aid) != adig:
            failures.append(Diagnostic(RENDERER_FAILURE, f"renderer '{component.key}' の manifest digest が不一致です: {aid}"))

    # Manifest completeness against the source IR: no semantic or relationship ID
    # may be silently omitted to escape the final DOM gate.
    if set(manifest.consumed_semantic_ids) != set(section.ir.semantic_ids()):
        failures.append(Diagnostic(RENDERER_FAILURE, f"renderer '{component.key}' の consumed_semantic_ids が IR と不一致です"))
    required_rel = {e.id for e in section.ir.flow.edges} if section.ir.flow is not None else set()
    if set(manifest.generated_relationship_ids) != required_rel:
        failures.append(Diagnostic(RENDERER_FAILURE, f"renderer '{component.key}' の generated_relationship_ids が IR の辺と不一致です"))

    # For flow, the rendered edges/endpoints/relations must equal the IR exactly
    # (no dropped, reversed, or invented edges/nodes).
    if section.ir.flow is not None and isinstance(result.markup, str):
        dom_nodes, dom_edges, incomplete = extract_flow_dom(result.markup)
        if incomplete:
            failures.append(Diagnostic(RENDERER_FAILURE, f"renderer '{component.key}' の flow 辺属性が不完全です"))
        if dom_nodes != {n.id for n in section.ir.flow.nodes}:
            failures.append(Diagnostic(RENDERER_FAILURE, f"renderer '{component.key}' の flow ノードが IR と不一致です"))
        if dom_edges != {(e.source, e.target, e.relation) for e in section.ir.flow.edges}:
            failures.append(Diagnostic(RENDERER_FAILURE, f"renderer '{component.key}' の flow 端点/関係が IR と不一致です"))

    svg_opens = _svg_open_tags(result.markup) if isinstance(result.markup, str) else ()
    declared_svg_ids = tuple(manifest.svg_root_ids)
    if any(svg_id is None for svg_id in svg_opens):
        failures.append(Diagnostic(RENDERER_FAILURE,
                                   f"renderer '{component.key}' の <svg> には id 属性が必須です"))
    emitted_svg_ids = tuple(svg_id for svg_id in svg_opens if svg_id is not None)
    if len(svg_opens) != len(declared_svg_ids):
        failures.append(Diagnostic(RENDERER_FAILURE,
                                   f"renderer '{component.key}' の <svg> 数が manifest.svg_root_ids と不一致です"))
    elif emitted_svg_ids != declared_svg_ids:
        failures.append(Diagnostic(RENDERER_FAILURE,
                                   f"renderer '{component.key}' の SVG ルートが manifest.svg_root_ids と不一致です"))
    if declared_svg_ids and component.key not in RENDERER_SVG_ALLOWLIST:
        failures.append(Diagnostic(RENDERER_FAILURE,
                                   f"renderer '{component.key}' は SVG 出力を宣言できません"))

    if failures:
        raise ContractError(failures)

    wrapper = (
        f'<section data-ve-section-kind="canonical" data-ve-component="{_attr(component.id)}"'
        f' data-ve-contract-version="{component.version}" data-ve-instance="{_attr(section.ir.id)}"'
        f' data-ve-fallback="{_attr(manifest.fallback_mode)}">\n'
        f'{result.markup}\n</section>'
    )
    style_assets = tuple(
        AssetRef(component.id, component.version, a) for a in component.assets
        if a.id in result.style_asset_ids
    )
    script_assets = tuple(
        AssetRef(component.id, component.version, a) for a in component.assets
        if a.id in result.script_asset_ids
    )
    return RenderedCanonical(
        instance_id=section.ir.id, markup=wrapper,
        style_assets=style_assets, script_assets=script_assets, manifest=manifest,
    )


def process_canonical_section(section: CanonicalSection, registry: Registry, renderers) -> RenderedCanonical:
    declaration = section.ir.relationship
    candidates = narrow_candidates(declaration, registry)
    validate_explicit_selection(declaration, section.ir.selection, candidates)
    resolved = resolve_component(section.ir.selection, registry, renderers)
    return render_canonical(section, resolved)


def process_compatibility_section(section: CompatibilitySection) -> WrappedCompatibility:
    diagnostics = validate_content_markup(section.markup, section_kind="compatibility")
    if diagnostics:
        raise ContractError(diagnostics)
    wrapper = (
        f'<section data-ve-section-kind="compatibility"'
        f' data-ve-compat-source="{_attr(section.provenance.source)}"'
        f' data-ve-compat-reason="{_attr(section.provenance.reason)}"'
        f' data-ve-instance="{_attr(section.id)}">\n{section.markup}\n</section>'
    )
    return WrappedCompatibility(
        instance_id=section.id, markup=wrapper,
        source=section.provenance.source, reason=section.provenance.reason,
    )


def process_narrative_section(
    section: NarrativeSection,
    *,
    include_anchor_id: bool = False,
) -> WrappedNarrative:
    diagnostics = validate_content_markup(section.markup, section_kind="narrative")
    if diagnostics:
        raise ContractError(diagnostics)
    id_attr = f' id="{_attr(section.id)}"' if include_anchor_id else ""
    wrapper = (
        f'<section data-ve-section-kind="narrative"'
        f' data-ve-instance="{_attr(section.id)}"{id_attr}>\n'
        f'{section.markup}\n</section>'
    )
    return WrappedNarrative(instance_id=section.id, markup=wrapper)


def compose_sections(items) -> CompositionResult:
    """Order-preserving composition with asset deduplication only."""
    markup: list[str] = []
    style_assets: list[AssetRef] = []
    script_assets: list[AssetRef] = []
    manifests: list[RenderManifest] = []
    compatibility: list[WrappedCompatibility] = []
    narrative: list[WrappedNarrative] = []
    seen_instances: set[str] = set()
    seen_styles: set[tuple] = set()
    seen_scripts: set[tuple] = set()
    for item in items:
        if item.instance_id in seen_instances:
            raise ContractError([Diagnostic(DUPLICATE_SECTION_ID, f"section id '{item.instance_id}' が重複しています")])
        seen_instances.add(item.instance_id)
        markup.append(item.markup)
        if isinstance(item, RenderedCanonical):
            manifests.append(item.manifest)
            for ref in item.style_assets:
                key = (ref.component_id, ref.version, ref.asset.id, ref.asset.digest)
                if key not in seen_styles:
                    seen_styles.add(key)
                    style_assets.append(ref)
            for ref in item.script_assets:
                key = (ref.component_id, ref.version, ref.asset.id, ref.asset.digest)
                if key not in seen_scripts:
                    seen_scripts.add(key)
                    script_assets.append(ref)
        elif isinstance(item, WrappedCompatibility):
            compatibility.append(item)
        elif isinstance(item, WrappedNarrative):
            narrative.append(item)
        elif hasattr(item, "instance_id") and hasattr(item, "markup"):
            # Duck-typed typed document sections (first-screen / closing / ask / toc):
            # markup already recorded; not aggregated into specialized tuples.
            pass
        else:
            raise TypeError(f"compose_sections: unrecognized item type {type(item).__name__}")
    return CompositionResult(
        sections_markup=tuple(markup), style_assets=tuple(style_assets),
        script_assets=tuple(script_assets), manifests=tuple(manifests),
        compatibility=tuple(compatibility), narrative=tuple(narrative),
    )
