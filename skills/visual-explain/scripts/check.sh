#!/usr/bin/env bash
# Validate visual-explain HTML without dependencies beyond Python's standard library.
# Public CLI (unchanged): check.sh <html> --type <proposal|system|research>,
# check.sh --selftest. New: check.sh <html> auto-detects legacy type or the
# component route and additionally runs the four-layer component checker.
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SKELETON="$SCRIPT_DIR/../assets/skeleton.html"
REGISTRY="$SCRIPT_DIR/../assets/components/registry.json"

set +e
python3 - "$SCRIPT_DIR" "$@" <<'PY'
from __future__ import annotations

import hashlib
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

TITLE_BEGIN = b"<!-- TITLE:BEGIN -->"
TITLE_END = b"<!-- TITLE:END -->"
CONTENT_BEGIN = b"<!-- CONTENT:BEGIN -->"
CONTENT_END = b"<!-- CONTENT:END -->"
# Controlled component slots that live in the fixed head/script regions. Their
# bodies are variable (trusted, hash-verified assets injected at build time), so
# they are normalized away before the fixed-region comparison. The content slot
# lives inside the already-variable CONTENT body and needs no stripping here.
CONTROLLED_FIXED_SLOTS = (b"COMPONENT-STYLES", b"COMPONENT-SCRIPTS")


def strip_fixed_controlled(raw: bytes) -> bytes:
    for name in CONTROLLED_FIXED_SLOTS:
        pattern = re.compile(
            rb"[ \t]*<!-- VE-CONTROLLED:" + name + rb":BEGIN -->.*?<!-- VE-CONTROLLED:" + name + rb":END -->[ \t]*\n?",
            re.DOTALL,
        )
        raw = pattern.sub(b"", raw)
    return raw
