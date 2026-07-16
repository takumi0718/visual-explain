"""構造不変条件: first-screen/closing の位置・個数、narrative の h1/予約属性禁止。"""
from __future__ import annotations

import unittest

from ve_components.diagnostics import ContractError
from ve_components.validation import validate_assembly

_DOC = {
    "id": "doc-1",
    "title": "料金改定は限定対象で段階公開する",
    "summary": "要約文。",
    "type": "proposal",
    "profile": "strict",
}

_FIRST = {"kind": "first-screen", "id": "sec-first", "decision": "決めます。"}
_CLOSING = {
    "kind": "closing",
    "id": "sec-closing",
    "blocks": [
        {"heading": "リスクと弱い前提", "items": ["前提Aが弱い"]},
        {"heading": "不確かな点", "items": ["未確認の利用状況"]},
    ],
}
_NARR = {"kind": "narrative", "id": "sec-body", "markup": "<p>本文です。</p>"}


def _assembly(*sections: dict) -> dict:
    return {"schemaVersion": 1, "document": dict(_DOC), "sections": list(sections)}


def _messages(exc: ContractError) -> str:
    return " ".join(str(d) for d in exc.diagnostics)


class DocumentStructureTest(unittest.TestCase):
    def test_rejects_missing_first_screen(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_CLOSING))
        self.assertIn("first-screen は先頭にちょうど1個必要です", _messages(ctx.exception))

    def test_rejects_two_first_screens(self) -> None:
        second = {"kind": "first-screen", "id": "sec-first-2", "decision": "別の判断をします。"}
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_FIRST, second, _CLOSING))
        self.assertIn("first-screen は先頭にちょうど1個必要です", _messages(ctx.exception))

    def test_rejects_first_screen_not_at_front(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_NARR, _FIRST, _CLOSING))
        self.assertIn("first-screen は先頭にちょうど1個必要です", _messages(ctx.exception))

    def test_rejects_missing_closing(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_FIRST))
        self.assertIn("closing は最後にちょうど1個必要です", _messages(ctx.exception))

    def test_rejects_narrative_after_closing(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_FIRST, _CLOSING, _NARR))
        self.assertIn("closing は最後にちょうど1個必要です", _messages(ctx.exception))

    def test_rejects_h1_in_narrative(self) -> None:
        narr = {"kind": "narrative", "id": "sec-bad-h1", "markup": "<h1>見出し</h1><p>本文</p>"}
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_FIRST, narr, _CLOSING))
        self.assertIn("narrative に <h1> は置けません（h1 は first-screen 専有）", _messages(ctx.exception))

    def test_rejects_data_ask_in_narrative(self) -> None:
        narr = {
            "kind": "narrative",
            "id": "sec-bad-ask",
            "markup": '<div data-ask="decision"><p>問いはここに置かない</p></div>',
        }
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_FIRST, narr, _CLOSING))
        self.assertIn("narrative に予約属性 data-ask は置けません", _messages(ctx.exception))

    def test_valid_structure_accepted(self) -> None:
        req = validate_assembly(_assembly(_FIRST, _NARR, _CLOSING))
        self.assertEqual(len(req.sections), 3)

    def test_compatibility_allows_reserved_attrs(self) -> None:
        compat = {
            "kind": "compatibility",
            "id": "sec-compat",
            "markup": '<ol class="flow" data-connect="a->b"><li id="a">A</li><li id="b">B</li></ol>',
            "provenance": {
                "source": "legacy-html-insertion",
                "reason": "unmigrated-format",
                "format": "flow",
            },
        }
        req = validate_assembly(_assembly(_FIRST, compat, _CLOSING))
        self.assertEqual(len(req.sections), 3)

    def test_compatibility_rejects_h1(self) -> None:
        compat = {
            "kind": "compatibility",
            "id": "sec-compat-h1",
            "markup": "<h1>禁止</h1><p>legacy</p>",
            "provenance": {
                "source": "legacy-html-insertion",
                "reason": "unmigrated-format",
                "format": "freeform",
            },
        }
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_FIRST, compat, _CLOSING))
        self.assertIn("<h1>", _messages(ctx.exception))
