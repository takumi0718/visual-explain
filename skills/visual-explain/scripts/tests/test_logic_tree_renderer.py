"""S4 tests: logic-tree validation and renderer DOM contract."""
from __future__ import annotations

from fixture_util import canonical_ir, canonical_section
import json
import re
import unittest
from pathlib import Path

from ve_components.diagnostics import ContractError, INVALID_COMPONENT_PAYLOAD
from ve_components.model import CanonicalSection
from ve_components.registry import load_registry
from ve_components.validation import validate_canonical_section

LOGIC_TREE_STRUCTURE_VIOLATION = "logic_tree_structure_violation"

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"
COMPONENTS = SKILL / "assets" / "components"
LOGIC_TREE_DEF = REGISTRY.find("logic-tree", 2)


def _base_ir(**logic_tree_overrides) -> dict:
    logic_tree = {
        "root": {"id": "root-topic", "label": "全体テーマ"},
        "branches": [
            {"id": "branch-a", "label": "枝A"},
            {"id": "branch-b", "label": "枝B", "leaves": [{"id": "leaf-b1", "text": "詳細B"}]},
            {
                "id": "branch-c",
                "label": "枝C",
                "leaves": [
                    {"id": "leaf-c1", "text": "詳細C1"},
                    {"id": "leaf-c2", "text": "詳細C2"},
                ],
            },
        ],
    }
    logic_tree.update(logic_tree_overrides)
    return {
        "id": "sec-logic-tree",
        "relationship": {
            "kind": "hierarchical-decomposition",
            "capabilities": ["mece-decomposition"],
        },
        "selection": {
            "component": "logic-tree",
            "version": 2,
            "matchedCapabilities": ["mece-decomposition"],
        },
        "caption": "構成の分解",
        "certainty": [{"id": "cert-lt", "level": "confirmed", "statement": "テスト用。"}],
        "sources": [{"id": "src-lt", "label": "出典"}],
        "accessibility": {"label": "ロジックツリー", "summary": "全体を枝に分解して示す。"},
        "logic-tree": logic_tree,
    }


def _branches(n: int, *, leaves_per_branch: int = 0) -> list[dict]:
    out: list[dict] = []
    for i in range(1, n + 1):
        branch: dict = {"id": f"branch-{i}", "label": f"枝{i}"}
        if leaves_per_branch:
            branch["leaves"] = [
                {"id": f"leaf-{i}-{j}", "text": f"詳細{i}-{j}"}
                for j in range(1, leaves_per_branch + 1)
            ]
        out.append(branch)
    return out


def validate_raw(ir: dict):
    return validate_canonical_section(ir)


def expect_violation(ir: dict, code: str = LOGIC_TREE_STRUCTURE_VIOLATION) -> None:
    with unittest.TestCase().assertRaises(ContractError) as ctx:
        validate_raw(ir)
    codes = {d.code for d in ctx.exception.diagnostics}
    unittest.TestCase().assertIn(code, codes)


def _fixture_path(name: str) -> Path:
    return TESTS / name if name.endswith(".json") else TESTS / f"{name}.json"


def render_fixture(name: str):
    from ve_components.renderers.logic_tree import render_logic_tree
    raw = json.loads(_fixture_path(name).read_text("utf-8"))
    ir = validate_canonical_section(canonical_ir(raw))
    return ir, render_logic_tree(CanonicalSection(ir=ir), LOGIC_TREE_DEF)


