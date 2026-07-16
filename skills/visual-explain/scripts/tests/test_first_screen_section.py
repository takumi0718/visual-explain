"""型付き first-screen: h1 は document.title 由来、subtitle は型で切替。"""
from __future__ import annotations

import unittest
from pathlib import Path

from build_explainer import build_document
from ve_components.assembly import compose_sections
from ve_components.diagnostics import ContractError
from ve_components.document_sections import render_first_screen
from ve_components.model import DocumentMetadata, FirstScreenSection
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.validation import validate_assembly

DOC = DocumentMetadata(id="doc-1", title="料金改定は限定対象で段階公開する", summary="要約文。",
                       type="proposal", profile="strict")

SKILL_DIR = Path(__file__).resolve().parents[2]
SKELETON = (SKILL_DIR / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS_DIR = SKILL_DIR / "assets" / "components"
REGISTRY = load_registry(COMPONENTS_DIR / "registry.json")


def _first_screen_assembly(**section_extra):
    section = {"kind": "first-screen", "id": "sec-first", "decision": "決めます。"}
    section.update(section_extra)
    return {
        "schemaVersion": 1,
        "document": {
            "id": "d",
            "title": "料金改定は限定対象で段階公開する",
            "summary": "要約文。",
            "type": "proposal",
            "profile": "strict",
        },
        "sections": [section],
    }


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
        raw = _first_screen_assembly(conditions=["a", "b", "c"])
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("conditions" in str(d) for d in ctx.exception.diagnostics))

    def test_null_conditions_rejected_by_validation(self) -> None:
        raw = _first_screen_assembly(conditions=None)
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("conditions" in str(d) for d in ctx.exception.diagnostics))

    def test_omitted_conditions_defaults_to_empty(self) -> None:
        req = validate_assembly(_first_screen_assembly())
        section = req.sections[0]
        self.assertIsInstance(section, FirstScreenSection)
        self.assertEqual(section.conditions, ())

    def test_compose_sections_accepts_wrapped_document_section(self) -> None:
        section = FirstScreenSection(id="sec-first", decision="決めます。", conditions=("a",))
        wrapped = render_first_screen(section, DOC)
        composition = compose_sections([wrapped])
        self.assertEqual(composition.sections_markup, (wrapped.markup,))

    def test_build_document_includes_first_screen(self) -> None:
        html = build_document(
            _first_screen_assembly(conditions=["撤回条件を先に合意できること"]),
            REGISTRY,
            TRUSTED_RENDERERS,
            SKELETON,
            COMPONENTS_DIR,
        )
        self.assertIn('data-ve-section-kind="first-screen"', html)
        self.assertIn("<h1>料金改定は限定対象で段階公開する</h1>", html)
        self.assertIn("要約文。", html)
        self.assertIn("あなたが決めること", html)
