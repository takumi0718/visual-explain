"""Review-layer block numbering shared by the build (stamp) and the checker.

Both sides walk content markup with the same eligibility rules, so a document
passes only when every eligible block carries its 1-based DOM ordinal in
``data-ve-blk`` and no other element carries the attribute.
"""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

from .diagnostics import DOCUMENT_STRUCTURE_VIOLATION, Diagnostic

BLOCK_ATTR = "data-ve-blk"
BLOCK_TAGS = frozenset({"p", "h2", "h3", "li", "figure", "blockquote", "pre", "table"})
_TAG_LIST = "p / h2 / h3 / li / figure / blockquote / pre / table"
_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})


@dataclass(frozen=True)
class BlockSite:
    tag: str
    insert_at: int        # source index just before the start tag's ">" (or "/>")
    eligible: bool        # must carry the next ordinal
    value: str | None     # current data-ve-blk value, if present


def _starts_excluded_subtree(tag: str, attrs: dict[str, str]) -> bool:
    """UI parts and duplicated stepper panels never get a number, nor do their descendants."""
    classes = set(attrs.get("class", "").split())
    return (
        (tag == "section" and attrs.get("data-ve-section-kind") == "decision-panel")
        or "data-ask-option" in attrs
        or "data-stepper" in attrs
        or "ask-kind" in classes
        or "ask-memo" in classes
        or tag in {"svg", "template", "script", "style"}
    )


class _BlockWalker(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self._line_starts = [0]
        for index, char in enumerate(source):
            if char == "\n":
                self._line_starts.append(index + 1)
        self._stack: list[tuple[str, bool]] = []  # (tag, descendants_excluded)
        self.sites: list[BlockSite] = []

    def handle_starttag(self, tag, attrs):
        self._visit(tag, attrs, self_closing=False)

    def handle_startendtag(self, tag, attrs):
        self._visit(tag, attrs, self_closing=True)

    def handle_endtag(self, tag):
        tag = tag.lower()
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                return

    def _visit(self, tag: str, attrs, *, self_closing: bool) -> None:
        tag = tag.lower()
        attr_map: dict[str, str] = {}
        for name, value in attrs:
            attr_map.setdefault(name.lower(), value or "")
        inherited = bool(self._stack) and self._stack[-1][1]
        excluded = inherited or _starts_excluded_subtree(tag, attr_map)
        if tag in BLOCK_TAGS or BLOCK_ATTR in attr_map:
            self.sites.append(BlockSite(
                tag=tag,
                insert_at=self._insert_position(),
                eligible=tag in BLOCK_TAGS and not excluded,
                value=attr_map.get(BLOCK_ATTR),
            ))
        if not self_closing and tag not in _VOID_TAGS:
            self._stack.append((tag, excluded or tag == "figure"))

    def _insert_position(self) -> int:
        line, col = self.getpos()
        start = self._line_starts[line - 1] + col
        text = self.get_starttag_text() or ""
        trim = 2 if text.endswith("/>") else 1
        return start + len(text) - trim


def _walk(markup: str) -> list[BlockSite]:
    walker = _BlockWalker(markup)
    walker.feed(markup)
    walker.close()
    return walker.sites


def stamp_review_blocks(markup: str, start: int = 1) -> tuple[str, int]:
    """Insert ``data-ve-blk`` on every eligible block; return (markup, next ordinal)."""
    pieces: list[str] = []
    cursor = 0
    number = start
    for site in _walk(markup):
        if not site.eligible:
            continue
        pieces.append(markup[cursor:site.insert_at])
        pieces.append(f' {BLOCK_ATTR}="{number}"')
        cursor = site.insert_at
        number += 1
    pieces.append(markup[cursor:])
    return "".join(pieces), number


def stamp_review_sections(markups: tuple[str, ...]) -> tuple[str, ...]:
    """Number blocks across ordered section markups as one document."""
    stamped: list[str] = []
    number = 1
    for markup in markups:
        text, number = stamp_review_blocks(markup, number)
        stamped.append(text)
    return tuple(stamped)


def check_review_blocks(content: str) -> list[Diagnostic]:
    """Re-derive the expected numbering and report every deviation (first sequence break only)."""
    diagnostics: list[Diagnostic] = []
    expected = 0
    sequence_reported = False
    for site in _walk(content):
        if site.tag not in BLOCK_TAGS:
            diagnostics.append(Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION,
                f"data-ve-blk は {_TAG_LIST} にだけ付けられます: <{site.tag}>", "content"))
            continue
        if not site.eligible:
            if site.value is not None:
                diagnostics.append(Diagnostic(
                    DOCUMENT_STRUCTURE_VIOLATION,
                    f"data-ve-blk を付けられない位置にあります: <{site.tag}>", "content"))
            continue
        expected += 1
        if site.value != str(expected) and not sequence_reported:
            actual = site.value if site.value is not None else "なし"
            diagnostics.append(Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION,
                f"data-ve-blk は1からの連番である必要があります（{expected} 番目のブロックが {actual}）",
                "content"))
            sequence_reported = True
    return diagnostics
