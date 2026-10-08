"""Versioned skeleton resolution: each document is checked against the skeleton it declares."""
from __future__ import annotations

import hashlib
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
REGISTRY = load_registry(COMPONENTS / "registry.json")
TESTS = Path(__file__).resolve().parent
CHECK = TESTS.parent / "check.sh"

FROZEN_SHA256 = {
    "skeleton-v1.html": "7512debf49653053249be88218a2025a2d5374e2c5b289784fb47a0f5d1f720b",
    "skeleton-v2.html": "1f58a12aa50e73a08f4ae12f7ef70bc271f39ebfe53a9910eb9ab14104f03125",
}


class SkeletonVersionTest(unittest.TestCase):
    def test_latest_declares_latest_version(self) -> None:
        self.assertEqual(declared_skeleton_version(LATEST), LATEST_SKELETON_VERSION)
        self.assertEqual(LATEST_SKELETON_VERSION, 3)

    def test_missing_attribute_means_v1(self) -> None:
        self.assertEqual(declared_skeleton_version(V1), 1)

    def test_frozen_v2_declares_two(self) -> None:
        self.assertEqual(declared_skeleton_version(V2), 2)

    def test_frozen_skeletons_are_byte_identical_to_their_release(self) -> None:
        for name, digest in FROZEN_SHA256.items():
            data = (ASSETS / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest, name)

    def test_skeleton_file_mapping(self) -> None:
        self.assertEqual(skeleton_file(3, ASSETS), ASSETS / "skeleton.html")
        self.assertEqual(skeleton_file(2, ASSETS), ASSETS / "skeleton-v2.html")
        self.assertEqual(skeleton_file(1, ASSETS), ASSETS / "skeleton-v1.html")

    def test_resolve_returns_given_when_versions_match(self) -> None:
        self.assertIs(resolve_skeleton(LATEST, LATEST, ASSETS), LATEST)

    def test_resolve_loads_frozen_skeletons(self) -> None:
        self.assertEqual(resolve_skeleton(V1, LATEST, ASSETS), V1)
        self.assertEqual(resolve_skeleton(V2, LATEST, ASSETS), V2)

    def test_resolve_unknown_version_is_none(self) -> None:
        doc = LATEST.replace('data-ve-skeleton="3"', 'data-ve-skeleton="9"', 1)
        self.assertIsNone(resolve_skeleton(doc, LATEST, ASSETS))

    def test_v2_first_screen_has_no_viewport_min_height(self) -> None:
        rule = next(line for line in LATEST.splitlines() if line.strip().startswith(".first-screen {"))
        self.assertNotIn("min-height", rule)


class BackwardCompatibilityTest(unittest.TestCase):
    def test_v1_rendered_fixtures_still_pass_against_latest(self) -> None:
        for name in ("matrix-doc-all-notations.html", "chevron-doc.html"):
            raw = (TESTS / name).read_text("utf-8")
            self.assertEqual(declared_skeleton_version(raw), 1, name)
            diags = check_final_document(raw, LATEST, REGISTRY, components_dir=COMPONENTS)
            self.assertEqual([d.message for d in diags], [], name)

    def test_v2_document_passes_both_checkers(self) -> None:
        path = TESTS / "v2-proposal-doc.html"
        raw = path.read_text("utf-8")
        self.assertEqual(declared_skeleton_version(raw), 2)
        diags = check_final_document(raw, LATEST, REGISTRY, components_dir=COMPONENTS)
        self.assertEqual([d.message for d in diags], [])
        proc = subprocess.run(["bash", str(CHECK), str(path)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_unknown_version_document_fails(self) -> None:
        raw = (TESTS / "matrix-doc-all-notations.html").read_text("utf-8").replace(
            '<html lang="ja"', '<html lang="ja" data-ve-skeleton="9"', 1)
        diags = check_final_document(raw, LATEST, REGISTRY, components_dir=COMPONENTS)
        self.assertIn("未知の skeleton 版です: 9", [d.message for d in diags])


class BuildUsesLatestSkeletonTest(unittest.TestCase):
    def test_build_refuses_frozen_skeleton(self) -> None:
        raw = assembly({"conclusion": "限定対象で開始する。"})
        with self.assertRaises(ContractError) as ctx:
            build_document(raw, REGISTRY, TRUSTED_RENDERERS, V2, COMPONENTS, document_path="x.html")
        self.assertEqual([d.message for d in ctx.exception.diagnostics],
                         ["ビルドは最新の skeleton 版（3）だけを使えます: 2"])

    def test_built_document_declares_latest_version(self) -> None:
        raw = assembly({"conclusion": "限定対象で開始する。"})
        html = build_document(raw, REGISTRY, TRUSTED_RENDERERS, LATEST, COMPONENTS, document_path="x.html")
        self.assertEqual(declared_skeleton_version(html), 3)


if __name__ == "__main__":
    unittest.main()
