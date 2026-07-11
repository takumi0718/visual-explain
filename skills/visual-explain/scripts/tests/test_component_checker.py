"""Task 7 tests: complete four-layer checker coverage and vertical-slice fixtures."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from ve_components.checker import check_final_document, validate_final_provenance
from ve_components.diagnostics import ContractError
from ve_components.final_checks import check_manifest_to_dom
from ve_components.model import RenderManifest
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from build_explainer import build_document

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS = SKILL / "assets" / "components"
REGISTRY = load_registry(COMPONENTS / "registry.json")
TESTS = SKILL / "scripts" / "tests"
BUILD = SKILL / "scripts" / "build_explainer.py"
CHECK = SKILL / "scripts" / "check.sh"


def build(name: str) -> str:
    raw = json.loads((TESTS / name).read_text("utf-8"))
    return build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS)


class LayerTwoBuildRejectionTest(unittest.TestCase):
    """IR/selection layer: bad assemblies fail the build and publish no output."""

    BAD = [
        "component-bad-selection.json",
        "component-bad-selection-reason.json",
        "component-bad-combined-relationship.json",
        "component-bad-flow-edge.json",
        "component-bad-matrix-cell.json",
    ]

    def test_bad_assemblies_raise(self) -> None:
        for name in self.BAD:
            with self.subTest(name=name):
                with self.assertRaises(ContractError):
                    build(name)

    def test_bad_assemblies_via_cli_write_no_output(self) -> None:
        for name in self.BAD:
            with self.subTest(name=name):
                out = Path(tempfile.gettempdir()) / f"ve-rej-{name}.html"
                out.unlink(missing_ok=True)
                proc = subprocess.run(["python3", str(BUILD), "--assembly", str(TESTS / name), "--output", str(out)],
                                      capture_output=True, text=True)
                self.assertNotEqual(proc.returncode, 0)
                self.assertFalse(out.exists())


class LayerOneAndFourSafetyTest(unittest.TestCase):
    """Safety/fixed-region and flattened-document layers reject bad HTML."""

    def check(self, name: str) -> set[str]:
        raw = (TESTS / name).read_text("utf-8")
        return {d.code for d in check_final_document(raw, SKELETON, REGISTRY, components_dir=COMPONENTS)}

    def test_fixed_region(self) -> None:
        self.assertIn("fixed_region_mismatch", self.check("component-bad-fixed-region.html"))

    def test_content_style(self) -> None:
        self.assertIn("forbidden_content_markup", self.check("component-bad-content-style.html"))

    def test_ask_decision_single_option(self) -> None:
        self.assertIn("ask_contract_violation", self.check("bad-ask-decision.html"))

    def test_asset_hash(self) -> None:
        self.assertIn("invalid_controlled_asset", self.check("component-bad-asset-hash.html"))

    def test_unclosed_script(self) -> None:
        self.assertIn("invalid_controlled_asset", self.check("component-bad-unclosed-script.html"))

    def test_unclosed_style(self) -> None:
        self.assertIn("invalid_controlled_asset", self.check("component-bad-unclosed-style.html"))

    def test_unclosed_script_fails_via_check_sh(self) -> None:
        proc = subprocess.run(["bash", str(CHECK), str(TESTS / "component-bad-unclosed-script.html")],
                              capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)

    def test_unclosed_style_fails_via_check_sh(self) -> None:
        proc = subprocess.run(["bash", str(CHECK), str(TESTS / "component-bad-unclosed-style.html")],
                              capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)

    def test_missing_compatibility_provenance(self) -> None:
        self.assertIn("missing_provenance", self.check("component-bad-compatibility-provenance.html"))

    def test_provenance_scan_accepts_valid_wrappers(self) -> None:
        content = ('<section data-ve-section-kind="canonical" data-ve-component="matrix" data-ve-instance="a"></section>'
                   '<section data-ve-section-kind="compatibility" data-ve-compat-source="legacy-html-insertion"'
                   ' data-ve-compat-reason="unmigrated-format" data-ve-instance="b"></section>')
        self.assertEqual(validate_final_provenance(content), [])


DIGEST_A = "a" * 64


def _manifest(**overrides) -> RenderManifest:
    base = dict(
        component_id="matrix", component_version=1, instance_id="sec-1",
        consumed_semantic_ids=("sec-1", "row-x"), generated_relationship_ids=(),
        generated_landmark_ids=("sec-1-caption",), asset_ids=("matrix.css",),
        asset_digests=(DIGEST_A,), declared_dependencies=(), fallback_mode="static-content")
    base.update(overrides)
    return RenderManifest(**base)


def _expected(manifest):
    class Expected:
        manifests = (manifest,)
        compatibility = ()
    return Expected()


def _good_dom() -> str:
    return ('<section data-ve-section-kind="canonical" data-ve-component="matrix"'
            ' data-ve-contract-version="1" data-ve-instance="sec-1" data-ve-fallback="static-content">'
            '<figcaption id="sec-1-caption">c</figcaption>'
            '<span data-ve-semantic-id="row-x"></span></section>')


def _good_slots() -> dict:
    return {"styles": f'<style data-ve-asset="matrix.css" data-ve-digest="{DIGEST_A}"></style>', "scripts": ""}


class ManifestToDomTest(unittest.TestCase):
    def check(self, content, manifest, slots=None):
        return {d.code for d in check_manifest_to_dom(content, slots or _good_slots(), _expected(manifest))}

    def test_valid_manifest_passes(self) -> None:
        self.assertEqual(check_manifest_to_dom(_good_dom(), _good_slots(), _expected(_manifest())), [])

    def test_missing_semantic_id_is_caught(self) -> None:
        dom = _good_dom().replace('<span data-ve-semantic-id="row-x"></span>', "")
        self.assertIn("manifest_dom_mismatch", self.check(dom, _manifest()))

    def test_missing_landmark_is_caught(self) -> None:
        dom = _good_dom().replace('id="sec-1-caption"', 'id="other"')
        self.assertIn("manifest_dom_mismatch", self.check(dom, _manifest()))

    def test_component_mismatch_is_caught(self) -> None:
        self.assertIn("manifest_dom_mismatch", self.check(_good_dom(), _manifest(component_id="flow")))

    def test_version_mismatch_is_caught(self) -> None:
        self.assertIn("manifest_dom_mismatch", self.check(_good_dom(), _manifest(component_version=2)))

    def test_fallback_mismatch_is_caught(self) -> None:
        self.assertIn("manifest_dom_mismatch", self.check(_good_dom(), _manifest(fallback_mode="degrade")))

    def test_missing_asset_digest_is_caught(self) -> None:
        slots = {"styles": '<style data-ve-asset="matrix.css" data-ve-digest="ffff"></style>', "scripts": ""}
        self.assertIn("manifest_dom_mismatch", self.check(_good_dom(), _manifest(), slots))

    def test_missing_dependency_is_caught(self) -> None:
        self.assertIn("manifest_dom_mismatch", self.check(_good_dom(), _manifest(declared_dependencies=("dep.css",))))


class ArtifactSemanticTest(unittest.TestCase):
    """Standalone (expected=None) checking is artifact-semantic."""

    def diags(self, doc: str) -> set[str]:
        return {d.code for d in check_final_document(doc, SKELETON, REGISTRY, components_dir=COMPONENTS)}

    def test_valid_flow_artifact_passes(self) -> None:
        doc = build("component-valid-flow.json")
        self.assertNotIn("artifact_semantic_mismatch", self.diags(doc))

    def test_removed_flow_from_attribute_fails(self) -> None:
        doc = build("component-valid-flow.json").replace(' data-ve-from="node-draft"', "", 1)
        self.assertIn("artifact_semantic_mismatch", self.diags(doc))

    def test_removed_flow_relation_attribute_fails(self) -> None:
        doc = build("component-valid-flow.json").replace(' data-ve-relation="ordered-transition"', "", 1)
        self.assertIn("artifact_semantic_mismatch", self.diags(doc))

    def test_flow_from_ghost_reference_fails(self) -> None:
        # An edge endpoint that is not a node in this canonical flow must fail,
        # even though all three attributes are still present.
        doc = build("component-valid-flow.json").replace('data-ve-from="node-draft"', 'data-ve-from="ghost"', 1)
        self.assertIn("artifact_semantic_mismatch", self.diags(doc))

    def test_flow_to_ghost_reference_fails(self) -> None:
        doc = build("component-valid-flow.json").replace('data-ve-to="node-review"', 'data-ve-to="ghost"', 1)
        self.assertIn("artifact_semantic_mismatch", self.diags(doc))

    def test_flow_endpoint_requires_true_node_identity(self) -> None:
        # An arbitrary element that merely exposes data-ve-node-id — without a
        # non-empty data-ve-semantic-id equal to it — must NOT satisfy an edge
        # endpoint. Otherwise a tampered artifact could smuggle a fake node in to
        # make a rewritten from/to reference resolve.
        doc = build("component-valid-flow.json")
        tampered = doc.replace(
            '<ul class="ve-flow-edges visually-hidden">',
            '<ul class="ve-flow-edges visually-hidden"><li data-ve-node-id="ghost"></li>', 1,
        ).replace('data-ve-from="node-draft"', 'data-ve-from="ghost"', 1)
        self.assertIn("artifact_semantic_mismatch", self.diags(tampered))

    def test_flow_endpoint_rejects_semantic_id_mismatch(self) -> None:
        # A node element whose data-ve-node-id disagrees with its
        # data-ve-semantic-id is not a real node and cannot anchor an endpoint.
        doc = build("component-valid-flow.json")
        tampered = doc.replace(
            '<ul class="ve-flow-edges visually-hidden">',
            '<ul class="ve-flow-edges visually-hidden"><li data-ve-semantic-id="other" data-ve-node-id="ghost"></li>', 1,
        ).replace('data-ve-from="node-draft"', 'data-ve-from="ghost"', 1)
        self.assertIn("artifact_semantic_mismatch", self.diags(tampered))

    def test_flow_endpoint_rejects_arbitrary_matching_attributes(self) -> None:
        # A bare element carrying data-ve-node-id AND an equal data-ve-semantic-id
        # must still NOT count as a node: only a real renderer node element (a
        # ve-flow-node span inside a station in the canvas) may anchor an endpoint.
        doc = build("component-valid-flow.json")
        tampered = doc.replace(
            '<ul class="ve-flow-edges visually-hidden">',
            '<ul class="ve-flow-edges visually-hidden"><span data-ve-node-id="ghost" data-ve-semantic-id="ghost"></span>', 1,
        ).replace('data-ve-from="node-draft"', 'data-ve-from="ghost"', 1)
        self.assertIn("artifact_semantic_mismatch", self.diags(tampered))

    def test_flow_endpoint_rejects_matching_node_outside_canvas(self) -> None:
        # Even a full ve-flow-node span counts only inside a station in the
        # canvas; one smuggled into the edge list is not a real node.
        doc = build("component-valid-flow.json")
        tampered = doc.replace(
            '<ul class="ve-flow-edges visually-hidden">',
            '<ul class="ve-flow-edges visually-hidden"><span class="ve-flow-node" data-ve-node-id="ghost" data-ve-semantic-id="ghost">Ghost</span>', 1,
        ).replace('data-ve-from="node-draft"', 'data-ve-from="ghost"', 1)
        self.assertIn("artifact_semantic_mismatch", self.diags(tampered))

    def test_flow_endpoint_rejects_station_span_without_node_class(self) -> None:
        # A span injected DIRECTLY into a station in the canvas must still not
        # count as a node unless it carries the ve-flow-node class: recognized
        # nodes are bound to the renderer's exact node-element shape (its node
        # class), so an arbitrary station child cannot become an endpoint target.
        doc = build("component-valid-flow.json")
        tampered = doc.replace(
            '<ol class="ve-flow-canvas">',
            '<ol class="ve-flow-canvas"><li class="ve-flow-station">'
            '<span data-ve-node-id="ghost" data-ve-semantic-id="ghost">Ghost</span></li>', 1,
        ).replace('data-ve-from="node-draft"', 'data-ve-from="ghost"', 1)
        self.assertIn("artifact_semantic_mismatch", self.diags(tampered))

    def test_flow_endpoint_cannot_reference_node_in_other_flow(self) -> None:
        # Two canonical flow sections; an edge in the first references a real
        # node of the second. Endpoint identity is scoped per canonical flow, so
        # this must fail.
        from ve_components.checker import validate_artifact_semantics
        doc = build("component-valid-flow.json")
        content = doc.split("VE-CONTROLLED:CONTENT:BEGIN -->")[1].split("<!-- VE-CONTROLLED:CONTENT:END")[0]
        second = content.replace("node-draft", "n2-draft").replace("node-review", "n2-review").replace("node-approve", "n2-approve")
        # First flow's opening edge now points at the second flow's node.
        first = content.replace('data-ve-to="node-review"', 'data-ve-to="n2-review"', 1)
        diags = {d.code for d in validate_artifact_semantics(first + second)}
        self.assertIn("artifact_semantic_mismatch", diags)

    def test_matrix_cell_missing_column_association_fails(self) -> None:
        doc = build("component-valid-matrix.json").replace(' data-ve-column-id="col-read"', "", 1)
        self.assertIn("artifact_semantic_mismatch", self.diags(doc))

    def test_removed_figcaption_fails(self) -> None:
        import re
        doc = build("component-valid-matrix.json")
        doc = re.sub(r"<figcaption[^>]*>.*?</figcaption>", "", doc, count=1, flags=re.DOTALL)
        self.assertIn("artifact_semantic_mismatch", self.diags(doc))


class StaticFirstTest(unittest.TestCase):
    def test_empty_script_slot_and_semantic_content_survive(self) -> None:
        for name in ("component-valid-matrix.json", "component-valid-flow.json", "component-valid-mixed.json"):
            with self.subTest(name=name):
                doc = build(name)
                scripts = doc.split("VE-CONTROLLED:COMPONENT-SCRIPTS:BEGIN")[1].split("VE-CONTROLLED:COMPONENT-SCRIPTS:END")[0]
                self.assertNotIn("<script", scripts)
                self.assertIn("data-ve-semantic-id=", doc)

    def test_registry_declares_no_script_assets(self) -> None:
        for component in REGISTRY.components:
            self.assertEqual([a for a in component.assets if a.slot == "scripts"], [])


class TrustedAssetTamperTest(unittest.TestCase):
    def test_tampered_css_fails_build(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="ve-assets-"))
        try:
            shutil.copytree(COMPONENTS, tmp, dirs_exist_ok=True)
            registry = load_registry(tmp / "registry.json")
            raw = json.loads((TESTS / "component-valid-matrix.json").read_text("utf-8"))
            # Baseline build succeeds against the copied assets.
            build_document(raw, registry, TRUSTED_RENDERERS, SKELETON, tmp)
            # Tamper one byte of the isolated copy; the digest gate must fail.
            css = tmp / "matrix.css"
            css.write_text(css.read_text("utf-8") + "/* x */", "utf-8")
            with self.assertRaises(ContractError):
                build_document(raw, registry, TRUSTED_RENDERERS, SKELETON, tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class MixedAndWeakModelFinalTest(unittest.TestCase):
    def test_mixed_one_content_slot_and_clean_compat(self) -> None:
        doc = build("component-valid-mixed.json")
        self.assertEqual(doc.count("VE-CONTROLLED:CONTENT:BEGIN"), 1)
        # compatibility wrapper carries no registry/renderer provenance
        compat = doc.split('data-ve-section-kind="compatibility"')[1].split("</section>")[0]
        self.assertNotIn("data-ve-component", compat)
        styles = doc.split("VE-CONTROLLED:COMPONENT-STYLES:BEGIN")[1].split("VE-CONTROLLED:COMPONENT-STYLES:END")[0]
        self.assertNotIn("lane-label", styles)

    def test_weak_model_retains_reason_through_final_check(self) -> None:
        doc = build("component-valid-weak-model.json")
        diags = check_final_document(doc, SKELETON, REGISTRY, components_dir=COMPONENTS)
        self.assertEqual(diags, [])
        self.assertIn('data-ve-compat-source="legacy-html-insertion"', doc)
        self.assertIn('data-ve-compat-reason="weak-model-degradation"', doc)

    def test_bad_weak_model_fixtures_fail_no_output(self) -> None:
        for name in ("component-bad-weak-model-style.json", "component-bad-weak-model-script.json"):
            with self.subTest(name=name):
                out = Path(tempfile.gettempdir()) / f"ve-weakrej-{name}.html"
                out.unlink(missing_ok=True)
                proc = subprocess.run(["python3", str(BUILD), "--assembly", str(TESTS / name), "--output", str(out)],
                                      capture_output=True, text=True)
                self.assertNotEqual(proc.returncode, 0)
                self.assertFalse(out.exists())
                self.assertIn("forbidden_content_markup", proc.stderr)


if __name__ == "__main__":
    unittest.main()
