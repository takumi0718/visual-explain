# 判断資料 v3 Phase 1（基盤）実装計画

> **For agentic workers:** この計画はタスク単位で実装する。各タスクは TDD（失敗するテスト→最小実装→パス→コミット）で進め、チェックボックス（`- [ ]`）で進捗を管理する。正本 spec: `docs/superpowers/specs/2026-07-16-decision-document-v3-design.md`。計画と spec が矛盾したら実装せず報告する。

**Goal:** IR に document.type / document.profile / 型付きセクション（first-screen・closing・ask）を導入し、検査群③（正直さ・構造）を新設して「構造なし資料が PASS する」穴を塞ぎ、外部出典リンク・summary 描画・自動目次を実装する。

**Architecture:** 型付きセクションは registry を通らない信頼済みレンダラ（`document_sections.py` 新設）として実装し、既存の composer / flattener にダックタイプ（`instance_id` / `markup`）で合流する。文書型と profile は first-screen の wrapper に data 属性で自己表明し、`check_final_document` に新設する検査群③がそれを読む。**Phase 1 では `assets/skeleton.html` を 1 バイトも変更しない**（型付きセクションは既存の `.first-screen` / `.closing-section` / `.ask` CSS を使う）。

**Tech Stack:** Python 3 標準ライブラリのみ（実装・検査とも）。テストは pytest（開発時専用）。

## Global Constraints

- `assets/skeleton.html` は変更禁止（固定領域ハッシュを壊す。回収 JS は Phase 2、CSP は Phase 3）。
- 診断メッセージは日本語。既存テストは診断文字列の完全一致で検証するため、既存文言の変更は対応するテスト・selftest 期待値の更新を伴う。
- テストは必ず `skills/visual-explain/scripts/` から `python3 -m pytest tests -q` で実行する（`ve_components` を cwd 経由で import するため）。
- コミットは conventional commits ＋ `(ve)` スコープ（例: `feat(ve): ...`）。1 タスク 1 コミット以上。
- 後方互換は切る（spec の決定）: 旧方式（narrative への first-screen / closing / ask 生 HTML）は受理せず、旧 IR フィールドの別名・救済コードを書かない。
- 予約 data 属性（`data-ve-*`, `data-connect`, `data-connect-scope`, `data-stepper`, `data-step`, `data-step-action`, `data-ask`, `data-ask-*`, `data-theme`, `data-theme-*`, `data-lane`, `data-tone`）と予約 class（`first-screen`, `closing-section`, `ask`, `link-domain`）は narrative / freeform の markup で禁止。レンダラ出力と compatibility 節のみ許可。
- YAGNI: Phase 2（回収 JS）・Phase 3（code/image/freeform）の先取り実装をしない。ask は**静的表示のみ**。

## ファイル構成（新規/変更の全体地図)

- 新規 `scripts/ve_components/document_sections.py` — first-screen / closing / ask の型付きレンダラと目次生成（1 責務: 型付きセクション→検査済み markup）。
- 新規 `scripts/ve_components/document_checks.py` — 検査群③(最終文書の構造検査。type/profile 表明を読む)。
- 変更 `scripts/ve_components/model.py` — DocumentMetadata 拡張＋型付きセクションの dataclass 追加。
- 変更 `scripts/ve_components/validation.py` — document.type/profile、新 section kind の検証、構造不変条件、予約属性/クラス検査。
- 変更 `scripts/ve_components/checker.py` — 外部リンク方針の変更(href の https 許可＋ドメインマーカー検証)、`check_final_document` への検査群③接続。
- 変更 `scripts/ve_components/assembly.py` — narrative の外部リンク後処理(ドメインマーカー付与)。
- 変更 `scripts/build_explainer.py` — 新 section kind の dispatch と目次挿入。
- 変更 `scripts/check_component_html.py` — 変更なしの見込み(check_final_document 経由で③が効く)。
- 変更 `scripts/check.sh` — selftest ケース追加。
- 再生成 `examples/example-proposal.assembly.json` / `examples/example-proposal.html`、影響する `scripts/tests/*-doc.html` fixture。
- 改訂 `SKILL.md`、`references/patterns.md`、`references/assembly.schema.json`、`references/design-system.md`、リポジトリ `CLAUDE.md`。

---

### Task 1: DocumentMetadata の type / profile 拡張

