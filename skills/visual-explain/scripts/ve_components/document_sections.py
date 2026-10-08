"""Typed document sections: first-screen, closing, ask, and the overview marker list.

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
_OVERVIEW_NAV_INSTANCE_ID_PREFIX = "sec-overview-nav"
_PANEL_INSTANCE_ID_PREFIX = "sec-decision-panel"

_ASK_KIND_LABEL = {
    "decision": "判断してください",
    "request": "お願いする動作",
    "hypothesis": "検証待ちの仮説",
}


@dataclass(frozen=True)
class WrappedDocumentSection:
    instance_id: str
    markup: str


def _esc(value: str) -> str:
    return html.escape(value)


class _FirstH2H3Parser(HTMLParser):
    """Extract the first h2/h3 text the same way as check.sh ContentInspector.headings."""

    def __init__(self, levels: frozenset[str] = frozenset({"h2", "h3"})) -> None:
        super().__init__(convert_charrefs=True)
        self._levels = levels
        self.stack: list[str] = []
        self.active: tuple[int, list[str]] | None = None
        self.result: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag not in _VOID_TAGS:
            self.stack.append(tag)
        depth = len(self.stack)
        if self.result is None and self.active is None and tag in self._levels:
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


def extract_first_h2(markup: str) -> str | None:
    """Return the text of the first h2 in markup (h3 ignored), or None if absent/blank."""
    parser = _FirstH2H3Parser(frozenset({"h2"}))
    parser.feed(markup)
    parser.close()
    return parser.result


class _FirstHeadingFinder(HTMLParser):
    """Record the source position of the first h2 and the first h3 start tag."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: dict[str, tuple[int, int]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"h2", "h3"} and tag not in self.found:
            self.found[tag] = self.getpos()


def mark_first_heading(markup: str, n: int) -> str:
    """Stamp ``data-ve-marker="n"`` on the first h2 (else h3) of trusted-validated markup.

    The skeleton draws the number with CSS, so the heading text, copy output
    and text counts stay exactly as authored. Markup without a heading is
    returned unchanged.
    """
    finder = _FirstHeadingFinder()
    finder.feed(markup)
    finder.close()
    tag = "h2" if "h2" in finder.found else "h3" if "h3" in finder.found else None
    if tag is None:
        return markup
    lineno, col = finder.found[tag]
    lines = markup.split("\n")
    index = sum(len(line) + 1 for line in lines[:lineno - 1]) + col + 1 + len(tag)
    return f'{markup[:index]} data-ve-marker="{n}"{markup[index:]}'


def _marker_attr(marker: int | None) -> str:
    return f' data-ve-marker="{marker}"' if marker is not None else ""


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


def render_first_screen(section: FirstScreenSection, document: DocumentMetadata) -> WrappedDocumentSection:
    markup = (
        f'<section data-ve-section-kind="first-screen"'
        f' data-ve-document-type="{_esc(document.type)}" data-ve-profile="{_esc(document.profile)}"'
        f' id="{_esc(section.id)}">\n'
        f'<section class="first-screen" aria-label="最初に伝えること">\n'
        f'  <h1>{_esc(document.title)}</h1>\n'
        f'  <p class="conclusion"><strong>結論:</strong> {_esc(section.conclusion)}</p>\n'
        f'</section>\n</section>'
    )
    return WrappedDocumentSection(instance_id=section.id, markup=markup)


def build_overview_nav(
    first: FirstScreenSection,
    *,
    occupied_ids: frozenset[str] | set[str] = frozenset(),
) -> WrappedDocumentSection | None:
    """Numbered links from the overview figure to the sections it marks."""
    if first.overview is None:
        return None
    items = "".join(
        f'<li><a href="#{_esc(m.target)}"><span class="marker-n" aria-hidden="true">{m.n}</span>'
        f'<span>{_esc(m.label)}</span></a></li>'
        for m in first.overview.markers
    )
    markup = (
        '<section data-ve-section-kind="overview-nav">\n'
        f'<nav class="overview-markers" aria-label="この資料の論点"><ol>{items}</ol></nav>\n'
        "</section>"
    )
    return WrappedDocumentSection(
        instance_id=_allocate_instance_id(_OVERVIEW_NAV_INSTANCE_ID_PREFIX, occupied_ids),
        markup=markup,
    )


def render_closing(section: ClosingSection, *, marker: int | None = None) -> WrappedDocumentSection:
    parts: list[str] = []
    for i, block in enumerate(section.blocks):
        items = "".join(f"<li>{_esc(item)}</li>" for item in block.items)
        attr = _marker_attr(marker) if i == 0 else ""
        parts.append(f"  <h2{attr}>{_esc(block.heading)}</h2>\n  <ul>{items}</ul>")
    body = "\n".join(parts)
    markup = (
        f'<section data-ve-section-kind="closing" id="{_esc(section.id)}">\n'
        f'<section class="closing-section" aria-label="判断材料">\n'
        f"{body}\n"
        f"</section>\n</section>"
    )
    return WrappedDocumentSection(instance_id=section.id, markup=markup)


