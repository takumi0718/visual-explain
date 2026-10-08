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
from html.parser import HTMLParser
from dataclasses import dataclass, replace

from .checker import extract_flow_dom, validate_content_markup, RENDERER_SVG_ALLOWLIST
from .diagnostics import DUPLICATE_SECTION_ID, RENDERER_FAILURE, ContractError, Diagnostic
from .model import (
    Assertion,
    CanonicalSection,
    CompatibilitySection,
    NarrativeSection,
    RenderManifest,
    SequenceDeclaration,
)
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
class ExpectedCanonicalRecord:
    """Validated IR facts retained for later final-document checks."""
    component_id: str
    instance_id: str
    payload_semantic_ids: frozenset[str]
    claim: str | None
    assertions: tuple[Assertion, ...] | None
    sequence: SequenceDeclaration | None
    generated_dom_id_bases: tuple[str, ...] = ()


@dataclass(frozen=True)
class RenderedCanonical:
    instance_id: str
    markup: str
    style_assets: tuple[AssetRef, ...]
    script_assets: tuple[AssetRef, ...]
    manifest: RenderManifest
    expected_record: ExpectedCanonicalRecord | None = None


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
    expected_records: tuple[ExpectedCanonicalRecord, ...] = ()


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


def _expected_generated_dom_id_bases(
    manifest: RenderManifest,
    sequence: SequenceDeclaration | None,
) -> tuple[str, ...]:
    ids = tuple(dict.fromkeys(manifest.generated_landmark_ids + manifest.svg_root_ids))
    if sequence is None:
        return ids
    panel_numbers = range(1, len(sequence.steps) + 2)
    bases: list[str] = []
    for dom_id in ids:
        matches = [number for number in panel_numbers if dom_id.endswith(f"--p{number}")]
        if len(matches) != 1:
            continue
        suffix = f"--p{matches[0]}"
        base = dom_id[:-len(suffix)]
        if base not in bases:
            bases.append(base)
    return tuple(bases)


def _expected_record(
    section: CanonicalSection,
    component_id: str,
    manifest: RenderManifest,
) -> ExpectedCanonicalRecord:
    ir = section.ir
    non_payload_ids = {ir.id}
    non_payload_ids.update(item.id for item in ir.certainty)
    non_payload_ids.update(item.id for item in ir.sources)
    return ExpectedCanonicalRecord(
        component_id=component_id,
        instance_id=ir.id,
        payload_semantic_ids=frozenset(ir.semantic_ids()) - non_payload_ids,
        claim=ir.claim,
        assertions=ir.assertions,
        sequence=ir.sequence,
        generated_dom_id_bases=_expected_generated_dom_id_bases(manifest, ir.sequence),
    )


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
        expected_record=_expected_record(section, component.id, manifest),
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


def _linecol_to_index(text: str, lineno: int, col: int) -> int:
    """Convert 1-based lineno + 0-based col (HTMLParser.getpos) to a string index.

    HTMLParser counts lines by "\n" only; splitting on universal newlines
    (splitlines) would also break on lone "\r" and desynchronize offsets.
    """
    offset = 0
    for _ in range(lineno - 1):
        offset = text.index("\n", offset) + 1
    return offset + col


def insert_link_domain_markers(markup: str) -> str:
    """Insert ``<span class="link-domain">‹hostname›</span>`` before ``</a>`` of https anchors.

    hostname comes from ``urllib.parse.urlsplit(href).hostname`` (IDN preserved).
    Call only after content-safety validation has rejected author ``link-domain`` classes.
    """
    from html.parser import HTMLParser
    from urllib.parse import urlsplit

    class _Finder(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=False)
            self.stack: list[str | None] = []
            # (index of '</a>', hostname) — insert marker immediately before this index
            self.inserts: list[tuple[int, str]] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag.lower() != "a":
                return
            href = None
            for name, value in attrs:
                if name.lower() == "href" and value is not None:
                    href = value.strip()
                    break
            host: str | None = None
            if href and href.lower().startswith("https://"):
                host = urlsplit(href).hostname
            self.stack.append(host)

        def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            # Void / self-closing <a> has no inner content to annotate.
            if tag.lower() == "a":
                return

        def handle_endtag(self, tag: str) -> None:
            if tag.lower() != "a" or not self.stack:
                return
            host = self.stack.pop()
            if not host:
                return
            lineno, col = self.getpos()
            self.inserts.append((_linecol_to_index(markup, lineno, col), host))

    finder = _Finder()
    finder.feed(markup)
    finder.close()
    if not finder.inserts:
        return markup
    parts: list[str] = []
    cursor = 0
    for index, host in finder.inserts:
        parts.append(markup[cursor:index])
        parts.append(f'<span class="link-domain">‹{html.escape(host)}›</span>')
        cursor = index
    parts.append(markup[cursor:])
    return "".join(parts)


