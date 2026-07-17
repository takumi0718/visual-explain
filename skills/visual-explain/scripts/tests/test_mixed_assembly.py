"""Task 4 tests: one mixed composition/flattening route with compatibility bypass."""
from __future__ import annotations

from fixture_util import canonical_ir, canonical_section, compatibility_section
import copy
import hashlib
import html
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import ve_components.assembly as assembly
from ve_components.assembly import compose_sections, process_compatibility_section
from ve_components.diagnostics import ContractError
from ve_components.model import RenderManifest, RenderResult
from ve_components.registry import Registry, load_registry
from ve_components.renderers.flow import render_flow
from ve_components.renderers.matrix import render_matrix
from ve_components.validation import validate_assembly
from build_explainer import build_document

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
TESTS = SKILL / "scripts" / "tests"
PROD_REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")


def esc(value: str) -> str:
    return html.escape(str(value))


# The mixed-assembly tests use the real production renderers against an isolated
# temp registry/asset dir. This exercises the full trust boundary (renderer
# markup verified against the source IR), which a generic double cannot.
REAL_RENDERERS = {"matrix@2": render_matrix, "flow@2": render_flow}


class MixedAssemblyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="ve-mixed-"))
        cls.matrix_css = "[data-ve-component=\"matrix\"]{color:inherit}\n"
        cls.flow_css = "[data-ve-component=\"flow\"]{color:inherit}\n"
        (cls.tmp / "matrix.css").write_text(cls.matrix_css, "utf-8")
        (cls.tmp / "flow.css").write_text(cls.flow_css, "utf-8")
        cls.matrix_digest = hashlib.sha256(cls.matrix_css.encode()).hexdigest()
        cls.flow_digest = hashlib.sha256(cls.flow_css.encode()).hexdigest()
        registry_dict = {
            "registryVersion": 1,
            "components": [
                cls._entry("matrix", "two-axis", ["two-axis-classification", "intersection-comparison"], "matrix.css", cls.matrix_digest, version=2),
                cls._entry("flow", "directed-graph", ["ordered-transition", "directed-transition", "branching"], "flow.css", cls.flow_digest, version=2),
            ],
        }
        cls.registry = load_registry(registry_dict)
        cls.renderers = REAL_RENDERERS

    @staticmethod
    def _entry(cid, kind, caps, asset, digest, version=1):
        return {
            "id": cid, "version": version, "relationshipKind": kind, "capabilities": caps,
            "semanticResponsibility": f"{cid} responsibility", "requiredInputs": ["caption"],
            "optionalInputs": [], "behavior": "static", "slots": ["caption", "certainty", "source", "accessibility"],
            "accessibility": "labelled figure", "responsive": True, "dependencies": [],
            "fallback": "static-content", "checkerRules": ["static-content", "semantic-ids"],
            "renderer": f"{cid}@{version}", "assets": [{"id": asset, "slot": "styles", "path": asset, "digest": digest}],
        }

    def build(self, name: str) -> str:
        raw = json.loads((TESTS / name).read_text("utf-8"))
        return build_document(raw, self.registry, self.renderers, SKELETON, self.tmp, document_path="doc.html")

    def test_mixed_order_and_single_markers(self) -> None:
        doc = self.build("component-valid-mixed.json")
        i_matrix = doc.index("sec-mixed-matrix")
        i_compat = doc.index("sec-mixed-legacy")
        i_flow = doc.index("sec-mixed-flow")
        self.assertTrue(i_matrix < i_compat < i_flow)
        for marker in ("VE-CONTROLLED:CONTENT:BEGIN", "VE-CONTROLLED:COMPONENT-STYLES:BEGIN", "VE-CONTROLLED:COMPONENT-SCRIPTS:BEGIN"):
            self.assertEqual(doc.count(marker), 1)

    def test_compatibility_wrapper_provenance(self) -> None:
        doc = self.build("component-valid-mixed.json")
        self.assertIn('data-ve-section-kind="compatibility"', doc)
        self.assertIn('data-ve-compat-source="legacy-html-insertion"', doc)
        self.assertIn('data-ve-compat-reason="unmigrated-format"', doc)

    def test_canonical_instance_provenance(self) -> None:
        doc = self.build("component-valid-mixed.json")
        self.assertIn('data-ve-component="matrix"', doc)
        self.assertIn('data-ve-instance="sec-mixed-matrix"', doc)
        self.assertIn('data-ve-instance="sec-mixed-flow"', doc)

    def test_styles_deduplicated_one_per_component(self) -> None:
        doc = self.build("component-valid-mixed.json")
        self.assertEqual(doc.count('data-ve-asset="matrix.css"'), 1)
        self.assertEqual(doc.count('data-ve-asset="flow.css"'), 1)
        self.assertEqual(doc.count("<script data-ve"), 0)

    def test_weak_model_builds_with_production_registry(self) -> None:
        raw = json.loads((TESTS / "component-valid-weak-model.json").read_text("utf-8"))
        doc = build_document(raw, PROD_REGISTRY, {}, SKELETON, SKILL / "assets" / "components", document_path="doc.html")
        self.assertIn('data-ve-compat-source="legacy-html-insertion"', doc)
        self.assertIn('data-ve-compat-reason="weak-model-degradation"', doc)
        # Compatibility markup lands only in the content slot, never in styles/scripts.
        styles_body = doc.split("VE-CONTROLLED:COMPONENT-STYLES:BEGIN")[1].split("VE-CONTROLLED:COMPONENT-STYLES:END")[0]
        self.assertNotIn("matrix-cell", styles_body)


