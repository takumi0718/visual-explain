"""Build-time repetition gate over validated assembly sections.

Rejects restating the same claim: h2 vs its claim line, a figure caption vs the
preceding h2, a sentence repeated anywhere, and long prose before the first
figure when the document has no overview.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

from .metrics import _VOID_TAGS
from .model import AskSection, CanonicalSection, ClosingSection, CompatibilitySection, FirstScreenSection, NarrativeSection

SIMILARITY_THRESHOLD = 0.6
MAX_CHARS_BEFORE_FIGURE = 200
_MIN_DUPLICATE_CHARS = 10
_NOISE_RE = re.compile(r"[\s、。，．,.！？!?「」『』（）()・:：;；\-—]")
# A trailing run without a terminator is a sentence too, so unterminated
# list items and labels take part in the duplicate check.
_SENTENCE_RE = re.compile(r"[^。！？!?]+(?:[。！？!?]|$)")
_BLOCK_TAGS = frozenset({"h2", "h3", "p", "li", "figcaption"})
# Start tags that end an open <p> whose </p> the author omitted.
_P_CLOSERS = frozenset({
    "p", "h2", "h3", "h4", "li", "ul", "ol", "dl", "div", "section", "figure",
    "figcaption", "table", "blockquote", "pre", "details", "nav",
})


def normalize_sentence(text: str) -> str:
    return _NOISE_RE.sub("", text)


def bigram_jaccard(a: str, b: str) -> float:
    def grams(s: str) -> set[str]:
        s = normalize_sentence(s)
        return {s[i:i + 2] for i in range(len(s) - 1)} or {s}
    ga, gb = grams(a), grams(b)
    return len(ga & gb) / len(ga | gb) if ga | gb else 0.0


class _Blocks(HTMLParser):
    """Collect (tag, classes, text) for h2/h3/p/li/figcaption.

    Any element with class ``certainty`` is skipped with its whole subtree,
    whatever its tag. Omitted ``</p>`` and ``</li>`` are implied the way a
    browser implies them for these cases, and an end tag closes every element
    opened after its start tag.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, frozenset[str], str]] = []
        # (tag, classes, text parts for block tags else None, starts a skipped subtree)
        self._stack: list[tuple[str, frozenset[str], list[str] | None, bool]] = []

    def _skipping(self) -> bool:
        return any(entry[3] for entry in self._stack)

    def _pop(self) -> None:
        tag, classes, parts, _skip = self._stack.pop()
        if parts is not None:
            self.blocks.append((tag, classes, "".join(parts).strip()))

    def handle_starttag(self, tag, attrs):
        if self._stack and self._stack[-1][0] == "p" and tag in _P_CLOSERS:
            self._pop()
        if tag == "li" and self._stack and self._stack[-1][0] == "li":
            self._pop()
        if tag in _VOID_TAGS:
            return
        classes = frozenset(" ".join(v or "" for k, v in attrs if k == "class").split())
        skip = "certainty" in classes
        collect = tag in _BLOCK_TAGS and not skip and not self._skipping()
        self._stack.append((tag, classes, [] if collect else None, skip))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if not any(entry[0] == tag for entry in self._stack):
            return
        while self._stack:
            closing = self._stack[-1][0] == tag
            self._pop()
            if closing:
                return

    def handle_data(self, data):
        if self._skipping():
            return
        for entry in reversed(self._stack):
            if entry[2] is not None:
                entry[2].append(data)
                return

    def close(self) -> None:
        super().close()
        while self._stack:
            self._pop()


def _blocks(markup: str) -> list[tuple[str, frozenset[str], str]]:
    parser = _Blocks()
    parser.feed(markup)
    parser.close()
    return parser.blocks


def chars_before_first_figure(sections: tuple[object, ...]) -> int:
    """Visible characters before the first figure, counted like the build report.

    The first-screen (h1 and conclusion) is excluded. Narrative and ask
    sections are measured on the markup the build emits for them, including
    the link-domain markers the build appends to external links.
    """
    from .assembly import insert_link_domain_markers
    from .document_sections import render_ask
    from .metrics import visible_chars

    total = 0
    for section in sections:
        if isinstance(section, (CanonicalSection, CompatibilitySection)):
            break
        if isinstance(section, NarrativeSection):
            total += visible_chars(insert_link_domain_markers(section.markup))
        elif isinstance(section, AskSection):
            total += visible_chars(render_ask(section).markup)
    return total


def check_repetition(sections: tuple[object, ...]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    sentences: list[str] = []
    last_h2: str | None = None
    seen_figure = False
    first = sections[0] if sections and isinstance(sections[0], FirstScreenSection) else None

    for section in sections:
        if isinstance(section, FirstScreenSection):
            sentences += _SENTENCE_RE.findall(section.conclusion)
        elif isinstance(section, NarrativeSection):
            blocks = _blocks(section.markup)
            for i, (tag, classes, text) in enumerate(blocks):
                if tag == "h2":
                    last_h2 = text
                    nxt = blocks[i + 1] if i + 1 < len(blocks) else None
                    if nxt and "claim" in nxt[1] and bigram_jaccard(text, nxt[2]) >= SIMILARITY_THRESHOLD:
                        out.append((f"見出しと主張行がほぼ同じ文です（{section.id}）。主張行を削るか、見出しと別の情報を書いてください",
                                    section.id))
                if tag in {"p", "li", "figcaption"}:
                    sentences += _SENTENCE_RE.findall(text)
        elif isinstance(section, CanonicalSection):
            seen_figure = True
            caption = section.ir.caption or ""
            if last_h2 and bigram_jaccard(caption, last_h2) >= SIMILARITY_THRESHOLD:
                out.append((f"図のキャプションが直前の見出しの言い換えです（{section.ir.id}）。キャプションには「何を見るか」を書いてください",
                            section.ir.id))
            sentences += _SENTENCE_RE.findall(caption)
            last_h2 = None  # a later figure is not "right after" this heading
        elif isinstance(section, CompatibilitySection):
            seen_figure = True
            for tag, _classes, text in _blocks(section.markup):
                if tag == "figcaption":
                    sentences += _SENTENCE_RE.findall(text)
            last_h2 = None
        elif isinstance(section, AskSection):
            for text in (section.question, section.claim.text if section.claim else None, section.verify):
                if text:
                    sentences += _SENTENCE_RE.findall(text)
        elif isinstance(section, ClosingSection):
            for block in section.blocks:
                for item in block.items:
                    sentences += _SENTENCE_RE.findall(item)

    counts: dict[str, tuple[int, str]] = {}
    for s in sentences:
        key = normalize_sentence(s)
        if len(key) < _MIN_DUPLICATE_CHARS:
            continue
        n, original = counts.get(key, (0, s))
        counts[key] = (n + 1, original)
    for n, original in counts.values():
        if n >= 2:
            out.append((f"同じ文が{n}回出てきます: 「{original.strip()}」", "assembly.sections"))

    has_overview = first is not None and first.overview is not None
    if seen_figure and not has_overview:
        chars = chars_before_first_figure(sections)
        if chars > MAX_CHARS_BEFORE_FIGURE:
            out.append((f"最初の図より前の本文が{chars}字あります（上限200字）", "assembly.sections"))
    return out
