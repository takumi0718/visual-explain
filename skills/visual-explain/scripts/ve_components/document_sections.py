"""Typed document sections: first-screen, closing, ask, and the build-time TOC.

These are trusted renderers that bypass the component registry: their inputs are
validated dataclasses, their markup uses only fixed skeleton classes, and the
final checker (group 3) re-verifies the result in the flattened document.
"""
from __future__ import annotations

import hashlib
import html
import json
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
_TOC_INSTANCE_ID_PREFIX = "sec-toc"
_TOC_MIN_ENTRIES = 5
_PANEL_INSTANCE_ID_PREFIX = "sec-decision-panel"

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


def _allocate_instance_id(prefix: str, occupied_ids: frozenset[str] | set[str]) -> str:
    """Pick a compose-only instance id that does not collide with section ids."""
    if prefix not in occupied_ids:
        return prefix
    n = 2
    while True:
        candidate = f"{prefix}-{n}"
        if candidate not in occupied_ids:
            return candidate
        n += 1


def allocate_toc_instance_id(occupied_ids: frozenset[str] | set[str]) -> str:
    """Pick a compose-only TOC instance id that does not collide with section ids.

    Compatibility wrapper around ``_allocate_instance_id``.
    """
    return _allocate_instance_id(_TOC_INSTANCE_ID_PREFIX, occupied_ids)


def build_toc(
    entries: tuple[TocEntry, ...],
    *,
    occupied_ids: frozenset[str] | set[str] = frozenset(),
) -> WrappedDocumentSection | None:
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
    return WrappedDocumentSection(
        instance_id=allocate_toc_instance_id(occupied_ids),
        markup=markup,
    )


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
        attrs = f'data-ask-option data-ask-option-id="{_esc(opt.id)}"'
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
    memo = (
        '\n  <div class="ask-memo">'
        '<label>メモ（この判断について）<textarea data-ask-memo></textarea></label></div>'
    )
    return (
        f'<div class="ask" data-ask="decision">\n'
        f'  <p class="ask-kind">{_esc(kind_label)}</p>\n'
        f'  <p class="ask-question">{_esc(section.question or "")}</p>\n'
        f'  <ul class="ask-options">\n'
        f'    {"".join(options_html)}\n'
        f"  </ul>{reason}{memo}\n"
        f"</div>"
    )


def compute_ask_digest_from_pairs(pairs: tuple[tuple[str, tuple[str, ...]], ...]) -> str:
    """Ask-contract digest: sha256 over the JSON-canonical [askId, [optionIds]] list.

    JSON encoding keeps ids with delimiter characters (",", ";", "=") from
    colliding across field boundaries.
    """
    payload = json.dumps([[ask_id, list(option_ids)] for ask_id, option_ids in pairs],
                         ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def compute_ask_digest(asks: tuple[AskSection, ...]) -> str:
    pairs = tuple((a.id, tuple(o.id for o in a.options))
                  for a in asks if a.ask_type == "decision")
    return compute_ask_digest_from_pairs(pairs)


def render_decision_panel(
    asks: tuple[AskSection, ...],
    document: DocumentMetadata,
    schema_version: int,
    document_path: str,
    *,
    occupied_ids: frozenset[str] | set[str] = frozenset(),
) -> WrappedDocumentSection | None:
    """Build the decision-recovery panel inserted after closing.

    Returns ``None`` when there are no decision-type asks (an empty panel is
    never emitted). Static markup only: JS-driven selection sync, copy
    controls, and status updates are Task 5.
    """
    decisions = tuple(a for a in asks if a.ask_type == "decision")
    if not decisions:
        return None
    digest = compute_ask_digest(asks)
    items_html = "".join(_render_panel_ask_item(a) for a in decisions)
    instance_id = _allocate_instance_id(_PANEL_INSTANCE_ID_PREFIX, occupied_ids)
    body = (
        '<section class="decision-panel" aria-label="判断の回収">\n'
        "  <h2>判断の回収</h2>\n"
        '  <ul class="panel-asks">\n'
        f"    {items_html}\n"
        "  </ul>\n"
        '  <div class="ask-memo"><label>全体メモ'
        "<textarea data-ve-panel-global-memo></textarea></label></div>\n"
        '  <p class="panel-note">選択の反映・メモの保存・コピーはブラウザの'
        "JavaScript が有効なときに使えます。</p>\n"
        "</section>"
    )
    markup = (
        f'<section data-ve-section-kind="decision-panel"'
        f' data-ve-document-id="{_esc(document.id)}"'
        f' data-ve-schema-version="{schema_version}"'
        f' data-ve-ask-digest="{_esc(digest)}"'
        f' data-ve-document-path="{_esc(document_path)}"'
        f' id="{_esc(instance_id)}">\n'
        f"{body}\n"
        f"</section>"
    )
    return WrappedDocumentSection(instance_id=instance_id, markup=markup)


def _render_panel_ask_item(section: AskSection) -> str:
    default_label = None
    if section.default_id is not None:
        default_label = next(
            (opt.label for opt in section.options if opt.id == section.default_id), None
        )
    status = f"未選択（既定案: {default_label}）" if default_label is not None else "未選択（既定案なし）"
    return (
        f'<li data-ve-panel-ask="{_esc(section.id)}">'
        f'<span class="panel-question">{_esc(section.question or "")}</span>'
        f'<span class="panel-status" data-ve-panel-status>{_esc(status)}</span>'
        f'<span class="panel-memo" data-ve-panel-memo hidden></span>'
        f"</li>"
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
