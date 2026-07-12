"""S3 tests: stairs validation and renderer DOM contract."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from ve_components.diagnostics import ContractError
from ve_components.model import CanonicalSection
from ve_components.registry import load_registry
from ve_components.validation import validate_canonical_section

STAIRS_STRUCTURE_VIOLATION = "stairs_structure_violation"

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"
STAIRS_DEF = REGISTRY.find("stairs", 1)


def _base_ir(**stairs_overrides) -> dict:
    stairs = {
        "stages": [
            {"id": "s-low", "label": "初期段"},
            {"id": "s-mid", "label": "移行段", "current": True, "note": "現在地"},
            {"id": "s-high", "label": "到達段"},
        ],
    }
    stairs.update(stairs_overrides)
    return {
        "id": "sec-stairs",
        "relationship": {
            "kind": "staged-maturity",
            "capabilities": ["maturity-staging"],
        },
        "selection": {
            "component": "stairs",
            "version": 1,
            "matchedCapabilities": ["maturity-staging"],
        },
        "caption": "成熟度の階段",
        "certainty": [{"id": "cert-1", "level": "confirmed", "statement": "テスト用。"}],
        "sources": [{"id": "src-1", "label": "出典"}],
        "accessibility": {"label": "階段", "summary": "低い段から高い段へ成熟度を示す。"},
        "stairs": stairs,
    }


def _stages(n: int, *, current_index: int | None = None) -> list[dict]:
    out: list[dict] = []
    for i in range(1, n + 1):
        stage: dict = {"id": f"s{i}", "label": f"段{i}"}
        if current_index == i:
            stage["current"] = True
            stage["note"] = "ここにいる"
        out.append(stage)
    return out


def validate_raw(ir: dict):
    return validate_canonical_section(ir)


def expect_violation(ir: dict, code: str = STAIRS_STRUCTURE_VIOLATION) -> None:
    with unittest.TestCase().assertRaises(ContractError) as ctx:
        validate_raw(ir)
    codes = {d.code for d in ctx.exception.diagnostics}
    unittest.TestCase().assertIn(code, codes)


def render_fixture(name: str):
    from ve_components.renderers.stairs import render_stairs
    raw = json.loads((TESTS / name).read_text("utf-8"))
    ir = validate_canonical_section(raw["sections"][0]["ir"])
    return ir, render_stairs(CanonicalSection(ir=ir), STAIRS_DEF)


class StairsValidationTest(unittest.TestCase):
    def test_accepts_three_to_five_stages_low_to_high(self) -> None:
        for n in range(3, 6):
            with self.subTest(stages=n):
                ir = _base_ir(stages=_stages(n, current_index=2 if n >= 2 else None))
                result = validate_raw(ir)
                self.assertEqual(len(result.stairs.stages), n)
                self.assertEqual(result.stairs.stages[0].id, "s1")

    def test_rejects_two_stages(self) -> None:
        ir = _base_ir(stages=_stages(2))
        expect_violation(ir)

    def test_rejects_six_stages(self) -> None:
        ir = _base_ir(stages=_stages(6))
        expect_violation(ir)

    def test_label_accepts_14_chars(self) -> None:
        ir = _base_ir(stages=[
            {"id": "s1", "label": "あ" * 14},
            {"id": "s2", "label": "中", "current": True, "note": "現在地"},
            {"id": "s3", "label": "上"},
        ])
        validate_raw(ir)

    def test_label_rejects_15_chars(self) -> None:
        ir = _base_ir(stages=[
            {"id": "s1", "label": "あ" * 15},
            {"id": "s2", "label": "中", "current": True, "note": "現在地"},
            {"id": "s3", "label": "上"},
        ])
        expect_violation(ir)

    def test_note_accepts_20_chars(self) -> None:
        ir = _base_ir(stages=[
            {"id": "s1", "label": "下"},
            {"id": "s2", "label": "中", "current": True, "note": "あ" * 20},
            {"id": "s3", "label": "上"},
        ])
        validate_raw(ir)

    def test_note_rejects_21_chars(self) -> None:
        ir = _base_ir(stages=[
            {"id": "s1", "label": "下"},
            {"id": "s2", "label": "中", "current": True, "note": "あ" * 21},
            {"id": "s3", "label": "上"},
        ])
        expect_violation(ir)

    def test_rejects_two_current_stages(self) -> None:
        ir = _base_ir(stages=[
            {"id": "s1", "label": "下", "current": True, "note": "A"},
            {"id": "s2", "label": "中", "current": True, "note": "B"},
            {"id": "s3", "label": "上"},
        ])
        expect_violation(ir)

    def test_current_without_note_raises_stairs_structure_violation(self) -> None:
        ir = _base_ir(stages=[
            {"id": "s1", "label": "下"},
            {"id": "s2", "label": "中", "current": True},
            {"id": "s3", "label": "上"},
        ])
        expect_violation(ir)


class StairsManifestTest(unittest.TestCase):
    def test_registry_entry_is_complete(self) -> None:
        self.assertIsNotNone(STAIRS_DEF)
        self.assertEqual(STAIRS_DEF.relationship_kind, "staged-maturity")
        self.assertEqual(STAIRS_DEF.capabilities, ("maturity-staging",))
        self.assertEqual(STAIRS_DEF.renderer, "stairs@1")
        self.assertEqual([a.id for a in STAIRS_DEF.assets], ["stairs.css"])

    def test_manifest_consumes_all_semantic_ids(self) -> None:
        ir, result = render_fixture("component-valid-stairs.json")
        self.assertEqual(set(result.manifest.consumed_semantic_ids), set(ir.semantic_ids()))

    def test_declares_css_and_no_script(self) -> None:
        _, result = render_fixture("component-valid-stairs.json")
        self.assertEqual(result.style_asset_ids, ("stairs.css",))
        self.assertEqual(result.script_asset_ids, ())
        self.assertEqual(result.manifest.generated_relationship_ids, ())


class StairsMarkupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ir, self.result = render_fixture("component-valid-stairs.json")
        self.markup = self.result.markup

    def test_semantic_figure_with_visible_caption_summary_and_notes(self) -> None:
        self.assertIn('<figure data-ve-component="stairs"', self.markup)
        self.assertIn("<figcaption", self.markup)
        self.assertIn(self.ir.caption, self.markup)
        self.assertIn(self.ir.accessibility.summary, self.markup)
        self.assertIn("ve-stairs-notes", self.markup)

    def test_one_stage_per_item_with_semantic_id(self) -> None:
        for stage in self.ir.stairs.stages:
            self.assertIn(f'data-ve-semantic-id="{stage.id}"', self.markup)

    def test_current_tread_only_gets_accent_class(self) -> None:
        current = next(s for s in self.ir.stairs.stages if s.current)
        last = self.ir.stairs.stages[-1]
        for stage in self.ir.stairs.stages:
            block = re.search(
                rf'<li[^>]*data-ve-semantic-id="{re.escape(stage.id)}"[^>]*>.*?</li>',
                self.markup,
                re.DOTALL,
            )
            self.assertIsNotNone(block)
            if stage.id == current.id:
                self.assertIn("ve-stairs-tread-accent", block.group(0))
            else:
                self.assertNotIn("ve-stairs-tread-accent", block.group(0))
        last_block = re.search(
            rf'<li[^>]*data-ve-semantic-id="{re.escape(last.id)}"[^>]*>.*?</li>',
            self.markup,
            re.DOTALL,
        )
        self.assertIsNotNone(last_block)
        self.assertNotIn("ve-stairs-tread-accent", last_block.group(0))

    def test_current_note_text_rendered_visibly(self) -> None:
        current = next(s for s in self.ir.stairs.stages if s.current)
        self.assertIsNotNone(current.note)
        self.assertIn(current.note, self.markup)
        self.assertIn("ve-stairs-note", self.markup)

    def test_heights_via_count_and_index_classes(self) -> None:
        count = len(self.ir.stairs.stages)
        self.assertIn(f"ve-stairs-count-{count}", self.markup)
        for index in range(1, count + 1):
            self.assertIn(f"ve-stairs-index-{index}", self.markup)

    def test_no_inline_style_attributes(self) -> None:
        self.assertNotIn("style=", self.markup)

    def test_no_flow_or_matrix_relation_attributes(self) -> None:
        self.assertNotIn("data-ve-from", self.markup)
        self.assertNotIn("data-ve-to", self.markup)
        self.assertNotIn("data-ve-relation", self.markup)
        self.assertNotIn("data-ve-row-id", self.markup)
        self.assertNotIn("data-ve-column-id", self.markup)


if __name__ == "__main__":
    unittest.main()
