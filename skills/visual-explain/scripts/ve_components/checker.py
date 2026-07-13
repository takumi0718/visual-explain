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
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from .diagnostics import (
    ARTIFACT_SEMANTIC_MISMATCH,
    ASK_CONTRACT_VIOLATION,
    EVIDENCE_MAP_STRUCTURE_VIOLATION,
    FIXED_REGION_MISMATCH,
    FORBIDDEN_CONTENT_MARKUP,
    INVALID_CONTROLLED_ASSET,
    MISSING_CONTROLLED_MARKER,
    MISSING_PROVENANCE,
    NOTATION_CERTAINTY_VOCABULARY,
    NOTATION_EMPHASIS_LIMIT,
    NOTATION_HIGHLIGHT_LIMIT,
    RENDERER_SVG_VIOLATION,
    SLOPE_STRUCTURE_VIOLATION,
    Diagnostic,
)
from .validation import VOCABULARY

_COMPAT_SOURCES = set(VOCABULARY["compatibility"]["sources"])
_COMPAT_REASONS = set(VOCABULARY["compatibility"]["reasons"])
_COMPONENTS = set(VOCABULARY["components"])
_SECTION_TAG_RE = re.compile(r"<section\b([^>]*)>")
_ATTR_RE = lambda name: re.compile(name + r'="([^"]*)"')

RENDERER_SVG_ALLOWLIST = frozenset({"slope@1"})

_SVG_ALLOWED_TAGS = frozenset({"svg", "g", "line", "circle", "text", "title", "desc"})
_SVG_ATTR_ALLOWLIST = {
    "svg": frozenset({"id", "class", "viewBox", "preserveAspectRatio", "role", "aria-label", "aria-describedby"}),
    "g": frozenset({"class", "data-ve-semantic-id", "data-ve-takeaway"}),
    "line": frozenset({"class", "x1", "y1", "x2", "y2"}),
    "circle": frozenset({"class", "cx", "cy", "r", "data-ve-semantic-id", "data-ve-takeaway"}),
    "text": frozenset({"class", "x", "y", "text-anchor"}),
    "title": frozenset(),
    "desc": frozenset(),
}
_SVG_INT_COORD_RE = re.compile(r"^-?[0-9]+$")
_SVG_R_RE = re.compile(r"^[0-9]+$")
_SVG_VIEWBOX_EXACT = "0 0 600 220"
_SVG_PRESERVE_EXACT = "xMidYMid meet"
_SVG_TEXT_ANCHOR = frozenset({"start", "middle", "end"})
_SVG_OPEN_RE = re.compile(r"<svg\b([^>]*)>", re.IGNORECASE)
_WRAPPER_SECTION_RE = re.compile(
    r'<section\b([^>]*)data-ve-section-kind="([^"]+)"([^>]*)>(.*?)</section>',
    re.DOTALL,
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
    diagnostics = list(parser.diagnostics)
    diagnostics.extend(validate_ask_blocks(content_markup))
    return diagnostics


_ASK_KINDS = frozenset({"decision", "request", "hypothesis"})
_ASK_ROLES = frozenset({"user", "agent", "third-party"})
_CERTAINTY_CLASSES = frozenset({"confirmed", "inferred", "unverified"})


class _AskParser(HTMLParser):
    """Collect structural and content-quality facts for each data-ask subtree.

    Nesting is depth-scoped (mirrors ``_DomSemanticParser``): a stack of open
    ``data-ask`` blocks plus a stack of open "text scopes" (question, option
    tradeoff, no-default-reason, request step, claim, verify). ``handle_data``
    appends to every text scope currently open for a block, so nested markup
    (e.g. a certainty badge inside a claim) still counts toward the claim's
    own text without a separate accumulator.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict] = []
        self._stack: list[tuple[dict, int]] = []
        self._scopes: list[tuple[int, dict, str, int | None]] = []
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._depth += 1
        attr = dict(attrs)
        classes = frozenset((attr.get("class") or "").split())
        if "data-ask" in attr:
            block = {
                "kind": attr.get("data-ask") or "",
                "question_texts": [],
                "options": 0,
                "option_records": [],
                "defaults": 0,
                "no_default_reason_texts": [],
                "roles": [],
                "role_labels": 0,
                "role_texts": [],
                "claims": 0,
                "claim_texts": [],
                "claim_certainty": 0,
                "claim_certainty_valid": 0,
                "verify_texts": [],
                "_claim_depth": None,
            }
            self.blocks.append(block)
            self._stack.append((block, self._depth))
        for block, _block_depth in self._stack:
            if "ask-question" in classes:
                block["question_texts"].append("")
                self._scopes.append((self._depth, block, "question_texts", len(block["question_texts"]) - 1))
            if "data-ask-option" in attr:
                block["options"] += 1
                block["option_records"].append({"tradeoffs": 0, "text": ""})
            if "ask-tradeoff" in classes and block["option_records"]:
                block["option_records"][-1]["tradeoffs"] += 1
                self._scopes.append((self._depth, block, "option_tradeoff_text", None))
            if "data-ask-default" in attr:
                block["defaults"] += 1
            if "ask-no-default-reason" in classes:
                block["no_default_reason_texts"].append("")
                self._scopes.append((self._depth, block, "no_default_reason_texts", len(block["no_default_reason_texts"]) - 1))
            if "data-ask-role" in attr:
                block["roles"].append(attr.get("data-ask-role") or "")
                if attr.get("data-ask-role-label"):
                    block["role_labels"] += 1
                block["role_texts"].append("")
                self._scopes.append((self._depth, block, "role_texts", len(block["role_texts"]) - 1))
            if "ask-claim" in classes:
                block["claims"] += 1
                block["claim_texts"].append("")
                self._scopes.append((self._depth, block, "claim_texts", len(block["claim_texts"]) - 1))
                block["_claim_depth"] = self._depth
            if "certainty" in classes and block["_claim_depth"] is not None and self._depth > block["_claim_depth"]:
                block["claim_certainty"] += 1
                if len(classes & _CERTAINTY_CLASSES) == 1:
                    block["claim_certainty_valid"] += 1
            if "ask-verify" in classes:
                block["verify_texts"].append("")
                self._scopes.append((self._depth, block, "verify_texts", len(block["verify_texts"]) - 1))

    def handle_data(self, data: str) -> None:
        for _depth, block, field, idx in self._scopes:
            if field == "option_tradeoff_text":
                block["option_records"][-1]["text"] += data
            else:
                block[field][idx] += data

    def handle_endtag(self, tag: str) -> None:
        while self._scopes and self._scopes[-1][0] == self._depth:
            self._scopes.pop()
        if self._stack and self._stack[-1][1] == self._depth:
            block, _ = self._stack[-1]
            if block["_claim_depth"] == self._depth:
                block["_claim_depth"] = None
            self._stack.pop()
        self._depth -= 1


def validate_ask_blocks(content_markup: str) -> list[Diagnostic]:
    """Validate every ``data-ask`` subtree's DOM structure and content quality."""
    parser = _AskParser()
    parser.feed(content_markup)
    parser.close()
    diags: list[Diagnostic] = []
    for block in parser.blocks:
        kind = block["kind"]
        if kind not in _ASK_KINDS:
            diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, f"未知の ask 種別 '{kind}'"))
            continue
        if kind == "decision":
            if len(block["question_texts"]) != 1 or not block["question_texts"][0].strip():
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "decision には非空の ask-question がちょうど1つ必要です"))
            if block["options"] < 2:
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "decision には選択肢が2件以上必要です"))
            if any(rec["tradeoffs"] != 1 or not rec["text"].strip() for rec in block["option_records"]):
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "各選択肢には非空テキストの ask-tradeoff がちょうど1つ必要です"))
            if block["defaults"] > 1:
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "decision の既定案は最大1件です"))
            if block["defaults"] == 0 and (
                len(block["no_default_reason_texts"]) != 1 or not block["no_default_reason_texts"][0].strip()
            ):
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "既定案なしの decision には非空の ask-no-default-reason が必要です"))
        elif kind == "request":
            if not block["roles"]:
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "request には data-ask-role 付きの手順が1件以上必要です"))
            if any(role not in _ASK_ROLES for role in block["roles"]):
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "data-ask-role は user/agent/third-party のみ有効です"))
            if block["role_labels"] != len(block["roles"]):
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "各手順に data-ask-role-label（表示ラベル）が必要です"))
            if any(not text.strip() for text in block["role_texts"]):
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "request の各手順には非空の動作テキストが必要です"))
        else:  # hypothesis
            if len(block["claim_texts"]) != 1 or not block["claim_texts"][0].strip():
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "hypothesis には非空の ask-claim がちょうど1つ必要です"))
            if block["claim_certainty"] != 1 or block["claim_certainty_valid"] != 1:
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "hypothesis の ask-claim には確度クラスがちょうど1つ必要です"))
            if len(block["verify_texts"]) != 1 or not block["verify_texts"][0].strip():
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "hypothesis には非空の ask-verify がちょうど1つ必要です"))
    return diags


