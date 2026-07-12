"""S1 tests: enumeration renderer DOM contract and manifest invariants."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from ve_components.diagnostics import ContractError
from ve_components.model import CanonicalSection
from ve_components.registry import load_registry
from ve_components.renderers.enumeration import render_enumeration
from ve_components.validation import validate_canonical_section

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"
ENUM_DEF = REGISTRY.find("enumeration", 1)


def render_fixture(name: str = "component-valid-enumeration.json"):
    raw = json.loads((TESTS / name).read_text("utf-8"))
    ir = validate_canonical_section(raw["sections"][0]["ir"])
    return ir, render_enumeration(CanonicalSection(ir=ir), ENUM_DEF)


class EnumerationManifestTest(unittest.TestCase):
    def test_registry_entry_is_complete(self) -> None:
        self.assertIsNotNone(ENUM_DEF)
        self.assertEqual(ENUM_DEF.relationship_kind, "parallel-enumeration")
        self.assertEqual(ENUM_DEF.capabilities, ("parallel-itemization",))
        self.assertEqual(ENUM_DEF.renderer, "enumeration@1")
        self.assertEqual([a.id for a in ENUM_DEF.assets], ["enumeration.css"])

    def test_manifest_consumes_all_semantic_ids(self) -> None:
        ir, result = render_fixture()
        self.assertEqual(set(result.manifest.consumed_semantic_ids), set(ir.semantic_ids()))

    def test_declares_css_and_no_script(self) -> None:
        _, result = render_fixture()
        self.assertEqual(result.style_asset_ids, ("enumeration.css",))
        self.assertEqual(result.script_asset_ids, ())
        self.assertEqual(result.manifest.generated_relationship_ids, ())


class EnumerationMarkupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ir, self.result = render_fixture()
        self.markup = self.result.markup

    def test_semantic_figure_with_visible_caption_summary_and_notes(self) -> None:
        self.assertIn('<figure data-ve-component="enumeration"', self.markup)
        self.assertIn("<figcaption", self.markup)
        self.assertIn(self.ir.caption, self.markup)
        self.assertIn(self.ir.accessibility.summary, self.markup)
        self.assertIn("ve-enumeration-notes", self.markup)

    def test_one_block_per_item_with_semantic_id(self) -> None:
        for item in self.ir.enumeration.items:
            self.assertIn(f'data-ve-semantic-id="{item.id}"', self.markup)

    def test_number_mode_renders_sequence_without_ir_numbers(self) -> None:
        numbers = re.findall(r'class="ve-enum-number"[^>]*>(\d+)<', self.markup)
        self.assertEqual(numbers, ["1", "2", "3"])
        raw = json.loads((TESTS / "component-valid-enumeration.json").read_text("utf-8"))
        for item in raw["sections"][0]["ir"]["enumeration"]["items"]:
            self.assertNotIn("number", item)

    def test_number_mode_requires_title_even_with_description(self) -> None:
        raw = json.loads((TESTS / "component-valid-enumeration.json").read_text("utf-8"))
        items = raw["sections"][0]["ir"]["enumeration"]["items"]
        for item in items:
            item["description"] = ["全項目に説明がある"]
        item = items[0]
        item.pop("title")
        item["description"] = ["説明だけではコンセプトにならない"]
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(raw["sections"][0]["ir"])
        self.assertIn(
            "enumeration_structure_violation",
            {diagnostic.code for diagnostic in ctx.exception.diagnostics},
        )

    def test_item_container_is_unordered_not_ordered_list(self) -> None:
        self.assertIn('<ul class="ve-enum-items', self.markup)
        self.assertNotRegex(self.markup, r"<ol[^>]*class=\"[^\"]*ve-enum-items")

    def test_number_spans_are_decorative_only(self) -> None:
        for match in re.finditer(r'<span class="ve-enum-number"([^>]*)>', self.markup):
            self.assertIn('aria-hidden="true"', match.group(1))

    def test_list_presentation_uses_centered_wrapper(self) -> None:
        self.assertIn("ve-enum-list-centered", self.markup)

    def test_columns_presentation_uses_columns_wrapper(self) -> None:
        ir, result = render_fixture("component-valid-enumeration-columns.json")
        self.assertIn("ve-enum-columns", result.markup)

    def test_no_flow_or_matrix_relation_attributes(self) -> None:
        self.assertNotIn("data-ve-from", self.markup)
        self.assertNotIn("data-ve-to", self.markup)
        self.assertNotIn("data-ve-relation", self.markup)
        self.assertNotIn("data-ve-row-id", self.markup)
        self.assertNotIn("data-ve-column-id", self.markup)


if __name__ == "__main__":
    unittest.main()
