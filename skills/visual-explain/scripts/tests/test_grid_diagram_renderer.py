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
from ve_components.grid_layout import check_layout, route_edges
from ve_components.validation import validate_assembly, validate_canonical_section, validate_grid_diagram

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

    def test_region_is_listed_with_the_nodes_inside_it(self) -> None:
        self.assertIn('<li class="ve-gd-rel-region">根拠: 契約例外・料金改定案</li>', self.markup)

    def test_region_without_nodes_says_so(self) -> None:
        raw = raw_fixture()
        raw["sections"][1]["ir"]["grid-diagram"]["regions"].append(
            {"id": "spare", "label": "予備", "from": [4, 1], "to": [4, 2]})
        self.assertIn('<li class="ve-gd-rel-region">予備: 中は空</li>', build(raw))

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

    def test_reading_list_must_describe_every_region(self) -> None:
        forged = self.html.replace('<li class="ve-gd-rel-region">根拠: 契約例外・料金改定案</li>', "", 1)
        self.assertIn("grid-diagram の読み上げ一覧が図と一致しません", check(forged))

    def test_unknown_grid_attribute_reports_only_itself(self) -> None:
        forged = self.html.replace('data-ve-grid="4x3"', 'data-ve-grid="7x3"', 1)
        self.assertEqual(check(forged), ["grid-diagram の figure に1〜6の data-ve-grid がありません"])

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

    def test_non_integer_coordinate_is_rejected(self) -> None:
        forged = self.html.replace('class="ve-gd-node-box" x="316"', 'class="ve-gd-node-box" x="316.5"', 1)
        self.assertIn("座標属性 x の値 '316.5' は整数である必要があります", check(forged))

    def test_attribute_outside_the_allowlist_is_rejected(self) -> None:
        forged = self.html.replace('<rect class="ve-gd-node-box" x="316"', '<rect class="ve-gd-node-box" rx="6" x="316"', 1)
        self.assertIn("<rect> に許可されていない属性 'rx'", check(forged))

    def test_node_needs_its_box(self) -> None:
        forged = self.html.replace('class="ve-gd-node-box" x="316"', 'class="ve-gd-box" x="316"', 1)
        self.assertIn("grid-diagram ノードは rect.ve-gd-node-box を1つだけ持つ必要があります", check(forged))


def _messages(raw_ir: dict) -> list[str]:
    with unittest.TestCase().assertRaises(ContractError) as ctx:
        validate_canonical_section(raw_ir)
    return [d.message for d in ctx.exception.diagnostics]


class ReservedClassTest(unittest.TestCase):
    def test_narrative_cannot_hide_prose_from_the_text_budget(self) -> None:
        for cls in ("visually-hidden", "ve-gd-relations"):
            with self.subTest(cls=cls):
                raw = raw_fixture()
                raw["sections"].insert(1, {"kind": "narrative", "id": "sec-hide",
                                           "markup": f'<p class="{cls}">隠した本文</p>'})
                with self.assertRaises(ContractError) as ctx:
                    validate_assembly(raw)
                self.assertIn(f"narrative に予約 class {cls} は置けません",
                              [d.message for d in ctx.exception.diagnostics])


def _route_payload(*, blocker: bool) -> dict:
    """b sits top-left, a bottom-right; the first bend puts the edge label on region 'r's label."""
    nodes = [{"id": "a", "label": "甲", "cell": [2, 4]}, {"id": "b", "label": "乙", "cell": [1, 1]}]
    if blocker:
        nodes.append({"id": "c", "label": "丙", "cell": [2, 2]})
    return {"grid": {"cols": 3, "rows": 4}, "nodes": nodes,
            "regions": [{"id": "r", "label": "囲み", "from": [2, 3], "to": [2, 3]}],
            "edges": [{"id": "e", "from": "a", "to": "b", "label": "あいうえおかきく"}]}


