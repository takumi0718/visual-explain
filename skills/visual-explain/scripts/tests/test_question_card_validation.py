"""問いカード（decision ask）の IR 契約: 利点・代償・根拠・推奨・取り下げ・4問上限。"""
from __future__ import annotations

import unittest

from first_screen_ir import CANONICAL, assembly, decision_ask, messages

_PILOT = {"id": "pilot", "label": "試験導入だけする", "benefit": "学びが早い",
          "tradeoff": "効果が見えにくい", "withdrawn": True}


def _one(ask: dict) -> list[str]:
    return messages(assembly({"conclusion": "限定対象で開始する。"}, ask))


class QuestionCardValidationTest(unittest.TestCase):
    def test_valid_card_passes(self) -> None:
        self.assertEqual(_one(decision_ask()), [])

    def test_non_recommended_option_without_benefit_fails(self) -> None:
        ask = decision_ask()
        del ask["options"][1]["benefit"]
        self.assertEqual(_one(ask), ["推奨でない選択肢 'all' にも benefit（選ぶ理由）が必要です"])

    def test_recommended_option_without_benefit_fails(self) -> None:
        ask = decision_ask()
        del ask["options"][0]["benefit"]
        self.assertEqual(_one(ask), ["decision.options[].benefit は空にできません"])

    def test_blank_tradeoff_fails(self) -> None:
        ask = decision_ask()
        ask["options"][1]["tradeoff"] = " "
        self.assertEqual(_one(ask), ["decision.options[].tradeoff は空にできません"])

    def test_missing_evidence_fails(self) -> None:
        ask = decision_ask()
        del ask["evidence"]
        self.assertEqual(_one(ask), ["decision.evidence は空にできません（file:line か実行結果の引用）"])

    def test_evidence_without_location_or_quote_fails(self) -> None:
        self.assertEqual(_one(decision_ask(evidence="たぶん大丈夫")),
                         ["decision.evidence には file:line か「」で囲んだ実行結果の引用が必要です"])

    def test_evidence_accepts_file_line_and_run_quote(self) -> None:
        for evidence in ("ve_components/validation.py:2925", "pytest の結果「1224 passed」"):
            self.assertEqual(_one(decision_ask(evidence=evidence)), [], evidence)

    def test_evidence_over_200_chars_fails(self) -> None:
        self.assertEqual(_one(decision_ask(evidence="a.py:1 " + "あ" * 200)),
                         ["decision.evidence は200字以内です（207字）"])

    def test_no_default_reason_is_retired(self) -> None:
        ask = decision_ask()
        del ask["defaultId"]
        ask["noDefaultReason"] = "判断材料が拮抗しているため"
        self.assertEqual(_one(ask), [
            "decision.noDefaultReason は廃止されました。推奨案を defaultId で示してください",
            "decision には推奨案の defaultId が必要です",
        ])

    def test_missing_default_fails(self) -> None:
        ask = decision_ask()
        del ask["defaultId"]
        self.assertEqual(_one(ask), ["decision には推奨案の defaultId が必要です"])

    def test_withdrawn_option_is_accepted(self) -> None:
        ask = decision_ask()
        ask["options"].append(dict(_PILOT))
        self.assertEqual(_one(ask), [])

    def test_withdrawn_must_be_boolean(self) -> None:
        ask = decision_ask()
        ask["options"][1]["withdrawn"] = "yes"
        self.assertEqual(_one(ask), ["decision.options[].withdrawn は true / false のいずれかです"])

    def test_default_cannot_point_to_withdrawn(self) -> None:
        ask = decision_ask(default="pilot")
        ask["options"].append(dict(_PILOT))
        self.assertEqual(_one(ask), ["decision.defaultId は取り下げた選択肢を指せません"])

    def test_fewer_than_two_active_options_fails(self) -> None:
        ask = decision_ask()
        ask["options"][1]["withdrawn"] = True
        self.assertEqual(_one(ask), ["decision の取り下げていない選択肢は2件以上必要です"])

    def test_four_decision_asks_pass_and_five_fail(self) -> None:
        def doc(n: int) -> dict:
            asks = [decision_ask(f"sec-q{i}", question=f"問い{i}を選びますか？") for i in range(1, n + 1)]
            first = {"conclusion": "限定対象で開始する。",
                     "overview": {"section": "sec-map",
                                  "markers": [{"n": 1, "label": "最初の問い", "target": "sec-q1"}]}}
            return assembly(first, CANONICAL, *asks)
        self.assertEqual(messages(doc(4)), [])
        self.assertEqual(messages(doc(5)), ["decision ask は1資料4問までです（5問）"])

    def test_parsed_section_carries_card_fields(self) -> None:
        from ve_components.model import AskSection
        from ve_components.validation import validate_assembly
        ask = decision_ask()
        ask["options"].append(dict(_PILOT))
        request = validate_assembly(assembly({"conclusion": "限定対象で開始する。"}, ask))
        card = next(s for s in request.sections if isinstance(s, AskSection))
        self.assertEqual(card.evidence, "scripts/build_explainer.py:1")
        self.assertEqual([(o.id, o.benefit, o.withdrawn) for o in card.options], [
            ("limited", "影響範囲を絞れる", False),
            ("all", "切替が一度で済む", False),
            ("pilot", "学びが早い", True),
        ])


if __name__ == "__main__":
    unittest.main()