def render_ask(section: AskSection, *, marker: int | None = None) -> WrappedDocumentSection:
    """Render a question card; ``marker`` echoes an overview number on its lead line."""
    kind = section.ask_type
    kind_label = _ASK_KIND_LABEL[kind]
    attr = _marker_attr(marker)
    if kind == "decision":
        body = _render_decision_body(section, kind_label, attr)
    elif kind == "request":
        body = _render_request_body(section, kind_label, attr)
    else:
        body = _render_hypothesis_body(section, kind_label, attr)
    markup = (
        f'<section data-ve-section-kind="ask" data-ve-ask-type="{_esc(kind)}"'
        f' id="{_esc(section.id)}">\n'
        f'{body}\n'
        f"</section>"
    )
    return WrappedDocumentSection(instance_id=section.id, markup=markup)


def _render_decision_body(section: AskSection, kind_label: str, marker_attr: str = "") -> str:
    options_html: list[str] = []
    for opt in section.options:
        attrs = f'data-ask-option data-ask-option-id="{_esc(opt.id)}"'
        badge = ""
        if opt.id == section.default_id:
            attrs += " data-ask-default"
            badge = '<span class="ask-badge">推奨</span>'
        if opt.withdrawn:
            attrs += " data-ask-withdrawn"
            badge = '<span class="ask-withdrawn-note">取り下げ</span>'
        options_html.append(
            f"<li {attrs}>"
            f'<span class="ask-option-head"><span class="ask-option-label">{_esc(opt.label)}</span>{badge}</span>'
            f'<span class="ask-benefit"><span class="ask-prefix">利点:</span> {_esc(opt.benefit)}</span>'
            f'<span class="ask-tradeoff"><span class="ask-prefix">代償:</span> {_esc(opt.tradeoff)}</span>'
            "</li>"
        )
    memo = (
        '\n  <div class="ask-memo">'
        '<label>補足（任意）<textarea data-ask-memo></textarea></label></div>'
    )
    return (
        f'<div class="ask" data-ask="decision">\n'
        f'  <p class="ask-kind">{_esc(kind_label)}</p>\n'
        f'  <p class="ask-question"{marker_attr}>{_esc(section.question or "")}</p>\n'
        f'  <p class="ask-evidence"><span class="ask-prefix">根拠:</span> {_esc(section.evidence)}</p>\n'
        f'  <ul class="ask-options">\n'
        f'    {"".join(options_html)}\n'
        f"  </ul>{memo}\n"
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
) -> WrappedDocumentSection:
    """Build the collection panel inserted after closing (always exactly one).

    It lists decision asks when there are any, and always carries the
    annotation count and the global memo. Selection sync, drafts, and the
    copy control are the skeleton's fixed collection JS.
    """
    decisions = tuple(a for a in asks if a.ask_type == "decision")
    digest = compute_ask_digest(asks)
    instance_id = _allocate_instance_id(_PANEL_INSTANCE_ID_PREFIX, occupied_ids)
    asks_html = ""
    if decisions:
        items_html = "".join(_render_panel_ask_item(a) for a in decisions)
        asks_html = f'  <ul class="panel-asks">\n    {items_html}\n  </ul>\n'
    body = (
        '<section class="decision-panel" aria-label="回答と指摘の回収">\n'
        "  <h2>回答と指摘の回収</h2>\n"
        f"{asks_html}"
        '  <p class="panel-review-count" data-ve-panel-review-count>指摘 0 件</p>\n'
        '  <div class="ask-memo"><label>全体メモ'
        "<textarea data-ve-panel-global-memo></textarea></label></div>\n"
        '  <p class="panel-note">選択・指摘の保存とコピーは、ブラウザの'
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
    default_label = next(
        opt.label for opt in section.options if opt.id == section.default_id
    )
    status = f"お任せ（推奨: {default_label}）"
    return (
        f'<li data-ve-panel-ask="{_esc(section.id)}">'
        f'<span class="panel-question">{_esc(section.question or "")}</span>'
        f'<span class="panel-status" data-ve-panel-status>{_esc(status)}</span>'
        f'<span class="panel-memo" data-ve-panel-memo hidden></span>'
        f"</li>"
    )


def _render_request_body(section: AskSection, kind_label: str, marker_attr: str = "") -> str:
    steps_html = "".join(
        f'<li data-ask-role="{_esc(step.role)}" '
        f'data-ask-role-label="{_esc(step.role_label)}">{_esc(step.text)}</li>'
        for step in section.steps
    )
    return (
        f'<div class="ask" data-ask="request">\n'
        f'  <p class="ask-kind"{marker_attr}>{_esc(kind_label)}</p>\n'
        f'  <ol class="ask-steps">\n'
        f"    {steps_html}\n"
        f"  </ol>\n"
        f"</div>"
    )


def _render_hypothesis_body(section: AskSection, kind_label: str, marker_attr: str = "") -> str:
    assert section.claim is not None
    certainty = section.claim.certainty
    certainty_label = CERTAINTY_LABEL[certainty]
    # Keep the chip on the same line as the claim's last character.
    head, tail = section.claim.text[:-1], section.claim.text[-1:]
    return (
        f'<div class="ask" data-ask="hypothesis">\n'
        f'  <p class="ask-kind">{_esc(kind_label)}</p>\n'
        f'  <p class="ask-claim"{marker_attr}>{_esc(head)}'
        f'<span class="certainty-tail">{_esc(tail)} '
        f'<span class="certainty {certainty}">{_esc(certainty_label)}</span></span></p>\n'
        f'  <p class="ask-verify">{_esc(section.verify or "")}</p>\n'
        f"</div>"
    )
