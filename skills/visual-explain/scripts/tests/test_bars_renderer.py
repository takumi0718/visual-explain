"""S7 tests: bars validation, width classes, and renderer DOM contract."""
from __future__ import annotations

from fixture_util import canonical_ir, canonical_section
import json
import unittest
from pathlib import Path

from ve_components.diagnostics import BARS_WIDTH_CLASSES, ContractError
from ve_components.model import CanonicalSection
from ve_components.registry import load_registry
from ve_components.validation import validate_canonical_section

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"
BARS_CSS = SKILL / "assets" / "components" / "bars.css"
BARS_DEF = REGISTRY.find("bars", 2)
BAD_STRUCTURE = TESTS / "component-bad-bars-structure.html"


def _fixture_path(name: str) -> Path:
    return TESTS / name if name.endswith(".json") else TESTS / f"{name}.json"


def expect_violation(test_case: unittest.TestCase, fixture_name: str, code: str) -> None:
    raw = json.loads(_fixture_path(fixture_name).read_text("utf-8"))
    with test_case.assertRaises(ContractError) as ctx:
        validate_canonical_section(canonical_ir(raw))
    codes = {d.code for d in ctx.exception.diagnostics}
    test_case.assertIn(code, codes)


def render_fixture(name: str = "component-valid-bars"):
    from ve_components.renderers.bars import render_bars

    raw = json.loads(_fixture_path(name).read_text("utf-8"))
    ir = validate_canonical_section(canonical_ir(raw))
    return render_bars(CanonicalSection(ir=ir), BARS_DEF)


class BarsCssTest(unittest.TestCase):
    def test_bars_css_enumerates_width_classes_zero_through_hundred(self) -> None:
        css = BARS_CSS.read_text("utf-8")
        for pct in range(101):
            self.assertIn(f".ve-bars-w-{pct} {{ width: {pct}%; }}", css)
        self.assertNotIn("ve-bars-w-150", css)

    def test_bad_fixture_embedded_css_keeps_canonical_width_classes(self) -> None:
        html = BAD_STRUCTURE.read_text("utf-8")
        styles = html.split("<!-- VE-CONTROLLED:COMPONENT-STYLES:BEGIN -->", 1)[1]
        styles = styles.split("<!-- VE-CONTROLLED:COMPONENT-STYLES:END -->", 1)[0]
        self.assertIn("figure[data-ve-component=\"bars\"] .ve-bars-w-17 { width: 17%; }", styles)
        self.assertNotIn("ve-bars-w-150", styles)


class BarsAssemblyTest(unittest.TestCase):
    def test_bars_fixture_validates_assembly(self) -> None:
        from ve_components.validation import validate_assembly

        raw = json.loads(_fixture_path("component-valid-bars").read_text("utf-8"))
        request = validate_assembly(raw)
        section = next(s for s in request.sections if hasattr(s, "ir"))
        self.assertEqual(section.ir.selection.component, "bars")
        self.assertEqual(section.ir.selection.version, 2)
        self.assertEqual(section.ir.relationship.kind, "quantitative-comparison")


class BarsMarkupTest(unittest.TestCase):
    def test_bars_renders_rows_with_integer_width_class(self) -> None:
        markup = render_fixture("component-valid-bars").markup
        self.assertIn("ve-bars-w-100", markup)
        self.assertIn("ve-bars-w-17", markup)
        self.assertEqual(markup.count("ve-dg-highlight"), 1)

    def test_bars_rejects_more_than_ten_items(self) -> None:
        expect_violation(self, "component-bad-bars-eleven-items", "bars-item-limit")


class BarsCheckerTest(unittest.TestCase):
    SKELETON = SKILL / "assets" / "skeleton.html"
    COMPONENTS = SKILL / "assets" / "components"

    def test_bars_width_classes_diagnostic_is_registered(self) -> None:
        from ve_components.diagnostics import ALL_CODES

        self.assertEqual(BARS_WIDTH_CLASSES, "bars-width-classes")
        self.assertIn(BARS_WIDTH_CLASSES, ALL_CODES)

    def test_bars_structure_bad_fixture_emits_width_classes_code(self) -> None:
        from ve_components.checker import check_final_document

        codes = [d.code for d in check_final_document(
            BAD_STRUCTURE.read_text("utf-8"),
            self.SKELETON.read_text("utf-8"),
            REGISTRY,
            components_dir=self.COMPONENTS,
        )]
        self.assertIn(BARS_WIDTH_CLASSES, codes)
        self.assertNotIn("bars_structure_violation", codes)


if __name__ == "__main__":
    unittest.main()