class RouteAgreementTest(unittest.TestCase):
    def _render(self, payload_raw: dict) -> str:
        ir = canonical_ir(raw_fixture())
        ir["grid-diagram"] = payload_raw
        section = CanonicalSection(ir=validate_canonical_section(ir))
        return render_grid_diagram(section, REGISTRY.find("grid-diagram", 2)).markup

    def test_renderer_uses_the_route_check_layout_accepted(self) -> None:
        payload_raw = {
            "grid": {"cols": 4, "rows": 2},
            "nodes": [{"id": "a", "label": "甲", "cell": [1, 1]}, {"id": "b", "label": "乙", "cell": [4, 1]},
                      {"id": "c", "label": "丙", "cell": [3, 2]}],
            "edges": [{"id": "e-ab", "from": "a", "to": "b", "label": "あいうえおかき"},
                      {"id": "e-ac", "from": "a", "to": "c", "label": "さしすせそたち"}],
        }
        payload = validate_grid_diagram(copy.deepcopy(payload_raw))
        self.assertEqual(check_layout(payload), [])
        accepted = route_edges(payload)[1]
        # The first bend's label would sit on e-ab's label, so e-ac goes down first.
        self.assertEqual(accepted.points, ((75, 74), (75, 144), (316, 144)))
        markup = self._render(payload_raw)
        drawn = "".join(
            f'<line class="ve-gd-edge-line" x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}"></line>'
            for a, b in zip(accepted.points, accepted.points[1:]))
        self.assertIn(f'<g class="ve-gd-edge" data-ve-semantic-id="e-ac">{drawn}', markup)

    def test_edge_label_avoids_a_region_label_by_taking_the_other_bend(self) -> None:
        payload = validate_grid_diagram(_route_payload(blocker=False))
        self.assertEqual(route_edges(payload)[0].points, ((225, 310), (225, 48), (134, 48)))
        self.assertIn('x1="225" y1="310" x2="225" y2="48"', self._render(_route_payload(blocker=False)))

    def test_edge_label_on_a_region_label_with_no_other_bend_is_reported(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_grid_diagram(_route_payload(blocker=True))
        self.assertEqual([d.message for d in ctx.exception.diagnostics],
                         ["辺 'e' のラベルを置く場所がありません"])


class DuplicateIdTest(unittest.TestCase):
    def test_duplicate_inside_the_picture_is_reported_once(self) -> None:
        ir = canonical_ir(raw_fixture())
        ir["grid-diagram"]["regions"][0]["id"] = "approval"
        hits = [m for m in _messages(ir) if "'approval'" in m and "重複" in m]
        self.assertEqual(hits, ["図の id 'approval' が重複しています"])

    def test_node_id_clashing_with_a_source_id_is_reported(self) -> None:
        ir = canonical_ir(raw_fixture())
        ir["grid-diagram"]["nodes"][3]["id"] = "src-grid"
        ir["grid-diagram"]["edges"][2]["to"] = "src-grid"
        self.assertEqual([m for m in _messages(ir) if "重複" in m], ["意味 ID 'src-grid' が重複しています"])


class GridStyleTest(unittest.TestCase):
    CSS = (COMPONENTS / "grid-diagram.css").read_text("utf-8")

    def test_dark_base_nodes_differ_from_primary_by_tint_and_outline(self) -> None:
        rule = ('[data-ve-component="grid-diagram"] .ve-gd-tone-base .ve-gd-node-box { fill: color-mix(in srgb, '
                'var(--accent) 12%, var(--surface)); stroke: var(--dg-primary-mid); stroke-width: 1.5; }')
        self.assertIn(':root[data-theme="dark"] ' + rule, self.CSS)
        self.assertIn('@media (prefers-color-scheme: dark) { :root:not([data-theme]) ' + rule + ' }', self.CSS)

    def test_scrolling_canvas_shows_edge_shadows_with_existing_tokens(self) -> None:
        rule = next(line for line in self.CSS.splitlines() if ".ve-gd-canvas { overflow-x: auto;" in line)
        self.assertEqual(rule.count("no-repeat local"), 2)
        self.assertEqual(rule.count("no-repeat scroll"), 2)
        self.assertIn("var(--ve-gd-canvas-bg, var(--bg))", rule)
        self.assertIn("color-mix(in srgb, var(--text) 12%, var(--surface))", rule)
        self.assertIn(".ve-gd-thumb .ve-gd-canvas { background: none; }", self.CSS)


if __name__ == "__main__":
    unittest.main()
