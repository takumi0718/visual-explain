# 判断資料 v3 Phase 2（判断回収）実装計画

> **For agentic workers:** この計画はタスク単位で実装する。各タスクは TDD（失敗するテスト→最小実装→パス→コミット）で進め、チェックボックス（`- [ ]`）で進捗を管理する。正本 spec: `docs/superpowers/specs/2026-07-16-decision-document-v3-design.md`。計画と spec が矛盾したら実装せず報告する（ただし本計画の「spec 逸脱」節に記録済みの Playwright 廃止は人間承認済みの意図的逸脱であり、矛盾報告の対象外）。

## Goal

ask（decision）の選択 UI・末尾回収パネル・skeleton 固定 JS（判断回収エンジン）・localStorage 永続化を実装し、「読む→決める→返す」ループを単一 HTML で閉じる。あわせて Phase 1 残課題の T07 エッジケース 2 件（CR/LF 改行位置誤計算・xlink:href 名前空間非対称)を解消する。

## Architecture

回収エンジンは 2 層に分ける。**純関数コア**（`scripts/tests/runtime/decision_engine.js` が正本。選択・メモ・復元判定・コピー整形・storage キー計算。DOM 非依存で Node 標準だけで実行可能）と、**DOM バインダ**（skeleton の固定 JS。テーマトグル・ステッパーと同格の信頼済み領域。選択ボタン・メモ欄・コピー導線を progressive enhancement として注入する）。コアは skeleton にマーカーコメント間へ**逐語埋め込み**し、正本ファイルとのバイト一致を pytest が固定する。

ask レンダラは選択肢（`data-ask-option-id`）とメモ欄（`data-ask-memo` つき textarea）を data 属性つきの**静的 HTML** として出力し（spec 109 行目。モデルは JS を書かない）、build 時に `render_decision_panel` が closing の**後**に回収パネルを生成する。パネルは `document.id` / `schemaVersion` / ask 契約ダイジェスト（ビルド時に Python で計算した SHA-256）/ 生成先ファイルパス（`--output` 引数の逐語。コピー出力の `<ファイルパス>` の正本）を data 属性で自己表明し、検査群③が DOM からダイジェストを再計算して照合する（偽装注入・改竄の防止）。localStorage キーは `ve-decision:<document.id>:<schemaVersion>:<digest>` で、選択肢を変更した再生成文書では digest が変わるため古い選択は物理的に復元されない。JS 無効時は ask が既定案つき静的表示、パネルが要約表示として成立する（無操作の不変条件）。

**IR / assembly schema は変更しない**（ask の型定義は Phase 1 で完成済み。Phase 2 はレンダラ・skeleton・検査の変更のみ）。

## Tech Stack

Python 3 標準ライブラリのみ（実装・検査とも）。テストは pytest（開発時専用）＋ 回収エンジン純関数の検証に **node 標準**（開発時専用・npm パッケージなし・pytest から `subprocess.run` で駆動）。ブラウザ自動化フレームワークは導入しない（下記「spec 逸脱」）。

## spec 逸脱（人間承認済み・2026-07-17 記録）: Playwright 廃止

spec 144 行目は「判断回収 JS は実ブラウザでの自動受入テスト（Playwright・開発時専用依存）を Phase 2 の完了条件とする」と定めるが、**Playwright は採用しない**。

- 採用しない理由: 開発時依存の追加はリポ規約「外部依存ゼロ」を破る / 利用者は 1 名のみ / MCP 関係は使用しない方向性。
- 代替方針（本計画での実装先）:
  1. 回収 JS のロジック（コピー出力の構造化・localStorage 復元判定・ダイジェスト鍵計算・選択肢→選択の写像）を**純関数化**し、node 標準のみで実行できる `scripts/tests/runtime/decision_engine.js` を作る。pytest から `subprocess.run` で呼び出して検証する（→ Task 4）。
  2. 既存 `check.sh`（legacy checker）による JS 構文・データ属性整合・固定領域ハッシュの最終検査は維持する（→ Task 5, 6）。
  3. **手動ブラウザ QA**（spec の検証シナリオ 7 項目、file:// と http:// の両方）を Phase 2 完了ゲートに組み込む。QA 記録は `.runs/decision-doc-v3-p2/qa/` に保存する（→ Task 8, 9）。
  4. スキル利用時のゼロ依存不変（Playwright / npm install / pip install をしない）を `CLAUDE.md` 改訂で明文化する（→ Task 7）。
- 影響: Phase 2 完了ゲートのうち「実ブラウザでの自動受入テスト」が「純関数の機械検証＋手動 QA 7 シナリオ」に置換される。

## テスト戦略（spec 検証シナリオ 7 項目の充足マップ)

| spec シナリオ | 機械検証（Playwright 代替） | 手動 QA（Task 8） |
| --- | --- | --- |
| ① 複数 ask の選択・変更・再読み込み後の復元 | 純関数 `selectOption` / `restoreState` / `serializeState` のラウンドトリップ（Task 4） | file:// と http:// で再読み込み復元を実施 |
| ② キーボード操作とフォーカス順 | バインダは `button` / `textarea` の標準フォーカス可能要素のみ使い、選択ボタンの可視テキストに選択肢ラベルを含めて accessible name を一意化し `aria-pressed` を管理する設計（Task 5） | Tab 順・Enter/Space 操作・ボタン名の読み分けを実施 |
| ③ クリップボード成功／拒否時の手動コピー縮退 | バインダの try/catch 縮退経路をコードで固定（Task 5） | 許可時と拒否時（権限ブロック）の両方を実施 |
| ④ localStorage 例外時の縮退 | `restoreState` は不正入力で空状態を返す（Task 4）。バインダは storage 例外で永続化のみ喪失（Task 5） | Firefox `dom.storage.enabled=false` で例外を確実に再現して実施（手順は Task 8 Step 1） |
| ⑤ JS 無効時の静的表示 | レンダラの静的 markup を pytest で固定（Task 2, 3） | JS 無効ブラウザで表示確認 |
| ⑥ 日本語・改行・長文メモのコピー結果の完全性 | `formatCopyText` のテストベクタ（日本語・CR/LF・長文）（Task 4） | 実ブラウザでコピー→ペースト照合 |
| ⑦ 選択肢を変更した再生成文書で古い選択を復元しない | digest によるキー分離＋ `restoreState` の未知 option 破棄（Task 4）、digest 整合の検査群③（Task 6） | 選択肢を変えて再生成した資料で実施 |

file:// と http:// の実行環境差（localStorage / Clipboard API）は手動 QA が両プロトコルで全シナリオを実施することで担保する（http:// は `python3 -m http.server`＝標準ライブラリ・開発時のみ）。

## Global Constraints

- `assets/skeleton.html` の変更は **Task 5 のみ**で行う。変更は CSS 追加ブロックと固定 JS 追加ブロック（DECISION ENGINE CORE ＋ DECISION COLLECTION）に限り、既存の固定 JS（テーマ初期化・テーマトグル・コネクタ・ステッパー）と既存 CSS 行は 1 バイトも変更しない。skeleton 変更後は全 HTML fixture を `scripts/tests/tools/resplice.py` で一括再生成し、KEEP_AS_IS の 6 fixture へは同一編集をテキスト置換で適用する（resplice.py docstring の規約）。
- Playwright / Selenium / Puppeteer / jsdom / 外部テストツール・npm パッケージ・pip パッケージの追加は禁止。JS テストは node 標準のみ（node は開発時専用。スキル利用時のゼロ依存は不変）。
- 診断メッセージは日本語。既存テストは診断文字列の完全一致で検証するため、既存文言の変更は対応するテスト・selftest 期待値の更新を伴う。
- テストは必ず `skills/visual-explain/scripts/` から `python3 -m pytest tests -q` で実行する（`ve_components` を cwd 経由で import するため）。
- コミットは conventional commits ＋ `(ve)` スコープ（例: `feat(ve): ...`）。1 タスク 1 コミット以上。ファイル変更とコミットを必ず対応させる。
- 予約 data 属性（`data-ve-*`, `data-connect`, `data-connect-scope`, `data-stepper`, `data-step`, `data-step-action`, `data-ask`, `data-ask-*`, `data-theme`, `data-theme-*`, `data-lane`, `data-tone`）は Phase 1 と同一の一覧を維持する。Phase 2 で新設する `data-ask-option-id` / `data-ask-selected` / `data-ask-select` / `data-ve-panel-*` / `data-ve-ask-digest` 等はすべて既存の予約プレフィックス（`data-ask-*` / `data-ve-*`）に収まるため一覧の追加は不要。予約 class には `decision-panel` を追加する（narrative / compatibility の markup で禁止）。
- IR / `references/assembly.schema.json` は変更しない。ask の IR 契約（Phase 1 Task 4）をそのまま使う。
- YAGNI: Phase 3（code / image / freeform / CSP 改定・SVG 許可リスト拡張）の先取り実装をしない。spec が「v1 では実装しない」と明記した項目（シンタックスカラー、code 部品の自動レイアウト等)を持ち込まない。
- 後方互換は切る（spec の決定）: 旧 fixture・旧 markup の救済コードを書かない。ask 契約の拡張（option-id 必須化）は既存 fixture の更新で対応する。

## ファイル構成（新規/変更の全体地図）

