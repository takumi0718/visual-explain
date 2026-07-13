# McKinsey 流ビジュアル標準 v3 実装計画（レビュー反映 rev.2）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** canonical 12 形式（既存 10＋bars/kpi 昇格）の視覚層を McKinsey 流（固定紺パレット・角丸なし・エルボー/レール接続契約・waterfall SVG 化）へ `@2` として一括リスタイルする。

**Architecture:** 骨格に図解専用トークン `--dg-*` を追加し、各コンポーネントの CSS/レンダラ/checker 契約を `@2` へバージョンアップする。品質フロア（固定領域バイト一致・四層検証・fail-closed）は不変。見た目の正はコミット済みモック `.visual-explain/2026-07-13-mckinsey-restyle-candidates-mock.html`、規範は spec `docs/superpowers/specs/2026-07-13-mckinsey-restyle-design.md`。

**Tech Stack:** Python 3.14（stdlib のみ・pytest）、素の CSS、renderer 生成 SVG。外部ライブラリ追加なし。

## Global Constraints

- 骨格の固定領域・テーマ JS・CSP は変更しない（トークン追加は `:root`/dark ブロック内のみ。skeleton 変更時は `test_skeleton_audit.py`・resplice・KEEP_AS_IS 6 ファイルへの手動反映を同一タスクで行う）。
- パレットは spec のトークン表の値をそのまま使う。CSS に生の色値を書かない（`#fff` も `var(--dg-on-primary)` を使う）。
- 図形コンポーネント CSS に `border-radius`（kpi リング円の `50%` のみ例外）・アニメーション・新フォントを書かない。**matrix.css / flow.css の margin/padding/gap は `0 | var(--space-1..7) | auto` のみ**（`test_component_css_spacing_on_grid` が強制。他 CSS も可能な限り `--space-*` へ丸める）。
- CSS 資産を変更したら `shasum -a 256` で digest を再計算し `registry.json` を厳密値で更新する。**同時に、その CSS を styles スロットへ digest 付きで埋め込んでいる当該コンポーネントの全 HTML/JSON フィクスチャ（`*-doc.html`, `catalog.html`, `component-valid-*.json`, `component-bad-*` の該当分, `component-valid-mixed.json`）を再生成する**（resplice は骨格領域しか直さない。埋め込み CSS・digest・`data-ve-contract-version` は再ビルドで更新する）。
- **テストの流儀**: レンダラテストは unittest ベース。IR は JSON フィクスチャ＋`render_fixture(name)`（例 `test_enumeration_renderer.py:22`）または `_base_ir(**overrides)`（例 `test_slope_renderer.py:25`）で作る。`make_*_ir` というヘルパは存在しない。検証違反は `ValidationError` ではなく **`ContractError`（diagnostics.py:138-153）＋ diagnostic code** で、`expect_violation(ir, code)`（test_slope_renderer.py:62）の型で判定する。本計画のテスト例はこの流儀へ読み替えて書くこと。
- **診断コードは閉集合**: 新しい検査を足すときは `diagnostics.py` の `ALL_CODES`（diagnostics.py:77-118）へコードを登録し、`Diagnostic(code=..., message=..., path=...)` で構築する（`rule=` 引数は存在しない）。registry の `checkerRules` に新規則名を書くときは `registry.py:34-55` の `KNOWN_CHECKER_RULES` への追加が必須（違反は `UNKNOWN_CHECKER_RULE`）。
- **version bump の遷移**: Task 2 で `component-ir.schema.json` の `contractVersion` enum を `[1]`→`[1, 2]` へ広げ（`test_component_contract.py:87-88` が schema enum == vocabulary contractVersion 集合を強制するため、vocabulary 側と同時に）、形式ごとのタスクで当該コンポーネントだけ 2 へ bump、**Task 16 で全形式完了を確認して `[2]` へ絞る**。`selection.version == 1` をハードコードした既存テスト（test_component_contract.py:43,54、test_component_selection.py:53、各レンダラテストの IR 例）は当該タスクで更新する。
- 確度語彙は「確認済み / 推論 / 未確認」の 3 語のみ。文中強調は 1 説明文に `dg-em` 最大 1 個。teal ハイライトは 1 図 1 箇所。
- 各タスクの最後に `python3 -m pytest tests/ -q`（`skills/visual-explain/scripts/` で実行）と、有効フィクスチャ 1 つ以上での `bash scripts/check.sh` PASS を維持する。
- コミットは Conventional Commits。タスクごとに最低 1 コミット。作業ブランチ: `feat/mckinsey-restyle-v3`（main 直コミット禁止。完了後 draft PR、merge はユーザー判断）。

## File Structure（今回触るもの）

```
skills/visual-explain/
  assets/skeleton.html                      … :root/dark に --dg-* / --radius 追加（Task 1）
  assets/components/<comp>.css              … 12 形式の CSS 全面書換（Task 4-14）
  assets/components/registry.json           … version 2 / renderer @2 / digest 更新（各タスク）
  references/component-vocabulary.json      … contractVersion 2 / bars・kpi 追加
  references/component-ir.schema.json       … title/unitLabel/descriptionEmphasis/highlightId/bars/kpi
  references/assembly.schema.json           … enum 同期
  references/design-system.md, patterns.md  … 規範文書の同期（Task 15）
  scripts/ve_components/diagnostics.py      … 新診断コードの ALL_CODES 登録（Task 3, 6, 13）
  scripts/ve_components/model.py            … 共通フィールド追加・確度語彙定数（Task 2）
  scripts/ve_components/checker.py          … notation 規則・viewBox マップ・_check_*_artifact 改修（Task 3-14）
  scripts/ve_components/registry.py         … KNOWN_CHECKER_RULES 追加（Task 6, 12, 13）
  scripts/ve_components/renderers/*.py      … 各レンダラ改修＋bars.py / kpi.py 新設
  scripts/ve_components/renderers/__init__.py … TRUSTED_RENDERERS の @2 化（Task 4-14 各タスク）
  scripts/tests/test_*_renderer.py          … 各レンダラの期待更新＋新規 2 本
  scripts/tests/*.html, *.json              … フィクスチャの再生成（各タスク）＋resplice（Task 1）
```

実行前に `superpowers:using-git-worktrees` で worktree を作り、`git checkout -b feat/mckinsey-restyle-v3`。

---

### Task 1: 骨格トークン（--dg-* / --radius）追加と監査同期

**Files:**
- Modify: `skills/visual-explain/assets/skeleton.html`（`:root` と dark ブロックのみ）
- Modify: `skills/visual-explain/scripts/tests/test_skeleton_audit.py`
- Modify: resplice 対象の全フィクスチャ＋KEEP_AS_IS 6 ファイル
- Test: `skills/visual-explain/scripts/tests/test_skeleton_audit.py`

**Interfaces:**
- Produces: CSS カスタムプロパティ `--dg-primary, --dg-primary-mid, --dg-primary-light, --dg-highlight, --dg-negative, --dg-neutral, --dg-line, --dg-emphasis, --dg-on-primary, --radius`（後続全タスクが参照）と skeleton 内の `.dg-em` 記法規則。

- [ ] **Step 1: 失敗するテストを書く** — `test_skeleton_audit.py` に追加（骨格テキストは既存の読み込み済み定数 `SKELETON`（test_skeleton_audit.py:5）を使う）:

```python
DG_TOKENS = [
    "--dg-primary:", "--dg-primary-mid:", "--dg-primary-light:",
    "--dg-highlight:", "--dg-negative:", "--dg-neutral:",
    "--dg-line:", "--dg-emphasis:", "--dg-on-primary:", "--radius:",
]

def test_skeleton_defines_diagram_tokens_in_all_theme_blocks():
    for token in DG_TOKENS:
        assert SKELETON.count(token) >= 3, f"{token} は light / @media dark / [data-theme=dark] に必要"

def test_skeleton_defines_dg_em_rule():
    assert ".dg-em" in SKELETON and "var(--dg-emphasis)" in SKELETON
```

さらに WCAG コントラスト検査 `PAIRS`（test_skeleton_audit.py:80-86）へ dg の組合せを追加: light/dark それぞれで（`--dg-primary` × `--dg-on-primary`）（`--dg-primary-light` × `--text`〔light は `#1a1d21`〕）（`--dg-negative` × `#ffffff`）。既存 PAIRS の書式に合わせて記述する。

- [ ] **Step 2: 失敗確認** — `cd skills/visual-explain/scripts && python3 -m pytest tests/test_skeleton_audit.py -k "dg or contrast" -v` → FAIL。

- [ ] **Step 3: skeleton に spec の表のとおり実装** — light `:root` に:

```css
      --radius: .4rem;
      --dg-primary: #1F4E79; --dg-primary-mid: #2E6DA4; --dg-primary-light: #BDD7EE;
      --dg-highlight: #2E8B9A; --dg-negative: #C55A11; --dg-neutral: #F2F2F2;
      --dg-line: #7F7F7F; --dg-emphasis: #2E75B6; --dg-on-primary: #ffffff;
```

