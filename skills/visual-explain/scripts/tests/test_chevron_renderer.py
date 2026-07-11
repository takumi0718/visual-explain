"""S2 tests: chevron validation and renderer DOM contract."""
from __future__ import annotations

import json
import re
import unittest
from copy import deepcopy
from pathlib import Path

from ve_components.diagnostics import ContractError
from ve_components.model import CanonicalSection
from ve_components.registry import load_registry
from ve_components.validation import validate_canonical_section

CHEVRON_STRUCTURE_VIOLATION = "chevron_structure_violation"

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"
CHEVRON_DEF = REGISTRY.find("chevron", 1)


def _base_ir(**chevron_overrides) -> dict:
    """Minimal valid chevron IR skeleton for validation tests."""
    chevron = {
        "steps": [
            {"id": "s1", "title": "受付", "description": ["行1", "行2"]},
            {"id": "s2", "title": "検証", "description": ["行1", "行2"]},
        ],
        "orientation": "vertical",
        "blockContent": "number",
        "loop": False,
    }
    chevron.update(chevron_overrides)
    return {
        "id": "sec-chevron",
        "relationship": {
            "kind": "ordered-sequence",
            "capabilities": ["linear-sequence"],
        },
        "selection": {
            "component": "chevron",
            "version": 1,
            "matchedCapabilities": ["linear-sequence"],
        },
        "caption": "線形順序のチェブロン",
        "certainty": [{"id": "cert-1", "level": "confirmed", "statement": "テスト用。"}],
        "sources": [{"id": "src-1", "label": "出典"}],
        "accessibility": {"label": "チェブロン", "summary": "順序付きステップを示す。"},
        "chevron": chevron,
    }


def _steps(n: int, *, horizontal: bool = False) -> list[dict]:
    out: list[dict] = []
    for i in range(1, n + 1):
        step: dict = {"id": f"s{i}"}
        if horizontal:
            step["description"] = [f"説明{i}（横）"]
        else:
            step["title"] = f"段{i}"
            step["description"] = ["行1", "行2"]
        out.append(step)
    return out


def validate_raw(ir: dict):
    return validate_canonical_section(ir)


def expect_violation(ir: dict, code: str = CHEVRON_STRUCTURE_VIOLATION) -> None:
    with unittest.TestCase().assertRaises(ContractError) as ctx:
        validate_raw(ir)
    codes = {d.code for d in ctx.exception.diagnostics}
    unittest.TestCase().assertIn(code, codes)


def render_fixture(name: str):
    from ve_components.renderers.chevron import render_chevron
    raw = json.loads((TESTS / name).read_text("utf-8"))
    ir = validate_canonical_section(raw["sections"][0]["ir"])
    return ir, render_chevron(CanonicalSection(ir=ir), CHEVRON_DEF)


