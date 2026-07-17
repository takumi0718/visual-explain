"""Final-document structure checks (checker group 3).

Reads first-screen self-declaration (``data-ve-document-type`` /
``data-ve-profile``) and enforces honesty/structure invariants on the
flattened content markup. Invoked from ``check_final_document`` for
component documents only; pre-migration legacy documents never reach here.

Structure is discovered via ``HTMLParser`` so HTML comments and the text
content of ``script`` / ``style`` cannot spoof section wrappers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urlsplit

from .diagnostics import DOCUMENT_STRUCTURE_VIOLATION, Diagnostic
from .document_sections import compute_ask_digest_from_pairs
from .validation import _CLOSING_REQUIRED, _DOCUMENT_PROFILES, _DOCUMENT_TYPES

_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})
_OPAQUE_TAGS = frozenset({"script", "style"})

# Phase 3 extended-only section kinds. Phase 1 has none in the wild; presence
# under profile=strict is still rejected so the gate is ready.
_EXTENDED_ONLY_KINDS = frozenset({"freeform", "image"})


@dataclass
class _SectionNode:
    kind: str | None
    attrs: dict[str, str]
    h1_texts: list[str] = field(default_factory=list)
    h2_texts: list[str] = field(default_factory=list)
    has_summary: bool = False
    option_ids: list[str] = field(default_factory=list)


@dataclass
class _DocStructure:
    sections: list[_SectionNode] = field(default_factory=list)
    h1_in_first_screen: int = 0
    h1_total: int = 0


class _StructureParser(HTMLParser):
    """Collect real section / heading / summary nodes; skip comments & opaque text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.structure = _DocStructure()
        self._open: list[_SectionNode | None] = []  # None = non-section element frame
        self._element_stack: list[str] = []
        self._opaque: str | None = None
        self._heading_tag: str | None = None
        self._heading_parts: list[str] = []
        self._paragraph_classes: set[str] | None = None
        self._paragraph_parts: list[str] = []
        # Outermost data-ve-section-kind="first-screen" currently open, if any.
        self._first_screen_depth: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._opaque is not None:
            return
        if tag in _OPAQUE_TAGS:
            self._opaque = tag
            return
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        if "data-ask-option-id" in attr_map:
            ask_node = self._current_ask_decision()
            if ask_node is not None:
                ask_node.option_ids.append(attr_map["data-ask-option-id"])
        if tag not in _VOID_TAGS:
            self._element_stack.append(tag)

        if tag == "section":
            kind = attr_map.get("data-ve-section-kind") or None
            node = _SectionNode(kind=kind, attrs=attr_map)
            self._open.append(node)
            if kind == "first-screen" and self._first_screen_depth is None:
                self._first_screen_depth = len(self._open)
            return

        if tag == "h1" and self._heading_tag is None:
            self._heading_tag = "h1"
            self._heading_parts = []
            return
        if tag == "h2" and self._heading_tag is None:
            self._heading_tag = "h2"
            self._heading_parts = []
            return
        if tag == "p" and self._paragraph_classes is None:
            classes = {tok for tok in attr_map.get("class", "").split() if tok}
            self._paragraph_classes = classes
            self._paragraph_parts = []
            return

        if self._heading_tag and tag not in _VOID_TAGS:
            # Nested tags inside heading: still collect text via handle_data.
            pass

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Void / self-closing: no stack push beyond start handling for voids.
        tag = tag.lower()
        if self._opaque is not None or tag in _OPAQUE_TAGS:
            return
        # No structural effect for void tags we care about.

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._opaque is not None:
            if tag == self._opaque:
                self._opaque = None
            return

        if self._heading_tag == tag:
            text = "".join(self._heading_parts).strip()
            self._finish_heading(tag, text)
            self._heading_tag = None
            self._heading_parts = []
            self._pop_element(tag)
            return

        if self._paragraph_classes is not None and tag == "p":
            text = "".join(self._paragraph_parts).strip()
            classes = self._paragraph_classes
            self._paragraph_classes = None
            self._paragraph_parts = []
            if "subtitle" in classes and "decision" not in classes and text:
                # Attribute summary to the innermost open first-screen section.
                target = self._current_first_screen()
                if target is not None:
                    target.has_summary = True
            self._pop_element(tag)
            return

        if tag == "section" and self._open:
            node = self._open.pop()
            if node is not None:
                self.structure.sections.append(node)
            if self._first_screen_depth is not None and len(self._open) < self._first_screen_depth:
                self._first_screen_depth = None
            self._pop_element(tag)
            return

        self._pop_element(tag)

    def handle_data(self, data: str) -> None:
        if self._opaque is not None:
            return
        if self._heading_tag is not None:
            self._heading_parts.append(data)
        elif self._paragraph_classes is not None:
            self._paragraph_parts.append(data)

    def _pop_element(self, tag: str) -> None:
        if self._element_stack and self._element_stack[-1] == tag:
            self._element_stack.pop()
        elif tag in self._element_stack:
            # Tolerant pop for mildly broken markup in fixtures.
            idx = len(self._element_stack) - 1
            while idx >= 0 and self._element_stack[idx] != tag:
                idx -= 1
            if idx >= 0:
                del self._element_stack[idx:]

    def _current_first_screen(self) -> _SectionNode | None:
        if self._first_screen_depth is None:
            return None
        if len(self._open) < self._first_screen_depth:
            return None
        node = self._open[self._first_screen_depth - 1]
        return node

    def _current_ask_decision(self) -> _SectionNode | None:
        """Innermost currently-open decision-typed ask wrapper, if any.

        Walks outward through any intervening nested sections (e.g. plain
        grouping wrappers with no ``data-ve-section-kind``) so options
        nested arbitrarily deep inside an ask still attribute to it in
        document order, instead of silently dropping out of the digest.
        """
        for node in reversed(self._open):
            if node is not None and node.kind == "ask" and node.attrs.get("data-ve-ask-type") == "decision":
                return node
        return None

    def _finish_heading(self, tag: str, text: str) -> None:
        if tag == "h1":
            self.structure.h1_total += 1
            fs = self._current_first_screen()
            if fs is not None:
                self.structure.h1_in_first_screen += 1
                if text:
                    fs.h1_texts.append(text)
        elif tag == "h2":
            # Attribute to innermost open section with kind=closing, else any open section.
            for node in reversed(self._open):
                if node is not None and node.kind == "closing":
                    if text:
                        node.h2_texts.append(text)
                    return
            for node in reversed(self._open):
                if node is not None:
                    if text:
                        node.h2_texts.append(text)
                    return