class _StrictSlotParser(HTMLParser):
    """Consume a controlled slot completely.

    The only permitted content is a sequence of the target asset tag; any other
    tag, stray non-whitespace text, or comment is recorded as foreign content so
    the slot cannot smuggle raw JavaScript/CSS or arbitrary HTML past the gate.
    """

    def __init__(self, target: str) -> None:
        super().__init__(convert_charrefs=False)
        self.target = target  # "style" | "script"
        self.blocks: list[tuple[dict[str, str], str]] = []
        self.foreign: list[str] = []
        self._inside = False
        self._attrs: dict[str, str] = {}
        self._body: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == self.target and not self._inside:
            self._inside = True
            self._attrs = {k.lower(): (v or "") for k, v in attrs}
            self._body = []
        else:
            self.foreign.append(f"想定外のタグ <{tag}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.foreign.append(f"想定外のタグ <{tag}/>")

    def handle_data(self, data: str) -> None:
        if self._inside:
            self._body.append(data)
        elif data.strip():
            self.foreign.append("スロット直下に想定外のテキスト")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == self.target and self._inside:
            self.blocks.append((self._attrs, "".join(self._body)))
            self._inside = False
            self._attrs = {}
            self._body = []
        else:
            # A stray or mismatched end tag (e.g. </style> inside <script>, or a
            # close with no open) is fail-closed foreign content.
            self.foreign.append(f"想定外の終了タグ </{tag}>")

    def handle_comment(self, data: str) -> None:
        if not self._inside:
            self.foreign.append("スロット直下に想定外のコメント")

    def close(self) -> None:
        super().close()
        if self._inside:
            # An unclosed <style>/<script> must never leave the slot in a
            # successful empty state — reject at EOF.
            self.foreign.append("未閉じのアセットタグがあります")
            self._inside = False


def validate_controlled_assets(slots: dict[str, str], registry, components_dir: Path | None) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    diagnostics += _validate_asset_slot(slots.get("styles", ""), "style", "styles", registry, components_dir)
    diagnostics += _validate_asset_slot(slots.get("scripts", ""), "script", "scripts", registry, components_dir)
    return diagnostics


def _validate_asset_slot(markup: str, tag: str, slot_type: str, registry, components_dir: Path | None) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    collector = _StrictSlotParser(tag)
    collector.feed(markup)
    collector.close()
    # The slot must be whitespace plus allowlisted asset blocks and nothing else.
    if collector.foreign:
        diagnostics.append(Diagnostic(INVALID_CONTROLLED_ASSET,
                                      f"{slot_type} スロットに許可されない内容があります"))
    seen: set[str] = set()
    for attrs, body in collector.blocks:
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


def validate_final_provenance(content: str) -> list[Diagnostic]:
    """Every section wrapper in the content slot must carry valid provenance."""
    diagnostics: list[Diagnostic] = []
    for match in _SECTION_TAG_RE.finditer(content):
        attrs = match.group(1)
        kind_match = _ATTR_RE("data-ve-section-kind").search(attrs)
        if kind_match is None:
            continue
        kind = kind_match.group(1)
        if kind == "canonical":
            if not _ATTR_RE("data-ve-component").search(attrs) or not _ATTR_RE("data-ve-instance").search(attrs):
                diagnostics.append(Diagnostic(MISSING_PROVENANCE, "canonical セクションに component/instance provenance がありません"))
        elif kind == "compatibility":
            src = _ATTR_RE("data-ve-compat-source").search(attrs)
            reason = _ATTR_RE("data-ve-compat-reason").search(attrs)
            if src is None or src.group(1) not in _COMPAT_SOURCES or reason is None or reason.group(1) not in _COMPAT_REASONS:
                diagnostics.append(Diagnostic(MISSING_PROVENANCE, "compatibility セクションに正しい provenance がありません"))
        else:
            diagnostics.append(Diagnostic(MISSING_PROVENANCE, f"未知の section-kind '{kind}'"))
    return diagnostics


# The single ``<ol>`` (the spine+rails grid) under which the trusted flow
# renderer emits every station. A real node lives two levels down: a
# ``span.ve-flow-node`` inside a ``li.ve-flow-station`` inside this canvas.
_NODE_LIST_CLASSES = frozenset({"ve-flow-canvas"})
# The class on the ``<li>`` that directly wraps a node span.
_STATION_CLASS = "ve-flow-station"
# The class the trusted flow renderer stamps on every node element and nothing
# else. Recognized nodes are bound to this exact shape.
_NODE_CLASS = "ve-flow-node"
# HTML void elements never nest children, so they must not stay on the open
# element stack and pollute ancestor lookups.
_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})


