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
from decimal import Decimal, InvalidOperation
from html import unescape
from html.parser import HTMLParser
import re
import unicodedata
from urllib.parse import urlsplit

from .diagnostics import DOCUMENT_STRUCTURE_VIOLATION, Diagnostic
from .document_sections import compute_ask_digest_from_pairs
from .validation import (
    _CLOSING_REQUIRED,
    _DOCUMENT_PROFILES,
    _DOCUMENT_TYPES,
    MAX_VISUAL_STAGE_NARRATIVE_CHARS,
    MAX_VISUAL_STAGE_NARRATIVE_SECTIONS,
    SEQUENCE_REFERENCE_ATTRIBUTES,
    _SEQUENCE_COMPONENTS,
    _plain_text_character_count,
)

_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})
_OPAQUE_TAGS = frozenset({"script", "style"})

# Phase 3 extended-only section kinds. Phase 1 has none in the wild; presence
# under profile=strict is still rejected so the gate is ready.
_EXTENDED_ONLY_KINDS = frozenset({"freeform", "image"})

# Structural reserved attributes and the single tag each may legitimately
# appear on. The skeleton's JS binder and this checker both key document
# structure off these attributes via bare `[attr]` DOM queries (not
# `tag[attr]`), so an attacker who smuggles one onto the wrong tag — e.g. a
# `<div data-ve-section-kind="decision-panel">` inside otherwise-permitted
# compatibility markup, which `_StructureParser` below only tracks on
# `<section>` — is invisible to `structure.sections` yet still matched by a
# real browser's `document.querySelector('[data-ve-section-kind=...]')`.
# Fail-closed on any occurrence outside its designated tag, mirroring the
# self-closing-tag divergence guard above.
_RESERVED_ATTR_REQUIRED_TAG = {
    "data-ve-section-kind": "section",
    "data-ve-ask-type": "section",
    "data-ve-panel-ask": "li",
}

_VISUAL_STAGE_PROFILE = "visual-stage"
_MAX_VISUAL_STAGE_DIAGNOSTICS = 32
_MAX_DIAGNOSTIC_IDS = 8
_MAX_DIAGNOSTIC_IDENTIFIER_CHARS = 96
_MAX_DIAGNOSTIC_ID_LIST_CHARS = 256
_MAX_DIAGNOSTIC_MESSAGE_CHARS = 384
_MIN_VISUAL_STAGE_OVERLAP_CHARS = 10
_SEQUENCE_HIGHLIGHT_CLASSES = frozenset({
    "ve-seq-spot", "ve-seq-dim", "ve-takeaway-target",
})
_SEQUENCE_STATE_CLASSES = _SEQUENCE_HIGHLIGHT_CLASSES | frozenset({"is-current"})
_SEQUENCE_STATE_ATTRIBUTES = frozenset({
    "hidden", "aria-hidden", "aria-current", "tabindex",
})
_SEQUENCE_ACTIONS = ("previous", "next", "all")
_CONNECT_PAIR_RE = re.compile(r"\s*([^\s>]+)\s*->\s*([^\s>]+)\s*")
_EXACT_URL_REF_RE = re.compile(r"^url\(\s*#([^\s)'\"#]+)\s*\)$", re.IGNORECASE)
_INLINE_URL_REF_RE = re.compile(r"url\(\s*#([^\s)'\"#]+)\s*\)", re.IGNORECASE)

_HIGHLIGHT_PAINT_PROPERTIES = frozenset({
    "opacity", "outline", "outline-offset", "box-shadow", "color",
    "background-color", "fill", "stroke",
})
_HIGHLIGHT_CLASS_NAMES = frozenset({
    "ve-seq-spot", "ve-seq-dim", "ve-takeaway-target",
})
_GLOBAL_AXIS_RESET_PROPERTIES = frozenset({"writing-mode", "all"})
_PATH_WIDTH_VARIABLES = (
    "--ve-path-spotlight-node-width",
    "--ve-path-spotlight-gap",
    "--ve-path-spotlight-content-width",
)
_SKELETON_CONTENT_WIDTH_TOKEN = "--w-narrative"
_PATH_CANVAS_SELECTOR = (
    '[data-stepper][data-ve-sequence-mode="path-spotlight"] '
    '[data-ve-component="flow"] .ve-flow-path-canvas'
)
_PATH_SCROLL_SELECTOR = (
    '[data-stepper][data-ve-sequence-mode="path-spotlight"] '
    '[data-ve-component="flow"] .ve-flow-scroll'
)
_PATH_STATION_SELECTOR = f"{_PATH_CANVAS_SELECTOR} .ve-flow-station"
_PATH_NODE_SELECTOR = f"{_PATH_CANVAS_SELECTOR} .ve-flow-node"


@dataclass
class _DomNode:
    tag: str
    attrs: dict[str, str]
    children: list["_DomNode | str"] = field(default_factory=list)