**Files:**
- Modify: `scripts/ve_components/model.py:20-24`（DocumentMetadata）
- Modify: `scripts/ve_components/validation.py:167`（`_DOCUMENT_KEYS`）と `validation.py:1989-1997`（`_validate_document`）
- Test: `scripts/tests/test_document_metadata.py`（新規）

**Interfaces:**
- Produces: `DocumentMetadata(id, title, summary, type, profile)`。`type ∈ {"proposal","system","research"}`、`profile ∈ {"strict","extended"}`。後続タスク全てがこの 2 フィールドを参照する。

- [ ] **Step 1: 失敗するテストを書く**

```python
# scripts/tests/test_document_metadata.py
"""document.type / document.profile の検証テスト。"""
from __future__ import annotations

import unittest

from ve_components.diagnostics import ContractError
from ve_components.validation import validate_assembly

BASE = {
    "schemaVersion": 1,
    "document": {"id": "doc-1", "title": "タイトル", "summary": "要約。",
                 "type": "proposal", "profile": "strict"},
    "sections": [],  # Task 5 までは空 sections を許す前提で書く（Task 5 で必須構造テストに置き換える）
}


def _doc(**overrides) -> dict:
    raw = {**BASE, "document": {**BASE["document"], **overrides}}
    return raw


class DocumentMetadataTest(unittest.TestCase):
    def test_valid_type_and_profile_accepted(self) -> None:
        request = validate_assembly(_doc())
        self.assertEqual(request.document.type, "proposal")
        self.assertEqual(request.document.profile, "strict")

    def test_missing_type_rejected(self) -> None:
        raw = _doc()
        del raw["document"]["type"]
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("document.type" in str(d) for d in ctx.exception.diagnostics))

    def test_unknown_type_rejected(self) -> None:
        with self.assertRaises(ContractError):
            validate_assembly(_doc(type="poem"))

    def test_unknown_profile_rejected(self) -> None:
        with self.assertRaises(ContractError):
            validate_assembly(_doc(profile="rich"))
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_document_metadata.py -q`
Expected: FAIL（`document に不正なフィールド 'type'` 系の診断、または TypeError）

- [ ] **Step 3: 最小実装**

`model.py` の DocumentMetadata:

```python
@dataclass(frozen=True)
class DocumentMetadata:
    id: str
    title: str
    summary: str
    type: str
    profile: str
```

`validation.py`:

```python
_DOCUMENT_KEYS = {"id", "title", "summary", "type", "profile"}
_DOCUMENT_TYPES = frozenset({"proposal", "system", "research"})
_DOCUMENT_PROFILES = frozenset({"strict", "extended"})


def _validate_document(raw: object, path: str, col: DiagnosticCollector) -> DocumentMetadata | None:
    if not isinstance(raw, dict):
        col.add(MISSING_REQUIRED_SLOT, "document はオブジェクトである必要があります", path)
        return None
    _check_keys(raw, _DOCUMENT_KEYS, path, col)
    for slot in ("id", "title", "summary"):
        if not _nonblank_str(raw.get(slot)):
            col.add(MISSING_REQUIRED_SLOT, f"document.{slot} は空にできません", path)
    if raw.get("type") not in _DOCUMENT_TYPES:
        col.add(MISSING_REQUIRED_SLOT, "document.type は proposal / system / research のいずれかが必要です", path)
    if raw.get("profile") not in _DOCUMENT_PROFILES:
        col.add(MISSING_REQUIRED_SLOT, "document.profile は strict / extended のいずれかが必要です", path)
    return DocumentMetadata(id=raw.get("id", ""), title=raw.get("title", ""), summary=raw.get("summary", ""),
                            type=raw.get("type", ""), profile=raw.get("profile", ""))
```

- [ ] **Step 4: 既存テストの修復** — 既存 fixture / テストの `document` に `"type"` / `"profile"` を追加する（`scripts/tests/component-valid-*.json`・`component-bad-*.json`・各 `test_*.py` 内のインライン assembly。`grep -rl '"document"' tests/` で列挙し、一括で `"type": "system", "profile": "strict"` を既定として足す。proposal 見本系は `"type": "proposal"`）。

- [ ] **Step 5: 全テストがパスすることを確認**

Run: `python3 -m pytest tests -q`
Expected: PASS（578 件＋新 4 件）

- [ ] **Step 6: Commit**

```bash
git add -A skills/visual-explain/scripts
git commit -m "feat(ve): require document.type and document.profile in assembly IR"
```

