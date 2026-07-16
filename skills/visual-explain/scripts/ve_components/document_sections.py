"""Typed document sections: first-screen, closing, ask, and the build-time TOC.

These are trusted renderers that bypass the component registry: their inputs are
validated dataclasses, their markup uses only fixed skeleton classes, and the
final checker (group 3) re-verifies the result in the flattened document.
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from html.parser import HTMLParser

from .model import (
    AskSection,
    CERTAINTY_LABEL,
    ClosingSection,
    DocumentMetadata,
    FirstScreenSection,
)

_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})
_TOC_INSTANCE_ID = "sec-toc"
_TOC_MIN_ENTRIES = 5

_SUBTITLE_LABEL = {"proposal": "あなたが決めること", "system": "この資料が答える問い",
                   "research": "この資料が答える問い"}
_ASK_KIND_LABEL = {
    "decision": "判断してください",
    "request": "お願いする動作",
    "hypothesis": "検証待ちの仮説",
}


@dataclass(frozen=True)
class WrappedDocumentSection:
    instance_id: str
    markup: str


@dataclass(frozen=True)
class TocEntry:
    anchor_id: str
    heading: str


def _esc(value: str) -> str:
    return html.escape(value)


class _FirstH2H3Parser(HTMLParser):
    """Extract the first h2/h3 text the same way as check.sh ContentInspector.headings."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.active: tuple[int, list[str]] | None = None
        self.result: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag not in _VOID_TAGS:
            self.stack.append(tag)
        depth = len(self.stack)
        if self.result is None and self.active is None and tag in {"h2", "h3"}:
            self.active = (depth, [])

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _VOID_TAGS or not self.stack:
            return
        depth = len(self.stack)
        if self.active is not None and self.active[0] == depth:
            text = "".join(self.active[1]).strip()
            self.result = text if text else None
            self.active = None
        self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self.active is not None:
            self.active[1].append(data)


def extract_first_h2_h3(markup: str) -> str | None:
    """Return the text of the first h2/h3 in markup, or None if absent/blank."""
    parser = _FirstH2H3Parser()
    parser.feed(markup)
    parser.close()
    return parser.result


def build_toc(entries: tuple[TocEntry, ...]) -> WrappedDocumentSection | None:
    """Build a flat TOC section when there are at least five headed body sections."""
    if len(entries) < _TOC_MIN_ENTRIES:
        return None
    items = "".join(
        f'<li><a href="#{_esc(entry.anchor_id)}">{_esc(entry.heading)}</a></li>'
        for entry in entries
    )
    markup = (
        f'<section data-ve-section-kind="toc">\n'
        f'<nav aria-label="目次"><ol>{items}</ol></nav>\n'
        f"</section>"
    )
    return WrappedDocumentSection(instance_id=_TOC_INSTANCE_ID, markup=markup)


def render_first_screen(section: FirstScreenSection, document: DocumentMetadata) -> WrappedDocumentSection:
    conditions = ""
    if section.conditions:
        items = "".join(f"<li>{_esc(c)}</li>" for c in section.conditions)
        conditions = f'\n  <ul class="conditions">{items}</ul>'
    label = _SUBTITLE_LABEL[document.type]
    markup = (
        f'<section data-ve-section-kind="first-screen"'
        f' data-ve-document-type="{_esc(document.type)}" data-ve-profile="{_esc(document.profile)}"'
        f' id="{_esc(section.id)}">\n'
        f'<section class="first-screen" aria-label="最初に伝えること">\n'
        f'  <h1>{_esc(document.title)}</h1>\n'
        f'  <p class="subtitle decision"><strong>{label}:</strong> {_esc(section.decision)}</p>\n'
        f'  <p class="subtitle">{_esc(document.summary)}</p>{conditions}\n'
        f'</section>\n</section>'
    )
    return WrappedDocumentSection(instance_id=section.id, markup=markup)


def render_closing(section: ClosingSection) -> WrappedDocumentSection:
    parts: list[str] = []
    for block in section.blocks:
        items = "".join(f"<li>{_esc(item)}</li>" for item in block.items)
        parts.append(f"  <h2>{_esc(block.heading)}</h2>\n  <ul>{items}</ul>")
    body = "\n".join(parts)
    markup = (
        f'<section data-ve-section-kind="closing" id="{_esc(section.id)}">\n'
        f'<section class="closing-section" aria-label="判断材料">\n'
        f"{body}\n"
        f"</section>\n</section>"
    )
    return WrappedDocumentSection(instance_id=section.id, markup=markup)


def render_ask(section: AskSection) -> WrappedDocumentSection:
    kind = section.ask_type
    kind_label = _ASK_KIND_LABEL[kind]
    if kind == "decision":
        body = _render_decision_body(section, kind_label)
    elif kind == "request":
        body = _render_request_body(section, kind_label)
    else:
        body = _render_hypothesis_body(section, kind_label)
    markup = (
        f'<section data-ve-section-kind="ask" data-ve-ask-type="{_esc(kind)}"'
        f' id="{_esc(section.id)}">\n'
        f'{body}\n'
        f"</section>"
    )
    return WrappedDocumentSection(instance_id=section.id, markup=markup)


def _render_decision_body(section: AskSection, kind_label: str) -> str:
    options_html: list[str] = []
    for opt in section.options:
        attrs = "data-ask-option"
        if section.default_id is not None and opt.id == section.default_id:
            attrs += " data-ask-default"
        options_html.append(
            f"<li {attrs}><span>{_esc(opt.label)}</span>"
            f'<span class="ask-tradeoff">{_esc(opt.tradeoff)}</span></li>'
        )
    reason = ""
    if section.no_default_reason:
        reason = (
            f'\n  <p class="ask-no-default-reason">{_esc(section.no_default_reason)}</p>'
        )
    return (
        f'<div class="ask" data-ask="decision">\n'
        f'  <p class="ask-kind">{_esc(kind_label)}</p>\n'
        f'  <p class="ask-question">{_esc(section.question or "")}</p>\n'
        f'  <ul class="ask-options">\n'
        f'    {"".join(options_html)}\n'
        f"  </ul>{reason}\n"
        f"</div>"
    )


def _render_request_body(section: AskSection, kind_label: str) -> str:
    steps_html = "".join(
        f'<li data-ask-role="{_esc(step.role)}" '
        f'data-ask-role-label="{_esc(step.role_label)}">{_esc(step.text)}</li>'
        for step in section.steps
    )
    return (
        f'<div class="ask" data-ask="request">\n'
        f'  <p class="ask-kind">{_esc(kind_label)}</p>\n'
        f'  <ol class="ask-steps">\n'
        f"    {steps_html}\n"
        f"  </ol>\n"
        f"</div>"
    )


def _render_hypothesis_body(section: AskSection, kind_label: str) -> str:
    assert section.claim is not None
    certainty = section.claim.certainty
    certainty_label = CERTAINTY_LABEL[certainty]
    return (
        f'<div class="ask" data-ask="hypothesis">\n'
        f'  <p class="ask-kind">{_esc(kind_label)}</p>\n'
        f'  <p class="ask-claim">{_esc(section.claim.text)} '
        f'<span class="certainty {certainty}">{_esc(certainty_label)}</span></p>\n'
        f'  <p class="ask-verify">{_esc(section.verify or "")}</p>\n'
        f"</div>"
    )
