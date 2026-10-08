"""Overview marker numbers echoed on the target section headings.

The build stamps ``data-ve-marker="n"`` on the heading of each section an
overview marker points to; the skeleton draws the number with CSS, so the
reader-facing text (copy, counts, accessible names) stays unchanged.
"""
from __future__ import annotations

import copy
import json
import re
import unittest
from decimal import Decimal
from pathlib import Path

from build_explainer import build_document
from ve_components.document_checks import check_document_structure
from ve_components.document_sections import mark_first_heading
from ve_components.metrics import text_metrics
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS

SKILL = Path(__file__).resolve().parents[2]
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS = SKILL / "assets" / "components"
REGISTRY = load_registry(COMPONENTS / "registry.json")
EXAMPLE = SKILL / "examples" / "example-proposal.assembly.json"
DOC_PATH = "skills/visual-explain/examples/example-proposal.html"


def _raw() -> dict:
    return json.loads(EXAMPLE.read_text("utf-8"), parse_float=Decimal)


def _build(raw: dict) -> str:
    return build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS, document_path=DOC_PATH)


def _content(html: str) -> str:
    begin = "<!-- VE-CONTROLLED:CONTENT:BEGIN -->"
    return html[html.index(begin) + len(begin):html.index("<!-- VE-CONTROLLED:CONTENT:END -->")]


class MarkFirstHeadingTest(unittest.TestCase):
    def test_marks_only_the_first_h2(self) -> None:
        out = mark_first_heading('<section><h2 id="a">A</h2><h2>B</h2></section>', 2)
        self.assertEqual(out, '<section><h2 data-ve-marker="2" id="a">A</h2><h2>B</h2></section>')

    def test_falls_back_to_h3_and_leaves_headless_markup(self) -> None:
        self.assertEqual(mark_first_heading("<p>x</p><h3>t</h3>", 1), '<p>x</p><h3 data-ve-marker="1">t</h3>')
        self.assertEqual(mark_first_heading("<p>x</p>", 1), "<p>x</p>")


class ExampleMarkersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = _build(_raw())

    def test_each_marker_target_heading_carries_its_number(self) -> None:
        content = _content(self.html)
        self.assertRegex(content, r'<h2 data-ve-marker="1" id="current-problem"')
        self.assertRegex(content, r'<h2 data-ve-marker="2" id="approval-map"')
        self.assertRegex(content, r'<p class="ask-question" data-ve-marker="3"')
        self.assertEqual(len(re.findall(r"data-ve-marker=", content)), 3)

    def test_skeleton_draws_the_number_like_the_overview_marker(self) -> None:
        self.assertIn("[data-ve-section-kind] [data-ve-marker]::before { content: attr(data-ve-marker);", SKELETON)

    def test_echoed_number_has_empty_alt_text_after_a_plain_fallback(self) -> None:
        plain = "content: attr(data-ve-marker); content: attr(data-ve-marker) / \"\";"
        self.assertIn(plain, SKELETON)

    def test_marker_number_is_not_counted_as_text(self) -> None:
        stripped = re.sub(r' data-ve-marker="\d+"', "", self.html)
        self.assertEqual(text_metrics(self.html), text_metrics(stripped))

    def test_closing_target_marks_its_first_h2(self) -> None:
        raw = _raw()
        raw["sections"][0]["overview"]["markers"][2]["target"] = "sec-closing"
        content = _content(_build(raw))
        self.assertRegex(content, r'<h2 data-ve-marker="3" data-ve-blk="\d+">リスクと弱い前提</h2>')


class MarkerCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.content = _content(_build(_raw()))

    def test_built_document_passes(self) -> None:
        self.assertEqual(check_document_structure(self.content, skeleton_version=4), [])

    def test_number_that_does_not_match_the_overview_is_rejected(self) -> None:
        forged = self.content.replace('data-ve-marker="2"', 'data-ve-marker="3"', 1)
        messages = [d.message for d in check_document_structure(forged, skeleton_version=4)]
        self.assertIn("論点番号 3 の印が、概要の番号 3 の飛び先ではない場所にあります", messages)

    def test_marker_outside_any_target_is_rejected(self) -> None:
        moved = self.content.replace(' data-ve-marker="1"', "", 1)
        forged = re.sub(r"<h3( data-ve-blk=\"\d+\">Before)", r'<h3 data-ve-marker="1"\1', moved, count=1)
        self.assertNotEqual(forged, moved)
        messages = [d.message for d in check_document_structure(forged, skeleton_version=4)]
        self.assertIn("論点番号 1 の印が、概要の番号 1 の飛び先ではない場所にあります", messages)

    def test_duplicate_marker_is_rejected(self) -> None:
        forged = self.content.replace('<p class="claim"', '<p class="claim" data-ve-marker="1"', 1)
        messages = [d.message for d in check_document_structure(forged, skeleton_version=4)]
        self.assertIn("論点番号 1 の印が複数あります", messages)


    def test_missing_echo_on_an_overview_target_is_rejected_from_v4(self) -> None:
        stripped = self.content.replace(' data-ve-marker="2"', "", 1)
        messages = [d.message for d in check_document_structure(stripped, skeleton_version=4)]
        self.assertIn("概要の番号 2 の飛び先に論点番号の印がありません", messages)
        older = [d.message for d in check_document_structure(stripped, skeleton_version=3)]
        self.assertNotIn("概要の番号 2 の飛び先に論点番号の印がありません", older)

    def test_echo_on_an_element_the_build_never_stamps_is_rejected_from_v4(self) -> None:
        moved = self.content.replace(' data-ve-marker="3"', "", 1)
        forged = moved.replace('<span class="ask-prefix">根拠:', '<span data-ve-marker="3" class="ask-prefix">根拠:', 1)
        self.assertNotEqual(forged, moved)
        messages = [d.message for d in check_document_structure(forged, skeleton_version=4)]
        self.assertIn("論点番号の印は h2 / h3 / p 以外の要素 <span> には付けられません", messages)
        older = [d.message for d in check_document_structure(forged, skeleton_version=3)]
        self.assertNotIn("論点番号の印は h2 / h3 / p 以外の要素 <span> には付けられません", older)


class AskMarkerTest(unittest.TestCase):
    """Request asks echo on .ask-kind, hypothesis asks on .ask-claim."""

    def _ask_html(self, ask_type: str) -> str:
        raw = _raw()
        if ask_type == "request":
            ask = {"kind": "ask", "id": "sec-ask-request", "askType": "request",
                   "steps": [{"role": "user", "roleLabel": "あなた", "text": "承認地図を確認する"}]}
            closing = next(i for i, s in enumerate(raw["sections"]) if s.get("kind") == "closing")
            raw["sections"].insert(closing, ask)
        else:
            ask = next(s for s in raw["sections"] if s.get("kind") == "ask" and s.get("askType") == ask_type)
        raw["sections"][0]["overview"]["markers"][2]["target"] = ask["id"]
        return _content(_build(raw))

    def test_request_ask_marker_sits_on_ask_kind(self) -> None:
        content = self._ask_html("request")
        self.assertRegex(content, r'<p class="ask-kind" data-ve-marker="3"')
        self.assertEqual(check_document_structure(content, skeleton_version=4), [])

    def test_hypothesis_ask_marker_sits_on_ask_claim(self) -> None:
        content = self._ask_html("hypothesis")
        self.assertRegex(content, r'<p class="ask-claim" data-ve-marker="3"')
        self.assertEqual(check_document_structure(content, skeleton_version=4), [])


class NarrativeH3FallbackTest(unittest.TestCase):
    def test_narrative_without_h2_is_marked_on_its_first_h3_through_the_pipeline(self) -> None:
        raw = _raw()
        target = next(s for s in raw["sections"] if s.get("kind") == "narrative" and s["id"] == "sec-current-problem")
        target["markup"] = target["markup"].replace("<h2", "<h3").replace("</h2>", "</h3>")
        content = _content(_build(raw))
        self.assertRegex(content, r'<h3 data-ve-marker="1"')
        self.assertEqual(len(re.findall(r"data-ve-marker=", content)), 3)
        self.assertEqual(check_document_structure(content, skeleton_version=4), [])


if __name__ == "__main__":
    unittest.main()