dark（`@media (prefers-color-scheme: dark)` 内と `:root[data-theme="dark"]` の両方）に:

```css
      --radius: .4rem;
      --dg-primary: #2E5A8F; --dg-primary-mid: #3E77B4; --dg-primary-light: #274664;
      --dg-highlight: #3FA3B4; --dg-negative: #E07B39; --dg-neutral: #262b31;
      --dg-line: #9aa1ab; --dg-emphasis: #6FA8DC; --dg-on-primary: #f2f5f9;
```

`<style>` の記法セクションに 1 行追加: `.dg-em { color: var(--dg-emphasis); font-weight: 700; }`
コントラストが PAIRS 検査を満たさない組があれば、**色相を保ったまま明度のみ**調整し、確定値を spec のトークン表に反映する。

- [ ] **Step 4: フィクスチャの骨格領域を更新** — 3 系統すべて:
  1. `python3 tests/tools/resplice.py`（引数なし＝ `scripts/tests/*.html` 一括。`--help` は実装されていない）
  2. `python3 tests/tools/resplice.py ../examples/example-proposal.html`（明示引数）
  3. **KEEP_AS_IS 6 ファイル**（resplice.py:22-27 でスキップされる、骨格 CSS を埋め込む 6 件）へ、docstring（resplice.py:7-10）の指示どおり同じ CSS 差分をテキスト置換で手動適用。

- [ ] **Step 5: 全テスト＋check.sh 通過確認** — `python3 -m pytest tests/ -q` → 全 PASS。`bash ../scripts/check.sh $(pwd)/tests/valid-system.html --type system` → PASS。

- [ ] **Step 6: Commit** — `git add -A && git commit -m "feat(skeleton): add --dg-* diagram tokens, --radius, .dg-em notation"`

---

### Task 2: モデル共通拡張と確度語彙の中央化

**Files:**
- Modify: `scripts/ve_components/model.py`、`scripts/ve_components/validation.py`
- Modify: `scripts/ve_components/renderers/*.py`（`_CERT_LABEL` の置換のみ・全 10 ファイル）
- Modify: `references/component-ir.schema.json`（contractVersion enum `[1, 2]` 化＋共通 optional フィールド）、`references/assembly.schema.json`、`references/component-vocabulary.json`
- Test: `scripts/tests/test_v2_core.py`

**Interfaces:**
- Produces: `model.CERTAINTY_LABEL = {"confirmed": "確認済み", "inferred": "推論", "unverified": "未確認"}`（全レンダラが import）。IR optional フィールド `unit_label` / `title`（定量系 payload: slope/waterfall/bars 用。この時点では optional、各コンポーネントタスクで必須化）、`description_emphasis`（enumeration/chevron item）、`highlight_id`（stairs/bars/matrix/slope）。スキーマ camelCase: `unitLabel` / `title` / `descriptionEmphasis` / `highlightId`。

- [ ] **Step 1: 失敗するテストを書く** — `test_v2_core.py` に追加:

```python
from ve_components.model import CERTAINTY_LABEL

def test_certainty_label_uses_design_system_vocabulary():
    assert CERTAINTY_LABEL == {
        "confirmed": "確認済み", "inferred": "推論", "unverified": "未確認",
    }

def test_no_renderer_defines_local_cert_label():
    import pathlib
    for path in pathlib.Path("ve_components/renderers").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert '"confirmed": "確定"' not in text, path.name

def test_schema_allows_contract_version_two():
    import json
    schema = json.loads(Path("../references/component-ir.schema.json").read_text())
    # 移行期間: [1, 2]。Task 16 で [2] へ絞る
    assert 2 in schema["$defs"]["selection"]["properties"]["version"]["enum"] \
        or "2" in str(schema)  # 実スキーマの version/contractVersion 定義位置に合わせて特定して書く
```

（最後のテストは実スキーマの `contractVersion`/`version` の定義位置（component-ir.schema.json:59 付近）を確認して正確な参照で書き直すこと。）

- [ ] **Step 2: 失敗確認** — `python3 -m pytest tests/test_v2_core.py -k "vocabulary or cert or contract_version" -v` → FAIL。

- [ ] **Step 3: 実装** — `model.py` に `CERTAINTY_LABEL` を追加し、各レンダラの `_CERT_LABEL = {...}`（slope.py:12 と同型が全レンダラにある）を `from ..model import CERTAINTY_LABEL as _CERT_LABEL` へ置換。model dataclass へ optional フィールド追加、validation.py の camelCase 変換に対応。スキーマ: contractVersion enum を `[1, 2]` へ（vocabulary 側の許容と `test_component_contract.py:87-88` の整合を保つ）、共通 optional フィールドを追加（`additionalProperties: false` 維持）。

- [ ] **Step 4: 図中チップ・notes 語彙の期待更新** — 対象を**チップ/notes に限定**して置換する: `grep -rn '<strong>確定\|<strong>推定\|ve-cert' tests/ ../references/patterns.md` で「`<strong>確定:</strong>`／`<strong>推定:</strong>`」型と `ve-cert` チップ文言だけを「確認済み/推論」へ更新（地の文の「確定する」等は触らない）。

- [ ] **Step 5: 全テスト通過確認** — `python3 -m pytest tests/ -q` → PASS。

- [ ] **Step 6: Commit** — `git commit -am "feat(ve-components): centralize certainty vocabulary, add title/unitLabel/descriptionEmphasis/highlightId"`

---

### Task 3: checker 全域 notation 規則

**Files:**
- Modify: `scripts/ve_components/diagnostics.py`（ALL_CODES へ 3 コード追加）
- Modify: `scripts/ve_components/checker.py`
- Create: `scripts/tests/component-bad-emphasis-overuse.html`, `component-bad-highlight-overuse.html`, `component-bad-certainty-vocabulary.html`
- Test: `scripts/tests/test_component_checker.py`

**Interfaces:**
- Produces: `checker.validate_notation_rules(content: str) -> list[Diagnostic]`（最終文書検査層 checker.py:1489 付近から呼ぶ）。診断コード（ALL_CODES 登録・命名は既存コードの表記慣行に合わせる）: `notation-emphasis-limit`, `notation-highlight-limit`, `notation-certainty-vocabulary`。

- [ ] **Step 1: 失敗するテストを書く** — `test_component_checker.py` に追加（`Diagnostic` は `code/message/path`）:

```python
def test_emphasis_limit_rejects_two_dg_em_in_one_description(self):
    html = ('<p class="ve-enum-desc">Aを<strong class="dg-em">強調1</strong>し'
            '<strong class="dg-em">強調2</strong>する</p>')
    codes = [d.code for d in checker.validate_notation_rules(html)]
    self.assertIn("notation-emphasis-limit", codes)

def test_highlight_limit_rejects_two_highlights_in_one_figure(self):
    html = ('<figure data-ve-component="bars">'
            '<div class="ve-bars-fill ve-dg-highlight"></div>'
            '<div class="ve-bars-fill ve-dg-highlight"></div></figure>')
    codes = [d.code for d in checker.validate_notation_rules(html)]
    self.assertIn("notation-highlight-limit", codes)

def test_certainty_vocabulary_rejects_old_labels(self):
    codes = [d.code for d in checker.validate_notation_rules(
        '<li><strong>確定:</strong> 何か</li>')]
    self.assertIn("notation-certainty-vocabulary", codes)
```

- [ ] **Step 2: 失敗確認** — `python3 -m pytest tests/test_component_checker.py -k notation -v` → FAIL（ALL_CODES 未登録なら `Diagnostic` 構築時 ValueError になることも確認）。

- [ ] **Step 3: 実装** — `diagnostics.py` の `ALL_CODES` に 3 コードを追加し、`checker.py` に:

```python
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
```

（`Diagnostic` の実引数順・`path` の慣行値は diagnostics.py:121-135 と既存呼出しに合わせる。）最終文書検査へ `diagnostics += validate_notation_rules(content)` を追加。`quantitative-unit-required`（unit_label 必須）は validation.py 側に実装し、適用対象は Task 12(waterfall)/13(bars)/11(slope) の各タスクで有効化する。

- [ ] **Step 4: bad フィクスチャ 3 本を作成し FAIL を固定** — 既存 `component-bad-*.html` の作法（valid をコピーして 1 点だけ壊す）を踏襲。

- [ ] **Step 5: 全テスト通過確認** — `python3 -m pytest tests/ -q` → PASS。

- [ ] **Step 6: Commit** — `git commit -am "feat(checker): notation rules (emphasis/highlight limits, certainty vocabulary)"`

---

### 共通手順（Task 4〜14 の各コンポーネントタスクで必ず行う）

以下を各タスクの Step に含める（本文では差分だけ記す）:

