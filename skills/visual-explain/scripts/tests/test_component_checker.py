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

    def test_asset_hash(self) -> None:
        self.assertIn("invalid_controlled_asset", self.check("component-bad-asset-hash.html"))

    def test_missing_compatibility_provenance(self) -> None:
        self.assertIn("missing_provenance", self.check("component-bad-compatibility-provenance.html"))

    def test_provenance_scan_accepts_valid_wrappers(self) -> None:
        content = ('<section data-ve-section-kind="canonical" data-ve-component="matrix" data-ve-instance="a"></section>'
                   '<section data-ve-section-kind="compatibility" data-ve-compat-source="legacy-html-insertion"'
                   ' data-ve-compat-reason="unmigrated-format" data-ve-instance="b"></section>')
        self.assertEqual(validate_final_provenance(content), [])


class ManifestToDomTest(unittest.TestCase):
    def test_missing_semantic_id_is_caught(self) -> None:
        manifest = RenderManifest(
            component_id="matrix", component_version=1, instance_id="sec-1",
            consumed_semantic_ids=("sec-1", "row-x"), generated_relationship_ids=(),
            generated_landmark_ids=(), asset_ids=(), asset_digests=(),
            declared_dependencies=(), fallback_mode="static-content")

        class Expected:
            manifests = (manifest,)
            compatibility = ()

        content = '<section data-ve-instance="sec-1"><span data-ve-semantic-id="row-x"></span></section>'
        self.assertEqual(check_manifest_to_dom(content, {}, Expected()), [])
        missing = '<section data-ve-instance="sec-1"></section>'
        codes = {d.code for d in check_manifest_to_dom(missing, {}, Expected())}
        self.assertIn("manifest_dom_mismatch", codes)


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