FORBIDDEN_TAGS = {"script", "style", "meta", "iframe", "form", "object", "embed"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def slot_bounds(raw: bytes, begin_marker: bytes, end_marker: bytes, slot: str, label: str, errors: list[str]) -> tuple[int, int] | None:
    if raw.count(begin_marker) != 1 or raw.count(end_marker) != 1:
        errors.append(f"{label}: {slot} マーカーは BEGIN/END を各1個含めてください")
        return None
    begin = raw.index(begin_marker) + len(begin_marker)
    end = raw.index(end_marker)
    if begin > end:
        errors.append(f"{label}: {slot} マーカーの順序が不正です")
        return None
    return begin, end


def fixed_regions_match(candidate: bytes, skeleton: bytes, errors: list[str]) -> tuple[bytes, bytes | None]:
    candidate_title = slot_bounds(candidate, TITLE_BEGIN, TITLE_END, "TITLE", "生成HTML", errors)
    candidate_content = slot_bounds(candidate, CONTENT_BEGIN, CONTENT_END, "CONTENT", "生成HTML", errors)
    skeleton_title = slot_bounds(skeleton, TITLE_BEGIN, TITLE_END, "TITLE", "skeleton", errors)
    skeleton_content = slot_bounds(skeleton, CONTENT_BEGIN, CONTENT_END, "CONTENT", "skeleton", errors)
    content = candidate[candidate_content[0]:candidate_content[1]] if candidate_content else b""
    title = candidate[candidate_title[0]:candidate_title[1]] if candidate_title else None
    if None in (candidate_title, candidate_content, skeleton_title, skeleton_content):
        return content, title
    assert candidate_title and candidate_content and skeleton_title and skeleton_content
    if candidate_title[1] > candidate_content[0]:
        errors.append("生成HTML: TITLE スロットは CONTENT スロットより前に置いてください")
        return content, title
    if skeleton_title[1] > skeleton_content[0]:
        errors.append("skeleton: TITLE スロットは CONTENT スロットより前に置いてください")
        return content, title
    candidate_fixed = (
        candidate[:candidate_title[0]],
        candidate[candidate_title[1]:candidate_content[0]],
        candidate[candidate_content[1]:],
    )
    skeleton_fixed = (
        skeleton[:skeleton_title[0]],
        skeleton[skeleton_title[1]:skeleton_content[0]],
        skeleton[skeleton_content[1]:],
    )
    labels = ("TITLE:BEGIN より前", "TITLE:END から CONTENT:BEGIN まで", "CONTENT:END より後")
    for candidate_region, skeleton_region, label in zip(candidate_fixed, skeleton_fixed, labels):
        if hashlib.sha256(candidate_region).digest() != hashlib.sha256(skeleton_region).digest():
            errors.append(f"固定領域が skeleton.html と一致しません ({label})")
    return content, title


def validate_title(title: str, errors: list[str]) -> None:
    match = re.fullmatch(r"\s*<title>(.*?)</title>\s*", title, re.IGNORECASE | re.DOTALL)
    if match is None:
        errors.append("title: TITLE スロットには <title> 要素を1つだけ置いてください")
        return
    value = match.group(1)
    if re.search(r"\{\{[^{}]+\}\}", value):
        errors.append("title: 未解決プレースホルダーは使えません")
    elif not value.strip():
        errors.append("title: タイトルは空にできません")
    elif "<" in value or ">" in value:
        errors.append("title: タイトルにはマークアップを使えません")


def class_has(attrs: dict[str, str | None], name: str) -> bool:
    return name in (attrs.get("class") or "").split()


class IdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name.lower() == "id" and value is not None:
                self.ids.append(value)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


class ContentInspector(HTMLParser):
    def __init__(self, all_ids: set[str]) -> None:
        super().__init__(convert_charrefs=True)
        self.all_ids = all_ids
        self.errors: list[str] = []
        self.stack: list[str] = []
        self.first_screen_depth: int | None = None
        self.active_decisions: list[tuple[int, list[str]]] = []
        self.decisions: list[str] = []
        self.headings: list[str] = []
        self.active_headings: list[tuple[int, list[str]]] = []
        self.comments: list[str] = []
        self.svg_count = 0

    def check_url(self, value: str, context: str) -> None:
        value = value.strip()
        if not value or value.startswith("#"):
            return
        parsed = urlsplit(value)
        scheme = parsed.scheme.lower()
        if value.startswith("//") or scheme not in {"", "https", "file"}:
            self.errors.append(f"{context}: 許可されない URL スキームです: {value}")
        elif context.startswith("<") and " の src" in context and scheme == "https":
            self.errors.append(f"{context}: 外部リソース参照は使えません: {value}")

    def check_attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            name = name.lower()
            local_name = name.rsplit(":", 1)[-1]
            if name.startswith("on"):
                self.errors.append(f"<{tag}>: イベント属性 {name} は禁止です")
            if local_name in {"href", "src"} and value is not None:
                self.check_url(value, f"<{tag}> の {name}")
            if name == "data-connect" and value is not None:
                declarations = [item.strip() for item in value.split(",") if item.strip()]
                if not declarations:
                    self.errors.append("data-connect: 接続指定が空です")
                for declaration in declarations:
                    parts = [part.strip() for part in declaration.split("->")]
                    if len(parts) != 2 or not all(parts):
                        self.errors.append(f"data-connect: 接続形式が不正です: {declaration}")
                        continue
                    for target in parts:
                        if target not in self.all_ids:
                            self.errors.append(f"data-connect: 参照 ID が存在しません: {target}")

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs = dict(attrs_list)
        if tag in FORBIDDEN_TAGS:
            self.errors.append(f"禁止タグ <{tag}> が CONTENT 内にあります")
        if tag in {"animate", "animatetransform", "set"}:
            self.errors.append(f"禁止アニメーションタグ <{tag}> が CONTENT 内にあります")
        self.check_attrs(tag, attrs_list)
        if tag not in VOID_TAGS:
            self.stack.append(tag)
        depth = len(self.stack)
        if class_has(attrs, "first-screen"):
            self.first_screen_depth = depth
        if self.first_screen_depth is not None and class_has(attrs, "decision"):
            self.active_decisions.append((depth, []))
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.active_headings.append((depth, []))
        if tag == "svg":
            self.svg_count += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in VOID_TAGS:
            return
        if not self.stack:
            self.errors.append(f"ネスト不整合: </{tag}> に対応する開始タグがありません")
            return
        if self.stack[-1] != tag:
            self.errors.append(f"ネスト不整合: </{tag}> の前に <{self.stack[-1]}> を閉じる必要があります")
            return
        depth = len(self.stack)
        if self.active_headings and self.active_headings[-1][0] == depth:
            _, text = self.active_headings.pop()
            self.headings.append("".join(text).strip())
        if self.active_decisions and self.active_decisions[-1][0] == depth:
            _, text = self.active_decisions.pop()
            self.decisions.append("".join(text).strip())
        if self.first_screen_depth == depth:
            self.first_screen_depth = None
        self.stack.pop()

    def handle_data(self, data: str) -> None:
        for _, decision in self.active_decisions:
            decision.append(data)
        for _, heading in self.active_headings:
            heading.append(data)

    def handle_comment(self, data: str) -> None:
        self.comments.append(data)

    def finish(self) -> None:
        if self.stack:
            self.errors.append("ネスト不整合: 閉じられていないタグがあります: " + ", ".join(f"<{tag}>" for tag in self.stack))



def validate_decision(inspector: ContentInspector, errors: list[str]) -> None:
    # Only decision elements opened in .first-screen are collected. A sentence
    # must be a single visible Japanese sentence following the fixed label.
    if len(inspector.decisions) != 1:
        errors.append("proposal: 第一画面に「あなたが決めること」の判断文が1件必要です")
        return
    text = inspector.decisions[0]
    if "あなたが決めること" not in text:
        errors.append("proposal: 判断文に「あなたが決めること」がありません")
        return
    remainder = re.sub(r"^.*?あなたが決めること\s*[:：]?\s*", "", text, count=1).strip()
    sentence_marks = re.findall(r"[。！？!?]", remainder)
    if not remainder or len(sentence_marks) != 1 or not re.search(r"[。！？!?]\s*$", remainder):
        errors.append("proposal: 「あなたが決めること」は1文で記述してください")


def pattern_checks(content: str, type_name: str, inspector: ContentInspector, errors: list[str]) -> None:
    if type_name == "proposal":
        validate_decision(inspector, errors)
        for required in ("リスクと弱い前提", "不確かな点"):
            if required not in inspector.headings:
                errors.append(f"proposal: 末尾節「{required}」が必要です")
    elif type_name == "system":
        if "限界・確度" not in inspector.headings:
            errors.append("system: 末尾節「限界・確度」が必要です")
    elif "限界・反証・確度" not in inspector.headings:
        errors.append("research: 末尾節「限界・反証・確度」が必要です")

    if re.search(r"animation(?:-iteration-count)?\s*:[^;}]*\binfinite\b", content, re.IGNORECASE):
        errors.append("禁止アニメーション: infinite 指定は使えません")
    for _, raw_url in re.findall(r"url\(\s*(['\"]?)(.*?)\1\s*\)", content, re.IGNORECASE | re.DOTALL):
        css_url = raw_url.strip()
        parsed = urlsplit(css_url)
        if css_url.startswith("//") or parsed.scheme.lower() not in {"", "https", "file"}:
            errors.append(f"CSS url(): 許可されない URL スキームです: {css_url}")
        elif parsed.scheme.lower() == "https":
            errors.append(f"CSS url(): 外部リソース参照は使えません: {css_url}")
    if inspector.svg_count:
        reasons = re.findall(r"<!--.*?(?:svg\s*(?:の)?\s*(?:理由|reason)|(?:理由|reason).*?svg).*?-->", content, re.IGNORECASE | re.DOTALL)
        if len(reasons) < inspector.svg_count:
            errors.append("自由 SVG には SVG理由 コメントが必要です")
    for style in re.findall(r"\bstyle\s*=\s*(['\"])(.*?)\1", content, re.IGNORECASE | re.DOTALL):
        declarations = style[1]
        if re.search(r"\bposition\s*:\s*absolute\b", declarations, re.IGNORECASE) and len(re.findall(r"[-+]?\d*\.?\d+px\b", declarations, re.IGNORECASE)) >= 2:
            errors.append("座標直書き: position:absolute と複数の px 指定は使えません")
            break


def check_file(html_path: Path, type_name: str | None, skeleton_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        candidate = html_path.read_bytes()
    except OSError as exc:
        return [f"生成HTMLを読めません: {exc}"]
    try:
        skeleton = skeleton_path.read_bytes()
    except OSError as exc:
        return [f"skeleton.htmlを読めません: {exc}"]
    content_bytes, title_bytes = fixed_regions_match(strip_fixed_controlled(candidate), strip_fixed_controlled(skeleton), errors)
    try:
        full_text = candidate.decode("utf-8")
        content = content_bytes.decode("utf-8")
        title = title_bytes.decode("utf-8") if title_bytes is not None else None
    except UnicodeDecodeError:
        return errors + ["HTML は UTF-8 である必要があります"]
    if title is not None:
        validate_title(title, errors)
    ids = IdCollector()
    ids.feed(full_text)
    ids.close()
    for identifier in sorted({item for item in ids.ids if ids.ids.count(item) > 1}):
        errors.append(f"id は文書内で一意である必要があります: {identifier}")
    inspector = ContentInspector(set(ids.ids))
    inspector.feed(content)
    inspector.close()
    inspector.finish()
    errors.extend(inspector.errors)
    # type_name is None for component/mixed documents, whose closing sections are
    # driven by the canonical route rather than the legacy pattern requirements.
    if type_name is not None:
        pattern_checks(content, type_name, inspector, errors)
    return errors


def is_component_document(raw: bytes) -> bool:
    return (b"VE-CONTROLLED:" in raw or b"data-ve-component" in raw
            or b"data-ve-section-kind" in raw)


def detect_legacy_type(content_text: str) -> str:
    if "限界・反証・確度" in content_text:
        return "research"
    if "限界・確度" in content_text:
        return "system"
    return "proposal"


def usage() -> int:
    print("usage: check.sh <生成HTML> [--type <proposal|system|research>] | check.sh --selftest", file=sys.stderr)
    return 2


def run_selftest(script_dir: Path) -> int:
    cases = [
        ("valid-proposal.html", "proposal", ()),
        ("bad-external-url.html", "proposal", ("<img> の src: 外部リソース参照は使えません: https://example.invalid/image.png",)),
        ("bad-onclick.html", "proposal", ("<button>: イベント属性 onclick は禁止です",)),
        ("bad-decision.html", "proposal", ("proposal: 第一画面に「あなたが決めること」の判断文が1件必要です",)),
        ("bad-closing.html", "proposal", ("proposal: 末尾節「不確かな点」が必要です",)),
        ("bad-fixed-region.html", "proposal", ("固定領域が skeleton.html と一致しません (TITLE:BEGIN より前)", "固定領域が skeleton.html と一致しません (CONTENT:END より後)")),
        ("bad-title-empty.html", "proposal", ("title: タイトルは空にできません",)),
        ("bad-title-markup.html", "proposal", ("title: タイトルにはマークアップを使えません",)),
        ("bad-title-placeholder.html", "proposal", ("title: 未解決プレースホルダーは使えません",)),
        ("bad-title-missing.html", "proposal", ("生成HTML: TITLE マーカーは BEGIN/END を各1個含めてください",)),
        ("bad-data-connect.html", "proposal", ("data-connect: 参照 ID が存在しません: unknown",)),
        ("bad-javascript-link.html", "proposal", ("<a> の href: 許可されない URL スキームです: javascript:alert(1)",)),
        ("bad-forbidden-tag.html", "proposal", ("禁止タグ <script> が CONTENT 内にあります",)),
        ("bad-id-duplicate.html", "proposal", ("id は文書内で一意である必要があります: duplicate",)),
        ("bad-animation.html", "proposal", ("禁止アニメーション: infinite 指定は使えません",)),
        ("bad-animate.html", "proposal", ("禁止アニメーションタグ <animate> が CONTENT 内にあります",)),
        ("bad-css-url.html", "proposal", ("CSS url(): 許可されない URL スキームです: data:text/plain,blocked",)),
        ("bad-svg-reason.html", "proposal", ("自由 SVG には SVG理由 コメントが必要です",)),
        ("bad-absolute-px.html", "proposal", ("座標直書き: position:absolute と複数の px 指定は使えません",)),
        ("bad-nesting.html", "proposal", ("ネスト不整合: </div> の前に <span> を閉じる必要があります", "ネスト不整合: </section> の前に <span> を閉じる必要があります", "ネスト不整合: 閉じられていないタグがあります: <section>, <div>, <span>")),
        ("bad-svg-xlink-javascript.html", "proposal", ("<a> の xlink:href: 許可されない URL スキームです: javascript:alert(1)",)),
        ("valid-system.html", "system", ()),
        ("valid-research.html", "research", ()),
        ("bad-system-closing.html", "system", ("system: 末尾節「限界・確度」が必要です",)),
        ("valid-system.html", "research", ("research: 末尾節「限界・反証・確度」が必要です",)),
    ]
    passed = failed = 0
    skeleton = script_dir.parent / "assets" / "skeleton.html"
    fixtures = script_dir / "tests"
    for filename, type_name, expected_errors in cases:
        errors = check_file(fixtures / filename, type_name, skeleton)
        if errors == list(expected_errors):
            passed += 1
        else:
            failed += 1
            print(f"selftest failure: {filename}: diagnostics differed", file=sys.stderr)
            print(f"  expected: {list(expected_errors)!r}", file=sys.stderr)
            print(f"  actual:   {errors!r}", file=sys.stderr)

    # Group 3 structure checks (component checker path).
    sys.path.insert(0, str(script_dir))
    from ve_components.checker import check_final_document
    from ve_components.registry import load_registry
    registry_path = script_dir.parent / "assets" / "components" / "registry.json"
    registry = load_registry(registry_path)
    structure_cases = [
        ("structure-bad-no-first-screen.html", ("文書型の自己表明がありません",)),
        ("structure-bad-duplicate-h1.html", ("h1 は first-screen 内にちょうど1個必要です",)),
        ("structure-bad-title-mismatch.html", ("title と h1 が一致しません",)),
        ("structure-bad-no-closing.html", ("closing セクションがありません",)),
    ]
    for filename, expected_errors in structure_cases:
        raw = (fixtures / filename).read_text("utf-8")
        diags = check_final_document(
            raw, skeleton.read_text("utf-8"), registry,
            components_dir=registry_path.parent,
        )
        errors = tuple(d.message for d in diags)
        if errors == expected_errors:
            passed += 1
        else:
            failed += 1
            print(f"selftest failure: {filename}: diagnostics differed", file=sys.stderr)
            print(f"  expected: {list(expected_errors)!r}", file=sys.stderr)
            print(f"  actual:   {list(errors)!r}", file=sys.stderr)

    print(f"selftest: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


def main(argv: list[str]) -> int:
    if not argv:
        return usage()
    script_dir = Path(argv[0])
    args = argv[1:]
    if args == ["--selftest"]:
        return run_selftest(script_dir)
    skeleton = script_dir.parent / "assets" / "skeleton.html"
    if len(args) == 3 and args[1] == "--type" and args[2] in {"proposal", "system", "research"}:
        html_path, type_name = Path(args[0]), args[2]
    elif len(args) == 1:
        html_path = Path(args[0])
        try:
            raw = html_path.read_bytes()
        except OSError as exc:
            print(f"FAIL: 生成HTMLを読めません: {exc}")
            return 1
        if is_component_document(raw):
            type_name = None  # universal safety only; component layers run separately
        else:
            type_name = detect_legacy_type(raw.decode("utf-8", errors="replace"))
    else:
        return usage()
    errors = check_file(html_path, type_name, skeleton)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
PY
embedded_status=$?
set -e

# --selftest and usage errors are fully handled by the embedded checker.
if [ "${1:-}" = "--selftest" ]; then
  exit "$embedded_status"
fi
if [ "$embedded_status" -eq 2 ]; then
  exit 2
fi

# Run the four-layer component checker on the same document. It recognizes a
# pre-migration legacy document (no markers/data-ve) and passes it unchanged.
DOC="$1"
DOC_ABS="$(CDPATH= cd -- "$(dirname -- "$DOC")" && pwd)/$(basename -- "$DOC")"
set +e
python3 "$SCRIPT_DIR/check_component_html.py" "$DOC_ABS" "$SKELETON" "$REGISTRY"
component_status=$?
set -e

if [ "$embedded_status" -eq 0 ] && [ "$component_status" -eq 0 ]; then
  echo "PASS"
  exit 0
fi
exit 1
