"""S5 tests: waterfall validation, Decimal parsing, and renderer DOM contract."""
from __future__ import annotations

import json
import re
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from ve_components.diagnostics import ContractError, RENDERER_FAILURE
from ve_components.model import CanonicalSection
from ve_components.registry import load_registry
from ve_components.validation import validate_canonical_section

WATERFALL_STRUCTURE_VIOLATION = "waterfall_structure_violation"
WATERFALL_ARITHMETIC_MISMATCH = "waterfall_arithmetic_mismatch"

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"
WATERFALL_DEF = REGISTRY.find("waterfall", 2)


def _base_ir(**waterfall_overrides) -> dict:
    waterfall = {
        "displayPrecision": 1,
        "title": "主要指標",
        "unitLabel": "件",
        "axisTicks": ["0", "10", "20"],
        "start": {"id": "wf-start", "label": "開始", "value": 10, "valueText": "10件"},
        "steps": [{"id": "wf-step", "label": "増", "delta": 5, "tone": "positive", "valueText": "+5件"}],
        "end": {"id": "wf-end", "label": "終了", "value": 15, "valueText": "15件"},
    }
    waterfall.update(waterfall_overrides)
    return {
        "id": "sec-waterfall",
        "relationship": {"kind": "additive-bridge", "capabilities": ["additive-bridging"]},
        "selection": {
            "component": "waterfall",
            "version": 2,
            "matchedCapabilities": ["additive-bridging"],
        },
        "caption": "件数ブリッジ",
        "certainty": [{"id": "cert-1", "level": "confirmed", "statement": "テスト用。"}],
        "sources": [{"id": "src-1", "label": "出典"}],
        "accessibility": {"label": "ウォーターフォール", "summary": "増減を示す。"},
        "waterfall": waterfall,
    }


def validate_raw(ir: dict):
    return validate_canonical_section(ir)


def expect_violation(ir: dict, code: str) -> None:
    with unittest.TestCase().assertRaises(ContractError) as ctx:
        validate_raw(ir)
    codes = {d.code for d in ctx.exception.diagnostics}
    unittest.TestCase().assertIn(code, codes)


def render_fixture(name: str):
    from ve_components.renderers.waterfall import render_waterfall

    path = TESTS / name if name.endswith(".json") else TESTS / f"{name}.json"
    raw = json.loads(path.read_text("utf-8"))
    ir = validate_canonical_section(raw["sections"][0]["ir"])
    return render_waterfall(CanonicalSection(ir=ir), WATERFALL_DEF)


def expect_violation_fixture(test_case: unittest.TestCase, fixture_name: str, code: str) -> None:
    path = TESTS / fixture_name if fixture_name.endswith(".json") else TESTS / f"{fixture_name}.json"
    raw = json.loads(path.read_text("utf-8"))
    with test_case.assertRaises(ContractError) as ctx:
        validate_canonical_section(raw["sections"][0]["ir"])
    codes = {d.code for d in ctx.exception.diagnostics}
    test_case.assertIn(code, codes)


