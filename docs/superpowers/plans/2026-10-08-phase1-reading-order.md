# Phase 1: 読み順と反復の削減 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 第一画面を「題名 → 結論（3 文以内）→ 全体図 → 番号一覧」に変え、同じ主張の反復をビルドで止め、skeleton に版管理を入れて v2 を出す。

**Architecture:** skeleton は `assets/skeleton.html`（最新 = v2）と凍結した `assets/skeleton-v1.html` に分け、checker は文書の `<html data-ve-skeleton>` が宣言する版と照合する。assembly IR は schemaVersion 2 に上げ、first-screen を `conclusion` / `overview` に置き換える。目次の自動生成を廃止し、全体図の直後にビルドが番号一覧（`overview-nav`）を挿入する。反復検査は validation の最後に走る新モジュール `repetition.py` が担う。

**Tech Stack:** Python 3 標準ライブラリのみ（`html.parser`, `re`, `dataclasses`）、pytest（開発時のみ）、bash。

**Spec:** `docs/superpowers/specs/2026-10-07-visual-explain-review-loop-design.md` の「Phase 1」節。

## Global Constraints

- 外部依存ゼロ: build / check は Python 標準ライブラリのみ。npm / pip / Playwright を追加しない。
- 既存配色のみ: skeleton の既存トークン（`--accent` など）だけを使う。新しい色相を足さない。
- 生成 HTML の手編集禁止。見本の修正は IR → `build_explainer.py` で再ビルド。
- 参考にした他者スキルの固有名を、コード・コメント・コミット・文書に書かない。
- コードのコメント / docstring は英語、checker 診断とスキル文書は日本語。
- コミットは conventional commits ＋ `(ve)` スコープ。末尾に次の 2 行を付ける:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` / `Claude-Session: https://claude.ai/code/session_01NgfQq9eGiPhoY46Nmdb2Xv`
- テストは必ず `cd skills/visual-explain/scripts && python3 -m pytest tests -q` で実行する（他ディレクトリからは import に失敗する）。
- 結論: 1〜3 文、各文 80 字以内。番号マーカー: 1〜5 件。図より前の本文: 200 字以内（全体図の無い文書のみ）。類似度しきい値: 文字 bigram Jaccard 0.6。

## Review Focus

- 旧版（v1）で生成済みの HTML（`.visual-explain/*.html`、`tests/*-doc.html`）が `check.sh` で引き続き合格すること → Task 1 の後方互換テスト。
- `data-ve-skeleton="9"` のような未知の版を宣言した文書は、黙って最新版と照合せず「未知の skeleton 版」で落ちること → Task 1。
- 番号マーカーの `target` が canonical セクション（id 属性を持たない）を指したとき、壊れたリンクを出さずにエラーにすること → Task 2。
- 結論が文末記号なしで終わる・句点が連続する（「。。」）などの崩れた入力で、文数判定が例外を出さずに診断を返すこと → Task 2。
- 確度バッジ（`<span class="certainty">未確認</span>`）だけが異なる h2 と claim を「同じ文」と判定できること（バッジ文字で類似度が下がらない）→ Task 4。

---

### Task 1: skeleton の版管理と v2

**Files:**
- Create: `skills/visual-explain/assets/skeleton-v1.html`（現 `skeleton.html` のバイト完全コピー）
- Modify: `skills/visual-explain/assets/skeleton.html`（v2 化: 2 行目の `<html>` タグと 110 行目付近の CSS）
- Create: `skills/visual-explain/scripts/ve_components/skeletons.py`
- Modify: `skills/visual-explain/scripts/ve_components/checker.py`（`check_final_document`）
- Modify: `skills/visual-explain/scripts/check.sh`（埋め込み `check_file`）
- Test: `skills/visual-explain/scripts/tests/test_skeleton_versions.py`

**Interfaces:**
- Produces: `ve_components.skeletons.LATEST_SKELETON_VERSION: int = 2`、`declared_skeleton_version(markup: str) -> int`、`skeleton_file(version: int, assets_dir: Path = ASSETS_DIR) -> Path`、`resolve_skeleton(candidate: str, skeleton: str, assets_dir: Path = ASSETS_DIR) -> str | None`

- [ ] **Step 1: v1 を凍結する**

```bash
cd skills/visual-explain/assets && cp -p skeleton.html skeleton-v1.html && shasum -a 256 skeleton.html skeleton-v1.html
```
Expected: 2 行のハッシュが一致する。

- [ ] **Step 2: 失敗するテストを書く** — `tests/test_skeleton_versions.py`

```python
"""Versioned skeleton resolution: each document is checked against the skeleton it declares."""
from __future__ import annotations

import unittest
from pathlib import Path

from ve_components.checker import check_final_document
from ve_components.registry import load_registry
from ve_components.skeletons import (
    LATEST_SKELETON_VERSION,
    declared_skeleton_version,
    resolve_skeleton,
    skeleton_file,
)

SKILL = Path(__file__).resolve().parents[2]
ASSETS = SKILL / "assets"
LATEST = (ASSETS / "skeleton.html").read_text("utf-8")
V1 = (ASSETS / "skeleton-v1.html").read_text("utf-8")
REGISTRY = load_registry(ASSETS / "components" / "registry.json")
TESTS = Path(__file__).resolve().parent


class SkeletonVersionTest(unittest.TestCase):
    def test_latest_declares_latest_version(self) -> None:
        self.assertEqual(declared_skeleton_version(LATEST), LATEST_SKELETON_VERSION)
        self.assertEqual(LATEST_SKELETON_VERSION, 2)

    def test_missing_attribute_means_v1(self) -> None:
        self.assertEqual(declared_skeleton_version(V1), 1)

    def test_skeleton_file_mapping(self) -> None:
        self.assertEqual(skeleton_file(2, ASSETS), ASSETS / "skeleton.html")
        self.assertEqual(skeleton_file(1, ASSETS), ASSETS / "skeleton-v1.html")

    def test_resolve_returns_given_when_versions_match(self) -> None:
        self.assertIs(resolve_skeleton(LATEST, LATEST, ASSETS), LATEST)

    def test_resolve_loads_frozen_v1_for_v1_document(self) -> None:
        self.assertEqual(resolve_skeleton(V1, LATEST, ASSETS), V1)

    def test_resolve_unknown_version_is_none(self) -> None:
        doc = LATEST.replace('data-ve-skeleton="2"', 'data-ve-skeleton="9"', 1)
        self.assertIsNone(resolve_skeleton(doc, LATEST, ASSETS))

    def test_v2_first_screen_has_no_viewport_min_height(self) -> None:
        rule = next(line for line in LATEST.splitlines() if line.strip().startswith(".first-screen {"))
        self.assertNotIn("min-height", rule)


class BackwardCompatibilityTest(unittest.TestCase):
    def test_v1_rendered_fixtures_still_pass_against_latest(self) -> None:
        for name in ("matrix-doc-all-notations.html", "chevron-doc.html"):
            raw = (TESTS / name).read_text("utf-8")
            self.assertEqual(declared_skeleton_version(raw), 1, name)
            diags = check_final_document(raw, LATEST, REGISTRY, components_dir=ASSETS / "components")
            self.assertEqual([d.message for d in diags], [], name)

    def test_unknown_version_document_fails(self) -> None:
        raw = (TESTS / "matrix-doc-all-notations.html").read_text("utf-8").replace(
            '<html lang="ja"', '<html lang="ja" data-ve-skeleton="9"', 1)
        diags = check_final_document(raw, LATEST, REGISTRY, components_dir=ASSETS / "components")
        self.assertIn("未知の skeleton 版です: 9", [d.message for d in diags])


if __name__ == "__main__":
    unittest.main()
```

どちらも v1 生成物（`data-ve-skeleton` を持たない）であることを `grep -c data-ve-skeleton` が 0 で確認しておく。

