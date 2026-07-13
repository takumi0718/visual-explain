"""S6 tests: slope validation, geometry, and renderer DOM contract."""
from __future__ import annotations

import json
import re
import unittest
from decimal import Decimal
from pathlib import Path

from ve_components.diagnostics import ContractError
from ve_components.model import CanonicalSection
from ve_components.numeric import slope_scale_values, slope_y, to_decimal
from ve_components.registry import load_registry
from ve_components.validation import validate_canonical_section

SLOPE_STRUCTURE_VIOLATION = "slope_structure_violation"

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"
SLOPE_DEF = REGISTRY.find("slope", 2)


def _base_ir(**slope_overrides) -> dict:
    slope = {
        "axes": {"fromLabel": "開始", "toLabel": "終了"},
        "title": "主要指標",
        "unitLabel": "件",
        "items": [
            {
                "id": "s1",
                "label": "売上",
                "fromValue": 10,
                "toValue": 40,
                "fromValueText": "10件",
                "toValueText": "40件",
                "tone": "positive",
            }
        ],
    }
    slope.update(slope_overrides)
    return {
        "id": "sec-slope",
        "relationship": {"kind": "two-point-change", "capabilities": ["two-point-comparison"]},
        "selection": {
            "component": "slope",
            "version": 2,
            "matchedCapabilities": ["two-point-comparison"],
        },
        "caption": "推移",
        "certainty": [{"id": "cert-1", "level": "confirmed", "statement": "テスト。"}],
        "sources": [{"id": "src-1", "label": "出典"}],
        "accessibility": {"label": "スロープ", "summary": "2時点比較。"},
        "slope": slope,
    }


def validate_raw(ir: dict):
    return validate_canonical_section(ir)


def expect_violation(ir: dict, code: str = SLOPE_STRUCTURE_VIOLATION) -> None:
    with unittest.TestCase().assertRaises(ContractError) as ctx:
        validate_raw(ir)
    codes = {d.code for d in ctx.exception.diagnostics}
    unittest.TestCase().assertIn(code, codes)


def render_fixture(name: str):
    from ve_components.renderers.slope import render_slope

    raw = json.loads((TESTS / name).read_text("utf-8"))
    ir = validate_canonical_section(raw["sections"][0]["ir"])
    return ir, render_slope(CanonicalSection(ir=ir), SLOPE_DEF)


def render_ir(ir: dict):
    from ve_components.renderers.slope import render_slope

    validated = validate_canonical_section(ir)
    return render_slope(CanonicalSection(ir=validated), SLOPE_DEF)


class SlopeGeometryTest(unittest.TestCase):
    def test_endpoints_map_min_to_200_max_to_20(self) -> None:
        lo, hi = Decimal(10), Decimal(50)
        self.assertEqual(slope_y(lo, lo, hi), 200)
        self.assertEqual(slope_y(hi, lo, hi), 20)

    def test_increase_has_y2_less_than_y1(self) -> None:
        lo, hi = Decimal(0), Decimal(100)
        y1 = slope_y(20, lo, hi)
        y2 = slope_y(80, lo, hi)
        self.assertLess(y2, y1)

    def test_decrease_has_y2_greater_than_y1(self) -> None:
        lo, hi = Decimal(0), Decimal(100)
        y1 = slope_y(80, lo, hi)
        y2 = slope_y(20, lo, hi)
        self.assertGreater(y2, y1)

    def test_range_zero_maps_all_to_110(self) -> None:
        for value in (0, 5, 10):
            self.assertEqual(slope_y(value, 10, 10), 110)

    def test_fixed_x_coordinates_in_markup(self) -> None:
        _, result = render_fixture("component-valid-slope.json")
        self.assertIn('x1="120"', result.markup)
        self.assertIn('x2="480"', result.markup)

    def test_round_half_up_boundary(self) -> None:
        lo, hi = Decimal(0), Decimal(3)
        self.assertEqual(slope_y(Decimal("1.5"), lo, hi), 110)