1. **checker 契約の同時改修**: 当該コンポーネントの `_check_*_artifact`（checker.py:1398-1407 から全 canonical セクションへ適用される）を新クラス契約へ書き換え、旧クラス名の強制を残さない。対応する `component-bad-*.html` の期待も更新。
2. **バージョン bump 一式**: vocabulary contractVersion=2、registry `version: 2`／`renderer: "<id>@2"`、`renderers/__init__.py` の `TRUSTED_RENDERERS`（renderers/__init__.py:22-33）のキーを `<id>@2` へ、CSS digest 再計算。
3. **フィクスチャ再生成**: 当該コンポーネントの `component-valid-*.json`（`"version": 1`→2）、`*-doc.html`、`catalog.html`・`component-valid-mixed.json` の該当セクション、bad フィクスチャを新契約・新 CSS 埋め込みで再生成。
4. **ハードコード version 期待の更新**: test_component_contract.py:43,54 / test_component_selection.py:53 / 当該レンダラテストの IR 例。
5. `python3 -m pytest tests/ -q` 全 PASS ＋ 当該 doc フィクスチャで `check.sh` PASS。

---

### Task 4: enumeration@2

**Files:**
- Modify: `assets/components/enumeration.css`（全面書換）、`renderers/enumeration.py`、`checker.py`（`_check_enumeration_artifact`、checker.py:739-763）、`validation.py`、registry/vocabulary/TRUSTED_RENDERERS、フィクスチャ一式
- Test: `scripts/tests/test_enumeration_renderer.py`

**Interfaces:**
- Consumes: `--dg-*`（Task 1）、`description_emphasis`（Task 2）。
- Produces: **意味構造は現行の `<ul>`＋`<li class="ve-enum-block">` を維持**し、li 内部を「コンセプト箱＋説明」の 2 領域に再構成: `<div class="ve-enum-concept ve-enum-box">`（紺・白抜き太字）＋`<p class="ve-enum-description ve-enum-desc">`（`・` 始まり。`description_emphasis` があれば該当部分文字列を `<strong class="dg-em">` で 1 回だけ包む）。既存の concept/description クラス（checker が検査）は保持し、新クラスを追加する形にする。

- [ ] **Step 1: 失敗するテストを書く**（`render_fixture` 流儀。新フィクスチャ `component-valid-enumeration.json` に `descriptionEmphasis` を追加）:

```python
def test_enumeration_v2_wraps_emphasis_once(self):
    markup = render_fixture("component-valid-enumeration").markup
    self.assertEqual(
        markup.count('<strong class="dg-em">無料のフィットネス利用券</strong>'), 1)
    self.assertIn('class="ve-enum-concept ve-enum-box"', markup)

def test_enumeration_v2_rejects_emphasis_not_in_description(self):
    # descriptionEmphasis が description の部分文字列でない IR → ContractError
    expect_violation(self, "component-bad-enum-emphasis-missing",
                     "enumeration-emphasis-not-found")
```

（`expect_violation` の実装は test_slope_renderer.py:62 の流儀を enumeration テストへ移植。診断コード `enumeration-emphasis-not-found` は ALL_CODES へ登録。）

- [ ] **Step 2: 失敗確認** — `python3 -m pytest tests/test_enumeration_renderer.py -k v2 -v` → FAIL。

- [ ] **Step 3: レンダラ実装** — description 描画部に:

```python
def _desc_html(text: str, emphasis: str | None) -> str:
    escaped = _esc(text)
    if emphasis:
        needle = _esc(emphasis)
        escaped = escaped.replace(needle, f'<strong class="dg-em">{needle}</strong>', 1)
    return escaped
```

validation.py に「`description_emphasis` は description のいずれかの要素の部分文字列」検査を追加（違反コード `enumeration-emphasis-not-found`）。

- [ ] **Step 4: CSS 全面書換**（モック `.enum-*` の namespaced 化）:

```css
figure[data-ve-component="enumeration"] ul { display: grid; gap: var(--space-4); list-style: none; margin: 0; padding: 0; }
figure[data-ve-component="enumeration"] .ve-enum-block {
  display: grid; grid-template-columns: 13rem minmax(0, 1fr);
  gap: var(--space-3); align-items: center; }
figure[data-ve-component="enumeration"] .ve-enum-box {
  display: grid; place-items: center; min-height: 5.5rem; padding: var(--space-2);
  background: var(--dg-primary); color: var(--dg-on-primary);
  font-size: 1.0625rem; font-weight: 700; text-align: center; line-height: 1.5; }
figure[data-ve-component="enumeration"] .ve-enum-desc {
  margin: 0; padding-left: 1.1rem; text-indent: -1.1rem; }
figure[data-ve-component="enumeration"] .ve-enum-desc::before { content: "・"; }
@media (max-width: 42rem) {
  figure[data-ve-component="enumeration"] .ve-enum-block { grid-template-columns: 1fr; }
}
```

（実際の現行クラス構造 `ve-enum-concept`/`ve-enum-description` を checker ごと確認し、checker.py:739-763 の期待を新レイアウトに合わせて更新。`presentation: "columns"` は同トークンで列方向 grid・説明は下。）

- [ ] **Step 5: 共通手順 1〜5 を実施**（digest 例: `shasum -a 256 assets/components/enumeration.css`）。

- [ ] **Step 6: Commit** — `git commit -am "feat(enumeration): v2 McKinsey restyle with dg tokens and dg-em emphasis"`

---

### Task 5: chevron@2

**Files:**
- Modify: `assets/components/chevron.css`（全面書換）、`renderers/chevron.py`（ループ経路の要素構成）、`checker.py`（`_check_chevron_artifact`、checker.py:766-799 — rail 検査を rail＋tail の 2 要素契約へ）、registry/vocabulary/TRUSTED_RENDERERS、フィクスチャ一式
- Test: `scripts/tests/test_chevron_renderer.py`

**Interfaces:**
- Consumes: Task 1 トークン、Task 2 `description_emphasis`。
- Produces: `li.ve-chevron-step`＋concept/description の意味構造は維持。コンセプトは `.ve-chevron-concept ve-chv-box`（下向き五角形 clip-path）。`loop:true` のとき wrap（`data-ve-loop="true"`）直下に `ve-chevron-loop-rail`（既存クラス名を維持し新スタイル）＋`ve-chevron-loop-tail`（新設）を各 1 個だけ出力（checker は「rail 最大 1」→「rail/tail とも loop 時のみ各 1」へ）。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_chevron_v2_emits_rail_and_tail_only_when_loop(self):
    looped = render_fixture("component-valid-chevron-loop").markup
    plain = render_fixture("component-valid-chevron").markup
    self.assertEqual(looped.count('ve-chevron-loop-rail'), 1)
    self.assertEqual(looped.count('ve-chevron-loop-tail'), 1)
    self.assertNotIn('ve-chevron-loop', plain)
```

- [ ] **Step 2: 失敗確認 → Step 3: レンダラ改修** — renderers/chevron.py:74-87 の既存 rail 出力に tail を追加し、wrap へ `data-ve-loop` 属性。

- [ ] **Step 4: CSS 全面書換** — モック `.chv-*` の namespaced 化。接続契約は spec のとおり「途切れない単一経路」:

```css
figure[data-ve-component="chevron"] [data-ve-loop="true"] {
  position: relative; --chv-cx: 9rem;
  padding-left: 2.5rem; padding-top: 2.3rem; padding-bottom: 1.2rem; }
figure[data-ve-component="chevron"] .ve-chevron-loop-rail {
  position: absolute; left: .5rem; top: .5rem; bottom: .2rem;
  width: calc(var(--chv-cx) - .5rem);
  border: 2.5px solid var(--dg-line); border-right: 0; }
figure[data-ve-component="chevron"] .ve-chevron-loop-rail::before {
  content: ""; position: absolute; top: -2.5px; right: -2.5px;
  height: .95rem; border-right: 2.5px solid var(--dg-line); }
figure[data-ve-component="chevron"] .ve-chevron-loop-rail::after {
  content: ""; position: absolute; top: calc(.95rem - 2.5px); right: -.6rem;
  border: .6rem solid transparent; border-top: .85rem solid var(--dg-line); border-bottom: 0; }
figure[data-ve-component="chevron"] .ve-chevron-loop-tail {
  position: absolute; left: calc(var(--chv-cx) - 1.25px); bottom: .2rem;
  height: 1rem; border-left: 2.5px solid var(--dg-line); }
figure[data-ve-component="chevron"] .ve-chevron-step {
  display: grid; grid-template-columns: 13rem minmax(0, 1fr);
  gap: var(--space-3); align-items: center; }