- [ ] **Step 3: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_skeleton_versions.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 've_components.skeletons'`）

- [ ] **Step 4: `ve_components/skeletons.py` を書く**

```python
"""Versioned skeleton resolution.

A generated document declares the skeleton version it was built from on its
``<html>`` start tag (``data-ve-skeleton``). Documents without the attribute
are version 1. The checker compares fixed regions against the declared version.
"""
from __future__ import annotations

import re
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
LATEST_SKELETON_VERSION = 2

_HTML_TAG_RE = re.compile(r"<html\b[^>]*>", re.IGNORECASE)
_VERSION_ATTR_RE = re.compile(r'\sdata-ve-skeleton="([0-9]+)"')


def declared_skeleton_version(markup: str) -> int:
    tag = _HTML_TAG_RE.search(markup)
    if tag is None:
        return 1
    match = _VERSION_ATTR_RE.search(tag.group(0))
    return int(match.group(1)) if match else 1


def skeleton_file(version: int, assets_dir: Path = ASSETS_DIR) -> Path:
    if version == LATEST_SKELETON_VERSION:
        return assets_dir / "skeleton.html"
    return assets_dir / f"skeleton-v{version}.html"


def resolve_skeleton(candidate: str, skeleton: str, assets_dir: Path = ASSETS_DIR) -> str | None:
    """Return the skeleton text the candidate must match, or None if unknown."""
    wanted = declared_skeleton_version(candidate)
    if wanted == declared_skeleton_version(skeleton):
        return skeleton
    if not 1 <= wanted <= LATEST_SKELETON_VERSION:
        return None
    try:
        return skeleton_file(wanted, assets_dir).read_text("utf-8")
    except OSError:
        return None
```

- [ ] **Step 5: `check_final_document` で解決する** — `ve_components/checker.py` の `check_final_document` 内、`skel = ...` の直後を次に置き換える

```python
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    skel = skeleton.decode("utf-8") if isinstance(skeleton, bytes) else skeleton
    if not is_component_document(text):
        return []
    from .skeletons import declared_skeleton_version, resolve_skeleton
    resolved = resolve_skeleton(text, skel)
    diagnostics: list[Diagnostic] = []
    if resolved is None:
        diagnostics.append(Diagnostic(
            FIXED_REGION_MISMATCH,
            f"未知の skeleton 版です: {declared_skeleton_version(text)}",
        ))
        resolved = skel
    skel = resolved
```

（元の `diagnostics: list[Diagnostic] = []` の行は削除し、以降の処理は `skel` をそのまま使う。）

- [ ] **Step 6: skeleton.html を v2 にする**

2 行目を次にする:
```html
<html lang="ja" data-theme-storage-key="visual-explain-theme" data-ve-skeleton="2">
```
110 行目の `.first-screen` 規則を次の 6 行で置き換える:
```css
    .first-screen { display: grid; gap: var(--space-3); padding: var(--space-4) 0 var(--space-2); margin-block: 0; background: transparent; border-left: 0; }
    .conclusion { margin: 0; padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: var(--radius); font-size: var(--fs-body); color: var(--text); }
    [data-ve-section-kind="first-screen"] + [data-ve-section-kind="canonical"], [data-ve-section-kind="canonical"] + [data-ve-section-kind="overview-nav"] { margin-top: var(--space-2); }
    .overview-markers ol { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-1); }
    .overview-markers a { display: inline-flex; gap: var(--space-1); align-items: baseline; color: var(--text); text-decoration: none; }
    .overview-markers .marker-n { display: inline-grid; place-items: center; min-width: 1.5rem; height: 1.5rem; border: 2px solid var(--accent); border-radius: 50%; color: var(--accent); font-weight: 700; font-size: var(--fs-small); font-variant-numeric: tabular-nums; }
```

- [ ] **Step 7: check.sh の埋め込み checker で解決する** — `check_file` の `skeleton = skeleton_path.read_bytes()` の直後に追加

```python
    version_match = re.search(rb'<html\b[^>]*\sdata-ve-skeleton="([0-9]+)"', candidate)
    skeleton_version = re.search(rb'<html\b[^>]*\sdata-ve-skeleton="([0-9]+)"', skeleton)
    wanted = int(version_match.group(1)) if version_match else 1
    given = int(skeleton_version.group(1)) if skeleton_version else 1
    if wanted != given:
        frozen = skeleton_path.parent / f"skeleton-v{wanted}.html"
        try:
            skeleton = frozen.read_bytes()
        except OSError:
            return [f"未知の skeleton 版です: {wanted}"]
```

- [ ] **Step 8: 全テストと selftest**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest`
Expected: 全件 PASS、`selftest: 31 passed, 0 failed`。既存テストが skeleton の旧 CSS 文字列を直接検査して落ちた場合は、その期待値を v2 の規則（Step 6）に更新する。

- [ ] **Step 9: Commit**

```bash
git add skills/visual-explain/assets/skeleton.html skills/visual-explain/assets/skeleton-v1.html \
  skills/visual-explain/scripts/ve_components/skeletons.py skills/visual-explain/scripts/ve_components/checker.py \
  skills/visual-explain/scripts/check.sh skills/visual-explain/scripts/tests/test_skeleton_versions.py
git commit -m "feat(ve): version the skeleton and ship v2 first-screen layout"
```

---