class ChevronValidationTest(unittest.TestCase):
    def test_accepts_two_to_six_steps(self) -> None:
        for n in range(2, 7):
            with self.subTest(steps=n):
                ir = _base_ir(steps=_steps(n))
                result = validate_raw(ir)
                self.assertEqual(len(result.chevron.steps), n)

    def test_rejects_loop_true_with_horizontal_orientation(self) -> None:
        ir = _base_ir(
            orientation="horizontal",
            loop=True,
            steps=_steps(3, horizontal=True),
        )
        ir["relationship"]["capabilities"] = ["linear-sequence", "closed-loop"]
        ir["selection"]["matchedCapabilities"] = ["linear-sequence", "closed-loop"]
        expect_violation(ir)

    def test_rejects_loop_true_without_closed_loop_capability(self) -> None:
        ir = _base_ir(loop=True, blockContent="label", steps=[
            {"id": "s1", "label": "計測"},
            {"id": "s2", "label": "評価"},
            {"id": "s3", "label": "改善"},
        ])
        expect_violation(ir)

    def test_rejects_closed_loop_capability_without_loop_true(self) -> None:
        ir = _base_ir(steps=_steps(3))
        ir["relationship"]["capabilities"] = ["linear-sequence", "closed-loop"]
        ir["selection"]["matchedCapabilities"] = ["linear-sequence", "closed-loop"]
        expect_violation(ir)

    def test_rejects_title_in_horizontal_orientation(self) -> None:
        ir = _base_ir(
            orientation="horizontal",
            steps=[
                {"id": "s1", "title": "禁止", "description": ["説明1"]},
                {"id": "s2", "description": ["説明2"]},
                {"id": "s3", "description": ["説明3"]},
            ],
        )
        expect_violation(ir)

    def test_rejects_horizontal_number_mode_without_descriptions(self) -> None:
        ir = _base_ir(
            orientation="horizontal",
            steps=[
                {"id": "s1", "description": ["説明1"]},
                {"id": "s2"},
                {"id": "s3", "description": ["説明3"]},
            ],
        )
        expect_violation(ir)

    def test_vertical_description_accepts_40_char_line(self) -> None:
        line = "あ" * 40
        ir = _base_ir(steps=[
            {"id": "s1", "title": "A", "description": [line]},
            {"id": "s2", "title": "B", "description": ["短い"]},
        ])
        validate_raw(ir)

    def test_vertical_description_rejects_41_char_line(self) -> None:
        line = "あ" * 41
        ir = _base_ir(steps=[
            {"id": "s1", "title": "A", "description": [line]},
            {"id": "s2", "title": "B", "description": ["短い"]},
        ])
        expect_violation(ir)

    def test_horizontal_description_accepts_30_char_line(self) -> None:
        line = "あ" * 30
        ir = _base_ir(
            orientation="horizontal",
            steps=[
                {"id": "s1", "description": [line]},
                {"id": "s2", "description": ["短"]},
                {"id": "s3", "description": ["短"]},
            ],
        )
        validate_raw(ir)

    def test_horizontal_description_rejects_31_char_line(self) -> None:
        line = "あ" * 31
        ir = _base_ir(
            orientation="horizontal",
            steps=[
                {"id": "s1", "description": [line]},
                {"id": "s2", "description": ["短"]},
                {"id": "s3", "description": ["短"]},
            ],
        )
        expect_violation(ir)

    def test_vertical_description_accepts_one_line(self) -> None:
        ir = _base_ir(steps=[
            {"id": "s1", "title": "A", "description": ["一行のみ"]},
            {"id": "s2", "title": "B", "description": ["一行のみ"]},
        ])
        validate_raw(ir)

    def test_vertical_description_accepts_three_lines(self) -> None:
        ir = _base_ir(steps=[
            {"id": "s1", "title": "A", "description": ["行1", "行2", "行3"]},
            {"id": "s2", "title": "B", "description": ["行1", "行2", "行3"]},
        ])
        validate_raw(ir)

    def test_vertical_description_rejects_four_lines(self) -> None:
        ir = _base_ir(steps=[
            {"id": "s1", "title": "A", "description": ["行1", "行2", "行3", "行4"]},
            {"id": "s2", "title": "B", "description": ["短"]},
        ])
        expect_violation(ir)

    def test_horizontal_description_accepts_two_lines(self) -> None:
        ir = _base_ir(
            orientation="horizontal",
            steps=[
                {"id": "s1", "description": ["行1", "行2"]},
                {"id": "s2", "description": ["行1", "行2"]},
                {"id": "s3", "description": ["行1", "行2"]},
            ],
        )
        validate_raw(ir)

    def test_horizontal_description_rejects_three_lines(self) -> None:
        ir = _base_ir(
            orientation="horizontal",
            steps=[
                {"id": "s1", "description": ["行1", "行2", "行3"]},
                {"id": "s2", "description": ["短"]},
                {"id": "s3", "description": ["短"]},
            ],
        )
        expect_violation(ir)

    def test_rejects_gap_in_descriptions(self) -> None:
        ir = _base_ir(steps=[
            {"id": "s1", "title": "A", "description": ["あり"]},
            {"id": "s2", "title": "B"},
        ])
        expect_violation(ir)


