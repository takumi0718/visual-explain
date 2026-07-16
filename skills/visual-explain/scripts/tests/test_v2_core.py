"""S1 core tests: cross-cutting generalization and enumeration validation."""
from __future__ import annotations

from fixture_util import canonical_ir, canonical_section
import copy
import json
import unittest
from pathlib import Path

from ve_components.diagnostics import ContractError
from ve_components.model import CERTAINTY_LABEL
from ve_components.validation import validate_assembly, validate_canonical_section

FIXTURES = Path(__file__).resolve().parent


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text("utf-8"))


def _ir(raw: dict) -> dict:
    return canonical_ir(raw)


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
        ir = next(s for s in request.sections if hasattr(s, "ir")).ir
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


class PayloadDispatchRegistryTest(unittest.TestCase):
    """Regression: dispatch tables route payloads; no implicit enumeration fallback."""

    def test_payload_validators_dispatch_registered_component(self) -> None:
        import ve_components.validation as v
        from ve_components.diagnostics import DiagnosticCollector

        enum_calls: list[str] = []
        stub_calls: list[str] = []
        real_enum = v._PAYLOAD_VALIDATORS["enumeration"]

        def tracking_enumeration(raw, path, col):
            enum_calls.append(path)
            return real_enum(raw, path, col)

        def stub_validator(raw, path, col):
            stub_calls.append(path)
            return object()

        raw = copy.deepcopy(_load("component-valid-enumeration.json"))
        ir_raw = _ir(raw)
        ir_raw.pop("enumeration")
        ir_raw["__stub__"] = {"marker": True}

        original_validators = dict(v._PAYLOAD_VALIDATORS)
        original_keys = v._PAYLOAD_KEYS
        try:
            v._PAYLOAD_VALIDATORS["__stub__"] = stub_validator
            v._PAYLOAD_VALIDATORS["enumeration"] = tracking_enumeration
            v._PAYLOAD_KEYS = frozenset({*original_keys, "__stub__"})
            col = DiagnosticCollector()
            v._validate_canonical_ir(ir_raw, "ir", col)
            self.assertEqual(stub_calls, ["ir.__stub__"])
            self.assertEqual(enum_calls, [])
        finally:
            v._PAYLOAD_VALIDATORS.clear()
            v._PAYLOAD_VALIDATORS.update(original_validators)
            v._PAYLOAD_KEYS = original_keys

    def test_annotation_targets_dispatch_registered_component(self) -> None:
        import ve_components.validation as v
        from ve_components.diagnostics import DiagnosticCollector

        raw = copy.deepcopy(_load("component-valid-enumeration.json"))
        ir_raw = _ir(raw)
        ir_raw.pop("enumeration")
        ir_raw["__stub__"] = {"marker": True}
        ir_raw["takeawayTargetIds"] = ["stub-target"]

        original_validators = dict(v._PAYLOAD_VALIDATORS)
        original_targets = dict(v.ANNOTATION_TARGETS)
        original_keys = v._PAYLOAD_KEYS
        try:
            v._PAYLOAD_VALIDATORS["__stub__"] = lambda raw, path, col: object()
            v.ANNOTATION_TARGETS["__stub__"] = lambda _payload: {"stub-target"}
            v.ANNOTATION_TARGETS["enumeration"] = lambda _payload: {"wrong-target"}
            v._PAYLOAD_KEYS = frozenset({*original_keys, "__stub__"})
            col = DiagnosticCollector()
            targets, scope, _emphasis = v._validate_annotations(
                ir_raw, "ir", col, ir_raw["caption"], "__stub__", object(),
            )
            self.assertEqual(targets, ("stub-target",))
            self.assertFalse(col)
        finally:
            v._PAYLOAD_VALIDATORS.clear()
            v._PAYLOAD_VALIDATORS.update(original_validators)
            v.ANNOTATION_TARGETS.clear()
            v.ANNOTATION_TARGETS.update(original_targets)
            v._PAYLOAD_KEYS = original_keys

    def test_unregistered_payload_kind_is_rejected(self) -> None:
        import ve_components.validation as v
        from ve_components.diagnostics import DiagnosticCollector

        raw = copy.deepcopy(_load("component-valid-enumeration.json"))
        ir_raw = _ir(raw)
        ir_raw.pop("enumeration")
        ir_raw["__orphan__"] = {"marker": True}

        original_keys = v._PAYLOAD_KEYS
        try:
            v._PAYLOAD_KEYS = frozenset({*original_keys, "__orphan__"})
            col = DiagnosticCollector()
            v._validate_canonical_ir(ir_raw, "ir", col)
            codes = [d.code for d in col.diagnostics]
            self.assertIn("invalid_component_payload", codes)
        finally:
            v._PAYLOAD_KEYS = original_keys


class CertaintyVocabularyTest(unittest.TestCase):
    def test_certainty_label_uses_design_system_vocabulary(self) -> None:
        self.assertEqual(CERTAINTY_LABEL, {
            "confirmed": "確認済み", "inferred": "推論", "unverified": "未確認",
        })

    def test_no_renderer_defines_local_cert_label(self) -> None:
        import pathlib
        for path in pathlib.Path("ve_components/renderers").glob("*.py"):
            if path.name == "__init__.py":
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn('"confirmed": "確定"', text, path.name)

    def test_schema_allows_contract_version_two(self) -> None:
        schema = json.loads((FIXTURES.parent.parent / "references" / "component-ir.schema.json").read_text())
        self.assertEqual(schema["$defs"]["contractVersion"]["enum"], [2])


if __name__ == "__main__":
    unittest.main()
