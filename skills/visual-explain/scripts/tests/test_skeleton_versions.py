"""Versioned skeleton resolution: each document is checked against the skeleton it declares."""
from __future__ import annotations

import unittest
from pathlib import Path

from ve_components.checker import check_final_document
from ve_components.registry import load_registry
from ve_components.skeletons import (
    LATEST_SKELETON_VERSION,
    declared_skeleton_version,
    resolve_skeleton,
    skeleton_file,
)

SKILL = Path(__file__).resolve().parents[2]
ASSETS = SKILL / "assets"
LATEST = (ASSETS / "skeleton.html").read_text("utf-8")
V1 = (ASSETS / "skeleton-v1.html").read_text("utf-8")
REGISTRY = load_registry(ASSETS / "components" / "registry.json")
TESTS = Path(__file__).resolve().parent


class SkeletonVersionTest(unittest.TestCase):
    def test_latest_declares_latest_version(self) -> None:
        self.assertEqual(declared_skeleton_version(LATEST), LATEST_SKELETON_VERSION)
        self.assertEqual(LATEST_SKELETON_VERSION, 2)

    def test_missing_attribute_means_v1(self) -> None:
        self.assertEqual(declared_skeleton_version(V1), 1)

    def test_skeleton_file_mapping(self) -> None:
        self.assertEqual(skeleton_file(2, ASSETS), ASSETS / "skeleton.html")
        self.assertEqual(skeleton_file(1, ASSETS), ASSETS / "skeleton-v1.html")

    def test_resolve_returns_given_when_versions_match(self) -> None:
        self.assertIs(resolve_skeleton(LATEST, LATEST, ASSETS), LATEST)

    def test_resolve_loads_frozen_v1_for_v1_document(self) -> None:
        self.assertEqual(resolve_skeleton(V1, LATEST, ASSETS), V1)

    def test_resolve_unknown_version_is_none(self) -> None:
        doc = LATEST.replace('data-ve-skeleton="2"', 'data-ve-skeleton="9"', 1)
        self.assertIsNone(resolve_skeleton(doc, LATEST, ASSETS))

    def test_v2_first_screen_has_no_viewport_min_height(self) -> None:
        rule = next(line for line in LATEST.splitlines() if line.strip().startswith(".first-screen {"))
        self.assertNotIn("min-height", rule)


class BackwardCompatibilityTest(unittest.TestCase):
    def test_v1_rendered_fixtures_still_pass_against_latest(self) -> None:
        for name in ("matrix-doc-all-notations.html", "chevron-doc.html"):
            raw = (TESTS / name).read_text("utf-8")
            self.assertEqual(declared_skeleton_version(raw), 1, name)
            diags = check_final_document(raw, LATEST, REGISTRY, components_dir=ASSETS / "components")
            self.assertEqual([d.message for d in diags], [], name)

    def test_unknown_version_document_fails(self) -> None:
        raw = (TESTS / "matrix-doc-all-notations.html").read_text("utf-8").replace(
            '<html lang="ja"', '<html lang="ja" data-ve-skeleton="9"', 1)
        diags = check_final_document(raw, LATEST, REGISTRY, components_dir=ASSETS / "components")
        self.assertIn("未知の skeleton 版です: 9", [d.message for d in diags])


if __name__ == "__main__":
    unittest.main()