- 新規 `scripts/tests/runtime/decision_engine.js` — 回収エンジン純関数コアの**正本**（storage キー・選択写像・復元判定・コピー整形。DOM 非依存、Node/ブラウザ両用）。
- 新規 `scripts/tests/runtime/decision_engine_driver.js` — Node 実行ドライバ（stdin の JSON 呼び出し列を実行し JSON を返す）。
- 新規 `scripts/tests/test_decision_engine_js.py` — pytest → `subprocess.run(["node", driver])` の検証ハーネス。
- 変更 `assets/skeleton.html` — ask 選択 UI / 回収パネルの CSS 追加＋固定 JS 追加（コア逐語埋め込み＋ DOM バインダ）。**Task 5 のみ**。
- 変更 `scripts/ve_components/document_sections.py` — `render_ask` への `data-ask-option-id` 付与、`compute_ask_digest`、`render_decision_panel` 新設、instance id 割当の一般化。
- 変更 `scripts/ve_components/checker.py` — ask 契約検査の拡張（option-id 必須・一意）、T07 の xlink:href 非対称解消。
- 変更 `scripts/ve_components/assembly.py` — T07 の CR/LF 位置計算修正。
- 変更 `scripts/ve_components/document_checks.py` — 検査群③拡張（パネル存在・位置・digest 整合）。
- 変更 `scripts/ve_components/validation.py` — 予約 class へ `decision-panel` 追加。
- 変更 `scripts/build_explainer.py` — 回収パネルの挿入（closing の後）。
- 変更 `scripts/check.sh` — selftest ケース追加（パネル系 structure-bad）。
- 変更 `scripts/tests/test_skeleton_audit.py` — コア逐語埋め込みの一致検査・意味色/spacing 監査の追随。
- 新規 `scripts/tests/structure-bad-panel-missing.html` / `structure-bad-panel-digest.html` — 検査群③の bad fixture。
- 再生成 `scripts/tests/*.html` fixture 一式（resplice）、`examples/example-proposal.assembly.json` / `examples/example-proposal.html`。
- 改訂 `SKILL.md` / `references/design-system.md` / `references/patterns.md` / `scripts/tests/fixtures.md` / リポジトリ `CLAUDE.md`（ゼロ依存明文化を含む）。
- 新規（リポ管理外の運用記録）`.runs/decision-doc-v3-p2/qa/` — 手動 QA 記録の置き場。Phase 2 で追加する検証アーティファクトはすべてここに置く（Phase 1 の `.runs/decision-doc-v3-p1/` は保持し、変更しない）。

---

### Task 1: T07 エッジケース修正（CR/LF 位置計算・xlink:href 名前空間非対称）

Phase 1 残課題 2 件（`T07-remaining-issues.md`）を独立タスクとして先頭でクローズする。

**Files:**
- Modify: `scripts/ve_components/assembly.py:207-212`（`_linecol_to_index`）
- Modify: `scripts/ve_components/checker.py:192-223`（`_ContentSafetyParser._check_href` / `_check`）
- Test: `scripts/tests/test_external_links.py`（既存へケース追加）

**Interfaces:**
- Consumes: `HTMLParser.getpos()`（lineno は `\n` のみで数える CPython 実装）。
- Produces: `_linecol_to_index(text, lineno, col)` は `\n` のみを行区切りとして数える（`splitlines` の CR 分割と非対称にならない）。`_ContentSafetyParser` は名前空間つき href（属性名に `:` を含む `xlink:href` 等）に対し、https_or_anchor 方針では `#` アンカーのみ許可し外部 URL を拒否する（マーカー挿入が属性名 `href` しか拾わない非対称を、検査側を狭めて解消する）。compatibility（legacy_no_external）は従来どおり。
- 新診断文言: `"名前空間つき href では外部リンクを使えません: <値>"`。

- [ ] **Step 1: 失敗するテストを書く**（`test_external_links.py` に追加）

```python
class T07EdgeCaseTest(unittest.TestCase):
    def test_lone_cr_before_lf_does_not_shift_marker(self) -> None:
        # HTMLParser は \n だけを行として数えるが、splitlines は \r も分割する。
        # 単独 CR を含む markup でマーカーが </a> の直前に入ることを固定する。
        from ve_components.assembly import insert_link_domain_markers
        markup = '<p>\rfoo\n<a href="https://example.com">x</a></p>'
        result = insert_link_domain_markers(markup)
        self.assertEqual(
            result,
            '<p>\rfoo\n<a href="https://example.com">x'
            '<span class="link-domain">‹example.com›</span></a></p>',
        )

    def test_namespaced_external_href_rejected_in_narrative(self) -> None:
        from ve_components.checker import validate_content_markup
        markup = '<svg viewBox="0 0 10 10"><a xlink:href="https://example.com">x</a></svg>'
        diags = validate_content_markup(markup, section_kind="narrative")
        self.assertTrue(any("名前空間つき href では外部リンクを使えません" in d.message for d in diags))

    def test_namespaced_anchor_href_still_allowed(self) -> None:
        from ve_components.checker import validate_content_markup
        markup = '<svg viewBox="0 0 10 10"><a xlink:href="#sec-a">x</a></svg>'
        diags = validate_content_markup(markup, section_kind="narrative")
        self.assertFalse(any("名前空間つき" in d.message for d in diags))
```

- [ ] **Step 2: 失敗を確認** — Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_external_links.py -q` / Expected: FAIL（1 件目は壊れた挿入位置、2 件目は診断なし）

- [ ] **Step 3: 最小実装**

`assembly.py` の `_linecol_to_index` を `\n` 基準へ:

```python
def _linecol_to_index(text: str, lineno: int, col: int) -> int:
    """Convert 1-based lineno + 0-based col (HTMLParser.getpos) to a string index.

    HTMLParser counts lines by "\n" only; splitting on universal newlines
    (splitlines) would also break on lone "\r" and desynchronize offsets.
    """
    offset = 0
    for _ in range(lineno - 1):
        offset = text.index("\n", offset) + 1
    return offset + col
```

`checker.py` の `_check`: `local in {"href", "src"}` の分岐で、`href` かつ属性名に `:` を含む場合は新メソッドへ:

```python
            if local in {"href", "src"} and value is not None:
                v = value.strip()
                if local == "src":
                    self._check_src(v)
                elif ":" in name:
                    self._check_namespaced_href(v)
                else:
                    self._check_href(v)
```

```python
    def _check_namespaced_href(self, v: str) -> None:
        if self.href_policy == "legacy_no_external":
            self._check_href(v)  # compatibility は従来規則のまま（外部は既に拒否）
            return
        if v.startswith("#"):
            return
        self.diagnostics.append(Diagnostic(
            FORBIDDEN_CONTENT_MARKUP, f"名前空間つき href では外部リンクを使えません: {v}"))
```

- [ ] **Step 4: 既存テスト・fixture の回帰確認** — Run: `python3 -m pytest tests -q` と `bash check.sh --selftest`。`bad-svg-xlink-javascript.html`（legacy 経路）と `component-bad-svg-xlink-attr.html`（component 経路）の期待診断は不変のはず。変わった場合は原因を特定して報告（無断で期待値を書き換えない）。
- [ ] **Step 5: Commit**

```bash
git add -A skills/visual-explain/scripts
git commit -m "fix(ve): close T07 edge cases in link marker insertion and namespaced href policy"
```

**done_criteria:** 新 3 テストを含む全テスト PASS。selftest PASS（既存期待値不変）。T07-remaining-issues.md の再現例（単独 CR 入り markup / `xlink:href` 外部リンク）がそれぞれ「正しい位置に挿入」「ビルド拒否」になる。

---

### Task 2: ask decision レンダラの回収対応（data-ask-option-id）と契約ダイジェスト

**Files:**
- Modify: `scripts/ve_components/document_sections.py`（`_render_decision_body`、`compute_ask_digest` / `compute_ask_digest_from_pairs` 新設）
- Modify: `scripts/ve_components/checker.py`（`_AskParser` / `validate_ask_blocks` に option-id 契約を追加）
- Test: `scripts/tests/test_ask_section.py`・`scripts/tests/test_ask_blocks.py`（既存へケース追加）

**Interfaces:**
- Produces: decision の各選択肢 `<li data-ask-option data-ask-option-id="<opt.id>">`（既定案は従来どおり `data-ask-default` を併記）。DOM バインダ（Task 5）と検査群③（Task 6）はこの属性から選択肢 ID を読む。
- Produces: decision のメモ欄を**静的 markup として出力**する（spec 109 行目「選択肢・メモ欄を data 属性つきの静的 HTML として出力」。r1 C1）: options の `</ul>` の後に `<div class="ask-memo"><label>メモ（この判断について）<textarea data-ask-memo></textarea></label></div>`。JS 無効時にもメモ欄自体は存在し、保存・パネル同期・コピーへの反映だけが固定 JS（Task 5）の担当になる。
- Produces: `compute_ask_digest_from_pairs(pairs: tuple[tuple[str, tuple[str, ...]], ...]) -> str` — pairs を `json.dumps([[ask_id, [opt, ...]], ...], ensure_ascii=False, separators=(",", ":"))` で **JSON canonical 直列化**した文字列の SHA-256 hex 先頭 16 桁（ID に `,` `;` `=` 等の境界文字が含まれても衝突しない。r1 I2）。`compute_ask_digest(asks: tuple[AskSection, ...]) -> str` は decision ask のみを文書順で pairs 化して同関数へ渡す。Task 3（埋め込み）と Task 6（DOM からの再計算照合）が両方この関数を使う（アルゴリズムの正本は 1 箇所）。
- ask 契約の拡張（`validate_ask_blocks`）: decision の各 `data-ask-option` は非空の `data-ask-option-id` を持ち、ブロック内で一意。decision には `data-ask-memo` つき textarea が**ちょうど 1 つ**。新診断: `"decision の各選択肢には非空の data-ask-option-id が必要です"` / `"decision の選択肢 id が重複しています: <id>"` / `"decision にはメモ欄（data-ask-memo）がちょうど1つ必要です"`。回収対象は typed ask（`data-ve-section-kind="ask"` wrapper 内）のみだが、契約検査は破壊的変更ポリシーに従い全 `data-ask="decision"` ブロックへ一律適用する。

- [ ] **Step 1: 失敗するテストを書く**（要点。実ファイルには次の 6 ケース: レンダラ出力に option-id が出る / レンダラ出力に静的メモ欄が出る / digest が決定的で decision のみに依存 / digest が境界文字で衝突しない / option-id 欠落・重複が契約違反 / メモ欄欠落が契約違反）

```python
def test_decision_options_carry_option_ids(self) -> None:
    section = AskSection(id="ask-1", ask_type="decision", question="どちらにしますか。",
                         options=(AskOption("opt-a", "案A", "早いが粗い"),
                                  AskOption("opt-b", "案B", "遅いが確実")),
                         default_id="opt-b")
    wrapped = render_ask(section)
    self.assertIn('data-ask-option data-ask-option-id="opt-a"', wrapped.markup)
    self.assertIn('data-ask-option-id="opt-b" data-ask-default', wrapped.markup.replace("data-ask-option ", ""))

