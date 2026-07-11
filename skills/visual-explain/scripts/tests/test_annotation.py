import copy
import json
import unittest
from pathlib import Path

from ve_components.diagnostics import ContractError
from ve_components.validation import validate_assembly

FIXTURES = Path(__file__).resolve().parent


def _load(name):
    return json.loads((FIXTURES / name).read_text("utf-8"))


def _ir(raw):
    return raw["sections"][0]["ir"]


class AnnotationValidationTest(unittest.TestCase):
    def setUp(self):
        self.raw = _load("component-valid-flow-annotated.json")

    def _codes(self, raw):
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        return [d.code for d in ctx.exception.diagnostics]

    def test_valid_annotation_accepted(self):
        request = validate_assembly(self.raw)
        ir = request.sections[0].ir
        self.assertEqual(ir.takeaway_target_ids, ("edge-review-approve",))
        self.assertEqual(ir.emphasis[0].target_id, "node-review")

    def test_absent_annotation_fields_accepted(self):
        # 注釈フィールドを一切持たない既存 IR は従来どおり受理される（opt-in 契約）
        legacy = _load("component-valid-flow.json")
        request = validate_assembly(legacy)
        ir = request.sections[0].ir
        self.assertEqual(ir.takeaway_target_ids, ())
        self.assertEqual(ir.emphasis, ())

    def test_unknown_target_rejected(self):
        raw = copy.deepcopy(self.raw)
        _ir(raw)["takeawayTargetIds"] = ["no-such-id"]
        self.assertIn("invalid_component_payload", self._codes(raw))

    def test_zero_targets_require_whole_scope(self):
        raw = copy.deepcopy(self.raw)
        _ir(raw)["takeawayTargetIds"] = []
        del _ir(raw)["emphasis"]
        self.assertIn("invalid_component_payload", self._codes(raw))
        raw2 = copy.deepcopy(raw)
        _ir(raw2)["takeawayScope"] = "whole"
        validate_assembly(raw2)  # 明示すれば通る

    def test_over_three_targets_rejected(self):
        raw = copy.deepcopy(self.raw)
        _ir(raw)["takeawayTargetIds"] = ["node-draft", "node-review", "node-approve", "edge-draft-review"]
        self.assertIn("invalid_component_payload", self._codes(raw))

    def test_duplicate_targets_rejected(self):
        raw = copy.deepcopy(self.raw)
        _ir(raw)["takeawayTargetIds"] = ["node-draft", "node-draft"]
        self.assertIn("invalid_component_payload", self._codes(raw))

    def test_emphasis_label_over_40_chars_rejected(self):
        raw = copy.deepcopy(self.raw)
        _ir(raw)["emphasis"] = [{"targetId": "node-review", "label": "あ" * 41}]
        self.assertIn("invalid_component_payload", self._codes(raw))

    def test_emphasis_label_equal_to_caption_rejected(self):
        raw = copy.deepcopy(self.raw)
        _ir(raw)["emphasis"] = [{"targetId": "node-review", "label": _ir(raw)["caption"]}]
        self.assertIn("invalid_component_payload", self._codes(raw))

    def test_matrix_targets_must_be_cells(self):
        raw = _load("component-valid-mixed.json")
        for section in raw["sections"]:
            if section.get("kind") == "canonical" and "matrix" in section["ir"]:
                # 行 ID（セルではない）を指すと拒否される
                row_id = section["ir"]["matrix"]["rows"][0]["id"]
                section["ir"]["takeawayTargetIds"] = [row_id]
                break
        self.assertIn("invalid_component_payload", self._codes(raw))


if __name__ == "__main__":
    unittest.main()
