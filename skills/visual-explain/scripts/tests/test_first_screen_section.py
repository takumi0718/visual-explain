"""first-screen v2: title h1, conclusion (1-3 sentences), optional overview."""
from __future__ import annotations

import unittest

from first_screen_ir import CANONICAL, assembly as _assembly, messages as _messages, narr as _narr
from ve_components.model import FirstScreenSection, Overview, OverviewMarker
from ve_components.validation import split_sentences, validate_assembly


class SplitSentencesTest(unittest.TestCase):
    def test_splits_on_terminators(self) -> None:
        self.assertEqual(split_sentences("限定で始める。前提は二つ！"), ("限定で始める。", "前提は二つ！"))

    def test_trailing_text_without_terminator_is_none(self) -> None:
        self.assertIsNone(split_sentences("限定で始める。前提は二つ"))

    def test_empty_sentence_is_none(self) -> None:
        self.assertIsNone(split_sentences("限定で始める。。"))


class ConclusionValidationTest(unittest.TestCase):
    def test_valid_conclusion_builds_section(self) -> None:
        request = validate_assembly(_assembly({"conclusion": "限定対象で開始する。撤回条件の合意が前提。"}))
        self.assertEqual(request.schema_version, 2)
        first = request.sections[0]
        self.assertIsInstance(first, FirstScreenSection)
        self.assertEqual(first.conclusion, "限定対象で開始する。撤回条件の合意が前提。")
        self.assertIsNone(first.overview)

    def test_four_sentences_rejected(self) -> None:
        self.assertIn("first-screen.conclusion は文末（。！？!?）で終わる1〜3文である必要があります",
                      _messages(_assembly({"conclusion": "一。二。三。四。"})))

    def test_long_sentence_rejected(self) -> None:
        long = "あ" * 80 + "。"
        self.assertIn("first-screen.conclusion の各文は80字以内です（81字）",
                      _messages(_assembly({"conclusion": long})))

    def test_legacy_decision_field_rejected(self) -> None:
        self.assertIn("未知のフィールド 'decision'",
                      _messages(_assembly({"conclusion": "決める。", "decision": "決めます。"})))

    def test_schema_version_1_rejected_with_migration_hint(self) -> None:
        raw = _assembly({"conclusion": "決める。"})
        raw["schemaVersion"] = 1
        self.assertIn("schemaVersion 1 は廃止されました（first-screen を conclusion / overview で書き直してください）",
                      _messages(raw))


class OverviewValidationTest(unittest.TestCase):
    def _first(self, **overview) -> dict:
        base = {"section": "sec-map", "markers": [{"n": 1, "label": "背景", "target": "sec-a"}]}
        base.update(overview)
        return {"conclusion": "限定対象で開始する。", "overview": base}

    def test_valid_overview(self) -> None:
        request = validate_assembly(_assembly(self._first(), CANONICAL, _narr("sec-a", "背景の見出し")))
        self.assertEqual(request.sections[0].overview,
                         Overview(section="sec-map", markers=(OverviewMarker(1, "背景", "sec-a"),)))

    def test_overview_must_point_at_next_canonical(self) -> None:
        msgs = _messages(_assembly(self._first(), _narr("sec-a", "背景の見出し"), CANONICAL))
        self.assertIn("first-screen.overview.section は first-screen 直後の canonical セクションの id である必要があります",
                      msgs)

    def test_marker_target_must_be_linkable(self) -> None:
        first = self._first(markers=[{"n": 1, "label": "図", "target": "sec-map"}])
        self.assertIn("first-screen.overview.markers[0].target 'sec-map' は ask / narrative / closing セクションの id である必要があります",
                      _messages(_assembly(first, CANONICAL)))

    def test_narrative_marker_target_needs_a_heading_for_the_echo(self) -> None:
        headless = {"kind": "narrative", "id": "sec-a", "markup": "<p>見出しの無い本文。</p>"}
        self.assertIn("first-screen.overview.markers[0].target 'sec-a' の narrative には番号を付ける h2 か h3 が必要です",
                      _messages(_assembly(self._first(), CANONICAL, headless)))

    def test_narrative_with_only_an_h3_is_a_valid_marker_target(self) -> None:
        h3_only = {"kind": "narrative", "id": "sec-a", "markup": "<h3>小見出し</h3><p>本文。</p>"}
        self.assertEqual(_messages(_assembly(self._first(), CANONICAL, h3_only)), [])

    def test_marker_n_must_be_real_int(self) -> None:
        for bad in (True, 1.0):
            first = self._first(markers=[{"n": bad, "label": "背景", "target": "sec-a"}])
            self.assertIn("first-screen.overview.markers[].n は整数である必要があります",
                          _messages(_assembly(first, CANONICAL, _narr("sec-a", "背景の見出し"))))

    def test_markers_must_be_sequential(self) -> None:
        first = self._first(markers=[{"n": 2, "label": "背景", "target": "sec-a"}])
        self.assertIn("first-screen.overview.markers の n は1からの連番である必要があります",
                      _messages(_assembly(first, CANONICAL, _narr("sec-a", "背景の見出し"))))

    def test_bad_marker_n_is_reported_once(self) -> None:
        first = self._first(markers=[{"n": "1", "label": "背景", "target": "sec-a"},
                                     {"n": 2, "label": "決定", "target": "sec-a"}])
        msgs = _messages(_assembly(first, CANONICAL, _narr("sec-a", "背景の見出し")))
        self.assertIn("first-screen.overview.markers[].n は整数である必要があります", msgs)
        self.assertNotIn("first-screen.overview.markers の n は1からの連番である必要があります", msgs)

    def test_overview_required_with_three_headed_sections(self) -> None:
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "一つ目の見出し"), _narr("sec-b", "二つ目の見出し"), _narr("sec-c", "三つ目の見出し"))
        self.assertIn("h2 節または ask が3つ以上ある資料では first-screen.overview が必要です", _messages(raw))

    def test_overview_not_required_with_h3_only_narratives(self) -> None:
        def h3(sid: str) -> dict:
            return {"kind": "narrative", "id": sid,
                    "markup": f'<section aria-labelledby="{sid}-h"><h3 id="{sid}-h">小見出し{sid}</h3><p>本文。</p></section>'}
        raw = _assembly({"conclusion": "限定対象で開始する。"}, h3("sec-a"), h3("sec-b"), h3("sec-c"))
        self.assertNotIn("h2 節または ask が3つ以上ある資料では first-screen.overview が必要です", _messages(raw))


if __name__ == "__main__":
    unittest.main()