def test_decision_renders_static_memo_field(self) -> None:
    section = AskSection(id="ask-1", ask_type="decision", question="どちらにしますか。",
                         options=(AskOption("opt-a", "案A", "早いが粗い"),
                                  AskOption("opt-b", "案B", "遅いが確実")),
                         default_id="opt-b")
    wrapped = render_ask(section)
    self.assertIn('<textarea data-ask-memo></textarea>', wrapped.markup)
    self.assertIn('メモ（この判断について）', wrapped.markup)

def test_digest_ids_cannot_collide_across_field_boundaries(self) -> None:
    from ve_components.document_sections import compute_ask_digest_from_pairs
    self.assertNotEqual(
        compute_ask_digest_from_pairs((("ask-1", ("a,b",)),)),
        compute_ask_digest_from_pairs((("ask-1", ("a", "b")),)))
    self.assertNotEqual(
        compute_ask_digest_from_pairs((("ask-1=a", ("b",)),)),
        compute_ask_digest_from_pairs((("ask-1", ("a", "b")),)))

def test_digest_depends_only_on_decision_contract(self) -> None:
    from ve_components.document_sections import compute_ask_digest
    base = (AskSection(id="ask-1", ask_type="decision", question="Q。",
                       options=(AskOption("a", "A", "t"), AskOption("b", "B", "t")),
                       no_default_reason="理由"),)
    with_request = base + (AskSection(id="ask-2", ask_type="request",
                                      steps=(AskStep("user", "あなた", "確認する"),)),)
    self.assertEqual(compute_ask_digest(base), compute_ask_digest(with_request))
    changed = (AskSection(id="ask-1", ask_type="decision", question="Q。",
                          options=(AskOption("a", "A", "t"), AskOption("c", "C", "t")),
                          no_default_reason="理由"),)
    self.assertNotEqual(compute_ask_digest(base), compute_ask_digest(changed))
```

- [ ] **Step 2: 失敗を確認** — Run: `python3 -m pytest tests/test_ask_section.py tests/test_ask_blocks.py -q` / Expected: FAIL

- [ ] **Step 3: 実装**

`document_sections.py`（冒頭に `import hashlib` / `import json` を追加）:

```python
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
```

`_render_decision_body` の option 生成を変更し、options リストの後に静的メモ欄を追加:

```python
    for opt in section.options:
        attrs = f'data-ask-option data-ask-option-id="{_esc(opt.id)}"'
        if section.default_id is not None and opt.id == section.default_id:
            attrs += " data-ask-default"
```

```python
    memo = (
        '\n  <div class="ask-memo">'
        '<label>メモ（この判断について）<textarea data-ask-memo></textarea></label></div>'
    )
    # 返却 markup の "</ul>{reason}" 直後（</div> の前）に {memo} を挿入する
```

`checker.py` `_AskParser.handle_starttag` の option 記録に id を、block にメモ欄カウント（初期化辞書へ `"memos": 0`）を追加し、`validate_ask_blocks` の decision 分岐で検査:

```python
            if "data-ask-option" in attr:
                block["options"] += 1
                block["option_records"].append(
                    {"tradeoffs": 0, "text": "", "option_id": (attr.get("data-ask-option-id") or "").strip()})
            if "data-ask-memo" in attr:
                block["memos"] += 1
```

```python
            option_ids = [rec["option_id"] for rec in block["option_records"]]
            if any(not oid for oid in option_ids):
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "decision の各選択肢には非空の data-ask-option-id が必要です"))
            for oid in sorted({o for o in option_ids if o and option_ids.count(o) > 1}):
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, f"decision の選択肢 id が重複しています: {oid}"))
            if block["memos"] != 1:
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "decision にはメモ欄（data-ask-memo）がちょうど1つ必要です"))
```

- [ ] **Step 4: 既存テスト・fixture の修復** — decision ask markup を含む既存 fixture / テスト内 markup（`valid-proposal.html`・`bad-ask-decision.html`・`test_ask_blocks.py` のインライン markup。`grep -rln 'data-ask="decision"' tests/` で列挙）へ `data-ask-option-id` を追加する。`bad-ask-decision.html` は既存の期待診断が変わらないよう option-id は正しく付与する。
- [ ] **Step 5: 全テストパス確認** — Run: `python3 -m pytest tests -q` と `bash check.sh --selftest` / Expected: PASS
- [ ] **Step 6: Commit** — `git commit -m "feat(ve): add option ids to decision asks and build-time ask contract digest"`

**done_criteria:** レンダラ出力（option-id・静的メモ欄）・契約検査（option-id 一意・メモ欄ちょうど 1 つ）・digest（JSON canonical・境界文字非衝突）が新テストで固定され、全テスト・selftest PASS。

---

### Task 3: 回収パネルレンダラと build 挿入（静的サマリー・digest 埋め込み）

**Files:**
- Modify: `scripts/ve_components/document_sections.py`（`render_decision_panel` 新設、`_allocate_instance_id` へ一般化）
- Modify: `scripts/build_explainer.py`（closing の後にパネルを挿入）
- Modify: `scripts/ve_components/validation.py:207`（`_RESERVED_CLASSES` に `decision-panel` 追加）
- Test: `scripts/tests/test_decision_panel.py`（新規）

**Interfaces:**
- Produces: `render_decision_panel(asks, document, schema_version, document_path, *, occupied_ids=frozenset()) -> WrappedDocumentSection | None`。decision ask が 0 件なら `None`（空パネルは出さない）。wrapper は `data-ve-section-kind="decision-panel" data-ve-document-id data-ve-schema-version data-ve-ask-digest data-ve-document-path id="sec-decision-panel[-N]"`。instance id は TOC と同じ衝突回避方式（`_allocate_instance_id(prefix, occupied_ids)` に一般化し、`allocate_toc_instance_id` は互換ラッパーとして維持）。
- `document_path` は CLI の `--output` 引数を**逐語**で埋め込む（`resolve()` しない。r1 C4: spec 117 行目の `<ファイルパス>` の正本。相対 `--output` は相対のまま埋まるため、コミットされる fixture / example は機械間で再現可能。実運用は SKILL.md が絶対パスを指示済み）。
- 静的 markup（JS 無効時の要約表示。spec 110 行目の「問い→選択→メモ」サマリーと全体メモ欄を静的に持つ。r1 C2。コピー操作系＝ボタン・ステータス・fallback のみ Task 5 の固定 JS が注入する）:

```html
<section data-ve-section-kind="decision-panel" data-ve-document-id="doc-1"
 data-ve-schema-version="1" data-ve-ask-digest="0123456789abcdef"
 data-ve-document-path="examples/demo.html" id="sec-decision-panel">
<section class="decision-panel" aria-label="判断の回収">
  <h2>判断の回収</h2>
  <ul class="panel-asks">
    <li data-ve-panel-ask="ask-1">
      <span class="panel-question">どちらにしますか。</span>
      <span class="panel-status" data-ve-panel-status>未選択（既定案: 案B）</span>
      <span class="panel-memo" data-ve-panel-memo hidden></span>
    </li>
  </ul>
  <div class="ask-memo"><label>全体メモ<textarea data-ve-panel-global-memo></textarea></label></div>
  <p class="panel-note">選択の反映・メモの保存・コピーはブラウザの JavaScript が有効なときに使えます。</p>
</section>
</section>
```

- 既定案は選択済みとして扱わない: 静的 status は常に `未選択（既定案: <label>）` または `未選択（既定案なし）`。メモ表示（`data-ve-panel-memo`）は静的には空＋`hidden` で、Task 5 の固定 JS がメモ入力と同期して表示する。
- Consumes: `compute_ask_digest`（Task 2）、`AssemblyRequest.schema_version`。
- build 挿入位置: IR sections の最後（= closing。Phase 1 の構造不変条件で保証）を処理した後に `items.append(panel)`。TOC の発火判定・entries には**含めない**（パネルは利用者記述セクションではない）。`build_document` は `document_path: str` を新たな引数として受け、`build_to_path` が `str(paths.output)` を渡す（`BuildPaths.output` は `Path(args.output)` そのままなので相対は相対のまま）。

- [ ] **Step 1: 失敗するテストを書く**（decision 1 件でパネル生成・digest/document-id/schema/document-path 属性・既定案 status 文言・`data-ve-panel-memo`（hidden）と `data-ve-panel-global-memo` textarea の静的存在 / decision 0 件（request のみ）で `None` / build 経由で closing の後にパネル wrapper が出て `--output` 逐語のパスが埋まる / narrative に `class="decision-panel"` を書くと拒否）
- [ ] **Step 2: 失敗を確認** — Run: `python3 -m pytest tests/test_decision_panel.py -q` / Expected: FAIL（ImportError）
- [ ] **Step 3: 実装** — `render_decision_panel` を上記契約どおり実装。`build_explainer.build_document` にシグネチャ追加（`document_path: str`）し、ループ後・TOC 挿入前に:

```python
    panel = render_decision_panel(
        tuple(s for s in request.sections if isinstance(s, AskSection)),
        request.document, request.schema_version, document_path,
        occupied_ids=occupied_ids | ({toc.instance_id} if toc is not None else frozenset()))
    if panel is not None:
        items.append(panel)