class WaterfallValidationTest(unittest.TestCase):
    def test_accepts_arithmetic_at_exactly_half_precision(self) -> None:
        ir = _base_ir(
            start={"id": "st", "label": "開始", "value": Decimal("10"), "valueText": "10"},
            steps=[{"id": "s1", "label": "微", "delta": Decimal("0"), "tone": "neutral", "valueText": "0"}],
            end={"id": "en", "label": "終了", "value": Decimal("10.5"), "valueText": "10.5"},
            displayPrecision=Decimal("1"),
        )
        result = validate_raw(ir)
        self.assertEqual(result.waterfall.end.value, Decimal("10.5"))

    def test_rejects_arithmetic_just_above_half_precision(self) -> None:
        ir = _base_ir(
            start={"id": "st", "label": "開始", "value": Decimal("10"), "valueText": "10"},
            steps=[{"id": "s1", "label": "微", "delta": Decimal("0"), "tone": "neutral", "valueText": "0"}],
            end={"id": "en", "label": "終了", "value": Decimal("10.500001"), "valueText": "10.5"},
            displayPrecision=Decimal("1"),
        )
        expect_violation(ir, WATERFALL_ARITHMETIC_MISMATCH)

    def test_rejects_missing_display_precision(self) -> None:
        ir = _base_ir()
        ir["waterfall"].pop("displayPrecision")
        expect_violation(ir, WATERFALL_STRUCTURE_VIOLATION)

    def test_rejects_float_value_instance(self) -> None:
        ir = _base_ir()
        ir["waterfall"]["start"]["value"] = 0.1
        expect_violation(ir, WATERFALL_STRUCTURE_VIOLATION)

    def test_rejects_bool_value_instance(self) -> None:
        ir = _base_ir()
        ir["waterfall"]["start"]["value"] = True
        expect_violation(ir, WATERFALL_STRUCTURE_VIOLATION)

    def test_rejects_zero_range(self) -> None:
        raw = json.loads((TESTS / "component-bad-waterfall-zero-range.json").read_text("utf-8"))
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(raw["sections"][0]["ir"])
        self.assertIn(WATERFALL_STRUCTURE_VIOLATION, {d.code for d in ctx.exception.diagnostics})

    def test_accepts_delta_zero_step(self) -> None:
        ir = _base_ir(
            steps=[{"id": "s0", "label": "無", "delta": 0, "tone": "neutral", "valueText": "0件"}],
            end={"id": "wf-end", "label": "終了", "value": 10, "valueText": "10件"},
        )
        validate_raw(ir)

    def test_bars_accepts_one_to_five_steps(self) -> None:
        for n in range(1, 6):
            with self.subTest(steps=n):
                steps = [
                    {"id": f"s{i}", "label": f"段{i}", "delta": 0, "tone": "neutral", "valueText": "0件"}
                    for i in range(1, n + 1)
                ]
                validate_raw(_base_ir(steps=steps, end={"id": "en", "label": "終", "value": 10, "valueText": "10件"}))

    def test_bars_rejects_six_steps(self) -> None:
        raw = json.loads((TESTS / "component-bad-waterfall-too-many-bars.json").read_text("utf-8"))
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(raw["sections"][0]["ir"])
        self.assertIn(WATERFALL_STRUCTURE_VIOLATION, {d.code for d in ctx.exception.diagnostics})

    def test_requires_unit_label(self) -> None:
        ir = _base_ir()
        ir["waterfall"].pop("unitLabel")
        expect_violation(ir, "quantitative-unit-required")

    def test_requires_title(self) -> None:
        ir = _base_ir()
        ir["waterfall"].pop("title")
        expect_violation(ir, WATERFALL_STRUCTURE_VIOLATION)

    def test_requires_axis_ticks(self) -> None:
        ir = _base_ir()
        ir["waterfall"].pop("axisTicks")
        expect_violation(ir, WATERFALL_STRUCTURE_VIOLATION)

    def test_rejects_missing_tone(self) -> None:
        raw = json.loads((TESTS / "component-bad-waterfall-missing-tone.json").read_text("utf-8"))
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(raw["sections"][0]["ir"])
        self.assertIn(WATERFALL_STRUCTURE_VIOLATION, {d.code for d in ctx.exception.diagnostics})

    def test_value_text_required_nonempty_max_16(self) -> None:
        ir = _base_ir()
        ir["waterfall"]["steps"][0].pop("valueText")
        expect_violation(ir, WATERFALL_STRUCTURE_VIOLATION)
        ir = _base_ir()
        ir["waterfall"]["steps"][0]["valueText"] = ""
        expect_violation(ir, WATERFALL_STRUCTURE_VIOLATION)
        ir = _base_ir()
        ir["waterfall"]["steps"][0]["valueText"] = "あ" * 17
        expect_violation(ir, WATERFALL_STRUCTURE_VIOLATION)

    def test_value_text_not_cross_checked_against_value(self) -> None:
        ir = _base_ir(
            start={"id": "st", "label": "開始", "value": 100, "valueText": "表示は別"},
            steps=[{"id": "s1", "label": "減", "delta": -85, "tone": "neutral", "valueText": "−85件"}],
            end={"id": "en", "label": "終了", "value": 15, "valueText": "15件"},
        )
        validate_raw(ir)

    def test_rejects_arithmetic_mismatch_fixture(self) -> None:
        raw = json.loads((TESTS / "component-bad-waterfall-arithmetic.json").read_text("utf-8"))
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(raw["sections"][0]["ir"])
        self.assertIn(WATERFALL_ARITHMETIC_MISMATCH, {d.code for d in ctx.exception.diagnostics})