def process_narrative_section(
    section: NarrativeSection,
    *,
    include_anchor_id: bool = False,
    marker: int | None = None,
) -> WrappedNarrative:
    diagnostics = validate_content_markup(section.markup, section_kind="narrative")
    if diagnostics:
        raise ContractError(diagnostics)
    body = insert_link_domain_markers(section.markup)
    if marker is not None:
        from .document_sections import mark_first_heading
        body = mark_first_heading(body, marker)
    id_attr = f' id="{_attr(section.id)}"' if include_anchor_id else ""
    wrapper = (
        f'<section data-ve-section-kind="narrative"'
        f' data-ve-instance="{_attr(section.id)}"{id_attr}>\n'
        f'{body}\n</section>'
    )
    return WrappedNarrative(instance_id=section.id, markup=wrapper)


def option_figure_ids(asks) -> frozenset[str]:
    """DOM ids the option pictures generate (svg and text twin), per ask and option number."""
    return frozenset(
        f"{ask.id}-opt-{index}-{suffix}"
        for ask in asks for index, option in enumerate(ask.options, start=1)
        if option.figure is not None for suffix in ("svg", "relations"))


class _IdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        for name, value in attrs:
            if name == "id" and value is not None:
                self.ids.append(value)


def rendered_dom_ids(markup: str) -> list[str]:
    """Every id attribute value in rendered markup, duplicates kept."""
    collector = _IdCollector()
    collector.feed(markup)
    collector.close()
    return collector.ids


def option_figure_id_clashes(asks, rendered_markups, semantic_ids) -> list[str]:
    """Option-picture ids that some other generated DOM id or IR semantic id already uses.

    The pictures' own ids appear once in their ask's markup, so any second
    occurrence anywhere in the rendered sections (canonical figures, overview
    list, panels) or any equal semantic id is a clash.
    """
    picture_ids = option_figure_ids(asks)
    counts: dict[str, int] = {}
    for markup in rendered_markups:
        for value in rendered_dom_ids(markup):
            counts[value] = counts.get(value, 0) + 1
    taken = set(semantic_ids)
    return sorted(i for i in picture_ids if counts.get(i, 0) > 1 or i in taken)


def add_option_figure_assets(composition: CompositionResult, asks, registry: Registry) -> CompositionResult:
    """Option pictures reuse the grid-diagram stylesheet, even with no canonical grid-diagram."""
    if not any(option.figure is not None for ask in asks for option in ask.options):
        return composition
    component = registry.find("grid-diagram", 2)
    asset = component.asset_by_id("grid-diagram.css") if component is not None else None
    if asset is None:
        raise ContractError([Diagnostic(RENDERER_FAILURE, "選択肢の図には grid-diagram の資産が必要です")])
    if any(ref.asset.id == asset.id for ref in composition.style_assets):
        return composition
    return replace(composition, style_assets=composition.style_assets + (AssetRef("grid-diagram", 2, asset),))


def compose_sections(items) -> CompositionResult:
    """Order-preserving composition with asset deduplication only."""
    markup: list[str] = []
    style_assets: list[AssetRef] = []
    script_assets: list[AssetRef] = []
    manifests: list[RenderManifest] = []
    compatibility: list[WrappedCompatibility] = []
    narrative: list[WrappedNarrative] = []
    expected_records: list[ExpectedCanonicalRecord] = []
    seen_instances: set[str] = set()
    seen_styles: set[tuple] = set()
    seen_scripts: set[tuple] = set()
    for item in items:
        if item.instance_id in seen_instances:
            raise ContractError([Diagnostic(DUPLICATE_SECTION_ID, f"section id '{item.instance_id}' が重複しています")])
        seen_instances.add(item.instance_id)
        markup.append(item.markup)
        if isinstance(item, RenderedCanonical):
            if item.expected_record is None:
                raise ContractError([Diagnostic(
                    RENDERER_FAILURE,
                    f"canonical '{item.instance_id}' に expected record がありません",
                )])
            manifests.append(item.manifest)
            expected_records.append(item.expected_record)
            for ref in item.style_assets:
                key = (ref.asset.id, ref.asset.digest)
                if key not in seen_styles:
                    seen_styles.add(key)
                    style_assets.append(ref)
            for ref in item.script_assets:
                key = (ref.asset.id, ref.asset.digest)
                if key not in seen_scripts:
                    seen_scripts.add(key)
                    script_assets.append(ref)
        elif isinstance(item, WrappedCompatibility):
            compatibility.append(item)
        elif isinstance(item, WrappedNarrative):
            narrative.append(item)
        elif hasattr(item, "instance_id") and hasattr(item, "markup"):
            # Duck-typed typed document sections (first-screen / closing / ask / toc / decision-panel):
            # markup already recorded; not aggregated into specialized tuples.
            pass
        else:
            raise TypeError(f"compose_sections: unrecognized item type {type(item).__name__}")
    return CompositionResult(
        sections_markup=tuple(markup), style_assets=tuple(style_assets),
        script_assets=tuple(script_assets), manifests=tuple(manifests),
        compatibility=tuple(compatibility), narrative=tuple(narrative),
        expected_records=tuple(expected_records),
    )
