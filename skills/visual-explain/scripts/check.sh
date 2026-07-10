#!/usr/bin/env bash
# Validate visual-explain HTML without dependencies beyond Python's standard library.
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec python3 - "$SCRIPT_DIR" "$@" <<'PY'
from __future__ import annotations

import hashlib
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

BEGIN = b"<!-- CONTENT:BEGIN -->"
END = b"<!-- CONTENT:END -->"
FORBIDDEN_TAGS = {"script", "style", "meta", "iframe", "form", "object", "embed"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def content_bounds(raw: bytes, label: str, errors: list[str]) -> tuple[int, int] | None:
    if raw.count(BEGIN) != 1 or raw.count(END) != 1:
        errors.append(f"{label}: CONTENT マーカーは BEGIN/END を各1個含めてください")
        return None
    begin = raw.index(BEGIN) + len(BEGIN)
    end = raw.index(END)
    if begin > end:
        errors.append(f"{label}: CONTENT マーカーの順序が不正です")
        return None
    return begin, end


def fixed_regions_match(candidate: bytes, skeleton: bytes, errors: list[str]) -> bytes:
    candidate_bounds = content_bounds(candidate, "生成HTML", errors)
    skeleton_bounds = content_bounds(skeleton, "skeleton", errors)
    if candidate_bounds is None or skeleton_bounds is None:
        return b""
    candidate_prefix = candidate[:candidate_bounds[0]]
    candidate_suffix = candidate[candidate_bounds[1]:]
    skeleton_prefix = skeleton[:skeleton_bounds[0]]
    skeleton_suffix = skeleton[skeleton_bounds[1]:]
    if hashlib.sha256(candidate_prefix).digest() != hashlib.sha256(skeleton_prefix).digest():
        errors.append("固定領域が skeleton.html と一致しません (CONTENT:BEGIN より前)")
    if hashlib.sha256(candidate_suffix).digest() != hashlib.sha256(skeleton_suffix).digest():
        errors.append("固定領域が skeleton.html と一致しません (CONTENT:END より後)")
    return candidate[candidate_bounds[0]:candidate_bounds[1]]


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
    else:
        if "限界・確度" not in inspector.headings:
            errors.append(f"{type_name}: 末尾節「限界・確度」が必要です")

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


def check_file(html_path: Path, type_name: str, skeleton_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        candidate = html_path.read_bytes()
    except OSError as exc:
        return [f"生成HTMLを読めません: {exc}"]
    try:
        skeleton = skeleton_path.read_bytes()
    except OSError as exc:
        return [f"skeleton.htmlを読めません: {exc}"]
    content_bytes = fixed_regions_match(candidate, skeleton, errors)
    try:
        full_text = candidate.decode("utf-8")
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return errors + ["HTML は UTF-8 である必要があります"]
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
    pattern_checks(content, type_name, inspector, errors)
    return errors


def usage() -> int:
    print("usage: check.sh <生成HTML> --type <proposal|system|research> | check.sh --selftest", file=sys.stderr)
    return 2


def run_selftest(script_dir: Path) -> int:
    cases = [
        ("valid-proposal.html", "proposal", ()),
        ("bad-external-url.html", "proposal", ("<img> の src: 外部リソース参照は使えません: https://example.invalid/image.png",)),
        ("bad-onclick.html", "proposal", ("<button>: イベント属性 onclick は禁止です",)),
        ("bad-decision.html", "proposal", ("proposal: 第一画面に「あなたが決めること」の判断文が1件必要です",)),
        ("bad-closing.html", "proposal", ("proposal: 末尾節「不確かな点」が必要です",)),
        ("bad-fixed-region.html", "proposal", ("固定領域が skeleton.html と一致しません (CONTENT:BEGIN より前)", "固定領域が skeleton.html と一致しません (CONTENT:END より後)")),
        ("bad-data-connect.html", "proposal", ("data-connect: 参照 ID が存在しません: unknown",)),
        ("bad-javascript-link.html", "proposal", ("<a> の href: 許可されない URL スキームです: javascript:alert(1)",)),
        ("bad-forbidden-tag.html", "proposal", ("禁止タグ <script> が CONTENT 内にあります",)),
        ("bad-id-duplicate.html", "proposal", ("id は文書内で一意である必要があります: duplicate",)),
        ("bad-animation.html", "proposal", ("禁止アニメーション: infinite 指定は使えません",)),
        ("bad-svg-reason.html", "proposal", ("自由 SVG には SVG理由 コメントが必要です",)),
        ("bad-absolute-px.html", "proposal", ("座標直書き: position:absolute と複数の px 指定は使えません",)),
        ("bad-nesting.html", "proposal", ("ネスト不整合: </div> の前に <span> を閉じる必要があります", "ネスト不整合: </section> の前に <span> を閉じる必要があります", "ネスト不整合: 閉じられていないタグがあります: <section>, <div>, <span>")),
        ("bad-svg-xlink-javascript.html", "proposal", ("<a> の xlink:href: 許可されない URL スキームです: javascript:alert(1)",)),
        ("valid-system.html", "system", ()),
        ("valid-research.html", "research", ()),
        ("bad-system-closing.html", "system", ("system: 末尾節「限界・確度」が必要です",)),
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
    print(f"selftest: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


def main(argv: list[str]) -> int:
    if not argv:
        return usage()
    script_dir = Path(argv[0])
    args = argv[1:]
    if args == ["--selftest"]:
        return run_selftest(script_dir)
    if len(args) != 3 or args[1] != "--type" or args[2] not in {"proposal", "system", "research"}:
        return usage()
    errors = check_file(Path(args[0]), args[2], script_dir.parent / "assets" / "skeleton.html")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
PY
