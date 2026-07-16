"""型付き first-screen: h1 は document.title 由来、subtitle は型で切替。"""
from __future__ import annotations

import unittest

from ve_components.diagnostics import ContractError
from ve_components.document_sections import render_first_screen
from ve_components.model import DocumentMetadata, FirstScreenSection

DOC = DocumentMetadata(id="doc-1", title="料金改定は限定対象で段階公開する", summary="要約文。",
                       type="proposal", profile="strict")


class FirstScreenRenderTest(unittest.TestCase):
    def test_h1_comes_from_document_title(self) -> None:
        section = FirstScreenSection(id="sec-first", decision="限定対象で開始するか決めます。",
                                     conditions=("撤回条件を先に合意できること",))
        wrapped = render_first_screen(section, DOC)
        self.assertIn("<h1>料金改定は限定対象で段階公開する</h1>", wrapped.markup)
        self.assertIn("data-ve-document-type=\"proposal\"", wrapped.markup)
        self.assertIn("data-ve-profile=\"strict\"", wrapped.markup)
        self.assertIn("要約文。", wrapped.markup)  # summary が描画される
        self.assertIn("あなたが決めること", wrapped.markup)

    def test_system_uses_question_subtitle(self) -> None:
        doc = DocumentMetadata(id="d", title="T", summary="S。", type="system", profile="strict")
        section = FirstScreenSection(id="sec-first", decision="この仕組みはなぜ安全か。", conditions=())
        wrapped = render_first_screen(section, doc)
        self.assertIn("この資料が答える問い", wrapped.markup)
        self.assertNotIn("あなたが決めること", wrapped.markup)

    def test_more_than_two_conditions_rejected_by_validation(self) -> None:
        from ve_components.validation import validate_assembly
        raw = {"schemaVersion": 1,
               "document": {"id": "d", "title": "T", "summary": "S。", "type": "proposal", "profile": "strict"},
               "sections": [{"kind": "first-screen", "id": "sec-first",
                             "decision": "決めます。", "conditions": ["a", "b", "c"]}]}
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("conditions" in str(d) for d in ctx.exception.diagnostics))
