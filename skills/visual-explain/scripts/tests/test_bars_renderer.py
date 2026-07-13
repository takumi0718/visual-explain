"""S7 tests: bars validation, width classes, and renderer DOM contract."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from ve_components.diagnostics import ContractError
from ve_components.model import CanonicalSection
from ve_components.registry import load_registry
from ve_components.validation import validate_canonical_section

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"
BARS_DEF = REGISTRY.find("bars", 2)


def _fixture_path(name: str) -> Path:
    return TESTS / name if name.endswith(".json") else TESTS / f"{name}.json"


def expect_violation(test_case: unittest.TestCase, fixture_name: str, code: str) -> None:
    raw = json.loads(_fixture_path(fixture_name).read_text("utf-8"))
    with test_case.assertRaises(ContractError) as ctx:
        validate_canonical_section(raw["sections"][0]["ir"])
    codes = {d.code for d in ctx.exception.diagnostics}
    test_case.assertIn(code, codes)


def render_fixture(name: str = "component-valid-bars"):
    from ve_components.renderers.bars import render_bars

    raw = json.loads(_fixture_path(name).read_text("utf-8"))
    ir = validate_canonical_section(raw["sections"][0]["ir"])
    return render_bars(CanonicalSection(ir=ir), BARS_DEF)


class BarsMarkupTest(unittest.TestCase):
    def test_bars_renders_rows_with_integer_width_class(self) -> None:
        markup = render_fixture("component-valid-bars").markup
        self.assertIn("ve-bars-w-100", markup)
        self.assertIn("ve-bars-w-17", markup)
        self.assertEqual(markup.count("ve-dg-highlight"), 1)

    def test_bars_rejects_more_than_ten_items(self) -> None:
        expect_violation(self, "component-bad-bars-eleven-items", "bars-item-limit")


if __name__ == "__main__":
    unittest.main()
