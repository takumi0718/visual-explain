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
WATERFALL_DEF = REGISTRY.find("waterfall", 1)


def _base_ir(**waterfall_overrides) -> dict:
    waterfall = {
        "displayPrecision": 1,
        "orientation": "bars",
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
            "version": 1,
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

    raw = json.loads((TESTS / name).read_text("utf-8"))
    ir = validate_canonical_section(raw["sections"][0]["ir"])
    return ir, render_waterfall(CanonicalSection(ir=ir), WATERFALL_DEF)


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

    def test_bars_accepts_one_to_four_steps(self) -> None:
        for n in range(1, 5):
            with self.subTest(steps=n):
                steps = [
                    {"id": f"s{i}", "label": f"段{i}", "delta": 0, "tone": "neutral", "valueText": "0件"}
                    for i in range(1, n + 1)
                ]
                validate_raw(_base_ir(steps=steps, end={"id": "en", "label": "終", "value": 10, "valueText": "10件"}))

    def test_bars_rejects_five_steps(self) -> None:
        raw = json.loads((TESTS / "component-bad-waterfall-too-many-bars.json").read_text("utf-8"))
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(raw["sections"][0]["ir"])
        self.assertIn(WATERFALL_STRUCTURE_VIOLATION, {d.code for d in ctx.exception.diagnostics})

    def test_columns_accepts_one_to_seven_steps(self) -> None:
        for n in range(1, 8):
            with self.subTest(steps=n):
                steps = [
                    {"id": f"s{i}", "label": f"段{i}", "delta": 0, "tone": "neutral", "valueText": "0件"}
                    for i in range(1, n + 1)
                ]
                validate_raw(_base_ir(
                    orientation="columns",
                    steps=steps,
                    end={"id": "en", "label": "終", "value": 10, "valueText": "10件"},
                ))

    def test_columns_rejects_eight_steps(self) -> None:
        steps = [
            {"id": f"s{i}", "label": f"段{i}", "delta": 0, "tone": "neutral", "valueText": "0件"}
            for i in range(1, 9)
        ]
        expect_violation(_base_ir(orientation="columns", steps=steps,
                                  end={"id": "en", "label": "終", "value": 10, "valueText": "10件"}),
                         WATERFALL_STRUCTURE_VIOLATION)

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
        self.assertEqual(WATERFALL_DEF.renderer, "waterfall@1")
        self.assertEqual([a.id for a in WATERFALL_DEF.assets], ["waterfall.css"])

    def test_manifest_consumes_all_semantic_ids(self) -> None:
        ir, result = render_fixture("component-valid-waterfall.json")
        self.assertEqual(set(result.manifest.consumed_semantic_ids), set(ir.semantic_ids()))

    def test_declares_css_and_no_script(self) -> None:
        _, result = render_fixture("component-valid-waterfall.json")
        self.assertEqual(result.style_asset_ids, ("waterfall.css",))
        self.assertEqual(result.script_asset_ids, ())
        self.assertEqual(result.manifest.generated_relationship_ids, ())


class WaterfallMarkupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ir, self.result = render_fixture("component-valid-waterfall.json")
        self.markup = self.result.markup

    def _bar_blocks(self) -> list[str]:
        return re.findall(
            r'<div\s+[^>]*\bve-waterfall-bar\b[^>]*>.*?</div>',
            self.markup,
            re.DOTALL,
        )

    def test_figure_with_caption_summary_and_notes(self) -> None:
        self.assertIn('<figure data-ve-component="waterfall"', self.markup)
        self.assertIn(self.ir.caption, self.markup)
        self.assertIn(self.ir.accessibility.summary, self.markup)
        self.assertIn("ve-waterfall-notes", self.markup)

    def test_each_bar_has_exactly_one_visible_value_span(self) -> None:
        for block in self._bar_blocks():
            values = re.findall(
                r'<span\s+[^>]*\bve-waterfall-value\b[^>]*>([^<]*)</span>',
                block,
            )
            self.assertEqual(len(values), 1, block)
            self.assertTrue(values[0].strip(), block)

    def test_connectors_in_track_with_position_classes(self) -> None:
        connectors = re.findall(
            r'<div\s+[^>]*\bve-waterfall-connector-track\b[^>]*>\s*'
            r'<span\s+([^>]*\bve-waterfall-connector\b[^>]*)></span>',
            self.markup,
        )
        wf = self.ir.waterfall
        assert wf is not None
        self.assertEqual(len(connectors), len(wf.steps) + 1)
        for attrs in connectors:
            self.assertEqual(len(re.findall(r"\bve-wf-start-\d+\b", attrs)), 1)
            self.assertEqual(len(re.findall(r"\bve-wf-len-\d+\b", attrs)), 1)

    def test_css_has_exactly_202_percent_rules(self) -> None:
        css = (SKILL / "assets" / "components" / "waterfall.css").read_text("utf-8")
        percent_rules = [
            line for line in css.splitlines()
            if re.search(r"\.ve-wf-(start|len)-\d+\s*\{", line)
        ]
        self.assertEqual(len(percent_rules), 202)
        self.assertNotIn(".ve-wf-bars .ve-wf-start-", css)
        self.assertNotIn(".ve-wf-columns .ve-wf-start-", css)

    def test_each_bar_has_exactly_one_start_and_len_class(self) -> None:
        for block in self._bar_blocks():
            starts = re.findall(r"\bve-wf-start-(\d+)\b", block)
            lens = re.findall(r"\bve-wf-len-(\d+)\b", block)
            self.assertEqual(len(starts), 1, block)
            self.assertEqual(len(lens), 1, block)
            p_start, p_len = int(starts[0]), int(lens[0])
            self.assertGreaterEqual(p_start, 0)
            self.assertLessEqual(p_start, 100)
            self.assertGreaterEqual(p_len, 0)
            self.assertLessEqual(p_len, 100)

    def test_endpoints_map_min_to_zero_max_to_hundred(self) -> None:
        from ve_components.numeric import quantize_percent, waterfall_scale_values

        wf = self.ir.waterfall
        assert wf is not None
        values, lo, hi = waterfall_scale_values(wf)
        self.assertEqual(quantize_percent(lo, lo, hi), 0)
        self.assertEqual(quantize_percent(hi, lo, hi), 100)

    def test_no_inline_style_attributes(self) -> None:
        self.assertNotIn("style=", self.markup)

    def test_value_text_visible_for_start_steps_and_end(self) -> None:
        wf = self.ir.waterfall
        assert wf is not None
        self.assertIn(wf.start.value_text, self.markup)
        self.assertIn(wf.end.value_text, self.markup)
        for step in wf.steps:
            self.assertIn(step.value_text, self.markup)

    def test_tone_classes_only_on_steps(self) -> None:
        wf = self.ir.waterfall
        assert wf is not None
        start_block = re.search(
            rf'data-ve-semantic-id="{re.escape(wf.start.id)}"[^>]*>.*?</div>',
            self.markup,
            re.DOTALL,
        )
        end_block = re.search(
            rf'data-ve-semantic-id="{re.escape(wf.end.id)}"[^>]*>.*?</div>',
            self.markup,
            re.DOTALL,
        )
        self.assertIsNotNone(start_block)
        self.assertIsNotNone(end_block)
        for block in (start_block.group(0), end_block.group(0)):
            self.assertNotRegex(block, r"ve-wf-tone-")
        for step in wf.steps:
            step_block = re.search(
                rf'data-ve-semantic-id="{re.escape(step.id)}"[^>]*>.*?</div>',
                self.markup,
                re.DOTALL,
            )
            self.assertIsNotNone(step_block)
            self.assertIn(f"ve-wf-tone-{step.tone}", step_block.group(0))

    def test_dashed_connectors_between_consecutive_bars(self) -> None:
        connectors = re.findall(r'<span\s+[^>]*\bve-waterfall-connector\b', self.markup)
        wf = self.ir.waterfall
        assert wf is not None
        expected = len(wf.steps) + 1
        self.assertEqual(len(connectors), expected)

    def test_bars_orientation_container(self) -> None:
        self.assertIn("ve-wf-bars", self.markup)
        self.assertNotIn("ve-wf-columns", self.markup)


class WaterfallColumnsMarkupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ir, self.result = render_fixture("component-valid-waterfall-columns.json")
        self.markup = self.result.markup

    def test_columns_in_horizontal_scroll_container(self) -> None:
        self.assertIn("ve-waterfall-scroll", self.markup)
        self.assertIn("overflow-x: auto", (SKILL / "assets" / "components" / "waterfall.css").read_text("utf-8"))
        self.assertIn("ve-wf-columns", self.markup)
        self.assertNotIn("ve-wf-bars", self.markup)

    def test_columns_never_degrades_to_bars(self) -> None:
        self.assertNotIn("ve-wf-bars", self.markup)

    def test_connectors_in_track_with_position_classes(self) -> None:
        connectors = re.findall(
            r'<div\s+[^>]*\bve-waterfall-connector-track\b[^>]*>\s*'
            r'<span\s+([^>]*\bve-waterfall-connector\b[^>]*)></span>',
            self.markup,
        )
        wf = self.ir.waterfall
        assert wf is not None
        self.assertEqual(len(connectors), len(wf.steps) + 1)
        for attrs in connectors:
            self.assertEqual(len(re.findall(r"\bve-wf-start-\d+\b", attrs)), 1)
            self.assertEqual(len(re.findall(r"\bve-wf-len-\d+\b", attrs)), 1)


class WaterfallRendererFailureTest(unittest.TestCase):
    def test_out_of_range_percent_is_renderer_failure_not_clamp(self) -> None:
        from ve_components.renderers.waterfall import render_waterfall

        ir, _ = render_fixture("component-valid-waterfall.json")
        with patch("ve_components.renderers.waterfall.quantize_percent", return_value=101):
            result = render_waterfall(CanonicalSection(ir=ir), WATERFALL_DEF)
        codes = {d.code for d in result.diagnostics}
        self.assertIn(RENDERER_FAILURE, codes)
        self.assertNotIn("ve-wf-start-101", result.markup)
        self.assertNotIn("ve-wf-len-101", result.markup)


if __name__ == "__main__":
    unittest.main()