figure[data-ve-component="chevron"] .ve-chv-box {
  display: grid; place-items: center; min-height: 6.5rem;
  padding: var(--space-2) var(--space-2) 2.2rem;
  background: var(--dg-primary); color: var(--dg-on-primary);
  font-size: 1.0625rem; font-weight: 700; text-align: center; line-height: 1.5;
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 1.9rem), 50% 100%, 0 calc(100% - 1.9rem)); }
figure[data-ve-component="chevron"] .ve-chevron-description {
  margin: 0; padding-left: 1.1rem; text-indent: -1.1rem; }
figure[data-ve-component="chevron"] .ve-chevron-description::before { content: "・"; }
@media (max-width: 42rem) {
  figure[data-ve-component="chevron"] .ve-chevron-step { grid-template-columns: 1fr; }
  figure[data-ve-component="chevron"] [data-ve-loop="true"] { padding-left: 1.8rem; --chv-cx: 50%; }
  figure[data-ve-component="chevron"] .ve-chevron-loop-rail { left: .3rem; width: calc(var(--chv-cx) - .3rem); }
}
```

横型（orientation: horizontal）は右向き五角形で同トークン。

- [ ] **Step 5: 共通手順 1〜5 を実施 → Step 6: Commit** — `git commit -am "feat(chevron): v2 pentagon shape with unbroken loop rail"`

---

### Task 6: matrix@2

**Files:**
- Modify: `assets/components/matrix.css`、`renderers/matrix.py`、`checker.py`（matrix artifact 検査＋`matrix-concept-length` 新規則）、`diagnostics.py`（`matrix-concept-length` コード）、`registry.py`（KNOWN_CHECKER_RULES へ追加）、`component-ir.schema.json`（`presentation` enum）、registry/vocabulary/TRUSTED_RENDERERS、フィクスチャ一式
- Test: `scripts/tests/test_matrix_renderer.py`

**Interfaces:**
- Consumes: Task 1 トークン、Task 2 `highlight_id`。
- Produces: IR optional `presentation: "concept" | "dense"`（default `dense`）。`concept`: `<div class="ve-mx-grid ve-mx-cols-N">`（N=2..4）に `ve-mx-colhead`（紺箱）/`ve-mx-rowhead`（グレー箱）/`ve-mx-cell`（紺アウトライン・中央太字）。`dense`: 既存のセマンティック table 構造を維持し紺見出し＋細横罫。`highlight_id` のセルだけ `ve-dg-highlight`。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_matrix_v2_concept_presentation_renders_boxes(self):
    markup = render_fixture("component-valid-matrix-concept").markup
    self.assertIn('class="ve-mx-colhead"', markup)
    self.assertIn('class="ve-mx-cell"', markup)

def test_matrix_v2_concept_rejects_long_cell_text(self):
    expect_violation(self, "component-bad-matrix-concept-long-cell",
                     "matrix-concept-length")  # セル content 7 文字以上

def test_matrix_v2_highlight_marks_single_cell(self):
    markup = render_fixture("component-valid-matrix-concept").markup
    self.assertEqual(markup.count("ve-dg-highlight"), 1)
```

- [ ] **Step 2: 失敗確認 → Step 3: 実装** — スキーマに `presentation` 追加、validation.py で `concept` 時セル content ≤ 6 文字（違反 `matrix-concept-length`。ALL_CODES と KNOWN_CHECKER_RULES の両方へ登録）。concept のアクセシビリティは既存 matrix 契約（aria-label/visually-hidden 関係リスト）を踏襲。

- [ ] **Step 4: CSS 全面書換** — **余白は必ず `var(--space-*)`**（`test_component_css_spacing_on_grid`〔test_skeleton_audit.py:89-118〕が matrix.css を検査するため）:

```css
figure[data-ve-component="matrix"] .ve-mx-grid { display: grid; gap: var(--space-1); max-width: 34rem; }
figure[data-ve-component="matrix"] .ve-mx-cols-2 { grid-template-columns: 8rem repeat(2, minmax(0, 1fr)); }
figure[data-ve-component="matrix"] .ve-mx-cols-3 { grid-template-columns: 8rem repeat(3, minmax(0, 1fr)); }
figure[data-ve-component="matrix"] .ve-mx-cols-4 { grid-template-columns: 8rem repeat(4, minmax(0, 1fr)); }
figure[data-ve-component="matrix"] .ve-mx-colhead {
  display: grid; place-items: center; padding: var(--space-1);
  background: var(--dg-primary); color: var(--dg-on-primary); font-weight: 700; }
figure[data-ve-component="matrix"] .ve-mx-rowhead {
  display: grid; place-items: center; padding: var(--space-1);
  background: var(--dg-neutral); color: var(--text); font-weight: 700; }
figure[data-ve-component="matrix"] .ve-mx-cell {
  display: grid; place-items: center; padding: var(--space-1);
  border: 1.5px solid var(--dg-primary); font-weight: 700; font-size: 1.0625rem; }
figure[data-ve-component="matrix"] .ve-mx-cell.ve-dg-highlight { background: var(--dg-primary-light); }
figure[data-ve-component="matrix"] .ve-matrix-scroll th {
  color: var(--dg-primary); font-weight: 800; text-align: left;
  border-bottom: 1.5px solid var(--dg-primary); padding: var(--space-1) var(--space-2) var(--space-1) 0; }
figure[data-ve-component="matrix"] .ve-matrix-scroll td {
  border-bottom: 1px solid var(--border); padding: var(--space-1) var(--space-2) var(--space-1) 0; vertical-align: top; }
```

- [ ] **Step 5: 共通手順 1〜5 → Step 6: Commit** — `git commit -am "feat(matrix): v2 concept/dense presentations with navy headers"`

---

### Task 7: flow@2（CSS 主体の改修）

**Files:**
- Modify: `assets/components/flow.css`（v2 リスタイル）、`checker.py`（flow artifact 検査のクラス期待に変更があれば）、registry/vocabulary/TRUSTED_RENDERERS、フィクスチャ一式
- Test: `scripts/tests/test_flow_renderer.py`, `tests/test_flow_layout.py`

**Interfaces:**
- Consumes: Task 1 トークン。
- Produces: **DOM 契約は現状維持**（ラベルは既に矢印直後: renderers/flow.py:88 `<span class="ve-flow-arrow" aria-hidden="true">↓</span>{label}`。右端分離は flow.css:10 の `.ve-flow-link { grid-template-columns: auto 1fr auto }` が原因）。修正は CSS のみ: `.ve-flow-link` を `grid-template-columns: auto auto 1fr` へ変え、ラベルを矢印の隣に寄せる。ノード既定=紺塗り白抜き、中間状態（muted tone）=白抜き紺枠。レール 2.5px `var(--dg-line)`。

- [ ] **Step 1: 失敗するテストを書く**（CSS 資産のアサーション）:

```python
def test_flow_v2_css_keeps_edge_label_adjacent(self):
    css = Path("../assets/components/flow.css").read_text(encoding="utf-8")
    self.assertIn("auto auto 1fr", css)          # ラベルを矢印隣へ
    self.assertIn("var(--dg-primary)", css)      # 紺ノード
    self.assertNotIn("auto 1fr auto", css)       # 旧・右端分離の廃止
```

- [ ] **Step 2: 失敗確認 → Step 3: CSS 書換** — 余白は `var(--space-*)` のみ（spacing 監査対象）。ノード塗り: `.ve-flow-node { background: var(--dg-primary); color: var(--dg-on-primary); }`、tone=muted は `background: var(--bg); color: var(--text); border: 1.5px solid var(--dg-primary);`。矢印・レール色は `var(--dg-line)`。

- [ ] **Step 4: 共通手順 1〜5（レンダラ変更なしでも version bump とフィクスチャ再生成は行う）→ Step 5: Commit** — `git commit -am "feat(flow): v2 navy nodes, arrow-adjacent labels via CSS grid fix"`

---

### Task 8: pyramid@2

**Files:**
- Modify: `assets/components/pyramid.css`（全面書換）、`renderers/pyramid.py`（level クラス出力）、`checker.py`（`_check_pyramid_artifact`、checker.py:802-847 — `ve-pyramid-face-strong/dim` 強制を `ve-pyramid-level-K` 契約へ書換）、registry/vocabulary/TRUSTED_RENDERERS、フィクスチャ一式
- Test: `scripts/tests/test_pyramid_renderer.py`

**Interfaces:**
- Produces: **`<ul class="ve-pyramid-tiers ve-pyramid-count-N">`＋`<li class="ve-pyramid-tier ve-pyramid-index-K ve-pyramid-level-K">` の ul/li 構造を維持**（checker の index 検査と両立）。face クラス（strong/dim）は level クラスへ置換。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_pyramid_v2_emits_level_classes(self):
    markup = render_fixture("component-valid-pyramid").markup
    for k in (1, 2, 3):
        self.assertIn(f"ve-pyramid-level-{k}", markup)
    self.assertNotIn("ve-pyramid-face-strong", markup)

