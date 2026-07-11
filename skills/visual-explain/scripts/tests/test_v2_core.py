"""S1 core tests: cross-cutting generalization and enumeration validation."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ve_components.diagnostics import ContractError
from ve_components.validation import validate_assembly, validate_canonical_section

FIXTURES = Path(__file__).resolve().parent


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text("utf-8"))


def _ir(raw: dict) -> dict:
    return raw["sections"][0]["ir"]


class V2CoreValidationTest(unittest.TestCase):
    def _codes(self, raw: dict) -> list[str]:
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        return [d.code for d in ctx.exception.diagnostics]

    def test_flow_edge_relation_scoped(self) -> None:
        raw = _load("component-valid-flow.json")
        _ir(raw)["flow"]["edges"][0]["relation"] = "two-axis-classification"
        self.assertIn("invalid_flow_edge", self._codes(raw))

    def test_payload_dispatch_rejects_multi_payload(self) -> None:
        raw = _load("component-valid-matrix.json")
        enum = _load("component-valid-enumeration.json")
        _ir(raw)["enumeration"] = _ir(enum)["enumeration"]
        self.assertIn("invalid_component_payload", self._codes(raw))

    def test_payload_selection_mismatch(self) -> None:
        raw = _load("component-valid-enumeration.json")
        _ir(raw)["selection"]["component"] = "matrix"
        self.assertIn("invalid_component_payload", self._codes(raw))

    def test_semantic_ids_include_enumeration_items(self) -> None:
        request = validate_assembly(_load("component-valid-enumeration.json"))
        ir = request.sections[0].ir
        item_ids = {item.id for item in ir.enumeration.items}
        self.assertTrue(item_ids)
        self.assertTrue(item_ids <= set(ir.semantic_ids()))

    def test_annotation_targets_enumeration(self) -> None:
        raw = _load("component-valid-enumeration.json")
        _ir(raw)["takeawayTargetIds"] = ["item-a"]
        validate_assembly(raw)
        bad = copy.deepcopy(raw)
        _ir(bad)["takeawayTargetIds"] = ["no-such-item"]
        self.assertIn("invalid_component_payload", self._codes(bad))

    def test_bad_enumeration_fixtures_raise_structure_violation(self) -> None:
        for name in (
            "component-bad-enumeration-gap-description.json",
            "component-bad-enumeration-label-missing.json",
            "component-bad-enumeration-too-many.json",
            "component-bad-enumeration-empty-block.json",
        ):
            with self.subTest(name=name):
                self.assertIn("enumeration_structure_violation", self._codes(_load(name)))


if __name__ == "__main__":
    unittest.main()
