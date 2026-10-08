"""Versioned skeleton resolution: each document is checked against the skeleton it declares."""
from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from build_explainer import build_document
from first_screen_ir import assembly
from ve_components.checker import check_final_document
from ve_components.diagnostics import ContractError
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.skeletons import (
    LATEST_SKELETON_VERSION,
    declared_skeleton_version,
    resolve_skeleton,
    skeleton_file,
)

SKILL = Path(__file__).resolve().parents[2]
ASSETS = SKILL / "assets"
COMPONENTS = ASSETS / "components"
LATEST = (ASSETS / "skeleton.html").read_text("utf-8")
V1 = (ASSETS / "skeleton-v1.html").read_text("utf-8")
V2 = (ASSETS / "skeleton-v2.html").read_text("utf-8")
V3 = (ASSETS / "skeleton-v3.html").read_text("utf-8")
REGISTRY = load_registry(COMPONENTS / "registry.json")
TESTS = Path(__file__).resolve().parent
CHECK = TESTS.parent / "check.sh"

FROZEN_SHA256 = {
    "skeleton-v1.html": "7512debf49653053249be88218a2025a2d5374e2c5b289784fb47a0f5d1f720b",
    "skeleton-v2.html": "1f58a12aa50e73a08f4ae12f7ef70bc271f39ebfe53a9910eb9ab14104f03125",
    "skeleton-v3.html": "92629e1398a374c7090452ff5f5a8b03f4e18ce44e8103678843e84745031592",
}
# Asset digests are shared by every skeleton version: changing a component CSS
# file would fail every older document that embeds it (preflight ruling 1).
FROZEN_ASSET_DIGESTS = {
    "matrix.css": "fe9fd5f86063dcb93790a9549a7630a162d674082446e2dd5f86c540bd6b692c",
    "chevron.css": "afdb6d3b748a45e67714851bdb8033993fadd7bc27a9a5295f46fef77c6720f8",
}


class SkeletonVersionTest(unittest.TestCase):
    def test_latest_declares_latest_version(self) -> None:
        self.assertEqual(declared_skeleton_version(LATEST), LATEST_SKELETON_VERSION)
        self.assertEqual(LATEST_SKELETON_VERSION, 4)

    def test_missing_attribute_means_v1(self) -> None:
        self.assertEqual(declared_skeleton_version(V1), 1)

    def test_frozen_versions_declare_themselves(self) -> None:
        self.assertEqual(declared_skeleton_version(V2), 2)
        self.assertEqual(declared_skeleton_version(V3), 3)

    def test_frozen_skeletons_are_byte_identical_to_their_release(self) -> None:
        for name, digest in FROZEN_SHA256.items():
            data = (ASSETS / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest, name)

    def test_skeleton_file_mapping(self) -> None:
        self.assertEqual(skeleton_file(4, ASSETS), ASSETS / "skeleton.html")
        self.assertEqual(skeleton_file(3, ASSETS), ASSETS / "skeleton-v3.html")
        self.assertEqual(skeleton_file(2, ASSETS), ASSETS / "skeleton-v2.html")
        self.assertEqual(skeleton_file(1, ASSETS), ASSETS / "skeleton-v1.html")

    def test_resolve_returns_given_when_versions_match(self) -> None:
        self.assertIs(resolve_skeleton(LATEST, LATEST, ASSETS), LATEST)

    def test_resolve_loads_frozen_skeletons(self) -> None:
        self.assertEqual(resolve_skeleton(V1, LATEST, ASSETS), V1)
        self.assertEqual(resolve_skeleton(V2, LATEST, ASSETS), V2)
        self.assertEqual(resolve_skeleton(V3, LATEST, ASSETS), V3)

    def test_resolve_unknown_version_is_none(self) -> None:
        doc = LATEST.replace('data-ve-skeleton="4"', 'data-ve-skeleton="9"', 1)
        self.assertIsNone(resolve_skeleton(doc, LATEST, ASSETS))

    def test_latest_first_screen_has_no_viewport_min_height(self) -> None:
        rule = next(line for line in LATEST.splitlines() if line.strip().startswith(".first-screen {"))
        self.assertNotIn("min-height", rule)


class BackwardCompatibilityTest(unittest.TestCase):
    def test_v1_rendered_fixtures_still_pass_against_latest(self) -> None:
        for name in ("matrix-doc-all-notations.html", "chevron-doc.html"):
            raw = (TESTS / name).read_text("utf-8")
            self.assertEqual(declared_skeleton_version(raw), 1, name)
            diags = check_final_document(raw, LATEST, REGISTRY, components_dir=COMPONENTS)
            self.assertEqual([d.message for d in diags], [], name)

    def _passes_both_checkers(self, name: str, version: int) -> None:
        path = TESTS / name
        raw = path.read_text("utf-8")
        self.assertEqual(declared_skeleton_version(raw), version)
        diags = check_final_document(raw, LATEST, REGISTRY, components_dir=COMPONENTS)
        self.assertEqual([d.message for d in diags], [])
        proc = subprocess.run(["bash", str(CHECK), str(path)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_v2_document_passes_both_checkers(self) -> None:
        self._passes_both_checkers("v2-proposal-doc.html", 2)

    def test_v3_document_passes_both_checkers(self) -> None:
        self._passes_both_checkers("v3-proposal-doc.html", 3)

    def test_component_assets_are_not_modified(self) -> None:
        registry = json.loads((COMPONENTS / "registry.json").read_text("utf-8"))
        digests = {asset["path"]: asset["digest"]
                   for component in registry["components"] for asset in component["assets"]}
        for path, digest in FROZEN_ASSET_DIGESTS.items():
            self.assertEqual(digests[path], digest, path)
            self.assertEqual(hashlib.sha256((COMPONENTS / path).read_bytes()).hexdigest(), digest, path)

    def test_unknown_version_document_fails(self) -> None:
        raw = (TESTS / "matrix-doc-all-notations.html").read_text("utf-8").replace(
            '<html lang="ja"', '<html lang="ja" data-ve-skeleton="9"', 1)
        diags = check_final_document(raw, LATEST, REGISTRY, components_dir=COMPONENTS)
        self.assertIn("未知の skeleton 版です: 9", [d.message for d in diags])


class BuildUsesLatestSkeletonTest(unittest.TestCase):
    def test_build_refuses_frozen_skeleton(self) -> None:
        raw = assembly({"conclusion": "限定対象で開始する。"})
        with self.assertRaises(ContractError) as ctx:
            build_document(raw, REGISTRY, TRUSTED_RENDERERS, V3, COMPONENTS, document_path="x.html")
        self.assertEqual([d.message for d in ctx.exception.diagnostics],
                         ["ビルドは最新の skeleton 版（4）だけを使えます: 3"])

    def test_built_document_declares_latest_version(self) -> None:
        raw = assembly({"conclusion": "限定対象で開始する。"})
        html = build_document(raw, REGISTRY, TRUSTED_RENDERERS, LATEST, COMPONENTS, document_path="x.html")
        self.assertEqual(declared_skeleton_version(html), 4)


if __name__ == "__main__":
    unittest.main()