---

### Task 2: 型付き first-screen セクション（summary 描画・タイトル正本の一本化）

**Files:**
- Modify: `scripts/ve_components/model.py`（FirstScreenSection 追加）
- Modify: `scripts/ve_components/validation.py`（`kind: "first-screen"` の検証）
- Create: `scripts/ve_components/document_sections.py`
- Modify: `scripts/build_explainer.py:60-77`（dispatch）
- Test: `scripts/tests/test_first_screen_section.py`（新規）

**Interfaces:**
- Consumes: `DocumentMetadata`（Task 1）。
- Produces: `FirstScreenSection(id, decision, conditions)`、`render_first_screen(section, document) -> WrappedDocumentSection`（`instance_id` / `markup` を持つ frozen dataclass。`compose_sections` にそのまま渡せる）。wrapper は `data-ve-section-kind="first-screen" data-ve-document-type="<type>" data-ve-profile="<profile>" id="<instance-id>"` を持つ。

- [ ] **Step 1: 失敗するテストを書く**

```python
# scripts/tests/test_first_screen_section.py
"""型付き first-screen: h1 は document.title 由来、subtitle は型で切替。"""
from __future__ import annotations

import unittest

from ve_components.diagnostics import ContractError
from ve_components.document_sections import render_first_screen
from ve_components.model import DocumentMetadata, FirstScreenSection

DOC = DocumentMetadata(id="doc-1", title="料金改定は限定対象で段階公開する", summary="要約文。",
                       type="proposal", profile="strict")


class FirstScreenRenderTest(unittest.TestCase):
    def test_h1_comes_from_document_title(self) -> None:
        section = FirstScreenSection(id="sec-first", decision="限定対象で開始するか決めます。",
                                     conditions=("撤回条件を先に合意できること",))
        wrapped = render_first_screen(section, DOC)
        self.assertIn("<h1>料金改定は限定対象で段階公開する</h1>", wrapped.markup)
        self.assertIn("data-ve-document-type=\"proposal\"", wrapped.markup)
        self.assertIn("data-ve-profile=\"strict\"", wrapped.markup)
        self.assertIn("要約文。", wrapped.markup)  # summary が描画される
        self.assertIn("あなたが決めること", wrapped.markup)

    def test_system_uses_question_subtitle(self) -> None:
        doc = DocumentMetadata(id="d", title="T", summary="S。", type="system", profile="strict")
        section = FirstScreenSection(id="sec-first", decision="この仕組みはなぜ安全か。", conditions=())
        wrapped = render_first_screen(section, doc)
        self.assertIn("この資料が答える問い", wrapped.markup)
        self.assertNotIn("あなたが決めること", wrapped.markup)

    def test_more_than_two_conditions_rejected_by_validation(self) -> None:
        from ve_components.validation import validate_assembly
        raw = {"schemaVersion": 1,
               "document": {"id": "d", "title": "T", "summary": "S。", "type": "proposal", "profile": "strict"},
               "sections": [{"kind": "first-screen", "id": "sec-first",
                             "decision": "決めます。", "conditions": ["a", "b", "c"]}]}
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertTrue(any("conditions" in str(d) for d in ctx.exception.diagnostics))
```

- [ ] **Step 2: 失敗を確認** — Run: `python3 -m pytest tests/test_first_screen_section.py -q` / Expected: FAIL（ImportError）

- [ ] **Step 3: 実装**

`model.py` に追加:

```python
@dataclass(frozen=True)
class FirstScreenSection:
    id: str
    decision: str          # proposal: 判断文 / system・research: この資料が答える問い（1 文）
    conditions: tuple[str, ...] = ()   # 最大 2 件
```

`document_sections.py`（新規・冒頭）:

```python
"""Typed document sections: first-screen, closing, ask, and the build-time TOC.

These are trusted renderers that bypass the component registry: their inputs are
validated dataclasses, their markup uses only fixed skeleton classes, and the
final checker (group 3) re-verifies the result in the flattened document.
"""
from __future__ import annotations

import html
from dataclasses import dataclass

from .model import DocumentMetadata, FirstScreenSection

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
```

`validation.py` の `_validate_section` に分岐追加（`kind == "first-screen"`）: 許可キー `{"kind","id","decision","conditions"}`、`id`・`decision` は非空文字列、`decision` は 1 文（`。！？!?` がちょうど 1 個で末尾）、`conditions` は文字列配列で最大 2 件。ID 重複検査は narrative と同じ。