def _parse_structure(content: str) -> _DocStructure:
    parser = _StructureParser()
    parser.feed(content)
    parser.close()
    return parser.structure


def _dom_text(fragment: str) -> str:
    """Normalize a text fragment the same way heading text is collected."""
    class _Text(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []

        def handle_data(self, data: str) -> None:
            self.parts.append(data)

    p = _Text()
    p.feed(fragment)
    p.close()
    return "".join(p.parts).strip()


def check_document_structure(content_markup: str, *, title: str | None = None) -> list[Diagnostic]:
    """Inspect flattened content markup for group-3 structure invariants.

    ``title`` is the document ``<title>`` text (from the TITLE slot; may still
    contain character references). When omitted, the title↔h1 equality check
    is skipped.
    """
    diagnostics: list[Diagnostic] = []
    structure = _parse_structure(content_markup)
    first_nodes = [s for s in structure.sections if s.kind == "first-screen"]
    if not first_nodes:
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "文書型の自己表明がありません",
            "content",
        ))
        if structure.h1_total != 0:
            diagnostics.append(Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION,
                "h1 は first-screen 内にちょうど1個必要です",
                "content",
            ))
        diagnostics.extend(_check_external_link_markers(content_markup))
        # closing check still useful when first-screen is missing
        diagnostics.extend(_check_closing_from_structure(structure, None))
        return diagnostics

    if len(first_nodes) != 1:
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "first-screen はちょうど1個必要です",
            "content",
        ))
        diagnostics.extend(_check_external_link_markers(content_markup))
        return diagnostics

    first = first_nodes[0]
    doc_type = first.attrs.get("data-ve-document-type") or None
    profile = first.attrs.get("data-ve-profile") or None

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

    diagnostics.extend(_check_h1_from_structure(structure, first, title))
    if not first.has_summary:
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "first-screen に summary がありません",
            "content",
        ))
    diagnostics.extend(
        _check_closing_from_structure(
            structure, doc_type if doc_type in _DOCUMENT_TYPES else None,
        )
    )
    diagnostics.extend(_check_external_link_markers(content_markup))
    if profile == "strict":
        diagnostics.extend(_check_strict_excludes_extended(structure))
    diagnostics.extend(_check_decision_panel(structure))
    return diagnostics


def _check_h1_from_structure(
    structure: _DocStructure,
    first: _SectionNode,
    title: str | None,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if structure.h1_total != 1 or structure.h1_in_first_screen != 1:
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "h1 は first-screen 内にちょうど1個必要です",
            "content",
        ))
        return diagnostics
    if title is None:
        return diagnostics
    h1_text = first.h1_texts[0] if first.h1_texts else None
    title_text = _dom_text(title)
    if h1_text is None or h1_text != title_text:
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "title と h1 が一致しません",
            "content",
        ))
    return diagnostics