class BuildDecimalParsingTest(unittest.TestCase):
    FIXTURE = TESTS / "component-valid-waterfall-decimal.json"
    SKELETON = SKILL / "assets" / "skeleton.html"
    REGISTRY = SKILL / "assets" / "components" / "registry.json"

    def _main_argv(self, output: Path) -> list[str]:
        return [
            "--assembly", str(self.FIXTURE),
            "--output", str(output),
            "--skeleton", str(self.SKELETON),
            "--registry", str(self.REGISTRY),
        ]

    def test_main_parse_float_decimal_reaches_validation(self) -> None:
        import build_explainer as be

        captured: list[object] = []
        original_va = be.validate_assembly

        def tracking_validate(raw):
            prec = raw["sections"][0]["ir"]["waterfall"]["displayPrecision"]
            captured.append(("raw", prec, type(prec)))
            result = original_va(raw)
            section = result.sections[0]
            from ve_components.model import CanonicalSection
            assert isinstance(section, CanonicalSection)
            captured.append(("validated", section.ir.waterfall.display_precision,
                             type(section.ir.waterfall.display_precision)))
            return result

        out = TESTS / "_tmp-decimal-main-build.html"
        out.unlink(missing_ok=True)
        try:
            with patch.object(be, "validate_assembly", tracking_validate):
                rc = be.main(self._main_argv(out))
            self.assertEqual(rc, 0, "build_explainer.main should succeed")
            self.assertTrue(out.exists())
            self.assertEqual(len(captured), 2)
            _, raw_prec, raw_type = captured[0]
            _, val_prec, val_type = captured[1]
            self.assertIsInstance(raw_prec, Decimal)
            self.assertEqual(raw_prec, Decimal("0.1"))
            self.assertNotIsInstance(raw_prec, float)
            self.assertIsInstance(val_prec, Decimal)
            self.assertEqual(val_prec, Decimal("0.1"))
            self.assertIs(raw_type, val_type)
        finally:
            out.unlink(missing_ok=True)

    def test_main_without_parse_float_decimal_rejected_at_validation(self) -> None:
        """Regression guard: removing parse_float=Decimal must fail before a clean build."""
        import build_explainer as be

        real_loads = be.json.loads

        def loads_as_binary_float(*args, **kwargs):
            kwargs.pop("parse_float", None)
            return real_loads(*args, **kwargs)

        out = TESTS / "_tmp-decimal-main-red.html"
        out.unlink(missing_ok=True)
        try:
            with patch.object(be.json, "loads", loads_as_binary_float):
                rc = be.main(self._main_argv(out))
            self.assertEqual(rc, 1)
            self.assertFalse(out.exists())
        finally:
            out.unlink(missing_ok=True)