`build_explainer.py` の dispatch に追加:

```python
        elif isinstance(section, FirstScreenSection):
            items.append(render_first_screen(section, request.document))
```

- [ ] **Step 4: パス確認** — Run: `python3 -m pytest tests/test_first_screen_section.py tests/test_document_metadata.py -q` / Expected: PASS

- [ ] **Step 5: Commit** — `git commit -m "feat(ve): add typed first-screen section deriving h1 and title from document.title"`

---

### Task 3: 型付き closing セクション（型別必須節）

**Files:**
- Modify: `scripts/ve_components/model.py` / `scripts/ve_components/validation.py` / `scripts/ve_components/document_sections.py` / `scripts/build_explainer.py`
- Test: `scripts/tests/test_closing_section.py`（新規）

**Interfaces:**
- Produces: `ClosingSection(id, blocks)`。`blocks: tuple[ClosingBlock, ...]`、`ClosingBlock(heading, items: tuple[str, ...])`。型別の必須見出し: proposal は「リスクと弱い前提」と「不確かな点」、system は「限界・確度」、research は「限界・反証・確度」。必須見出しの欠落・items 空配列は validation が拒否する。
- Produces: wrapper は `data-ve-section-kind="closing" id="<instance-id>"`、内部は `<section class="closing-section" aria-label="判断材料">` に `<h2>` 見出し＋ `<ul>`。

- [ ] **Step 1: 失敗するテスト**（要点のみ抜粋 — 実ファイルには 4 ケース書く: 必須見出し欠落 FAIL / items 空 FAIL / 正常 markup に h2 見出しが出る / research 型の必須見出し）

```python
def test_proposal_requires_both_closing_headings(self) -> None:
    raw = _assembly(type="proposal", closing_blocks=[{"heading": "リスクと弱い前提", "items": ["前提Aが弱い"]}])
    with self.assertRaises(ContractError) as ctx:
        validate_assembly(raw)
    self.assertTrue(any("不確かな点" in str(d) for d in ctx.exception.diagnostics))
```

- [ ] **Step 2: 失敗確認** → **Step 3: 実装**（`_CLOSING_REQUIRED = {"proposal": ("リスクと弱い前提", "不確かな点"), "system": ("限界・確度",), "research": ("限界・反証・確度",)}` を validation に置き、document.type を参照して検査。`render_closing` は h2 と ul を escape 付きで生成）→ **Step 4: パス確認** → **Step 5: Commit** — `feat(ve): add typed closing section with per-document-type required blocks`

---

### Task 4: 型付き ask セクション（askType union・静的表示のみ）

**Files:**
- Modify: `scripts/ve_components/model.py` / `scripts/ve_components/validation.py` / `scripts/ve_components/document_sections.py` / `scripts/build_explainer.py`
- Test: `scripts/tests/test_ask_section.py`（新規）

**Interfaces:**
- Produces: `AskSection(id, ask_type, question, options, default_id, no_default_reason, steps, claim, verify)` — `ask_type ∈ {"decision","request","hypothesis"}` の discriminated union。decision は `question` + `options: tuple[AskOption, ...]`（`AskOption(id, label, tradeoff)`）+ `default_id`（任意・`no_default_reason` と排他）。request は `steps`、hypothesis は `claim` + `verify`。
- 出力 markup は**既存 checker の ask 契約**（`checker.py:196` `_ASK_KINDS` と `_AskInspector` の規則群、skeleton の `.ask` / `.ask-kind` / `.ask-question` / `.ask-options` / `[data-ask-option]` / `[data-ask-default]` / `.ask-tradeoff` / `.ask-steps` / `[data-ask-role]` クラス契約）を満たすこと。既存の合格 fixture（`scripts/tests/valid-proposal.html` 内 `.ask` ブロック）を出力の規範とし、`test_ask_blocks.py` の検査を新レンダラ出力にも通す。
- decision の wrapper は `data-ve-section-kind="ask" data-ve-ask-type="decision" id="<instance-id>"`（Phase 2 の回収 JS がこの data 属性を読む。**Phase 1 では JS を書かない**）。

