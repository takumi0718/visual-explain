"""document.type / document.profile の検証テスト。"""
from __future__ import annotations

import unittest

from ve_components.diagnostics import ContractError
from ve_components.validation import validate_assembly

_FIRST = {"kind": "first-screen", "id": "sec-first", "decision": "決めます。"}
_CLOSING = {
    "kind": "closing",
    "id": "sec-closing",
    "blocks": [
        {"heading": "リスクと弱い前提", "items": ["前提"]},
        {"heading": "不確かな点", "items": ["未確認"]},
    ],
}

BASE = {
    "schemaVersion": 1,
    "document": {"id": "doc-1", "title": "タイトル", "summary": "要約。",
                 "type": "proposal", "profile": "strict"},
    "sections": [_FIRST, _CLOSING],
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

    def test_non_string_type_array_rejected(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_doc(type=["proposal"]))
        self.assertTrue(any("document.type" in str(d) for d in ctx.exception.diagnostics))

    def test_non_string_type_object_rejected(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_doc(type={"value": "proposal"}))
        self.assertTrue(any("document.type" in str(d) for d in ctx.exception.diagnostics))

    def test_non_string_profile_array_rejected(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_doc(profile=["strict"]))
        self.assertTrue(any("document.profile" in str(d) for d in ctx.exception.diagnostics))

    def test_non_string_profile_object_rejected(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_doc(profile={"value": "strict"}))
        self.assertTrue(any("document.profile" in str(d) for d in ctx.exception.diagnostics))