```

`build_to_path` は `build_document(..., document_path=str(paths.output))` を渡す。`build_document` の既存呼び出し元（テスト含む）は `grep -rn "build_document(" scripts/` で列挙して更新する。

`validation.py`: `_RESERVED_CLASSES = frozenset({"first-screen", "closing-section", "ask", "link-domain", "decision-panel"})`。

- [ ] **Step 4: 既存テスト修復** — decision ask を含む assembly を全文一致で検証する既存テスト（`test_mixed_assembly.py` 等。`grep -rln '"ask"' tests/component-valid-*.json` と `grep -rln 'askType' tests/` で列挙）にパネル分の期待値を追加。ビルド済み fixture のうち decision ask を含むものは再ビルド。
- [ ] **Step 5: 全テストパス確認** — Run: `python3 -m pytest tests -q` / Expected: PASS。`check_final_document` の expected 比較（`CompositionResult.sections_markup`）にパネルが含まれて整合することを `test_decision_panel.py` の build 経由ケースで確認。未知 section kind を拒否する検査が存在した場合は `decision-panel` を語彙へ追加し、そのテストも更新する。
- [ ] **Step 6: Commit** — `git commit -m "feat(ve): render decision collection panel after closing with embedded ask digest"`

**done_criteria:** decision ask を含む資料のビルドで closing 直後にパネル wrapper が生成され、digest・document-id・schemaVersion・document-path（`--output` 逐語）が data 属性で自己表明され、問い・status・メモ表示・全体メモ欄が静的 markup に存在する。decision ask ゼロの資料にはパネルが出ない。全テスト PASS。

---

### Task 4: 判断回収エンジン純関数コア（decision_engine.js＋Node テストハーネス）

**Files:**
- Create: `scripts/tests/runtime/decision_engine.js`
- Create: `scripts/tests/runtime/decision_engine_driver.js`
- Test: `scripts/tests/test_decision_engine_js.py`（新規）

**Interfaces:**
- Produces（すべて純関数。contract / state は plain object を非破壊で扱う）:
  - `storageKey(contract) -> "ve-decision:<documentId>:<schemaVersion>:<digest>"`
  - `emptyState() -> {selections: {}, memos: {}, globalMemo: ""}`
  - `selectOption(state, askId, optionId, contract) -> state`（contract に無い ask/option は無視して元 state を返す）
  - `setMemo(state, askId, text) -> state` / `setGlobalMemo(state, text) -> state`
  - `restoreState(raw, contract) -> state`（localStorage の生文字列を受け、JSON 破損・未知 ask/option を**破棄**して復元。シナリオ⑦の正本）
  - `serializeState(state) -> string`
  - `formatCopyText(contract, state) -> string` — spec 112-124 行目のテンプレートに一致。**全 ask を文書順に** `問い:` ブロックとして出力する（spec 21 行目「各 ask の問い→選択→メモ」。r1 C3）。選択済みは `→ 選択: <label>（既定案どおり|既定案から変更|既定案なし） — トレードオフ: <tradeoff>`、未選択は `→ 選択: 未選択（既定案: <label>|なし）`（spec 111 行目の文言）。`→ メモ:` 行は選択状態にかかわらず **trim 後非空のときのみ**出力する（空メモの行は出さない。この出し分けはテストの完全一致で固定する）。その後に `未選択:`（未選択 ask の集約。spec テンプレートの行）、`リスク要約:`（riskHeadings の列挙）、`全体メモ:`（trim 後非空のときのみ）。
- contract の形（DOM バインダが Task 5 で組み立てる）: `{documentId, schemaVersion, digest, title, documentPath, riskHeadings: [..], asks: [{id, question, defaultId|null, options: [{id, label, tradeoff}]}]}`。`documentPath` はパネルの `data-ve-document-path`（Task 3 がビルド時に埋め込んだ `--output` 逐語。spec 117 行目の `<ファイルパス>`。実行時 URL は使わない。r1 C4）。
- Node ↔ ブラウザ両用: 末尾で `module.exports`（Node）または `globalThis.veDecisionEngine`（ブラウザ）へ公開。ファイル全文が Task 5 で skeleton のマーカー間に**逐語**埋め込まれる。

- [ ] **Step 1: Node ドライバを書く** — `scripts/tests/runtime/decision_engine_driver.js`（テストの実行基盤。エンジン本体はまだ書かない）:

```js
/* Test driver: read a JSON list of calls on stdin, run them against the
   engine, print the JSON list of results. "$state" in args is replaced by
   the running state; {assign: true} stores the result back into it. */
const engine = require("./decision_engine.js");
let input = "";
process.stdin.on("data", (chunk) => { input += chunk; });
process.stdin.on("end", () => {
  const calls = JSON.parse(input);
  let state = engine.emptyState();
  const results = [];
  for (const call of calls) {
    const args = (call.args || []).map((a) => (a === "$state" ? state : a));
    const result = engine[call.fn](...args);
    if (call.assign) state = result;
    results.push(result === undefined ? null : result);
  }
  process.stdout.write(JSON.stringify(results));
});
```

- [ ] **Step 2: 失敗するテストを書く（RED）** — `scripts/tests/test_decision_engine_js.py` 全文:

```python
"""回収エンジン純関数の検証（node 標準のみ・npm 依存なし。spec 逸脱の Playwright 代替）。"""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

NODE = shutil.which("node")
RUNTIME = Path(__file__).resolve().parent / "runtime"
DRIVER = RUNTIME / "decision_engine_driver.js"

CONTRACT = {
    "documentId": "doc-1", "schemaVersion": 1, "digest": "0123456789abcdef",
    "title": "料金改定は限定対象で段階公開する",
    "documentPath": "examples/demo.html",
    "riskHeadings": ["リスクと弱い前提", "不確かな点"],
    "asks": [
        {"id": "ask-1", "question": "対象範囲をどちらにしますか。", "defaultId": "opt-b",
         "options": [{"id": "opt-a", "label": "案A", "tradeoff": "早いが粗い"},
                     {"id": "opt-b", "label": "案B", "tradeoff": "遅いが確実"}]},
        {"id": "ask-2", "question": "開始時期はいつにしますか。", "defaultId": None,
         "options": [{"id": "opt-c", "label": "今月", "tradeoff": "準備が薄い"},
                     {"id": "opt-d", "label": "来月", "tradeoff": "機会損失"}]},
    ],
}

HEADER = [
    "[visual-explain 判断結果]",
    "資料: 料金改定は限定対象で段階公開する",
    "(examples/demo.html / id: doc-1 / schema: 1 / asks: 0123456789abcdef)",
]


def run_calls(calls: list[dict]) -> list:
    proc = subprocess.run([NODE, str(DRIVER)], input=json.dumps(calls).encode("utf-8"),
                          capture_output=True, timeout=30)
    assert proc.returncode == 0, proc.stderr.decode("utf-8")
    return json.loads(proc.stdout)


@unittest.skipUnless(NODE, "node が無い環境ではスキップ（Task 9 の完了ゲートでは非スキップ実行が必須）")
class DecisionEngineJsTest(unittest.TestCase):
    def test_storage_key_format(self) -> None:
        (key,) = run_calls([{"fn": "storageKey", "args": [CONTRACT]}])
        self.assertEqual(key, "ve-decision:doc-1:1:0123456789abcdef")

    def test_select_change_serialize_restore_roundtrip(self) -> None:
        results = run_calls([
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-a", CONTRACT], "assign": True},
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-b", CONTRACT], "assign": True},
            {"fn": "serializeState", "args": ["$state"]},
        ])
        (restored,) = run_calls([{"fn": "restoreState", "args": [results[-1], CONTRACT]}])
        self.assertEqual(restored["selections"], {"ask-1": "opt-b"})

    def test_restore_drops_unknown_ask_and_option(self) -> None:
        stale = json.dumps({"selections": {"ask-1": "opt-z", "ask-9": "opt-a"},
                            "memos": {"ask-9": "古いメモ"}, "globalMemo": "残す"})
        (restored,) = run_calls([{"fn": "restoreState", "args": [stale, CONTRACT]}])
        self.assertEqual(restored["selections"], {})
        self.assertEqual(restored["memos"], {})
        self.assertEqual(restored["globalMemo"], "残す")

    def test_restore_tolerates_broken_input(self) -> None:
        empty = {"selections": {}, "memos": {}, "globalMemo": ""}
        for raw in [None, "not json", "[]", "42"]:
            (restored,) = run_calls([{"fn": "restoreState", "args": [raw, CONTRACT]}])
            self.assertEqual(restored, empty)

    def test_select_option_ignores_unknown_option(self) -> None:
        (state,) = run_calls([{"fn": "selectOption", "args": ["$state", "ask-1", "opt-z", CONTRACT]}])
        self.assertEqual(state["selections"], {})

    def test_copy_text_full_selection_exact(self) -> None:
        calls = [
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-a", CONTRACT], "assign": True},
            {"fn": "selectOption", "args": ["$state", "ask-2", "opt-c", CONTRACT], "assign": True},
            {"fn": "setMemo", "args": ["$state", "ask-1", "撤回条件を先に固める"], "assign": True},
            {"fn": "setGlobalMemo", "args": ["$state", "全体の所感"], "assign": True},
            {"fn": "formatCopyText", "args": [CONTRACT, "$state"]},
        ]
        expected = "\n".join(HEADER + [
            "問い: 対象範囲をどちらにしますか。",
            "→ 選択: 案A（既定案から変更） — トレードオフ: 早いが粗い",
            "→ メモ: 撤回条件を先に固める",
            "問い: 開始時期はいつにしますか。",
            "→ 選択: 今月（既定案なし） — トレードオフ: 準備が薄い",
            "リスク要約: リスクと弱い前提 / 不確かな点",
            "全体メモ: 全体の所感",
        ])
        self.assertEqual(run_calls(calls)[-1], expected)

    def test_copy_text_preserves_memo_of_unselected_ask(self) -> None:
        # r1 C3: 未選択の ask もメモを欠落させない（spec 21 行目「各 ask の問い→選択→メモ」）
        calls = [
            {"fn": "setMemo", "args": ["$state", "ask-2", "まだ迷っている"], "assign": True},
            {"fn": "formatCopyText", "args": [CONTRACT, "$state"]},
        ]
        expected = "\n".join(HEADER + [
            "問い: 対象範囲をどちらにしますか。",
            "→ 選択: 未選択（既定案: 案B）",
            "問い: 開始時期はいつにしますか。",
            "→ 選択: 未選択（既定案: なし）",
            "→ メモ: まだ迷っている",
            "未選択: 対象範囲をどちらにしますか。（既定案: 案B） / 開始時期はいつにしますか。（既定案: なし）",
            "リスク要約: リスクと弱い前提 / 不確かな点",
        ])
        self.assertEqual(run_calls(calls)[-1], expected)

    def test_copy_text_keeps_multiline_japanese_memo_verbatim(self) -> None:
        memo = "一行目\r\n二行目：長文" + "あ" * 1200
        calls = [
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-b", CONTRACT], "assign": True},
            {"fn": "setMemo", "args": ["$state", "ask-1", memo], "assign": True},
            {"fn": "formatCopyText", "args": [CONTRACT, "$state"]},
        ]
        text = run_calls(calls)[-1]
        self.assertIn("→ メモ: " + memo, text)
        self.assertIn("→ 選択: 案B（既定案どおり） — トレードオフ: 遅いが確実", text)

    def test_blank_memo_emits_no_memo_line(self) -> None:
        calls = [
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-b", CONTRACT], "assign": True},
            {"fn": "setMemo", "args": ["$state", "ask-1", "  \n  "], "assign": True},
            {"fn": "formatCopyText", "args": [CONTRACT, "$state"]},
        ]
        self.assertNotIn("→ メモ:", run_calls(calls)[-1])

    def test_engine_sources_pass_node_check(self) -> None:
        for name in ("decision_engine.js", "decision_engine_driver.js"):
            proc = subprocess.run([NODE, "--check", str(RUNTIME / name)], capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))
