"""型付き ask: askType discriminated union（decision / request / hypothesis）の静的表示。"""
from __future__ import annotations

import unittest
from pathlib import Path

from build_explainer import build_document
from ve_components.checker import validate_ask_blocks
from ve_components.diagnostics import ContractError
from ve_components.document_sections import render_ask
from ve_components.model import AskOption, AskSection, AskStep
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.validation import validate_assembly

SKILL_DIR = Path(__file__).resolve().parents[2]
SKELETON = (SKILL_DIR / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS_DIR = SKILL_DIR / "assets" / "components"
REGISTRY = load_registry(COMPONENTS_DIR / "registry.json")


def _doc() -> dict:
    return {
        "id": "d",
        "title": "料金改定は限定対象で段階公開する",
        "summary": "要約文。",
        "type": "proposal",
        "profile": "strict",
    }


def _assembly(section: dict) -> dict:
    return {
        "schemaVersion": 1,
        "document": _doc(),
        "sections": [
            {"kind": "first-screen", "id": "sec-first", "decision": "決めます。"},
            section,
            {
                "kind": "closing",
                "id": "sec-closing",
                "blocks": [
                    {"heading": "リスクと弱い前提", "items": ["前提Aが弱い"]},
                    {"heading": "不確かな点", "items": ["未確認の利用状況"]},
                ],
            },
        ],
    }


def _decision_section(**extra) -> dict:
    section = {
        "kind": "ask",
        "id": "sec-ask-decision",
        "askType": "decision",
        "question": "注釈を今回に含めますか？",
        "options": [
            {"id": "include", "label": "含める", "tradeoff": "変更量が増える"},
            {"id": "later", "label": "次フェーズ", "tradeoff": "効果が遅れる"},
        ],
        "defaultId": "include",
    }
    section.update(extra)
    return section


class AskSectionTest(unittest.TestCase):
    def test_decision_happy_path_renders_and_passes_ask_inspector(self) -> None:
        req = validate_assembly(_assembly(_decision_section()))
        section = next(s for s in req.sections if isinstance(s, AskSection))
        self.assertEqual(section.ask_type, "decision")
        self.assertEqual(section.question, "注釈を今回に含めますか？")
        self.assertEqual(section.default_id, "include")
        self.assertIsNone(section.no_default_reason)
        self.assertEqual(len(section.options), 2)

        wrapped = render_ask(section)
        self.assertIn('data-ve-section-kind="ask"', wrapped.markup)
        self.assertIn('data-ve-ask-type="decision"', wrapped.markup)
        self.assertIn('id="sec-ask-decision"', wrapped.markup)
        self.assertIn('class="ask" data-ask="decision"', wrapped.markup)
        self.assertIn('class="ask-kind"', wrapped.markup)
        self.assertIn("判断してください", wrapped.markup)
        self.assertIn('class="ask-question"', wrapped.markup)
        self.assertIn("注釈を今回に含めますか？", wrapped.markup)
        self.assertIn('class="ask-options"', wrapped.markup)
        self.assertIn("data-ask-option", wrapped.markup)
        self.assertIn("data-ask-default", wrapped.markup)
        self.assertIn('class="ask-tradeoff"', wrapped.markup)
        self.assertEqual(validate_ask_blocks(wrapped.markup), [])

    def test_default_id_not_in_options_fails(self) -> None:
        raw = _assembly(_decision_section(defaultId="missing"))
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("defaultId" in str(d) or "default_id" in str(d)
                            for d in ctx.exception.diagnostics))

    def test_default_id_and_no_default_reason_together_fail(self) -> None:
        raw = _assembly(_decision_section(noDefaultReason="判断材料が拮抗しているため"))
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("defaultId" in str(d) or "noDefaultReason" in str(d)
                            or "既定" in str(d)
                            for d in ctx.exception.diagnostics))

    def test_ask_id_with_quote_character_is_rejected(self) -> None:
        """The built document's id attribute round-trips through the DOM and
        is spliced into a CSS attribute selector by the fixed decision-panel
        binder script; a quote in the id breaks that selector's syntax at
        runtime, so the id shape must be rejected up front at validation.
        """
        raw = _assembly(_decision_section(id='sec-ask"decision'))
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("ask.id" in str(d) for d in ctx.exception.diagnostics))

    def test_option_id_with_quote_character_is_rejected(self) -> None:
        raw = _assembly(_decision_section(
            options=[
                {"id": 'opt"a', "label": "A", "tradeoff": "t1"},
                {"id": "opt-b", "label": "B", "tradeoff": "t2"},
            ],
            defaultId="opt-b",
        ))
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("options" in str(d) for d in ctx.exception.diagnostics))

    def test_ask_id_with_trailing_newline_is_rejected(self) -> None:
        """Python's ``$`` anchor matches just before a string-final newline
        under ``re.match``, so a naive safe-token check using ``match``
        would accept 'sec-ask-decision\\n' as if the trailing newline were
        not there. IR authoring must reject it up front.
        """
        raw = _assembly(_decision_section(id="sec-ask-decision\n"))
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("ask.id" in str(d) for d in ctx.exception.diagnostics))

    def test_option_id_with_trailing_newline_is_rejected(self) -> None:
        """Same trailing-newline gap as the ask id, but on an option id."""
        raw = _assembly(_decision_section(
            options=[
                {"id": "opt-a\n", "label": "A", "tradeoff": "t1"},
                {"id": "opt-b", "label": "B", "tradeoff": "t2"},
            ],
            defaultId="opt-b",
        ))
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("options" in str(d) for d in ctx.exception.diagnostics))

    def test_request_static_output_passes_ask_inspector(self) -> None:
        raw = _assembly({
            "kind": "ask",
            "id": "sec-ask-request",
            "askType": "request",
            "steps": [
                {"role": "user", "roleLabel": "あなた", "text": "specをレビューする"},
                {"role": "agent", "roleLabel": "Claude", "text": "planを執筆する"},
            ],
        })
        req = validate_assembly(raw)
        section = next(s for s in req.sections if isinstance(s, AskSection))
        self.assertEqual(section.ask_type, "request")
        self.assertEqual(len(section.steps), 2)

        wrapped = render_ask(section)
        self.assertIn('data-ve-section-kind="ask"', wrapped.markup)
        self.assertIn('data-ve-ask-type="request"', wrapped.markup)
        self.assertIn('class="ask" data-ask="request"', wrapped.markup)
        self.assertIn("お願いする動作", wrapped.markup)
        self.assertIn('class="ask-steps"', wrapped.markup)
        self.assertIn('data-ask-role="user"', wrapped.markup)
        self.assertIn('data-ask-role-label="あなた"', wrapped.markup)
        self.assertIn('data-ask-role="agent"', wrapped.markup)
        self.assertEqual(validate_ask_blocks(wrapped.markup), [])

    def test_hypothesis_static_output_passes_ask_inspector(self) -> None:
        raw = _assembly({
            "kind": "ask",
            "id": "sec-ask-hypothesis",
            "askType": "hypothesis",
            "claim": {"text": "見出しだけで判断できる", "certainty": "inferred"},
            "verify": "検証方法: 見出し列のみで判断内容を言えるか確認する",
        })
        req = validate_assembly(raw)
        section = next(s for s in req.sections if isinstance(s, AskSection))
        self.assertEqual(section.ask_type, "hypothesis")
        self.assertIsNotNone(section.claim)
        self.assertEqual(section.claim.text, "見出しだけで判断できる")
        self.assertEqual(section.claim.certainty, "inferred")
        self.assertEqual(section.verify, "検証方法: 見出し列のみで判断内容を言えるか確認する")

        wrapped = render_ask(section)
        self.assertIn('data-ve-section-kind="ask"', wrapped.markup)
        self.assertIn('data-ve-ask-type="hypothesis"', wrapped.markup)
        self.assertIn('class="ask" data-ask="hypothesis"', wrapped.markup)
        self.assertIn("検証待ちの仮説", wrapped.markup)
        self.assertIn('class="ask-claim"', wrapped.markup)
        self.assertIn('class="certainty inferred"', wrapped.markup)
        self.assertIn("推論", wrapped.markup)
        self.assertIn('class="ask-verify"', wrapped.markup)
        self.assertEqual(validate_ask_blocks(wrapped.markup), [])

    def test_decision_without_default_renders_no_default_reason(self) -> None:
        section = AskSection(
            id="sec-ask-no-default",
            ask_type="decision",
            question="どちらにしますか？",
            options=(
                AskOption(id="a", label="案A", tradeoff="コスト増"),
                AskOption(id="b", label="案B", tradeoff="効果遅延"),
            ),
            no_default_reason="判断材料が拮抗しているため",
        )
        wrapped = render_ask(section)
        self.assertNotIn("data-ask-default", wrapped.markup)
        self.assertIn('class="ask-no-default-reason"', wrapped.markup)
        self.assertIn("判断材料が拮抗しているため", wrapped.markup)
        self.assertEqual(validate_ask_blocks(wrapped.markup), [])

    def test_build_document_includes_decision_ask(self) -> None:
        html = build_document(
            _assembly(_decision_section()),
            REGISTRY,
            TRUSTED_RENDERERS,
            SKELETON,
            COMPONENTS_DIR,
            document_path="doc.html",
        )
        self.assertIn('data-ve-section-kind="ask"', html)
        self.assertIn('data-ve-ask-type="decision"', html)
        self.assertIn('id="sec-ask-decision"', html)
        self.assertIn('data-ask="decision"', html)
        self.assertIn("注釈を今回に含めますか？", html)
        self.assertIn("data-ask-default", html)

    def test_decision_options_carry_option_ids(self) -> None:
        section = AskSection(id="ask-1", ask_type="decision", question="どちらにしますか。",
                             options=(AskOption("opt-a", "案A", "早いが粗い"),
                                      AskOption("opt-b", "案B", "遅いが確実")),
                             default_id="opt-b")
        wrapped = render_ask(section)
        self.assertIn('data-ask-option data-ask-option-id="opt-a"', wrapped.markup)
        self.assertIn('data-ask-option-id="opt-b" data-ask-default', wrapped.markup.replace("data-ask-option ", ""))

    def test_decision_renders_static_memo_field(self) -> None:
        section = AskSection(id="ask-1", ask_type="decision", question="どちらにしますか。",
                             options=(AskOption("opt-a", "案A", "早いが粗い"),
                                      AskOption("opt-b", "案B", "遅いが確実")),
                             default_id="opt-b")
        wrapped = render_ask(section)
        self.assertIn('<textarea data-ask-memo></textarea>', wrapped.markup)
        self.assertIn('メモ（この判断について）', wrapped.markup)

    def test_digest_ids_cannot_collide_across_field_boundaries(self) -> None:
        from ve_components.document_sections import compute_ask_digest_from_pairs
        self.assertNotEqual(
            compute_ask_digest_from_pairs((("ask-1", ("a,b",)),)),
            compute_ask_digest_from_pairs((("ask-1", ("a", "b")),)))
        self.assertNotEqual(
            compute_ask_digest_from_pairs((("ask-1=a", ("b",)),)),
            compute_ask_digest_from_pairs((("ask-1", ("a", "b")),)))

    def test_digest_depends_only_on_decision_contract(self) -> None:
        from ve_components.document_sections import compute_ask_digest
        base = (AskSection(id="ask-1", ask_type="decision", question="Q。",
                           options=(AskOption("a", "A", "t"), AskOption("b", "B", "t")),
                           no_default_reason="理由"),)
        with_request = base + (AskSection(id="ask-2", ask_type="request",
                                          steps=(AskStep("user", "あなた", "確認する"),)),)
        self.assertEqual(compute_ask_digest(base), compute_ask_digest(with_request))
        changed = (AskSection(id="ask-1", ask_type="decision", question="Q。",
                              options=(AskOption("a", "A", "t"), AskOption("c", "C", "t")),
                              no_default_reason="理由"),)
        self.assertNotEqual(compute_ask_digest(base), compute_ask_digest(changed))

    def test_render_escapes_html(self) -> None:
        section = AskSection(
            id="sec-x",
            ask_type="decision",
            question="<script>alert(1)</script>",
            options=(
                AskOption(id="a", label="<b>A</b>", tradeoff="<i>t</i>"),
                AskOption(id="b", label="B", tradeoff="u"),
            ),
            default_id="a",
        )
        wrapped = render_ask(section)
        self.assertIn("&lt;script&gt;", wrapped.markup)
        self.assertIn("&lt;b&gt;A&lt;/b&gt;", wrapped.markup)
        self.assertNotIn("<script>", wrapped.markup)
        self.assertNotIn("<b>A</b>", wrapped.markup)


if __name__ == "__main__":
    unittest.main()