- [ ] **Step 1: 失敗するテスト**（decision 正常系 / default_id が options に無い FAIL / no_default_reason と default_id の併記 FAIL / request・hypothesis の静的出力 / 出力が `_AskInspector` 検査に合格）
- [ ] **Step 2: 失敗確認** → **Step 3: 実装** → **Step 4: パス確認**（`python3 -m pytest tests/test_ask_section.py tests/test_ask_blocks.py -q`）→ **Step 5: Commit** — `feat(ve): add typed ask section as discriminated union over decision/request/hypothesis`

---

### Task 5: 構造不変条件（位置・個数・h1/予約属性の禁止）

**Files:**
- Modify: `scripts/ve_components/validation.py`（`validate_assembly` の sections ループ後に構造検査を追加。`_validate_narrative_section` に markup 内容検査を追加）
- Modify: `scripts/ve_components/checker.py`（`validate_content_markup` に h1 / 予約 class / 予約 data 属性の拒否を追加）
- Test: `scripts/tests/test_document_structure.py`（新規）

**Interfaces:**
- Produces: 検査規則 —
  1. first-screen はちょうど 1 個で sections[0]。
  2. closing はちょうど 1 個で最後（compatibility / canonical / narrative / ask より後ろに置けない）。
  3. narrative / compatibility の markup に `<h1>`・`<title>` を置けない（h1 は first-screen 専有）。
  4. narrative の markup に予約 class（`first-screen`, `closing-section`, `ask`, `link-domain`）と予約 data 属性（Global Constraints の一覧）を置けない。compatibility 節は従来どおり許可（legacy 図の機構）。
- 診断文言例: `"first-screen は先頭にちょうど1個必要です"` / `"closing は最後にちょうど1個必要です"` / `"narrative に <h1> は置けません（h1 は first-screen 専有）"` / `"narrative に予約属性 data-connect は置けません"`。

- [ ] **Step 1: 失敗するテスト**（first-screen なし / 2 個 / 先頭以外・closing なし / closing の後に narrative・narrative 内 h1・narrative 内 data-ask、の 7 ケース）
- [ ] **Step 2: 失敗確認** → **Step 3: 実装** → **Step 4: 既存テスト修復**（既存インライン assembly に first-screen / closing を足すか、構造検査を通る形へ移行。旧 `valid-*.html` 系 fixture は Task 8-9 で扱う）→ **Step 5: 全テストパス確認** → **Step 6: Commit** — `feat(ve): enforce document structure invariants and reserved attribute bans`

---

### Task 6: 自動目次（ビルド時生成）

**Files:**
- Modify: `scripts/ve_components/document_sections.py`（`build_toc` 追加）
- Modify: `scripts/build_explainer.py`（compose 前に目次 item を挿入）
- Test: `scripts/tests/test_toc_generation.py`（新規）

**Interfaces:**
- Produces: `build_toc(entries: tuple[TocEntry, ...]) -> WrappedDocumentSection | None`。`TocEntry(anchor_id, heading)`。
- 発火条件: 見出しを持つ本文セクション（narrative の最初の h2/h3、closing。first-screen と目次自身は含まない）が **5 個以上**。未満なら `None`（目次なし）。
- 挿入位置: first-screen の直後。anchor は各セクション wrapper の `id`（= instance id）。目次が発火する文書では narrative wrapper にも `id="<instance-id>"` を付与する（発火しない文書の narrative wrapper は現状維持 = 既存 fixture 非破壊）。
- markup: `<section data-ve-section-kind="toc"><nav aria-label="目次"><ol><li><a href="#sec-x">見出し</a></li>…</ol></nav></section>`。narrative の見出し抽出は `HTMLParser` で最初の h2/h3 のテキストを取る（checker.py の `ContentInspector.headings` と同じ方式）。

- [ ] **Step 1: 失敗するテスト**（4 セクション→None / 5 セクション→目次あり・アンカーが instance id を指す / narrative wrapper に id が付く / 見出しなし narrative は entries に入らない）
- [ ] **Step 2: 失敗確認** → **Step 3: 実装** → **Step 4: パス確認** → **Step 5: Commit** — `feat(ve): generate build-time table of contents for long documents`

---

### Task 7: 外部出典リンクの解放（閉じた scheme 許可＋レンダラ生成ドメインマーカー）

**Files:**
- Modify: `scripts/ve_components/checker.py:157-172`（`_ContentSafetyParser._check` の href 方針）
- Modify: `scripts/ve_components/assembly.py:207-215`（`process_narrative_section` に外部リンク後処理を追加）
- Test: `scripts/tests/test_external_links.py`（新規）

