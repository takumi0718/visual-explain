"""Typed document sections: first-screen, closing, ask, and the build-time TOC.

These are trusted renderers that bypass the component registry: their inputs are
validated dataclasses, their markup uses only fixed skeleton classes, and the
final checker (group 3) re-verifies the result in the flattened document.
"""
from __future__ import annotations

import html
from dataclasses import dataclass

from .model import ClosingSection, DocumentMetadata, FirstScreenSection

_SUBTITLE_LABEL = {"proposal": "あなたが決めること", "system": "この資料が答える問い",
                   "research": "この資料が答える問い"}


@dataclass(frozen=True)
class WrappedDocumentSection:
    instance_id: str
    markup: str


def _esc(value: str) -> str:
    return html.escape(value)


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