def _check_closing_from_structure(
    structure: _DocStructure,
    doc_type: str | None,
) -> list[Diagnostic]:
    closing_nodes = [s for s in structure.sections if s.kind == "closing"]
    if not closing_nodes:
        return [Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "closing セクションがありません",
            "content",
        )]
    if doc_type is None:
        return []
    required = _CLOSING_REQUIRED.get(doc_type, ())
    headings = set()
    for node in closing_nodes:
        headings.update(node.h2_texts)
    diagnostics: list[Diagnostic] = []
    for heading in required:
        if heading not in headings:
            diagnostics.append(Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION,
                f"closing に必須見出し '{heading}' がありません（document.type={doc_type}）",
                "content",
            ))
    return diagnostics


class _LinkMarkerParser(HTMLParser):
    """Verify every https <a> carries a matching link-domain hostname marker."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.diagnostics: list[Diagnostic] = []
        self._anchor_stack: list[tuple[str | None, list[str]]] = []
        self._opaque: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._opaque is not None:
            return
        if tag in _OPAQUE_TAGS:
            self._opaque = tag
            return
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        if tag == "a":
            href = attr_map.get("href", "")
            track = href if href.lower().startswith("https://") else None
            self._anchor_stack.append((track, []))
        if self._anchor_stack:
            self._anchor_stack[-1][1].append(_render_start(tag, attrs))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in _VOID_TAGS and tag.lower() not in _OPAQUE_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._opaque is not None:
            if tag == self._opaque:
                self._opaque = None
            return
        if tag != "a" or not self._anchor_stack:
            if self._anchor_stack:
                self._anchor_stack[-1][1].append(f"</{tag}>")
            return
        href, parts = self._anchor_stack.pop()
        inner = "".join(parts[1:])
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
        escaped = f'<span class="link-domain">‹{_html_escape_minimal(host)}›</span>'
        if expected not in inner and escaped not in inner:
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
        if self._opaque is not None:
            return
        if self._anchor_stack:
            self._anchor_stack[-1][1].append(data)

    def close(self) -> None:
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


def _check_decision_panel(structure: _DocStructure) -> list[Diagnostic]:
    """Group-3: decision-recovery panel presence, position, and digest integrity.

    Only typed ask wrappers (``data-ve-section-kind="ask"`` with
    ``data-ve-ask-type="decision"``) count toward the decision-ask tally; the
    panel's own summary ``<li>`` elements use a distinct attribute name and
    never leak into ``option_ids``.
    """
    ask_nodes = [
        s for s in structure.sections
        if s.kind == "ask" and s.attrs.get("data-ve-ask-type") == "decision"
    ]
    panel_nodes = [s for s in structure.sections if s.kind == "decision-panel"]

    if not ask_nodes:
        if panel_nodes:
            return [Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION,
                "decision ask がないのに回収パネルがあります",
                "content",
            )]
        return []

    if not panel_nodes:
        return [Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "decision ask があるのに回収パネルがありません",
            "content",
        )]
    if len(panel_nodes) != 1:
        return [Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "回収パネルはちょうど1個必要です",
            "content",
        )]

    diagnostics: list[Diagnostic] = []
    panel = panel_nodes[0]
    panel_index = next(i for i, node in enumerate(structure.sections) if node is panel)
    closing_indices = [
        i for i, node in enumerate(structure.sections) if node.kind == "closing"
    ]
    if closing_indices and panel_index < max(closing_indices):
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "回収パネルは closing の後に必要です",
            "content",
        ))

    pairs = tuple((node.attrs.get("id", ""), tuple(node.option_ids)) for node in ask_nodes)
    expected_digest = compute_ask_digest_from_pairs(pairs)
    if panel.attrs.get("data-ve-ask-digest") != expected_digest:
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "回収パネルの ask 契約ダイジェストが一致しません",
            "content",
        ))

    required_attrs = ("data-ve-document-id", "data-ve-schema-version", "data-ve-document-path")
    if any(not panel.attrs.get(attr) for attr in required_attrs):
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "回収パネルの自己表明属性が不足しています",
            "content",
        ))

    return diagnostics


def _check_strict_excludes_extended(structure: _DocStructure) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for node in structure.sections:
        if node.kind in _EXTENDED_ONLY_KINDS:
            diagnostics.append(Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION,
                f"strict プロファイルに extended 限定要素は置けません: {node.kind}",
                "content",
            ))
    return diagnostics
