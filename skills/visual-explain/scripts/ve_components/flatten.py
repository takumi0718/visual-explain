"""Flatten a CompositionResult into the skeleton's controlled slots.

Exact controlled-marker replacement only: one trusted <style> per deduplicated
asset with provenance, ordered section markup in the content slot, and zero
scripts unless a registry entry supplies an allowlisted script asset. Any change
outside the controlled bodies is rejected by comparing normalized fixed regions
before returning.
"""
from __future__ import annotations

import hashlib
import html
from pathlib import Path

from .checker import (
    CONTENT_BEGIN,
    CONTENT_END,
    SCRIPTS_BEGIN,
    SCRIPTS_END,
    STYLES_BEGIN,
    STYLES_END,
    TITLE_BEGIN,
    TITLE_END,
    normalized_fixed_regions,
)
from .diagnostics import FIXED_REGION_MISMATCH, INVALID_CONTROLLED_ASSET, ContractError, Diagnostic


def _replace_slot(text: str, begin: str, end: str, body: str) -> str:
    b = text.index(begin) + len(begin)
    e = text.index(end)
    return text[:b] + body + text[e:]


def _style_block(ref, components_dir: Path) -> str:
    css = (components_dir / ref.asset.path).read_text("utf-8")
    digest = hashlib.sha256(css.encode("utf-8")).hexdigest()
    if digest != ref.asset.digest:
        raise ContractError([Diagnostic(INVALID_CONTROLLED_ASSET, f"資産 '{ref.asset.id}' のファイルダイジェストが不一致です")])
    return (
        f'\n  <style data-ve-component="{html.escape(ref.component_id, quote=True)}"'
        f' data-ve-contract-version="{ref.version}"'
        f' data-ve-asset="{html.escape(ref.asset.id, quote=True)}"'
        f' data-ve-digest="{digest}">{css}</style>'
    )


def _script_block(ref, components_dir: Path) -> str:
    body = (components_dir / ref.asset.path).read_text("utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if digest != ref.asset.digest:
        raise ContractError([Diagnostic(INVALID_CONTROLLED_ASSET, f"資産 '{ref.asset.id}' のファイルダイジェストが不一致です")])
    return (
        f'\n  <script data-ve-component="{html.escape(ref.component_id, quote=True)}"'
        f' data-ve-contract-version="{ref.version}"'
        f' data-ve-asset="{html.escape(ref.asset.id, quote=True)}"'
        f' data-ve-digest="{digest}">{body}</script>'
    )


def flatten_document(composition, skeleton: str, components_dir: Path, title: str) -> str:
    styles_body = "".join(_style_block(ref, components_dir) for ref in composition.style_assets)
    if styles_body:
        styles_body += "\n  "
    scripts_body = "".join(_script_block(ref, components_dir) for ref in composition.script_assets)
    if scripts_body:
        scripts_body += "\n  "
    content_body = "\n    " + "\n    ".join(composition.sections_markup) + "\n    " if composition.sections_markup else "\n    "
    title_body = f"\n  <title>{html.escape(title)}</title>\n  "

    document = skeleton
    document = _replace_slot(document, TITLE_BEGIN, TITLE_END, title_body)
    document = _replace_slot(document, STYLES_BEGIN, STYLES_END, styles_body)
    document = _replace_slot(document, CONTENT_BEGIN, CONTENT_END, content_body)
    document = _replace_slot(document, SCRIPTS_BEGIN, SCRIPTS_END, scripts_body)

    # Nothing outside the controlled/title bodies may have changed.
    drift = normalized_fixed_regions(document, skeleton)
    if drift:
        raise ContractError([Diagnostic(FIXED_REGION_MISMATCH, "flatten が固定領域を変更しました")])
    return document
