"""Phase 4: the overview figure as a grid-diagram draws the overview numbers on its nodes."""
from __future__ import annotations

import json
import unittest
from decimal import Decimal
from pathlib import Path

from build_explainer import build_document
from ve_components.checker import check_final_document
from ve_components.diagnostics import ContractError
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.validation import validate_assembly

SKILL = Path(__file__).resolve().parents[2]
TESTS = SKILL / "scripts" / "tests"
COMPONENTS = SKILL / "assets" / "components"
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
REGISTRY = load_registry(COMPONENTS / "registry.json")


def overview_assembly() -> dict:
    """The grid fixture promoted to the overview figure, with three marked targets."""
    raw = json.loads((TESTS / "component-valid-grid-diagram.json").read_text("utf-8"), parse_float=Decimal)
    first, grid, closing = raw["sections"]
    first["overview"] = {"section": "sec-grid", "markers": [
        {"n": 1, "label": "例外の扱い", "target": "sec-exception"},
        {"n": 2, "label": "共同承認の役割", "target": "sec-approval"},
        {"n": 3, "label": "撤回の条件", "target": "sec-closing"},
    ]}
    grid["ir"]["grid-diagram"]["markers"] = [
        {"n": 1, "target": "exception"},
        {"n": 2, "target": "approval"},
        {"n": 3, "target": "rollback", "ask": "sec-closing"},
    ]
    narratives = [
        {"kind": "narrative", "id": "sec-exception",
         "markup": "<section><h2>契約例外は法務が先に分類する</h2><p>分類が済むまで公開しない。</p></section>"},
        {"kind": "narrative", "id": "sec-approval",
         "markup": "<section><h2>共同承認で三部門がそろう</h2><p>一つの場で照合する。</p></section>"},
    ]
    raw["sections"] = [first, grid, *narratives, closing]
    return raw


def build(raw: dict) -> str:
    return build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS,
                          document_path="grid-overview.html")


def errors(raw: dict) -> list[str]:
    with unittest.TestCase().assertRaises(ContractError) as ctx:
        validate_assembly(raw)
    return [d.message for d in ctx.exception.diagnostics]


class OverviewMarkersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = build(overview_assembly())

    def test_document_passes_every_layer(self) -> None:
        self.assertEqual(check_final_document(self.html, SKELETON, REGISTRY, components_dir=COMPONENTS), [])

    def test_marker_is_a_blue_circle_on_the_node_top_right(self) -> None:
        self.assertIn(
            '<g class="ve-gd-marker"><circle class="ve-gd-marker-dot" cx="434" cy="118" r="10"></circle>'
            '<text class="ve-gd-marker-n" x="434" y="122" text-anchor="middle">2</text></g>',
            self.html)

    def test_numbers_are_also_listed_in_text(self) -> None:
        self.assertIn('<li class="ve-gd-rel-marker">番号 ②: 共同承認</li>', self.html)
        self.assertIn('<nav class="overview-markers" aria-label="この資料の論点">', self.html)

    def test_forged_marker_number_is_rejected_by_the_checker(self) -> None:
        forged = self.html.replace('text-anchor="middle">2</text></g>', 'text-anchor="middle">9</text></g>', 1)
        messages = [d.message for d in check_final_document(forged, SKELETON, REGISTRY, components_dir=COMPONENTS)]
        self.assertIn("grid-diagram の番号は1〜5の重複しない数字である必要があります", messages)


class OverviewMarkerRulesTest(unittest.TestCase):
    def test_overview_grid_must_carry_every_overview_number(self) -> None:
        raw = overview_assembly()
        raw["sections"][1]["ir"]["grid-diagram"]["markers"].pop()
        self.assertIn("全体図の grid-diagram の markers は first-screen.overview.markers と同じ番号を持つ必要があります",
                      errors(raw))
        del raw["sections"][1]["ir"]["grid-diagram"]["markers"]
        self.assertIn("全体図の grid-diagram の markers は first-screen.overview.markers と同じ番号を持つ必要があります",
                      errors(raw))

    def test_marker_ask_must_agree_with_the_overview_target(self) -> None:
        raw = overview_assembly()
        raw["sections"][1]["ir"]["grid-diagram"]["markers"][2]["ask"] = "sec-approval"
        self.assertIn("grid-diagram の marker 3 の ask 'sec-approval' は first-screen.overview.markers"
                      " の同じ番号の target と一致する必要があります", errors(raw))

    def test_markers_outside_the_overview_figure_are_rejected(self) -> None:
        raw = json.loads((TESTS / "component-valid-grid-diagram.json").read_text("utf-8"), parse_float=Decimal)
        raw["sections"][1]["ir"]["grid-diagram"]["markers"] = [{"n": 1, "target": "approval"}]
        self.assertIn("grid-diagram の markers は first-screen.overview の図にだけ付けられます", errors(raw))


if __name__ == "__main__":
    unittest.main()