class LogicTreeValidationTest(unittest.TestCase):
    def test_accepts_two_to_four_branches(self) -> None:
        for n in range(2, 5):
            with self.subTest(branches=n):
                ir = _base_ir(branches=_branches(n))
                result = validate_raw(ir)
                self.assertEqual(len(result.logic_tree.branches), n)

    def test_rejects_one_branch(self) -> None:
        ir = _base_ir(branches=_branches(1))
        expect_violation(ir)

    def test_rejects_five_branches(self) -> None:
        ir = _base_ir(branches=_branches(5))
        expect_violation(ir)

    def test_rejects_three_leaves_on_branch(self) -> None:
        ir = _base_ir(branches=[
            {"id": "branch-a", "label": "枝A"},
            {
                "id": "branch-b",
                "label": "枝B",
                "leaves": [
                    {"id": "leaf-1", "text": "a"},
                    {"id": "leaf-2", "text": "b"},
                    {"id": "leaf-3", "text": "c"},
                ],
            },
        ])
        expect_violation(ir)

    def test_root_label_accepts_20_chars(self) -> None:
        ir = _base_ir(root={"id": "root-topic", "label": "あ" * 20})
        validate_raw(ir)

    def test_root_label_rejects_21_chars(self) -> None:
        ir = _base_ir(root={"id": "root-topic", "label": "あ" * 21})
        expect_violation(ir)

    def test_branch_label_accepts_16_chars(self) -> None:
        ir = _base_ir(branches=[
            {"id": "branch-a", "label": "あ" * 16},
            {"id": "branch-b", "label": "枝B"},
        ])
        validate_raw(ir)

    def test_branch_label_rejects_17_chars(self) -> None:
        ir = _base_ir(branches=[
            {"id": "branch-a", "label": "あ" * 17},
            {"id": "branch-b", "label": "枝B"},
        ])
        expect_violation(ir)

    def test_leaf_text_accepts_40_chars(self) -> None:
        ir = _base_ir(branches=[
            {"id": "branch-a", "label": "枝A"},
            {"id": "branch-b", "label": "枝B", "leaves": [{"id": "leaf-1", "text": "あ" * 40}]},
        ])
        validate_raw(ir)

    def test_leaf_text_rejects_41_chars(self) -> None:
        ir = _base_ir(branches=[
            {"id": "branch-a", "label": "枝A"},
            {"id": "branch-b", "label": "枝B", "leaves": [{"id": "leaf-1", "text": "あ" * 41}]},
        ])
        expect_violation(ir)

    def test_leaf_with_nested_leaves_rejects_unknown_field(self) -> None:
        ir = _base_ir(branches=[
            {"id": "branch-a", "label": "枝A"},
            {
                "id": "branch-b",
                "label": "枝B",
                "leaves": [{"id": "leaf-1", "text": "詳細", "leaves": [{"id": "x", "text": "y"}]}],
            },
        ])
        with self.assertRaises(ContractError) as ctx:
            validate_raw(ir)
        codes = {d.code for d in ctx.exception.diagnostics}
        self.assertIn(INVALID_COMPONENT_PAYLOAD, codes)

    def test_bad_fixture_too_few_branches(self) -> None:
        raw = json.loads((TESTS / "component-bad-logic-tree-too-few-branches.json").read_text("utf-8"))
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(canonical_ir(raw))
        self.assertIn(LOGIC_TREE_STRUCTURE_VIOLATION, {d.code for d in ctx.exception.diagnostics})

    def test_bad_fixture_too_many_branches(self) -> None:
        raw = json.loads((TESTS / "component-bad-logic-tree-too-many-branches.json").read_text("utf-8"))
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(canonical_ir(raw))
        self.assertIn(LOGIC_TREE_STRUCTURE_VIOLATION, {d.code for d in ctx.exception.diagnostics})

    def test_bad_fixture_three_leaves(self) -> None:
        raw = json.loads((TESTS / "component-bad-logic-tree-three-leaves.json").read_text("utf-8"))
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(canonical_ir(raw))
        self.assertIn(LOGIC_TREE_STRUCTURE_VIOLATION, {d.code for d in ctx.exception.diagnostics})

    def test_bad_fixture_label_long(self) -> None:
        raw = json.loads((TESTS / "component-bad-logic-tree-label-long.json").read_text("utf-8"))
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(canonical_ir(raw))
        self.assertIn(LOGIC_TREE_STRUCTURE_VIOLATION, {d.code for d in ctx.exception.diagnostics})

    def test_bad_fixture_depth(self) -> None:
        raw = json.loads((TESTS / "component-bad-logic-tree-depth.json").read_text("utf-8"))
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(canonical_ir(raw))
        self.assertIn(INVALID_COMPONENT_PAYLOAD, {d.code for d in ctx.exception.diagnostics})


