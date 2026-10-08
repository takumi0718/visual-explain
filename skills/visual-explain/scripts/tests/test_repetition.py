"""Build-time repetition gate: the same claim must not be restated."""
from __future__ import annotations

import copy
import unittest
from pathlib import Path

from build_explainer import build_document
from first_screen_ir import CANONICAL, assembly as _assembly, decision_ask, messages as _msgs, narr as _narr
from ve_components.metrics import text_metrics, visible_chars
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.repetition import bigram_jaccard, chars_before_first_figure, normalize_sentence
from ve_components.validation import validate_assembly

SKILL = Path(__file__).resolve().parents[2]
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS = SKILL / "assets" / "components"
REGISTRY = load_registry(COMPONENTS / "registry.json")
SENTENCE = "これは説明用の想定であり実在の状況ではありません。"


def _compat(markup: str) -> dict:
    return {"kind": "compatibility", "id": "sec-c", "markup": markup,
            "provenance": {"source": "legacy-html-insertion", "reason": "unmigrated-format", "format": "layers"}}


class HelpersTest(unittest.TestCase):
    def test_jaccard_identical_is_one(self) -> None:
        self.assertEqual(bigram_jaccard("限定公開で始める", "限定公開で始める"), 1.0)

    def test_normalize_strips_punctuation_and_space(self) -> None:
        self.assertEqual(normalize_sentence("限定 公開、で始める。"), "限定公開で始める")


class RepetitionGateTest(unittest.TestCase):
    def test_h2_and_claim_restated(self) -> None:
        body = '<p class="claim">部門別に確認すると限定公開の影響は判断できない。<span class="certainty unverified">未確認</span></p>'
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "部門別に確認する限り限定公開の影響は判断できない", body))
        self.assertIn("見出しと主張行がほぼ同じ文です（sec-a）。主張行を削るか、見出しと別の情報を書いてください", _msgs(raw))

    def test_distinct_claim_passes(self) -> None:
        body = '<p class="claim">請求と通知が別の顧客群を指していた事例が過去に2件ある。</p>'
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "部門別の確認では影響を判断できない", body))
        self.assertEqual(_msgs(raw), [])

    def test_caption_restates_previous_h2(self) -> None:
        canon = copy.deepcopy(CANONICAL)
        canon["ir"]["caption"] = "限定公開だけが影響確認の機会を残しつつ改定を進められる。"
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "限定公開だけが影響確認の機会を残しつつ改定を進められる", "<p>補足。</p>"), canon)
        self.assertIn("図のキャプションが直前の見出しの言い換えです（sec-map）。キャプションには「何を見るか」を書いてください",
                      _msgs(raw))

    def test_duplicate_sentence(self) -> None:
        sentence = "これは説明用の想定であり実在の状況ではありません。"
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "背景", f"<p>{sentence}</p>"),
                        _narr("sec-b", "前提", f"<p>{sentence}</p>"))
        self.assertIn("同じ文が2回出てきます: 「これは説明用の想定であり実在の状況ではありません。」", _msgs(raw))

    def test_too_much_text_before_first_figure(self) -> None:
        long_body = "<p>" + "あ" * 120 + "。</p><p>" + "い" * 100 + "。</p>"
        raw = _assembly({"conclusion": "限定対象で開始する。"}, _narr("sec-a", "背景", long_body), CANONICAL)
        self.assertIn("最初の図より前の本文が224字あります（上限200字）", _msgs(raw))

    def test_figureless_document_is_not_limited(self) -> None:
        long_body = "<p>" + "あ" * 300 + "。</p>"
        raw = _assembly({"conclusion": "限定対象で開始する。"}, _narr("sec-a", "背景", long_body))
        self.assertEqual(_msgs(raw), [])


class ParserGapTest(unittest.TestCase):
    def test_badge_on_non_span_does_not_hide_later_text(self) -> None:
        body = f'<p>前置き<strong class="certainty inferred">推論</strong></p><p>{SENTENCE}</p>'
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "背景", body), _narr("sec-b", "前提", f"<p>{SENTENCE}</p>"))
        self.assertIn(f"同じ文が2回出てきます: 「{SENTENCE}」", _msgs(raw))

    def test_omitted_end_tags_still_count(self) -> None:
        body = f"<ul><li>{SENTENCE}<li>別の項目です。</ul>"
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "背景", body), _narr("sec-b", "前提", f"<p>{SENTENCE}</p>"))
        self.assertIn(f"同じ文が2回出てきます: 「{SENTENCE}」", _msgs(raw))

    def test_unterminated_duplicate_is_caught(self) -> None:
        item = "請求計算と告知対象の照合手順"
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "背景", f"<ul><li>{item}</li></ul>"),
                        _narr("sec-b", "前提", f"<ul><li>{item}</li></ul>"))
        self.assertIn(f"同じ文が2回出てきます: 「{item}」", _msgs(raw))

    def test_compatibility_figure_caption_counts(self) -> None:
        compat = _compat(f'<figure class="figure"><figcaption>{SENTENCE}</figcaption><p>図</p></figure>')
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "背景", f"<p>{SENTENCE}</p>"), compat)
        self.assertIn(f"同じ文が2回出てきます: 「{SENTENCE}」", _msgs(raw))

    def test_heading_is_forgotten_after_a_figure(self) -> None:
        heading = "限定公開だけが影響確認の機会を残しつつ改定を進められる"
        canon = copy.deepcopy(CANONICAL)
        canon["ir"]["caption"] = heading + "。"
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", heading, "<p>補足。</p>"),
                        _compat('<figure class="figure"><figcaption>承認の流れ。</figcaption><p>図</p></figure>'),
                        canon)
        self.assertNotIn("図のキャプションが直前の見出しの言い換えです（sec-map）。キャプションには「何を見るか」を書いてください",
                         _msgs(raw))


class PreFigureCountParityTest(unittest.TestCase):
    def test_gate_and_report_count_the_same_text(self) -> None:
        body = ('<p class="claim">請求、告知、例外を<a href="https://example.com/a">同じ表</a>で照合する。'
                '<span class="certainty inferred">推論</span></p>')
        raw = _assembly({"conclusion": "限定対象で開始する。"}, _narr("sec-a", "背景", body),
                        decision_ask(), CANONICAL)
        request = validate_assembly(raw)
        html = build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS, document_path="x.html")
        gate = chars_before_first_figure(request.sections)
        self.assertGreater(gate, 0)
        self.assertEqual(gate, text_metrics(html).chars_before_figure)

    def test_ask_card_labels_are_chrome_not_body(self) -> None:
        # 93 visible chars of prose, then a two-option card, then a figure: the
        # card's fixed labels (kind, 根拠:/利点:/代償:, 推奨, 補足) must not push
        # the document over the 200-char limit.
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "背景", "<p>" + "あ" * 90 + "。</p>"),
                        decision_ask(), CANONICAL)
        request = validate_assembly(raw)
        self.assertEqual(visible_chars(request.sections[1].markup), 93)
        self.assertEqual(_msgs(raw), [])
        html = build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS, document_path="x.html")
        self.assertEqual(chars_before_first_figure(request.sections), text_metrics(html).chars_before_figure)

    def test_ask_prefix_text_is_skipped_by_the_counter(self) -> None:
        self.assertEqual(visible_chars('<p>ab<span class="ask-prefix">根拠:</span> cd</p>'), 4)
        self.assertEqual(visible_chars('<p class="ask-kind">判断してください</p><p>x</p>'), 1)
        self.assertEqual(visible_chars('<div class="ask-memo"><label>補足<textarea></textarea></label></div>y'), 1)


if __name__ == "__main__":
    unittest.main()
