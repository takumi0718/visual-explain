"""Task 1 contract tests: vocabulary, strict IR validation, bounded diagnostics.

The canonical authoring format carries no HTML/CSS/JavaScript/coordinate. Every
rejection maps to one of the bounded diagnostic codes owned by this task.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ve_components.diagnostics import ContractError
from ve_components.validation import validate_assembly, validate_canonical_section

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REFERENCES = SKILL / "references"
TESTS = SKILL / "scripts" / "tests"

VOCABULARY = json.loads((REFERENCES / "component-vocabulary.json").read_text("utf-8"))
IR_SCHEMA = json.loads((REFERENCES / "component-ir.schema.json").read_text("utf-8"))
ASSEMBLY_SCHEMA = json.loads((REFERENCES / "assembly.schema.json").read_text("utf-8"))


def load(name: str) -> dict:
    return json.loads((TESTS / name).read_text("utf-8"))


def codes(error: ContractError) -> set[str]:
    return {d.code for d in error.diagnostics}


class VocabularyFixtureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = load("component-valid-matrix.json")
        self.flow = load("component-valid-flow.json")

    def test_matrix_fixture_uses_authoritative_vocabulary(self) -> None:
        request = validate_assembly(self.matrix)
        section = request.sections[0]
        self.assertEqual(section.ir.selection.component, "matrix")
        self.assertEqual(section.ir.selection.version, 1)
        self.assertEqual(section.ir.relationship.kind, "two-axis")
        allowed = set(VOCABULARY["components"]["matrix"]["capabilities"])
        self.assertTrue(set(section.ir.selection.matched_capabilities) <= allowed)
        self.assertTrue(set(section.ir.relationship.capabilities) <= allowed)
        self.assertTrue(section.ir.selection.matched_capabilities)

    def test_flow_fixture_uses_authoritative_vocabulary(self) -> None:
        request = validate_assembly(self.flow)
        section = request.sections[0]
        self.assertEqual(section.ir.selection.component, "flow")
        self.assertEqual(section.ir.selection.version, 1)
        self.assertEqual(section.ir.relationship.kind, "directed-graph")
        allowed = set(VOCABULARY["components"]["flow"]["capabilities"])
        self.assertTrue(set(section.ir.selection.matched_capabilities) <= allowed)
        self.assertTrue(set(section.ir.relationship.capabilities) <= allowed)

    def test_validate_canonical_section_accepts_matrix_ir(self) -> None:
        ir = validate_canonical_section(self.matrix["sections"][0]["ir"])
        self.assertEqual(ir.selection.component, "matrix")
        self.assertEqual([r.id for r in ir.matrix.rows], ["row-admin", "row-viewer"])
        self.assertEqual(len(ir.matrix.cells), 4)


class SchemaVocabularyConsistencyTest(unittest.TestCase):
    """Vocabulary, schema, and fixtures cannot drift."""

    def test_component_ids_match(self) -> None:
        self.assertEqual(
            set(IR_SCHEMA["$defs"]["componentId"]["enum"]),
            set(VOCABULARY["components"].keys()),
        )

    def test_relationship_kinds_match(self) -> None:
        kinds = {c["relationshipKind"] for c in VOCABULARY["components"].values()}
        self.assertEqual(set(IR_SCHEMA["$defs"]["relationshipKind"]["enum"]), kinds)

    def test_capabilities_match(self) -> None:
        caps: set[str] = set()
        for component in VOCABULARY["components"].values():
            caps.update(component["capabilities"])
        self.assertEqual(set(IR_SCHEMA["$defs"]["capability"]["enum"]), caps)

    def test_contract_versions_match(self) -> None:
        versions = {c["contractVersion"] for c in VOCABULARY["components"].values()}
        self.assertEqual(set(IR_SCHEMA["$defs"]["contractVersion"]["enum"]), versions)

    def test_compatibility_provenance_matches(self) -> None:
        self.assertEqual(
            set(ASSEMBLY_SCHEMA["$defs"]["compatibilitySource"]["enum"]),
            set(VOCABULARY["compatibility"]["sources"]),
        )
        self.assertEqual(
            set(ASSEMBLY_SCHEMA["$defs"]["compatibilityReason"]["enum"]),
            set(VOCABULARY["compatibility"]["reasons"]),
        )


class CanonicalRejectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = load("component-valid-matrix.json")["sections"][0]["ir"]
        self.flow_ir = load("component-valid-flow.json")["sections"][0]["ir"]

    def reject(self, ir: dict) -> ContractError:
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(ir)
        return ctx.exception

    def test_unknown_relationship_kind(self) -> None:
        ir = copy.deepcopy(self.ir)
        ir["relationship"]["kind"] = "three-axis"
        self.assertIn("invalid_relationship_declaration", codes(self.reject(ir)))

    def test_unknown_capability(self) -> None:
        ir = copy.deepcopy(self.ir)
        ir["relationship"]["capabilities"] = ["mind-reading"]
        self.assertIn("invalid_relationship_declaration", codes(self.reject(ir)))

    def test_under_specified_relationship(self) -> None:
        ir = copy.deepcopy(self.ir)
        ir["relationship"]["capabilities"] = []
        self.assertIn("invalid_relationship_declaration", codes(self.reject(ir)))

    def test_unknown_component_id(self) -> None:
        ir = copy.deepcopy(self.ir)
        ir["selection"]["component"] = "sankey"
        self.assertIn("invalid_component_payload", codes(self.reject(ir)))

    def test_boolean_is_not_version(self) -> None:
        ir = copy.deepcopy(self.ir)
        ir["selection"]["version"] = True
        self.assertIn("invalid_component_payload", codes(self.reject(ir)))

    def test_both_payloads_present(self) -> None:
        ir = copy.deepcopy(self.ir)
        ir["flow"] = load("component-valid-flow.json")["sections"][0]["ir"]["flow"]
        self.assertIn("invalid_component_payload", codes(self.reject(ir)))

    def test_unknown_field(self) -> None:
        ir = copy.deepcopy(self.ir)
        ir["theme"] = "dark"
        self.assertIn("invalid_component_payload", codes(self.reject(ir)))

    def test_missing_caption(self) -> None:
        ir = copy.deepcopy(self.ir)
        del ir["caption"]
        self.assertIn("missing_required_slot", codes(self.reject(ir)))

    def test_missing_certainty(self) -> None:
        ir = copy.deepcopy(self.ir)
        del ir["certainty"]
        self.assertIn("missing_required_slot", codes(self.reject(ir)))

    def test_missing_source(self) -> None:
        ir = copy.deepcopy(self.ir)
        del ir["sources"]
        self.assertIn("missing_required_slot", codes(self.reject(ir)))

    def test_missing_accessibility_summary(self) -> None:
        ir = copy.deepcopy(self.ir)
        del ir["accessibility"]["summary"]
        self.assertIn("missing_required_slot", codes(self.reject(ir)))

    def test_forbidden_html_field(self) -> None:
        ir = copy.deepcopy(self.ir)
        ir["matrix"]["cells"][0]["html"] = "<b>x</b>"
        self.assertIn("forbidden_authoring_field", codes(self.reject(ir)))

    def test_forbidden_style_field(self) -> None:
        ir = copy.deepcopy(self.ir)
        ir["style"] = "color:red"
        self.assertIn("forbidden_authoring_field", codes(self.reject(ir)))

    def test_forbidden_coordinate_field(self) -> None:
        ir = copy.deepcopy(self.flow_ir)
        ir["flow"]["nodes"][0]["x"] = 10
        self.assertIn("forbidden_authoring_field", codes(self.reject(ir)))

    def test_forbidden_script_field(self) -> None:
        ir = copy.deepcopy(self.ir)
        ir["script"] = "alert(1)"
        self.assertIn("forbidden_authoring_field", codes(self.reject(ir)))

    def test_duplicate_semantic_id(self) -> None:
        ir = copy.deepcopy(self.ir)
        ir["matrix"]["rows"][1]["id"] = "row-admin"
        self.assertIn("duplicate_semantic_id", codes(self.reject(ir)))

    def test_bad_matrix_row_reference(self) -> None:
        ir = copy.deepcopy(self.ir)
        ir["matrix"]["cells"][0]["rowId"] = "row-missing"
        self.assertIn("invalid_matrix_reference", codes(self.reject(ir)))

    def test_bad_matrix_column_reference(self) -> None:
        ir = copy.deepcopy(self.ir)
        ir["matrix"]["cells"][0]["columnId"] = "col-missing"
        self.assertIn("invalid_matrix_reference", codes(self.reject(ir)))

    def test_duplicate_matrix_intersection(self) -> None:
        ir = copy.deepcopy(self.ir)
        ir["matrix"]["cells"][1]["rowId"] = "row-admin"
        ir["matrix"]["cells"][1]["columnId"] = "col-read"
        self.assertIn("invalid_matrix_reference", codes(self.reject(ir)))

    def test_flow_edge_missing_from(self) -> None:
        ir = copy.deepcopy(self.flow_ir)
        del ir["flow"]["edges"][0]["from"]
        self.assertIn("invalid_flow_edge", codes(self.reject(ir)))

    def test_flow_edge_missing_relation(self) -> None:
        ir = copy.deepcopy(self.flow_ir)
        del ir["flow"]["edges"][0]["relation"]
        self.assertIn("invalid_flow_edge", codes(self.reject(ir)))

    def test_flow_edge_dangling_target(self) -> None:
        ir = copy.deepcopy(self.flow_ir)
        ir["flow"]["edges"][0]["to"] = "node-missing"
        self.assertIn("invalid_flow_edge", codes(self.reject(ir)))


class CompatibilityProvenanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.request = load("component-valid-matrix.json")

    def compat(self, **provenance) -> dict:
        req = copy.deepcopy(self.request)
        req["sections"].append({
            "kind": "compatibility",
            "id": "legacy-section",
            "markup": "<section>既存ルールの内容</section>",
            "provenance": provenance,
        })
        return req

    def test_accepts_known_provenance(self) -> None:
        req = self.compat(source="legacy-html-insertion", reason="unmigrated-format", format="layers")
        result = validate_assembly(req)
        self.assertEqual(result.sections[1].provenance.source, "legacy-html-insertion")

    def test_rejects_unknown_source(self) -> None:
        req = self.compat(source="hand-written", reason="unmigrated-format", format="layers")
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(req)
        self.assertIn("invalid_compatibility_provenance", codes(ctx.exception))

    def test_rejects_unknown_reason(self) -> None:
        req = self.compat(source="legacy-html-insertion", reason="just-because", format="layers")
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(req)
        self.assertIn("invalid_compatibility_provenance", codes(ctx.exception))

    def test_rejects_relationship_field_on_compatibility(self) -> None:
        req = copy.deepcopy(self.request)
        req["sections"].append({
            "kind": "compatibility",
            "id": "legacy-section",
            "markup": "<section>x</section>",
            "provenance": {"source": "legacy-html-insertion", "reason": "unmigrated-format", "format": "layers"},
            "relationship": {"kind": "two-axis", "capabilities": ["two-axis-classification"]},
        })
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(req)
        self.assertIn("invalid_compatibility_provenance", codes(ctx.exception))


class DocumentationConsistencyTest(unittest.TestCase):
    """Documented assembly examples validate; only matrix/flow are production;
    documentation introduces no vocabulary aliases."""

    import re as _re

    def _assembly_blocks(self, name: str) -> list[dict]:
        text = (SKILL / "references" / name).read_text("utf-8")
        blocks = self._re.findall(r"```json\n(.*?)\n```", text, self._re.DOTALL)
        return [json.loads(b) for b in blocks if '"schemaVersion"' in b]

    def test_patterns_assembly_examples_validate(self) -> None:
        assemblies = self._assembly_blocks("patterns.md")
        self.assertGreaterEqual(len(assemblies), 3)  # matrix, flow, mixed
        for raw in assemblies:
            validate_assembly(raw)  # raises on any contract violation

    def test_only_matrix_and_flow_in_production_registry(self) -> None:
        from ve_components.registry import load_registry
        registry = load_registry(SKILL / "assets" / "components" / "registry.json")
        self.assertEqual({c.id for c in registry.components}, {"matrix", "flow"})

    def test_documented_tokens_are_in_vocabulary(self) -> None:
        components = VOCABULARY["components"]
        all_caps = {cap for c in components.values() for cap in c["capabilities"]}
        sources = set(VOCABULARY["compatibility"]["sources"])
        reasons = set(VOCABULARY["compatibility"]["reasons"])
        for raw in self._assembly_blocks("patterns.md"):
            request = validate_assembly(raw)
            for section in request.sections:
                ir = getattr(section, "ir", None)
                if ir is not None:
                    self.assertIn(ir.selection.component, components)
                    self.assertEqual(ir.selection.version, components[ir.selection.component]["contractVersion"])
                    self.assertEqual(ir.relationship.kind, components[ir.selection.component]["relationshipKind"])
                    self.assertTrue(set(ir.relationship.capabilities) <= all_caps)
                else:
                    self.assertIn(section.provenance.source, sources)
                    self.assertIn(section.provenance.reason, reasons)


if __name__ == "__main__":
    unittest.main()
