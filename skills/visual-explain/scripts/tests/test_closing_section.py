"""型付き closing: 資料型別の必須見出しと h2+ul markup。"""
from __future__ import annotations

import unittest

from ve_components.diagnostics import ContractError
from ve_components.document_sections import render_closing
from ve_components.model import ClosingBlock, ClosingSection
from ve_components.validation import validate_assembly


def _assembly(*, type: str = "proposal", closing_blocks: list | None = None) -> dict:
    if closing_blocks is None:
        closing_blocks = [
            {"heading": "リスクと弱い前提", "items": ["前提Aが弱い"]},
            {"heading": "不確かな点", "items": ["未確認の利用状況"]},
        ]
    return {
        "schemaVersion": 1,
        "document": {
            "id": "d",
            "title": "料金改定は限定対象で段階公開する",
            "summary": "要約文。",
            "type": type,
            "profile": "strict",
        },
        "sections": [
            {"kind": "closing", "id": "sec-closing", "blocks": closing_blocks},
        ],
    }


class ClosingSectionTest(unittest.TestCase):
    def test_proposal_requires_both_closing_headings(self) -> None:
        raw = _assembly(type="proposal", closing_blocks=[{"heading": "リスクと弱い前提", "items": ["前提Aが弱い"]}])
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("不確かな点" in str(d) for d in ctx.exception.diagnostics))

    def test_empty_items_rejected(self) -> None:
        raw = _assembly(
            type="proposal",
            closing_blocks=[
                {"heading": "リスクと弱い前提", "items": []},
                {"heading": "不確かな点", "items": ["未確認の利用状況"]},
            ],
        )
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("items" in str(d) for d in ctx.exception.diagnostics))

    def test_render_closing_includes_h2_headings(self) -> None:
        section = ClosingSection(
            id="sec-closing",
            blocks=(
                ClosingBlock(heading="リスクと弱い前提", items=("前提Aが弱い",)),
                ClosingBlock(heading="不確かな点", items=("未確認の利用状況",)),
            ),
        )
        wrapped = render_closing(section)
        self.assertIn('data-ve-section-kind="closing"', wrapped.markup)
        self.assertIn('id="sec-closing"', wrapped.markup)
        self.assertIn('<section class="closing-section" aria-label="判断材料">', wrapped.markup)
        self.assertIn("<h2>リスクと弱い前提</h2>", wrapped.markup)
        self.assertIn("<h2>不確かな点</h2>", wrapped.markup)
        self.assertIn("<ul><li>前提Aが弱い</li></ul>", wrapped.markup)
        self.assertIn("<ul><li>未確認の利用状況</li></ul>", wrapped.markup)
        # escape
        escaped = render_closing(ClosingSection(
            id="sec-x",
            blocks=(ClosingBlock(heading="<script>", items=("<b>x</b>",)),),
        ))
        self.assertIn("<h2>&lt;script&gt;</h2>", escaped.markup)
        self.assertIn("<li>&lt;b&gt;x&lt;/b&gt;</li>", escaped.markup)
        self.assertNotIn("<script>", escaped.markup)

    def test_research_requires_closing_heading(self) -> None:
        raw = _assembly(type="research", closing_blocks=[{"heading": "限界・確度", "items": ["推論を含む"]}])
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("限界・反証・確度" in str(d) for d in ctx.exception.diagnostics))

        ok = _assembly(
            type="research",
            closing_blocks=[{"heading": "限界・反証・確度", "items": ["推論を含む"]}],
        )
        req = validate_assembly(ok)
        self.assertIsInstance(req.sections[0], ClosingSection)
        self.assertEqual(req.sections[0].blocks[0].heading, "限界・反証・確度")
