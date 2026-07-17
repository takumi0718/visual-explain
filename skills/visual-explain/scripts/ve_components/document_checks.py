"""Final-document structure checks (checker group 3).

Reads first-screen self-declaration (``data-ve-document-type`` /
``data-ve-profile``) and enforces honesty/structure invariants on the
flattened content markup. Invoked from ``check_final_document`` for
component documents only; pre-migration legacy documents never reach here.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

from .diagnostics import DOCUMENT_STRUCTURE_VIOLATION, Diagnostic
from .validation import _CLOSING_REQUIRED, _DOCUMENT_PROFILES, _DOCUMENT_TYPES

_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})

# Phase 3 extended-only section kinds. Phase 1 has none in the wild; presence
# under profile=strict is still rejected so the gate is ready.
_EXTENDED_ONLY_KINDS = frozenset({"freeform", "image"})

_FIRST_SCREEN_KIND_RE = re.compile(
    r'<section\b([^>]*\bdata-ve-section-kind\s*=\s*["\']first-screen["\'][^>]*)>',
    re.IGNORECASE,
)
_ATTR_RE = lambda name: re.compile(  # noqa: E731 — local attr matcher factory
    rf'\b{re.escape(name)}\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE,
)
_CLOSING_KIND_RE = re.compile(
    r'<section\b[^>]*\bdata-ve-section-kind\s*=\s*["\']closing["\'][^>]*>',
    re.IGNORECASE,
)
_SECTION_KIND_RE = re.compile(
    r'<section\b[^>]*\bdata-ve-section-kind\s*=\s*["\']([^"\']+)["\'][^>]*>',
    re.IGNORECASE,
)


def check_document_structure(content_markup: str, *, title: str | None = None) -> list[Diagnostic]:
    """Inspect flattened content markup for group-3 structure invariants.

    ``title`` is the document ``<title>`` text (from the TITLE slot). When
    omitted, the title↔h1 equality check is skipped.
    """
    diagnostics: list[Diagnostic] = []
    first = _find_first_screen(content_markup)
    if first is None:
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "文書型の自己表明がありません",
            "content",
        ))
        # Without a declared type the remaining type-scoped checks cannot run.
        diagnostics.extend(_check_h1_without_first_screen(content_markup))
        diagnostics.extend(_check_external_link_markers(content_markup))
        return diagnostics

    attrs, inner = first
    doc_type = _attr(attrs, "data-ve-document-type")
    profile = _attr(attrs, "data-ve-profile")

    if doc_type is None:
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "文書型の自己表明がありません",
            "content",
        ))
    elif doc_type not in _DOCUMENT_TYPES:
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            f"文書型の自己表明が不正です: {doc_type}",
            "content",
        ))

    if profile is None:
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "プロファイルの自己表明がありません",
            "content",
        ))
    elif profile not in _DOCUMENT_PROFILES:
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            f"プロファイルの自己表明が不正です: {profile}",
            "content",
        ))

    diagnostics.extend(_check_h1(content_markup, inner, title))
    diagnostics.extend(_check_summary(inner))
    diagnostics.extend(_check_closing(content_markup, doc_type if doc_type in _DOCUMENT_TYPES else None))
    diagnostics.extend(_check_external_link_markers(content_markup))
    if profile == "strict":
        diagnostics.extend(_check_strict_excludes_extended(content_markup))
    return diagnostics


def _attr(attrs: str, name: str) -> str | None:
    m = _ATTR_RE(name).search(attrs)
    return m.group(1) if m else None


def _find_first_screen(content: str) -> tuple[str, str] | None:
    """Return (opening-tag attrs, inner HTML) of the first first-screen section."""
    m = _FIRST_SCREEN_KIND_RE.search(content)
    if m is None:
        return None
    attrs = m.group(1)
    start = m.end()
    # Balance nested <section>…</section> from the opening we matched.
    # The match is the outer wrapper's open tag; walk from there.
    open_tag_start = m.start()
    depth = 0
    i = open_tag_start
    inner_start = start
    while i < len(content):
        if content.startswith("<section", i):
            depth += 1
            gt = content.find(">", i)
            if gt < 0:
                break
            i = gt + 1
            continue
        if content.startswith("</section>", i):
            depth -= 1
            if depth == 0:
                return attrs, content[inner_start:i]
            i += len("</section>")
            continue
        i += 1
    # Unbalanced: treat the remainder as inner so other checks still run.
    return attrs, content[inner_start:]


def _check_h1_without_first_screen(content: str) -> list[Diagnostic]:
    count = len(re.findall(r"<h1\b", content, re.IGNORECASE))
    if count != 0:
        return [Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "h1 は first-screen 内にちょうど1個必要です",
            "content",
        )]
    return []


def _check_h1(content: str, first_inner: str, title: str | None) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    total = len(re.findall(r"<h1\b", content, re.IGNORECASE))
    inside = len(re.findall(r"<h1\b", first_inner, re.IGNORECASE))
    if total != 1 or inside != 1:
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "h1 は first-screen 内にちょうど1個必要です",
            "content",
        ))
        return diagnostics
    if title is None:
        return diagnostics
    h1_text = _extract_h1_text(first_inner)
    if h1_text is None or h1_text != title:
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "title と h1 が一致しません",
            "content",
        ))
    return diagnostics


class _H1TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._depth = 0
        self._parts: list[str] = []
        self.text: str | None = None
        self._done = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._done:
            return
        tag = tag.lower()
        if tag == "h1" and self._depth == 0 and self.text is None:
            self._depth = 1
            self._parts = []
            return
        if self._depth and tag not in _VOID_TAGS:
            self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._done or not self._depth:
            return
        if tag.lower() == "h1" and self._depth == 1:
            self.text = "".join(self._parts).strip()
            self._done = True
            self._depth = 0
            return
        if self._depth:
            self._depth -= 1

    def handle_data(self, data: str) -> None:
        if self._depth:
            self._parts.append(data)


def _extract_h1_text(markup: str) -> str | None:
    parser = _H1TextParser()
    parser.feed(markup)
    parser.close()
    return parser.text


def _check_summary(first_inner: str) -> list[Diagnostic]:
    """Require a non-decision ``p.subtitle`` text block inside first-screen."""
    # Match <p class="subtitle">…</p> that does NOT also carry class "decision".
    for m in re.finditer(r"<p\b([^>]*)>(.*?)</p>", first_inner, re.IGNORECASE | re.S):
        attrs, body = m.group(1), m.group(2)
        classes = _class_tokens(attrs)
        if "subtitle" in classes and "decision" not in classes:
            text = re.sub(r"<[^>]+>", "", body).strip()
            if text:
                return []
    return [Diagnostic(
        DOCUMENT_STRUCTURE_VIOLATION,
        "first-screen に summary がありません",
        "content",
    )]


def _class_tokens(attrs: str) -> set[str]:
    m = _ATTR_RE("class").search(attrs)
    if m is None:
        return set()
    return {tok for tok in m.group(1).split() if tok}


def _check_closing(content: str, doc_type: str | None) -> list[Diagnostic]:
    if not _CLOSING_KIND_RE.search(content):
        return [Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "closing セクションがありません",
            "content",
        )]
    if doc_type is None:
        return []
    required = _CLOSING_REQUIRED.get(doc_type, ())
    headings = _extract_closing_h2(content)
    diagnostics: list[Diagnostic] = []
    for heading in required:
        if heading not in headings:
            diagnostics.append(Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION,
                f"closing に必須見出し '{heading}' がありません（document.type={doc_type}）",
                "content",
            ))
    return diagnostics


def _extract_closing_h2(content: str) -> set[str]:
    """Collect h2 text inside the closing section wrapper."""
    m = _CLOSING_KIND_RE.search(content)
    if m is None:
        return set()
    start = m.start()
    depth = 0
    i = start
    end = len(content)
    while i < len(content):
        if content.startswith("<section", i):
            depth += 1
            i = content.find(">", i) + 1
            continue
        if content.startswith("</section>", i):
            depth -= 1
            i += len("</section>")
            if depth == 0:
                end = i
                break
            continue
        i += 1
    block = content[start:end]
    headings: set[str] = set()
    for hm in re.finditer(r"<h2\b[^>]*>(.*?)</h2>", block, re.IGNORECASE | re.S):
        text = re.sub(r"<[^>]+>", "", hm.group(1)).strip()
        if text:
            headings.add(text)
    return headings


class _LinkMarkerParser(HTMLParser):
    """Verify every https <a> carries a matching link-domain hostname marker."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.diagnostics: list[Diagnostic] = []
        # stack of (href_or_None_for_non_https, collected_html_fragments_inside)
        self._anchor_stack: list[tuple[str | None, list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        if tag == "a":
            href = attr_map.get("href", "")
            track = href if href.lower().startswith("https://") else None
            self._anchor_stack.append((track, []))
        if self._anchor_stack:
            # Record nested markup for marker inspection (self-closing included).
            rendered = _render_start(tag, attrs)
            self._anchor_stack[-1][1].append(rendered)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag != "a" or not self._anchor_stack:
            if self._anchor_stack:
                self._anchor_stack[-1][1].append(f"</{tag}>")
            return
        href, parts = self._anchor_stack.pop()
        inner = "".join(parts[1:])  # drop the opening <a …> we recorded
        if href is None:
            return
        try:
            host = urlsplit(href).hostname
        except ValueError:
            host = None
        if not host:
            self.diagnostics.append(Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION,
                f"外部リンクのドメインマーカーが不正です: {href}",
                "content",
            ))
            return
        expected = f'<span class="link-domain">‹{host}›</span>'
        # Also accept HTML-escaped host in marker body.
        if expected not in inner and f'<span class="link-domain">‹{_html_escape_minimal(host)}›</span>' not in inner:
            if 'class="link-domain"' not in inner and "class='link-domain'" not in inner:
                self.diagnostics.append(Diagnostic(
                    DOCUMENT_STRUCTURE_VIOLATION,
                    f"外部リンクにドメインマーカーがありません: {href}",
                    "content",
                ))
            else:
                self.diagnostics.append(Diagnostic(
                    DOCUMENT_STRUCTURE_VIOLATION,
                    f"外部リンクのドメインマーカーが不正です: {href}",
                    "content",
                ))

    def handle_data(self, data: str) -> None:
        if self._anchor_stack:
            self._anchor_stack[-1][1].append(data)

    def close(self) -> None:
        # Unclosed https anchors: treat as missing marker (assembly should reject,
        # but final docs may be hand-broken fixtures).
        while self._anchor_stack:
            href, _ = self._anchor_stack.pop()
            if href is not None:
                self.diagnostics.append(Diagnostic(
                    DOCUMENT_STRUCTURE_VIOLATION,
                    f"外部リンクにドメインマーカーがありません: {href}",
                    "content",
                ))
        super().close()


def _render_start(tag: str, attrs: list[tuple[str, str | None]]) -> str:
    parts = [f"<{tag}"]
    for k, v in attrs:
        if v is None:
            parts.append(f" {k}")
        else:
            parts.append(f' {k}="{v}"')
    parts.append(">")
    return "".join(parts)


def _html_escape_minimal(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _check_external_link_markers(content: str) -> list[Diagnostic]:
    parser = _LinkMarkerParser()
    parser.feed(content)
    parser.close()
    return parser.diagnostics


def _check_strict_excludes_extended(content: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for m in _SECTION_KIND_RE.finditer(content):
        kind = m.group(1)
        if kind in _EXTENDED_ONLY_KINDS:
            diagnostics.append(Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION,
                f"strict プロファイルに extended 限定要素は置けません: {kind}",
                "content",
            ))
    return diagnostics