class WaterfallNumericTest(unittest.TestCase):
    def test_quantize_percent_endpoints(self) -> None:
        from ve_components.numeric import quantize_percent

        lo, hi = Decimal("-20"), Decimal("30")
        self.assertEqual(quantize_percent(Decimal("-20"), lo, hi), 0)
        self.assertEqual(quantize_percent(Decimal("30"), lo, hi), 100)

    def test_quantize_percent_rounds_half_up_at_midpoint(self) -> None:
        from ve_components.numeric import quantize_percent

        lo, hi = Decimal("0"), Decimal("100")
        self.assertEqual(quantize_percent(Decimal("50.5"), lo, hi), 51)
        self.assertEqual(quantize_percent(Decimal("50.4"), lo, hi), 50)


class WaterfallManifestTest(unittest.TestCase):
    def test_registry_entry_is_complete(self) -> None:
        self.assertIsNotNone(WATERFALL_DEF)
        self.assertEqual(WATERFALL_DEF.relationship_kind, "additive-bridge")
        self.assertEqual(WATERFALL_DEF.capabilities, ("additive-bridging",))
        self.assertEqual(WATERFALL_DEF.renderer, "waterfall@2")
        self.assertEqual([a.id for a in WATERFALL_DEF.assets], ["waterfall.css"])

    def test_manifest_consumes_all_semantic_ids(self) -> None:
        raw = json.loads((TESTS / "component-valid-waterfall.json").read_text("utf-8"))
        ir = validate_canonical_section(raw["sections"][0]["ir"])
        result = render_fixture("component-valid-waterfall.json")
        self.assertEqual(set(result.manifest.consumed_semantic_ids), set(ir.semantic_ids()))

    def test_declares_css_and_no_script(self) -> None:
        result = render_fixture("component-valid-waterfall.json")
        self.assertEqual(result.style_asset_ids, ("waterfall.css",))
        self.assertEqual(result.script_asset_ids, ())
        self.assertEqual(result.manifest.generated_relationship_ids, ())
        self.assertTrue(result.manifest.svg_root_ids)


class WaterfallV2MarkupTest(unittest.TestCase):
    def test_waterfall_v2_renders_svg_with_fixed_viewbox(self) -> None:
        result = render_fixture("component-valid-waterfall")
        self.assertIn('viewBox="0 0 640 360"', result.markup)
        self.assertTrue(result.manifest.svg_root_ids)

    def test_waterfall_v2_negative_uses_triangle_notation(self) -> None:
        markup = render_fixture("component-valid-waterfall").markup
        self.assertIn("▲50", markup)
        self.assertIn("▲20", markup)
        self.assertNotIn(">-50<", markup)

    def test_waterfall_v2_triangle_preserves_decimal_in_value_text(self) -> None:
        from ve_components.renderers.waterfall import render_waterfall

        ir = validate_canonical_section(_base_ir(
            start={"id": "st", "label": "開始", "value": 100, "valueText": "100"},
            steps=[{"id": "s1", "label": "減", "delta": -50, "tone": "warning", "valueText": "-50.5"}],
            end={"id": "en", "label": "終", "value": 50, "valueText": "50"},
            axisTicks=["0", "50", "100"],
        ))
        markup = render_waterfall(CanonicalSection(ir=ir), WATERFALL_DEF).markup
        self.assertIn("▲50.5", markup)
        self.assertNotIn("▲505", markup)

    def test_waterfall_v2_only_largest_decrease_is_filled(self) -> None:
        markup = render_fixture("component-valid-waterfall").markup
        self.assertEqual(markup.count('class="ve-wf-bar ve-wf-minus"'), 1)
        self.assertEqual(markup.count('class="ve-wf-bar ve-wf-minus-soft"'), 1)

    def test_waterfall_v2_emits_connectors_between_adjacent_bars(self) -> None:
        markup = render_fixture("component-valid-waterfall").markup
        self.assertEqual(markup.count("ve-wf-connector"), 5)

    def test_waterfall_v2_requires_unit_label(self) -> None:
        expect_violation_fixture(self, "component-bad-waterfall-no-unit", "quantitative-unit-required")


if __name__ == "__main__":
    unittest.main()
