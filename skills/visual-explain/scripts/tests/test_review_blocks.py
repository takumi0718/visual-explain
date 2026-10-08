"""指摘層のブロック番号: ビルドの付与と checker の再計算が同じ規則で一致する。"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from build_explainer import build_document
from first_screen_ir import assembly, decision_ask, messages, narr
from ve_components.checker import check_final_document
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.document_checks import check_document_structure
from ve_components.review_blocks import check_review_blocks, stamp_review_blocks

SKILL = Path(__file__).resolve().parents[2]
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS = SKILL / "assets" / "components"
REGISTRY = load_registry(COMPONENTS / "registry.json")
TAGS = "p / h2 / h3 / li / figure / blockquote / pre / table"


def _msgs(content: str) -> list[str]:
    return [d.message for d in check_review_blocks(content)]


def _build(raw: dict) -> str:
    return build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS, document_path="x.html")


class StampTest(unittest.TestCase):
    def test_attribute_goes_before_closing_bracket(self) -> None:
        self.assertEqual(stamp_review_blocks('<p class="x">a</p><h2>b</h2>'),
                         ('<p class="x" data-ve-blk="1">a</p><h2 data-ve-blk="2">b</h2>', 3))

    def test_start_offset(self) -> None:
        self.assertEqual(stamp_review_blocks("<p>a</p>", start=5), ('<p data-ve-blk="5">a</p>', 6))

    def test_nested_list_items_in_dom_order(self) -> None:
        stamped, _ = stamp_review_blocks("<ul><li>a<ul><li>b</li></ul></li><li>c</li></ul>")
        self.assertEqual(re.findall(r'data-ve-blk="(\d+)"', stamped), ["1", "2", "3"])

    def test_figure_is_one_block(self) -> None:
        stamped, _ = stamp_review_blocks(
            "<figure><table><tr><td><p>x</p></td></tr></table><figcaption>c</figcaption></figure><p>y</p>")
        self.assertEqual(stamped,
                         '<figure data-ve-blk="1"><table><tr><td><p>x</p></td></tr></table>'
                         '<figcaption>c</figcaption></figure><p data-ve-blk="2">y</p>')

    def test_stepper_subtree_is_not_numbered(self) -> None:
        markup = '<div data-stepper><div data-step="1"><figure>f</figure><p class="ve-seq-next">n</p></div></div>'
        self.assertEqual(stamp_review_blocks(markup), (markup, 1))

    def test_question_card_ui_parts_are_skipped(self) -> None:
        markup = (
            '<div class="ask" data-ask="decision"><p class="ask-kind">判断してください</p>'
            '<p class="ask-question">Q？</p><ul class="ask-options">'
            '<li data-ask-option data-ask-option-id="a"><span>A</span></li></ul>'
            '<div class="ask-memo"><label>補足<textarea data-ask-memo></textarea></label></div></div>')
        stamped, nxt = stamp_review_blocks(markup)
        self.assertEqual(nxt, 2)
        self.assertIn('<p class="ask-question" data-ve-blk="1">', stamped)
        self.assertIn('<p class="ask-kind">', stamped)
        self.assertIn('<li data-ask-option data-ask-option-id="a">', stamped)

    def test_collection_panel_is_skipped(self) -> None:
        markup = '<section data-ve-section-kind="decision-panel"><h2>回収</h2><p>x</p></section>'
        self.assertEqual(stamp_review_blocks(markup), (markup, 1))


class CheckTest(unittest.TestCase):
    def test_contiguous_numbers_pass(self) -> None:
        self.assertEqual(_msgs('<p data-ve-blk="1">a</p><p data-ve-blk="2">b</p>'), [])

    def test_missing_number(self) -> None:
        self.assertEqual(_msgs('<p data-ve-blk="1">a</p><p>b</p>'),
                         ["data-ve-blk は1からの連番である必要があります（2 番目のブロックが なし）"])

    def test_duplicate_number(self) -> None:
        self.assertEqual(_msgs('<p data-ve-blk="1">a</p><p data-ve-blk="1">b</p>'),
                         ["data-ve-blk は1からの連番である必要があります（2 番目のブロックが 1）"])

    def test_gap_reports_first_mismatch_only(self) -> None:
        self.assertEqual(_msgs('<p data-ve-blk="1">a</p><p data-ve-blk="3">b</p><p data-ve-blk="4">c</p>'),
                         ["data-ve-blk は1からの連番である必要があります（2 番目のブロックが 3）"])

    def test_wrong_tag(self) -> None:
        self.assertEqual(_msgs('<div data-ve-blk="1">a</div>'),
                         [f"data-ve-blk は {TAGS} にだけ付けられます: <div>"])

    def test_excluded_position(self) -> None:
        self.assertEqual(
            _msgs('<section data-ve-section-kind="decision-panel"><p data-ve-blk="1">x</p></section>'),
            ["data-ve-blk を付けられない位置にあります: <p>"])


class BuildTest(unittest.TestCase):
    def test_built_document_numbers_blocks_from_one(self) -> None:
        html = _build(assembly({"conclusion": "限定対象で開始する。"}, narr("sec-a", "現状の確認"), decision_ask()))
        values = [int(v) for v in re.findall(r'data-ve-blk="(\d+)"', html)]
        self.assertEqual(values, list(range(1, len(values) + 1)))
        self.assertIn('<p class="conclusion" data-ve-blk="1">', html)
        self.assertNotIn("<h1 data-ve-blk", html)
        self.assertEqual(check_final_document(html, SKELETON, REGISTRY, components_dir=COMPONENTS), [])

    def test_tampered_numbering_fails_final_check(self) -> None:
        html = _build(assembly({"conclusion": "限定対象で開始する。"}, narr("sec-a", "現状の確認")))
        tampered = html.replace(' data-ve-blk="2"', ' data-ve-blk="3"', 1)
        msgs = [d.message for d in check_final_document(tampered, SKELETON, REGISTRY, components_dir=COMPONENTS)]
        self.assertEqual(msgs, ["data-ve-blk は1からの連番である必要があります（2 番目のブロックが 3）"])

    def test_compatibility_cannot_carry_block_numbers(self) -> None:
        compat = {"kind": "compatibility", "id": "sec-c",
                  "markup": '<div class="figure"><p data-ve-blk="1">x</p></div>',
                  "provenance": {"source": "legacy-html-insertion", "reason": "unmigrated-format",
                                 "format": "layers"}}
        self.assertIn("compatibility に data-ve-blk は書けません（ビルドが付与します）",
                      messages(assembly({"conclusion": "限定対象で開始する。"}, compat)))


if __name__ == "__main__":
    unittest.main()


class StampEdgeCaseTest(unittest.TestCase):
    def test_unquoted_value_before_self_closing_slash_is_preserved(self) -> None:
        stamped, _ = stamp_review_blocks("<p class=x/>")
        self.assertEqual(stamped, '<p class=x/ data-ve-blk="1">')

    def test_quoted_self_closing_still_inserts_before_slash(self) -> None:
        stamped, _ = stamp_review_blocks('<p class="x"/>')
        self.assertEqual(stamped, '<p class="x" data-ve-blk="1"/>')

    def test_stray_blk_is_ignored_before_v3_and_reported_from_v3(self) -> None:
        stray, plain = '<p data-ve-blk="9">a</p>', "<p>a</p>"
        for version in (1, 2):
            self.assertEqual(
                check_document_structure(stray, title=None, skeleton_version=version),
                check_document_structure(plain, title=None, skeleton_version=version))
        self.assertNotEqual(
            check_document_structure(stray, title=None, skeleton_version=3),
            check_document_structure(plain, title=None, skeleton_version=3))
