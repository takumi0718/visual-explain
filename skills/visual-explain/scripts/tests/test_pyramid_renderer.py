"""S3 tests: pyramid validation and renderer DOM contract."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from ve_components.diagnostics import ContractError
from ve_components.model import CanonicalSection
from ve_components.registry import load_registry
from ve_components.validation import validate_canonical_section

PYRAMID_STRUCTURE_VIOLATION = "pyramid_structure_violation"

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"
PYRAMID_DEF = REGISTRY.find("pyramid", 2)


def _fixture_path(name: str) -> Path:
    return TESTS / name if name.endswith(".json") else TESTS / f"{name}.json"


def _base_ir(**pyramid_overrides) -> dict:
    pyramid = {
        "tiers": [
            {"id": "t-apex", "label": "最優先"},
            {"id": "t-mid", "label": "中位", "sub": "補足テキスト"},
            {"id": "t-base", "label": "基盤層"},
        ],
    }
    pyramid.update(pyramid_overrides)
    return {
        "id": "sec-pyramid",
        "relationship": {
            "kind": "layered-priority",
            "capabilities": ["priority-layering"],
        },
        "selection": {
            "component": "pyramid",
            "version": 2,
            "matchedCapabilities": ["priority-layering"],
        },
        "caption": "優先度の階層",
        "certainty": [{"id": "cert-1", "level": "confirmed", "statement": "テスト用。"}],
        "sources": [{"id": "src-1", "label": "出典"}],
        "accessibility": {"label": "ピラミッド", "summary": "上ほど重要な3層を示す。"},
        "pyramid": pyramid,
    }


def _tiers(n: int) -> list[dict]:
    labels = ["頂点", "中層A", "中層B", "基盤", "余分"]
    return [{"id": f"t{i}", "label": labels[i - 1]} for i in range(1, n + 1)]


def validate_raw(ir: dict):
    return validate_canonical_section(ir)


def expect_violation(ir: dict, code: str = PYRAMID_STRUCTURE_VIOLATION) -> None:
    with unittest.TestCase().assertRaises(ContractError) as ctx:
        validate_raw(ir)
    codes = {d.code for d in ctx.exception.diagnostics}
    unittest.TestCase().assertIn(code, codes)


def render_fixture(name: str = "component-valid-pyramid"):
    from ve_components.renderers.pyramid import render_pyramid
    raw = json.loads(_fixture_path(name).read_text("utf-8"))
    ir = validate_canonical_section(raw["sections"][0]["ir"])
    return ir, render_pyramid(CanonicalSection(ir=ir), PYRAMID_DEF)


class PyramidValidationTest(unittest.TestCase):
    def test_accepts_three_to_four_tiers_top_first(self) -> None:
        for n in range(3, 5):
            with self.subTest(tiers=n):
                ir = _base_ir(tiers=_tiers(n))
                result = validate_raw(ir)
                self.assertEqual(len(result.pyramid.tiers), n)
                self.assertEqual(result.pyramid.tiers[0].id, "t1")

    def test_rejects_two_tiers(self) -> None:
        ir = _base_ir(tiers=_tiers(2))
        expect_violation(ir)

    def test_rejects_five_tiers(self) -> None:
        ir = _base_ir(tiers=_tiers(5))
        expect_violation(ir)

    def test_label_accepts_12_chars(self) -> None:
        ir = _base_ir(tiers=[
            {"id": "t1", "label": "あ" * 12},
            {"id": "t2", "label": "中"},
            {"id": "t3", "label": "下"},
        ])
        validate_raw(ir)

    def test_label_rejects_13_chars(self) -> None:
        ir = _base_ir(tiers=[
            {"id": "t1", "label": "あ" * 13},
            {"id": "t2", "label": "中"},
            {"id": "t3", "label": "下"},
        ])
        expect_violation(ir)

    def test_sub_accepts_30_chars(self) -> None:
        ir = _base_ir(tiers=[
            {"id": "t1", "label": "頂"},
            {"id": "t2", "label": "中", "sub": "あ" * 30},
            {"id": "t3", "label": "下"},
        ])
        validate_raw(ir)

    def test_sub_rejects_31_chars(self) -> None:
        ir = _base_ir(tiers=[
            {"id": "t1", "label": "頂"},
            {"id": "t2", "label": "中", "sub": "あ" * 31},
            {"id": "t3", "label": "下"},
        ])
        expect_violation(ir)


class PyramidManifestTest(unittest.TestCase):
    def test_registry_entry_is_complete(self) -> None:
        self.assertIsNotNone(PYRAMID_DEF)
        self.assertEqual(PYRAMID_DEF.relationship_kind, "layered-priority")
        self.assertEqual(PYRAMID_DEF.capabilities, ("priority-layering",))
        self.assertEqual(PYRAMID_DEF.renderer, "pyramid@2")
        self.assertEqual([a.id for a in PYRAMID_DEF.assets], ["pyramid.css"])

    def test_manifest_consumes_all_semantic_ids(self) -> None:
        ir, result = render_fixture("component-valid-pyramid.json")
        self.assertEqual(set(result.manifest.consumed_semantic_ids), set(ir.semantic_ids()))

    def test_declares_css_and_no_script(self) -> None:
        _, result = render_fixture("component-valid-pyramid.json")
        self.assertEqual(result.style_asset_ids, ("pyramid.css",))
        self.assertEqual(result.script_asset_ids, ())
        self.assertEqual(result.manifest.generated_relationship_ids, ())


class PyramidMarkupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ir, self.result = render_fixture("component-valid-pyramid.json")
        self.markup = self.result.markup

    def test_semantic_figure_with_visible_caption_summary_and_notes(self) -> None:
        self.assertIn('<figure data-ve-component="pyramid"', self.markup)
        self.assertIn("<figcaption", self.markup)
        self.assertIn(self.ir.caption, self.markup)
        self.assertIn(self.ir.accessibility.summary, self.markup)
        self.assertIn("ve-pyramid-notes", self.markup)

    def test_one_tier_per_item_with_semantic_id(self) -> None:
        for tier in self.ir.pyramid.tiers:
            self.assertIn(f'data-ve-semantic-id="{tier.id}"', self.markup)

    def test_widths_via_count_and_index_classes(self) -> None:
        count = len(self.ir.pyramid.tiers)
        self.assertIn(f"ve-pyramid-count-{count}", self.markup)
        for index in range(1, count + 1):
            self.assertIn(f"ve-pyramid-index-{index}", self.markup)

    def test_no_inline_style_attributes(self) -> None:
        self.assertNotIn("style=", self.markup)

    def test_no_flow_or_matrix_relation_attributes(self) -> None:
        self.assertNotIn("data-ve-from", self.markup)
        self.assertNotIn("data-ve-to", self.markup)
        self.assertNotIn("data-ve-relation", self.markup)
        self.assertNotIn("data-ve-row-id", self.markup)
        self.assertNotIn("data-ve-column-id", self.markup)


class PyramidV2Test(unittest.TestCase):
    def test_pyramid_v2_emits_level_classes(self) -> None:
        _, result = render_fixture("component-valid-pyramid")
        markup = result.markup
        for k in (1, 2, 3):
            self.assertIn(f"ve-pyramid-level-{k}", markup)
        self.assertNotIn("ve-pyramid-face-strong", markup)

    def test_pyramid_css_prevents_one_char_wrap(self) -> None:
        css = Path("../assets/components/pyramid.css").read_text(encoding="utf-8")
        self.assertNotIn("fit-content", css)
        self.assertIn("white-space: nowrap", css)
        self.assertIn("min-width: max-content", css)


if __name__ == "__main__":
    unittest.main()
