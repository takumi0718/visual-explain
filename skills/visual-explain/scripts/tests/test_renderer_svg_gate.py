"""S6 tests: renderer-svg allowlist, manifest cross-check, and bad SVG fixtures."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from ve_components.assembly import render_canonical
from ve_components.checker import RENDERER_SVG_ALLOWLIST, _SVG_ATTR_ALLOWLIST, check_final_document
from ve_components.checker import _validate_svg_subtree
from ve_components.diagnostics import RENDERER_FAILURE, RENDERER_SVG_VIOLATION, ContractError
from ve_components.model import CanonicalSection
from ve_components.registry import ResolvedComponent, load_registry
from ve_components.validation import validate_canonical_section
from ve_components.model import RenderManifest, RenderResult

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS = SKILL / "assets" / "components"

BAD_SVG_FIXTURES = [
    "component-bad-svg-foreign-section.html",
    "component-bad-svg-rect-element.html",
    "component-bad-svg-transform-attr.html",
    "component-bad-svg-xlink-attr.html",
    "component-bad-svg-xmlns-decl.html",
    "component-bad-svg-noninteger-coord.html",
    "component-bad-svg-nested-svg.html",
    "component-bad-svg-foreignobject.html",
]


def _check(name: str) -> set[str]:
    raw = (TESTS / name).read_text("utf-8")
    return {d.code for d in check_final_document(raw, SKELETON, REGISTRY, components_dir=COMPONENTS)}


class RendererSvgGateTest(unittest.TestCase):
    def test_allowlist_contains_only_slope(self) -> None:
        self.assertEqual(RENDERER_SVG_ALLOWLIST, frozenset({"slope@1"}))

    def test_line_allowlist_matches_committed_spec(self) -> None:
        self.assertEqual(
            _SVG_ATTR_ALLOWLIST["line"],
            frozenset({"class", "x1", "y1", "x2", "y2"}),
        )

    def test_line_rejects_semantic_attributes(self) -> None:
        svg = (
            '<svg id="sec-slope-svg" viewBox="0 0 600 220" preserveAspectRatio="xMidYMid meet">'
            '<line class="ve-slope-item" data-ve-semantic-id="sl-up" x1="120" y1="110" x2="480" y2="110"></line>'
            '</svg>'
        )
        codes = {d.code for d in _validate_svg_subtree(svg)}
        self.assertIn(RENDERER_SVG_VIOLATION, codes)

    def test_g_accepts_slope_semantic_attributes(self) -> None:
        svg = (
            '<svg id="sec-slope-svg" viewBox="0 0 600 220" preserveAspectRatio="xMidYMid meet">'
            '<g class="ve-slope-row" data-ve-semantic-id="sl-up" data-ve-takeaway="true">'
            '<line class="ve-slope-item" x1="120" y1="110" x2="480" y2="110"></line>'
            '</g>'
            '</svg>'
        )
        self.assertEqual(_validate_svg_subtree(svg), [])

    def test_bad_svg_fixtures_raise_violation(self) -> None:
        for name in BAD_SVG_FIXTURES:
            with self.subTest(fixture=name):
                self.assertIn(RENDERER_SVG_VIOLATION, _check(name))

    def test_boundary_valid_fixture_passes(self) -> None:
        self.assertEqual(_check("component-valid-svg-boundary.html"), set())

    def test_slope_structure_bad_fixture(self) -> None:
        codes = [d.code for d in check_final_document(
            (TESTS / "component-bad-slope-structure.html").read_text("utf-8"),
            SKELETON,
            REGISTRY,
            components_dir=COMPONENTS,
        )]
        self.assertEqual(codes.count("slope_structure_violation"), 1)

    def test_slope_missing_line_fixture(self) -> None:
        codes = [d.code for d in check_final_document(
            (TESTS / "component-bad-slope-missing-line.html").read_text("utf-8"),
            SKELETON,
            REGISTRY,
            components_dir=COMPONENTS,
        )]
        self.assertIn("slope_structure_violation", codes)
        messages = " ".join(d.message for d in check_final_document(
            (TESTS / "component-bad-slope-missing-line.html").read_text("utf-8"),
            SKELETON,
            REGISTRY,
            components_dir=COMPONENTS,
        ) if d.code == "slope_structure_violation")
        self.assertIn("line.ve-slope-item", messages)

    def test_slope_duplicate_line_fixture(self) -> None:
        codes = [d.code for d in check_final_document(
            (TESTS / "component-bad-slope-duplicate-line.html").read_text("utf-8"),
            SKELETON,
            REGISTRY,
            components_dir=COMPONENTS,
        )]
        self.assertIn("slope_structure_violation", codes)
        messages = " ".join(d.message for d in check_final_document(
            (TESTS / "component-bad-slope-duplicate-line.html").read_text("utf-8"),
            SKELETON,
            REGISTRY,
            components_dir=COMPONENTS,
        ) if d.code == "slope_structure_violation")
        self.assertIn("line.ve-slope-item", messages)


class RenderCanonicalSvgGateTest(unittest.TestCase):
    def test_undeclared_svg_is_renderer_failure(self) -> None:
        slope_def = REGISTRY.find("slope", 1)
        raw = json.loads((TESTS / "component-valid-slope.json").read_text("utf-8"))
        ir = validate_canonical_section(raw["sections"][0]["ir"])
        section = CanonicalSection(ir=ir)

        def stub_renderer(section, definition):
            return RenderResult(
                markup=(
                    f'<figure data-ve-component="slope">'
                    f'<svg id="{section.ir.id}-svg" viewBox="0 0 600 220"></svg>'
                    f'</figure>'
                ),
                style_asset_ids=("slope.css",),
                script_asset_ids=(),
                manifest=RenderManifest(
                    component_id="slope",
                    component_version=1,
                    instance_id=section.ir.id,
                    consumed_semantic_ids=section.ir.semantic_ids(),
                    generated_relationship_ids=(),
                    generated_landmark_ids=(f"{section.ir.id}-caption", f"{section.ir.id}-summary"),
                    asset_ids=("slope.css",),
                    asset_digests=(slope_def.assets[0].digest,),
                    declared_dependencies=(),
                    fallback_mode="static-content",
                ),
            )

        resolved = ResolvedComponent(component=slope_def, renderer=stub_renderer)
        with self.assertRaises(ContractError) as ctx:
            render_canonical(section, resolved)
        self.assertIn(RENDERER_FAILURE, {d.code for d in ctx.exception.diagnostics})

    def test_id_less_svg_is_renderer_failure(self) -> None:
        slope_def = REGISTRY.find("slope", 1)
        raw = json.loads((TESTS / "component-valid-slope.json").read_text("utf-8"))
        ir = validate_canonical_section(raw["sections"][0]["ir"])
        section = CanonicalSection(ir=ir)

        def stub_renderer(section, definition):
            return RenderResult(
                markup=(
                    f'<figure data-ve-component="slope">'
                    f'<svg viewBox="0 0 600 220"></svg>'
                    f'</figure>'
                ),
                style_asset_ids=("slope.css",),
                script_asset_ids=(),
                manifest=RenderManifest(
                    component_id="slope",
                    component_version=1,
                    instance_id=section.ir.id,
                    consumed_semantic_ids=section.ir.semantic_ids(),
                    generated_relationship_ids=(),
                    generated_landmark_ids=(f"{section.ir.id}-caption", f"{section.ir.id}-summary"),
                    asset_ids=("slope.css",),
                    asset_digests=(slope_def.assets[0].digest,),
                    declared_dependencies=(),
                    fallback_mode="static-content",
                    svg_root_ids=(),
                ),
            )

        resolved = ResolvedComponent(component=slope_def, renderer=stub_renderer)
        with self.assertRaises(ContractError) as ctx:
            render_canonical(section, resolved)
        codes = {d.code for d in ctx.exception.diagnostics}
        self.assertIn(RENDERER_FAILURE, codes)
        messages = " ".join(d.message for d in ctx.exception.diagnostics)
        self.assertIn("id", messages.lower())

    def test_extra_undeclared_svg_with_id_is_renderer_failure(self) -> None:
        slope_def = REGISTRY.find("slope", 1)
        raw = json.loads((TESTS / "component-valid-slope.json").read_text("utf-8"))
        ir = validate_canonical_section(raw["sections"][0]["ir"])
        section = CanonicalSection(ir=ir)
        svg_id = f"{section.ir.id}-svg"

        def stub_renderer(section, definition):
            return RenderResult(
                markup=(
                    f'<figure data-ve-component="slope">'
                    f'<svg id="{svg_id}" viewBox="0 0 600 220"></svg>'
                    f'<svg id="extra-svg" viewBox="0 0 600 220"></svg>'
                    f'</figure>'
                ),
                style_asset_ids=("slope.css",),
                script_asset_ids=(),
                manifest=RenderManifest(
                    component_id="slope",
                    component_version=1,
                    instance_id=section.ir.id,
                    consumed_semantic_ids=section.ir.semantic_ids(),
                    generated_relationship_ids=(),
                    generated_landmark_ids=(f"{section.ir.id}-caption", f"{section.ir.id}-summary", svg_id),
                    asset_ids=("slope.css",),
                    asset_digests=(slope_def.assets[0].digest,),
                    declared_dependencies=(),
                    fallback_mode="static-content",
                    svg_root_ids=(svg_id,),
                ),
            )

        resolved = ResolvedComponent(component=slope_def, renderer=stub_renderer)
        with self.assertRaises(ContractError) as ctx:
            render_canonical(section, resolved)
        self.assertIn(RENDERER_FAILURE, {d.code for d in ctx.exception.diagnostics})

    def test_non_allowlisted_component_cannot_declare_svg_root_ids(self) -> None:
        stairs_def = REGISTRY.find("stairs", 2)
        raw = json.loads((TESTS / "component-valid-stairs.json").read_text("utf-8"))
        ir = validate_canonical_section(raw["sections"][0]["ir"])
        section = CanonicalSection(ir=ir)

        def stub_renderer(section, definition):
            return RenderResult(
                markup='<figure data-ve-component="stairs"><p>x</p></figure>',
                style_asset_ids=("stairs.css",),
                script_asset_ids=(),
                manifest=RenderManifest(
                    component_id="stairs",
                    component_version=1,
                    instance_id=section.ir.id,
                    consumed_semantic_ids=section.ir.semantic_ids(),
                    generated_relationship_ids=(),
                    generated_landmark_ids=(f"{section.ir.id}-caption", f"{section.ir.id}-summary"),
                    asset_ids=("stairs.css",),
                    asset_digests=(stairs_def.assets[0].digest,),
                    declared_dependencies=(),
                    fallback_mode="static-content",
                    svg_root_ids=(f"{section.ir.id}-svg",),
                ),
            )

        resolved = ResolvedComponent(component=stairs_def, renderer=stub_renderer)
        with self.assertRaises(ContractError) as ctx:
            render_canonical(section, resolved)
        self.assertIn(RENDERER_FAILURE, {d.code for d in ctx.exception.diagnostics})


if __name__ == "__main__":
    unittest.main()
