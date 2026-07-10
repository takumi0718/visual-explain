"""Task 5 tests: the matrix component as a complete, static, accessible unit."""
from __future__ import annotations

import copy
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from ve_components.registry import load_registry
from ve_components.renderers.matrix import render_matrix
from ve_components.validation import validate_canonical_section
from ve_components.model import CanonicalSection

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"
MATRIX_DEF = REGISTRY.find("matrix", 1)


def render_fixture(name: str = "component-valid-matrix.json"):
    raw = json.loads((TESTS / name).read_text("utf-8"))
    ir = validate_canonical_section(raw["sections"][0]["ir"])
    return ir, render_matrix(CanonicalSection(ir=ir), MATRIX_DEF)


class MatrixManifestTest(unittest.TestCase):
    def test_registry_entry_is_complete(self) -> None:
        self.assertIsNotNone(MATRIX_DEF)
        self.assertEqual(MATRIX_DEF.relationship_kind, "two-axis")
        self.assertEqual(MATRIX_DEF.capabilities, ("two-axis-classification", "intersection-comparison"))
        self.assertEqual(MATRIX_DEF.renderer, "matrix@1")
        self.assertEqual([a.id for a in MATRIX_DEF.assets], ["matrix.css"])

    def test_manifest_consumes_all_semantic_ids(self) -> None:
        ir, result = render_fixture()
        expected = set(ir.semantic_ids())
        self.assertEqual(set(result.manifest.consumed_semantic_ids), expected)

    def test_declares_css_and_no_script(self) -> None:
        _, result = render_fixture()
        self.assertEqual(result.style_asset_ids, ("matrix.css",))
        self.assertEqual(result.script_asset_ids, ())
        self.assertEqual(result.manifest.generated_relationship_ids, ())


class MatrixMarkupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ir, self.result = render_fixture()
        self.markup = self.result.markup

    def test_semantic_figure_with_visible_caption_and_summary(self) -> None:
        self.assertIn("<figure data-ve-component=\"matrix\"", self.markup)
        self.assertIn(self.ir.caption, self.markup)
        self.assertIn(self.ir.accessibility.summary, self.markup)
        self.assertIn("<table>", self.markup)

    def test_headers_have_semantic_ids(self) -> None:
        for row in self.ir.matrix.rows:
            self.assertIn(f'scope="row" data-ve-semantic-id="{row.id}"', self.markup)
        for col in self.ir.matrix.columns:
            self.assertIn(f'scope="col" data-ve-semantic-id="{col.id}"', self.markup)

    def test_cells_carry_row_and_column_ids(self) -> None:
        for cell in self.ir.matrix.cells:
            self.assertIn(f'data-ve-semantic-id="{cell.id}"', self.markup)
            self.assertIn(f'data-ve-row-id="{cell.row_id}"', self.markup)
            self.assertIn(f'data-ve-column-id="{cell.column_id}"', self.markup)

    def test_visible_certainty_and_source_references(self) -> None:
        self.assertIn("ve-cert", self.markup)
        self.assertIn("権限仕様 v3", self.markup)  # source label rendered

    def test_deterministic_dom_order(self) -> None:
        self.assertLess(self.markup.index("row-admin"), self.markup.index("row-viewer"))
        self.assertLess(self.markup.index("col-read"), self.markup.index("col-write"))

    def test_authored_text_is_escaped(self) -> None:
        raw = json.loads((TESTS / "component-valid-matrix.json").read_text("utf-8"))
        raw["sections"][0]["ir"]["matrix"]["cells"][0]["content"] = "a<b>&\"x\""
        ir = validate_canonical_section(raw["sections"][0]["ir"])
        markup = render_matrix(CanonicalSection(ir=ir), MATRIX_DEF).markup
        self.assertNotIn("a<b>", markup)
        self.assertIn("a&lt;b&gt;", markup)

    def test_no_scripts_or_handlers_or_external(self) -> None:
        self.assertNotIn("<script", self.markup)
        self.assertFalse(re.search(r"\son[a-z]+=", self.markup))
        self.assertNotIn("style=", self.markup)
        self.assertNotIn("http://", self.markup)
        self.assertNotIn("https://", self.markup)

    def test_css_namespaced_and_scrollable(self) -> None:
        css = (SKILL / "assets" / "components" / "matrix.css").read_text("utf-8")
        for line in css.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("/*"):
                self.assertTrue(stripped.startswith('[data-ve-component="matrix"]'),
                                f"non-namespaced CSS rule: {stripped}")
        self.assertIn("overflow-x: auto", css)


class MatrixBuildTest(unittest.TestCase):
    def test_build_and_check_matrix_fixture(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as handle:
            out = Path(handle.name)
        try:
            build = subprocess.run(
                ["python3", str(SKILL / "scripts" / "build_explainer.py"),
                 "--assembly", str(TESTS / "component-valid-matrix.json"), "--output", str(out)],
                capture_output=True, text=True,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            check = subprocess.run(
                ["bash", str(SKILL / "scripts" / "check.sh"), str(out)],
                capture_output=True, text=True,
            )
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        finally:
            out.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