**Interfaces:**
- 新方針（narrative / typed セクション。compatibility は現行規則を維持）:
  - `href`: `https:` 絶対 URL と `#` アンカーのみ許可。`javascript:` / `data:` / `file:` / `//` / 相対 URL / `http:` は拒否（診断: `"外部リンクは https の絶対 URL か # アンカーだけ使えます: <値>"`）。
  - `src`: 従来どおり全外部参照拒否（変更なし）。
- ドメインマーカー: `process_narrative_section` が markup を後処理し、外部 `<a>` の内側末尾に `<span class="link-domain">‹<hostname>›</span>` を**挿入**する。モデル入力に `link-domain` class があれば拒否（Task 5 の予約 class）。hostname は `urllib.parse.urlsplit(href).hostname` から取り、IDN はそのまま表示する。
- `check_final_document`（検査群③・Task 8）が最終文書で「外部 `<a>` はすべて正しい hostname のマーカーを持つ」ことを再検証する。

- [ ] **Step 1: 失敗するテスト**（https リンクがビルドを通る / マーカーが hostname 付きで挿入される / `http:` 拒否 / 相対 URL 拒否 / `javascript:` 拒否 / モデルが偽マーカーを書いたら拒否）
- [ ] **Step 2: 失敗確認** → **Step 3: 実装** → **Step 4: 既存テスト修復**（`component-bad-*` の外部リンク系 fixture の期待診断を新文言へ更新。`bad-external-url.html` は src なので不変）→ **Step 5: パス確認** → **Step 6: Commit** — `feat(ve): allow https source links with renderer-generated domain markers`

---

### Task 8: 検査群③ — 最終文書の構造検査（check.sh 単体経路）

**Files:**
- Create: `scripts/ve_components/document_checks.py`
- Modify: `scripts/ve_components/checker.py`（`check_final_document` から呼ぶ）
- Modify: `scripts/check.sh`（selftest ケース追加）
- Create: `scripts/tests/structure-bad-no-first-screen.html` ほか bad fixture 群（次の Step 1 参照）
- Test: `scripts/tests/test_document_checks.py`（新規）

**Interfaces:**
- Produces: `check_document_structure(content_markup: str) -> list[Diagnostic]`。first-screen wrapper の `data-ve-document-type` / `data-ve-profile` を読み、次を検査する:
  1. type / profile 表明の存在と語彙（`"文書型の自己表明がありません"` など）。
  2. 型別必須節見出しの存在（Task 3 の `_CLOSING_REQUIRED` と同じ表を使う）。
  3. `<h1>` がちょうど 1 個で first-screen 内、`<title>` テキストと完全一致。
  4. summary の描画（first-screen 内に `document.summary` 相当のテキストブロックがあること — first-screen wrapper の構造で判定）。
  5. 外部 `<a>` の hostname マーカー整合（Task 7）。
  6. profile=strict の文書に extended 限定要素（Phase 3 で追加予定の freeform / image。Phase 1 では該当なし＝表明の検証のみ）が無いこと。
- `check_final_document` は `is_component_document` が真の文書で③を必ず実行する。**pre-migration legacy 文書（マーカーなし）は従来どおり素通し**（legacy 経路の検査は check.sh 埋め込み checker が担当し続ける）。

- [ ] **Step 1: bad fixture を作る** — 2026-07-16 の検証で PASS してしまった「すり抜け資料」を再現する fixture を IR からビルドできなくなるため、**旧ビルド出力を模した静的 HTML** として保存する: `structure-bad-no-first-screen.html`（第一画面なし）、`structure-bad-duplicate-h1.html`（h1 2 個）、`structure-bad-title-mismatch.html`（`<title>` ≠ h1）、`structure-bad-no-closing.html`（末尾節なし）。作り方: Task 9 の新見本をビルドした後、該当部分を意図的に壊した複製を保存する（fixture ヘッダコメントに破壊内容を記す）。
- [ ] **Step 2: 失敗するテストを書く**（各 bad fixture が期待診断を出す / 新見本 example-proposal.html が③を無診断で通る）
- [ ] **Step 3: 失敗確認** → **Step 4: 実装** → **Step 5: check.sh selftest にケース追加**（`structure-bad-*` 4 件を期待診断つきで登録）→ **Step 6: パス確認**（`python3 -m pytest tests -q` と `bash check.sh --selftest`）→ **Step 7: Commit** — `feat(ve): add final-document structure checks (group 3) closing the canonical bypass`

