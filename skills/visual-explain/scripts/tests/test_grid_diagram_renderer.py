"""Phase 4: grid-diagram registration, renderer DOM contract, and the final checker."""
from __future__ import annotations

import copy
import json
import unittest
from decimal import Decimal
from pathlib import Path

from build_explainer import build_document
from fixture_util import canonical_ir
from ve_components.checker import check_final_document
from ve_components.diagnostics import ContractError
from ve_components.model import CanonicalSection
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.renderers.grid_diagram import render_grid_diagram
from ve_components.validation import validate_assembly, validate_canonical_section

SKILL = Path(__file__).resolve().parents[2]
TESTS = SKILL / "scripts" / "tests"
COMPONENTS = SKILL / "assets" / "components"
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
REGISTRY = load_registry(COMPONENTS / "registry.json")
FIXTURE = "component-valid-grid-diagram.json"


def raw_fixture() -> dict:
    return json.loads((TESTS / FIXTURE).read_text("utf-8"), parse_float=Decimal)


def build(raw: dict) -> str:
    return build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS,
                          document_path="grid-diagram-doc.html")


def check(html: str) -> list[str]:
    return [d.message for d in check_final_document(html, SKELETON, REGISTRY, components_dir=COMPONENTS)]


class RegistrationTest(unittest.TestCase):
    def test_registry_and_renderer_allowlist_know_grid_diagram(self) -> None:
        definition = REGISTRY.find("grid-diagram", 2)
        self.assertIsNotNone(definition)
        self.assertEqual(definition.relationship_kind, "spatial-layout")
        self.assertEqual(definition.capabilities, ("spatial-placement",))
        self.assertEqual(definition.renderer, "grid-diagram@2")
        self.assertIn("grid-diagram@2", TRUSTED_RENDERERS)
        self.assertEqual([a.id for a in definition.assets], ["grid-diagram.css", "visual-stage"])

    def test_fixture_validates_as_a_canonical_section(self) -> None:
        ir = validate_canonical_section(canonical_ir(raw_fixture()))
        self.assertEqual(ir.payload_kind, "grid-diagram")
        self.assertEqual(ir.semantic_ids(), (
            "sec-grid", "cert-grid", "src-grid", "exception", "price", "approval", "rollback",
            "legal", "e-exception", "e-price", "e-rollback"))

    def test_annotations_are_not_offered_for_grid_diagram(self) -> None:
        ir = canonical_ir(raw_fixture())
        ir["takeawayTargetIds"] = ["approval"]
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(ir)
        self.assertIn("注釈対象が未登録のペイロード 'grid-diagram'", [d.message for d in ctx.exception.diagnostics])

    def test_semantic_ids_collide_with_certainty_ids(self) -> None:
        ir = canonical_ir(raw_fixture())
        ir["grid-diagram"]["nodes"][0]["id"] = "cert-grid"
        ir["grid-diagram"]["edges"][0]["from"] = "cert-grid"
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(ir)
        self.assertIn("意味 ID 'cert-grid' が重複しています", [d.message for d in ctx.exception.diagnostics])


class RendererTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ir = validate_canonical_section(canonical_ir(raw_fixture()))
        cls.result = render_grid_diagram(CanonicalSection(ir=ir), REGISTRY.find("grid-diagram", 2))
        cls.markup = cls.result.markup

    def test_figure_declares_its_grid_and_svg_viewbox_follows(self) -> None:
        self.assertIn('<figure data-ve-component="grid-diagram" class="ve-gd" data-ve-grid="4x3"', self.markup)
        self.assertIn('<svg id="sec-grid-svg" class="ve-gd-svg ve-gd-cols-4" viewBox="0 0 600 288"'
                      ' preserveAspectRatio="xMidYMid meet" role="img" aria-label="承認の配置図"'
                      ' aria-describedby="sec-grid-relations">', self.markup)

    def test_node_is_a_rect_and_centred_text_at_fixed_coordinates(self) -> None:
        self.assertIn(
            '<g class="ve-gd-node ve-gd-tone-primary" data-ve-semantic-id="approval">'
            '<rect class="ve-gd-node-box" x="316" y="118" width="118" height="52"></rect>'
            '<text class="ve-gd-node-label" x="375" y="149" text-anchor="middle">共同承認</text></g>',
            self.markup)

    def test_edge_is_line_pairs_with_one_bend_and_a_two_stroke_arrowhead(self) -> None:
        self.assertIn(
            '<g class="ve-gd-edge" data-ve-semantic-id="e-exception">'
            '<line class="ve-gd-edge-line" x1="134" y1="48" x2="375" y2="48"></line>'
            '<line class="ve-gd-edge-line" x1="375" y1="48" x2="375" y2="118"></line>'
            '<line class="ve-gd-edge-arrow" x1="371" y1="112" x2="375" y2="118"></line>'
            '<line class="ve-gd-edge-arrow" x1="379" y1="112" x2="375" y2="118"></line>'
            '<text class="ve-gd-edge-label" x="254" y="41" text-anchor="middle">照合</text></g>',
            self.markup)

    def test_region_is_a_frame_with_a_label(self) -> None:
        self.assertIn(
            '<g class="ve-gd-region" data-ve-semantic-id="legal">'
            '<rect class="ve-gd-region-frame" x="4" y="4" width="142" height="280"></rect>'
            '<text class="ve-gd-region-label" x="12" y="18" text-anchor="start">根拠</text></g>',
            self.markup)

    def test_reading_list_follows_the_picture(self) -> None:
        self.assertIn('<li class="ve-gd-rel-node">契約例外（根拠）</li>', self.markup)
        self.assertIn('<li class="ve-gd-rel-edge">契約例外 → 共同承認（照合）</li>', self.markup)
        self.assertIn('<li class="ve-gd-rel-edge">料金改定案 → 共同承認</li>', self.markup)

    def test_manifest_declares_the_svg_root_and_landmarks(self) -> None:
        manifest = self.result.manifest
        self.assertEqual(manifest.svg_root_ids, ("sec-grid-svg",))
        self.assertEqual(manifest.generated_landmark_ids,
                         ("sec-grid-caption", "sec-grid-summary", "sec-grid-relations", "sec-grid-svg"))
        self.assertEqual(self.result.style_asset_ids, ("grid-diagram.css",))


class FinalCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = build(raw_fixture())

    def test_built_fixture_passes_every_layer(self) -> None:
        self.assertEqual(check(self.html), [])

    def test_viewbox_must_match_the_declared_grid(self) -> None:
        forged = self.html.replace('viewBox="0 0 600 288"', 'viewBox="0 0 600 300"', 1)
        self.assertIn("viewBox は '0 0 600 288' の完全一致である必要があります", check(forged))

    def test_changing_the_grid_attribute_moves_the_expected_viewbox(self) -> None:
        forged = self.html.replace('data-ve-grid="4x3"', 'data-ve-grid="4x4"', 1)
        self.assertIn("viewBox は '0 0 600 384' の完全一致である必要があります", check(forged))

    def test_missing_grid_attribute_is_rejected(self) -> None:
        forged = self.html.replace(' data-ve-grid="4x3"', "", 1)
        self.assertIn("grid-diagram の figure に1〜6の data-ve-grid がありません", check(forged))

    def test_path_element_is_still_outside_the_allowlist(self) -> None:
        forged = self.html.replace('<g class="ve-gd-region"', '<path></path><g class="ve-gd-region"', 1)
        self.assertIn("許可されていない SVG 要素 <path>", check(forged))

    def test_reading_list_must_match_the_picture(self) -> None:
        forged = self.html.replace('<li class="ve-gd-rel-edge">料金改定案 → 共同承認</li>', "", 1)
        self.assertIn("grid-diagram の読み上げ一覧が図と一致しません", check(forged))

    def test_author_text_is_escaped_everywhere(self) -> None:
        raw = raw_fixture()
        raw["sections"][1]["ir"]["grid-diagram"]["nodes"][0]["label"] = "A&B <x>"
        html = build(raw)
        self.assertEqual(check(html), [])
        self.assertIn('text-anchor="middle">A&amp;B &lt;x&gt;</text>', html)
        self.assertIn('<li class="ve-gd-rel-node">A&amp;B &lt;x&gt;（根拠）</li>', html)

    def test_node_needs_its_box(self) -> None:
        forged = self.html.replace('class="ve-gd-node-box" x="316"', 'class="ve-gd-box" x="316"', 1)
        self.assertIn("grid-diagram ノードは rect.ve-gd-node-box を1つだけ持つ必要があります", check(forged))


if __name__ == "__main__":
    unittest.main()
