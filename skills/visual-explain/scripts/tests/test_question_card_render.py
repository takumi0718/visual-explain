"""問いカードの描画: 推奨バッジ・利点/代償・根拠・取り下げ・補足欄。"""
from __future__ import annotations

import unittest
from pathlib import Path

from ve_components.checker import validate_ask_blocks
from ve_components.document_sections import render_ask
from ve_components.model import AskOption, AskSection

SKELETON = (Path(__file__).resolve().parents[2] / "assets" / "skeleton.html").read_text("utf-8")
STYLE = SKELETON.split("<style>", 1)[1].split("</style>", 1)[0]

CARD = AskSection(
    id="sec-ask-decision", ask_type="decision", question="限定対象で開始しますか？",
    options=(
        AskOption("limited", "限定対象で公開する", "運用が追加で必要", benefit="影響範囲を絞れる"),
        AskOption("all", "一斉公開する", "影響範囲が最初から広い", benefit="切替が一度で済む"),
        AskOption("pilot", "試験導入だけする", "効果が見えにくい", benefit="学びが早い", withdrawn=True),
    ),
    default_id="limited",
    evidence="scripts/build_explainer.py:1",
)


class QuestionCardRenderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.markup = render_ask(CARD).markup

    def test_recommended_option_has_badge_benefit_and_tradeoff(self) -> None:
        self.assertIn(
            '<li data-ask-option data-ask-option-id="limited" data-ask-default>'
            '<span class="ask-option-head"><span class="ask-option-label">限定対象で公開する</span>'
            '<span class="ask-badge">推奨</span></span>'
            '<span class="ask-benefit">利点: 影響範囲を絞れる</span>'
            '<span class="ask-tradeoff">代償: 運用が追加で必要</span></li>',
            self.markup)

    def test_other_option_has_no_badge(self) -> None:
        self.assertIn(
            '<li data-ask-option data-ask-option-id="all">'
            '<span class="ask-option-head"><span class="ask-option-label">一斉公開する</span></span>',
            self.markup)

    def test_withdrawn_option_is_marked(self) -> None:
        self.assertIn(
            '<li data-ask-option data-ask-option-id="pilot" data-ask-withdrawn>'
            '<span class="ask-option-head"><span class="ask-option-label">試験導入だけする</span>'
            '<span class="ask-withdrawn-note">取り下げ</span></span>',
            self.markup)

    def test_evidence_line_follows_question(self) -> None:
        self.assertIn(
            '<p class="ask-question">限定対象で開始しますか？</p>\n'
            '  <p class="ask-evidence">根拠: scripts/build_explainer.py:1</p>',
            self.markup)

    def test_memo_label_is_supplement(self) -> None:
        self.assertIn('<label>補足（任意）<textarea data-ask-memo></textarea></label>', self.markup)

    def test_card_passes_ask_inspector(self) -> None:
        self.assertEqual(validate_ask_blocks(self.markup), [])


class QuestionCardStyleTest(unittest.TestCase):
    def test_badge_uses_positive_tint(self) -> None:
        self.assertIn(
            ".ask-badge { padding: 0 var(--space-1); border-radius: 999px; color: var(--positive); "
            "background: color-mix(in srgb, var(--positive) 12%, var(--surface)); font-size: var(--fs-small); }",
            STYLE)

    def test_withdrawn_label_is_struck_through(self) -> None:
        self.assertIn(".ask-options [data-ask-withdrawn] .ask-option-label { text-decoration: line-through; }", STYLE)

    def test_legacy_default_marker_is_gone(self) -> None:
        self.assertNotIn('content: "既定案"', STYLE)

    def test_all_ask_cards_share_a_border(self) -> None:
        self.assertRegex(STYLE, r"\.ask \{[^}]*border: 1px solid var\(--border\);")


if __name__ == "__main__":
    unittest.main()