---

### Task 9: 破壊的移行 — 見本・fixture・ドキュメントの一括改訂

**Files:**
- Modify: `examples/example-proposal.assembly.json`（first-screen / closing / ask を型付きへ移行。h1 重複は h2 化で解消）→ 再ビルドで `examples/example-proposal.html` を更新
- Modify: 影響する `scripts/tests/*-doc.html`・`valid-*.html` fixture（構造検査に通る形へ再生成。`scripts/tests/tools/resplice.py` を利用）
- Modify: `SKILL.md`（ワークフロー 5・6 手順、canonical 節、保存規約の前後に type/profile と型付きセクションの記述を追加。「narrative に first-screen を書く」旧記述を削除）
- Modify: `references/patterns.md`（資料型テンプレートを型付き IR の JSON 例で書き直す）
- Modify: `references/assembly.schema.json`（document.type/profile、新 section kind を追加）
- Modify: `references/design-system.md`（目次・ドメインマーカーの目視規範を追記)
- Modify: リポジトリ `CLAUDE.md`（アーキテクチャ節に型付きセクションと検査群③を反映）
- Test: 既存全テスト＋ `test_visual_explain_fixtures.py`

- [ ] **Step 1: example-proposal.assembly.json を型付きへ移行**（sections[0] を `kind: "first-screen"` に、末尾 2 節を `kind: "closing"` に、`.ask` 相当を `kind: "ask"` に）
- [ ] **Step 2: 再ビルドして差分を目視**（`python3 scripts/build_explainer.py --assembly examples/example-proposal.assembly.json --output examples/example-proposal.html` → `bash scripts/check.sh examples/example-proposal.html` が PASS）
- [ ] **Step 3: fixture 再生成と全テスト修復** — Run: `python3 -m pytest tests -q` / Expected: PASS
- [ ] **Step 4: ドキュメント改訂**（上記 5 文書。旧方式の記述が残っていないことを `grep -rn "first-screen" SKILL.md references/` で確認）
- [ ] **Step 5: Commit**（分割可: `docs(ve): migrate example and fixtures to typed sections` ＋ `docs(ve): update skill docs for typed IR and structure checks`）

---

### Task 10: 全体検証（Phase 1 完了ゲート）

- [ ] **Step 1: 全テスト** — Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q` / Expected: 全件 PASS
- [ ] **Step 2: selftest** — Run: `bash skills/visual-explain/scripts/check.sh --selftest` / Expected: `selftest: N passed, 0 failed`
- [ ] **Step 3: すり抜け再現テスト** — 2026-07-16 の「構造なし資料」IR（first-screen なし・closing なし・h1 2 個・title 不一致）をビルドし、**IR 段階で拒否される**ことを確認。旧ビルド出力を模した静的 HTML が `check.sh` で **FAIL** することを確認。
- [ ] **Step 4: 外部リンク実証** — 調査報告型の最小 IR に出典リンクを入れてビルドし、PASS＋ドメインマーカー描画を目視確認。
- [ ] **Step 5: skeleton 不変の確認** — Run: `git diff --stat main -- skills/visual-explain/assets/skeleton.html` / Expected: 差分なし
- [ ] **Step 6: Commit / PR** — draft PR を作成し、レビューへ回す。

---

## Self-Review 済みメモ

- spec の Phase 1 項目（IR 拡張・検査群③・外部リンク・summary 描画・目次・破壊的移行・既知 3 欠陥の消滅）は Task 1-10 で全て対応する。ask の回収 UI・JS・localStorage・freeform・image・code・CSP は Phase 2 / 3 であり、この計画に**含めない**。
- 診断文言は例示であり、実装時に既存文言のトーン（です・ます調の指示形）へ揃えること。文言を変えたら selftest / テスト期待値も同時に更新する。
- `WrappedDocumentSection` は `compose_sections` のダックタイプ契約（`instance_id` / `markup`）を満たすため、`assembly.py` の isinstance 分岐（RenderedCanonical / WrappedCompatibility / WrappedNarrative の集計）には追加不要。ただし集計タプルに載らないことが問題ないかは Task 2 実装時に `CompositionResult` の利用箇所（`checker.check_final_document` の `expected`）を確認し、必要なら `document_sections` 用の集計フィールドを追加する。
