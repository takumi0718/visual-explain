"""Phase 4: a decision option may carry a small grid-diagram picture of what it looks like."""
from __future__ import annotations

import copy
import re
import unittest
from pathlib import Path

from build_explainer import build_document
from first_screen_ir import CANONICAL
from ve_components.checker import check_final_document
from ve_components.diagnostics import ContractError
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.validation import validate_assembly

SKILL = Path(__file__).resolve().parents[2]
COMPONENTS = SKILL / "assets" / "components"
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
REGISTRY = load_registry(COMPONENTS / "registry.json")

LIMITED = {
    "grid": {"cols": 3, "rows": 1},
    "nodes": [
        {"id": "limited", "label": "限定対象で公開", "cell": [1, 1], "tone": "primary"},
        {"id": "check", "label": "影響を確認", "cell": [2, 1]},
        {"id": "expand", "label": "全顧客へ拡大", "cell": [3, 1]},
    ],
    "edges": [{"id": "e1", "from": "limited", "to": "check"}, {"id": "e2", "from": "check", "to": "expand"}],
}
ALL = {
    "grid": {"cols": 3, "rows": 1},
    "nodes": [
        {"id": "all", "label": "全顧客へ一斉公開", "cell": [1, 1], "span": [2, 1], "tone": "primary"},
        {"id": "risk", "label": "誤りも全体へ", "cell": [3, 1], "tone": "warning"},
    ],
    "edges": [{"id": "e1", "from": "all", "to": "risk"}],
}


def assembly() -> dict:
    return {
        "schemaVersion": 2,
        "document": {"id": "thumbs", "title": "公開範囲の判断", "summary": "選択肢ごとの公開の形を図で比べる。",
                     "type": "system", "profile": "strict"},
        "sections": [
            {"kind": "first-screen", "id": "sec-first", "conclusion": "限定対象から公開を始める。"},
            {"kind": "ask", "id": "sec-ask", "askType": "decision",
             "question": "どの範囲から公開しますか？",
             "evidence": "照合シートの試算「契約例外 12 件のうち 9 件が同じ顧客群に集中」",
             "defaultId": "limited",
             "options": [
                 {"id": "limited", "label": "限定対象で段階公開する", "benefit": "影響を限定できる",
                  "tradeoff": "運用が増える", "figure": copy.deepcopy(LIMITED)},
                 {"id": "all", "label": "全顧客へ一斉公開する", "benefit": "切替が一度で済む",
                  "tradeoff": "誤りが全体に及ぶ", "figure": copy.deepcopy(ALL)},
             ]},
            {"kind": "closing", "id": "sec-closing",
             "blocks": [{"heading": "限界・確度", "items": ["説明用の想定です。"]}]},
        ],
    }


def build(raw: dict) -> str:
    return build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS, document_path="thumbs.html")


def check(html: str) -> list[str]:
    return [d.message for d in check_final_document(html, SKELETON, REGISTRY, components_dir=COMPONENTS)]


def errors(raw: dict) -> list[str]:
    with unittest.TestCase().assertRaises(ContractError) as ctx:
        validate_assembly(raw)
    return [d.message for d in ctx.exception.diagnostics]


class ThumbnailValidationTest(unittest.TestCase):
    def test_option_figure_is_parsed(self) -> None:
        request = validate_assembly(assembly())
        ask = request.sections[1]
        self.assertEqual([o.figure.cols for o in ask.options], [3, 3])

    def test_option_figure_is_three_by_three_at_most(self) -> None:
        raw = assembly()
        raw["sections"][1]["options"][0]["figure"]["grid"] = {"cols": 4, "rows": 1}
        self.assertIn("grid.cols と grid.rows は1〜3の整数です", errors(raw))

    def test_pictures_go_on_every_live_option_or_none(self) -> None:
        raw = assembly()
        del raw["sections"][1]["options"][1]["figure"]
        self.assertIn("選択肢の図は、取り下げていない選択肢すべてに付ける必要があります", errors(raw))
        raw["sections"][1]["options"].append({"id": "hold", "label": "保留", "benefit": "影響なし",
                                              "tradeoff": "目的未達", "withdrawn": True})
        raw["sections"][1]["options"][1]["figure"] = copy.deepcopy(ALL)
        validate_assembly(raw)  # a withdrawn option needs no picture


class ThumbnailRenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = build(assembly())

    def test_document_passes_every_layer(self) -> None:
        self.assertEqual(check(self.html), [])

    def test_picture_sits_inside_its_option(self) -> None:
        self.assertRegex(self.html, re.compile(
            r'<li data-ask-option data-ask-option-id="limited" data-ask-default>.*?'
            r'<figure data-ve-component="grid-diagram" class="ve-gd ve-gd-thumb" data-ve-thumb'
            r' data-ve-grid="3x1" aria-label="限定対象で段階公開する の図">'
            r'<svg id="sec-ask-opt-1-svg" class="ve-gd-svg ve-gd-cols-3" viewBox="0 0 450 96"', re.S))
        self.assertIn('<svg id="sec-ask-opt-2-svg"', self.html)

    def test_picture_has_no_semantic_ids_or_review_numbers(self) -> None:
        figures = re.findall(r'<figure data-ve-component="grid-diagram" class="ve-gd ve-gd-thumb".*?</figure>',
                             self.html, re.S)
        self.assertEqual(len(figures), 2)
        for figure in figures:
            self.assertNotIn("data-ve-semantic-id", figure)
            self.assertNotIn("data-ve-blk", figure)

    def test_stylesheet_is_shipped_without_a_canonical_grid_diagram(self) -> None:
        self.assertIn('data-ve-component="grid-diagram" data-ve-contract-version="2" data-ve-asset="grid-diagram.css"',
                      self.html)
        self.assertEqual(self.html.count('data-ve-asset="grid-diagram.css"'), 1)

    def test_ask_id_with_quotes_and_spaces_still_passes(self) -> None:
        raw = assembly()
        raw["sections"][1]["id"] = '判断 "範囲"'
        html = build(raw)
        self.assertEqual(check(html), [])
        self.assertIn('<svg id="判断 &quot;範囲&quot;-opt-1-svg"', html)

    def test_svg_outside_a_picture_is_rejected(self) -> None:
        forged = self.html.replace('<p class="ask-question"', '<svg id="x"></svg><p class="ask-question"', 1)
        self.assertIn("選択肢の図の外に <svg> があります", check(forged))

    def test_picture_larger_than_three_by_three_is_rejected(self) -> None:
        forged = self.html.replace('data-ve-grid="3x1"', 'data-ve-grid="4x1"', 1)
        self.assertIn("選択肢の図は3×3以内の grid-diagram である必要があります", check(forged))

    def test_picture_svg_keeps_the_viewbox_rule(self) -> None:
        forged = self.html.replace('viewBox="0 0 450 96"', 'viewBox="0 0 450 90"', 1)
        self.assertIn("viewBox は '0 0 450 96' の完全一致である必要があります", check(forged))

    def test_picture_svg_id_follows_the_option(self) -> None:
        forged = self.html.replace('id="sec-ask-opt-1-svg"', 'id="other-svg"', 1)
        self.assertIn("選択肢の図の <svg> id は 'sec-ask-opt-<番号>-svg' の形である必要があります", check(forged))

    def test_picture_in_a_non_decision_ask_is_rejected(self) -> None:
        forged = self.html.replace('data-ve-ask-type="decision"', 'data-ve-ask-type="request"', 1)
        self.assertIn("選択肢の図は decision ask にだけ置けます", check(forged))

    def test_picture_without_a_grid_size_fails_closed(self) -> None:
        forged = self.html.replace(' data-ve-grid="3x1"', '', 1)
        self.assertIn("選択肢の図は3×3以内の grid-diagram である必要があります", check(forged))

    def test_picture_with_a_non_integer_coordinate_is_rejected(self) -> None:
        forged = re.sub(r'(<svg id="sec-ask-opt-1-svg".*?<rect [^>]*?\bx=")(\d+)"', r'\g<1>\2.5"', self.html, count=1, flags=re.S)
        self.assertNotEqual(forged, self.html)
        self.assertTrue(any("は整数である必要があります" in m for m in check(forged)))

    def test_picture_with_a_forbidden_attribute_is_rejected(self) -> None:
        start = self.html.index('<svg id="sec-ask-opt-1-svg"')
        at = self.html.index("<rect ", start)
        forged = self.html[:at] + '<rect onclick="x" ' + self.html[at + len("<rect "):]
        self.assertIn("<rect> に許可されていない属性 'onclick'", check(forged))

    def test_picture_svg_is_text_escaped(self) -> None:
        raw = assembly()
        raw["sections"][1]["options"][0]["figure"]["nodes"][0]["label"] = "A&B<c>"
        html = build(raw)
        self.assertEqual(check(html), [])
        self.assertIn("A&amp;B&lt;c&gt;", html)

    def test_withdrawn_option_may_keep_or_skip_its_picture(self) -> None:
        raw = assembly()
        raw["sections"][1]["options"].append({"id": "hold", "label": "保留", "benefit": "影響なし",
                                              "tradeoff": "目的未達", "withdrawn": True})
        html = build(raw)
        self.assertEqual(check(html), [])
        self.assertEqual(html.count('class="ve-gd ve-gd-thumb"'), 2)

    def test_pictures_do_not_count_as_text_before_the_first_figure(self) -> None:
        from ve_components.metrics import text_metrics
        from ve_components.repetition import chars_before_first_figure

        plain = assembly()
        for option in plain["sections"][1]["options"]:
            del option["figure"]
        with_pictures = assembly()
        for raw in (plain, with_pictures):
            raw["sections"].insert(2, copy.deepcopy(CANONICAL))
        counts = []
        for raw in (plain, with_pictures):
            gate = chars_before_first_figure(validate_assembly(raw).sections)
            report = text_metrics(build(raw)).chars_before_figure
            self.assertEqual(gate, report)
            counts.append(report)
        self.assertEqual(counts[0], counts[1])

    def test_generated_picture_ids_cannot_collide_with_a_section_id(self) -> None:
        raw = assembly()
        other = copy.deepcopy(raw["sections"][1])
        other["id"] = "sec-ask-opt-1-svg"
        other["question"] = "公開の順序はどちらにしますか？"
        other["evidence"] = "問い合わせ集計「公開後 7 日の問い合わせは 31 件」"
        for option in other["options"]:
            del option["figure"]
        raw["sections"].insert(2, other)
        with self.assertRaises(ContractError) as ctx:
            build(raw)
        self.assertIn("選択肢の図の id 'sec-ask-opt-1-svg' が他のセクション id と重複しています",
                      [d.message for d in ctx.exception.diagnostics])

    def test_picture_ids_cannot_collide_with_ids_a_canonical_figure_generates(self) -> None:
        import json
        raw = json.loads((SKILL / "examples" / "example-proposal.assembly.json").read_text("utf-8"))
        overview = raw["sections"][1]["ir"]
        overview["id"] = "sec-ask-decision-opt-1"
        raw["sections"][0]["overview"]["section"] = "sec-ask-decision-opt-1"
        with self.assertRaises(ContractError) as ctx:
            build(raw)
        self.assertIn("選択肢の図の id 'sec-ask-decision-opt-1-relations' が資料内の他の id と重複しています",
                      [d.message for d in ctx.exception.diagnostics])

    def test_picture_ids_cannot_collide_with_a_semantic_id(self) -> None:
        raw = assembly()
        canonical = copy.deepcopy(CANONICAL)
        canonical["ir"]["certainty"] = [{"id": "sec-ask-opt-2-svg", "level": "inferred",
                                         "statement": "説明用の想定です。"}]
        raw["sections"].insert(2, canonical)
        with self.assertRaises(ContractError) as ctx:
            build(raw)
        self.assertIn("選択肢の図の id 'sec-ask-opt-2-svg' が資料内の他の id と重複しています",
                      [d.message for d in ctx.exception.diagnostics])


if __name__ == "__main__":
    unittest.main()
