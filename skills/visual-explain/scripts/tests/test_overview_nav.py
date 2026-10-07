"""First-screen v2 rendering and the overview marker list that replaces the TOC."""
from __future__ import annotations

import unittest
from pathlib import Path

from build_explainer import build_document
from ve_components.document_sections import build_overview_nav, render_first_screen
from ve_components.model import DocumentMetadata, FirstScreenSection, Overview, OverviewMarker
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from first_screen_ir import CANONICAL, assembly as _assembly, narr as _narr

SKILL = Path(__file__).resolve().parents[2]
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS = SKILL / "assets" / "components"
REGISTRY = load_registry(COMPONENTS / "registry.json")
DOC = DocumentMetadata(id="d", title="料金改定は限定対象で段階公開する", summary="要約文。",
                       type="proposal", profile="strict")
FIRST = FirstScreenSection(
    id="sec-first", conclusion="限定対象で開始する。",
    overview=Overview(section="sec-map", markers=(OverviewMarker(1, "背景", "sec-a"),
                                                  OverviewMarker(2, "リスク", "sec-closing"))))


def _build(raw: dict) -> str:
    return build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS, document_path="/tmp/x.html")


class FirstScreenRenderTest(unittest.TestCase):
    def test_title_and_conclusion_only(self) -> None:
        markup = render_first_screen(FIRST, DOC).markup
        self.assertIn("<h1>料金改定は限定対象で段階公開する</h1>", markup)
        self.assertIn('<p class="conclusion"><strong>結論:</strong> 限定対象で開始する。</p>', markup)
        self.assertNotIn("要約文。", markup)
        self.assertNotIn("subtitle", markup)


class OverviewNavTest(unittest.TestCase):
    def test_nav_lists_markers_in_order(self) -> None:
        nav = build_overview_nav(FIRST)
        self.assertIn('data-ve-section-kind="overview-nav"', nav.markup)
        self.assertIn('<a href="#sec-a"><span class="marker-n" aria-hidden="true">1</span><span>背景</span></a>', nav.markup)
        self.assertLess(nav.markup.index("#sec-a"), nav.markup.index("#sec-closing"))

    def test_no_overview_no_nav(self) -> None:
        self.assertIsNone(build_overview_nav(FirstScreenSection(id="f", conclusion="一文。")))

    def test_built_document_places_nav_after_overview_and_has_no_toc(self) -> None:
        raw = _assembly({"conclusion": "限定対象で開始する。",
                         "overview": {"section": "sec-map",
                                      "markers": [{"n": 1, "label": "背景", "target": "sec-a"}]}},
                        CANONICAL, _narr("sec-a", "背景の見出し"))
        html = _build(raw)
        self.assertNotIn('data-ve-section-kind="toc"', html)
        first = html.index('data-ve-section-kind="first-screen"')
        canon = html.index('data-ve-section-kind="canonical"')
        nav = html.index('data-ve-section-kind="overview-nav"')
        self.assertLess(first, canon)
        self.assertLess(canon, nav)
        self.assertIn('data-ve-instance="sec-a" id="sec-a"', html)


if __name__ == "__main__":
    unittest.main()