class CompatibilityBypassTest(unittest.TestCase):
    def test_compatibility_never_calls_canonical_functions(self) -> None:
        raw = json.loads((TESTS / "component-valid-weak-model.json").read_text("utf-8"))
        with mock.patch.object(assembly, "narrow_candidates") as narrow, \
             mock.patch.object(assembly, "resolve_component") as resolve, \
             mock.patch.object(assembly, "validate_canonical_section") as vcs, \
             mock.patch.object(assembly, "render_canonical") as render, \
             mock.patch.object(assembly, "validate_content_markup", wraps=assembly.validate_content_markup) as vcm:
            build_document(raw, PROD_REGISTRY, {}, SKELETON, SKILL / "assets" / "components", document_path="doc.html")
            narrow.assert_not_called()
            resolve.assert_not_called()
            vcs.assert_not_called()
            render.assert_not_called()
            vcm.assert_called()

    def test_compatibility_wrapper_has_section_kind(self) -> None:
        request = validate_assembly(json.loads((TESTS / "component-valid-weak-model.json").read_text("utf-8")))
        wrapped = process_compatibility_section(next(s for s in request.sections if hasattr(s, "provenance") and s.provenance is not None))
        self.assertIn('data-ve-section-kind="compatibility"', wrapped.markup)


class FailureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.mixed = MixedAssemblyTest
        MixedAssemblyTest.setUpClass()

    def build(self, raw) -> str:
        return build_document(raw, MixedAssemblyTest.registry, MixedAssemblyTest.renderers, SKELETON, MixedAssemblyTest.tmp, document_path="doc.html")

    def test_false_provenance_rejected(self) -> None:
        raw = json.loads((TESTS / "component-valid-weak-model.json").read_text("utf-8"))
        del compatibility_section(raw)["provenance"]
        with self.assertRaises(ContractError):
            self.build(raw)

    def test_compat_css_injection_fails_no_output(self) -> None:
        raw = json.loads((TESTS / "component-bad-weak-model-style.json").read_text("utf-8"))
        with self.assertRaises(ContractError):
            self.build(raw)

    def test_compat_js_injection_fails_no_output(self) -> None:
        raw = json.loads((TESTS / "component-bad-weak-model-script.json").read_text("utf-8"))
        with self.assertRaises(ContractError):
            self.build(raw)

    def test_canonical_failure_no_silent_fallback(self) -> None:
        raw = json.loads((TESTS / "component-valid-matrix.json").read_text("utf-8"))
        canonical_ir(raw)["selection"]["component"] = "flow"  # mismatch → invalid before matching
        with self.assertRaises(ContractError):
            self.build(raw)

    def test_duplicate_section_ids_fail(self) -> None:
        raw = json.loads((TESTS / "component-valid-mixed.json").read_text("utf-8"))
        # Force two canonical sections to share the matrix instance id.
        canonicals = [s for s in raw["sections"] if s.get("kind") == "canonical"]
        self.assertGreaterEqual(len(canonicals), 2)
        canonicals[1]["ir"]["id"] = canonicals[0]["ir"]["id"]
        with self.assertRaises(ContractError):
            self.build(raw)

    def test_registry_lookup_failure(self) -> None:
        raw = json.loads((TESTS / "component-valid-matrix.json").read_text("utf-8"))
        # An empty registry yields no candidates → no_matching_component, no output.
        with self.assertRaises(ContractError):
            build_document(raw, Registry(registry_version=1, components=()), MixedAssemblyTest.renderers, SKELETON, MixedAssemblyTest.tmp, document_path="doc.html")