class LogicTreeManifestTest(unittest.TestCase):
    def test_registry_entry_is_complete(self) -> None:
        self.assertIsNotNone(LOGIC_TREE_DEF)
        self.assertEqual(LOGIC_TREE_DEF.relationship_kind, "hierarchical-decomposition")
        self.assertEqual(LOGIC_TREE_DEF.capabilities, ("mece-decomposition",))
        self.assertEqual(LOGIC_TREE_DEF.renderer, "logic-tree@2")
        self.assertEqual([a.id for a in LOGIC_TREE_DEF.assets], ["logic-tree.css"])

    def test_manifest_consumes_all_semantic_ids(self) -> None:
        ir, result = render_fixture("component-valid-logic-tree.json")
        self.assertEqual(set(result.manifest.consumed_semantic_ids), set(ir.semantic_ids()))

    def test_declares_css_and_no_script(self) -> None:
        _, result = render_fixture("component-valid-logic-tree.json")
        self.assertEqual(result.style_asset_ids, ("logic-tree.css",))
        self.assertEqual(result.script_asset_ids, ())
        self.assertEqual(result.manifest.generated_relationship_ids, ())


class LogicTreeMarkupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ir, self.result = render_fixture("component-valid-logic-tree.json")
        self.markup = self.result.markup

    def test_semantic_figure_with_visible_caption_summary_and_notes(self) -> None:
        self.assertIn('<figure data-ve-component="logic-tree"', self.markup)
        self.assertIn("<figcaption", self.markup)
        self.assertIn(self.ir.caption, self.markup)
        self.assertIn(self.ir.accessibility.summary, self.markup)
        self.assertIn("ve-logic-tree-notes", self.markup)

    def test_elbow_layout_wrapper(self) -> None:
        self.assertIn('class="ve-lt"', self.markup)
        self.assertIn("ve-lt-root", self.markup)
        self.assertIn("ve-lt-children", self.markup)

    def test_root_precedes_branches_in_dom(self) -> None:
        root_pos = self.markup.index("ve-lt-root")
        branches_pos = self.markup.index("ve-lt-children")
        self.assertLess(root_pos, branches_pos)

    def test_semantic_ids_on_root_branches_and_leaves(self) -> None:
        self.assertIn(f'data-ve-semantic-id="{self.ir.logic_tree.root.id}"', self.markup)
        for branch in self.ir.logic_tree.branches:
            self.assertIn(f'data-ve-semantic-id="{branch.id}"', self.markup)
            for leaf in branch.leaves:
                self.assertIn(f'data-ve-semantic-id="{leaf.id}"', self.markup)

    def test_stubs_are_presentation_only(self) -> None:
        stubs = re.findall(r'<div class="ve-lt-stub"[^>]*>', self.markup)
        self.assertGreaterEqual(len(stubs), 1)
        for tag in stubs:
            self.assertNotIn("data-ve-semantic-id", tag)
            self.assertNotIn("data-ve-from", tag)
            self.assertNotIn("data-ve-to", tag)
            self.assertNotIn("data-connect", tag)

    def test_elbow_connector_css(self) -> None:
        css = (COMPONENTS / "logic-tree.css").read_text("utf-8")
        self.assertIn(".ve-lt-stub", css)
        stub_block = css.split(".ve-lt-stub {")[1].split("}")[0]
        self.assertIn("border-top", stub_block)
        child_block = css.split(".ve-lt-child::before {")[1].split("}")[0]
        self.assertIn("border-top", child_block)
        spine_block = css.split(".ve-lt-child::after {")[1].split("}")[0]
        self.assertIn("border-left", spine_block)

    def test_no_inline_style_attributes(self) -> None:
        self.assertNotIn("style=", self.markup)

    def test_no_flow_or_matrix_relation_attributes(self) -> None:
        self.assertNotIn("data-ve-from", self.markup)
        self.assertNotIn("data-ve-to", self.markup)
        self.assertNotIn("data-ve-relation", self.markup)
        self.assertNotIn("data-ve-row-id", self.markup)
        self.assertNotIn("data-ve-column-id", self.markup)


class LogicTreeV2Test(unittest.TestCase):
    def test_logic_tree_v2_nests_children_with_elbow_wrappers(self) -> None:
        _, result = render_fixture("component-valid-logic-tree")
        markup = result.markup
        self.assertGreaterEqual(markup.count('class="ve-lt-child"'), 6)
        self.assertIn('class="ve-lt-stub"', markup)
        self.assertNotIn("ve-logic-tree-spine", markup)

    def test_logic_tree_v2_leafless_branch_has_no_nested_children(self) -> None:
        _, result = render_fixture("component-valid-logic-tree")
        markup = result.markup
        branch = re.search(
            r'<div class="ve-lt-child">(?:(?!ve-lt-child).)*?市場機会.*?</div>',
            markup, re.S).group(0)
        self.assertNotIn("ve-lt-children", branch)


if __name__ == "__main__":
    unittest.main()
