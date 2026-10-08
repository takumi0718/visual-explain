"""Check that overview marker numbers echoed on headings point where the overview does.

The build stamps ``data-ve-marker="n"`` on the heading of the section that
overview marker ``n`` links to. A number anywhere else (or twice) would tell
the reader a different story than the overview list, so it fails closed.

From skeleton v4 on, every overview target must also carry its echo, and the
attribute may sit only on the elements the build stamps (h2 / h3 / p).
"""
from __future__ import annotations

from html.parser import HTMLParser

from .diagnostics import DOCUMENT_STRUCTURE_VIOLATION, Diagnostic

MARKER_ATTR = "data-ve-marker"
# Elements the build stamps: narrative/closing headings and ask lead lines.
_STAMPED_TAGS = ("h2", "h3", "p")
_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})


class _MarkerWalker(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        # (tag, enclosing typed-section id, inside overview-nav, inside marker-n)
        self._stack: list[tuple[str, str | None, bool, bool]] = []
        self._href: str | None = None
        self.targets: dict[str, str] = {}      # overview number -> target id
        self.marks: list[tuple[str, str | None, str]] = []  # (number, enclosing section id, tag)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        _, section_id, in_nav, _ = self._stack[-1] if self._stack else ("", None, False, False)
        kind = a.get("data-ve-section-kind") if tag == "section" else None
        if kind is not None:
            section_id = a.get("id")
            in_nav = kind == "overview-nav"
        if in_nav and tag == "a":
            href = a.get("href") or ""
            self._href = href[1:] if href.startswith("#") else None
        if MARKER_ATTR in a:
            self.marks.append((a.get(MARKER_ATTR) or "", section_id, tag))
        in_number = in_nav and "marker-n" in (a.get("class") or "").split()
        if tag not in _VOID_TAGS:
            self._stack.append((tag, section_id, in_nav, in_number))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                del self._stack[i:]
                return

    def handle_data(self, data):
        if self._stack and self._stack[-1][3] and self._href is not None:
            self.targets.setdefault(data.strip(), self._href)


def check_section_markers(content_markup: str, skeleton_version: int = 1) -> list[Diagnostic]:
    walker = _MarkerWalker()
    walker.feed(content_markup)
    walker.close()
    diagnostics: list[Diagnostic] = []
    seen: set[str] = set()
    for number, section_id, tag in walker.marks:
        if skeleton_version >= 4 and tag not in _STAMPED_TAGS:
            diagnostics.append(Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION,
                f"論点番号の印は h2 / h3 / p 以外の要素 <{tag}> には付けられません", "content"))
        if number in seen:
            diagnostics.append(Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION, f"論点番号 {number} の印が複数あります", "content"))
            continue
        seen.add(number)
        target = walker.targets.get(number)
        if target is None or target != section_id:
            diagnostics.append(Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION,
                f"論点番号 {number} の印が、概要の番号 {number} の飛び先ではない場所にあります",
                "content",
            ))
    if skeleton_version >= 4:
        echoed = {number for number, _, _ in walker.marks}
        for number in sorted(walker.targets, key=lambda n: (len(n), n)):
            if number not in echoed:
                diagnostics.append(Diagnostic(
                    DOCUMENT_STRUCTURE_VIOLATION,
                    f"概要の番号 {number} の飛び先に論点番号の印がありません",
                    "content",
                ))
    return diagnostics