### Task 2: assembly schema v2 と first-screen の conclusion / overview

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/model.py:467-471`（`FirstScreenSection`、`OverviewMarker`、`Overview` 追加）
- Modify: `skills/visual-explain/scripts/ve_components/validation.py`（`_FIRST_SCREEN_SECTION_KEYS`、`_RESERVED_CLASSES`、`validate_assembly`、`_validate_first_screen_section`、新関数 `_validate_overview_links`）
- Modify: `skills/visual-explain/references/assembly.schema.json`
- Modify: `skills/visual-explain/scripts/tests/*.json`（first-screen を持つ 76 件）、`examples/example-proposal.assembly.json`、inline IR を持つ test py 12 件
- Create: `skills/visual-explain/scripts/tests/first_screen_ir.py`（共有ヘルパ）
- Test: `skills/visual-explain/scripts/tests/test_first_screen_section.py`（全面書き換え）

**Interfaces:**
- Consumes: `ve_components.document_sections.extract_first_h2_h3(markup: str) -> str | None`（既存）
- Produces: `OverviewMarker(n: int, label: str, target: str)`、`Overview(section: str, markers: tuple[OverviewMarker, ...])`、`FirstScreenSection(id: str, conclusion: str, overview: Overview | None = None)`、`AssemblyRequest.schema_version == 2`、`ve_components.validation.split_sentences(text: str) -> tuple[str, ...] | None`

- [ ] **Step 1: 失敗するテストを書く**

共有ヘルパ `tests/first_screen_ir.py`（Task 3・4 も使う。`tests/` には `__init__.py` が無く、pytest は各テストファイルのディレクトリを `sys.path` に入れるので `from first_screen_ir import ...` で読める）:

```python
"""Shared minimal v2 assembly builders for first-screen, overview, and repetition tests."""
from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path

from ve_components.diagnostics import ContractError
from ve_components.validation import validate_assembly

_HERE = Path(__file__).resolve().parent


def _matrix_canonical() -> dict:
    raw = json.loads((_HERE / "component-valid-matrix.json").read_text("utf-8"), parse_float=Decimal)
    section = next(s for s in raw["sections"] if s.get("kind") == "canonical")
    section = copy.deepcopy(section)
    section["ir"]["id"] = "sec-map"
    section["ir"]["caption"] = "見るところ: 右列の代償。"
    return section


CANONICAL = _matrix_canonical()
CLOSING = {"kind": "closing", "id": "sec-closing", "blocks": [
    {"heading": "リスクと弱い前提", "items": ["前提Aが弱い"]},
    {"heading": "不確かな点", "items": ["未確認の利用状況"]},
]}


def assembly(first: dict, *middle: dict) -> dict:
    return {
        "schemaVersion": 2,
        "document": {"id": "d", "title": "料金改定は限定対象で段階公開する", "summary": "要約文。",
                     "type": "proposal", "profile": "strict"},
        "sections": [{"kind": "first-screen", "id": "sec-first", **first}, *copy.deepcopy(list(middle)), CLOSING],
    }


def narr(sid: str, heading: str, body: str | None = None) -> dict:
    body = body if body is not None else f"<p>本文{sid}。</p>"
    return {"kind": "narrative", "id": sid,
            "markup": f'<section aria-labelledby="{sid}-h"><h2 id="{sid}-h">{heading}</h2>{body}</section>'}


def messages(raw: dict) -> list[str]:
    try:
        validate_assembly(raw)
    except ContractError as exc:
        return [d.message for d in exc.diagnostics]
    return []
```

`component-valid-matrix.json` は Task 2 Step 6 の移行前でも canonical セクションの中身は変わらないので、そのまま使える。

`tests/test_first_screen_section.py` を次で置き換える:

```python
"""first-screen v2: title h1, conclusion (1-3 sentences), optional overview."""
from __future__ import annotations

import unittest

from first_screen_ir import CANONICAL, assembly as _assembly, messages as _messages, narr as _narr
from ve_components.model import FirstScreenSection, Overview, OverviewMarker
from ve_components.validation import split_sentences, validate_assembly


class SplitSentencesTest(unittest.TestCase):
    def test_splits_on_terminators(self) -> None:
        self.assertEqual(split_sentences("限定で始める。前提は二つ！"), ("限定で始める。", "前提は二つ！"))

    def test_trailing_text_without_terminator_is_none(self) -> None:
        self.assertIsNone(split_sentences("限定で始める。前提は二つ"))

    def test_empty_sentence_is_none(self) -> None:
        self.assertIsNone(split_sentences("限定で始める。。"))


class ConclusionValidationTest(unittest.TestCase):
    def test_valid_conclusion_builds_section(self) -> None:
        request = validate_assembly(_assembly({"conclusion": "限定対象で開始する。撤回条件の合意が前提。"}))
        self.assertEqual(request.schema_version, 2)
        first = request.sections[0]
        self.assertIsInstance(first, FirstScreenSection)
        self.assertEqual(first.conclusion, "限定対象で開始する。撤回条件の合意が前提。")
        self.assertIsNone(first.overview)

    def test_four_sentences_rejected(self) -> None:
        self.assertIn("first-screen.conclusion は文末（。！？!?）で終わる1〜3文である必要があります",
                      _messages(_assembly({"conclusion": "一。二。三。四。"})))

    def test_long_sentence_rejected(self) -> None:
        long = "あ" * 80 + "。"
        self.assertIn("first-screen.conclusion の各文は80字以内です（81字）",
                      _messages(_assembly({"conclusion": long})))

    def test_legacy_decision_field_rejected(self) -> None:
        self.assertIn("未知のフィールド 'decision'",
                      _messages(_assembly({"conclusion": "決める。", "decision": "決めます。"})))

    def test_schema_version_1_rejected_with_migration_hint(self) -> None:
        raw = _assembly({"conclusion": "決める。"})
        raw["schemaVersion"] = 1
        self.assertIn("schemaVersion 1 は廃止されました（first-screen を conclusion / overview で書き直してください）",
                      _messages(raw))


class OverviewValidationTest(unittest.TestCase):
    def _first(self, **overview) -> dict:
        base = {"section": "sec-map", "markers": [{"n": 1, "label": "背景", "target": "sec-a"}]}
        base.update(overview)
        return {"conclusion": "限定対象で開始する。", "overview": base}

    def test_valid_overview(self) -> None:
        request = validate_assembly(_assembly(self._first(), CANONICAL, _narr("sec-a", "背景の見出し")))
        self.assertEqual(request.sections[0].overview,
                         Overview(section="sec-map", markers=(OverviewMarker(1, "背景", "sec-a"),)))

    def test_overview_must_point_at_next_canonical(self) -> None:
        msgs = _messages(_assembly(self._first(), _narr("sec-a", "背景の見出し"), CANONICAL))
        self.assertIn("first-screen.overview.section は first-screen 直後の canonical セクションの id である必要があります",
                      msgs)

    def test_marker_target_must_be_linkable(self) -> None:
        first = self._first(markers=[{"n": 1, "label": "図", "target": "sec-map"}])
        self.assertIn("first-screen.overview.markers[0].target 'sec-map' は ask / narrative / closing セクションの id である必要があります",
                      _messages(_assembly(first, CANONICAL)))

    def test_markers_must_be_sequential(self) -> None:
        first = self._first(markers=[{"n": 2, "label": "背景", "target": "sec-a"}])
        self.assertIn("first-screen.overview.markers の n は1からの連番である必要があります",
                      _messages(_assembly(first, CANONICAL, _narr("sec-a", "背景の見出し"))))

    def test_overview_required_with_three_headed_sections(self) -> None:
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "一つ目の見出し"), _narr("sec-b", "二つ目の見出し"), _narr("sec-c", "三つ目の見出し"))
        self.assertIn("h2 節または ask が3つ以上ある資料では first-screen.overview が必要です", _messages(raw))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_first_screen_section.py -q`
Expected: FAIL（`ImportError: cannot import name 'Overview'`）

- [ ] **Step 3: model を変える** — `model.py` の `FirstScreenSection` を次で置き換える

```python
@dataclass(frozen=True)
class OverviewMarker:
    n: int
    label: str
    target: str


@dataclass(frozen=True)
class Overview:
    section: str
    markers: tuple[OverviewMarker, ...]


@dataclass(frozen=True)
class FirstScreenSection:
    id: str
    conclusion: str                     # 1-3 sentences, each <= 80 chars
    overview: Optional[Overview] = None
```

- [ ] **Step 4: validation を変える**

`validation.py` の定数:
```python
_FIRST_SCREEN_SECTION_KEYS = {"kind", "id", "conclusion", "overview"}
_OVERVIEW_KEYS = {"section", "markers"}
_OVERVIEW_MARKER_KEYS = {"n", "label", "target"}
_ASSEMBLY_SCHEMA_VERSION = 2
_MAX_CONCLUSION_SENTENCES = 3
_MAX_CONCLUSION_SENTENCE_CHARS = 80
_MAX_OVERVIEW_MARKERS = 5
_MAX_OVERVIEW_LABEL_CHARS = 30
_SENTENCE_RE = re.compile(r"[^。！？!?]+[。！？!?]")
_RESERVED_CLASSES = frozenset({"first-screen", "closing-section", "ask", "link-domain", "decision-panel",
                               "conclusion", "overview-markers"})
```

`_is_single_sentence` の直後に追加:
```python
def split_sentences(text: str) -> tuple[str, ...] | None:
    """Split on 。！？!?; None when any text is left without a terminator or a sentence is empty."""
    parts = tuple(_SENTENCE_RE.findall(text))
    if not parts or "".join(parts) != text:
        return None
    return parts
```

`validate_assembly` の版判定を置き換える:
```python
    version = raw.get("schemaVersion")
    if version == 1:
        col.add(INVALID_COMPONENT_PAYLOAD,
                "schemaVersion 1 は廃止されました（first-screen を conclusion / overview で書き直してください）",
                "assembly")
    elif version != _ASSEMBLY_SCHEMA_VERSION:
        col.add(INVALID_COMPONENT_PAYLOAD, f"未知の schemaVersion '{version}'", "assembly")
```
同関数の `_validate_document_structure(sections_raw, col)` の直後に `_validate_overview_links(sections_raw, sections, col)` を追加し、末尾の `AssemblyRequest(schema_version=1, ...)` を `schema_version=_ASSEMBLY_SCHEMA_VERSION` にする。

`_validate_first_screen_section` を置き換える:
```python
def _validate_first_screen_section(raw: dict, path: str, col: DiagnosticCollector, seen_ids: set[str]):
    before = len(col.diagnostics)
    _check_keys(raw, _FIRST_SCREEN_SECTION_KEYS, path, col)
    sid = raw.get("id")
    if not _nonblank_str(sid):
        col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.id は空にできません", path)
    conclusion = raw.get("conclusion")
    if not _nonblank_str(conclusion):
        col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.conclusion は空にできません", path)
    else:
        sentences = split_sentences(conclusion)
        if sentences is None or len(sentences) > _MAX_CONCLUSION_SENTENCES:
            col.add(INVALID_COMPONENT_PAYLOAD,
                    "first-screen.conclusion は文末（。！？!?）で終わる1〜3文である必要があります", path)
        else:
            for sentence in sentences:
                if len(sentence) > _MAX_CONCLUSION_SENTENCE_CHARS:
                    col.add(INVALID_COMPONENT_PAYLOAD,
                            f"first-screen.conclusion の各文は80字以内です（{len(sentence)}字）", path)
    overview = _validate_overview(raw.get("overview"), f"{path}.overview", col) if "overview" in raw else None
    if len(col.diagnostics) > before:
        return None
    if sid in seen_ids:
        col.add(DUPLICATE_SEMANTIC_ID, f"section id '{sid}' が重複しています", path)
        return None
    seen_ids.add(sid)
    return FirstScreenSection(id=sid, conclusion=conclusion, overview=overview)


def _validate_overview(raw: object, path: str, col: DiagnosticCollector) -> Overview | None:
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.overview はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _OVERVIEW_KEYS, path, col)
    section = raw.get("section")
    if not _nonblank_str(section):
        col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.overview.section は空にできません", path)
    markers_raw = raw.get("markers")
    if not isinstance(markers_raw, list) or not 1 <= len(markers_raw) <= _MAX_OVERVIEW_MARKERS:
        col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.overview.markers は1〜5件の配列である必要があります", path)
        return None
    markers: list[OverviewMarker] = []
    for i, item in enumerate(markers_raw):
        mp = f"{path}.markers[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.overview.markers の各要素はオブジェクトである必要があります", mp)
            continue
        _check_keys(item, _OVERVIEW_MARKER_KEYS, mp, col)
        label, target = item.get("label"), item.get("target")
        if not _nonblank_str(label) or len(label) > _MAX_OVERVIEW_LABEL_CHARS:
            col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.overview.markers[].label は1〜30字です", mp)
        if not _nonblank_str(target):
            col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.overview.markers[].target は空にできません", mp)
        markers.append(OverviewMarker(n=item.get("n"), label=label or "", target=target or ""))
    if [m.n for m in markers] != list(range(1, len(markers) + 1)):
        col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.overview.markers の n は1からの連番である必要があります", path)
    return Overview(section=section or "", markers=tuple(markers))


def _validate_overview_links(sections_raw: list, sections: list[object], col: DiagnosticCollector) -> None:
    """Cross-section rules for the overview: placement, marker targets, and when it is required."""
    from .document_sections import extract_first_h2_h3

    first = sections[0] if sections and isinstance(sections[0], FirstScreenSection) else None
    if first is None:
        return
    headed = sum(1 for s in sections
                 if isinstance(s, NarrativeSection) and extract_first_h2_h3(s.markup) is not None)
    asks = sum(1 for s in sections if isinstance(s, AskSection))
    if first.overview is None:
        if headed >= 3 or asks >= 3:
            col.add(INVALID_COMPONENT_PAYLOAD,
                    "h2 節または ask が3つ以上ある資料では first-screen.overview が必要です",
                    "assembly.sections[0]")
        return
    second = sections[1] if len(sections) > 1 else None
    if not (isinstance(second, CanonicalSection) and second.ir.id == first.overview.section):
        col.add(INVALID_COMPONENT_PAYLOAD,
                "first-screen.overview.section は first-screen 直後の canonical セクションの id である必要があります",
                "assembly.sections[0].overview")
    linkable = {s.id for s in sections if isinstance(s, (AskSection, NarrativeSection, ClosingSection))}
    for i, marker in enumerate(first.overview.markers):
        if marker.target not in linkable:
            col.add(INVALID_COMPONENT_PAYLOAD,
                    f"first-screen.overview.markers[{i}].target '{marker.target}' は ask / narrative / closing セクションの id である必要があります",
                    "assembly.sections[0].overview")
```

`validation.py` の model import に `Overview`, `OverviewMarker` を足す（`AskSection` / `NarrativeSection` / `ClosingSection` / `CanonicalSection` が未 import なら同じく足す）。

- [ ] **Step 4b: 描画を暫定的に合わせる** — `document_sections.py` の `render_first_screen` を次の暫定実装にする（旧フィールドが無くなるため。最終形は Task 3）:

```python
def render_first_screen(section: FirstScreenSection, document: DocumentMetadata) -> WrappedDocumentSection:
    markup = (
        f'<section data-ve-section-kind="first-screen"'
        f' data-ve-document-type="{_esc(document.type)}" data-ve-profile="{_esc(document.profile)}"'
        f' id="{_esc(section.id)}">\n'
        f'<section class="first-screen" aria-label="最初に伝えること">\n'
        f'  <h1>{_esc(document.title)}</h1>\n'
        f'  <p class="subtitle">{_esc(section.conclusion)}</p>\n'
        f'</section>\n</section>'
    )
    return WrappedDocumentSection(instance_id=section.id, markup=markup)
```

- [ ] **Step 5: 新テストを通す**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_first_screen_section.py -q`
Expected: PASS

- [ ] **Step 6: fixture を一括移行する（使い捨てスクリプト、コミットしない）**

`$SCRATCH/migrate_v2.py`（`$SCRATCH` はセッションの scratchpad）:
```python
"""One-off: rewrite assembly fixtures to schemaVersion 2 first-screen."""
import json, re, sys
from decimal import Decimal
from pathlib import Path

def conclusion_of(fs: dict) -> str:
    text = fs.pop("decision", "").strip()
    fs.pop("conditions", None)
    if text and text[-1] not in "。！？!?":
        text += "。"
    return text or "結論を述べる。"

def migrate_json(path: Path) -> None:
    raw = json.loads(path.read_text("utf-8"), parse_float=Decimal)
    if not isinstance(raw, dict) or raw.get("schemaVersion") != 1:
        return
    raw["schemaVersion"] = 2
    for s in raw.get("sections", []):
        if isinstance(s, dict) and s.get("kind") == "first-screen" and "decision" in s:
            s["conclusion"] = conclusion_of(s)
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2, default=str) + "\n", "utf-8")
    print("json", path)

FS_RE = re.compile(r'("kind":\s*"first-screen",\s*"id":\s*"[^"]*",\s*)"decision":')
COND_RE = re.compile(r',\s*"conditions":\s*\[[^\]]*\]')

def migrate_py(path: Path) -> None:
    text = path.read_text("utf-8")
    new = FS_RE.sub(r'\1"conclusion":', text).replace('"schemaVersion": 1', '"schemaVersion": 2')
    new = COND_RE.sub("", new)
    if new != text:
        path.write_text(new, "utf-8")
        print("py", path)

root = Path(sys.argv[1])
for p in sorted(root.glob("scripts/tests/*.json")) + [root / "examples/example-proposal.assembly.json"]:
    migrate_json(p)
for p in sorted(root.glob("scripts/tests/test_*.py")):
    if p.name != "test_first_screen_section.py":
        migrate_py(p)
```
Run: `python3 -I "$SCRATCH/migrate_v2.py" skills/visual-explain`
Expected: `json …` が約 77 行、`py …` が約 12 行出る。`git diff --stat` で JSON の数値表記（`Decimal`）が変わっていないことを確認する（変わったファイルは `git checkout` で戻し、`"schemaVersion": 1` → `2` と first-screen の `"decision"` → `"conclusion"` だけを手で直す）。

- [ ] **Step 7: 全テストで残りを潰す**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q 2>&1 | tail -30`
落ちたテストを次の規則だけで直す（挙動は変えない）:
- 「`first-screen.overview が必要`」で落ちる fixture: `sections[1]` が canonical ならその id を `overview.section` にし、markers に最初の ask（無ければ最初の h2 付き narrative）を 1 件入れる。canonical でなければ h2 付き narrative が 2 つ以下になるよう、テスト目的に無関係な narrative を 1 つ削る。
- 旧 first-screen の文言（「あなたが決めること」「この資料が答える問い」、`p.subtitle decision`、conditions の `<ul>`）や `FirstScreenSection(decision=...)` を検査しているテスト: `FirstScreenSection(id=..., conclusion=...)` に置換し、描画の期待値は Step 4b の暫定描画（`<p class="subtitle">結論</p>`）に合わせる。Task 3 で最終形の期待値に再度更新する。
- `visual-stage` 系: 同じ置換で通る。
Expected: 全件 PASS。

- [ ] **Step 8: schema JSON を更新する** — `references/assembly.schema.json` の first-screen 定義を次にする（`schemaVersion` の `const` も `2` にする）

```json
{
  "type": "object",
  "required": ["kind", "id", "conclusion"],
  "additionalProperties": false,
  "properties": {
    "kind": {"const": "first-screen"},
    "id": {"type": "string", "minLength": 1},
    "conclusion": {"type": "string", "minLength": 1, "description": "1〜3 文、各文 80 字以内、文末は 。！？!?"},
    "overview": {
      "type": "object",
      "required": ["section", "markers"],
      "additionalProperties": false,
      "properties": {
        "section": {"type": "string", "minLength": 1, "description": "first-screen 直後の canonical セクションの id"},
        "markers": {
          "type": "array", "minItems": 1, "maxItems": 5,
          "items": {
            "type": "object", "required": ["n", "label", "target"], "additionalProperties": false,
            "properties": {
              "n": {"type": "integer", "minimum": 1, "maximum": 5},
              "label": {"type": "string", "minLength": 1, "maxLength": 30},
              "target": {"type": "string", "minLength": 1, "description": "ask / narrative / closing セクションの id"}
            }
          }
        }
      }
    }
  }
}
```
Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest`
Expected: 全件 PASS。

- [ ] **Step 9: Commit**

```bash
git add -A skills/visual-explain/scripts skills/visual-explain/references/assembly.schema.json \
  skills/visual-explain/examples/example-proposal.assembly.json
git commit -m "feat(ve): replace first-screen decision with conclusion and overview (schema v2)"
```

---

### Task 3: 第一画面の描画と番号一覧（目次の廃止）

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/document_sections.py`（`render_first_screen` 最終形、`build_overview_nav` 追加、`build_toc` / `TocEntry` / `_SUBTITLE_LABEL` 削除）
- Modify: `skills/visual-explain/scripts/build_explainer.py`（`_collect_toc_entries` 削除、nav 挿入、narrative の id 付与）
- Modify: `skills/visual-explain/scripts/ve_components/checker.py:1125`（`overview-nav` kind を許可。`toc` は旧文書のため残す）
- Modify: `skills/visual-explain/scripts/ve_components/document_checks.py:366`（`p.conclusion` を summary として数える）
- Delete: `skills/visual-explain/scripts/tests/test_toc_generation.py`
- Test: `skills/visual-explain/scripts/tests/test_overview_nav.py`

**Interfaces:**
- Consumes: `FirstScreenSection`, `Overview`, `OverviewMarker`（Task 2）
- Produces: `build_overview_nav(first: FirstScreenSection, *, occupied_ids: frozenset[str] | set[str] = frozenset()) -> WrappedDocumentSection | None`。生成 markup は `<section data-ve-section-kind="overview-nav">` 直下に `<nav class="overview-markers" aria-label="この資料の論点"><ol>…</ol></nav>`。第一画面は `<p class="conclusion"><strong>結論:</strong> …</p>`。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_overview_nav.py`

```python
"""First-screen v2 rendering and the overview marker list that replaces the TOC."""
from __future__ import annotations

import unittest
from pathlib import Path

from build_explainer import build_document
from ve_components.document_sections import build_overview_nav, render_first_screen
from ve_components.model import DocumentMetadata, FirstScreenSection, Overview, OverviewMarker
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from first_screen_ir import CANONICAL, assembly as _assembly, narr as _narr

SKILL = Path(__file__).resolve().parents[2]
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS = SKILL / "assets" / "components"
REGISTRY = load_registry(COMPONENTS / "registry.json")
DOC = DocumentMetadata(id="d", title="料金改定は限定対象で段階公開する", summary="要約文。",
                       type="proposal", profile="strict")
FIRST = FirstScreenSection(
    id="sec-first", conclusion="限定対象で開始する。",
    overview=Overview(section="sec-map", markers=(OverviewMarker(1, "背景", "sec-a"),
                                                  OverviewMarker(2, "リスク", "sec-closing"))))


def _build(raw: dict) -> str:
    return build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS, document_path="/tmp/x.html")


class FirstScreenRenderTest(unittest.TestCase):
    def test_title_and_conclusion_only(self) -> None:
        markup = render_first_screen(FIRST, DOC).markup
        self.assertIn("<h1>料金改定は限定対象で段階公開する</h1>", markup)
        self.assertIn('<p class="conclusion"><strong>結論:</strong> 限定対象で開始する。</p>', markup)
        self.assertNotIn("要約文。", markup)
        self.assertNotIn("subtitle", markup)


class OverviewNavTest(unittest.TestCase):
    def test_nav_lists_markers_in_order(self) -> None:
        nav = build_overview_nav(FIRST)
        self.assertIn('data-ve-section-kind="overview-nav"', nav.markup)
        self.assertIn('<a href="#sec-a"><span class="marker-n" aria-hidden="true">1</span><span>背景</span></a>', nav.markup)
        self.assertLess(nav.markup.index("#sec-a"), nav.markup.index("#sec-closing"))

    def test_no_overview_no_nav(self) -> None:
        self.assertIsNone(build_overview_nav(FirstScreenSection(id="f", conclusion="一文。")))

    def test_built_document_places_nav_after_overview_and_has_no_toc(self) -> None:
        raw = _assembly({"conclusion": "限定対象で開始する。",
                         "overview": {"section": "sec-map",
                                      "markers": [{"n": 1, "label": "背景", "target": "sec-a"}]}},
                        CANONICAL, _narr("sec-a", "背景の見出し"))
        html = _build(raw)
        self.assertNotIn('data-ve-section-kind="toc"', html)
        first = html.index('data-ve-section-kind="first-screen"')
        canon = html.index('data-ve-section-kind="canonical"')
        nav = html.index('data-ve-section-kind="overview-nav"')
        self.assertLess(first, canon)
        self.assertLess(canon, nav)
        self.assertIn('data-ve-instance="sec-a" id="sec-a"', html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_overview_nav.py -q`
Expected: FAIL（`ImportError: cannot import name 'build_overview_nav'`）

- [ ] **Step 3: `document_sections.py` を書き換える**

`_TOC_INSTANCE_ID_PREFIX` / `_TOC_MIN_ENTRIES` / `_SUBTITLE_LABEL` / `TocEntry` / `allocate_toc_instance_id` / `build_toc` を削除し、次を加える:
```python
_OVERVIEW_NAV_INSTANCE_ID_PREFIX = "sec-overview-nav"


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
```

- [ ] **Step 4: `build_explainer.py` を書き換える**

`_collect_toc_entries` と `build_toc` / `TocEntry` / `extract_first_h2_h3` の import を削除し、`build_document` の前半を次にする:
```python
    request = validate_assembly(raw_assembly)
    occupied_ids = frozenset(_section_instance_id(section) for section in request.sections)
    first = request.sections[0]
    nav = build_overview_nav(first, occupied_ids=occupied_ids)
    marked = {m.target for m in first.overview.markers} if first.overview is not None else set()
    items = []
    for section in request.sections:
        if isinstance(section, CanonicalSection):
            items.append(process_canonical_section(section, registry, renderers))
        elif isinstance(section, NarrativeSection):
            items.append(process_narrative_section(section, include_anchor_id=section.id in marked))
        elif isinstance(section, FirstScreenSection):
            items.append(render_first_screen(section, request.document))
        elif isinstance(section, ClosingSection):
            items.append(render_closing(section))
        elif isinstance(section, AskSection):
            items.append(render_ask(section))
        else:
            items.append(process_compatibility_section(section))
    panel = render_decision_panel(
        tuple(s for s in request.sections if isinstance(s, AskSection)),
        request.document, request.schema_version, document_path,
        occupied_ids=occupied_ids | ({nav.instance_id} if nav is not None else frozenset()))
    if panel is not None:
        items.append(panel)
    if nav is not None:
        # first-screen [0], overview canonical [1], then the marker list.
        items.insert(2, nav)
```
import に `build_overview_nav` を足す。

- [ ] **Step 5: checker と構造検査を通す**

`checker.py` の `elif kind == "toc":` の直後に:
```python
        elif kind == "overview-nav":
            # Build-time overview marker list: trusted renderer output.
            pass
```
`document_checks.py:366` の条件を:
```python
            if (("subtitle" in classes and "decision" not in classes) or "conclusion" in classes) and text:
```

- [ ] **Step 6: 旧 TOC テストを消し、全テストを通す**

```bash
git rm skills/visual-explain/scripts/tests/test_toc_generation.py
cd skills/visual-explain/scripts && python3 -m pytest tests -q 2>&1 | tail -30
```
Task 2 Step 7 で残した「旧描画文言（あなたが決めること / この資料が答える問い / `p.subtitle`）」を期待するテストは、`<p class="conclusion"><strong>結論:</strong> …` の期待に置き換える。
Expected: 全件 PASS、`bash check.sh --selftest` も `31 passed, 0 failed`。

- [ ] **Step 7: Commit**

```bash
git add -A skills/visual-explain/scripts
git commit -m "feat(ve): render conclusion first-screen and overview markers instead of TOC"
```

---

### Task 4: 反復の検査（repetition.py）

**Files:**
- Create: `skills/visual-explain/scripts/ve_components/repetition.py`
- Modify: `skills/visual-explain/scripts/ve_components/diagnostics.py`（`REDUNDANT_TEXT = "redundant_text"`）
- Modify: `skills/visual-explain/scripts/ve_components/validation.py`（`validate_assembly` の `col.raise_if_any()` 直前で呼ぶ）
- Test: `skills/visual-explain/scripts/tests/test_repetition.py`

**Interfaces:**
- Consumes: `FirstScreenSection`, `NarrativeSection`, `CanonicalSection`, `AskSection`, `ClosingSection`、`split_sentences`
- Produces: `check_repetition(sections: tuple[object, ...]) -> list[tuple[str, str]]`（`(message, path)` の列）、`bigram_jaccard(a: str, b: str) -> float`、`normalize_sentence(s: str) -> str`

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_repetition.py`

```python
"""Build-time repetition gate: the same claim must not be restated."""
from __future__ import annotations

import copy
import unittest

from first_screen_ir import CANONICAL, assembly as _assembly, messages as _msgs, narr as _narr
from ve_components.repetition import bigram_jaccard, normalize_sentence


class HelpersTest(unittest.TestCase):
    def test_jaccard_identical_is_one(self) -> None:
        self.assertEqual(bigram_jaccard("限定公開で始める", "限定公開で始める"), 1.0)

    def test_normalize_strips_punctuation_and_space(self) -> None:
        self.assertEqual(normalize_sentence("限定 公開、で始める。"), "限定公開で始める")


class RepetitionGateTest(unittest.TestCase):
    def test_h2_and_claim_restated(self) -> None:
        body = '<p class="claim">部門別に確認すると限定公開の影響は判断できない。<span class="certainty unverified">未確認</span></p>'
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "部門別に確認する限り限定公開の影響は判断できない", body))
        self.assertIn("見出しと主張行がほぼ同じ文です（sec-a）。主張行を削るか、見出しと別の情報を書いてください", _msgs(raw))

    def test_distinct_claim_passes(self) -> None:
        body = '<p class="claim">請求と通知が別の顧客群を指していた事例が過去に2件ある。</p>'
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "部門別の確認では影響を判断できない", body))
        self.assertEqual(_msgs(raw), [])

    def test_caption_restates_previous_h2(self) -> None:
        canon = copy.deepcopy(CANONICAL)
        canon["ir"]["caption"] = "限定公開だけが影響確認の機会を残しつつ改定を進められる。"
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "限定公開だけが影響確認の機会を残しつつ改定を進められる", "<p>補足。</p>"), canon)
        self.assertIn("図のキャプションが直前の見出しの言い換えです（sec-map）。キャプションには「何を見るか」を書いてください",
                      _msgs(raw))

    def test_duplicate_sentence(self) -> None:
        sentence = "これは説明用の想定であり実在の状況ではありません。"
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "背景", f"<p>{sentence}</p>"),
                        _narr("sec-b", "前提", f"<p>{sentence}</p>"))
        self.assertIn("同じ文が2回出てきます: 「これは説明用の想定であり実在の状況ではありません。」", _msgs(raw))

    def test_too_much_text_before_first_figure(self) -> None:
        long_body = "<p>" + "あ" * 120 + "。</p><p>" + "い" * 100 + "。</p>"
        raw = _assembly({"conclusion": "限定対象で開始する。"}, _narr("sec-a", "背景", long_body), CANONICAL)
        self.assertIn("最初の図より前の本文が224字あります（上限200字）", _msgs(raw))

    def test_figureless_document_is_not_limited(self) -> None:
        long_body = "<p>" + "あ" * 300 + "。</p>"
        raw = _assembly({"conclusion": "限定対象で開始する。"}, _narr("sec-a", "背景", long_body))
        self.assertEqual(_msgs(raw), [])


if __name__ == "__main__":
    unittest.main()
```

（「224字」= h2「背景」2 字 + 本文 121 字 + 101 字。`repetition.py` は空白と記号を除いた字数に文末記号の数を足して数える。）

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_repetition.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 've_components.repetition'`）

- [ ] **Step 3: `repetition.py` を書く**

```python
"""Build-time repetition gate over validated assembly sections.

Rejects restating the same claim: h2 vs its claim line, a figure caption vs the
preceding h2, a sentence repeated anywhere, and long prose before the first
figure when the document has no overview.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

from .model import AskSection, CanonicalSection, ClosingSection, CompatibilitySection, FirstScreenSection, NarrativeSection

SIMILARITY_THRESHOLD = 0.6
MAX_CHARS_BEFORE_FIGURE = 200
_MIN_DUPLICATE_CHARS = 10
_NOISE_RE = re.compile(r"[\s、。，．,.！？!?「」『』（）()・:：;；\-—]")
_SENTENCE_RE = re.compile(r"[^。！？!?]+[。！？!?]")


def normalize_sentence(text: str) -> str:
    return _NOISE_RE.sub("", text)


def bigram_jaccard(a: str, b: str) -> float:
    def grams(s: str) -> set[str]:
        s = normalize_sentence(s)
        return {s[i:i + 2] for i in range(len(s) - 1)} or {s}
    ga, gb = grams(a), grams(b)
    return len(ga & gb) / len(ga | gb) if ga | gb else 0.0


class _Blocks(HTMLParser):
    """Collect (tag, classes, text) for h2/h3/p/li, ignoring certainty badges."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, frozenset[str], str]] = []
        self._open: list[tuple[str, frozenset[str], list[str]]] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        classes = frozenset((dict(attrs).get("class") or "").split())
        if "certainty" in classes:
            self._skip += 1
        elif tag in {"h2", "h3", "p", "li"}:
            self._open.append((tag, classes, []))

    def handle_endtag(self, tag):
        if self._skip and tag == "span":
            self._skip -= 1
        elif self._open and self._open[-1][0] == tag:
            t, c, parts = self._open.pop()
            self.blocks.append((t, c, "".join(parts).strip()))

    def handle_data(self, data):
        if not self._skip and self._open:
            self._open[-1][2].append(data)


def _blocks(markup: str) -> list[tuple[str, frozenset[str], str]]:
    parser = _Blocks()
    parser.feed(markup)
    parser.close()
    return parser.blocks


def check_repetition(sections: tuple[object, ...]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    sentences: list[str] = []
    last_h2: str | None = None
    chars_before_figure = 0
    seen_figure = False
    first = sections[0] if sections and isinstance(sections[0], FirstScreenSection) else None

    for section in sections:
        if isinstance(section, FirstScreenSection):
            sentences += _SENTENCE_RE.findall(section.conclusion)
        elif isinstance(section, NarrativeSection):
            blocks = _blocks(section.markup)
            for i, (tag, classes, text) in enumerate(blocks):
                if tag == "h2":
                    last_h2 = text
                    nxt = blocks[i + 1] if i + 1 < len(blocks) else None
                    if nxt and "claim" in nxt[1] and bigram_jaccard(text, nxt[2]) >= SIMILARITY_THRESHOLD:
                        out.append((f"見出しと主張行がほぼ同じ文です（{section.id}）。主張行を削るか、見出しと別の情報を書いてください",
                                    section.id))
                if tag in {"p", "li"}:
                    sentences += _SENTENCE_RE.findall(text)
                if not seen_figure:
                    chars_before_figure += len(normalize_sentence(text)) + sum(
                        1 for ch in text if ch in "。！？!?")
        elif isinstance(section, CanonicalSection):
            seen_figure = True
            caption = section.ir.caption or ""
            if last_h2 and bigram_jaccard(caption, last_h2) >= SIMILARITY_THRESHOLD:
                out.append((f"図のキャプションが直前の見出しの言い換えです（{section.ir.id}）。キャプションには「何を見るか」を書いてください",
                            section.ir.id))
            sentences += _SENTENCE_RE.findall(caption)
        elif isinstance(section, CompatibilitySection):
            seen_figure = True
        elif isinstance(section, AskSection):
            for text in (section.question, section.claim.text if section.claim else None, section.verify):
                if text:
                    sentences += _SENTENCE_RE.findall(text)
        elif isinstance(section, ClosingSection):
            for block in section.blocks:
                for item in block.items:
                    sentences += _SENTENCE_RE.findall(item)

    counts: dict[str, tuple[int, str]] = {}
    for s in sentences:
        key = normalize_sentence(s)
        if len(key) < _MIN_DUPLICATE_CHARS:
            continue
        n, original = counts.get(key, (0, s))
        counts[key] = (n + 1, original)
    for n, original in counts.values():
        if n >= 2:
            out.append((f"同じ文が{n}回出てきます: 「{original}」", "assembly.sections"))

    has_overview = first is not None and first.overview is not None
    if seen_figure and not has_overview and chars_before_figure > MAX_CHARS_BEFORE_FIGURE:
        out.append((f"最初の図より前の本文が{chars_before_figure}字あります（上限200字）", "assembly.sections"))
    return out
```


- [ ] **Step 4: validation に接続する** — `diagnostics.py` に `REDUNDANT_TEXT = "redundant_text"` を追加。`validate_assembly` の `col.raise_if_any()` の直前に:

```python
    if not col.diagnostics:
        from .repetition import check_repetition
        for message, where in check_repetition(tuple(sections)):
            col.add(REDUNDANT_TEXT, message, where)
```

- [ ] **Step 5: テストを通し、既存 fixture の誤検出を直す**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q 2>&1 | tail -30`
既存 fixture が `redundant_text` で落ちた場合は、その fixture の文言を片方だけ言い換えて反復を解消する（検査を緩めない）。`examples/example-proposal.assembly.json` が落ちるのは想定内で、Task 6 で直すため、`test_example*` 系の失敗だけは Task 6 まで残してよい。それ以外は全件 PASS。

- [ ] **Step 6: Commit**

```bash
git add -A skills/visual-explain/scripts
git commit -m "feat(ve): reject restated claims, captions, duplicate sentences, and long pre-figure prose"
```

---

### Task 5: 文字量の報告

**Files:**
- Create: `skills/visual-explain/scripts/ve_components/metrics.py`
- Modify: `skills/visual-explain/scripts/build_explainer.py`（`main` の成功出力）
- Test: `skills/visual-explain/scripts/tests/test_metrics.py`

**Interfaces:**
- Produces: `TextMetrics(body_chars: int, chars_before_figure: int, figures: int)`、`text_metrics(document: str) -> TextMetrics`、`format_metrics(m: TextMetrics) -> str`

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_metrics.py`

```python
from __future__ import annotations

import unittest

from ve_components.metrics import TextMetrics, format_metrics, text_metrics

DOC = (
    "<html><body><!-- VE-CONTROLLED:CONTENT:BEGIN -->"
    '<section data-ve-section-kind="first-screen"><h1>題名です</h1></section>'
    '<section data-ve-section-kind="canonical"><p>図の中</p></section>'
    '<section data-ve-section-kind="narrative"><p>本文 です。</p></section>'
    '<section data-ve-section-kind="decision-panel"><p>回収パネルは数えない</p></section>'
    "<!-- VE-CONTROLLED:CONTENT:END --></body></html>"
)


class MetricsTest(unittest.TestCase):
    def test_counts(self) -> None:
        self.assertEqual(text_metrics(DOC), TextMetrics(body_chars=4 + 3 + 5, chars_before_figure=4, figures=1))

    def test_format(self) -> None:
        self.assertEqual(format_metrics(TextMetrics(1400, 80, 3)), "本文 1400 字 / 図より前 80 字 / 図 3 点")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_metrics.py -q`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: `metrics.py` を書く**

```python
"""Reader-facing text volume of a built document (reported, never enforced)."""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

_BEGIN = "<!-- VE-CONTROLLED:CONTENT:BEGIN -->"
_END = "<!-- VE-CONTROLLED:CONTENT:END -->"
_FIGURE_KINDS = frozenset({"canonical", "compatibility"})
_EXCLUDED_KINDS = frozenset({"decision-panel"})
_VOID_TAGS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"})


@dataclass(frozen=True)
class TextMetrics:
    body_chars: int
    chars_before_figure: int
    figures: int


class _Counter(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str | None] = []
        self.body = self.before = self.figures = 0
        self.seen_figure = False

    def handle_starttag(self, tag, attrs):
        if tag in _VOID_TAGS:
            return
        kind = dict(attrs).get("data-ve-section-kind") if tag == "section" else None
        if kind in _FIGURE_KINDS:
            self.figures += 1
            self.seen_figure = True
        self.stack.append(kind if kind else (self.stack[-1] if self.stack else None))

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.stack and self.stack[-1] in _EXCLUDED_KINDS:
            return
        n = sum(1 for ch in data if not ch.isspace())
        self.body += n
        if not self.seen_figure:
            self.before += n


def text_metrics(document: str) -> TextMetrics:
    start, end = document.find(_BEGIN), document.find(_END)
    content = document[start + len(_BEGIN):end] if 0 <= start < end else ""
    counter = _Counter()
    counter.feed(content)
    counter.close()
    return TextMetrics(counter.body, counter.before, counter.figures)


def format_metrics(m: TextMetrics) -> str:
    return f"本文 {m.body_chars} 字 / 図より前 {m.chars_before_figure} 字 / 図 {m.figures} 点"
```

- [ ] **Step 4: `build_explainer.main` に出力を足す** — `print(f"OK: {paths.output}")` を次にする

```python
    result = build_to_path(raw_assembly, paths)
    print(f"OK: {paths.output}")
    print(format_metrics(text_metrics(result.html)))
```
（直前の `build_to_path(raw_assembly, paths)` 呼び出しは `result = ...` に置き換える。import に `from ve_components.metrics import format_metrics, text_metrics`。）

- [ ] **Step 5: 通す**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_metrics.py -q && python3 -m pytest tests -q`
Expected: PASS（Task 4 で許容した見本関連の失敗を除く）

- [ ] **Step 6: Commit**

```bash
git add skills/visual-explain/scripts/ve_components/metrics.py skills/visual-explain/scripts/build_explainer.py \
  skills/visual-explain/scripts/tests/test_metrics.py
git commit -m "feat(ve): report body, pre-figure, and figure counts after build"
```

---

### Task 6: 同梱見本を新しい読み順で書き直す

**Files:**
- Modify: `skills/visual-explain/examples/example-proposal.assembly.json`
- Modify: `skills/visual-explain/examples/example-proposal.html`（再ビルド生成物）

- [ ] **Step 1: IR を書き直す**（`python3 -I` の使い捨てスクリプトか手編集）

1. `sections` を次の順に並べ替える: first-screen → canonical `sec-alternatives`（全体図にする）→ narrative `sec-current-problem` → narrative `sec-approval-map-intro` → compatibility `sec-approval-map` → compatibility `sec-before-after-compare` → ask `sec-ask-hypothesis` → ask `sec-ask-decision` → closing。
2. first-screen を次にする:
```json
{"kind": "first-screen", "id": "sec-first-screen",
 "conclusion": "限定対象で段階公開を始める。例外・請求・告知が同じ顧客群を指すことと、撤回条件の事前合意が前提。",
 "overview": {"section": "sec-alternatives", "markers": [
   {"n": 1, "label": "部門別確認の限界", "target": "sec-current-problem"},
   {"n": 2, "label": "承認地図での照合", "target": "sec-approval-map-intro"},
   {"n": 3, "label": "限定対象で開始するか", "target": "sec-ask-decision"}]}}
```
3. narrative を削る:
   - `sec-current-problem`: `<p class="evidence">これは正規見本のための想定です…</p>` と `<details class="source-note">…</details>` を削除。
   - `sec-approval-map-evidence` と `sec-before-after-intro` と `sec-alternatives-intro` を削除する。
4. closing の「不確かな点」の items に `"この資料は説明用の想定で、実在の顧客・契約・請求データは使っていません。"` を足す（見本注記の集約先）。
5. `sec-alternatives` の `caption` を `"見るところ: 右列のトレードオフ。限定公開だけが影響範囲を絞れる。"` にする。

- [ ] **Step 2: 再ビルドして数値を確認する**

```bash
cd "$(git rev-parse --show-toplevel)"
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/examples/example-proposal.assembly.json \
  --output skills/visual-explain/examples/example-proposal.html
```
Expected: `OK: …` の次行が `本文 N 字 / 図より前 M 字 / 図 3 点` で、N ≤ 1400。FAIL が出た場合は診断の文言どおりに IR を直して再実行する（`redundant_text` なら片方を削る）。M は h1 と結論の文字数だけになっていること（約 90 字以下）。

- [ ] **Step 3: 検査と目視**

```bash
bash skills/visual-explain/scripts/check.sh skills/visual-explain/examples/example-proposal.html
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars \
  --window-size=1440,900 --screenshot="$SCRATCH/fold.png" \
  "file://$(pwd)/skills/visual-explain/examples/example-proposal.html"
```
Expected: check.sh が無出力で終了コード 0。`fold.png`（Read ツールで開く）に h1・結論ボックス・比較表（全体図）の上端が収まっている。収まらない場合は Task 1 Step 6 の余白値を `var(--space-3)` → `var(--space-2)` に詰め、Task 1 のテストを再実行する。

- [ ] **Step 4: 全テスト**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest`
Expected: 全件 PASS、selftest 31 passed。

- [ ] **Step 5: Commit**

```bash
git add skills/visual-explain/examples/example-proposal.assembly.json skills/visual-explain/examples/example-proposal.html
git commit -m "docs(ve): rebuild the bundled proposal example in the conclusion-first order"
```

---

### Task 7: スキル文書の更新

**Files:**
- Modify: `skills/visual-explain/SKILL.md`（ワークフロー手順 5、「型と第一画面」節）
- Modify: `skills/visual-explain/references/patterns.md`（first-screen の例と説明）
- Modify: `CLAUDE.md`（リポジトリ概要の skeleton 不変条件の 1 文）

- [ ] **Step 1: SKILL.md**

「型と第一画面」節の first-screen の説明を次に置き換える:
```markdown
第一画面は「題名（`document.title`）→ 結論 → 全体図 → 番号一覧」の順にビルドが描く。IR の first-screen には `conclusion`（1〜3 文、各文 80 字以内）を書き、h2 付きの節か ask が 3 つ以上ある資料では `overview` を書く。`overview.section` は first-screen 直後に置いた canonical セクションの id、`overview.markers` は 1〜5 件で、各番号の行き先（ask / narrative / closing の id）とラベル（30 字以内）を持つ。番号一覧が目次を兼ねるので、目次は生成しない。`document.summary` はメタ情報で、画面には出ない。
```
手順 5 に次の 1 文を足す:
```markdown
ビルドは同じ主張の反復を止める（h2 と直後の主張行、図キャプションと直前の h2 の言い換え、同じ文の 2 回以上の出現、全体図の無い資料で最初の図より前の本文 200 字超）。診断が出たら片方を削って再ビルドする。成功時の「本文 N 字 / 図より前 M 字 / 図 K 点」を見て、文字量を確かめる。
```
`schemaVersion` の記述をすべて `2` にする。

- [ ] **Step 2: patterns.md** — 完全な JSON 例の first-screen を Task 6 Step 1 の形（`conclusion` ＋ `overview`）にし、`decision` / `conditions` の説明を削除する。`grep -n '"decision":\|conditions' skills/visual-explain/references/patterns.md` の結果が first-screen に関するものゼロであること。

- [ ] **Step 3: CLAUDE.md** — 「不可侵の骨格」節の「checker が skeleton と SHA-256 でバイト一致比較する」の直後に足す:
```markdown
skeleton は版ごとに不変で、最新版が `assets/skeleton.html`（`<html data-ve-skeleton="N">`）、旧版は `assets/skeleton-vN.html` に凍結する。checker は文書が宣言する版と照合する。
```

- [ ] **Step 4: 確認と Commit**

```bash
grep -rn "あなたが決めること\|目次" skills/visual-explain/SKILL.md skills/visual-explain/references/patterns.md
cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest
cd "$(git rev-parse --show-toplevel)"
git add skills/visual-explain/SKILL.md skills/visual-explain/references/patterns.md CLAUDE.md
git commit -m "docs(ve): document conclusion-first layout, overview markers, and skeleton versions"
```
Expected: grep は first-screen の旧説明に該当する行ゼロ。全テスト PASS。