def _class_tokens(attrs: list[tuple[str, str | None]]) -> frozenset[str]:
    for name, value in attrs:
        if name.lower() == "class" and value:
            return frozenset(value.split())
    return frozenset()


class _DomSemanticParser(HTMLParser):
    """Collect node IDs, edges, semantic IDs, and cell associations from a fragment.

    Node identity is bound to the renderer's exact node-element shape: a real
    node is a ``class="ve-flow-node"`` element that is a DIRECT child of a
    ``li.ve-flow-station`` which is itself a DIRECT child of the flow canvas
    (``ol.ve-flow-canvas``), and whose non-empty ``data-ve-node-id`` equals its
    own ``data-ve-semantic-id``. Arbitrary elements, node-shaped elements outside
    a station, and attribute-only elements injected into the canvas all fail this
    shape and so can never anchor an edge endpoint.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.semantic_ids: set[str] = set()
        self.node_ids: set[str] = set()
        self.edges: list[tuple[str, str, str]] = []
        self.incomplete_edge = False
        self.row_refs: list[str] = []
        self.col_refs: list[str] = []
        self.cell_incomplete = False
        self._stack: list[tuple[str, frozenset[str]]] = []

    def _is_station_in_canvas(self) -> bool:
        # Parent must be li.ve-flow-station whose own parent is ol.ve-flow-canvas.
        if len(self._stack) < 2:
            return False
        ptag, pclasses = self._stack[-1]
        gtag, gclasses = self._stack[-2]
        return (ptag == "li" and _STATION_CLASS in pclasses
                and gtag == "ol" and bool(gclasses & _NODE_LIST_CLASSES))

    def _check(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = {k.lower(): (v or "") for k, v in attrs}
        if "data-ve-semantic-id" in d:
            self.semantic_ids.add(d["data-ve-semantic-id"])
        node_id = d.get("data-ve-node-id")
        if (node_id and d.get("data-ve-semantic-id") == node_id
                and _NODE_CLASS in _class_tokens(attrs)
                and self._is_station_in_canvas()):
            self.node_ids.add(node_id)
        has = {k: (k in d) for k in ("data-ve-from", "data-ve-to", "data-ve-relation")}
        if all(has.values()):
            self.edges.append((d["data-ve-from"], d["data-ve-to"], d["data-ve-relation"]))
        elif any(has.values()):
            self.incomplete_edge = True
        has_row = "data-ve-row-id" in d
        has_col = "data-ve-column-id" in d
        if has_row != has_col:
            self.cell_incomplete = True
        if has_row:
            self.row_refs.append(d.get("data-ve-row-id", ""))
        if has_col:
            self.col_refs.append(d.get("data-ve-column-id", ""))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self._check(tag, attrs)
        if tag not in _VOID_TAGS:
            self._stack.append((tag, _class_tokens(attrs)))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._check(tag.lower(), attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                del self._stack[i:]
                return


def _parse_dom(fragment: str) -> _DomSemanticParser:
    parser = _DomSemanticParser()
    parser.feed(fragment)
    parser.close()
    return parser


@dataclass
class _ItemLayoutRecord:
    has_semantic_id: bool = False
    concept_count: int = 0
    concept_not_direct: bool = False
    description_count: int = 0
    description_nested_in_concept: bool = False


class _ItemLayoutParser(HTMLParser):
    """Collect direct concept/description ownership for one component item type."""

    def __init__(self, outer_class: str, concept_class: str, description_class: str) -> None:
        super().__init__(convert_charrefs=True)
        self.outer_class = outer_class
        self.concept_class = concept_class
        self.description_class = description_class
        self.records: list[_ItemLayoutRecord] = []
        self._stack: list[tuple[str, frozenset[str]]] = []
        self._active: list[tuple[int, _ItemLayoutRecord]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        classes = _class_tokens(attrs)
        values = {key.lower(): (value or "") for key, value in attrs}
        if tag == "li" and self.outer_class in classes:
            record = _ItemLayoutRecord(
                has_semantic_id=bool(values.get("data-ve-semantic-id")),
            )
            self.records.append(record)
            self._active.append((len(self._stack), record))
        elif self._active:
            outer_depth, record = self._active[-1]
            direct_child = len(self._stack) == outer_depth + 1
            if self.concept_class in classes:
                record.concept_count += 1
                record.concept_not_direct = record.concept_not_direct or not direct_child
            if self.description_class in classes:
                record.description_count += 1
                inside_concept = any(
                    self.concept_class in ancestor_classes
                    for _ancestor_tag, ancestor_classes in self._stack[outer_depth + 1:]
                )
                record.description_nested_in_concept = inside_concept or not direct_child
        if tag not in _VOID_TAGS:
            self._stack.append((tag, classes))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                break
        while self._active and len(self._stack) <= self._active[-1][0]:
            self._active.pop()


def _check_item_layout(
    body: str,
    *,
    component: str,
    outer: str,
    concept: str,
    description: str,
    max_description_blocks: int = 1,
) -> list[Diagnostic]:
    parser = _ItemLayoutParser(outer, concept, description)
    parser.feed(body)
    parser.close()
    diagnostics: list[Diagnostic] = []
    description_counts = [record.description_count for record in parser.records]
    for index, record in enumerate(parser.records, start=1):
        if not record.has_semantic_id:
            diagnostics.append(Diagnostic(
                ARTIFACT_SEMANTIC_MISMATCH,
                f"{component} 項目 {index} の外側に意味 ID がありません",
            ))
        if record.concept_count != 1 or record.concept_not_direct:
            diagnostics.append(Diagnostic(
                ARTIFACT_SEMANTIC_MISMATCH,
                f"{component} 項目 {index} の concept は直接の子として1個必要です",
            ))
        if record.description_count > max_description_blocks or record.description_nested_in_concept:
            diagnostics.append(Diagnostic(
                ARTIFACT_SEMANTIC_MISMATCH,
                f"{component} 項目 {index} の description は concept の兄弟である必要があります",
            ))
    if any(description_counts) and not all(count > 0 for count in description_counts):
        diagnostics.append(Diagnostic(
            ARTIFACT_SEMANTIC_MISMATCH,
            f"{component} の description は全有または全無である必要があります",
        ))
    return diagnostics


def extract_flow_dom(markup: str) -> tuple[set[str], set[tuple[str, str, str]], bool]:
    """Return (node ids, edge (from,to,relation) triples, any-incomplete-edge)."""
    parser = _parse_dom(markup)
    return parser.node_ids, set(parser.edges), parser.incomplete_edge


_COMPONENT_RE = re.compile(r'data-ve-component="([^"]+)"')
_CHEVRON_STEPS_OL_RE = re.compile(
    r'<ol[^>]*class="([^"]*\bve-chevron-steps\b[^"]*)"[^>]*>',
    re.IGNORECASE,
)


def _chevron_steps_orientation(body: str) -> str | None:
    """Return 'horizontal' or 'vertical' from chevron <ol> class tokens only."""
    match = _CHEVRON_STEPS_OL_RE.search(body)
    if match is None:
        return None
    classes = match.group(1).split()
    if "ve-chevron-horizontal" in classes:
        return "horizontal"
    if "ve-chevron-centered" in classes:
        return "vertical"
    return "vertical"


def _class_tokens_from_attr_string(attrs: str) -> frozenset[str]:
    match = re.search(r'\bclass="([^"]*)"', attrs)
    if not match:
        return frozenset()
    return frozenset(match.group(1).split())


def _visible_text(fragment: str) -> str:
    text = re.sub(r"<!--.*?-->", "", fragment, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _exact_index_token(prefix: str, classes: frozenset[str]) -> frozenset[str]:
    return {c for c in classes if c.startswith(f"{prefix}-index-")}


def _exact_count_token(prefix: str, classes: frozenset[str]) -> frozenset[str]:
    return {c for c in classes if c.startswith(f"{prefix}-count-")}


def _check_count_index_container(
    body: str,
    *,
    container_pattern: str,
    item_count: int,
    prefix: str,
    label: str,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    container_match = re.search(container_pattern, body)
    if container_match is None:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      f"{label} のコンテナが見つかりません"))
        return diagnostics
    container_classes = _class_tokens_from_attr_string(container_match.group(1))
    expected_count = f"{prefix}-count-{item_count}"
    count_tokens = _exact_count_token(prefix, container_classes)
    if count_tokens != {expected_count}:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      f"{label} のコンテナは {expected_count} である必要があります"))
    return diagnostics


def _check_enumeration_artifact(body: str, parser: _DomSemanticParser) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    block_attrs = re.findall(r'<li\s+([^>]*\bve-enum-block\b[^>]*)>', body)
    if len(block_attrs) < 2 or len(block_attrs) > 6:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      f"enumeration は2〜6項目である必要があります (found {len(block_attrs)})"))
    if len(block_attrs) != sum('data-ve-semantic-id="' in attrs for attrs in block_attrs):
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "enumeration ブロックに data-ve-semantic-id がありません"))
    for attrs in block_attrs:
        match = re.search(r'data-ve-semantic-id="([^"]+)"', attrs)
        if match is None:
            continue
        bid = match.group(1)
        if bid not in parser.semantic_ids:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          f"enumeration 項目 '{bid}' に意味 ID がありません"))
    diagnostics.extend(_check_item_layout(
        body,
        component="enumeration",
        outer="ve-enum-block",
        concept="ve-enum-concept",
        description="ve-enum-description",
        max_description_blocks=3,
    ))
    return diagnostics


def _check_chevron_artifact(body: str, parser: _DomSemanticParser) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    step_attrs = re.findall(r'<li\s+([^>]*\bve-chevron-step\b[^>]*)>', body)
    if len(step_attrs) < 2 or len(step_attrs) > 6:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      f"chevron は2〜6段である必要があります (found {len(step_attrs)})"))
    if len(step_attrs) != sum('data-ve-semantic-id="' in attrs for attrs in step_attrs):
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "chevron ステップに data-ve-semantic-id がありません"))
    for attrs in step_attrs:
        match = re.search(r'data-ve-semantic-id="([^"]+)"', attrs)
        if match is None:
            continue
        sid = match.group(1)
        if sid not in parser.semantic_ids:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          f"chevron ステップ '{sid}' に意味 ID がありません"))
    loop_rails = re.findall(r'class="[^"]*\bve-chevron-loop-rail\b[^"]*"', body)
    orientation = _chevron_steps_orientation(body)
    is_horizontal = orientation == "horizontal"
    if is_horizontal and loop_rails:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "horizontal chevron に loop レールは許可されていません"))
    if not is_horizontal and len(loop_rails) > 1:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "vertical chevron の loop レールは最大1本です"))
    diagnostics.extend(_check_item_layout(
        body,
        component="chevron",
        outer="ve-chevron-step",
        concept="ve-chevron-concept",
        description="ve-chevron-description",
    ))
    return diagnostics


def _check_pyramid_artifact(body: str, parser: _DomSemanticParser) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    tier_blocks = re.findall(
        r'<li\s+([^>]*\bve-pyramid-tier\b[^>]*)>(.*?)</li>',
        body,
        re.DOTALL,
    )
    tier_count = len(tier_blocks)
    if tier_count < 3 or tier_count > 4:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      f"pyramid は3〜4層である必要があります (found {tier_count})"))
    diagnostics.extend(_check_count_index_container(
        body,
        container_pattern=r'<ul\s+([^>]*\bve-pyramid-tiers\b[^>]*)>',
        item_count=tier_count,
        prefix="ve-pyramid",
        label="pyramid",
    ))
    if tier_count != sum('data-ve-semantic-id="' in attrs for attrs, _ in tier_blocks):
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "pyramid 層に data-ve-semantic-id がありません"))
    for index, (attrs, _inner) in enumerate(tier_blocks):
        classes = _class_tokens_from_attr_string(attrs)
        position = index + 1
        expected_index = f"ve-pyramid-index-{position}"
        index_tokens = _exact_index_token("ve-pyramid", classes)
        if index_tokens != {expected_index}:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          f"pyramid の層 {position} は {expected_index} を1つだけ持つ必要があります"))
        match = re.search(r'data-ve-semantic-id="([^"]+)"', attrs)
        if match is None:
            continue
        tid = match.group(1)
        if tid not in parser.semantic_ids:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          f"pyramid 層 '{tid}' に意味 ID がありません"))
        face_tokens = {c for c in classes if c.startswith("ve-pyramid-face-")}
        if index == 0:
            if face_tokens != {"ve-pyramid-face-strong"}:
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                              "pyramid の先頭層は ve-pyramid-face-strong のみである必要があります"))
        else:
            if face_tokens != {"ve-pyramid-face-dim"}:
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                              "pyramid の下位層は ve-pyramid-face-dim のみである必要があります"))
    return diagnostics


def _check_stairs_artifact(body: str, parser: _DomSemanticParser) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    stage_blocks = re.findall(
        r'<li\s+([^>]*\bve-stairs-stage\b[^>]*)>(.*?)</li>',
        body,
        re.DOTALL,
    )
    stage_count = len(stage_blocks)
    if stage_count < 3 or stage_count > 5:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      f"stairs は3〜5段である必要があります (found {stage_count})"))
    diagnostics.extend(_check_count_index_container(
        body,
        container_pattern=r'<ol\s+([^>]*\bve-stairs-stages\b[^>]*)>',
        item_count=stage_count,
        prefix="ve-stairs",
        label="stairs",
    ))
    if stage_count != sum('data-ve-semantic-id="' in attrs for attrs, _ in stage_blocks):
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "stairs 段に data-ve-semantic-id がありません"))
    accent_count = 0
    for index, (attrs, inner) in enumerate(stage_blocks):
        classes = _class_tokens_from_attr_string(attrs)
        position = index + 1
        expected_index = f"ve-stairs-index-{position}"
        index_tokens = _exact_index_token("ve-stairs", classes)
        if index_tokens != {expected_index}:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          f"stairs の段 {position} は {expected_index} を1つだけ持つ必要があります"))
        match = re.search(r'data-ve-semantic-id="([^"]+)"', attrs)
        if match is None:
            continue
        sid = match.group(1)
        if sid not in parser.semantic_ids:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          f"stairs 段 '{sid}' に意味 ID がありません"))
        tread_tokens = {c for c in classes if c.startswith("ve-stairs-tread-")}
        if tread_tokens and tread_tokens != {"ve-stairs-tread-accent"}:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          "stairs の tread クラスは ve-stairs-tread-accent のみ許可されます"))
        if "ve-stairs-tread-accent" in classes:
            accent_count += 1
            note_spans = re.findall(
                r'<span\s+class="([^"]*)"[^>]*>(.*?)</span>',
                inner,
                re.DOTALL,
            )
            note_texts = [
                _visible_text(content)
                for cls, content in note_spans
                if "ve-stairs-note" in frozenset(cls.split())
            ]
            if not note_texts:
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                              "current 段のブロック内に ve-stairs-note がありません"))
            elif not any(text for text in note_texts):
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                              "current 段の ve-stairs-note に可視テキストがありません"))
    if accent_count > 1:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "stairs の accent 段は最大1つです"))
    return diagnostics


def _check_waterfall_artifact(body: str, parser: _DomSemanticParser) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    bar_blocks = re.findall(
        r'<div\s+([^>]*\bve-waterfall-bar\b[^>]*)>(.*?)</div>',
        body,
        re.DOTALL,
    )
    if not bar_blocks:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, "waterfall に棒がありません"))
        return diagnostics

    for attrs, inner in bar_blocks:
        bar_sid = _semantic_id_from_attrs(attrs)
        if bar_sid is None:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          "waterfall 棒に data-ve-semantic-id がありません"))
        classes = _class_tokens_from_attr_string(attrs)
        starts = [c for c in classes if c.startswith("ve-wf-start-")]
        lens = [c for c in classes if c.startswith("ve-wf-len-")]
        if len(starts) != 1 or len(lens) != 1:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          "waterfall 棒は ve-wf-start/len を1つずつ持つ必要があります"))
            continue
        for token in starts + lens:
            suffix = token.rsplit("-", 1)[-1]
            if not suffix.isdigit() or not (0 <= int(suffix) <= 100):
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                              f"waterfall 百分率クラス '{token}' が範囲外です"))
        value_spans = re.findall(
            r'<span\s+[^>]*\bve-waterfall-value\b[^>]*>([^<]*)</span>',
            inner,
        )
        if len(value_spans) != 1:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          "waterfall 棒は ve-waterfall-value を1つだけ持つ必要があります"))
        elif not value_spans[0].strip():
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          "waterfall 棒の ve-waterfall-value に可視テキストがありません"))

    connector_blocks = re.findall(
        r'<div\s+[^>]*\bve-waterfall-connector-track\b[^>]*>\s*'
        r'(<span\s+[^>]*\bve-waterfall-connector\b[^>]*>\s*</span>)',
        body,
        re.DOTALL,
    )
    for connector_html in connector_blocks:
        starts = re.findall(r'\bve-wf-start-(\d+)\b', connector_html)
        lens = re.findall(r'\bve-wf-len-(\d+)\b', connector_html)
        if len(starts) != 1 or len(lens) != 1:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          "waterfall コネクタは ve-wf-start/len を1つずつ持つ必要があります"))

    if "ve-waterfall-notes" not in body:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "waterfall に ve-waterfall-notes がありません"))

    has_bars = "ve-wf-bars" in body
    has_columns = "ve-wf-columns" in body
    if has_bars == has_columns:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "waterfall は ve-wf-bars か ve-wf-columns のどちらか一方である必要があります"))
    if has_columns and "ve-waterfall-scroll" not in body:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "columns waterfall に横スクロールコンテナがありません"))

    row_attrs = re.findall(
        r'<div\s+([^>]*\bve-waterfall-row\b[^>]*)>',
        body,
    )
    for attrs in row_attrs:
        if _semantic_id_from_attrs(attrs) is not None:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          "waterfall row に data-ve-semantic-id は許可されていません"))

    bar_ids = [_semantic_id_from_attrs(attrs) for attrs, _ in bar_blocks]
    bar_ids = [sid for sid in bar_ids if sid is not None]
    if len(bar_ids) != len(set(bar_ids)):
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "waterfall の意味 ID が重複しています"))
    for sid in bar_ids:
        if body.count(f'data-ve-semantic-id="{sid}"') != 1:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          f"waterfall の意味 ID '{sid}' は DOM に1回だけ現れる必要があります"))

    for sid in parser.semantic_ids:
        if sid not in body:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          f"waterfall 意味 ID '{sid}' が DOM にありません"))
    return diagnostics


def _find_tags_with_exact_class(body: str, tag: str, class_name: str) -> list[tuple[int, str]]:
    """Return (start_index, attrs) for tags whose class token set includes class_name exactly."""
    results: list[tuple[int, str]] = []
    for match in re.finditer(rf'<{tag}\s+([^>]*)>', body, flags=re.IGNORECASE):
        attrs = match.group(1)
        if class_name in _class_tokens_from_attr_string(attrs):
            results.append((match.start(), attrs))
    return results


def _semantic_id_from_attrs(attrs: str) -> str | None:
    match = re.search(r'data-ve-semantic-id="([^"]+)"', attrs)
    return match.group(1) if match else None


def _extract_logic_tree_ids(body: str) -> tuple[str | None, list[str], list[str]]:
    root_tags = _find_tags_with_exact_class(body, "div", "ve-logic-tree-root")
    root_id = _semantic_id_from_attrs(root_tags[0][1]) if root_tags else None
    branch_ids = [
        bid for _, attrs in _find_tags_with_exact_class(body, "div", "ve-logic-tree-branch")
        if (bid := _semantic_id_from_attrs(attrs)) is not None
    ]
    leaf_ids = [
        lid for _, attrs in _find_tags_with_exact_class(body, "li", "ve-logic-tree-leaf")
        if (lid := _semantic_id_from_attrs(attrs)) is not None
    ]
    return root_id, branch_ids, leaf_ids


_LOGIC_TREE_FORBIDDEN_CONNECTOR_ATTRS = (
    "data-ve-semantic-id",
    "data-ve-from",
    "data-ve-to",
    "data-ve-relation",
    "data-connect",
)


def _check_logic_tree_artifact(body: str, parser: _DomSemanticParser) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    branch_rows = _find_tags_with_exact_class(body, "li", "ve-logic-tree-branch-row")
    branch_count = len(branch_rows)
    if branch_count < 2 or branch_count > 4:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      f"logic-tree は2〜4枝である必要があります (found {branch_count})"))

    branch_ols = _find_tags_with_exact_class(body, "ol", "ve-logic-tree-branches")
    if len(branch_ols) != 1:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "logic-tree のコンテナが見つかりません"))
    else:
        container_classes = _class_tokens_from_attr_string(branch_ols[0][1])
        expected_count = f"ve-logic-tree-count-{branch_count}"
        count_tokens = _exact_count_token("ve-logic-tree", container_classes)
        if count_tokens != {expected_count}:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          f"logic-tree のコンテナは {expected_count} である必要があります"))

    root_tags = _find_tags_with_exact_class(body, "div", "ve-logic-tree-root")
    root_id, branch_ids, leaf_ids = _extract_logic_tree_ids(body)
    if len(root_tags) != 1:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "logic-tree の root がありません"))
    elif root_id is None:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "logic-tree root に data-ve-semantic-id がありません"))

    leaf_blocks = _find_tags_with_exact_class(body, "li", "ve-logic-tree-leaf")
    if len(leaf_blocks) != sum(_semantic_id_from_attrs(attrs) is not None for _, attrs in leaf_blocks):
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "logic-tree leaf に data-ve-semantic-id がありません"))
    if branch_count != len(branch_ids):
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "logic-tree 枝に data-ve-semantic-id がありません"))

    tree_ids = ([root_id] if root_id else []) + branch_ids + leaf_ids
    if len(tree_ids) != len(set(tree_ids)):
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "logic-tree の意味 ID が重複しています"))
    for tid in tree_ids:
        if body.count(f'data-ve-semantic-id="{tid}"') != 1:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          f"logic-tree の意味 ID '{tid}' は DOM に1回だけ現れる必要があります"))

    for index, (_, attrs) in enumerate(branch_rows):
        classes = _class_tokens_from_attr_string(attrs)
        position = index + 1
        expected_index = f"ve-logic-tree-index-{position}"
        index_tokens = _exact_index_token("ve-logic-tree", classes)
        if index_tokens != {expected_index}:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          f"logic-tree の枝 {position} は {expected_index} を1つだけ持つ必要があります"))

    spines = _find_tags_with_exact_class(body, "span", "ve-logic-tree-spine")
    if len(spines) != 1:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "logic-tree の spine は1本である必要があります"))
    root_stems = _find_tags_with_exact_class(body, "span", "ve-logic-tree-root-stem")
    if len(root_stems) != 1:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "logic-tree の root-stem は1本である必要があります"))
    spine_columns = _find_tags_with_exact_class(body, "div", "ve-logic-tree-spine-column")
    if len(spine_columns) != 1:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "logic-tree の spine-column は1つである必要があります"))

    connectors = _find_tags_with_exact_class(body, "span", "ve-logic-tree-connector")
    if len(connectors) != branch_count:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      f"logic-tree の connector は枝数と一致する必要があります (found {len(connectors)}, expected {branch_count})"))
    presentation_attrs = [attrs for _, attrs in connectors + spines + root_stems]
    for attrs in presentation_attrs:
        for forbidden in _LOGIC_TREE_FORBIDDEN_CONNECTOR_ATTRS:
            if forbidden in attrs:
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                              f"logic-tree connector に {forbidden} は許可されていません"))
                break
    for _, attrs in connectors:
        if 'aria-hidden="true"' not in attrs:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          "logic-tree connector は aria-hidden である必要があります"))

    layout_tags = _find_tags_with_exact_class(body, "div", "ve-logic-tree-layout-horizontal")
    if len(layout_tags) != 1:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "logic-tree に ve-logic-tree-layout-horizontal がありません"))

    root_pos = root_tags[0][0] if root_tags else -1
    spine_pos = spines[0][0] if spines else -1
    branches_pos = branch_ols[0][0] if branch_ols else -1
    if root_pos >= 0 and branches_pos >= 0 and root_pos > branches_pos:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "logic-tree の DOM 順序は root が branches より前である必要があります"))
    if root_pos >= 0 and spine_pos >= 0 and spine_pos < root_pos:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "logic-tree の spine は root の後である必要があります"))
    if spine_pos >= 0 and branches_pos >= 0 and spine_pos > branches_pos:
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      "logic-tree の spine は branches より前である必要があります"))
    return diagnostics


class _SvgSubtreeParser(HTMLParser):
    """Validate one SVG subtree against the closed element/attribute allowlist."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.diagnostics: list[Diagnostic] = []
        self._svg_depth = 0

    def _reject(self, message: str) -> None:
        self.diagnostics.append(Diagnostic(RENDERER_SVG_VIOLATION, message))

    def _check_value(self, tag: str, name: str, value: str) -> None:
        if name == "viewBox":
            if value != _SVG_VIEWBOX_EXACT:
                self._reject(f"viewBox は '{_SVG_VIEWBOX_EXACT}' の完全一致である必要があります")
        elif name == "preserveAspectRatio":
            if value != _SVG_PRESERVE_EXACT:
                self._reject(f"preserveAspectRatio は '{_SVG_PRESERVE_EXACT}' のみ許可されます")
        elif name == "text-anchor":
            if value not in _SVG_TEXT_ANCHOR:
                self._reject(f"text-anchor '{value}' は許可されていません")
        elif name == "r":
            if not _SVG_R_RE.match(value):
                self._reject(f"属性 r の値 '{value}' が不正です")
        elif name in {"x", "y", "x1", "y1", "x2", "y2", "cx", "cy"}:
            if not _SVG_INT_COORD_RE.match(value):
                self._reject(f"座標属性 {name} の値 '{value}' は整数である必要があります")

    def _check_element(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag not in _SVG_ALLOWED_TAGS:
            self._reject(f"許可されていない SVG 要素 <{tag}>")
            return
        allowed = _SVG_ATTR_ALLOWLIST[tag]
        allowed_lower = {name.lower(): name for name in allowed}
        for name, value in attrs:
            if ":" in name:
                self._reject(f"名前空間属性 '{name}' は許可されていません")
                continue
            lname = name.lower()
            if lname not in allowed_lower:
                self._reject(f"<{tag}> に許可されていない属性 '{name}'")
                continue
            if value is None:
                self._reject(f"<{tag}> の属性 '{name}' に値が必要です")
                continue
            self._check_value(tag, allowed_lower[lname], value)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_l = tag.lower()
        if tag_l == "svg":
            self._svg_depth += 1
            if self._svg_depth > 1:
                self._reject("入れ子の <svg> は許可されていません")
        if self._svg_depth > 0:
            self._check_element(tag_l, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "svg" and self._svg_depth > 0:
            self._svg_depth -= 1


def _section_attr(attrs: str, name: str) -> str | None:
    match = _ATTR_RE(name).search(attrs)
    return match.group(1) if match else None


def _validate_svg_subtree(fragment: str) -> list[Diagnostic]:
    parser = _SvgSubtreeParser()
    parser.feed(fragment)
    parser.close()
    return parser.diagnostics


def validate_renderer_svg(content: str) -> list[Diagnostic]:
    """Enforce allowlisted SVG placement and per-element attribute grammars."""
    diagnostics: list[Diagnostic] = []
    for match in _WRAPPER_SECTION_RE.finditer(content):
        attrs = match.group(1) + match.group(3)
        kind = match.group(2)
        body = match.group(4)
        component = _section_attr(attrs, "data-ve-component")
        version = _section_attr(attrs, "data-ve-contract-version")
        instance = _section_attr(attrs, "data-ve-instance")
        svg_matches = list(_SVG_OPEN_RE.finditer(body))
        if not svg_matches:
            continue
        component_key = f"{component}@{version}" if component and version else ""
        allowed = (
            kind == "canonical"
            and component_key in RENDERER_SVG_ALLOWLIST
        )
        if not allowed:
            diagnostics.append(Diagnostic(
                RENDERER_SVG_VIOLATION,
                f"許可されていないセクションに <svg> があります ({kind}/{component_key or 'unknown'})",
            ))
            continue
        if len(svg_matches) != 1:
            diagnostics.append(Diagnostic(
                RENDERER_SVG_VIOLATION,
                "slope セクションの <svg> は1個である必要があります",
            ))
        for svg_match in svg_matches:
            svg_attrs = svg_match.group(1)
            if "xmlns" in svg_attrs or "xmlns:" in svg_attrs:
                diagnostics.append(Diagnostic(RENDERER_SVG_VIOLATION, "xmlns 宣言は許可されていません"))
            expected_id = f"{instance}-svg" if instance else ""
            sid = _section_attr(svg_attrs, "id")
            if sid != expected_id:
                diagnostics.append(Diagnostic(
                    RENDERER_SVG_VIOLATION,
                    f"<svg> id は '{expected_id}' である必要があります",
                ))
            start = svg_match.start()
            end = body.find("</svg>", svg_match.end())
            if end == -1:
                diagnostics.append(Diagnostic(RENDERER_SVG_VIOLATION, "<svg> が閉じられていません"))
                continue
            subtree = body[start:end + len("</svg>")]
            diagnostics.extend(_validate_svg_subtree(subtree))
    outside = content
    for match in _WRAPPER_SECTION_RE.finditer(content):
        outside = outside.replace(match.group(0), "")
    if _SVG_OPEN_RE.search(outside):
        diagnostics.append(Diagnostic(
            RENDERER_SVG_VIOLATION,
            "セクション外の <svg> は許可されていません",
        ))
    return diagnostics


def _check_slope_artifact(body: str, parser: _DomSemanticParser) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    row_blocks = re.findall(
        r'<g\s+([^>]*\bve-slope-row\b[^>]*)>(.*?)</g>',
        body,
        re.DOTALL,
    )
    item_count = len(row_blocks)
    if item_count < 1 or item_count > 5:
        diagnostics.append(Diagnostic(
            SLOPE_STRUCTURE_VIOLATION,
            f"slope は1〜5項目である必要があります (found {item_count})",
        ))
    for attrs, inner in row_blocks:
        if 'data-ve-semantic-id="' not in attrs:
            diagnostics.append(Diagnostic(
                SLOPE_STRUCTURE_VIOLATION,
                "slope 項目に data-ve-semantic-id がありません",
            ))
        line_items = re.findall(r'<line\s+[^>]*\bve-slope-item\b', inner)
        if len(line_items) != 1:
            diagnostics.append(Diagnostic(
                SLOPE_STRUCTURE_VIOLATION,
                "slope 項目は line.ve-slope-item を1本だけ持つ必要があります",
            ))
    svg_matches = list(_SVG_OPEN_RE.finditer(body))
    if len(svg_matches) != 1:
        diagnostics.append(Diagnostic(
            SLOPE_STRUCTURE_VIOLATION,
            "slope には <svg> がちょうど1つ必要です",
        ))
    return diagnostics


def _notes_semantic_ids(body: str, notes_class: str) -> set[str]:
    notes_match = re.search(
        rf'<ul[^>]*class="[^"]*\b{re.escape(notes_class)}\b[^"]*"[^>]*>(.*?)</ul>',
        body,
        re.DOTALL,
    )
    if notes_match is None:
        return set()
    return set(re.findall(r'data-ve-semantic-id="([^"]+)"', notes_match.group(1)))


def _check_evidence_map_artifact(body: str, parser: _DomSemanticParser) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    card_blocks = re.findall(
        r'<div\s+([^>]*\bve-em-evidence-card\b[^>]*)>(.*?)</div>',
        body,
        re.DOTALL,
    )
    card_count = len(card_blocks)
    if card_count < 2 or card_count > 4:
        diagnostics.append(Diagnostic(
            EVIDENCE_MAP_STRUCTURE_VIOLATION,
            f"evidence-map は根拠2〜4件である必要があります (found {card_count})",
        ))

    conclusion_blocks = re.findall(r'<div\s+([^>]*\bve-em-conclusion\b[^>]*)>', body)
    if len(conclusion_blocks) != 1:
        diagnostics.append(Diagnostic(
            EVIDENCE_MAP_STRUCTURE_VIOLATION,
            "evidence-map には結論カードがちょうど1つ必要です",
        ))
    elif "ve-em-border-strong" not in conclusion_blocks[0]:
        diagnostics.append(Diagnostic(
            EVIDENCE_MAP_STRUCTURE_VIOLATION,
            "結論カードに ve-em-border-strong がありません",
        ))

    note_ids = _notes_semantic_ids(body, "ve-evidence-map-notes")
    for attrs, inner in card_blocks:
        if "data-ve-from" in attrs or "data-ve-to" in attrs:
            diagnostics.append(Diagnostic(
                EVIDENCE_MAP_STRUCTURE_VIOLATION,
                "evidence カードに data-ve-from/to は許可されていません",
            ))
        cert_ref_match = re.search(r'data-ve-certainty-ref="([^"]+)"', attrs)
        if cert_ref_match is None:
            diagnostics.append(Diagnostic(
                EVIDENCE_MAP_STRUCTURE_VIOLATION,
                "evidence カードに data-ve-certainty-ref がありません",
            ))
        elif cert_ref_match.group(1) not in note_ids:
            diagnostics.append(Diagnostic(
                EVIDENCE_MAP_STRUCTURE_VIOLATION,
                f"certaintyRef '{cert_ref_match.group(1)}' が注記に解決できません",
            ))
        source_ref_match = re.search(r'data-ve-source-ref="([^"]+)"', attrs)
        if source_ref_match is not None and source_ref_match.group(1) not in note_ids:
            diagnostics.append(Diagnostic(
                EVIDENCE_MAP_STRUCTURE_VIOLATION,
                f"sourceRef '{source_ref_match.group(1)}' が注記に解決できません",
            ))
        cert_spans = re.findall(
            r'<span\s+([^>]*\bve-cert\b[^>]*)>(.*?)</span>',
            inner,
            re.DOTALL,
        )
        if len(cert_spans) != 1:
            diagnostics.append(Diagnostic(
                EVIDENCE_MAP_STRUCTURE_VIOLATION,
                "evidence カードに ve-cert 要素がちょうど1つ必要です",
            ))
        else:
            _attrs, cert_inner = cert_spans[0]
            if not _visible_text(cert_inner):
                diagnostics.append(Diagnostic(
                    EVIDENCE_MAP_STRUCTURE_VIOLATION,
                    "evidence カードの ve-cert 要素に可視テキストがありません",
                ))
    return diagnostics


COMPONENT_ARTIFACT_CHECKS = {
    "enumeration": _check_enumeration_artifact,
    "chevron": _check_chevron_artifact,
    "pyramid": _check_pyramid_artifact,
    "stairs": _check_stairs_artifact,
    "waterfall": _check_waterfall_artifact,
    "logic-tree": _check_logic_tree_artifact,
    "slope": _check_slope_artifact,
    "evidence-map": _check_evidence_map_artifact,
}

_CANONICAL_SECTION_RE = re.compile(
    r'<section\b[^>]*data-ve-section-kind="canonical"[^>]*>(.*?)</section>', re.DOTALL)


def validate_artifact_semantics(content: str) -> list[Diagnostic]:
    """Artifact-only static/semantic integrity, usable without an in-memory manifest.

    Within each canonical section: flow edges must carry from/to/relation and both
    endpoints must be node semantic IDs of that same flow; matrix cells must carry
    both row and column IDs referencing real headers; non-flow/matrix components must
    not carry flow/matrix relationship attributes; and caption/certainty/source
    notes must survive.
    """
    diagnostics: list[Diagnostic] = []
    component_ids = {cid for cid in _COMPONENTS}
    for body in _CANONICAL_SECTION_RE.findall(content):
        component_match = _COMPONENT_RE.search(body)
        component = component_match.group(1) if component_match else ""
        parser = _parse_dom(body)
        if component == "flow":
            if parser.incomplete_edge:
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, "flow 辺の from/to/relation が揃っていません"))
            for frm, to, _rel in parser.edges:
                if frm not in parser.node_ids:
                    diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, f"flow 辺の from '{frm}' が同一フロー内のノードを参照していません"))
                if to not in parser.node_ids:
                    diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, f"flow 辺の to '{to}' が同一フロー内のノードを参照していません"))
        elif component == "matrix":
            if parser.cell_incomplete:
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, "matrix セルの行/列の関連付けが欠けています"))
            for ref in parser.row_refs:
                if ref not in parser.semantic_ids:
                    diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, f"cell.row 参照 '{ref}' がヘッダに存在しません"))
            for ref in parser.col_refs:
                if ref not in parser.semantic_ids:
                    diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, f"cell.column 参照 '{ref}' がヘッダに存在しません"))
        elif component in component_ids:
            if parser.incomplete_edge or parser.edges:
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                              f"{component} セクションに flow 辺属性は許可されていません"))
            if parser.cell_incomplete or parser.row_refs or parser.col_refs:
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                              f"{component} セクションに matrix セル属性は許可されていません"))
            checker = COMPONENT_ARTIFACT_CHECKS.get(component)
            if checker is not None:
                diagnostics.extend(checker(body, parser))
        if "<figcaption" not in body:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, "canonical セクションに caption がありません"))
        if "data-ve-semantic-id=" not in body:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, "canonical セクションに意味 ID がありません"))
        if component in component_ids:
            if f"ve-{component}-notes" not in body:
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                              f"canonical セクションに確度/出典の注記がありません"))
        elif "ve-matrix-notes" not in body and "ve-flow-notes" not in body:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, "canonical セクションに確度/出典の注記がありません"))
    return diagnostics