def test_pyramid_css_prevents_one_char_wrap(self):
    css = Path("../assets/components/pyramid.css").read_text(encoding="utf-8")
    self.assertNotIn("fit-content", css)
    self.assertIn("white-space: nowrap", css)
    self.assertIn("min-width: max-content", css)
```

- [ ] **Step 2: 失敗確認 → Step 3: CSS 全面書換**:

```css
figure[data-ve-component="pyramid"] .ve-pyramid-tiers {
  display: grid; gap: 3px; width: min(100%, 24rem);
  margin-inline: auto; justify-items: center; list-style: none; padding: 0; }
figure[data-ve-component="pyramid"] .ve-pyramid-tier {
  display: grid; place-items: center; padding: var(--space-1) var(--space-2);
  font-weight: 700; white-space: nowrap; min-width: max-content; }
figure[data-ve-component="pyramid"] .ve-pyramid-level-1 { width: 40%; background: var(--dg-primary); color: var(--dg-on-primary); }
figure[data-ve-component="pyramid"] .ve-pyramid-level-2 { width: 70%; background: var(--dg-primary-mid); color: var(--dg-on-primary); }
figure[data-ve-component="pyramid"] .ve-pyramid-level-3 { width: 100%; background: var(--dg-primary-light); color: var(--text); }
figure[data-ve-component="pyramid"] .ve-pyramid-count-4 .ve-pyramid-level-3 { width: 85%; }
figure[data-ve-component="pyramid"] .ve-pyramid-count-4 .ve-pyramid-level-4 { width: 100%; background: var(--dg-neutral); color: var(--text); }
```

- [ ] **Step 4: レンダラ・checker 同時改修 → Step 5: 共通手順 1〜5 → Step 6: Commit** — `git commit -am "feat(pyramid): v2 fixed-width tiers, nowrap labels, navy gradation"`

---

### Task 9: stairs@2

**Files:**
- Modify: `assets/components/stairs.css`、`renderers/stairs.py`、`checker.py`（`_check_stairs_artifact`、checker.py:850-912 — accent/note 契約を highlight/here 契約へ）、registry/vocabulary/TRUSTED_RENDERERS、フィクスチャ一式
- Test: `scripts/tests/test_stairs_renderer.py`

**Interfaces:**
- Consumes: Task 2 `highlight_id`（現在地）。既存 IR の現在地指定（`ve-stairs-tread-accent` を生む accent 指定）を `highlight_id` へ移行し、旧指定はスキーマから除去。
- Produces: `<ol class="ve-stairs-stages">`＋`li.ve-stairs-stage ve-stairs-index-K` は維持。段の状態クラス: 到達済み `ve-stairs-done`（紺）/現在地 `ve-dg-highlight`（teal＋`<span class="ve-stairs-here">← 現在地</span>`）/未到達 `ve-stairs-todo`（neutral）。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_stairs_v2_marks_current_with_highlight_and_here_label(self):
    markup = render_fixture("component-valid-stairs").markup
    self.assertEqual(markup.count("ve-dg-highlight"), 1)
    self.assertIn("← 現在地", markup)
    self.assertIn("ve-stairs-done", markup)
    self.assertIn("ve-stairs-todo", markup)
```

- [ ] **Step 2: 失敗確認 → Step 3: 実装** — highlight_id より前=done、当該=highlight、後=todo。CSS はモック `.stairs` の namespaced 化（min-height 3〜8.6rem の 5 段・`gap: 3px`・`display: flex; align-items: flex-end`）。
- [ ] **Step 4: 共通手順 1〜5 → Step 5: Commit** — `git commit -am "feat(stairs): v2 ascending steps with teal current marker"`

---

### Task 10: logic-tree@2（エルボー接続契約）

**Files:**
- Modify: `assets/components/logic-tree.css`（全面書換）、`renderers/logic_tree.py`（構造書換）、`checker.py`（`_check_logic_tree_artifact`、checker.py:1044-1145 — spine/root-stem/connector 数の旧契約を `ve-lt-*` 入れ子契約へ全面書換）、registry/vocabulary/TRUSTED_RENDERERS、フィクスチャ一式
- Test: `scripts/tests/test_logic_tree_renderer.py`

**Interfaces:**
- Produces: 出力契約（fig-7 文法・spec の接続契約 (a)〜(d)）:

```html
<div class="ve-lt">
  <div class="ve-lt-node ve-lt-root">…</div>
  <div class="ve-lt-stub"></div>
  <div class="ve-lt-children">
    <div class="ve-lt-child">
      <div class="ve-lt-node ve-lt-branch">…</div>
      <div class="ve-lt-stub"></div>
      <div class="ve-lt-children">
        <div class="ve-lt-child"><div class="ve-lt-node ve-lt-leaf">…</div></div>
      </div>
    </div>
  </div>
</div>
```

新 checker 契約: root 1・`ve-lt-stub` は「子を持つノード数」と一致・`ve-lt-child` 数 = 枝＋leaf 総数・意味 ID/takeaway/notes は既存契約を維持。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_logic_tree_v2_nests_children_with_elbow_wrappers(self):
    markup = render_fixture("component-valid-logic-tree").markup  # 枝3・うち1枝にleaf1・1枝にleaf2
    self.assertGreaterEqual(markup.count('class="ve-lt-child"'), 6)
    self.assertIn('class="ve-lt-stub"', markup)
    self.assertNotIn("ve-logic-tree-spine", markup)  # 旧スパイン部品の廃止

def test_logic_tree_v2_leafless_branch_has_no_nested_children(self):
    markup = render_fixture("component-valid-logic-tree").markup
    branch = re.search(
        r'<div class="ve-lt-child">(?:(?!ve-lt-child).)*?市場機会.*?</div>',
        markup, re.S).group(0)
    self.assertNotIn("ve-lt-children", branch)
```

- [ ] **Step 2: 失敗確認 → Step 3: レンダラ・checker を上記契約へ書換**。

- [ ] **Step 4: CSS 全面書換**（Task 10 の旧版と同じ内容 — スパイン=最初の子の中心〜最後の子の中心、スタブ幅=インデント幅、only-child はスパインなし）:

```css
figure[data-ve-component="logic-tree"] .ve-lt { display: flex; align-items: center; }
figure[data-ve-component="logic-tree"] .ve-lt-node { padding: var(--space-1) var(--space-2); font-weight: 700; }
figure[data-ve-component="logic-tree"] .ve-lt-root { background: var(--dg-primary); color: var(--dg-on-primary); text-align: center; }
figure[data-ve-component="logic-tree"] .ve-lt-branch { background: var(--dg-primary-mid); color: var(--dg-on-primary); }
figure[data-ve-component="logic-tree"] .ve-lt-leaf {
  border: 1.5px solid var(--dg-line); color: var(--text);
  font-size: var(--fs-figure); font-weight: 400; padding: var(--space-1) var(--space-2); }
figure[data-ve-component="logic-tree"] .ve-lt-stub {
  flex: 0 0 1.5rem; border-top: 2px solid var(--dg-line); align-self: center; }
figure[data-ve-component="logic-tree"] .ve-lt-children { display: flex; flex-direction: column; gap: var(--space-1); }
figure[data-ve-component="logic-tree"] .ve-lt-child {
  position: relative; padding-left: 1.5rem; display: flex; align-items: center; }
figure[data-ve-component="logic-tree"] .ve-lt-child::before {
  content: ""; position: absolute; left: 0; top: 50%; width: 1.5rem;
  border-top: 2px solid var(--dg-line); }
figure[data-ve-component="logic-tree"] .ve-lt-child::after {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0;
  border-left: 2px solid var(--dg-line); }
figure[data-ve-component="logic-tree"] .ve-lt-child:first-child::after { top: 50%; }
figure[data-ve-component="logic-tree"] .ve-lt-child:last-child::after { top: 0; bottom: 50%; }
figure[data-ve-component="logic-tree"] .ve-lt-child:only-child::after { content: none; }
```

- [ ] **Step 5: 共通手順 1〜5 → Step 6: Commit** — `git commit -am "feat(logic-tree): v2 fig-7 elbow connectors, no overshoot/gap by construction"`

---

### Task 10b: evidence-map@2

**Files:** `assets/components/evidence-map.css`、`renderers/evidence_map.py`、`checker.py`（`_check_evidence_map_artifact`、checker.py:1328-1395 — カードクラス改名と枝線契約へ更新。`ve-em-evidence-card` 2〜4・結論・`ve-cert` 1 個/カードの検査は名前を新契約に合わせて維持）、registry/vocabulary/TRUSTED_RENDERERS、フィクスチャ一式。Test: `tests/test_evidence_map_renderer.py`

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_evidence_map_v2_uses_spine_children(self):
    markup = render_fixture("component-valid-evidence-map").markup
    self.assertIn('class="ve-em-body"', markup)
    self.assertIn("ve-em-solid", markup)   # 確認済み=実線の枝
```