class ChevronManifestTest(unittest.TestCase):
    def test_registry_entry_is_complete(self) -> None:
        self.assertIsNotNone(CHEVRON_DEF)
        self.assertEqual(CHEVRON_DEF.relationship_kind, "ordered-sequence")
        self.assertEqual(CHEVRON_DEF.capabilities, ("linear-sequence", "closed-loop"))
        self.assertEqual(CHEVRON_DEF.renderer, "chevron@1")
        self.assertEqual([a.id for a in CHEVRON_DEF.assets], ["chevron.css"])

    def test_manifest_consumes_all_semantic_ids(self) -> None:
        ir, result = render_fixture("component-valid-chevron.json")
        self.assertEqual(set(result.manifest.consumed_semantic_ids), set(ir.semantic_ids()))

    def test_declares_css_and_no_script(self) -> None:
        _, result = render_fixture("component-valid-chevron.json")
        self.assertEqual(result.style_asset_ids, ("chevron.css",))
        self.assertEqual(result.script_asset_ids, ())
        self.assertEqual(result.manifest.generated_relationship_ids, ())


class ChevronMarkupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ir, self.result = render_fixture("component-valid-chevron.json")
        self.markup = self.result.markup

    def test_semantic_figure_with_visible_caption_summary_and_notes(self) -> None:
        self.assertIn('<figure data-ve-component="chevron"', self.markup)
        self.assertIn("<figcaption", self.markup)
        self.assertIn(self.ir.caption, self.markup)
        self.assertIn(self.ir.accessibility.summary, self.markup)
        self.assertIn("ve-chevron-notes", self.markup)

    def test_one_block_per_step_with_semantic_id(self) -> None:
        for step in self.ir.chevron.steps:
            self.assertIn(f'data-ve-semantic-id="{step.id}"', self.markup)

    def test_vertical_variant_uses_centered_wrapper(self) -> None:
        self.assertIn("ve-chevron-centered", self.markup)

    def test_loop_renders_exactly_one_return_rail_without_from_to(self) -> None:
        _, result = render_fixture("component-valid-chevron-loop.json")
        markup = result.markup
        rails = re.findall(r'class="[^"]*ve-chevron-loop-rail[^"]*"', markup)
        self.assertEqual(len(rails), 1)
        self.assertNotIn("data-ve-from", markup)
        self.assertNotIn("data-ve-to", markup)

    def test_loop_wraps_centered_column_for_rail_alignment(self) -> None:
        _, result = render_fixture("component-valid-chevron-loop.json")
        self.assertIn("ve-chevron-centered-column", result.markup)
        self.assertRegex(
            result.markup,
            r'<div class="ve-chevron-centered-column">.*?ve-chevron-loop-rail.*?ve-chevron-steps',
            re.DOTALL,
        )

    def test_loop_rail_css_points_arrowhead_upward(self) -> None:
        css = (SKILL / "assets" / "components" / "chevron.css").read_text("utf-8")
        self.assertIn(".ve-chevron-loop-rail::after", css)
        after_block = css.split(".ve-chevron-loop-rail::after")[1].split("}")[0]
        self.assertIn("top: 0", after_block)
        self.assertIn("border-bottom-color", after_block)
        self.assertNotIn("border-top-color", after_block)

    def test_horizontal_clip_path_has_right_tip_and_left_notch(self) -> None:
        css = (SKILL / "assets" / "components" / "chevron.css").read_text("utf-8")
        horiz_block = css.split(".ve-chevron-horizontal .ve-chevron-step {")[1].split("}")[0]
        self.assertIn("clip-path: polygon(", horiz_block)
        self.assertIn("100% 50%", horiz_block)
        self.assertIn("0 50%", horiz_block)
        self.assertIn("calc(100% - 0.75rem)", horiz_block)
        self.assertIn("0.75rem 0", horiz_block)

    def test_narrow_screen_resets_horizontal_overlap_margin(self) -> None:
        css = (SKILL / "assets" / "components" / "chevron.css").read_text("utf-8")
        media_block = css.split("@media (max-width: 40rem)")[1]
        self.assertIn(".ve-chevron-horizontal .ve-chevron-step + .ve-chevron-step", media_block)
        reset_block = media_block.split(
            ".ve-chevron-horizontal .ve-chevron-step + .ve-chevron-step"
        )[1].split("}")[0]
        self.assertIn("margin-left: 0", reset_block)

    def test_loop_adds_visually_hidden_last_to_first_sentence(self) -> None:
        ir, result = render_fixture("component-valid-chevron-loop.json")
        hidden = re.search(r'<ul class="ve-chevron-loop-sentence visually-hidden">(.*?)</ul>', result.markup, re.DOTALL)
        self.assertIsNotNone(hidden)
        last_label = ir.chevron.steps[-1].label
        first_label = ir.chevron.steps[0].label
        self.assertTrue(last_label and first_label)
        self.assertIn(last_label, hidden.group(1))
        self.assertIn(first_label, hidden.group(1))
        self.assertRegex(hidden.group(1), rf"最終段〈{re.escape(last_label)}〉から先頭段〈{re.escape(first_label)}〉へ戻る")

    def test_number_mode_loop_names_nonempty_endpoints_last_to_first(self) -> None:
        ir, result = render_fixture("component-valid-chevron-loop-number.json")
        hidden = re.search(r'<ul class="ve-chevron-loop-sentence visually-hidden">(.*?)</ul>', result.markup, re.DOTALL)
        self.assertIsNotNone(hidden)
        last_title = ir.chevron.steps[-1].title
        first_title = ir.chevron.steps[0].title
        self.assertTrue(last_title and first_title)
        sentence = hidden.group(1)
        self.assertIn(last_title, sentence)
        self.assertIn(first_title, sentence)
        self.assertRegex(sentence, rf"最終段〈{re.escape(last_title)}〉から先頭段〈{re.escape(first_title)}〉へ戻る")
        self.assertLess(sentence.index(first_title), sentence.index("へ戻る"))

    def test_number_mode_loop_falls_back_to_ordinal_when_no_label_or_title(self) -> None:
        from ve_components.renderers.chevron import render_chevron
        raw = _base_ir(
            loop=True,
            blockContent="number",
            steps=[
                {"id": "s1", "description": ["行1"]},
                {"id": "s2", "description": ["行2"]},
                {"id": "s3", "description": ["行3"]},
            ],
        )
        raw["relationship"]["capabilities"] = ["linear-sequence", "closed-loop"]
        raw["selection"]["matchedCapabilities"] = ["linear-sequence", "closed-loop"]
        ir = validate_canonical_section(raw)
        result = render_chevron(CanonicalSection(ir=ir), CHEVRON_DEF)
        hidden = re.search(r'<ul class="ve-chevron-loop-sentence visually-hidden">(.*?)</ul>', result.markup, re.DOTALL)
        self.assertIsNotNone(hidden)
        sentence = hidden.group(1)
        self.assertIn("ステップ 3", sentence)
        self.assertIn("ステップ 1", sentence)
        self.assertRegex(sentence, r"最終段〈ステップ 3〉から先頭段〈ステップ 1〉へ戻る")

    def test_horizontal_variant_has_no_loop_rail(self) -> None:
        _, result = render_fixture("component-valid-chevron-horizontal.json")
        self.assertNotIn("ve-chevron-loop-rail", result.markup)
        self.assertIn("ve-chevron-horizontal", result.markup)

    def test_no_flow_or_matrix_relation_attributes(self) -> None:
        self.assertNotIn("data-ve-from", self.markup)
        self.assertNotIn("data-ve-to", self.markup)
        self.assertNotIn("data-ve-relation", self.markup)
        self.assertNotIn("data-ve-row-id", self.markup)
        self.assertNotIn("data-ve-column-id", self.markup)


if __name__ == "__main__":
    unittest.main()
