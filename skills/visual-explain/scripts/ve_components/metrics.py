"""Reader-facing text volume of a built document (reported, never enforced)."""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

_BEGIN = "<!-- VE-CONTROLLED:CONTENT:BEGIN -->"
_END = "<!-- VE-CONTROLLED:CONTENT:END -->"
_FIGURE_KINDS = frozenset({"canonical", "compatibility"})
_EXCLUDED_KINDS = frozenset({"decision-panel"})
_VOID_TAGS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"})


@dataclass(frozen=True)
class TextMetrics:
    body_chars: int
    chars_before_figure: int
    figures: int


class _Counter(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str | None] = []
        self.body = self.before = self.figures = 0
        self.seen_figure = False

    def handle_starttag(self, tag, attrs):
        if tag in _VOID_TAGS:
            return
        kind = dict(attrs).get("data-ve-section-kind") if tag == "section" else None
        if kind in _FIGURE_KINDS:
            self.figures += 1
            self.seen_figure = True
        self.stack.append(kind if kind else (self.stack[-1] if self.stack else None))

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.stack and self.stack[-1] in _EXCLUDED_KINDS:
            return
        n = sum(1 for ch in data if not ch.isspace())
        self.body += n
        if not self.seen_figure:
            self.before += n


def text_metrics(document: str) -> TextMetrics:
    start, end = document.find(_BEGIN), document.find(_END)
    content = document[start + len(_BEGIN):end] if 0 <= start < end else ""
    counter = _Counter()
    counter.feed(content)
    counter.close()
    return TextMetrics(counter.body, counter.before, counter.figures)


def format_metrics(m: TextMetrics) -> str:
    return f"本文 {m.body_chars} 字 / 図より前 {m.chars_before_figure} 字 / 図 {m.figures} 点"
