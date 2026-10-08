"""Reader-facing text volume of a built document (reported, never enforced).

``visible_chars`` is the single counting rule for "text before the first
figure": the build report and the repetition gate both use it, so the number
an author sees after a build is the number the gate enforces.
"""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

_BEGIN = "<!-- VE-CONTROLLED:CONTENT:BEGIN -->"
_END = "<!-- VE-CONTROLLED:CONTENT:END -->"
_FIGURE_KINDS = frozenset({"canonical", "compatibility"})
_EXCLUDED_KINDS = frozenset({"decision-panel"})
_NOT_BEFORE_FIGURE_KINDS = frozenset({"first-screen"})
# Fixed interface labels of the question card (chrome, not prose).
_CHROME_CLASSES = frozenset({"ask-kind", "ask-badge", "ask-withdrawn-note", "ask-memo", "ask-prefix"})
# Screen-reader twins of a picture (relation lists) are not read by the eye.
_HIDDEN_CLASSES = frozenset({"visually-hidden"})
VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})


@dataclass(frozen=True)
class TextMetrics:
    body_chars: int
    chars_before_figure: int
    figures: int


class _Counter(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str | None, bool]] = []
        self.body = self.before = self.figures = 0
        self.seen_figure = False

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            return
        kind = dict(attrs).get("data-ve-section-kind") if tag == "section" else None
        if kind in _FIGURE_KINDS:
            self.figures += 1
            self.seen_figure = True
        parent_kind, parent_skip = self.stack[-1] if self.stack else (None, False)
        attr_map = dict(attrs)
        classes = set((attr_map.get("class") or "").split())
        # An option picture (and its text twin) is a figure, not prose.
        thumb = tag == "figure" and "data-ve-thumb" in attr_map
        self.stack.append((kind if kind else parent_kind,
                           parent_skip or thumb or bool(classes & (_CHROME_CLASSES | _HIDDEN_CLASSES))))

    def handle_startendtag(self, tag, attrs):
        # <br/> must not pop the parent; <span/> opens and closes nothing.
        if tag in VOID_TAGS:
            return
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        kind, skip = self.stack[-1] if self.stack else (None, False)
        if skip or kind in _EXCLUDED_KINDS:
            return
        n = sum(1 for ch in data if not ch.isspace())
        self.body += n
        if not self.seen_figure and kind not in _NOT_BEFORE_FIGURE_KINDS:
            self.before += n


def _count(markup: str) -> _Counter:
    counter = _Counter()
    counter.feed(markup)
    counter.close()
    return counter


def visible_chars(markup: str) -> int:
    """Non-whitespace characters of the text in ``markup`` (tags and comments excluded)."""
    return _count(markup).body


def text_metrics(document: str) -> TextMetrics:
    start, end = document.find(_BEGIN), document.find(_END)
    content = document[start + len(_BEGIN):end] if 0 <= start < end else ""
    counter = _count(content)
    return TextMetrics(counter.body, counter.before, counter.figures)


def format_metrics(m: TextMetrics) -> str:
    return f"本文 {m.body_chars} 字 / 図より前 {m.chars_before_figure} 字 / 図 {m.figures} 点"
