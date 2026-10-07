"""Build-time repetition gate: the same claim must not be restated."""
from __future__ import annotations

import copy
import unittest

from first_screen_ir import CANONICAL, assembly as _assembly, messages as _msgs, narr as _narr
from ve_components.repetition import bigram_jaccard, normalize_sentence


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


if __name__ == "__main__":
    unittest.main()