def validate_notation_rules(content: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for block in re.findall(r"<(?:p|li)\b[^>]*>.*?</(?:p|li)>", content, re.S):
        if block.count('class="dg-em"') > 1:
            diagnostics.append(Diagnostic(
                code="notation-emphasis-limit",
                message="文中強調 dg-em は1説明文に1つまでです。",
                path="content"))
    for figure in re.findall(r"<figure\b.*?</figure>", content, re.S):
        if figure.count("ve-dg-highlight") > 1:
            diagnostics.append(Diagnostic(
                code="notation-highlight-limit",
                message="teal ハイライトは1図1箇所までです。",
                path="content"))
    if re.search(r"<strong>(確定|推定)[:：]", content):
        diagnostics.append(Diagnostic(
            code="notation-certainty-vocabulary",
            message="確度語彙は 確認済み/推論/未確認 の3語に統一してください。",
            path="content"))
    return diagnostics


def check_final_document(raw: bytes | str, skeleton: bytes | str, registry, expected=None,
                         components_dir: Path | None = None) -> list[Diagnostic]:
    """Run the four-layer checker. Legacy documents pass unchanged.

    Layers: (1) safety/fixed regions, (2) IR/selection is enforced at build time,
    (3) component/manifest — manifest-to-DOM when ``expected`` is present, final
    provenance/semantic attributes otherwise, (4) flattened-document safety.
    """
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    skel = skeleton.decode("utf-8") if isinstance(skeleton, bytes) else skeleton
    if not is_component_document(text):
        return []
    diagnostics: list[Diagnostic] = []
    slots, marker_diags = extract_controlled_slots(text)
    diagnostics += marker_diags
    diagnostics += normalized_fixed_regions(text, skel)
    content = slots.get("content", "")
    if "content" in slots:
        diagnostics += validate_content_markup(content)
        diagnostics += validate_final_provenance(content)
        diagnostics += validate_artifact_semantics(content)
        diagnostics += validate_renderer_svg(content)
        diagnostics += validate_notation_rules(content)
    diagnostics += validate_controlled_assets(slots, registry, components_dir)
    if expected is not None:
        from .final_checks import check_manifest_to_dom
        diagnostics += check_manifest_to_dom(content, slots, expected)
    return diagnostics