- [ ] **Step 2: 失敗確認 → Step 3: 実装** — 結論 `ve-em-conclusion`（紺塗り）、`ve-em-body`（左スパイン）、根拠カード `ve-em-item ve-em-{solid|dashed|dotted}`（certaintyRef 3 値と対応・カード内 `ve-cert` チップは維持）。CSS はモック `.em-*` の namespaced 化＋logic-tree と同じ first/last 端点規則（スパインは最初のカード中心〜最後のカード中心）。
- [ ] **Step 4: 共通手順 1〜5 → Step 5: Commit** — `git commit -am "feat(evidence-map): v2 spine-connected evidence cards"`

---

### Task 11: slope@2（端点結合ラベル・ハイライト・図ヘッダ・allowlist 更新）

**Files:**
- Modify: `renderers/slope.py`、`assets/components/slope.css`、`checker.py`（`RENDERER_SVG_ALLOWLIST`〔checker.py:39〕→ `{"slope@2"}`）、`validation.py`（`quantitative-unit-required` の対象へ slope を追加）、`component-ir.schema.json`（slope payload に `title` 必須追加・`unit`→`unitLabel` 改名）、registry/vocabulary/TRUSTED_RENDERERS、フィクスチャ一式
- Test: `scripts/tests/test_slope_renderer.py`, `scripts/tests/test_renderer_svg_gate.py`

**Interfaces:**
- Consumes: Task 1 トークン、Task 2 `highlight_id` / `unit_label` / `title`。
- Produces: 図ヘッダ `<p class="ve-fig-title">{title}</p><p class="ve-fig-unit">単位: {unit_label}</p>` を figure 冒頭（figcaption の前）に出力。**figcaption は takeaway（ir.caption）として維持**（checker.py:1455 の figcaption 必須と両立）。summary 末尾の `（単位: {unit}）`（slope.py:98）は削除（ve-fig-unit と二重になるため）。系列ラベルは終端値と結合（`{to_value_text} {label}`、`x=490, text-anchor=start`）。中央浮遊ラベル（`x=300`、slope.py:55）廃止。`highlight_id` の系列だけ `ve-slope-tone-highlight`（teal）、他は `ve-slope-tone-default`（紺）。端点 `circle`（r=4。`circle` は許可要素済み、checker.py:41）。

- [ ] **Step 1: 失敗するテストを書く**（`_base_ir(**overrides)` 流儀、test_slope_renderer.py:25）:

```python
def test_slope_v2_merges_series_label_into_endpoint(self):
    ir = _base_ir(highlightId="s1")
    markup = render_ir(ir).markup
    self.assertIn("40件 売上", markup)
    self.assertNotIn('x="300"', markup)

def test_slope_v2_emits_figure_header(self):
    markup = render_ir(_base_ir()).markup
    self.assertIn('class="ve-fig-title"', markup)
    self.assertIn("単位: 件", markup)

def test_svg_gate_accepts_slope_v2_only(self):
    from ve_components.checker import RENDERER_SVG_ALLOWLIST
    self.assertIn("slope@2", RENDERER_SVG_ALLOWLIST)
    self.assertNotIn("slope@1", RENDERER_SVG_ALLOWLIST)
```

- [ ] **Step 2: 失敗確認 → Step 3: 実装** — slope.py:51-56 の出力変更、tone を highlight_id 判定へ、図ヘッダ出力、CSS で `stroke: var(--dg-primary)` / highlight `var(--dg-highlight)` / `.ve-slope-value { font-weight: 700 }`。allowlist を `{"slope@2"}` へ、`test_renderer_svg_gate.py` の `slope@1` 期待を全更新。
- [ ] **Step 4: 共通手順 1〜5 → Step 5: Commit** — `git commit -am "feat(slope): v2 endpoint-merged labels, highlight series, figure header, allowlist slope@2"`

---

### Task 12: waterfall@2（renderer-SVG 全面移行）

**Files:**
- Modify: `renderers/waterfall.py`（全面書換）、`assets/components/waterfall.css`（全面書換・`ve-wf-start-*`/`ve-wf-len-*` 列挙〔waterfall.css:33-234〕を削除）、`ve_components/numeric.py`（座標関数追加・`ROUND_CEILING` import 追加〔現状 numeric.py:4 は ROUND_HALF_UP のみ〕）、`checker.py`（allowlist へ `waterfall@2` 追加・**viewBox のコンポーネント別マップ化**・`rect` の要素/属性 allowlist 追加・`_check_waterfall_artifact`〔checker.py:915-1010〕の CSS 版契約を SVG 版契約へ全面書換）、`diagnostics.py`/`registry.py`（新規則）、`model.py`/スキーマ（`orientation` 除去〔`presentation` ではない。validation.py:137 `_WATERFALL_KEYS` も更新〕・`title`/`unitLabel`/`axisTicks` 必須化・deltas `maxItems: 5`〔期首・期末込みで最大 7 本。現行 `maxItems: 7`（component-ir.schema.json:379）から変更〕）、registry/vocabulary/TRUSTED_RENDERERS、フィクスチャ一式
- Test: `scripts/tests/test_waterfall_renderer.py`, `tests/test_renderer_svg_gate.py`

**Interfaces:**
- Consumes: Task 2 `title`/`unit_label`（必須）、既存 Decimal 機構（`start + Σdelta == end`、tolerance=displayPrecision/2〔validation.py:1026〕— 維持）。
- Produces: SVG 契約:
  - `viewBox="0 0 640 360"`。**checker 改修**: `_SVG_VIEWBOX_EXACT` 単一定数（checker.py:53、`_SvgSubtreeParser._check_value` が全 SVG に適用〔checker.py:1160-1162〕）を、component_key 別マップ `_RENDERER_SVG_VIEWBOX = {"slope@2": "0 0 600 220", "waterfall@2": "0 0 640 360"}` へ変え、`_validate_svg_subtree` に component_key を渡す。
  - 許可要素へ `rect` を追加（checker.py:41）。属性 allowlist（checker.py:45 付近）へ `rect: {class, x, y, width, height}` を追加し、座標整数検証の対象属性（現行 x,y,x1,y1,x2,y2,cx,cy〔checker.py:1172-1174〕）に width/height を追加。**既存 bad フィクスチャ `component-bad-svg-rect-element.html`（rect 拒否を固定、test_renderer_svg_gate.py:26）は `polygon` 拒否のフィクスチャへ作り替える。**
  - 点線・色は **CSS のみ**で表現（`stroke-dasharray` を SVG 属性に書くと line の属性 allowlist 違反になる）。
  - Y 軸の矢尻は許可要素の制約（path/polygon/marker なし）から **line 2 本の合成**で描く。
  - チャート幾何: 領域 x∈[70,620]、baseline y=320、天井 y=40。`y(v) = 320 - round(280 * v / v_max)`（Decimal・ROUND_HALF_UP・整数座標）。バー n 本（n≤7）を等間隔配置: `slot_w = 550 // n`、バー幅 `min(70, slot_w - 20)`。
  - バー: 期首/期末 `ve-wf-total`（紺塗り・値は `ve-wf-value-on-fill`）、増加 `ve-wf-plus`（白抜き紺枠・`ve-wf-value-plus`）、減少は**絶対値最大の 1 本だけ** `ve-wf-minus`（橙塗り）、他は `ve-wf-minus-soft`（白抜き橙枠）。負値は `▲{valueText}`。因子名 `ve-wf-factor`（増加=バー上、減少=バー下）。隣接バー間の点線コネクタ `ve-wf-connector`（走行レベルの y、n 本のバーに対し n−1 本）。
  - `axisTicks`（string 配列・必須）: 各値が 0..v_max の数値であることを validation.py で検査し、目盛ラベルとして描画。
  - 図ヘッダ: Task 11 と同じ `ve-fig-title`/`ve-fig-unit`。figcaption=takeaway は維持。
  - `RenderManifest.svg_root_ids=(svg_id,)`（slope@2 と同型、slope.py:105-117 参照）。

- [ ] **Step 1: 失敗するテストを書く**（JSON フィクスチャ `component-valid-waterfall.json` を新契約で書き直し: start 90/end 80、deltas: 価格改定+40・販促費削減+20・値引き−50・原価上昇−20、unitLabel 億円、axisTicks ["0","50","100","150"]）:

```python
def test_waterfall_v2_renders_svg_with_fixed_viewbox(self):
    result = render_fixture("component-valid-waterfall")
    self.assertIn('viewBox="0 0 640 360"', result.markup)
    self.assertTrue(result.manifest.svg_root_ids)

def test_waterfall_v2_negative_uses_triangle_notation(self):
    markup = render_fixture("component-valid-waterfall").markup
    self.assertIn("▲50", markup); self.assertIn("▲20", markup)
    self.assertNotIn(">-50<", markup)

def test_waterfall_v2_only_largest_decrease_is_filled(self):
    markup = render_fixture("component-valid-waterfall").markup
    self.assertEqual(markup.count('class="ve-wf-bar ve-wf-minus"'), 1)
    self.assertEqual(markup.count('class="ve-wf-bar ve-wf-minus-soft"'), 1)

def test_waterfall_v2_emits_connectors_between_adjacent_bars(self):
    markup = render_fixture("component-valid-waterfall").markup
    self.assertEqual(markup.count("ve-wf-connector"), 5)  # バー6本 → 5本

def test_waterfall_v2_requires_unit_label(self):
    expect_violation(self, "component-bad-waterfall-no-unit",
                     "quantitative-unit-required")
```

- [ ] **Step 2: 失敗確認 → Step 3: numeric.py に座標関数を追加**:

```python
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP  # ROUND_CEILING を追加

def waterfall_axis_max(values: Sequence[Decimal]) -> Decimal:
    """累積系列の最大値を 50 の倍数へ切上げ（最小 50）。"""
    peak = max(values)
    step = Decimal(50)
    units = (peak / step).to_integral_value(rounding=ROUND_CEILING)
    return max(step, units * step)

def waterfall_y(value: Decimal, v_max: Decimal) -> int:
    return 320 - int((Decimal(280) * value / v_max)
                     .to_integral_value(rounding=ROUND_HALF_UP))
```

- [ ] **Step 4: waterfall.py 全面書換** — 累積レベルを Decimal で計算し、SVG を slope@2 と同型の f-string で組み立て（rect/line/text/g/title/desc のみ）。notes は slope.py:75-86 と同構造。
- [ ] **Step 5: checker/スキーマ改修**（Interfaces に列挙のとおり: viewBox マップ・rect allowlist・`_check_waterfall_artifact` 書換・orientation 除去・maxItems 5・rect bad フィクスチャ作り替え）。
- [ ] **Step 6: CSS 全面書換**（幾何なし・塗り/線のみ。生値禁止 — 白は `var(--dg-on-primary)`）:

```css
figure[data-ve-component="waterfall"] .ve-fig-title { margin: 0; font-weight: 700; font-size: var(--fs-h2); }
figure[data-ve-component="waterfall"] .ve-fig-unit {
  margin: 0 0 var(--space-1); color: var(--text-faint); font-size: var(--fs-figure); font-weight: 700;
  border-bottom: 1.5px solid var(--border); padding-bottom: var(--space-1); }
figure[data-ve-component="waterfall"] .ve-wf-axis { stroke: var(--text); stroke-width: 1.5; }
figure[data-ve-component="waterfall"] .ve-wf-connector { stroke: var(--dg-line); stroke-width: 1.5; stroke-dasharray: 3 4; }
figure[data-ve-component="waterfall"] .ve-wf-total { fill: var(--dg-primary); }
figure[data-ve-component="waterfall"] .ve-wf-plus { fill: var(--bg); stroke: var(--dg-primary); stroke-width: 1.5; }
figure[data-ve-component="waterfall"] .ve-wf-minus { fill: var(--dg-negative); }
figure[data-ve-component="waterfall"] .ve-wf-minus-soft { fill: var(--bg); stroke: var(--dg-negative); stroke-width: 1.5; }
figure[data-ve-component="waterfall"] .ve-wf-value-on-fill { fill: var(--dg-on-primary); font-weight: 700; font-size: 17px; }
figure[data-ve-component="waterfall"] .ve-wf-value-plus { fill: var(--dg-primary); font-weight: 700; font-size: 17px; }
figure[data-ve-component="waterfall"] .ve-wf-value-minus-soft { fill: var(--dg-negative); font-weight: 700; font-size: 17px; }
figure[data-ve-component="waterfall"] .ve-wf-factor { fill: var(--text); font-weight: 700; font-size: 14px; }
figure[data-ve-component="waterfall"] .ve-wf-tick, figure[data-ve-component="waterfall"] .ve-wf-unit-label { fill: var(--text); font-size: 14px; }
```

- [ ] **Step 7: 共通手順 1〜5 → Step 8: Commit** — `git commit -am "feat(waterfall): v2 renderer-SVG with axis, dotted connectors, triangle notation"`

---

### Task 13: bars@2 新設（拡張ゲート 10 手順）

**Files:**
- Create: `renderers/bars.py`、`assets/components/bars.css`、`scripts/tests/test_bars_renderer.py`、`scripts/tests/component-valid-bars.json`、`component-bad-bars-structure.html`
- Modify: `component-vocabulary.json`、`component-ir.schema.json`、`assembly.schema.json`、`registry.json`、`renderers/__init__.py`、`diagnostics.py`＋`registry.py`（`bars-width-classes` 規則）、`validation.py`

**Interfaces:**
- Consumes: Task 1 トークン、Task 2 `title`/`unit_label`（必須）/ `highlight_id`。
- Produces: `relationshipKind: "quantitative-comparison"`、capabilities `["single-axis-quantity", "ranked-comparison"]`、contractVersion 2。IR payload:

```json
{"bars": {"title": "各国の女性役員割合（2021年）", "unitLabel": "%", "items": [
  {"id": "b1", "label": "フランス", "value": "45.3", "valueText": "45.3%"}
]}, "highlightId": "b5"}
```

出力契約: 図ヘッダ（`ve-fig-title`/`ve-fig-unit`）＋行 `<div class="ve-bars-row"><span class="ve-bars-label">…</span><span class="ve-bars-track"><span class="ve-bars-fill ve-bars-w-K"></span><span class="ve-bars-value">…</span></span></div>`。幅は最大値=100% とした整数%クラス `ve-bars-w-{0..100}`（waterfall v1 の `ve-wf-len-*` 列挙〔waterfall.css:33-234、Task 12 で削除する前にコピー〕と同方式で bars.css に列挙）。`highlight_id` の行だけ `ve-dg-highlight`。items 1..10。figcaption=takeaway は他形式と同じく必須。

- [ ] **Step 1: 失敗するテストを書く**（新規テストファイル。unittest＋render_fixture 流儀で作る）:

```python
def test_bars_renders_rows_with_integer_width_class(self):
    markup = render_fixture("component-valid-bars").markup   # 45.3 と 7.5 の2行+highlight
    self.assertIn("ve-bars-w-100", markup)
    self.assertIn("ve-bars-w-17", markup)   # round(7.5/45.3*100)=17
    self.assertEqual(markup.count("ve-dg-highlight"), 1)

def test_bars_rejects_more_than_ten_items(self):
    expect_violation(self, "component-bad-bars-eleven-items", "bars-item-limit")
```

- [ ] **Step 2: 失敗確認 → Step 3: 拡張ゲート 10 手順を一括実施** — 語彙→スキーマ→model（`BarsPayload`）→validation（Decimal 解釈可・items 1..10〔違反 `bars-item-limit`〕・unit_label/title 必須）→レンダラ（幅% は `(v / v_max * 100).to_integral_value(ROUND_HALF_UP)`）→CSS→digest→TRUSTED_RENDERERS `bars@2`→registry エントリ（checkerRules に `bars-width-classes` — `KNOWN_CHECKER_RULES` へも追加）→checker（`_check_bars_artifact`: 幅クラスが 0..100 の整数・highlight 最大 1）→bad フィクスチャ。CSS 本体:

```css
figure[data-ve-component="bars"] .ve-bars-list { display: grid; gap: var(--space-1); max-width: 34rem; }
figure[data-ve-component="bars"] .ve-bars-row {
  display: grid; grid-template-columns: 8rem minmax(0, 1fr); gap: var(--space-2); align-items: center; }
figure[data-ve-component="bars"] .ve-bars-label { font-weight: 700; }
figure[data-ve-component="bars"] .ve-bars-track { display: flex; align-items: center; gap: var(--space-1); }
figure[data-ve-component="bars"] .ve-bars-fill { height: 1.6rem; background: var(--dg-primary); }
figure[data-ve-component="bars"] .ve-bars-fill.ve-dg-highlight { background: var(--dg-highlight); }
figure[data-ve-component="bars"] .ve-bars-value { font-weight: 700; white-space: nowrap; }
/* ve-bars-w-0 〜 ve-bars-w-100 を 1% 刻みで列挙（waterfall v1 の列挙をリネームして流用） */
```

- [ ] **Step 4: テスト＋check.sh 通過確認 → Step 5: Commit** — `git commit -am "feat(bars): promote to canonical bars@2 with navy fills and single highlight"`

---

### Task 14: kpi@2 新設（拡張ゲート 10 手順）

**Files:**
- Create: `renderers/kpi.py`、`assets/components/kpi.css`、`scripts/tests/test_kpi_renderer.py`、`scripts/tests/component-valid-kpi.json`、`component-bad-kpi-structure.html`
- Modify: Task 13 と同じ 7 ファイル群