```

- [ ] **Step 3: 失敗を確認（RED）** — Run: `python3 -m pytest tests/test_decision_engine_js.py -v` / Expected: 全ケース FAIL（`decision_engine.js` が存在せず driver の `require` がエラーになる）

- [ ] **Step 4: エンジン正本を書く（GREEN）** — `scripts/tests/runtime/decision_engine.js`:

```js
/* Decision-collection pure core for visual-explain.
   This file is the source of truth; assets/skeleton.html embeds it verbatim
   between the FIXED DECISION ENGINE CORE markers (byte-equality is enforced
   by test_skeleton_audit.py). No DOM, no timers, no I/O here. */
(function (global) {
  "use strict";

  function storageKey(contract) {
    return "ve-decision:" + contract.documentId + ":" + contract.schemaVersion + ":" + contract.digest;
  }

  function emptyState() {
    return { selections: {}, memos: {}, globalMemo: "" };
  }

  function findAsk(contract, askId) {
    for (const ask of contract.asks) if (ask.id === askId) return ask;
    return null;
  }

  function findOption(ask, optionId) {
    for (const option of ask.options) if (option.id === optionId) return option;
    return null;
  }

  function cloneWith(state, patch) {
    return {
      selections: Object.assign({}, state.selections, patch.selections || {}),
      memos: Object.assign({}, state.memos, patch.memos || {}),
      globalMemo: patch.globalMemo !== undefined ? patch.globalMemo : state.globalMemo,
    };
  }

  function selectOption(state, askId, optionId, contract) {
    const ask = findAsk(contract, askId);
    if (!ask || !findOption(ask, optionId)) return state;
    const patch = { selections: {} };
    patch.selections[askId] = optionId;
    return cloneWith(state, patch);
  }

  function setMemo(state, askId, text) {
    const patch = { memos: {} };
    patch.memos[askId] = String(text);
    return cloneWith(state, patch);
  }

  function setGlobalMemo(state, text) {
    return cloneWith(state, { globalMemo: String(text) });
  }

  function restoreState(raw, contract) {
    // Stale or foreign entries never survive: unknown ask ids and option ids
    // are dropped so a regenerated document starts unselected (scenario 7).
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (error) {
      return emptyState();
    }
    if (!parsed || typeof parsed !== "object") return emptyState();
    const state = emptyState();
    for (const ask of contract.asks) {
      const selected = parsed.selections ? parsed.selections[ask.id] : undefined;
      if (typeof selected === "string" && findOption(ask, selected)) state.selections[ask.id] = selected;
      const memo = parsed.memos ? parsed.memos[ask.id] : undefined;
      if (typeof memo === "string") state.memos[ask.id] = memo;
    }
    if (typeof parsed.globalMemo === "string") state.globalMemo = parsed.globalMemo;
    return state;
  }

  function serializeState(state) {
    return JSON.stringify(state);
  }

  function defaultLabel(ask) {
    if (!ask.defaultId) return null;
    const option = findOption(ask, ask.defaultId);
    return option ? option.label : null;
  }

  function unselectedNote(ask) {
    const label = defaultLabel(ask);
    return ask.question + "（既定案: " + (label === null ? "なし" : label) + "）";
  }

  function selectionStatus(ask, optionId) {
    if (!ask.defaultId) return "既定案なし";
    return optionId === ask.defaultId ? "既定案どおり" : "既定案から変更";
  }

  function askLines(state, ask, unselected) {
    // r1 C3: every ask emits its 問い/選択/メモ block regardless of selection
    // state, so memos on unselected asks are never dropped from the copy text.
    const lines = ["問い: " + ask.question];
    const selectedId = state.selections[ask.id];
    const option = selectedId ? findOption(ask, selectedId) : null;
    if (option) {
      lines.push("→ 選択: " + option.label + "（" + selectionStatus(ask, option.id) + "）"
        + " — トレードオフ: " + option.tradeoff);
    } else {
      const label = defaultLabel(ask);
      lines.push("→ 選択: 未選択（既定案: " + (label === null ? "なし" : label) + "）");
      unselected.push(unselectedNote(ask));
    }
    const memo = state.memos[ask.id];
    if (typeof memo === "string" && memo.trim()) lines.push("→ メモ: " + memo);
    return lines;
  }

  function formatCopyText(contract, state) {
    const lines = [
      "[visual-explain 判断結果]",
      "資料: " + contract.title,
      "(" + contract.documentPath + " / id: " + contract.documentId +
        " / schema: " + contract.schemaVersion + " / asks: " + contract.digest + ")",
    ];
    const unselected = [];
    for (const ask of contract.asks) lines.push(...askLines(state, ask, unselected));
    if (unselected.length) lines.push("未選択: " + unselected.join(" / "));
    if (contract.riskHeadings.length) lines.push("リスク要約: " + contract.riskHeadings.join(" / "));
    if (state.globalMemo && state.globalMemo.trim()) lines.push("全体メモ: " + state.globalMemo);
    return lines.join("\n");
  }

  const engine = {
    storageKey, emptyState, selectOption, setMemo, setGlobalMemo,
    restoreState, serializeState, formatCopyText,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = engine;
  else global.veDecisionEngine = engine;
})(globalThis);
```

- [ ] **Step 5: パス確認（GREEN）** — Run: `python3 -m pytest tests/test_decision_engine_js.py -v` / Expected: 全 10 ケース PASSED（SKIPPED なし。node が無い環境ではここで作業を止めて報告する）
- [ ] **Step 6: Commit** — `git commit -m "feat(ve): add pure-function decision engine core with node-only test harness"`

**done_criteria:** エンジン正本・ドライバ・pytest ハーネスが揃い、10 ケースが RED→GREEN の順で作成されて node 実行で PASS。コピー出力の完全一致テスト 2 件（全選択／未選択＋メモ保持）が spec 112-124 行目のテンプレートを固定している。npm / package.json は存在しない。

---

### Task 5: skeleton 改定（CSS＋固定 JS）と fixture 一括 resplice

skeleton の固定領域ハッシュが変わる唯一のタスク。改定→監査テスト→resplice→全数回帰を 1 コミット系列で完結させる。

**Files:**
- Modify: `assets/skeleton.html`（`<style>` 末尾へ CSS 追加、`</body>` 前の script 内へ固定 JS 2 ブロック追加）
- Modify: `scripts/tests/test_skeleton_audit.py`（コア逐語一致テスト追加・監査追随）
- Modify: `scripts/tests/*.html`（resplice 一括再生成）＋ KEEP_AS_IS 6 fixture（同一編集のテキスト適用）
- Test: `scripts/tests/test_skeleton_audit.py` / 全既存テスト

**Interfaces:**
- Consumes: `decision_engine.js`（Task 4 の正本を逐語埋め込み）、Task 3 のパネル markup（`data-ve-panel-ask` / `data-ve-panel-status` / `data-ve-panel-memo` / `data-ve-panel-global-memo` / `data-ve-document-path`）、Task 2 の `data-ask-option-id` と静的メモ欄（`data-ask-memo`）。
- Produces: バインダは**静的要素へのバインドを基本**とする — ask のメモ欄・パネルの全体メモ欄はレンダラ出力の textarea にイベントを結線し（JS が textarea を生成するのはゼロ。r1 C1/C2）、JS が新規生成するのは選択ボタン・コピー導線（ボタン／ステータス／fallback）だけ。選択ボタンの可視テキストは `この案を選ぶ（<選択肢ラベル>）` とし、accessible name に選択肢ラベルを含める（WCAG 2.5.3 label-in-name。r1 I5）。メモ入力はパネルの `data-ve-panel-memo` 表示へ即時同期する（spec 110 行目「問い→選択→メモ」サマリー）。
- Produces（CSS。`</style>` 直前の「図表記法」ブロックの後へ追加。spacing は `var(--space-*)` のみ・意味色は選択状態＝accent に限る）:

```css
    .ask-select { justify-self: start; margin-top: var(--space-1); }
    .ask-options [data-ask-option][data-ask-selected] { outline: 2px solid var(--accent); background: color-mix(in srgb, var(--accent) 12%, var(--surface)); }
    .ask-memo { display: grid; gap: var(--space-1); margin-top: var(--space-2); }
    .ask-memo textarea, .decision-panel textarea { font: inherit; color: inherit; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); padding: var(--space-1); min-height: 3rem; max-width: 100%; }
    .decision-panel { max-width: var(--w-narrative); padding: var(--space-3); background: var(--surface); border-radius: .5rem; }
    .decision-panel h2 { margin-top: 0; }
    .panel-asks { display: grid; gap: var(--space-1); margin: 0; padding-left: var(--space-3); }
    .panel-status { color: var(--text-dim); }
    .panel-memo { display: block; color: var(--text-dim); white-space: pre-wrap; }
    .panel-copy-status { margin: var(--space-1) 0 0; color: var(--text-dim); }
    .panel-copy-fallback { max-width: 100%; overflow: auto; padding: var(--space-2); background: var(--bg); border: 1px solid var(--border); white-space: pre-wrap; }
```

- Produces（固定 JS。ステッパー IIFE の後・`</script>` 前へ追加。**既存 3 ブロックには触れない**）:

```js
  /* FIXED DECISION ENGINE CORE:BEGIN (verbatim copy of scripts/tests/runtime/decision_engine.js) */
  ...decision_engine.js 全文を逐語で貼る（Task 4 の正本）...
  /* FIXED DECISION ENGINE CORE:END */

  /* FIXED DECISION COLLECTION JS: DO NOT MODIFY. */
  (() => {
    const engine = globalThis.veDecisionEngine;
    const panel = document.querySelector('[data-ve-section-kind="decision-panel"]');
    if (!engine || !panel) return;
    const askSections = Array.from(document.querySelectorAll(
      'section[data-ve-section-kind="ask"][data-ve-ask-type="decision"][id]'));
    const contract = {
      documentId: panel.dataset.veDocumentId || "",
      schemaVersion: panel.dataset.veSchemaVersion || "",
      digest: panel.dataset.veAskDigest || "",
      title: document.title,
      documentPath: panel.dataset.veDocumentPath || "",
      riskHeadings: Array.from(document.querySelectorAll(
        '[data-ve-section-kind="closing"] h2')).map((h) => h.textContent.trim()),
      asks: askSections.map((section) => {
        const defaultItem = section.querySelector('[data-ask-default]');
        return {
          id: section.id,
          question: (section.querySelector('.ask-question')?.textContent || "").trim(),
          defaultId: defaultItem ? (defaultItem.dataset.askOptionId || null) : null,
          options: Array.from(section.querySelectorAll('[data-ask-option]')).map((item) => ({
            id: item.dataset.askOptionId || "",
            label: (item.querySelector('span')?.textContent || "").trim(),
            tradeoff: (item.querySelector('.ask-tradeoff')?.textContent || "").trim(),
          })),
        };
      }),
    };
    let storage = null;
    let state = engine.emptyState();
    try {
      storage = window.localStorage;
      state = engine.restoreState(storage.getItem(engine.storageKey(contract)), contract);
    } catch {
      storage = null; // 永続化のみ喪失。選択は動き続ける（シナリオ④）。
    }
    const persist = () => {
      if (!storage) return;
      try { storage.setItem(engine.storageKey(contract), engine.serializeState(state)); } catch {}
    };
    const render = () => {
      contract.asks.forEach((ask) => {
        const section = document.getElementById(ask.id);
        if (!section) return;
        section.querySelectorAll('[data-ask-option]').forEach((item) => {
          const selected = state.selections[ask.id] === item.dataset.askOptionId;
          if (selected) item.setAttribute('data-ask-selected', '');
          else item.removeAttribute('data-ask-selected');
          const button = item.querySelector('button[data-ask-select]');
          if (button) button.setAttribute('aria-pressed', String(selected));
        });
        const row = panel.querySelector(`[data-ve-panel-ask="${ask.id}"]`);
        if (!row) return;
        const status = row.querySelector('[data-ve-panel-status]');
        const option = ask.options.find((o) => o.id === state.selections[ask.id]);
        if (status && option) status.textContent = `選択: ${option.label}`;
        const memoRow = row.querySelector('[data-ve-panel-memo]');
        if (memoRow) {
          const memo = state.memos[ask.id] || '';
          memoRow.hidden = !memo.trim();
          memoRow.textContent = memo.trim() ? `メモ: ${memo}` : '';
        }
      });
    };
    askSections.forEach((section) => {
      section.querySelectorAll('[data-ask-option]').forEach((item) => {
        const label = (item.querySelector('span')?.textContent || '').trim();
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'ask-select';
        button.setAttribute('data-ask-select', '');
        button.setAttribute('aria-pressed', 'false');
        button.textContent = `この案を選ぶ（${label}）`;
        button.addEventListener('click', () => {
          state = engine.selectOption(state, section.id, item.dataset.askOptionId, contract);
          persist(); render();
        });
        item.append(button);
      });
      const memoField = section.querySelector('textarea[data-ask-memo]');
      if (memoField) {
        memoField.value = state.memos[section.id] || '';
        memoField.addEventListener('input', () => {
          state = engine.setMemo(state, section.id, memoField.value);
          persist(); render();
        });
      }
    });
    const globalField = panel.querySelector('textarea[data-ve-panel-global-memo]');
    if (globalField) {
      globalField.value = state.globalMemo || '';
      globalField.addEventListener('input', () => {
        state = engine.setGlobalMemo(state, globalField.value);
        persist();
      });
    }
    const copyButton = document.createElement('button');
    copyButton.type = 'button';
    copyButton.textContent = '判断をプロンプトとしてコピー';
    const copyStatus = document.createElement('p');
    copyStatus.className = 'panel-copy-status';
    copyStatus.setAttribute('aria-live', 'polite');
    const fallback = document.createElement('pre');
    fallback.className = 'panel-copy-fallback';
    fallback.hidden = true;
    copyButton.addEventListener('click', async () => {
      const text = engine.formatCopyText(contract, state);
      try {
        await navigator.clipboard.writeText(text);
        fallback.hidden = true;
        copyStatus.textContent = 'コピーしました。エージェントへ貼り付けてください。';
      } catch {
        fallback.textContent = text;
        fallback.hidden = false;
        copyStatus.textContent = 'クリップボードを使えないため、以下を手動でコピーしてください。';
      }
    });
    panel.querySelector('.decision-panel')?.append(copyButton, copyStatus, fallback);
    render();
  })();
```

- [ ] **Step 1: 失敗するテストを書く** — `test_skeleton_audit.py` に追加:

```python
class DecisionEngineEmbedTest(unittest.TestCase):
    def test_skeleton_embeds_engine_core_verbatim(self):
        core = (Path(__file__).resolve().parent / "runtime" / "decision_engine.js").read_text("utf-8")
        begin = "/* FIXED DECISION ENGINE CORE:BEGIN"
        end = "/* FIXED DECISION ENGINE CORE:END */"
        self.assertIn(begin, SKELETON)
        embedded = SKELETON.split(begin, 1)[1].split("*/", 1)[1].split(end, 1)[0]
        self.assertEqual(embedded.strip(), core.strip())

    def test_skeleton_has_decision_collection_block(self):
        self.assertIn("/* FIXED DECISION COLLECTION JS: DO NOT MODIFY. */", SKELETON)
```

- [ ] **Step 2: 失敗を確認** — Run: `python3 -m pytest tests/test_skeleton_audit.py -q` / Expected: FAIL
- [ ] **Step 3: skeleton を改定** — 上記 CSS・JS を追加。既存監査（意味色 allowlist・spacing グリッド・二層幅）が通ることを確認し、`.ask-options [data-ask-option][data-ask-selected]` の accent 使用は既存 allowlist 項目 `.ask` で被覆されることを確認する（新規 allowlist 追加が必要になった場合は理由コメント付きで追加）。
- [ ] **Step 4: fixture 一括 resplice** — Run: `cd skills/visual-explain/scripts && python3 tests/tools/resplice.py`。続いて KEEP_AS_IS のうち骨格を埋め込む 6 fixture（`bad-closing.html` / `bad-system-closing.html` / `bad-fixed-region.html` / `bad-nesting.html` / `bad-title-missing.html` / `component-bad-fixed-region.html`）へ同一の CSS/JS 追加をテキスト置換で適用する（マーカー破壊・固定領域の故意相違は保存する。resplice.py docstring の規約）。
- [ ] **Step 5: 全数回帰** — Run: `python3 -m pytest tests -q` と `bash check.sh --selftest` / Expected: 全 PASS（selftest の期待診断は不変。変わる場合は Step 4 の適用漏れを疑う）
- [ ] **Step 6: Commit**（分割可）

```bash
git commit -m "feat(ve): add decision collection CSS and fixed JS to skeleton"
git commit -m "test(ve): resplice fixtures onto the decision-collection skeleton"
```

**done_criteria:** skeleton にコア逐語埋め込み＋バインダが入り、逐語一致テスト PASS。既存固定 JS 3 ブロック・既存 CSS は diff 上不変（追加行のみ）。全 fixture resplice 済みで全テスト・selftest PASS。

---

### Task 6: 検査群③拡張（パネル存在・位置・digest 整合）と selftest

**Files:**
- Modify: `scripts/ve_components/document_checks.py`（`_StructureParser` に ask option-id 収集を追加、`_check_decision_panel` 新設、`check_document_structure` から呼ぶ）
- Modify: `scripts/check.sh`（selftest の structure_cases へ 2 件追加）
- Create: `scripts/tests/structure-bad-panel-missing.html` / `scripts/tests/structure-bad-panel-digest.html`
- Test: `scripts/tests/test_document_checks.py`（既存へケース追加）

**Interfaces:**
- Produces: 検査規則（最終文書・DOM 基準。typed ask wrapper `data-ve-section-kind="ask"` のみ回収対象として数える）—
  1. decision ask（`data-ve-ask-type="decision"`）が 1 個以上 → `decision-panel` wrapper がちょうど 1 個。診断: `"decision ask があるのに回収パネルがありません"` / `"回収パネルはちょうど1個必要です"`。
  2. decision ask が 0 個 → パネル禁止。診断: `"decision ask がないのに回収パネルがあります"`。
  3. パネルは最後の closing より後。診断: `"回収パネルは closing の後に必要です"`（`_StructureParser.sections` は兄弟 wrapper を文書順で閉じるため、closing ノードの index < パネルノードの index で判定できる）。
  4. digest 整合: DOM の typed decision ask（wrapper id と `data-ask-option-id` を文書順に収集）から `compute_ask_digest_from_pairs` で再計算し、パネルの `data-ve-ask-digest` と照合。診断: `"回収パネルの ask 契約ダイジェストが一致しません"`。
  5. パネルの `data-ve-document-id` / `data-ve-schema-version` / `data-ve-document-path` が非空。診断: `"回収パネルの自己表明属性が不足しています"`。
- Consumes: `compute_ask_digest_from_pairs`（Task 2。import は `document_checks` → `document_sections` の一方向で循環しない）。

- [ ] **Step 1: bad fixture を作る** — Task 7 の新見本（decision ask 入り）をビルドした後、複製して意図的に壊す（fixture ヘッダコメントに破壊内容を記す）: `structure-bad-panel-missing.html`（パネル wrapper を除去）、`structure-bad-panel-digest.html`（`data-ve-ask-digest` を `0000000000000000` に改竄）。※見本が未整備の段階では最小 IR（first-screen＋decision ask＋closing）を一時ビルドして作成してよい。
- [ ] **Step 2: 失敗するテストを書く**（`test_document_checks.py`: 上記 5 規則それぞれの正常/異常、bad fixture 2 件が期待診断を出す、パネルなし＆ask なしの既存文書が無診断で通る）
- [ ] **Step 3: 失敗確認** → **Step 4: 実装** — `_StructureParser` に「開いている ask wrapper（kind="ask" かつ `data-ve-ask-type="decision"`）配下の `data-ask-option-id`」の収集を追加し（`_SectionNode` に `option_ids: list[str]` フィールド）、`check_document_structure` の末尾で `_check_decision_panel(structure)` を呼ぶ。
- [ ] **Step 5: check.sh selftest にケース追加** — `structure_cases` へ `("structure-bad-panel-missing.html", ("decision ask があるのに回収パネルがありません",))` と `("structure-bad-panel-digest.html", ("回収パネルの ask 契約ダイジェストが一致しません",))` を登録。
- [ ] **Step 6: パス確認** — Run: `python3 -m pytest tests -q` と `bash check.sh --selftest` / Expected: 全 PASS（selftest 件数 +2）
- [ ] **Step 7: Commit** — `git commit -m "feat(ve): verify decision panel presence, position, and ask digest in group-3 checks"`

**done_criteria:** パネルの偽装・欠落・改竄・位置違反が最終文書段階で FAIL になり、selftest に固定される。ビルド経路（`build_explainer.py`）の正常出力は無診断で通る。

---

### Task 7: 破壊的移行 — 見本・ドキュメントの一括改訂（ゼロ依存明文化を含む）

**Files:**
- Modify: `examples/example-proposal.assembly.json`（decision ask を最低 1 件含むことを確認。無ければ既存 ask を decision 化）→ 再ビルドで `examples/example-proposal.html` 更新
- Modify: `SKILL.md`（ワークフロー手順 5-7・「型と第一画面」「末尾節」節に回収パネルの記述、目視チェックにパネル項目追加）
- Modify: `references/design-system.md`（選択状態・パネルの目視規範）
- Modify: `references/patterns.md`（回収動線の説明 1 節。IR 例は**変更なし**＝schema 不変を明記）
- Modify: `scripts/tests/fixtures.md`（新 fixture の記載）
- Modify: リポジトリ `CLAUDE.md`（アーキテクチャ節へ回収エンジン・decision-panel・検査群③拡張を反映。**ゼロ依存不変の明文化**: 「スキル利用時の外部依存ゼロは不変。Playwright / Selenium / Puppeteer / jsdom・npm パッケージ・pip パッケージを追加しない。開発時の JS テストは node 標準のみで実行する」）
- Test: 既存全テスト＋ `bash scripts/check.sh examples/example-proposal.html`

- [ ] **Step 1: 見本を再ビルドして検証** — すべて**リポジトリルート（`~/workspace/visual-explain`）起点**で実行する（r1 I4）:

```bash
cd ~/workspace/visual-explain
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/examples/example-proposal.assembly.json \
  --output skills/visual-explain/examples/example-proposal.html
bash skills/visual-explain/scripts/check.sh skills/visual-explain/examples/example-proposal.html
```

Expected: PASS。生成 HTML に `data-ve-section-kind="decision-panel"`・digest 属性・`data-ve-document-path="skills/visual-explain/examples/example-proposal.html"`（`--output` 逐語＝リポジトリルート相対で機械間再現可能）があることを grep で確認。
- [ ] **Step 2: SKILL.md 改訂** — 手順 5 の型付きセクション記述に「decision ask は回収パネルの対象になる（パネルはビルドが自動生成し、IR に書かない）」、手順 7 の目視チェックと「目視チェック」節に「回収パネルが closing の後にあり、既定案が選択済み扱いされていない」を追加。「既定案は選択済みとして扱わない」原則を末尾節の説明に明記。
- [ ] **Step 3: design-system.md / patterns.md / fixtures.md 改訂** — 選択状態（accent アウトライン）・パネルの構成・コピー導線が読み順の最後にのみ置かれる理由を design-system.md へ。patterns.md には「Phase 2 で IR は変わらない。ask を書けば回収はビルドと固定 JS が担う」ことを追記。
- [ ] **Step 4: CLAUDE.md 改訂** — アーキテクチャ節（ビルドパイプライン・検査の説明）へ decision-panel と digest 照合を追加し、ゼロ依存不変の段落を「規約」節へ追加。
- [ ] **Step 5: 全テストパス確認** — Run: `python3 -m pytest tests -q` / Expected: PASS。旧記述の残存を `grep -rn "Playwright" SKILL.md references/ CLAUDE.md` 等で確認（ヒットは逸脱記録の文脈のみ許可）。
- [ ] **Step 6: Commit**（分割可: `docs(ve): rebuild example with decision panel` ＋ `docs(ve): document decision collection and the zero-dependency invariant`）

**done_criteria:** 見本が回収パネル付きで再生成され check.sh PASS。SKILL.md / CLAUDE.md / references が Phase 2 の挙動と一致し、ゼロ依存不変が CLAUDE.md に明文化されている。

---

### Task 8: 手動ブラウザ QA（7 シナリオ × file:// / http://）

**実行者は人間（利用者）。** エージェントは QA 手順書と記録テンプレートを用意し、実施結果を受領して記録を確定する。Playwright 廃止（spec 逸脱）の代替として Phase 2 完了ゲートに組み込まれる。

**Files:**
- Create: `.runs/decision-doc-v3-p2/qa/qa-checklist.md`（手順書＋記録テンプレート）
- Create: `.runs/decision-doc-v3-p2/qa/2026-MM-DD-manual-qa.md`（実施記録。実施日で命名）

**Interfaces:**
- Consumes: Task 7 の `examples/example-proposal.html`（回収パネル付き見本）と Task 5 のバインダ挙動（選択・メモ・コピー・縮退）。
- Produces: 全 14 項目（7 シナリオ × file:// / http://）の PASS/FAIL 記録。Task 9 の Step 7 がこの記録の存在と全 PASS を完了条件として参照する。

**Steps:**
- [ ] **Step 1: QA 手順書を書く** — 対象は Task 7 の `examples/example-proposal.html`（decision ask 2 件以上を含む版。1 件しか無ければ QA 用 IR を `.runs/decision-doc-v3-p2/qa/` にビルドして併用）。各シナリオに操作手順・期待結果を明記:
  1. 複数 ask の選択・変更・再読み込み後の復元
  2. キーボードのみで選択・メモ・コピーまで到達（Tab 順が読み順、`aria-pressed` が読み上げに反映、選択ボタンの名前が「この案を選ぶ（<選択肢ラベル>）」で選択肢ごとに読み分けられる。r1 I5）
  3. クリップボード成功時のステータス表示／拒否時の `panel-copy-fallback` 表示と手動コピー（拒否の再現: Chrome は `chrome://settings/content/clipboard` で対象サイトをブロック、または DevTools なしで file:// の `navigator.clipboard` が使えない環境を利用）
  4. localStorage 例外時に選択が機能し永続化のみ失われる（**確実な再現手順**（r1 I3）: Firefox で `about:config` → `dom.storage.enabled` を `false` → 資料を再読み込み。`localStorage` アクセスが例外になり、バインダの try/catch 縮退経路に入る。file:// / http:// の両方でこの方法が使える。確認後は必ず `true` へ戻す。補助的に Chrome では `chrome://settings/content/siteData`（サイトのデータ保存をブロック）で http://localhost 側を再現できる）
  5. JS 無効時に ask が既定案つき静的表示（選択肢・メモ欄・既定案マーク）・パネルが要約表示（問い・未選択 status・全体メモ欄）として読める
  6. 日本語・改行・長文メモのコピー結果をペースト先で逐語照合
  7. 選択肢を変更して再生成した文書（option id を 1 つ変えて再ビルド）で古い選択が復元されない
- [ ] **Step 2: 両プロトコルで実施** — file:// は直接開く。http:// は `cd <資料のあるディレクトリ> && python3 -m http.server 8000`（標準ライブラリ・開発時のみ・実施後停止）で `http://localhost:8000/...` を開く。7 シナリオ × 2 プロトコル = 14 セルの結果（PASS/FAIL＋気づき）を記録テンプレートに記入する。
- [ ] **Step 3: FAIL があれば修正タスクへ戻す** — 該当タスク（Task 4/5 が主）へ戻り修正→再 QA。全 PASS まで Task 9 へ進まない。
- [ ] **Step 4: 記録を確定** — 実施記録に実施日・ブラウザ名/バージョン・対象ファイルの git commit hash を記載して保存。

**done_criteria:** `.runs/decision-doc-v3-p2/qa/` に手順書と実施記録が存在し、**7 シナリオ × file:// / http:// の全 14 項目が PASS**（手動 QA 7 シナリオ PASS が Phase 2 完了の必須条件）。

---

### Task 9: 全体検証（Phase 2 完了ゲート）

- [ ] **Step 1: 全テスト** — Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q` / Expected: 全件 PASS（Phase 1 基準 672 件＋Phase 2 追加分）
- [ ] **Step 2: JS 純関数テストの非スキップ実行** — Run: `python3 -m pytest tests/test_decision_engine_js.py -v` / Expected: 全ケース PASSED（**SKIPPED が 1 件でもあればゲート不通過**。node を用意して再実行）
- [ ] **Step 3: selftest** — Run: `bash skills/visual-explain/scripts/check.sh --selftest` / Expected: `selftest: N passed, 0 failed`（N = 29 ＋ Phase 2 追加分）
- [ ] **Step 4: 見本検証** — Run: `bash skills/visual-explain/scripts/check.sh skills/visual-explain/examples/example-proposal.html` / Expected: PASS。パネル・digest・option-id の存在を grep で確認。
- [ ] **Step 5: skeleton 差分の意図確認** — Run: `git diff main -- skills/visual-explain/assets/skeleton.html` を目視し、差分が「CSS 追加ブロック＋固定 JS 2 ブロック追加」のみで、既存のテーマ/コネクタ/ステッパー JS と既存 CSS 行に変更が無いことを確認（Phase 1 の「skeleton 不変」ゲートは Phase 2 では「意図した追加のみ」ゲートに置き換わる）。
- [ ] **Step 6: T07 クローズ確認** — 単独 CR 入り markup の挿入位置テストと `xlink:href` 外部リンク拒否テストが PASS していることを個別に確認（`python3 -m pytest tests/test_external_links.py -v`）。
- [ ] **Step 7: 手動 QA 記録の確認** — `.runs/decision-doc-v3-p2/qa/` の実施記録が全 14 項目 PASS・commit hash 付きで存在することを確認（Task 8 の done_criteria）。
- [ ] **Step 8: Commit / PR** — draft PR を作成し、Phase 1 と同様の完了報告（テスト件数・selftest 件数・QA 記録パス・skeleton 差分の要約・spec 逸脱の明記）を添えてレビューへ回す。

**done_criteria:** Step 1-7 の全証跡が揃い、draft PR が作成されている。

---

## 開放質問（採用済み解釈の記録 — 転送不要）

計画作成中に spec の解釈が必要になった点。いずれも spec 内の他記述から解決可能と判断し、下記の解釈を採用した。**Pi への転送が必要な未解決事項はない。**

1. **パネル生成条件**: spec 106 行目「回収パネルは ask が 1 個以上あるときだけ生成」と 52 行目「request / hypothesis は回収パネルには入らない」「回収対象は decision のみ」を合わせ、**decision ask が 1 個以上のときだけ生成**（request / hypothesis のみの資料にはパネルを出さない）と解釈した。
2. **コピー出力の `<ファイルパス>`**: ビルド時の `--output` 引数を逐語で `data-ve-document-path` に埋め込み、コピー出力はこれを使う（spec 117 行目どおり・逸脱なし）。r1 C4 を受けて当初の `window.location.href` 案は**撤回**した。相対 `--output` は相対のまま埋め込むため、コミットされる fixture / example は機械間で再現可能（実運用は SKILL.md が絶対パス指定を指示済み）。
3. **node 不在環境**: JS 純関数テストは `skipUnless(node)` でローカル実行を妨げないが、**Task 9 の完了ゲートでは非スキップ実行を必須**とした（spec の「実ブラウザ自動テストを完了条件とする」の代替を骨抜きにしないため）。
4. **契約検査の適用範囲**: `data-ask-option-id` 必須化は破壊的変更ポリシーに従い全 decision ask ブロック（compatibility 節の legacy ask を含む）へ一律適用。ただし**回収・digest の対象は typed ask wrapper のみ**（legacy ask は静的表示のまま）。

## Self-Review 済みメモ

- spec の Phase 2 項目（ask 選択 UI・末尾回収パネル・固定 JS・localStorage 永続化・既定案非選択の原則・コピー出力の構造化ブロック・クリップボード/ストレージ縮退・無操作の不変条件・受入テスト）は Task 2-8 で全て対応する。spec のテスト戦略のうち Playwright だけが人間承認済みの逸脱で、本計画「spec 逸脱」節と Task 4/8 が代替を定義する。skeleton 改定→fixture 全数再生成（spec 141 行目「最大の機械的コスト」）は Task 5 に隔離した。code / image / freeform / CSP は Phase 3 であり、この計画に**含めない**。
- 型・名前の整合を確認済み: `compute_ask_digest_from_pairs`（Task 2 定義 → Task 3 埋め込み → Task 6 照合で同名使用）、`data-ask-option-id` / `data-ask-memo`（Task 2 レンダラ → Task 5 バインダ → Task 6 収集・契約検査）、`data-ve-panel-ask` / `data-ve-panel-status` / `data-ve-panel-memo` / `data-ve-panel-global-memo` / `data-ve-document-path`（Task 3 静的 markup → Task 5 バインダ → Task 6 自己表明検査）、`document_path` の受け渡し（Task 3 `build_to_path` → `build_document` → `render_decision_panel` → Task 4/5 の contract.documentPath）、engine API 8 関数（Task 4 定義 → Task 5 バインダ呼び出し: `emptyState` / `storageKey` / `restoreState` / `serializeState` / `selectOption` / `setMemo` / `setGlobalMemo` / `formatCopyText`）。
- 診断文言は例示であり、実装時に既存文言のトーン（です・ます調の指示形）へ揃えること。文言を変えたらテスト・selftest 期待値も同時に更新する。
- タスク順序の依存: Task 2（option-id・digest）→ Task 3（パネル）→ Task 5（skeleton バインダ）→ Task 6（検査群③）の順に契約が積み上がる。Task 4（エンジン正本）は Task 5 の埋め込みの前提。Task 1（T07）は独立で先頭。Task 7 の見本再生成は Task 5 の skeleton 確定後でないと固定領域が合わない。
- バインダはモデル生成 markup を信頼しない設計にした: contract は data 属性からのみ組み立て、digest はビルド時計算値を使い、narrative / freeform は予約 class（`decision-panel`）と予約 data 属性（`data-ve-*` / `data-ask-*`）の禁止でパネル偽装・選択 UI 偽装ができない（Phase 1 の不変条件＋Task 3 の予約 class 追加＋Task 6 の digest 照合）。
- Task 5 のバインダ JS はテーマトグルと同じく `try/catch` で storage / clipboard 不可へ縮退し、JS 例外が文書の可読性を壊さない（バインダ全体が panel 不在時に早期 return）。`?.` 使用は既存 skeleton の構文水準（アロー関数・テンプレートリテラル）と同世代であり問題ない。
- 検証アーティファクトの置き場: Phase 2 の追加分はすべて `.runs/decision-doc-v3-p2/`（QA 記録は `qa/`）。Phase 1 の `.runs/decision-doc-v3-p1/` と `scripts/tests/structure-bad-*.html` は保持し変更しない（Phase 2 の新 bad fixture は `structure-bad-panel-*.html` として追加）。

---

## レビュー r1 反映記録

ADOPTED:
- C1: ask のメモ欄をレンダラの静的 markup（`data-ask-memo` つき textarea）へ移動し、checker 契約（decision にちょうど 1 つ）とテストで固定。JS はバインドのみで textarea を生成しない（Task 2 / 3 / 5 改訂）
- C2: 回収パネルへ ask ごとのメモ表示（`data-ve-panel-memo`・静的は hidden）と静的な全体メモ欄（`data-ve-panel-global-memo`）を追加し、バインダの render() がメモ入力と同期。静的・動的双方のテストを明記（Task 3 / 5 改訂）
- C3: `formatCopyText` を全 ask 出力へ変更（未選択は spec 111 行目の「→ 選択: 未選択（既定案: X）」、`→ メモ:` 行は trim 後非空のときのみ）。完全一致テスト 2 件＋空メモ非出力テストを Task 4 に実コードで記載
- C4: `window.location.href` 案を撤回。ビルド時 `--output` を `data-ve-document-path` へ逐語埋め込みし、コピー出力の `<ファイルパス>` に使用（spec 117 行目どおり・新規逸脱なし。Task 3 / 4 / 5 / 6 / 7 改訂）
- I1: Task 4 をドライバ→RED テスト全文→失敗確認→GREEN 実装の順へ再構成し、10 テストケースの実コードを plan に記載（placeholder 排除）
- I2: digest 直列化を JSON canonical encoding（`json.dumps` + separators）へ変更し、境界文字（`,` `=`）の非衝突テストを追加
- I3: localStorage 例外 QA の確実な再現手順（Firefox `about:config` → `dom.storage.enabled=false`、Chrome の siteData ブロック併記）を Task 8 とテスト戦略表に明記
- I4: Task 7 Step 1 の build / check コマンドをリポジトリルート起点の単一 cwd へ統一
- I5: 選択ボタンの可視テキストを「この案を選ぶ（<選択肢ラベル>）」とし accessible name を一意化（WCAG 2.5.3）。QA シナリオ②に読み分け確認を追加

REJECTED:
- なし

STATUS: complete

## レビュー r2 反映記録

ADOPTED:
- C1': 検査群③（`document_checks.py`）が `data-ve-section-kind` / `data-ve-ask-type` を `<section>` 限定、`data-ve-panel-ask` を `<li>` 限定として検証していなかった。compatibility セクションは `forbid_reserved=False`（意図的・provenance 追跡前提）により予約 data 属性の禁止対象外なので、正しく閉じた `<div data-ve-section-kind="decision-panel" ...>` を compatibility markup に紛れ込ませると、IR ビルド（`build_document`）・最終 HTML 再検査（`check_final_document`）の両経路をすり抜けていた（`_StructureParser` が `<section>` 以外の要素を構造ノードとして追跡しないため）。一方 skeleton の JS バインダは `document.querySelector('[data-ve-section-kind="decision-panel"]')` のようにタグ非限定の属性セレクタでパネルを取得しており、実ブラウザでは spoof した div が実際にライブパネルとしてマッチしてしまう非対称があった。`_StructureParser` に構造予約属性のタグ限定チェックを追加し、指定タグ以外での出現を `DOCUMENT_STRUCTURE_VIOLATION` で fail-closed（自己閉じタグ検知と同じ早期 return の優先度）。RED（違反が素通りする）→ 実装 → GREEN（IR path・最終 HTML path 双方で FAIL する）の回帰テスト2件を `test_document_checks.py` に追加。対称化として skeleton.html バインダの該当 `querySelector`/`querySelectorAll` を `section[data-ve-section-kind=...]` / `li[data-ve-panel-ask]` へタグ限定し、`decision_engine.js`（source of truth）のコメントも追従、fixture 一括 resplice（`tests/tools/resplice.py` ＋ `KEEP_AS_IS` 6件の手動テキスト置換＋`examples/example-proposal.html`）で固定領域を揃えた。

REJECTED:
- なし

STATUS: complete
