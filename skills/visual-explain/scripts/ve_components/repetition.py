"""Build-time repetition gate over validated assembly sections.

Rejects restating the same claim: h2 vs its claim line, a figure caption vs the
preceding h2, a sentence repeated anywhere, and long prose before the first
figure when the document has no overview.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

from .model import AskSection, CanonicalSection, ClosingSection, CompatibilitySection, FirstScreenSection, NarrativeSection

SIMILARITY_THRESHOLD = 0.6
MAX_CHARS_BEFORE_FIGURE = 200
_MIN_DUPLICATE_CHARS = 10
_NOISE_RE = re.compile(r"[\s、。，．,.！？!?「」『』（）()・:：;；\-—]")
_SENTENCE_RE = re.compile(r"[^。！？!?]+[。！？!?]")


def normalize_sentence(text: str) -> str:
    return _NOISE_RE.sub("", text)


def bigram_jaccard(a: str, b: str) -> float:
    def grams(s: str) -> set[str]:
        s = normalize_sentence(s)
        return {s[i:i + 2] for i in range(len(s) - 1)} or {s}
    ga, gb = grams(a), grams(b)
    return len(ga & gb) / len(ga | gb) if ga | gb else 0.0


class _Blocks(HTMLParser):
    """Collect (tag, classes, text) for h2/h3/p/li, ignoring certainty badges."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, frozenset[str], str]] = []
        self._open: list[tuple[str, frozenset[str], list[str]]] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        classes = frozenset((dict(attrs).get("class") or "").split())
        if "certainty" in classes:
            self._skip += 1
        elif tag in {"h2", "h3", "p", "li"}:
            self._open.append((tag, classes, []))

    def handle_endtag(self, tag):
        if self._skip and tag == "span":
            self._skip -= 1
        elif self._open and self._open[-1][0] == tag:
            t, c, parts = self._open.pop()
            self.blocks.append((t, c, "".join(parts).strip()))

    def handle_data(self, data):
        if not self._skip and self._open:
            self._open[-1][2].append(data)


def _blocks(markup: str) -> list[tuple[str, frozenset[str], str]]:
    parser = _Blocks()
    parser.feed(markup)
    parser.close()
    return parser.blocks


def check_repetition(sections: tuple[object, ...]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    sentences: list[str] = []
    last_h2: str | None = None
    chars_before_figure = 0
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
                if tag in {"p", "li"}:
                    sentences += _SENTENCE_RE.findall(text)
                if not seen_figure:
                    chars_before_figure += len(normalize_sentence(text)) + sum(
                        1 for ch in text if ch in "。！？!?")
        elif isinstance(section, CanonicalSection):
            seen_figure = True
            caption = section.ir.caption or ""
            if last_h2 and bigram_jaccard(caption, last_h2) >= SIMILARITY_THRESHOLD:
                out.append((f"図のキャプションが直前の見出しの言い換えです（{section.ir.id}）。キャプションには「何を見るか」を書いてください",
                            section.ir.id))
            sentences += _SENTENCE_RE.findall(caption)
        elif isinstance(section, CompatibilitySection):
            seen_figure = True
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
            out.append((f"同じ文が{n}回出てきます: 「{original}」", "assembly.sections"))

    has_overview = first is not None and first.overview is not None
    if seen_figure and not has_overview and chars_before_figure > MAX_CHARS_BEFORE_FIGURE:
        out.append((f"最初の図より前の本文が{chars_before_figure}字あります（上限200字）", "assembly.sections"))
    return out
