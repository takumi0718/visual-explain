"""document.type / document.profile の検証テスト。"""
from __future__ import annotations

import unittest

from ve_components.diagnostics import ContractError
from ve_components.validation import validate_assembly

BASE = {
    "schemaVersion": 1,
    "document": {"id": "doc-1", "title": "タイトル", "summary": "要約。",
                 "type": "proposal", "profile": "strict"},
    "sections": [],  # Task 5 までは空 sections を許す前提で書く（Task 5 で必須構造テストに置き換える）
}


def _doc(**overrides) -> dict:
    raw = {**BASE, "document": {**BASE["document"], **overrides}}
    return raw


class DocumentMetadataTest(unittest.TestCase):
    def test_valid_type_and_profile_accepted(self) -> None:
        request = validate_assembly(_doc())
        self.assertEqual(request.document.type, "proposal")
        self.assertEqual(request.document.profile, "strict")

    def test_missing_type_rejected(self) -> None:
        raw = _doc()
        del raw["document"]["type"]
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("document.type" in str(d) for d in ctx.exception.diagnostics))

    def test_unknown_type_rejected(self) -> None:
        with self.assertRaises(ContractError):
            validate_assembly(_doc(type="poem"))

    def test_unknown_profile_rejected(self) -> None:
        with self.assertRaises(ContractError):
            validate_assembly(_doc(profile="rich"))
