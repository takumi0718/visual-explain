"""Guards for the canonical proposal example: text budget and first-screen reading order."""
from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

from build_explainer import build_document
from ve_components.metrics import text_metrics
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS

SKILL = Path(__file__).resolve().parents[2]
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS = SKILL / "assets" / "components"
REGISTRY = load_registry(COMPONENTS / "registry.json")
EXAMPLES = SKILL / "examples"
DOC_PATH = "skills/visual-explain/examples/example-proposal.html"


def _build() -> str:
    from decimal import Decimal
    raw = json.loads((EXAMPLES / "example-proposal.assembly.json").read_text("utf-8"), parse_float=Decimal)
    return build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS, document_path=DOC_PATH)


class _PreCanonicalText(HTMLParser):
    """Collect text and section kinds seen before the first canonical section."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.kinds: list[str] = []
        self.texts: list[tuple[str, str]] = []  # (enclosing tag, text)
        self.stack: list[str] = []
        self.done = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        kind = a.get("data-ve-section-kind")
        if kind == "canonical":
            self.done = True
        if kind and not self.done:
            self.kinds.append(kind)
        if tag not in {"br", "img", "meta", "link", "hr", "input"}:
            self.stack.append(tag + ("." + a["class"] if a.get("class") else ""))

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if not self.done and data.strip() and "script" not in "".join(self.stack) and "style" not in "".join(self.stack):
            self.texts.append((self.stack[-1] if self.stack else "", data.strip()))


class ExampleProposalTest(unittest.TestCase):
    def test_body_chars_within_budget(self) -> None:
        self.assertLessEqual(text_metrics(_build()).body_chars, 1400)

    def test_first_screen_is_h1_and_conclusion_only(self) -> None:
        html = _build()
        content = html[html.index("<!-- VE-CONTROLLED:CONTENT:BEGIN -->"):]
        parser = _PreCanonicalText()
        parser.feed(content)
        self.assertEqual(parser.kinds, ["first-screen"])
        tags = [t.split(".")[0] if not t.startswith("p.conclusion") else "p.conclusion" for t, _ in parser.texts]
        self.assertEqual(tags[0], "h1")
        self.assertTrue(all(t in {"p.conclusion", "strong"} for t in tags[1:]), tags)
        self.assertIn("p.conclusion", tags)

    def test_checked_in_html_matches_fresh_build(self) -> None:
        checked_in = (EXAMPLES / "example-proposal.html").read_text("utf-8")
        self.assertIn(f'data-ve-document-path="{DOC_PATH}"', checked_in)
        self.assertEqual(checked_in, _build())


if __name__ == "__main__":
    unittest.main()
