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
    ARTIFACT_SEMANTIC_MISMATCH,
    ASK_CONTRACT_VIOLATION,
    FIXED_REGION_MISMATCH,
    FORBIDDEN_CONTENT_MARKUP,
    INVALID_CONTROLLED_ASSET,
    MISSING_CONTROLLED_MARKER,
    MISSING_PROVENANCE,
    Diagnostic,
)
from .validation import VOCABULARY

_COMPAT_SOURCES = set(VOCABULARY["compatibility"]["sources"])
_COMPAT_REASONS = set(VOCABULARY["compatibility"]["reasons"])
_SECTION_TAG_RE = re.compile(r"<section\b([^>]*)>")
_ATTR_RE = lambda name: re.compile(name + r'="([^"]*)"')

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


def extract_flow_dom(markup: str) -> tuple[set[str], set[tuple[str, str, str]], bool]:
    """Return (node ids, edge (from,to,relation) triples, any-incomplete-edge)."""
    parser = _parse_dom(markup)
    return parser.node_ids, set(parser.edges), parser.incomplete_edge


_CANONICAL_SECTION_RE = re.compile(
    r'<section\b[^>]*data-ve-section-kind="canonical"[^>]*>(.*?)</section>', re.DOTALL)


def validate_artifact_semantics(content: str) -> list[Diagnostic]:
    """Artifact-only static/semantic integrity, usable without an in-memory manifest.

    Within each canonical section: flow edges must carry from/to/relation and both
    endpoints must be node semantic IDs of that same flow; matrix cells must carry
    both row and column IDs referencing real headers; and caption/certainty/source
    notes must survive.
    """
    diagnostics: list[Diagnostic] = []
    for body in _CANONICAL_SECTION_RE.findall(content):
        parser = _parse_dom(body)
        if parser.incomplete_edge:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, "flow 辺の from/to/relation が揃っていません"))
        for frm, to, _rel in parser.edges:
            if frm not in parser.node_ids:
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, f"flow 辺の from '{frm}' が同一フロー内のノードを参照していません"))
            if to not in parser.node_ids:
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, f"flow 辺の to '{to}' が同一フロー内のノードを参照していません"))
        if parser.cell_incomplete:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, "matrix セルの行/列の関連付けが欠けています"))
        for ref in parser.row_refs:
            if ref not in parser.semantic_ids:
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, f"cell.row 参照 '{ref}' がヘッダに存在しません"))
        for ref in parser.col_refs:
            if ref not in parser.semantic_ids:
                diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, f"cell.column 参照 '{ref}' がヘッダに存在しません"))
        if "<figcaption" not in body:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, "canonical セクションに caption がありません"))
        if "data-ve-semantic-id=" not in body:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, "canonical セクションに意味 ID がありません"))
        if "ve-matrix-notes" not in body and "ve-flow-notes" not in body:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH, "canonical セクションに確度/出典の注記がありません"))
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
    diagnostics += validate_controlled_assets(slots, registry, components_dir)
    if expected is not None:
        from .final_checks import check_manifest_to_dom
        diagnostics += check_manifest_to_dom(content, slots, expected)
    return diagnostics