class _DomTreeParser(HTMLParser):
    """Build the small element/text tree needed for sequence comparison."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _DomNode("#document", {})
        self._stack = [self.root]
        self._opaque: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        node = _DomNode(tag, {name.lower(): (value or "") for name, value in attrs})
        self._stack[-1].children.append(node)
        if tag not in _VOID_TAGS:
            self._stack.append(node)
        if tag in _OPAQUE_TAGS:
            self._opaque = tag

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self._stack[-1].children.append(
            _DomNode(tag, {name.lower(): (value or "") for name, value in attrs}),
        )

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._opaque == tag:
            self._opaque = None
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == tag:
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if self._opaque is None:
            self._stack[-1].children.append(data)


def _parse_dom_tree(markup: str) -> _DomNode:
    parser = _DomTreeParser()
    parser.feed(markup)
    parser.close()
    return parser.root


def _element_children(node: _DomNode) -> list[_DomNode]:
    return [child for child in node.children if isinstance(child, _DomNode)]


def _descendants(node: _DomNode, *, include_self: bool = False):
    if include_self:
        yield node
    for child in node.children:
        if isinstance(child, _DomNode):
            yield child
            yield from _descendants(child)


def _classes(node: _DomNode) -> set[str]:
    return {token for token in node.attrs.get("class", "").split() if token}


def _has_ancestor(root: _DomNode, target: _DomNode, predicate) -> bool:
    def visit(node: _DomNode, ancestors: tuple[_DomNode, ...]) -> bool:
        if node is target:
            return any(predicate(item) for item in ancestors)
        return any(
            visit(child, ancestors + (node,))
            for child in node.children
            if isinstance(child, _DomNode)
        )

    return visit(root, ())


@dataclass
class _SectionNode:
    kind: str | None
    attrs: dict[str, str]
    h1_texts: list[str] = field(default_factory=list)
    h2_texts: list[str] = field(default_factory=list)
    has_summary: bool = False
    option_ids: list[str] = field(default_factory=list)
    claim_texts: list[str] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)


@dataclass
class _DocStructure:
    sections: list[_SectionNode] = field(default_factory=list)
    h1_in_first_screen: int = 0
    h1_total: int = 0
    self_closing_tags: list[str] = field(default_factory=list)
    misplaced_reserved_attrs: list[tuple[str, str]] = field(default_factory=list)


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
        # Depth of nested <svg> foreign content currently open (0 = none).
        self._svg_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._opaque is not None:
            return
        if tag in _OPAQUE_TAGS:
            self._opaque = tag
            return
        if tag == "svg":
            self._svg_depth += 1
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        self._collect_option_id(attr_map)
        self._check_reserved_attr_placement(tag, attr_map)
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
        # Self-closing syntax (``<tag .../>``) has no structural effect for
        # genuinely void elements (``<br/>`` etc: browsers treat them
        # identically with or without the slash). For any other element in
        # HTML content, real browsers ignore the trailing slash as a parse
        # error and open the element as a normal, unclosed start tag instead
        # of skipping it — the opposite of a no-op. Silently ignoring it
        # here (as a naive ``HTMLParser`` override might) would let a
        # self-closed ``<section data-ve-section-kind="decision-panel".../>``
        # (or a fake ask) vanish from this parser's model while a browser
        # still materializes a real, open section. Recording it as a
        # violation closes that divergence fail-closed rather than trying to
        # emulate browser mis-nesting.
        #
        # Inside <svg> foreign content the HTML5 parsing algorithm takes the
        # opposite branch: the self-closing flag IS honored for every
        # element there (not just a recognized SVG tag list), so a
        # self-closed ``<path/>``/``<circle/>`` genuinely self-closes in a
        # real browser too — there is no divergence to guard against, and
        # any HTML section/panel/ask tag self-closed inside <svg> becomes an
        # inert, foreign-namespaced element rather than a real document
        # section, so it can't spoof structure either. Treat that case as a
        # no-op for the self-closing-tag violation only — the element is
        # still a real, attribute-bearing DOM node a browser materializes,
        # so any ``data-ask-option-id`` it carries must still reach the
        # digest, exactly like a void self-closing tag's does below.
        tag = tag.lower()
        if self._opaque is not None or tag in _OPAQUE_TAGS:
            return
        in_svg = tag == "svg" or self._svg_depth > 0
        if not in_svg and tag not in _VOID_TAGS:
            self.structure.self_closing_tags.append(tag)
            return
        # Void elements (e.g. ``<input .../>``) never reach handle_starttag
        # — HTMLParser fires handle_startendtag exclusively for self-closing
        # syntax. Collect data-ask-option-id here too (and for any element
        # self-closed inside <svg>, void or not), or an option carried on it
        # silently evades the decision-panel digest.
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        self._collect_option_id(attr_map)
        self._check_reserved_attr_placement(tag, attr_map)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._opaque is not None:
            if tag == self._opaque:
                self._opaque = None
            return
        if tag == "svg" and self._svg_depth > 0:
            self._svg_depth -= 1

        if self._heading_tag == tag:
            text = "".join(self._heading_parts).strip()
            self._finish_heading(tag, text)
            self._heading_tag = None
            self._heading_parts = []
            self._pop_element(tag)
            return

        if self._paragraph_classes is not None and tag == "p":
            raw_text = "".join(self._paragraph_parts)
            text = raw_text.strip()
            classes = self._paragraph_classes
            self._paragraph_classes = None
            self._paragraph_parts = []
            if "subtitle" in classes and "decision" not in classes and text:
                # Attribute summary to the innermost open first-screen section.
                target = self._current_first_screen()
                if target is not None:
                    target.has_summary = True
            if "ve-claim" in classes:
                target = self._current_section("canonical")
                if target is not None:
                    target.claim_texts.append(raw_text)
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
        for node in self._open:
            if node is not None and node.kind == "narrative":
                node.text_parts.append(data)
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

    def _current_section(self, kind: str) -> _SectionNode | None:
        for node in reversed(self._open):
            if node is not None and node.kind == kind:
                return node
        return None

    def _collect_option_id(self, attr_map: dict[str, str]) -> None:
        """Record ``data-ask-option-id`` on the innermost open decision ask.

        Shared by ``handle_starttag`` and ``handle_startendtag`` (both the
        void-tag and svg-foreign-content branches) so every code path that
        can carry the attribute on a real DOM element funnels through one
        place instead of duplicating the presence check and lookup.
        """
        if "data-ask-option-id" in attr_map:
            ask_node = self._current_ask_decision()
            if ask_node is not None:
                ask_node.option_ids.append(attr_map["data-ask-option-id"])

    def _check_reserved_attr_placement(self, tag: str, attr_map: dict[str, str]) -> None:
        """Fail-closed on a structural reserved attribute borne by the wrong tag.

        Shared by ``handle_starttag`` and ``handle_startendtag`` so a bare
        ``[data-ve-section-kind]``-style DOM query (as the skeleton's JS
        binder and ``document.querySelector`` calls use) can never match an
        element this parser silently ignored as non-structural.
        """
        for attr, required_tag in _RESERVED_ATTR_REQUIRED_TAG.items():
            if tag != required_tag and attr in attr_map:
                self.structure.misplaced_reserved_attrs.append((tag, attr))

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


def _bounded_identifier(value: object) -> str:
    """Keep attacker-controlled identifiers from inflating diagnostics."""
    rendered = str(value)
    if len(rendered) <= _MAX_DIAGNOSTIC_IDENTIFIER_CHARS:
        return rendered
    return rendered[:_MAX_DIAGNOSTIC_IDENTIFIER_CHARS - 1] + "…"


def _bounded_id_list(values) -> str:
    """Render a stable, bounded identifier list for diagnostics."""
    ordered = sorted({str(value) for value in values})
    shown = [_bounded_identifier(value) for value in ordered[:_MAX_DIAGNOSTIC_IDS]]
    suffix = f", …(+{len(ordered) - len(shown)})" if len(ordered) > len(shown) else ""
    rendered = ", ".join(shown) + suffix
    if len(rendered) <= _MAX_DIAGNOSTIC_ID_LIST_CHARS:
        return rendered
    return rendered[:_MAX_DIAGNOSTIC_ID_LIST_CHARS - 1] + "…"


def _bounded_diagnostic_message(prefix: str, message: object) -> str:
    """Apply one stable bound to every visual-stage diagnostic field."""
    body = str(message)
    available = max(1, _MAX_DIAGNOSTIC_MESSAGE_CHARS - len(prefix))
    if len(body) > available:
        body = body[:available - 1] + "…"
    return prefix + body


def _visual_stage_diagnostic(message: str, path: str) -> Diagnostic:
    return Diagnostic(
        DOCUMENT_STRUCTURE_VIOLATION,
        _bounded_diagnostic_message("visual-stage 情報完全性: ", message),
        path,
    )


def _sequence_diagnostic(message: str, path: str = "content") -> Diagnostic:
    return Diagnostic(
        DOCUMENT_STRUCTURE_VIOLATION,
        _bounded_diagnostic_message("visual-stage sequence: ", message),
        path,
    )


def _strip_panel_suffix(value: str, panel_number: int) -> str:
    suffix = f"--p{panel_number}"
    return value[:-len(suffix)] if value.endswith(suffix) else value


def _normalize_reference_value(name: str, value: str, panel_number: int) -> str:
    kind = SEQUENCE_REFERENCE_ATTRIBUTES.get(name)
    if kind == "dom-id":
        return _strip_panel_suffix(value, panel_number)
    if kind == "fragment":
        trimmed = value.strip()
        return (
            "#" + _strip_panel_suffix(trimmed[1:], panel_number)
            if trimmed.startswith("#") else trimmed
        )
    if kind == "single-idref":
        return _strip_panel_suffix(value, panel_number)
    if kind == "idref-list":
        return " ".join(_strip_panel_suffix(token, panel_number) for token in value.split())
    if kind == "connector-declaration":
        normalized: list[str] = []
        for declaration in value.split(","):
            match = _CONNECT_PAIR_RE.fullmatch(declaration)
            if match is None:
                return value
            normalized.append(
                f"{_strip_panel_suffix(match.group(1), panel_number)}->"
                f"{_strip_panel_suffix(match.group(2), panel_number)}"
            )
        return ",".join(normalized)
    if kind == "url-reference":
        match = _EXACT_URL_REF_RE.fullmatch(value)
        if match is None:
            return value
        return f"url(#{_strip_panel_suffix(match.group(1), panel_number)})"
    if kind == "inline-url-reference":
        return _INLINE_URL_REF_RE.sub(
            lambda match: f"url(#{_strip_panel_suffix(match.group(1), panel_number)})",
            value,
        )
    return value


def _normalized_panel_dom(node: _DomNode, panel_number: int, *, forecast: bool = False):
    classes = _classes(node)
    is_forecast = forecast or "ve-seq-next" in classes
    normalized_attrs: list[tuple[str, str]] = []
    for name, value in node.attrs.items():
        if name == "data-step" or name in _SEQUENCE_STATE_ATTRIBUTES:
            continue
        if name == "class":
            remaining = sorted(classes - _SEQUENCE_STATE_CLASSES)
            if remaining:
                normalized_attrs.append((name, " ".join(remaining)))
            continue
        normalized_attrs.append((name, _normalize_reference_value(name, value, panel_number)))
    normalized_children = []
    for child in node.children:
        if isinstance(child, str):
            normalized_children.append("" if is_forecast else child)
        else:
            normalized_children.append(
                _normalized_panel_dom(child, panel_number, forecast=is_forecast),
            )
    return (node.tag, tuple(sorted(normalized_attrs)), tuple(normalized_children))


def _panel_reference_analysis(node: _DomNode) -> tuple[tuple[str, ...], tuple[str, ...]]:
    targets: list[str] = []
    malformed: list[str] = []
    for element in _descendants(node, include_self=True):
        for name, value in element.attrs.items():
            kind = SEQUENCE_REFERENCE_ATTRIBUTES.get(name)
            if kind == "fragment":
                trimmed = value.strip()
                if trimmed.startswith("#"):
                    target = trimmed[1:]
                    if target and "#" not in target and not any(char.isspace() for char in target):
                        targets.append(target)
                    else:
                        malformed.append(name)
                else:
                    malformed.append(name)
            elif kind == "single-idref":
                if value and not any(char.isspace() for char in value):
                    targets.append(value)
                else:
                    malformed.append(name)
            elif kind == "idref-list":
                tokens = value.split()
                if tokens:
                    targets.extend(tokens)
                else:
                    malformed.append(name)
            elif kind == "connector-declaration":
                declarations = value.split(",")
                valid = bool(value) and all(declaration.strip() for declaration in declarations)
                parsed: list[re.Match[str]] = []
                for declaration in declarations:
                    match = _CONNECT_PAIR_RE.fullmatch(declaration)
                    if match is None:
                        valid = False
                    else:
                        parsed.append(match)
                if valid:
                    for match in parsed:
                        targets.extend(match.groups())
                else:
                    malformed.append(name)
            elif kind == "url-reference":
                decoded_value = _decode_css_identifier(value)
                match = _EXACT_URL_REF_RE.fullmatch(decoded_value)
                if match is not None:
                    targets.append(match.group(1))
                else:
                    malformed.append(name)
            elif kind == "inline-url-reference":
                decoded_value = _decode_css_identifier(value)
                url_seen = False
                for _property, declaration_value in _css_declarations(decoded_value):
                    if not re.search(r"url\s*\(", declaration_value, re.I):
                        continue
                    url_seen = True
                    match = _EXACT_URL_REF_RE.fullmatch(declaration_value.strip())
                    if match is None:
                        malformed.append(name)
                    else:
                        targets.append(match.group(1))
                if re.search(r"url\s*\(", decoded_value, re.I) and not url_seen:
                    malformed.append(name)
    return tuple(targets), tuple(malformed)


def _check_panel_namespace(
    panel: _DomNode,
    panel_number: int,
    path: str,
    *,
    expected_payload_ids: frozenset[str] = frozenset(),
    expected_landmark_ids: tuple[str, ...] = (),
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    suffix = f"--p{panel_number}"
    ids = [
        element.attrs["id"]
        for element in _descendants(panel, include_self=True)
        if "id" in element.attrs
    ]
    for dom_id in ids:
        if not dom_id.endswith(suffix):
            diagnostics.append(_sequence_diagnostic(
                f"panel {panel_number} の DOM id '{_bounded_identifier(dom_id)}' は"
                f" {suffix} で終わる必要があります",
                path,
            ))
    id_set = set(ids)
    for base_id in expected_payload_ids:
        if base_id in id_set:
            diagnostics.append(_sequence_diagnostic(
                f"panel {panel_number} の expected semantic DOM id は"
                f" '{_bounded_identifier(base_id + suffix)}' が必要です"
                f"（base id '{_bounded_identifier(base_id)}' のままでは不正です）",
                path,
            ))
    for element in _descendants(panel, include_self=True):
        semantic_id = element.attrs.get("data-ve-semantic-id")
        dom_id = element.attrs.get("id")
        if semantic_id in expected_payload_ids and dom_id is not None:
            expected_id = f"{semantic_id}{suffix}"
            if dom_id != expected_id:
                diagnostics.append(_sequence_diagnostic(
                    f"panel {panel_number} の semantic id"
                    f" '{_bounded_identifier(semantic_id)}' に対応する DOM id は"
                    f" '{_bounded_identifier(expected_id)}' が必要です",
                    path,
                ))
    for base_id in expected_landmark_ids:
        expected_id = f"{base_id}{suffix}"
        if expected_id not in id_set:
            diagnostics.append(_sequence_diagnostic(
                f"panel {panel_number} の expected landmark DOM id"
                f" '{_bounded_identifier(expected_id)}' がありません",
                path,
            ))
    reference_targets, malformed = _panel_reference_analysis(panel)
    for attribute in malformed:
        diagnostics.append(_sequence_diagnostic(
            f"panel {panel_number} の参照属性 '{attribute}' の形式が閉じた grammar に違反します",
            path,
        ))
    for target in reference_targets:
        if target not in id_set:
            diagnostics.append(_sequence_diagnostic(
                f"panel {panel_number} の参照 '{_bounded_identifier(target)}' は"
                "同一 panel 内の id を指す必要があります",
                path,
            ))
    return diagnostics


def _check_sequence_stepper(
    canonical: _DomNode,
    stepper: _DomNode,
    *,
    instance_id: str,
    component_id: str,
    expected_sequence,
    expected_payload_ids: frozenset[str],
    expected_landmark_ids: tuple[str, ...],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    path = f"content.canonical[{instance_id}]"
    mode = stepper.attrs.get("data-ve-sequence-mode", "")
    if component_id not in _SEQUENCE_COMPONENTS.get(mode, frozenset()):
        diagnostics.append(_sequence_diagnostic(
            f"mode '{mode}' は component '{component_id}' では使用できません",
            path,
        ))
    expected_steps = None
    if expected_sequence is not None:
        expected_mode = getattr(expected_sequence, "mode", None)
        if mode != expected_mode:
            diagnostics.append(_sequence_diagnostic(
                f"描画 mode '{mode}' が expected mode '{expected_mode}' と一致しません",
                path,
            ))
        steps = getattr(expected_sequence, "steps", None)
        if isinstance(steps, tuple):
            expected_steps = len(steps)
            if expected_steps > 8:
                diagnostics.append(_sequence_diagnostic(
                    f"sequence step 数は8以下です（実測 {expected_steps}）",
                    path,
                ))
        else:
            diagnostics.append(_sequence_diagnostic("expected sequence steps が不正です", path))

    panels = [
        child for child in _element_children(stepper)
        if "data-step" in child.attrs
    ]
    panel_numbers = [panel.attrs.get("data-step", "") for panel in panels]
    required_numbers = [str(index) for index in range(1, len(panels) + 1)]
    if panel_numbers != required_numbers:
        diagnostics.append(_sequence_diagnostic(
            f"data-step は1からの連番である必要があります（実測 {panel_numbers}）",
            path,
        ))
    if len(panels) - 1 > 8:
        diagnostics.append(_sequence_diagnostic(
            f"描画 sequence step 数は8以下です（実測 {max(0, len(panels) - 1)}）",
            path,
        ))
    if expected_steps is not None and len(panels) != expected_steps + 1:
        diagnostics.append(_sequence_diagnostic(
            f"panel 数は steps+1 必要です（期待 {expected_steps + 1}, 実測 {len(panels)}）",
            path,
        ))
    total = stepper.attrs.get("data-total-steps")
    if total != str(len(panels)):
        diagnostics.append(_sequence_diagnostic(
            f"data-total-steps は panel 数と一致する必要があります（値 {total!r}, panel {len(panels)}）",
            path,
        ))

    buttons = [node for node in _descendants(stepper) if node.tag == "button"]
    for action in _SEQUENCE_ACTIONS:
        matching = [node for node in buttons if node.attrs.get("data-step-action") == action]
        if len(matching) != 1:
            diagnostics.append(_sequence_diagnostic(
                f"stepper は data-step-action='{action}' button をちょうど1個必要とします",
                path,
            ))
        elif _has_ancestor(stepper, matching[0], lambda item: "data-step" in item.attrs):
            diagnostics.append(_sequence_diagnostic(
                f"data-step-action='{action}' button は panel 外に置く必要があります",
                path,
            ))
    next_buttons = [node for node in buttons if node.attrs.get("data-step-action") == "next"]
    if len(next_buttons) == 1 and not next_buttons[0].attrs.get("data-next-label"):
        diagnostics.append(_sequence_diagnostic("next button に data-next-label が必要です", path))

    if panels:
        first_highlights = [
            element for element in _descendants(panels[0], include_self=True)
            if _classes(element) & _SEQUENCE_HIGHLIGHT_CLASSES
        ]
        if first_highlights:
            diagnostics.append(_sequence_diagnostic(
                "panel 1 は強調 class を持たない完成図である必要があります",
                path,
            ))

    normalized = []
    for index, panel in enumerate(panels, 1):
        diagnostics.extend(_check_panel_namespace(
            panel,
            index,
            path,
            expected_payload_ids=expected_payload_ids,
            expected_landmark_ids=expected_landmark_ids,
        ))
        normalized.append(_normalized_panel_dom(panel, index))
    if normalized and any(item != normalized[0] for item in normalized[1:]):
        diagnostics.append(_sequence_diagnostic(
            "全 panel の DOM は許可された状態差を正規化した後に同一である必要があります",
            path,
        ))
    return diagnostics


def _check_visual_stage_sequences(content_markup: str, expected) -> list[Diagnostic]:
    root = _parse_dom_tree(content_markup)
    canonicals = [
        node for node in _descendants(root)
        if node.tag == "section" and node.attrs.get("data-ve-section-kind") == "canonical"
    ]
    expected_by_instance = {}
    if expected is not None:
        try:
            expected_by_instance = {
                str(record.instance_id): record
                for record in expected
                if hasattr(record, "instance_id")
            }
        except TypeError:
            expected_by_instance = {}

    diagnostics: list[Diagnostic] = []
    for canonical in canonicals:
        instance_id = canonical.attrs.get("data-ve-instance", "<unknown>")
        path = f"content.canonical[{instance_id}]"
        record = expected_by_instance.get(instance_id)
        component_id = (
            str(record.component_id) if record is not None
            else canonical.attrs.get("data-ve-component", "")
        )
        if record is not None and canonical.attrs.get("data-ve-component", "") != component_id:
            diagnostics.append(_sequence_diagnostic(
                f"描画 component が expected component '{component_id}' と一致しません",
                path,
            ))

        direct_children = _element_children(canonical)
        claims = [node for node in _descendants(canonical) if "ve-claim" in _classes(node)]
        outside_claims = [
            node for node in claims
            if not _has_ancestor(canonical, node, lambda item: "data-step" in item.attrs)
        ]
        if len(claims) != 1 or len(outside_claims) != 1:
            diagnostics.append(_sequence_diagnostic(
                "claim は sequence panel 外にちょうど1個必要です",
                path,
            ))
        direct_claims = [node for node in direct_children if "ve-claim" in _classes(node)]

        steppers = [node for node in _descendants(canonical) if "data-stepper" in node.attrs]
        expected_sequence = getattr(record, "sequence", None) if record is not None else None
        if record is not None:
            required = expected_sequence is not None
            if required and len(steppers) != 1:
                diagnostics.append(_sequence_diagnostic(
                    f"expected sequence には stepper がちょうど1個必要です（実測 {len(steppers)}）",
                    path,
                ))
            elif not required and steppers:
                diagnostics.append(_sequence_diagnostic(
                    "expected に sequence がない canonical は stepper を持てません",
                    path,
                ))
        elif len(steppers) > 1:
            diagnostics.append(_sequence_diagnostic(
                f"canonical の stepper は最大1個です（実測 {len(steppers)}）",
                path,
            ))
        if len(steppers) == 1:
            direct_steppers = [node for node in direct_children if "data-stepper" in node.attrs]
            if len(direct_claims) != 1 or direct_steppers != steppers:
                diagnostics.append(_sequence_diagnostic(
                    "claim と stepper は canonical 直下で隣接し、claim が直前である必要があります",
                    path,
                ))
            else:
                claim_index = direct_children.index(direct_claims[0])
                stepper_index = direct_children.index(steppers[0])
                if stepper_index != claim_index + 1:
                    diagnostics.append(_sequence_diagnostic(
                        "claim は canonical 直下の stepper 直前に必要です",
                        path,
                    ))
            diagnostics.extend(_check_sequence_stepper(
                canonical,
                steppers[0],
                instance_id=instance_id,
                component_id=component_id,
                expected_sequence=expected_sequence,
                expected_payload_ids=(
                    frozenset(str(value) for value in record.payload_semantic_ids)
                    if record is not None else frozenset()
                ),
                expected_landmark_ids=(
                    tuple(str(value) for value in getattr(record, "generated_dom_id_bases", ()))
                    if record is not None else ()
                ),
            ))
        if len(diagnostics) >= _MAX_VISUAL_STAGE_DIAGNOSTICS:
            return diagnostics[:_MAX_VISUAL_STAGE_DIAGNOSTICS]
    return diagnostics[:_MAX_VISUAL_STAGE_DIAGNOSTICS]


def _css_diagnostic(message: str) -> Diagnostic:
    return Diagnostic(
        DOCUMENT_STRUCTURE_VIOLATION,
        _bounded_diagnostic_message("visual-stage CSS: ", message),
        "assets.visual-stage",
    )


def _bound_visual_stage_diagnostics(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    bounded: list[Diagnostic] = []
    visual_count = 0
    for diagnostic in diagnostics:
        is_visual = diagnostic.message.startswith("visual-stage ")
        if is_visual:
            if visual_count >= _MAX_VISUAL_STAGE_DIAGNOSTICS:
                continue
            visual_count += 1
        bounded.append(diagnostic)
    return bounded


def _remove_css_comments(source: str) -> str:
    """Remove comments while preserving strings and CSS token adjacency."""
    out: list[str] = []
    index = 0
    quote: str | None = None
    while index < len(source):
        char = source[index]
        if quote is not None:
            out.append(char)
            if char == "\\" and index + 1 < len(source):
                out.append(source[index + 1])
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            out.append(char)
            index += 1
            continue
        if source.startswith("/*", index):
            end = source.find("*/", index + 2)
            index = len(source) if end == -1 else end + 2
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _css_matching_brace(source: str, opening: int) -> int | None:
    depth = 1
    quote: str | None = None
    index = opening + 1
    while index < len(source):
        char = source[index]
        if quote is not None:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _css_rule_blocks(source: str):
    """Yield selector/declaration blocks, descending through grouping at-rules."""
    source = _remove_css_comments(source)
    index = 0
    start = 0
    quote: str | None = None
    parens = 0
    brackets = 0
    while index < len(source):
        char = source[index]
        if quote is not None:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "(":
            parens += 1
        elif char == ")" and parens:
            parens -= 1
        elif char == "[":
            brackets += 1
        elif char == "]" and brackets:
            brackets -= 1
        elif char == ";" and parens == 0 and brackets == 0:
            start = index + 1
        elif char == "{" and parens == 0 and brackets == 0:
            header = source[start:index].strip()
            closing = _css_matching_brace(source, index)
            if closing is None:
                return
            body = source[index + 1:closing]
            if header.startswith("@"):
                yield from _css_rule_blocks(body)
            else:
                yield header, body
            index = closing
            start = closing + 1
        index += 1


def _decode_css_escape(source: str, index: int) -> tuple[str, int]:
    if index >= len(source):
        return "", index
    match = re.match(r"[0-9a-fA-F]{1,6}", source[index:])
    if match is not None:
        digits = match.group(0)
        end = index + len(digits)
        if end < len(source) and source[end].isspace():
            end += 1
        value = int(digits, 16)
        return (chr(value) if 0 < value <= 0x10FFFF else "\ufffd"), end
    if source[index] in "\r\n\f":
        return "", index + 1
    return source[index], index + 1


def _decode_css_identifier(source: str) -> str:
    out: list[str] = []
    index = 0
    while index < len(source):
        if source[index] == "\\":
            decoded, index = _decode_css_escape(source, index + 1)
            out.append(decoded)
        else:
            out.append(source[index])
            index += 1
    return "".join(out)


def _selector_attribute_contents(selector: str) -> tuple[str, ...]:
    contents: list[str] = []
    index = 0
    quote: str | None = None
    while index < len(selector):
        char = selector[index]
        if quote is not None:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            index += 1
            continue
        if char != "[":
            if char == "\\":
                index += 2
            else:
                index += 1
            continue
        start = index + 1
        index = start
        inner_quote: str | None = None
        while index < len(selector):
            inner = selector[index]
            if inner_quote is not None:
                if inner == "\\":
                    index += 2
                    continue
                if inner == inner_quote:
                    inner_quote = None
                index += 1
                continue
            if inner in {'"', "'"}:
                inner_quote = inner
            elif inner == "]":
                contents.append(selector[start:index])
                break
            index += 1
        index += 1
    return tuple(contents)


def _attribute_selector_targets_highlight(content: str) -> bool:
    name_pattern = r"((?:\\.|[-_a-zA-Z0-9])+?)"
    value_pattern = r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|(?:\\.|[^\s])+?)'
    match = re.fullmatch(
        rf"\s*{name_pattern}\s*(~=|\^=|\$=|\*=|\|=|=)\s*"
        rf"{value_pattern}\s*((?:\\.|[iIsS0-9])*)\s*",
        content,
    )
    if match is None:
        return False
    name = _decode_css_identifier(match.group(1)).lower()
    if name != "class":
        return False
    operator = match.group(2)
    raw_value = match.group(3)
    if raw_value[:1] in {'"', "'"} and raw_value[-1:] == raw_value[:1]:
        raw_value = raw_value[1:-1]
    value = _decode_css_identifier(raw_value)
    flag = (_decode_css_identifier(match.group(4)) or "s").lower()
    if flag == "i":
        value = value.lower()
    if operator == "~=":
        return value in _HIGHLIGHT_CLASS_NAMES
    if operator == "=":
        return any(class_name in value.split() for class_name in _HIGHLIGHT_CLASS_NAMES)
    return bool(value) and any(
        class_name in value or value in class_name
        for class_name in _HIGHLIGHT_CLASS_NAMES
    )


def _selector_may_target_class(selector: str, class_name: str) -> bool:
    decoded = _decode_css_identifier(selector)
    if re.search(rf"\.{re.escape(class_name)}(?![-_a-zA-Z0-9])", decoded):
        return True
    for content in _selector_attribute_contents(decoded):
        name_pattern = r"((?:\\.|[-_a-zA-Z0-9])+?)"
        value_pattern = r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|(?:\\.|[^\s])+?)'
        match = re.fullmatch(
            rf"\s*{name_pattern}\s*(~=|\^=|\$=|\*=|\|=|=)\s*"
            rf"{value_pattern}\s*((?:\\.|[iIsS0-9])*)\s*",
            content,
        )
        if match is None or _decode_css_identifier(match.group(1)).lower() != "class":
            continue
        value = match.group(3)
        if value[:1] in {'"', "'"} and value[-1:] == value[:1]:
            value = value[1:-1]
        value = _decode_css_identifier(value)
        flag = (_decode_css_identifier(match.group(4)) or "s").lower()
        target = class_name
        if flag == "i":
            value, target = value.lower(), target.lower()
        operator = match.group(2)
        if operator == "~=" and value == target:
            return True
        if operator == "=" and target in value.split():
            return True
        if operator not in {"~=", "="} and value and (target in value or value in target):
            return True
    return False


def _selector_has_universal_target(selector: str) -> bool:
    """Recognize a universal selector without confusing attribute ``*=``."""
    decoded = _decode_css_identifier(selector)
    quote: str | None = None
    brackets = 0
    index = 0
    while index < len(decoded):
        char = decoded[index]
        if quote is not None:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in {'"', "'"}:
            quote = char
        elif char == "[":
            brackets += 1
        elif char == "]" and brackets:
            brackets -= 1
        elif char == "*" and brackets == 0:
            return True
        index += 1
    return False


def _selector_attribute_name(content: str) -> str:
    match = re.match(r"\s*([-_a-zA-Z0-9]+)", content)
    return match.group(1).lower() if match is not None else ""


def _selector_may_affect_path_sizing(selector: str) -> bool:
    """Conservatively classify controlled selectors that can size path mode."""
    if _selector_has_universal_target(selector):
        return True
    if any(
        _selector_may_target_class(selector, class_name)
        for class_name in (
            "ve-flow-scroll", "ve-flow-path-canvas", "ve-flow-station", "ve-flow-node",
        )
    ):
        return True
    decoded = _decode_css_identifier(selector)
    attributes = _selector_attribute_contents(decoded)
    if any(_selector_attribute_name(content) == "data-stepper" for content in attributes):
        return True
    return any(
        _selector_attribute_name(content) == "data-ve-component"
        and "flow" in content.lower()
        for content in attributes
    )


def _selector_may_affect_main_sizing(selector: str) -> bool:
    if _selector_has_universal_target(selector):
        return True
    decoded = _decode_css_identifier(selector)
    # Remove attribute contents and strings before looking for type selectors.
    syntax = decoded
    for content in _selector_attribute_contents(decoded):
        syntax = syntax.replace(f"[{content}]", " ")
    syntax = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', " ", syntax)
    return re.search(
        r"(?<![-_a-zA-Z0-9])(html|body|main)(?![-_a-zA-Z0-9])|:root\b",
        syntax,
        re.I,
    ) is not None


def _is_sizing_property(name: str) -> bool:
    if name in {
        "width", "min-width", "max-width", "height", "min-height", "max-height",
        "inline-size", "min-inline-size", "max-inline-size",
        "block-size", "min-block-size", "max-block-size",
        "gap", "row-gap", "column-gap", "grid-gap", "grid-row-gap", "grid-column-gap",
        "flex", "box-sizing", "display", "margin",
    }:
        return True
    return name.startswith(("flex-", "padding-", "border-", "margin-")) or name in {
        "padding", "border",
    }


def _selector_targets_highlight(selector: str) -> bool:
    decoded_selector = _decode_css_identifier(selector)
    if any(
        _attribute_selector_targets_highlight(content)
        for content in _selector_attribute_contents(decoded_selector)
    ):
        return True
    index = 0
    quote: str | None = None
    while index < len(decoded_selector):
        char = decoded_selector[index]
        if quote is not None:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            index += 1
            continue
        if char != ".":
            if char == "\\":
                index += 2
            else:
                index += 1
            continue
        index += 1
        raw: list[str] = []
        while index < len(decoded_selector):
            char = decoded_selector[index]
            if char == "\\" and index + 1 < len(decoded_selector):
                start = index
                _decoded, index = _decode_css_escape(decoded_selector, index + 1)
                raw.append(decoded_selector[start:index])
                continue
            if char.isalnum() or char in {"-", "_"} or ord(char) >= 128:
                raw.append(char)
                index += 1
                continue
            break
        if _decode_css_identifier("".join(raw)).lower() in _HIGHLIGHT_CLASS_NAMES:
            return True
    return False


def _css_declarations(body: str) -> tuple[tuple[str, str], ...]:
    declarations: list[tuple[str, str]] = []
    start = 0
    index = 0
    quote: str | None = None
    parens = 0
    segments: list[str] = []
    while index <= len(body):
        char = body[index] if index < len(body) else ";"
        if quote is not None:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in {'"', "'"}:
            quote = char
        elif char == "(":
            parens += 1
        elif char == ")" and parens:
            parens -= 1
        elif char == ";" and parens == 0:
            segments.append(body[start:index])
            start = index + 1
        index += 1
    for segment in segments:
        if ":" not in segment:
            continue
        name, value = segment.split(":", 1)
        decoded_name = _decode_css_identifier(_remove_css_comments(name).strip()).lower()
        if decoded_name:
            declarations.append((decoded_name, value.strip()))
    return tuple(declarations)


def _parsed_css_rules(source: str) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    return tuple(
        (selector.strip(), _css_declarations(body))
        for selector, body in _css_rule_blocks(source)
    )


def _unique_exact_declaration(
    rules: tuple[tuple[str, tuple[tuple[str, str], ...]], ...],
    selector: str,
    property_name: str,
) -> str | None:
    values = [
        value
        for candidate, declarations in rules
        if candidate == selector
        for name, value in declarations
        if name == property_name
    ]
    matching_rules = [candidate for candidate, _declarations in rules if candidate == selector]
    if len(matching_rules) != 1 or len(values) != 1:
        return None
    return values[0]


def _unique_root_token(
    rules: tuple[tuple[str, tuple[tuple[str, str], ...]], ...],
    token: str,
) -> str | None:
    definitions = [
        (selector, value)
        for selector, declarations in rules
        for name, value in declarations
        if name == token
    ]
    if len(definitions) != 1 or definitions[0][0] != ":root":
        return None
    return definitions[0][1]


def _skeleton_css(skeleton_markup: str) -> str:
    match = re.search(r"<style\b[^>]*>(.*?)</style>", skeleton_markup, re.I | re.S)
    return match.group(1) if match is not None else ""


def _rem_value(value: str) -> Decimal | None:
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)rem", value.strip(), re.I)
    if match is None:
        return None
    try:
        return Decimal(match.group(1))
    except InvalidOperation:
        return None


def _compact_css_value(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def _require_layout_declaration(
    diagnostics: list[Diagnostic],
    rules: tuple[tuple[str, tuple[tuple[str, str], ...]], ...],
    selector: str,
    property_name: str,
    expected_value: str,
) -> None:
    actual = _unique_exact_declaration(rules, selector, property_name)
    if actual is None or _compact_css_value(actual) != _compact_css_value(expected_value):
        diagnostics.append(_css_diagnostic(
            f"path layout の {selector!r} / {property_name} は"
            f" '{expected_value}' の一意な有効宣言が必要です",
        ))


def check_visual_stage_css(css: str, skeleton_markup: str) -> list[Diagnostic]:
    """Enforce emphasis paint-only rules and the skeleton-linked width equation."""
    diagnostics: list[Diagnostic] = []
    css_rules = _parsed_css_rules(css)
    skeleton_rules = _parsed_css_rules(_skeleton_css(skeleton_markup))
    for source_name, rules in (
        ("visual-stage", css_rules),
        ("skeleton", skeleton_rules),
    ):
        for selector, declarations in rules:
            for property_name, _value in declarations:
                if property_name in _GLOBAL_AXIS_RESET_PROPERTIES:
                    diagnostics.append(_css_diagnostic(
                        f"1212px {source_name} selector"
                        f" {_bounded_identifier(selector)!r} の {property_name} は"
                        "全 rule で禁止されています",
                    ))
    for selector, declarations in css_rules:
        if not _selector_targets_highlight(selector):
            continue
        for property_name, _value in declarations:
            if property_name not in _HIGHLIGHT_PAINT_PROPERTIES:
                diagnostics.append(_css_diagnostic(
                    f"強調 selector の '{property_name}' は paint-only allowlist 外です",
                ))

    css_vars: dict[str, str] = {}
    for name in _PATH_WIDTH_VARIABLES:
        value = _unique_root_token(css_rules, name)
        if value is None:
            diagnostics.append(_css_diagnostic(
                f"幅定数 '{name}' は exact :root に一意に宣言する必要があります",
            ))
        else:
            css_vars[name] = value
    width = _rem_value(css_vars.get(_PATH_WIDTH_VARIABLES[0], ""))
    gap = _rem_value(css_vars.get(_PATH_WIDTH_VARIABLES[1], ""))
    content_decl = css_vars.get(_PATH_WIDTH_VARIABLES[2], "")
    source_link = re.fullmatch(
        rf"var\(\s*{re.escape(_SKELETON_CONTENT_WIDTH_TOKEN)}\s*\)",
        content_decl,
        re.I,
    )
    if source_link is None:
        diagnostics.append(_css_diagnostic(
            "content width C は skeleton の --w-narrative token を var() で参照する必要があります",
        ))
    skeleton_content = _unique_root_token(skeleton_rules, _SKELETON_CONTENT_WIDTH_TOKEN)
    if skeleton_content is None:
        diagnostics.append(_css_diagnostic(
            "skeleton の --w-narrative は exact :root に一意に宣言する必要があります",
        ))
    content = _rem_value(skeleton_content or "")
    if width is None or gap is None or content is None:
        diagnostics.append(_css_diagnostic(
            "W・gap・skeleton content token C は rem の固定値として解決できる必要があります",
        ))
    elif width * 4 + gap * 3 > content:
        diagnostics.append(_css_diagnostic(
            f"幅式 4W + 3gap <= C に違反します（{width * 4 + gap * 3}rem > {content}rem）",
        ))

    main_rules = [declarations for selector, declarations in skeleton_rules if selector == "main"]
    expected_main_width = "min(100% - var(--space-4), var(--w-narrative))"
    allowed_main_widths = {
        _compact_css_value(expected_main_width),
        _compact_css_value("min(100% - var(--space-2), var(--w-narrative))"),
    }
    base_contracts = 0
    main_invalid = not main_rules
    for declarations in main_rules:
        values_by_name: dict[str, list[str]] = {}
        for name, value in declarations:
            values_by_name.setdefault(name, []).append(value)
        for value in values_by_name.get("width", []):
            if _compact_css_value(value) not in allowed_main_widths:
                main_invalid = True
        for name in ("padding-inline", "padding-left", "padding-right"):
            if any(_compact_css_value(value) != "0" for value in values_by_name.get(name, [])):
                main_invalid = True
        widths = values_by_name.get("width", [])
        paddings = values_by_name.get("padding", [])
        if len(widths) == 1 and _compact_css_value(widths[0]) == _compact_css_value(expected_main_width):
            if len(paddings) != 1:
                main_invalid = True
                continue
            padding_parts = paddings[0].split()
            inline_zero = (
                len(padding_parts) == 2 and padding_parts[1] == "0"
                or len(padding_parts) == 3 and padding_parts[1] == "0"
                or len(padding_parts) == 4
                and padding_parts[1] == "0"
                and padding_parts[3] == "0"
            )
            if inline_zero:
                base_contracts += 1
            else:
                main_invalid = True
    for selector, declarations in skeleton_rules:
        decoded_selector = _decode_css_identifier(selector)
        if selector == "main" or re.search(
            r"(?<![-_a-zA-Z0-9])main(?![-_a-zA-Z0-9])",
            decoded_selector,
        ) is None:
            continue
        if any(
            name in {"width", "max-width", "padding", "padding-inline", "padding-left", "padding-right"}
            for name, _value in declarations
        ):
            main_invalid = True
    if main_invalid or base_contracts != 1:
        diagnostics.append(_css_diagnostic(
            "1212px skeleton main は --w-narrative linked width と inline padding 0 の一意な宣言が必要です",
        ))

    _require_layout_declaration(
        diagnostics, css_rules, _PATH_SCROLL_SELECTOR, "max-width",
        "var(--ve-path-spotlight-content-width)",
    )
    _require_layout_declaration(
        diagnostics, css_rules, _PATH_CANVAS_SELECTOR, "gap",
        "var(--ve-path-spotlight-gap)",
    )
    _require_layout_declaration(
        diagnostics, css_rules, _PATH_CANVAS_SELECTOR, "max-width",
        "var(--ve-path-spotlight-content-width)",
    )
    _require_layout_declaration(
        diagnostics, css_rules, _PATH_STATION_SELECTOR, "flex",
        "0 0 var(--ve-path-spotlight-node-width)",
    )
    _require_layout_declaration(
        diagnostics, css_rules, _PATH_STATION_SELECTOR, "max-width",
        "var(--ve-path-spotlight-node-width)",
    )
    _require_layout_declaration(
        diagnostics, css_rules, _PATH_NODE_SELECTOR, "max-width",
        "var(--ve-path-spotlight-node-width)",
    )
    permitted_path_layout = {
        (_PATH_SCROLL_SELECTOR, "max-width", "var(--ve-path-spotlight-content-width)"),
        (_PATH_CANVAS_SELECTOR, "gap", "var(--ve-path-spotlight-gap)"),
        (_PATH_CANVAS_SELECTOR, "max-width", "var(--ve-path-spotlight-content-width)"),
        (_PATH_CANVAS_SELECTOR, "width", "100%"),
        (_PATH_CANVAS_SELECTOR, "min-width", "0"),
        (_PATH_CANVAS_SELECTOR, "box-sizing", "border-box"),
        (_PATH_CANVAS_SELECTOR, "display", "flex"),
        (_PATH_CANVAS_SELECTOR, "flex-wrap", "wrap"),
        (_PATH_STATION_SELECTOR, "flex", "0 0 var(--ve-path-spotlight-node-width)"),
        (_PATH_STATION_SELECTOR, "max-width", "var(--ve-path-spotlight-node-width)"),
        (_PATH_STATION_SELECTOR, "min-width", "0"),
        (_PATH_STATION_SELECTOR, "box-sizing", "border-box"),
        (_PATH_NODE_SELECTOR, "max-width", "var(--ve-path-spotlight-node-width)"),
        (_PATH_NODE_SELECTOR, "width", "100%"),
        (_PATH_NODE_SELECTOR, "min-width", "0"),
        (_PATH_NODE_SELECTOR, "box-sizing", "border-box"),
        (_PATH_NODE_SELECTOR, "display", "block"),
    }
    for selector, declarations in css_rules:
        if not _selector_may_affect_path_sizing(selector):
            continue
        for name, value in declarations:
            if not _is_sizing_property(name):
                continue
            candidate = (selector, name, value)
            if not any(
                candidate[0] == allowed[0]
                and candidate[1] == allowed[1]
                and _compact_css_value(candidate[2]) == _compact_css_value(allowed[2])
                for allowed in permitted_path_layout
            ):
                diagnostics.append(_css_diagnostic(
                    f"1212px path layout の selector {_bounded_identifier(selector)!r} が"
                    f" {name} を契約外で上書きしています",
                ))

    permitted_skeleton_layout = {
        ("*", "box-sizing", "border-box"),
        ("main", "width", expected_main_width),
        ("main", "width", "min(100% - var(--space-2), var(--w-narrative))"),
        ("main", "padding", "var(--space-4) 0 var(--space-6)"),
        ("main", "padding-top", "var(--space-2)"),
        ("main", "margin", "0 auto"),
        ("body", "margin", "0"),
    }
    universal_border_box = 0
    for selector, declarations in skeleton_rules:
        decoded_selector = _decode_css_identifier(selector).strip()
        affects_main = _selector_may_affect_main_sizing(selector)
        for name, value in declarations:
            if not _is_sizing_property(name):
                continue
            compact = _compact_css_value(value)
            if decoded_selector == "*" and name == "box-sizing" and compact == "border-box":
                universal_border_box += 1
            candidate = (decoded_selector, name, value)
            allowed = any(
                candidate[0] == permitted[0]
                and candidate[1] == permitted[1]
                and _compact_css_value(candidate[2]) == _compact_css_value(permitted[2])
                for permitted in permitted_skeleton_layout
            )
            if affects_main and not allowed:
                diagnostics.append(_css_diagnostic(
                    f"1212px skeleton selector {_bounded_identifier(selector)!r} の {name} は"
                    " content width/padding/border/box-sizing の閉じた宣言元に違反します",
                ))
    if universal_border_box != 1:
        diagnostics.append(_css_diagnostic(
            "1212px skeleton は exact '*' で box-sizing:border-box を一意に宣言する必要があります",
        ))
    return diagnostics[:_MAX_VISUAL_STAGE_DIAGNOSTICS]


class _StyleAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.visual_stage_bodies: list[str] = []
        self._collecting = False
        self._body: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "style":
            return
        values = {name.lower(): (value or "") for name, value in attrs}
        self._collecting = values.get("data-ve-asset") == "visual-stage"
        self._body = []

    def handle_data(self, data: str) -> None:
        if self._collecting:
            self._body.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._collecting:
            self._body.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._collecting:
            self._body.append(f"&#{name};")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "style" and self._collecting:
            self.visual_stage_bodies.append("".join(self._body))
            self._collecting = False
            self._body = []


def _check_visual_stage_style_slot(styles_markup: str, skeleton_markup: str) -> list[Diagnostic]:
    parser = _StyleAssetParser()
    parser.feed(styles_markup)
    parser.close()
    if len(parser.visual_stage_bodies) != 1:
        return [_css_diagnostic(
            f"visual-stage style asset はちょうど1個必要です（実測 {len(parser.visual_stage_bodies)}）",
        )]
    return check_visual_stage_css(parser.visual_stage_bodies[0], skeleton_markup)


def check_visual_stage_document_css(
    content_markup: str,
    styles_markup: str,
    skeleton_markup: str,
    *,
    max_diagnostics: int = _MAX_VISUAL_STAGE_DIAGNOSTICS,
) -> list[Diagnostic]:
    """Profile-gated CSS contract entry point for the final-document checker."""
    structure = _parse_structure(content_markup)
    first_nodes = [node for node in structure.sections if node.kind == "first-screen"]
    if len(first_nodes) != 1:
        return []
    if first_nodes[0].attrs.get("data-ve-profile") != _VISUAL_STAGE_PROFILE:
        return []
    return _check_visual_stage_style_slot(styles_markup, skeleton_markup)[:max(0, max_diagnostics)]


def _rendered_narrative_text_length(
    node: _SectionNode,
    *,
    generated_wrapper: bool,
) -> int:
    """Count author text, conditionally removing generated wrapper newlines.

    ``process_narrative_section`` emits one structural ``\n`` immediately
    inside each side of the section wrapper. Removing exactly those code
    points is safe only on the build path carrying expected provenance.
    Standalone artifact markup has no such provenance, so every decoded text
    code point is counted unchanged.
    """
    text = "".join(node.text_parts)
    if generated_wrapper:
        if text.startswith("\n"):
            text = text[1:]
        if text.endswith("\n"):
            text = text[:-1]
    return _plain_text_character_count((text,))


def _normalize_overlap_text(text: str) -> str:
    """Apply the fixed assertion/narrative comparison normalization.

    The threshold is measured in Python Unicode code points after entity
    decoding and NFKC normalization.  Every Unicode separator, punctuation,
    symbol, and whitespace code point is removed; letters, marks, and numbers
    remain significant.
    """
    normalized = unicodedata.normalize("NFKC", unescape(text))
    return "".join(
        char
        for char in normalized
        if not char.isspace() and unicodedata.category(char)[0] not in {"P", "S", "Z"}
    )


def _has_common_substring_at_least(
    left: str,
    right: str,
    minimum: int = _MIN_VISUAL_STAGE_OVERLAP_CHARS,
) -> bool:
    """Return whether two strings share a contiguous substring of ``minimum``.

    A longest-common-substring has length at least ``minimum`` exactly when
    the strings share one ``minimum``-code-point window.  Comparing fixed-size
    windows gives the specified LCS threshold result in linear time and keeps
    memory proportional to the shorter input instead of allocating an LCS
    matrix for rendered prose.
    """
    if minimum <= 0:
        return True
    if len(left) < minimum or len(right) < minimum:
        return False
    if len(left) > len(right):
        left, right = right, left
    windows = {
        left[index:index + minimum]
        for index in range(len(left) - minimum + 1)
    }
    return any(
        right[index:index + minimum] in windows
        for index in range(len(right) - minimum + 1)
    )


def _check_visual_stage_completeness(
    structure: _DocStructure,
    expected,
) -> list[Diagnostic]:
    """Recheck rendered visual-stage completeness against immutable IR facts.

    ``expected is None`` denotes the documented artifact-only checking route;
    the IR-dependent checks are unavailable there.  If the build route supplies
    an expected collection, an empty or malformed collection fails closed.
    """
    diagnostics: list[Diagnostic] = []

    def add(message: str, path: str = "content") -> None:
        if len(diagnostics) < _MAX_VISUAL_STAGE_DIAGNOSTICS:
            diagnostics.append(_visual_stage_diagnostic(message, path))

    narrative_nodes = [node for node in structure.sections if node.kind == "narrative"]
    if len(narrative_nodes) > MAX_VISUAL_STAGE_NARRATIVE_SECTIONS:
        add(
            f"narrative section は最大{MAX_VISUAL_STAGE_NARRATIVE_SECTIONS}件です"
            f"（実測 {len(narrative_nodes)}件）",
            "content.narrative",
        )
    for node in narrative_nodes:
        text_length = _rendered_narrative_text_length(
            node,
            generated_wrapper=expected is not None,
        )
        if text_length > MAX_VISUAL_STAGE_NARRATIVE_CHARS:
            instance_id = node.attrs.get("data-ve-instance", "<unknown>")
            add(
                f"narrative '{instance_id}' の plain text は"
                f"{MAX_VISUAL_STAGE_NARRATIVE_CHARS}字以内です（実測 {text_length}字）",
                f"content.narrative[{instance_id}]",
            )

    # Standalone HTML checking deliberately has no immutable IR inventory.
    if expected is None:
        return diagnostics

    try:
        records = tuple(expected)
    except TypeError:
        add("expected record collection が不正です", "expected")
        return diagnostics
    if not records:
        add("canonical の expected record がありません", "expected")
        return diagnostics

    canonical_nodes = [node for node in structure.sections if node.kind == "canonical"]
    nodes_by_instance: dict[str, list[_SectionNode]] = {}
    for node in canonical_nodes:
        instance_id = node.attrs.get("data-ve-instance", "")
        nodes_by_instance.setdefault(instance_id, []).append(node)

    records_by_instance: dict[str, object] = {}
    required_fields = (
        "component_id", "instance_id", "payload_semantic_ids",
        "claim", "assertions", "sequence",
    )
    for index, record in enumerate(records):
        if any(not hasattr(record, name) for name in required_fields):
            add(f"expected record[{index}] が必要フィールドを欠いています", f"expected[{index}]")
            continue
        instance_id = str(record.instance_id)
        if instance_id in records_by_instance:
            add(f"canonical '{instance_id}' の expected record が重複しています", f"expected[{index}]")
            continue
        records_by_instance[instance_id] = record

    normalized_narratives = tuple(
        (
            narrative.attrs.get("data-ve-instance", "<unknown>"),
            _normalize_overlap_text("".join(narrative.text_parts)),
        )
        for narrative in narrative_nodes
    )

    for instance_id in sorted(set(nodes_by_instance) - set(records_by_instance)):
        label = instance_id or "<missing-instance-id>"
        add(f"canonical '{label}' に対応する expected record がありません", f"content.canonical[{label}]")

    seen_step_ids: set[str] = set()
    for instance_id, record in records_by_instance.items():
        path = f"content.canonical[{instance_id}]"
        matching_nodes = nodes_by_instance.get(instance_id, [])
        if len(matching_nodes) != 1:
            add(
                f"expected canonical '{instance_id}' に対応する描画 canonical は1件必要です"
                f"（実測 {len(matching_nodes)}件）",
                path,
            )
            node = None
        else:
            node = matching_nodes[0]

        claim = record.claim
        assertions = record.assertions
        if not isinstance(claim, str) or not claim:
            add(f"canonical '{instance_id}' の claim は必須です", path)
        if not isinstance(assertions, tuple) or not assertions:
            add(f"canonical '{instance_id}' の assertions は必須です", path)
            assertion_items = ()
        else:
            assertion_items = assertions

        assertion_texts = {
            assertion.text for assertion in assertion_items
            if isinstance(getattr(assertion, "text", None), str)
        }
        if isinstance(claim, str) and claim and claim not in assertion_texts:
            add(
                f"canonical '{instance_id}' の claim は assertion.text のいずれかと一致する必要があります",
                path,
            )

        if isinstance(claim, str) and claim and node is not None:
            # T12 checks lossless transfer. T14 owns the separate structural
            # cardinality/placement rule for the claim element.
            if claim not in node.claim_texts:
                add(
                    f"canonical '{instance_id}' の IR claim と .ve-claim が一致しません"
                    f"（描画件数 {len(node.claim_texts)}件）",
                    path,
                )

        for assertion in assertion_items:
            assertion_text = getattr(assertion, "text", None)
            if not isinstance(assertion_text, str):
                continue
            normalized_assertion = _normalize_overlap_text(assertion_text)
            if not normalized_assertion:
                continue
            assertion_id = str(getattr(assertion, "id", "<unknown>"))
            for narrative_id, normalized_narrative in normalized_narratives:
                if _has_common_substring_at_least(
                    normalized_assertion,
                    normalized_narrative,
                ):
                    add(
                        f"claim/narrative 語句重複: canonical '{instance_id}' assertion "
                        f"'{assertion_id}' と narrative '{narrative_id}' に正規化後"
                        f"{_MIN_VISUAL_STAGE_OVERLAP_CHARS}文字以上の共通部分文字列があります",
                        f"content.narrative[{narrative_id}]",
                    )

        try:
            payload_ids = frozenset(str(value) for value in record.payload_semantic_ids)
        except TypeError:
            add(f"canonical '{instance_id}' の payload semantic id 集合が不正です", path)
            payload_ids = frozenset()

        covered_ids: set[str] = set()
        for assertion in assertion_items:
            assertion_id = str(getattr(assertion, "id", "<unknown>"))
            cover_ids = getattr(assertion, "cover_ids", None)
            if not isinstance(cover_ids, tuple) or not cover_ids:
                add(
                    f"canonical '{instance_id}' assertion '{assertion_id}' の coverIds は必須です",
                    path,
                )
                continue
            normalized_cover_ids = {str(value) for value in cover_ids}
            covered_ids.update(normalized_cover_ids)
            dangling = normalized_cover_ids - payload_ids
            if dangling:
                add(
                    f"canonical '{instance_id}' assertion '{assertion_id}' の coverIds が"
                    f" payload に存在しません: {_bounded_id_list(dangling)}",
                    path,
                )

        uncovered = payload_ids - covered_ids
        if uncovered:
            add(
                f"canonical '{instance_id}' の payload semantic id が assertions で未カバーです: "
                f"{_bounded_id_list(uncovered)}",
                path,
            )

        sequence = record.sequence
        if sequence is None:
            continue
        steps = getattr(sequence, "steps", None)
        if not isinstance(steps, tuple):
            add(f"canonical '{instance_id}' の sequence steps が不正です", path)
            continue
        for step in steps:
            step_id = str(getattr(step, "id", "<unknown>"))
            if step_id in seen_step_ids:
                add(f"sequence step id '{step_id}' が文書内で重複しています", path)
            else:
                seen_step_ids.add(step_id)
            target_ids = getattr(step, "target_ids", None)
            if not isinstance(target_ids, tuple):
                add(f"sequence step '{step_id}' の targetIds が不正です", path)
                continue
            dangling = {str(value) for value in target_ids} - payload_ids
            if dangling:
                add(
                    f"sequence step '{step_id}' の targetIds が payload に存在しません: "
                    f"{_bounded_id_list(dangling)}",
                    path,
                )

    return diagnostics


def check_document_structure(
    content_markup: str,
    *,
    title: str | None = None,
    expected=None,
) -> list[Diagnostic]:
    """Inspect flattened content markup for group-3 structure invariants.

    ``title`` is the document ``<title>`` text (from the TITLE slot; may still
    contain character references). When omitted, the title↔h1 equality check
    is skipped. ``expected`` carries immutable canonical IR facts on the build
    path; standalone HTML checks pass ``None``.
    """
    diagnostics: list[Diagnostic] = []
    structure = _parse_structure(content_markup)
    if structure.self_closing_tags:
        tags = ", ".join(f"<{tag}/>" for tag in structure.self_closing_tags)
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            f"自己閉じタグは許容されません（ブラウザとの解釈差異のため）: {tags}",
            "content",
        ))
        return diagnostics
    if structure.misplaced_reserved_attrs:
        offenders = ", ".join(
            f"<{tag} {attr}>" for tag, attr in structure.misplaced_reserved_attrs
        )
        diagnostics.append(Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            f"構造予約属性が許可されない要素にあります: {offenders}",
            "content",
        ))
        return diagnostics
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
    if profile == _VISUAL_STAGE_PROFILE:
        diagnostics.extend(_check_visual_stage_completeness(structure, expected))
        diagnostics.extend(_check_visual_stage_sequences(content_markup, expected))
        diagnostics = _bound_visual_stage_diagnostics(diagnostics)
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
    if len(closing_nodes) != 1:
        return [Diagnostic(
            DOCUMENT_STRUCTURE_VIOLATION,
            "closing はちょうど1個必要です",
            "content",
        )]
    if doc_type is None:
        return []
    required = _CLOSING_REQUIRED.get(doc_type, ())
    headings = set(closing_nodes[0].h2_texts)
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
