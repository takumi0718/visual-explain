"""S7 tests: kpi validation, ring markup, and renderer DOM contract."""
from __future__ import annotations

from fixture_util import canonical_ir, canonical_section
import json
import unittest
from pathlib import Path

from ve_components.diagnostics import KPI_ITEM_LIMIT, KPI_STRUCTURE_VIOLATION, ContractError
from ve_components.model import CanonicalSection
from ve_components.registry import load_registry
from ve_components.validation import validate_canonical_section

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"
KPI_CSS = SKILL / "assets" / "components" / "kpi.css"
KPI_DEF = REGISTRY.find("kpi", 2)
BAD_STRUCTURE = TESTS / "component-bad-kpi-structure.html"


def _fixture_path(name: str) -> Path:
    return TESTS / name if name.endswith(".json") else TESTS / f"{name}.json"


def expect_violation(test_case: unittest.TestCase, fixture_name: str, code: str) -> None:
    raw = json.loads(_fixture_path(fixture_name).read_text("utf-8"))
    with test_case.assertRaises(ContractError) as ctx:
        validate_canonical_section(canonical_ir(raw))
    codes = {d.code for d in ctx.exception.diagnostics}
    test_case.assertIn(code, codes)


def render_fixture(name: str = "component-valid-kpi"):
    from ve_components.renderers.kpi import render_kpi

    raw = json.loads(_fixture_path(name).read_text("utf-8"))
    ir = validate_canonical_section(canonical_ir(raw))
    return render_kpi(CanonicalSection(ir=ir), KPI_DEF)


class KpiAssemblyTest(unittest.TestCase):
    def test_kpi_fixture_validates_assembly(self) -> None:
        from ve_components.validation import validate_assembly

        raw = json.loads(_fixture_path("component-valid-kpi").read_text("utf-8"))
        request = validate_assembly(raw)
        section = next(s for s in request.sections if hasattr(s, "ir"))
        self.assertEqual(section.ir.selection.component, "kpi")
        self.assertEqual(section.ir.selection.version, 2)
        self.assertEqual(section.ir.relationship.kind, "headline-metrics")


class KpiMarkupTest(unittest.TestCase):
    def test_kpi_renders_ring_number_and_caption(self) -> None:
        markup = render_fixture("component-valid-kpi").markup
        self.assertIn('class="ve-kpi-ring"', markup)
        self.assertIn("<small>%</small>", markup)
        self.assertIn("本プログラムの満足度", markup)

    def test_kpi_rejects_more_than_five_items(self) -> None:
        expect_violation(self, "component-bad-kpi-six-items", "kpi-item-limit")


class KpiCheckerTest(unittest.TestCase):
    SKELETON = SKILL / "assets" / "skeleton.html"
    COMPONENTS = SKILL / "assets" / "components"

    def test_kpi_item_limit_diagnostic_is_registered(self) -> None:
        from ve_components.diagnostics import ALL_CODES
        from ve_components.registry import KNOWN_CHECKER_RULES

        self.assertEqual(KPI_ITEM_LIMIT, "kpi-item-limit")
        self.assertIn(KPI_ITEM_LIMIT, ALL_CODES)
        self.assertIn(KPI_ITEM_LIMIT, KNOWN_CHECKER_RULES)

    def test_kpi_structure_violation_diagnostic_is_registered(self) -> None:
        from ve_components.diagnostics import ALL_CODES
        from ve_components.registry import KNOWN_CHECKER_RULES

        self.assertEqual(KPI_STRUCTURE_VIOLATION, "kpi_structure_violation")
        self.assertIn(KPI_STRUCTURE_VIOLATION, ALL_CODES)
        self.assertIn("kpi-structure", KNOWN_CHECKER_RULES)

    def test_kpi_artifact_ignores_small_tags_outside_ve_kpi_num(self) -> None:
        from ve_components.checker import _check_kpi_artifact, _parse_dom

        body = (
            '<figure data-ve-component="kpi">'
            '<figcaption class="ve-kpi-caption">注記<small>補足</small></figcaption>'
            '<p class="ve-kpi-summary">概要<small>詳細</small></p>'
            '<div class="ve-kpi-list">'
            '<div class="ve-kpi-item" data-ve-semantic-id="k1">'
            '<div class="ve-kpi-ring"><span class="ve-kpi-num">88<small>%</small></span></div>'
            '<p class="ve-kpi-cap">満足度</p></div></div>'
            '<ul class="ve-kpi-notes"><li data-ve-semantic-id="cert">x</li></ul>'
            '</figure>'
        )
        codes = {d.code for d in _check_kpi_artifact(body, _parse_dom(body))}
        self.assertNotIn(KPI_STRUCTURE_VIOLATION, codes)
        self.assertNotIn(KPI_ITEM_LIMIT, codes)

    def test_kpi_missing_ring_emits_structure_violation(self) -> None:
        from ve_components.checker import _check_kpi_artifact, _parse_dom

        body = (
            '<figure data-ve-component="kpi">'
            '<figcaption class="ve-kpi-caption">caption</figcaption>'
            '<div class="ve-kpi-list">'
            '<div class="ve-kpi-item" data-ve-semantic-id="k1">'
            '<span class="ve-kpi-num">88<small>%</small></span>'
            '<p class="ve-kpi-cap">満足度</p></div></div>'
            '<ul class="ve-kpi-notes"><li data-ve-semantic-id="cert">x</li></ul>'
            '</figure>'
        )
        codes = {d.code for d in _check_kpi_artifact(body, _parse_dom(body))}
        self.assertIn(KPI_STRUCTURE_VIOLATION, codes)
        self.assertNotIn(KPI_ITEM_LIMIT, codes)

    def test_kpi_structure_bad_fixture_emits_item_limit_code(self) -> None:
        from ve_components.checker import check_final_document

        codes = [d.code for d in check_final_document(
            BAD_STRUCTURE.read_text("utf-8"),
            self.SKELETON.read_text("utf-8"),
            REGISTRY,
            components_dir=self.COMPONENTS,
        )]
        self.assertIn(KPI_ITEM_LIMIT, codes)


if __name__ == "__main__":
    unittest.main()