class SlopeValidationTest(unittest.TestCase):
    def test_requires_unit_label(self) -> None:
        ir = _base_ir()
        ir["slope"].pop("unitLabel")
        with self.assertRaises(ContractError) as ctx:
            validate_raw(ir)
        self.assertIn("quantitative-unit-required", {d.code for d in ctx.exception.diagnostics})

    def test_rejects_float_value(self) -> None:
        ir = _base_ir(items=[{
            "id": "sl-1", "label": "A", "fromValue": 0.1, "toValue": 2,
            "fromValueText": "0.1", "toValueText": "2", "tone": "neutral",
        }])
        expect_violation(ir)

    def test_rejects_six_items(self) -> None:
        raw = json.loads((TESTS / "component-bad-slope-too-many-items.json").read_text("utf-8"))
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(raw["sections"][0]["ir"])
        self.assertIn(SLOPE_STRUCTURE_VIOLATION, {d.code for d in ctx.exception.diagnostics})

    def test_rejects_three_point_shape(self) -> None:
        raw = json.loads((TESTS / "component-bad-slope-three-points-shape.json").read_text("utf-8"))
        with self.assertRaises(ContractError):
            validate_canonical_section(raw["sections"][0]["ir"])

    def test_accepts_contradictory_value_text(self) -> None:
        ir = _base_ir(items=[{
            "id": "sl-1", "label": "A", "fromValue": 10, "toValue": 20,
            "fromValueText": "据置", "toValueText": "急増", "tone": "neutral",
        }])
        validate_raw(ir)


class SlopeManifestTest(unittest.TestCase):
    def test_registry_entry_is_complete(self) -> None:
        self.assertIsNotNone(SLOPE_DEF)
        self.assertEqual(SLOPE_DEF.relationship_kind, "two-point-change")
        self.assertEqual(SLOPE_DEF.renderer, "slope@2")

    def test_manifest_declares_svg_root(self) -> None:
        ir, result = render_fixture("component-valid-slope.json")
        self.assertEqual(result.manifest.svg_root_ids, (f"{ir.id}-svg",))
        self.assertIn(f"{ir.id}-svg", result.manifest.generated_landmark_ids)

    def test_manifest_consumes_all_semantic_ids(self) -> None:
        ir, result = render_fixture("component-valid-slope.json")
        self.assertEqual(set(result.manifest.consumed_semantic_ids), set(ir.semantic_ids()))


class SlopeV2MarkupTest(unittest.TestCase):
    def test_slope_v2_merges_series_label_into_endpoint(self) -> None:
        ir = _base_ir(highlightId="s1")
        markup = render_ir(ir).markup
        self.assertIn("40件 売上", markup)
        self.assertNotIn('x="300"', markup)

    def test_slope_v2_emits_figure_header(self) -> None:
        markup = render_ir(_base_ir()).markup
        self.assertIn('class="ve-fig-title"', markup)
        self.assertIn("単位: 件", markup)


class SlopeMarkupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ir, self.result = render_fixture("component-valid-slope.json")
        self.markup = self.result.markup

    def test_svg_viewbox_and_id(self) -> None:
        self.assertIn(f'id="{self.ir.id}-svg"', self.markup)
        self.assertIn('viewBox="0 0 600 220"', self.markup)

    def test_slope_items_with_semantic_ids_on_g_not_line(self) -> None:
        for item in self.ir.slope.items:
            self.assertRegex(
                self.markup,
                rf'<g[^>]*class="[^"]*\bve-slope-row\b[^"]*"[^>]*data-ve-semantic-id="{re.escape(item.id)}"',
            )
            self.assertNotRegex(
                self.markup,
                rf'<line[^>]*data-ve-semantic-id="{re.escape(item.id)}"',
            )

    def test_unit_visible_in_figure_header(self) -> None:
        self.assertIn(f"単位: {self.ir.slope.unit_label}", self.markup)
        self.assertNotIn("（単位:", self.markup)

    def test_value_texts_rendered(self) -> None:
        for item in self.ir.slope.items:
            self.assertIn(item.from_value_text, self.markup)
            self.assertIn(item.to_value_text, self.markup)


if __name__ == "__main__":
    unittest.main()