**Interfaces:**
- Produces: `relationshipKind: "headline-metrics"`、capabilities `["metric-highlight"]`、contractVersion 2。IR payload:

```json
{"kpi": {"items": [
  {"id": "k1", "value": "88", "unit": "%", "caption": "本プログラムの満足度"}
]}}
```

出力契約: `<div class="ve-kpi-item"><div class="ve-kpi-ring"><span class="ve-kpi-num">88<small>%</small></span></div><p class="ve-kpi-cap">…</p></div>`。items 1..5（違反 `kpi-item-limit`）。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_kpi_renders_ring_number_and_caption(self):
    markup = render_fixture("component-valid-kpi").markup
    self.assertIn('class="ve-kpi-ring"', markup)
    self.assertIn("<small>%</small>", markup)
    self.assertIn("本プログラムの満足度", markup)

def test_kpi_rejects_more_than_five_items(self):
    expect_violation(self, "component-bad-kpi-six-items", "kpi-item-limit")
```

- [ ] **Step 2: 失敗確認 → Step 3: 拡張ゲート 10 手順を一括実施**。CSS:

```css
figure[data-ve-component="kpi"] .ve-kpi-list {
  display: flex; flex-wrap: wrap; gap: var(--space-4); justify-content: center; }
figure[data-ve-component="kpi"] .ve-kpi-item { display: grid; justify-items: center; gap: var(--space-2); max-width: 12rem; }
figure[data-ve-component="kpi"] .ve-kpi-ring {
  display: grid; place-items: center; width: 8.5rem; height: 8.5rem;
  border: 5px solid var(--dg-primary); border-radius: 50%; text-align: center; }
figure[data-ve-component="kpi"] .ve-kpi-num {
  font-size: 2.1rem; font-weight: 700; color: var(--dg-primary); line-height: 1.1; }
figure[data-ve-component="kpi"] .ve-kpi-num small { font-size: 1rem; color: var(--text-dim); }
figure[data-ve-component="kpi"] .ve-kpi-cap { text-align: center; font-size: var(--fs-figure); margin: 0; }
```

（`border-radius: 50%` はリング円の本質形状で、矩形装飾角丸の禁止対象外 — Task 15 で design-system.md に例外を明記。）

- [ ] **Step 4: テスト通過確認 → Step 5: Commit** — `git commit -am "feat(kpi): promote to canonical kpi@2 ring metrics"`

---

### Task 15: 規範文書の同期（design-system.md / patterns.md / SKILL.md）

**Files:**
- Modify: `references/design-system.md`（`--dg-*` トークン表、図解構造色=紺の教義、文中強調 1 フレーズ、ハイライト 1 箇所、kpi リング円の例外、waterfall の整数%量子化記述を SVG 契約へ差替、確度語彙の再確認）
- Modify: `references/patterns.md`（12 形式の canonical JSON 例を @2 契約へ更新、bars/kpi の canonical 組み立て例を新規追加、選択ガイドへ bars/kpi 行を追加、legacy 節の bars/kpi は「canonical 昇格済み」と注記）
- Modify: `SKILL.md`（コンポーネント列挙を 12 形式へ、意思決定列に bars/kpi を追記）

- [ ] **Step 1: ドリフト検査をテストとして書く** — legacy 見出し（`### kpi — 効果・指標`〔patterns.md:177〕等）と衝突しない **canonical 例の実体**で検出する:

```python
def test_docs_have_canonical_examples_for_all_twelve_components(self):
    text = Path("../references/patterns.md").read_text(encoding="utf-8")
    for comp in ["matrix", "flow", "enumeration", "chevron", "pyramid", "stairs",
                 "logic-tree", "waterfall", "slope", "evidence-map", "bars", "kpi"]:
        self.assertIn(f'"component": "{comp}"', text, comp)  # canonical JSON 例の実体

def test_design_system_documents_dg_tokens(self):
    ds = Path("../references/design-system.md").read_text(encoding="utf-8")
    self.assertIn("--dg-primary", ds)
    self.assertIn("dg-em", ds)
```

- [ ] **Step 2: 失敗確認 → 文書更新 → PASS 確認 → Step 3: Commit** — `git commit -am "docs(ve): sync design-system/patterns/SKILL to visual standard v3"`

---

### Task 16: 統合検証（version 収束・ギャラリー再生成・4 系統 visual QA・全体グリーン）

**Files:**
- Modify: `references/component-ir.schema.json`（contractVersion enum を `[1, 2]`→`[2]` へ絞る。vocabulary と test_component_contract の整合を確認）
- Create: `.visual-explain/2026-07-XX-v3-gallery.html`（12 形式×1 例の IR を build_explainer.py でビルド）
- Modify: `.visual-explain/fixture-claude-{proposal,system,research}.html`, `fixture-pi-{proposal,system,research}.html`（旧 72rem 骨格 — 新骨格・新スタイルで再生成）、`examples/example-proposal.html`

- [ ] **Step 1: version 収束** — 全 12 形式が contractVersion 2 であることを確認し、schema enum を `[2]` へ。`python3 -m pytest tests/test_component_contract.py -q` → PASS。
- [ ] **Step 2: 12 形式の IR JSON を書きビルド** — `python3 scripts/build_explainer.py --assembly /tmp/v3-gallery.json --output .visual-explain/2026-07-XX-v3-gallery.html`（IR は patterns.md の @2 例 12 個を連結）。
- [ ] **Step 3: 四層検査** — `bash scripts/check.sh <絶対パス>` → PASS。
- [ ] **Step 4: Playwright 4 系統スクリーンショット**:

```bash
for scheme in light dark; do for vp in 1440,900 390,844; do
  npx playwright screenshot --channel chrome --full-page \
    --viewport-size $vp --color-scheme $scheme --wait-for-timeout 800 \
    "file://$PWD/.visual-explain/2026-07-XX-v3-gallery.html" "shot-$scheme-${vp%%,*}.png"
done; done
```

- [ ] **Step 5: spec の判定基準 (a)〜(d) を目視確認** — (a) 数値・ラベル折返しゼロ (b) 見出しへの重なりゼロ (c) 強調・ハイライト上限遵守 (d) 接続線の途切れ・はみ出しゼロ（logic-tree エルボー / chevron ループ / evidence-map スパイン / waterfall コネクタ）。モックと突合し、乖離は該当タスクへ戻して修正。
- [ ] **Step 6: 旧 fixtures の再生成** — `.visual-explain/fixture-claude-*` / `fixture-pi-*` と `examples/example-proposal.html` を新骨格・新スタイルで再生成（spec の要求）。
- [ ] **Step 7: 全体グリーン確認** — `python3 -m pytest tests/ -q` → 全 PASS。`git status` clean。
- [ ] **Step 8: Commit & draft PR** — `git commit -am "test(ve): v3 gallery fixture and visual QA evidence"` → `gh pr create --draft --title "feat: McKinsey-style visual standard v3 (canonical 12 @2)" --body "spec: docs/superpowers/specs/2026-07-13-mckinsey-restyle-design.md"`（merge はユーザー判断）。

---

## Self-Review 結果（rev.2: サブエージェント技術レビューの全指摘を反映）

- C1 反映: Diagnostic は `code/message/path`・ALL_CODES 登録・KNOWN_CHECKER_RULES 追加（Task 3/6/12/13）。
- C2 反映: viewBox のコンポーネント別マップ化を Task 12 に明記。
- C3 反映: 全リスタイルタスクに `_check_*_artifact` 改修を組込み（共通手順 1）。pyramid/stairs/enumeration/chevron は ul/ol/li 意味構造を維持。
- C4 反映: matrix/flow の余白は `var(--space-*)` のみ（spacing 監査）。
- M1 反映: contractVersion enum の `[1,2]`→`[2]` 遷移（Task 2/16）とフィクスチャ再生成の共通手順化。
- M2 反映: テスト流儀（render_fixture / _base_ir / ContractError＋code / unittest）を Global Constraints に明記し、全テスト例を書き換え。
- M3 反映: resplice の実仕様（引数なし一括・--help なし・KEEP_AS_IS 6 件手動）を Task 1 に明記。
- M4/M5 反映: 図ヘッダは新 `title` フィールド＋figcaption=takeaway 維持、slope summary の単位重複を削除、slope にも図ヘッダと unit 必須を適用（Task 11）。
- MINOR 反映: orientation（≠presentation）除去・rect bad フィクスチャ作替え・rect 属性 allowlist＋width/height 整数検証・dasharray は CSS・矢尻は line 2 本・deltas maxItems 5・ROUND_CEILING import・語彙置換のスコープ限定・renderers/__init__.py を Files へ・SKELETON 定数名・Task 15 ドリフトテストの検出力・fixture-claude/pi 再生成（Task 16）・PAIRS コントラスト追加（Task 1）・`#fff`→`var(--dg-on-primary)`。
