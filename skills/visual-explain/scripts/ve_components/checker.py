"""Safety and skeleton layer of the four-layer component checker.

This module never executes scripts and never uses an HTML-repair parser that
could normalize unsafe input before validation. It enforces: exactly three
controlled marker pairs in order, byte-identical fixed regions outside the
controlled bodies, existing-rule content safety inside the content slot, and
trusted/allowlisted/hash-verified controlled assets. When ``expected`` is
provided (Task 7), manifest-to-DOM comparisons are added on top of these.
"""
from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

from .diagnostics import (
    FIXED_REGION_MISMATCH,
    FORBIDDEN_CONTENT_MARKUP,
    INVALID_CONTROLLED_ASSET,
    MISSING_CONTROLLED_MARKER,
    Diagnostic,
)

STYLES_BEGIN = "<!-- VE-CONTROLLED:COMPONENT-STYLES:BEGIN -->"
STYLES_END = "<!-- VE-CONTROLLED:COMPONENT-STYLES:END -->"
CONTENT_BEGIN = "<!-- VE-CONTROLLED:CONTENT:BEGIN -->"
CONTENT_END = "<!-- VE-CONTROLLED:CONTENT:END -->"
SCRIPTS_BEGIN = "<!-- VE-CONTROLLED:COMPONENT-SCRIPTS:BEGIN -->"
SCRIPTS_END = "<!-- VE-CONTROLLED:COMPONENT-SCRIPTS:END -->"

TITLE_BEGIN = "<!-- TITLE:BEGIN -->"
TITLE_END = "<!-- TITLE:END -->"

# (name, begin, end) in required document order.
CONTROLLED_SLOTS = (
    ("styles", STYLES_BEGIN, STYLES_END),
    ("content", CONTENT_BEGIN, CONTENT_END),
    ("scripts", SCRIPTS_BEGIN, SCRIPTS_END),
)

# Bodies normalized away before the fixed-region comparison.
_NORMALIZE_PAIRS = (
    (TITLE_BEGIN, TITLE_END),
    (STYLES_BEGIN, STYLES_END),
    (CONTENT_BEGIN, CONTENT_END),
    (SCRIPTS_BEGIN, SCRIPTS_END),
)

FORBIDDEN_CONTENT_TAGS = {"style", "script", "link", "base", "iframe", "object", "embed", "meta", "form"}


def is_component_document(text: str) -> bool:
    return ("VE-CONTROLLED:" in text or "data-ve-component" in text
            or "data-ve-section-kind" in text)


def extract_controlled_slots(text: str) -> tuple[dict[str, str], list[Diagnostic]]:
    """Return each controlled slot body, requiring one ordered pair per slot."""
    diagnostics: list[Diagnostic] = []
    slots: dict[str, str] = {}
    positions: list[int] = []
    for name, begin, end in CONTROLLED_SLOTS:
        if text.count(begin) != 1 or text.count(end) != 1:
            diagnostics.append(Diagnostic(MISSING_CONTROLLED_MARKER,
                                          f"{name} スロットの BEGIN/END マーカーは各1個必要です"))
            continue
        b = text.index(begin)
        e = text.index(end)
        if b + len(begin) > e:
            diagnostics.append(Diagnostic(MISSING_CONTROLLED_MARKER, f"{name} スロットのマーカー順序が不正です"))
            continue
        slots[name] = text[b + len(begin):e]
        positions.append(b)
    if len(positions) == len(CONTROLLED_SLOTS) and positions != sorted(positions):
        diagnostics.append(Diagnostic(MISSING_CONTROLLED_MARKER,
                                      "制御スロットは styles→content→scripts の順で並べてください"))
    return slots, diagnostics


def _blank_between(text: str, begin: str, end: str) -> str:
    if text.count(begin) != 1 or text.count(end) != 1:
        return text
    b = text.index(begin) + len(begin)
    e = text.index(end)
    if b > e:
        return text
    return text[:b] + text[e:]


def normalized_fixed_regions(candidate: str, skeleton: str) -> list[Diagnostic]:
    """Every byte outside the controlled/title bodies must match the skeleton."""
    cand = candidate
    skel = skeleton
    for begin, end in _NORMALIZE_PAIRS:
        cand = _blank_between(cand, begin, end)
        skel = _blank_between(skel, begin, end)
    if cand != skel:
        return [Diagnostic(FIXED_REGION_MISMATCH, "固定領域が skeleton.html と一致しません")]
    return []