class MatrixAnnotationRenderTest(unittest.TestCase):
    def setUp(self) -> None:
        MixedAssemblyTest.setUpClass()

    def _build_with_annotation(self):
        raw = json.loads((TESTS / "component-valid-mixed.json").read_text("utf-8"))
        for section in raw["sections"]:
            if section.get("kind") == "canonical" and "matrix" in section["ir"]:
                cell_id = section["ir"]["matrix"]["cells"][0]["id"]
                section["ir"]["takeawayTargetIds"] = [cell_id]
                section["ir"]["emphasis"] = [{"targetId": cell_id, "label": "判断の分岐点"}]
                doc = build_document(raw, MixedAssemblyTest.registry, MixedAssemblyTest.renderers, SKELETON, MixedAssemblyTest.tmp, document_path="doc.html")
                return doc, cell_id
        raise AssertionError("matrix section not found")

    def test_takeaway_target_marked(self) -> None:
        doc, cell_id = self._build_with_annotation()
        self.assertIn(f'data-ve-semantic-id="{esc(cell_id)}" data-ve-row-id=', doc)
        self.assertIn('data-ve-takeaway="true"', doc)
        self.assertIn('class="ve-takeaway-target"', doc)

    def test_emphasis_label_rendered_and_in_summary(self) -> None:
        doc, _ = self._build_with_annotation()
        self.assertIn('<span class="ve-emphasis">判断の分岐点</span>', doc)
        self.assertIn("注釈: 判断の分岐点", doc)


class RendererTrustBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        MixedAssemblyTest.setUpClass()
        cls.registry = MixedAssemblyTest.registry
        cls.tmp = MixedAssemblyTest.tmp
        cls.digest = MixedAssemblyTest.matrix_digest

    def _build_matrix(self, renderer) -> str:
        raw = json.loads((TESTS / "component-valid-matrix.json").read_text("utf-8"))
        return build_document(raw, self.registry, {"matrix@2": renderer}, SKELETON, self.tmp, document_path="doc.html")

    def _build_flow(self, renderer) -> str:
        raw = json.loads((TESTS / "component-valid-flow.json").read_text("utf-8"))
        return build_document(raw, self.registry, {"flow@2": renderer}, SKELETON, self.tmp, document_path="doc.html")

    @staticmethod
    def _mutate_matrix(**changes):
        import dataclasses
        def renderer(section, component):
            base = render_matrix(section, component)
            manifest_changes = changes.pop("_manifest", None)
            result = dataclasses.replace(base, **changes)
            if manifest_changes is not None:
                result = dataclasses.replace(result, manifest=dataclasses.replace(base.manifest, **manifest_changes))
            return result
        return renderer

    def test_renderer_diagnostics_fail_build(self) -> None:
        from ve_components.diagnostics import Diagnostic
        with self.assertRaises(ContractError):
            self._build_matrix(self._mutate_matrix(diagnostics=(Diagnostic("renderer_failure", "報告"),)))

    def test_undeclared_style_asset_fails_build(self) -> None:
        with self.assertRaises(ContractError):
            self._build_matrix(self._mutate_matrix(style_asset_ids=("ghost.css",)))

    def test_manifest_component_mismatch_fails_build(self) -> None:
        with self.assertRaises(ContractError):
            self._build_matrix(self._mutate_matrix(_manifest={"component_id": "flow"}))

    def test_manifest_asset_ids_disagree_with_declared_fails(self) -> None:
        with self.assertRaises(ContractError):
            self._build_matrix(self._mutate_matrix(_manifest={"asset_ids": ("matrix.css", "phantom.css")}))

    def test_asset_ids_digests_length_mismatch_fails(self) -> None:
        with self.assertRaises(ContractError):
            self._build_matrix(self._mutate_matrix(_manifest={"asset_digests": ()}))

    def test_manifest_drops_semantic_id_fails(self) -> None:
        def renderer(section, component):
            import dataclasses
            base = render_matrix(section, component)
            dropped = base.manifest.consumed_semantic_ids[:-1]
            return dataclasses.replace(base, manifest=dataclasses.replace(base.manifest, consumed_semantic_ids=dropped))
        with self.assertRaises(ContractError):
            self._build_matrix(renderer)

    def test_flow_manifest_drops_relationship_id_fails(self) -> None:
        def renderer(section, component):
            import dataclasses
            base = render_flow(section, component)
            return dataclasses.replace(base, manifest=dataclasses.replace(base.manifest, generated_relationship_ids=()))
        with self.assertRaises(ContractError):
            self._build_flow(renderer)

    def test_flow_renderer_reversed_edge_fails_build(self) -> None:
        def renderer(section, component):
            base = render_flow(section, component)
            import dataclasses
            reversed_markup = base.markup.replace(
                'data-ve-from="node-draft" data-ve-to="node-review"',
                'data-ve-from="node-review" data-ve-to="node-draft"')
            return dataclasses.replace(base, markup=reversed_markup)
        with self.assertRaises(ContractError):
            self._build_flow(renderer)


if __name__ == "__main__":
    unittest.main()
