"""One order-preserving composition route for canonical and compatibility sections.

Canonical sections go through validate → narrow → explicit-select → resolve →
render. Compatibility sections bypass all of that: they are content-safety
validated and wrapped, then enter the very same composer and flattener. The
composer may scope IDs and deduplicate identical assets; it never infers
relationships, chooses components, merges graphs, or creates connectors.
"""
from __future__ import annotations

import html
from dataclasses import dataclass

from .checker import validate_content_markup
from .diagnostics import DUPLICATE_SECTION_ID, RENDERER_FAILURE, ContractError, Diagnostic
from .model import CanonicalSection, CompatibilitySection, RenderManifest
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
class CompositionResult:
    sections_markup: tuple[str, ...]
    style_assets: tuple[AssetRef, ...]
    script_assets: tuple[AssetRef, ...]
    manifests: tuple[RenderManifest, ...]
    compatibility: tuple[WrappedCompatibility, ...]


def _attr(value: str) -> str:
    return html.escape(str(value), quote=True)


def render_canonical(section: CanonicalSection, resolved) -> RenderedCanonical:
    """Render one canonical section and wrap it with provenance data attributes."""
    component = resolved.component
    result = resolved.renderer(section, component)
    if not isinstance(result.markup, str) or not result.markup.strip():
        raise ContractError([Diagnostic(RENDERER_FAILURE, f"renderer '{component.key}' が空の markup を返しました")])
    wrapper = (
        f'<section data-ve-section-kind="canonical" data-ve-component="{_attr(component.id)}"'
        f' data-ve-contract-version="{component.version}" data-ve-instance="{_attr(section.ir.id)}">\n'
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
        style_assets=style_assets, script_assets=script_assets, manifest=result.manifest,
    )


def process_canonical_section(section: CanonicalSection, registry: Registry, renderers) -> RenderedCanonical:
    declaration = section.ir.relationship
    candidates = narrow_candidates(declaration, registry)
    validate_explicit_selection(declaration, section.ir.selection, candidates)
    resolved = resolve_component(section.ir.selection, registry, renderers)
    return render_canonical(section, resolved)


def process_compatibility_section(section: CompatibilitySection) -> WrappedCompatibility:
    diagnostics = validate_content_markup(section.markup)
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


def compose_sections(items) -> CompositionResult:
    """Order-preserving composition with asset deduplication only."""
    markup: list[str] = []
    style_assets: list[AssetRef] = []
    script_assets: list[AssetRef] = []
    manifests: list[RenderManifest] = []
    compatibility: list[WrappedCompatibility] = []
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
        else:
            compatibility.append(item)
    return CompositionResult(
        sections_markup=tuple(markup), style_assets=tuple(style_assets),
        script_assets=tuple(script_assets), manifests=tuple(manifests),
        compatibility=tuple(compatibility),
    )