class _ContentSafetyParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.diagnostics: list[Diagnostic] = []

    def _check(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in FORBIDDEN_CONTENT_TAGS:
            self.diagnostics.append(Diagnostic(FORBIDDEN_CONTENT_MARKUP, f"禁止タグ <{tag}> が content スロットにあります"))
        for name, value in attrs:
            name = name.lower()
            if name.startswith("on"):
                self.diagnostics.append(Diagnostic(FORBIDDEN_CONTENT_MARKUP, f"イベント属性 {name} は禁止です"))
            if name == "style":
                self.diagnostics.append(Diagnostic(FORBIDDEN_CONTENT_MARKUP, "インライン style 属性は禁止です"))
            local = name.rsplit(":", 1)[-1]
            if local in {"href", "src"} and value is not None:
                v = value.strip()
                scheme = v.split(":", 1)[0].lower() if ":" in v.split("/", 1)[0] else ""
                if v.startswith("//") or v.lower().startswith(("http://", "https://")):
                    self.diagnostics.append(Diagnostic(FORBIDDEN_CONTENT_MARKUP, f"外部参照は禁止です: {v}"))
                elif scheme not in {"", "file"} and not v.startswith("#"):
                    self.diagnostics.append(Diagnostic(FORBIDDEN_CONTENT_MARKUP, f"許可されない URL スキームです: {v}"))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._check(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._check(tag, attrs)

    def handle_comment(self, data: str) -> None:
        if "VE-CONTROLLED:" in data:
            self.diagnostics.append(Diagnostic(FORBIDDEN_CONTENT_MARKUP, "content スロット内に制御マーカーを入れ子にできません"))


def validate_content_markup(content_markup: str) -> list[Diagnostic]:
    """Reject style/script/link/base/iframe/object/embed, inline style, on* attrs,
    executable/external URLs, and nested controlled markers in content markup."""
    parser = _ContentSafetyParser()
    parser.feed(content_markup)
    parser.close()
    return parser.diagnostics


class _AssetTagCollector(HTMLParser):
    def __init__(self, target: str) -> None:
        super().__init__(convert_charrefs=False)
        self.target = target  # "style" | "script"
        self.blocks: list[tuple[dict[str, str], list[str]]] = []
        self._current: list[str] | None = None
        self._attrs: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == self.target:
            self._attrs = {k.lower(): (v or "") for k, v in attrs}
            self._current = []

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == self.target and self._current is not None:
            self.blocks.append((self._attrs, self._current))
            self._current = None
            self._attrs = {}


def validate_controlled_assets(slots: dict[str, str], registry, components_dir: Path | None) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    diagnostics += _validate_asset_slot(slots.get("styles", ""), "style", "styles", registry, components_dir)
    diagnostics += _validate_asset_slot(slots.get("scripts", ""), "script", "scripts", registry, components_dir)
    return diagnostics


def _validate_asset_slot(markup: str, tag: str, slot_type: str, registry, components_dir: Path | None) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    collector = _AssetTagCollector(tag)
    collector.feed(markup)
    collector.close()
    seen: set[str] = set()
    for attrs, body_parts in collector.blocks:
        body = "".join(body_parts)
        component_id = attrs.get("data-ve-component")
        version_raw = attrs.get("data-ve-contract-version")
        asset_id = attrs.get("data-ve-asset")
        digest = attrs.get("data-ve-digest")
        if not (component_id and version_raw and asset_id and digest):
            diagnostics.append(Diagnostic(INVALID_CONTROLLED_ASSET, f"{slot_type} 資産に provenance 属性が不足しています"))
            continue
        try:
            version = int(version_raw)
        except ValueError:
            diagnostics.append(Diagnostic(INVALID_CONTROLLED_ASSET, f"{slot_type} 資産の contract-version が不正です"))
            continue
        component = registry.find(component_id, version)
        if component is None:
            diagnostics.append(Diagnostic(INVALID_CONTROLLED_ASSET, f"未登録のコンポーネント資産です: {component_id}@{version}"))
            continue
        asset = component.asset_by_id(asset_id)
        if asset is None or asset.slot != slot_type:
            diagnostics.append(Diagnostic(INVALID_CONTROLLED_ASSET, f"資産 '{asset_id}' が {slot_type} スロットに登録されていません"))
            continue
        if asset_id in seen:
            diagnostics.append(Diagnostic(INVALID_CONTROLLED_ASSET, f"資産 '{asset_id}' が重複しています"))
            continue
        seen.add(asset_id)
        body_digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if digest != asset.digest or body_digest != asset.digest:
            diagnostics.append(Diagnostic(INVALID_CONTROLLED_ASSET, f"資産 '{asset_id}' のダイジェストが一致しません"))
            continue
        if "//" in body or re.search(r"url\(\s*['\"]?\s*(?:https?:)?//", body, re.IGNORECASE):
            diagnostics.append(Diagnostic(INVALID_CONTROLLED_ASSET, f"資産 '{asset_id}' に外部参照があります"))
        if components_dir is not None:
            file_path = components_dir / asset.path
            try:
                file_digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
            except OSError:
                diagnostics.append(Diagnostic(INVALID_CONTROLLED_ASSET, f"資産ファイルを読めません: {asset.path}"))
                continue
            if file_digest != asset.digest:
                diagnostics.append(Diagnostic(INVALID_CONTROLLED_ASSET, f"資産ファイル '{asset.path}' が改竄されています"))
    return diagnostics


def check_final_document(raw: bytes | str, skeleton: bytes | str, registry, expected=None,
                         components_dir: Path | None = None) -> list[Diagnostic]:
    """Run the safety/skeleton layer. Legacy documents pass unchanged."""
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    skel = skeleton.decode("utf-8") if isinstance(skeleton, bytes) else skeleton
    if not is_component_document(text):
        return []
    diagnostics: list[Diagnostic] = []
    slots, marker_diags = extract_controlled_slots(text)
    diagnostics += marker_diags
    diagnostics += normalized_fixed_regions(text, skel)
    if "content" in slots:
        diagnostics += validate_content_markup(slots["content"])
    diagnostics += validate_controlled_assets(slots, registry, components_dir)
    if expected is not None:
        from .final_checks import check_manifest_to_dom  # Task 7
        diagnostics += check_manifest_to_dom(text, slots, expected)
    return diagnostics
