# McKinsey 流ビジュアル標準 v3 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** canonical 12 形式（既存 10＋bars/kpi 昇格）の視覚層を McKinsey 流（固定紺パレット・角丸なし・エルボー/レール接続契約・waterfall SVG 化）へ `@2` として一括リスタイルする。

**Architecture:** 骨格に図解専用トークン `--dg-*` を追加し、各コンポーネントの CSS/レンダラを `@2` へバージョンアップする。品質フロア（固定領域バイト一致・四層検証・fail-closed）は不変。見た目の正はコミット済みモック `.visual-explain/2026-07-13-mckinsey-restyle-candidates-mock.html`、規範は spec `docs/superpowers/specs/2026-07-13-mckinsey-restyle-design.md`。

**Tech Stack:** Python 3.14（stdlib のみ・pytest）、素の CSS、renderer 生成 SVG。外部ライブラリ追加なし。

## Global Constraints

- 骨格の固定領域・テーマ JS・CSP は 1 バイトも変更しない（トークン追加は `:root` ブロック内のみ。skeleton 変更時は `test_skeleton_audit.py` と全フィクスチャの resplice を同一タスクで行う）。
- パレットは spec のトークン表の値をそのまま使う（light/dark とも。独自の色値を発明しない）。
- 図形コンポーネント CSS に `border-radius`・アニメーション・新フォントを書かない。
- CSS 資産を変更したら `shasum -a 256` で digest を再計算し `registry.json` を厳密値で更新する（ワイルドカード禁止）。
- 確度語彙は「確認済み / 推論 / 未確認」の 3 語のみ（「確定/推定」は禁止）。
- 文中強調は 1 説明文に `<strong class="dg-em">` 最大 1 個。teal ハイライトは 1 図 1 箇所。
- 各タスクの最後に `bash skills/visual-explain/scripts/check.sh` が通る有効フィクスチャを 1 つ以上維持する。
- コミットは Conventional Commits（`feat(ve-components): ...` / `test: ...`）。タスクごとに最低 1 コミット。
- 作業ブランチ: `feat/mckinsey-restyle-v3`（main 直コミット禁止。完了後 draft PR、merge はユーザー判断）。

## File Structure（今回触るもの）

```
skills/visual-explain/
  assets/skeleton.html                      … :root に --dg-* / --radius 追加（Task 1）
  assets/components/<comp>.css              … 12 形式の CSS 全面書換（Task 4-14）
  assets/components/registry.json           … version 2 / renderer @2 / digest 更新（各タスク）
  references/component-vocabulary.json      … contractVersion 2 / bars・kpi 追加
  references/component-ir.schema.json       … descriptionEmphasis / unitLabel / highlight / bars / kpi
  references/assembly.schema.json           … enum 同期
  references/design-system.md, patterns.md  … 規範文書の同期（Task 15）
  scripts/ve_components/model.py            … 共通フィールド追加・確度語彙定数（Task 2）
  scripts/ve_components/checker.py          … 全域規則 5 種＋SVG allowlist（Task 3, 11, 12）
  scripts/ve_components/renderers/*.py      … 各レンダラ改修＋bars.py / kpi.py 新設
  scripts/ve_components/renderers/__init__.py … TRUSTED_RENDERERS の @2 化
  scripts/tests/test_*_renderer.py          … 各レンダラの期待更新＋新規 2 本
  scripts/tests/*.html                      … bad/valid フィクスチャ追加・resplice
```

実行前に `superpowers:using-git-worktrees` で worktree を作り、`git checkout -b feat/mckinsey-restyle-v3`。

---

### Task 1: 骨格トークン（--dg-* / --radius）追加と監査同期

**Files:**
- Modify: `skills/visual-explain/assets/skeleton.html`（`:root` と dark ブロックのみ）
- Modify: `skills/visual-explain/scripts/tests/test_skeleton_audit.py`
- Test: `skills/visual-explain/scripts/tests/test_skeleton_audit.py`

**Interfaces:**
- Produces: CSS カスタムプロパティ `--dg-primary, --dg-primary-mid, --dg-primary-light, --dg-highlight, --dg-negative, --dg-neutral, --dg-line, --dg-emphasis, --dg-on-primary, --radius`（後続全タスクの CSS が参照）と skeleton 内の `.dg-em` 記法規則。

- [ ] **Step 1: 失敗するテストを書く** — `test_skeleton_audit.py` に追加:

```python
DG_TOKENS = [
    "--dg-primary:", "--dg-primary-mid:", "--dg-primary-light:",
    "--dg-highlight:", "--dg-negative:", "--dg-neutral:",
    "--dg-line:", "--dg-emphasis:", "--dg-on-primary:", "--radius:",
]

def test_skeleton_defines_diagram_tokens_in_all_theme_blocks():
    text = SKELETON_PATH.read_text(encoding="utf-8")
    for token in DG_TOKENS:
        assert text.count(token) >= 2, f"{token} は light と dark の両方に必要"

def test_skeleton_defines_dg_em_rule():
    text = SKELETON_PATH.read_text(encoding="utf-8")
    assert ".dg-em" in text and "var(--dg-emphasis)" in text
```

（`SKELETON_PATH` は既存テストの定数を再利用。無ければ `Path(__file__).resolve().parents[1] / ".." / "assets" / "skeleton.html"` を既存流儀に合わせて定義。）

- [ ] **Step 2: 失敗確認** — `cd skills/visual-explain/scripts && python3 -m pytest tests/test_skeleton_audit.py -k dg -v` → FAIL（token 不在）。

- [ ] **Step 3: skeleton に spec の表のとおり実装** — light `:root` に:

```css
      --radius: .4rem;
      --dg-primary: #1F4E79; --dg-primary-mid: #2E6DA4; --dg-primary-light: #BDD7EE;
      --dg-highlight: #2E8B9A; --dg-negative: #C55A11; --dg-neutral: #F2F2F2;
      --dg-line: #7F7F7F; --dg-emphasis: #2E75B6; --dg-on-primary: #ffffff;
```

dark（`@media` 内と `[data-theme="dark"]` の両方）に:

```css
      --radius: .4rem;
      --dg-primary: #2E5A8F; --dg-primary-mid: #3E77B4; --dg-primary-light: #274664;
      --dg-highlight: #3FA3B4; --dg-negative: #E07B39; --dg-neutral: #262b31;
      --dg-line: #9aa1ab; --dg-emphasis: #6FA8DC; --dg-on-primary: #f2f5f9;
```

`<style>` の記法セクションに 1 行追加: `.dg-em { color: var(--dg-emphasis); font-weight: 700; }`
既存 `button { border-radius: .4rem; }` 等はそのまま（`--radius` 参照への書換はしない。最小差分）。

- [ ] **Step 4: 固定領域が変わったので全 HTML フィクスチャを resplice** — `python3 tests/tools/resplice.py --help` で使い方を確認し、`tests/*.html` と `examples/example-proposal.html` の骨格領域を新 skeleton で貼り直す。ツールが一括対応しない場合は対象ファイルを列挙して個別実行。

- [ ] **Step 5: 全テスト＋check.sh 通過確認** — `python3 -m pytest tests/ -q` → 全 PASS。`bash ../scripts/check.sh $(pwd)/tests/valid-system.html --type system` → PASS。

- [ ] **Step 6: Commit** — `git add -A && git commit -m "feat(skeleton): add --dg-* diagram tokens, --radius, .dg-em notation"`

---

### Task 2: モデル共通拡張と確度語彙の中央化

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/model.py`
- Modify: `skills/visual-explain/scripts/ve_components/renderers/*.py`（`_CERT_LABEL` の置換のみ）
- Modify: `skills/visual-explain/references/component-ir.schema.json`, `references/assembly.schema.json`
- Test: `skills/visual-explain/scripts/tests/test_v2_core.py`

**Interfaces:**
- Produces: `model.CERTAINTY_LABEL = {"confirmed": "確認済み", "inferred": "推論", "unverified": "未確認"}`（全レンダラが import）。IR 共通 optional フィールド `unit_label: Optional[str]`（定量系 payload: slope/waterfall/bars）、`description_emphasis: Optional[str]`（enumeration/chevron の item）、`highlight_id: Optional[str]`（stairs/bars/matrix/slope の注目対象）。スキーマの同名 camelCase（`unitLabel` / `descriptionEmphasis` / `highlightId`）。

- [ ] **Step 1: 失敗するテストを書く** — `test_v2_core.py` に追加:

```python
from ve_components.model import CERTAINTY_LABEL

def test_certainty_label_uses_design_system_vocabulary():
    assert CERTAINTY_LABEL == {
        "confirmed": "確認済み", "inferred": "推論", "unverified": "未確認",
    }

def test_no_renderer_uses_old_vocabulary():
    import pathlib
    renderers = pathlib.Path("ve_components/renderers")
    for path in renderers.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "確定" not in text and "推定" not in text, path.name
```

- [ ] **Step 2: 失敗確認** — `python3 -m pytest tests/test_v2_core.py -k vocabulary -v` → FAIL。

- [ ] **Step 3: 実装** — `model.py` に `CERTAINTY_LABEL` 定数を追加。各レンダラの `_CERT_LABEL = {"confirmed": "確定", ...}` を `from ..model import CERTAINTY_LABEL as _CERT_LABEL` へ置換（slope.py:12 と同型の定義が各レンダラにある）。`model.py` の該当 dataclass に `unit_label` / `description_emphasis` / `highlight_id` を `Optional[str] = None` で追加し、`validation.py` の IR パース箇所（camelCase→snake_case 変換部）へ対応を追加。スキーマ 2 ファイルの該当 payload に `"unitLabel": {"type": "string", "minLength": 1}` 等を optional で追加（`additionalProperties: false` を維持）。

- [ ] **Step 4: 既存レンダラテストの語彙期待を更新** — `grep -rn "確定\|推定" tests/*.py tests/*.html` で旧語彙の期待を洗い出し、「確認済み/推論」へ更新。フィクスチャ HTML 内の図中チップ文言も同時に更新。

- [ ] **Step 5: 全テスト通過確認** — `python3 -m pytest tests/ -q` → PASS。

- [ ] **Step 6: Commit** — `git commit -am "feat(ve-components): centralize certainty vocabulary, add unitLabel/descriptionEmphasis/highlightId"`

---

### Task 3: checker 全域規則（強調上限・ハイライト上限・語彙固定・unitLabel 必須・折返し禁止クラス）

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/checker.py`
- Create: `skills/visual-explain/scripts/tests/component-bad-emphasis-overuse.html`, `component-bad-highlight-overuse.html`, `component-bad-certainty-vocabulary.html`
- Test: `skills/visual-explain/scripts/tests/test_component_checker.py`

**Interfaces:**
- Produces: `checker.validate_notation_rules(content: str) -> list[Diagnostic]`（最終文書検査層から呼ぶ）。ルール ID: `notation-emphasis-limit`, `notation-highlight-limit`, `notation-certainty-vocabulary`。IR 検査側: 定量コンポーネント（slope/waterfall/bars）で `unit_label` 欠落を FAIL（`quantitative-unit-required`）。

- [ ] **Step 1: 失敗するテストを書く** — `test_component_checker.py` に追加:

```python
def test_emphasis_limit_rejects_two_dg_em_in_one_description():
    html = '<p class="ve-enum-desc">Aを<strong class="dg-em">強調1</strong>し'
    html += '<strong class="dg-em">強調2</strong>する</p>'
    diags = checker.validate_notation_rules(html)
    assert any(d.rule == "notation-emphasis-limit" for d in diags)

def test_highlight_limit_rejects_two_highlights_in_one_figure():
    html = ('<figure data-ve-component="bars">'
            '<div class="ve-bars-fill ve-dg-highlight"></div>'
            '<div class="ve-bars-fill ve-dg-highlight"></div></figure>')
    diags = checker.validate_notation_rules(html)
    assert any(d.rule == "notation-highlight-limit" for d in diags)

def test_certainty_vocabulary_rejects_old_labels():
    html = '<li><strong>確定:</strong> 何か</li>'
    diags = checker.validate_notation_rules(html)
    assert any(d.rule == "notation-certainty-vocabulary" for d in diags)
```

- [ ] **Step 2: 失敗確認** — `python3 -m pytest tests/test_component_checker.py -k notation -v` → FAIL（関数未定義）。

- [ ] **Step 3: 実装** — `checker.py` に追加（既存 `validate_renderer_svg` の直後）:

```python
def validate_notation_rules(content: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    # 1説明文（説明ブロック要素）内の dg-em は最大1
    for block in re.findall(r"<(?:p|li)\b[^>]*>.*?</(?:p|li)>", content, re.S):
        if block.count('class="dg-em"') > 1:
            diagnostics.append(Diagnostic(
                rule="notation-emphasis-limit",
                message="文中強調 dg-em は1説明文に1つまでです。"))
    # 1 figure 内の ve-dg-highlight は最大1
    for figure in re.findall(r"<figure\b.*?</figure>", content, re.S):
        if figure.count("ve-dg-highlight") > 1:
            diagnostics.append(Diagnostic(
                rule="notation-highlight-limit",
                message="teal ハイライトは1図1箇所までです。"))
    # 旧確度語彙の禁止（<strong>確定:</strong> / <strong>推定:</strong> 型のみを対象）
    if re.search(r"<strong>(確定|推定)[:：]", content):
        diagnostics.append(Diagnostic(
            rule="notation-certainty-vocabulary",
            message="確度語彙は 確認済み/推論/未確認 の3語に統一してください。"))
    return diagnostics
```

`Diagnostic` の実コンストラクタ引数は既存定義（`checker.py` 冒頭）に合わせる。最終文書検査（`checker.py:1489` 付近の `validate_renderer_svg` 呼出しと同じ場所）に `diagnostics += validate_notation_rules(content)` を追加。IR 検査側は `validation.py` の各定量 payload 検証に `unit_label` 必須チェックを追加（ルール ID `quantitative-unit-required`。※既存 slope は `slope.unit` を持つ — 後方互換のため Task 11/12 で `unit_label` へ移行するまで slope は対象外にし、bars/waterfall@2 から適用）。

- [ ] **Step 4: bad フィクスチャ 3 本を作成し checker が FAIL を出すことをテストに固定** — 既存 `component-bad-*.html` の構造（valid フィクスチャをコピーして 1 点だけ壊す）を踏襲。

- [ ] **Step 5: 全テスト通過確認** — `python3 -m pytest tests/ -q` → PASS。

- [ ] **Step 6: Commit** — `git commit -am "feat(checker): notation rules (emphasis/highlight limits, certainty vocabulary)"`

---

### Task 4: enumeration@2

**Files:**
- Modify: `skills/visual-explain/assets/components/enumeration.css`（全面書換）
- Modify: `skills/visual-explain/scripts/ve_components/renderers/enumeration.py`
- Modify: `skills/visual-explain/assets/components/registry.json`（version 2 / renderer `enumeration@2` / digest）
- Modify: `skills/visual-explain/references/component-vocabulary.json`（contractVersion 2）
- Test: `skills/visual-explain/scripts/tests/test_enumeration_renderer.py`

**Interfaces:**
- Consumes: `--dg-*` トークン（Task 1）、`description_emphasis`（Task 2）。
- Produces: 出力契約 — コンセプト箱 `<div class="ve-enum-box">`（紺・白抜き太字）、説明 `<p class="ve-enum-desc">`（`・` 始まり、`description_emphasis` があれば該当部分文字列を `<strong class="dg-em">` で 1 回だけ包む）。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_enumeration_v2_wraps_emphasis_once():
    ir = make_enumeration_ir(items=[{
        "id": "e1", "title": "無料体験チラシ",
        "description": ["チラシに無料のフィットネス利用券をつけて配布する"],
        "descriptionEmphasis": "無料のフィットネス利用券",
    }])
    result = render(ir)
    assert result.markup.count('<strong class="dg-em">無料のフィットネス利用券</strong>') == 1
    assert 'class="ve-enum-box"' in result.markup

def test_enumeration_v2_rejects_emphasis_not_in_description():
    # descriptionEmphasis が description の部分文字列でなければ ValidationError
    with pytest.raises(ValidationError):
        make_enumeration_ir(items=[{"id": "e1", "title": "t",
            "description": ["本文"], "descriptionEmphasis": "存在しない句"}])
```

（`make_enumeration_ir` / `render` は既存テストのヘルパを再利用。実名が違う場合は既存テストの流儀に合わせる。）

- [ ] **Step 2: 失敗確認** — `python3 -m pytest tests/test_enumeration_renderer.py -k v2 -v` → FAIL。

- [ ] **Step 3: レンダラ実装** — description 描画部で:

```python
def _desc_html(text: str, emphasis: str | None) -> str:
    escaped = _esc(text)
    if emphasis:
        needle = _esc(emphasis)
        escaped = escaped.replace(needle, f'<strong class="dg-em">{needle}</strong>', 1)
    return escaped
```

`validation.py` に「`description_emphasis` は description のいずれかの要素の部分文字列」検査を追加。

- [ ] **Step 4: CSS 全面書換** — `enumeration.css` を以下へ（モック `.enum` 系の namespaced 版）:

```css
figure[data-ve-component="enumeration"] .ve-enum-list { display: grid; gap: 2rem; }
figure[data-ve-component="enumeration"] .ve-enum-row {
  display: grid; grid-template-columns: 13rem minmax(0, 1fr);
  gap: 1.5rem; align-items: center; }
figure[data-ve-component="enumeration"] .ve-enum-box {
  display: grid; place-items: center; min-height: 5.5rem; padding: 1rem;
  background: var(--dg-primary); color: var(--dg-on-primary);
  font-size: 1.0625rem; font-weight: 700; text-align: center; line-height: 1.5; }
figure[data-ve-component="enumeration"] .ve-enum-desc {
  margin: 0; padding-left: 1.1rem; text-indent: -1.1rem; }
figure[data-ve-component="enumeration"] .ve-enum-desc::before { content: "・"; }
@media (max-width: 42rem) {
  figure[data-ve-component="enumeration"] .ve-enum-row { grid-template-columns: 1fr; }
}
```

`presentation: "columns"`（横型）は同トークンで列方向 grid に写像（説明は下）。既存クラス名が `ve-enum-*` と異なる場合はレンダラ・テスト・CSS を同時に新契約へ揃える。

- [ ] **Step 5: registry/vocabulary 更新** — `version: 2`、`renderer: "enumeration@2"`、`TRUSTED_RENDERERS` のキーを `enumeration@2` へ、digest 再計算:
`shasum -a 256 assets/components/enumeration.css` → 出力値を registry.json に貼付。

- [ ] **Step 6: テスト＋check.sh 通過確認** — `python3 -m pytest tests/test_enumeration_renderer.py tests/test_component_checker.py -q` → PASS。

- [ ] **Step 7: Commit** — `git commit -am "feat(enumeration): v2 McKinsey restyle with dg tokens and dg-em emphasis"`

---

### Task 5: chevron@2

**Files:**
- Modify: `assets/components/chevron.css`（全面書換）、`scripts/ve_components/renderers/chevron.py`、`registry.json`、`component-vocabulary.json`
- Test: `scripts/tests/test_chevron_renderer.py`

**Interfaces:**
- Consumes: Task 1 トークン、Task 2 `description_emphasis`。
- Produces: 下向き五角形 `<div class="ve-chv-box">`、`loop:true` 時のみ `<div class="ve-chv-rail"></div><div class="ve-chv-tail"></div>` を wrap 直下に出力。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_chevron_v2_emits_loop_rail_and_tail_only_when_loop():
    looped = render(make_chevron_ir(loop=True))
    plain = render(make_chevron_ir(loop=False))
    assert 'class="ve-chv-rail"' in looped.markup and 'class="ve-chv-tail"' in looped.markup
    assert 've-chv-rail' not in plain.markup

def test_chevron_v2_box_uses_pentagon_class():
    result = render(make_chevron_ir(loop=False))
    assert 'class="ve-chv-box"' in result.markup
```

- [ ] **Step 2: 失敗確認** — `python3 -m pytest tests/test_chevron_renderer.py -k v2 -v` → FAIL。

- [ ] **Step 3: レンダラ改修** — wrap を `<div class="ve-chv-wrap">`（loop 時 `data-ve-loop="true"`）とし、loop 時に rail/tail の 2 要素を先頭に出力。既存の「最終段から先頭への1本だけ」検証は維持。

- [ ] **Step 4: CSS 全面書換** — モックの `.chv-*` を namespaced 化（接続契約は spec の「途切れない単一経路」）:

```css
figure[data-ve-component="chevron"] .ve-chv-wrap { position: relative; --chv-cx: 9rem; }
figure[data-ve-component="chevron"] .ve-chv-wrap[data-ve-loop="true"] {
  padding-left: 2.5rem; padding-top: 2.3rem; padding-bottom: 1.2rem; }
figure[data-ve-component="chevron"] .ve-chv-rail {
  position: absolute; left: .5rem; top: .5rem; bottom: .2rem;
  width: calc(var(--chv-cx) - .5rem);
  border: 2.5px solid var(--dg-line); border-right: 0; }
figure[data-ve-component="chevron"] .ve-chv-rail::before {
  content: ""; position: absolute; top: -2.5px; right: -2.5px;
  height: .95rem; border-right: 2.5px solid var(--dg-line); }
figure[data-ve-component="chevron"] .ve-chv-rail::after {
  content: ""; position: absolute; top: calc(.95rem - 2.5px); right: -.6rem;
  border: .6rem solid transparent; border-top: .85rem solid var(--dg-line); border-bottom: 0; }
figure[data-ve-component="chevron"] .ve-chv-tail {
  position: absolute; left: calc(var(--chv-cx) - 1.25px); bottom: .2rem;
  height: 1rem; border-left: 2.5px solid var(--dg-line); }
figure[data-ve-component="chevron"] .ve-chv-row {
  display: grid; grid-template-columns: 13rem minmax(0, 1fr);
  gap: 1.5rem; align-items: center; }
figure[data-ve-component="chevron"] .ve-chv-box {
  display: grid; place-items: center; min-height: 6.5rem;
  padding: 1rem 1rem 2.2rem; background: var(--dg-primary); color: var(--dg-on-primary);
  font-size: 1.0625rem; font-weight: 700; text-align: center; line-height: 1.5;
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 1.9rem), 50% 100%, 0 calc(100% - 1.9rem)); }
figure[data-ve-component="chevron"] .ve-chv-desc {
  margin: 0; padding-left: 1.1rem; text-indent: -1.1rem; }
figure[data-ve-component="chevron"] .ve-chv-desc::before { content: "・"; }
@media (max-width: 42rem) {
  figure[data-ve-component="chevron"] .ve-chv-row { grid-template-columns: 1fr; }
  figure[data-ve-component="chevron"] .ve-chv-wrap[data-ve-loop="true"] {
    padding-left: 1.8rem; --chv-cx: 50%; }
  figure[data-ve-component="chevron"] .ve-chv-rail { left: .3rem; width: calc(var(--chv-cx) - .3rem); }
}
```

行間は縦 `gap: 2rem`。横型（orientation: horizontal）は右向き五角形（clip-path の右辺を尖らせる）で同トークン。

- [ ] **Step 5: registry/vocabulary/digest 更新**（Task 4 Step 5 と同手順、対象 chevron）。

- [ ] **Step 6: テスト通過確認** — `python3 -m pytest tests/test_chevron_renderer.py -q` → PASS。

- [ ] **Step 7: Commit** — `git commit -am "feat(chevron): v2 pentagon shape with unbroken loop rail"`

---

### Task 6: matrix@2

**Files:**
- Modify: `assets/components/matrix.css`、`renderers/matrix.py`、`registry.json`、`component-vocabulary.json`、`references/component-ir.schema.json`
- Test: `scripts/tests/test_matrix_renderer.py`

**Interfaces:**
- Consumes: Task 1 トークン、Task 2 `highlight_id`。
- Produces: IR に optional `presentation: "concept" | "dense"`（default `dense`）。`concept` は紺列ヘッダ箱＋グレー行ラベル箱＋アウトライン値セル（grid）。`dense` は現行のセマンティック table を維持し見出しを紺文字＋下罫へリスタイル。`highlight_id` のセルだけ `ve-dg-highlight`（淡紺背景）。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_matrix_v2_concept_presentation_renders_boxes():
    result = render(make_matrix_ir(presentation="concept"))
    assert 'class="ve-mx-colhead"' in result.markup
    assert 'class="ve-mx-cell"' in result.markup

def test_matrix_v2_concept_rejects_long_cell_text():
    with pytest.raises(ValidationError):
        make_matrix_ir(presentation="concept",
                       cells=[{"id": "c1", "rowId": "r1", "columnId": "k1",
                               "content": "六文字を超える長い説明文"}])

def test_matrix_v2_highlight_marks_single_cell():
    result = render(make_matrix_ir(highlight_id="c2"))
    assert result.markup.count("ve-dg-highlight") == 1
```

- [ ] **Step 2: 失敗確認** — `python3 -m pytest tests/test_matrix_renderer.py -k v2 -v` → FAIL。

- [ ] **Step 3: 実装** — スキーマに `presentation` enum 追加。`validation.py`: `concept` のとき全セル content は 6 文字以下を強制（超過は ValidationError）。レンダラ: `concept` は `<div class="ve-mx-grid">` に colhead/rowhead/cell を出力（table でないため `accessibility.summary` の役割が増える — aria-label と visually-hidden の関係リストは既存 matrix 契約を踏襲）。`dense` は既存 table 構造を維持しクラスだけ v2 へ。

- [ ] **Step 4: CSS 全面書換**:

```css
figure[data-ve-component="matrix"] .ve-mx-grid {
  display: grid; grid-template-columns: 8rem repeat(var(--mx-cols, 2), minmax(0, 1fr));
  gap: .6rem; max-width: 34rem; }
figure[data-ve-component="matrix"] .ve-mx-colhead {
  display: grid; place-items: center; padding: .5rem;
  background: var(--dg-primary); color: var(--dg-on-primary); font-weight: 700; }
figure[data-ve-component="matrix"] .ve-mx-rowhead {
  display: grid; place-items: center; padding: .5rem;
  background: var(--dg-neutral); color: var(--text); font-weight: 700; }
figure[data-ve-component="matrix"] .ve-mx-cell {
  display: grid; place-items: center; padding: .6rem;
  border: 1.5px solid var(--dg-primary); font-weight: 700; font-size: 1.0625rem; }
figure[data-ve-component="matrix"] .ve-mx-cell.ve-dg-highlight { background: var(--dg-primary-light); }
figure[data-ve-component="matrix"] .ve-matrix-scroll table { border-collapse: collapse; width: 100%; }
figure[data-ve-component="matrix"] .ve-matrix-scroll th {
  color: var(--dg-primary); font-weight: 800; text-align: left;
  border-bottom: 1.5px solid var(--dg-primary); padding: .5rem 1rem .5rem 0; }
figure[data-ve-component="matrix"] .ve-matrix-scroll td {
  border-bottom: 1px solid var(--border); padding: .5rem 1rem .5rem 0; vertical-align: top; }
```

（`--mx-cols` はレンダラが列数を inline style でなく `style` 属性なしで出せないため、列数クラス `ve-mx-cols-2` / `ve-mx-cols-3` を出力し CSS 側に 2/3/4 列の規則を書く。座標直書き検査に抵触しない。）

- [ ] **Step 5: registry/vocabulary/digest 更新**。`checkerRules` に `matrix-concept-length` を追記。

- [ ] **Step 6: テスト通過確認** — `python3 -m pytest tests/test_matrix_renderer.py -q` → PASS。

- [ ] **Step 7: Commit** — `git commit -am "feat(matrix): v2 concept/dense presentations with navy headers"`

---

### Task 7: flow@2

**Files:**
- Modify: `assets/components/flow.css`、`renderers/flow.py`（エッジラベル位置のみ）、`registry.json`、`component-vocabulary.json`
- Test: `scripts/tests/test_flow_renderer.py`

**Interfaces:**
- Consumes: Task 1 トークン。
- Produces: ノード `<div class="ve-flow-node">`（既定=紺塗り・白抜き。`tone: muted` 相当の中間状態は `ve-flow-node-outline`=白抜き紺枠）。遷移行 `<div class="ve-flow-edge"><span class="ve-flow-arrow"></span><span class="ve-flow-edge-label">…</span></div>`（ラベルは矢印の直後）。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_flow_v2_edge_label_adjacent_to_arrow():
    result = render(make_flow_ir())
    # 矢印 span の直後にラベル span（右端分離レイアウトの廃止）
    assert re.search(
        r'class="ve-flow-arrow"></span>\s*<span class="ve-flow-edge-label"',
        result.markup)
```

- [ ] **Step 2: 失敗確認** — `python3 -m pytest tests/test_flow_renderer.py -k v2 -v` → FAIL。

- [ ] **Step 3: 実装** — flow.py のエッジ描画 grid（`auto 1fr auto` 相当）を「矢印＋ラベル横並び」へ。分岐レール・グループの既存ロジック（flow_layout.py）は座標契約を変えず、クラス名と色だけ v2 化。

- [ ] **Step 4: CSS 書換** — 既定塗り `var(--dg-primary)`/白抜き、outline ノードは `border: 1.5px solid var(--dg-primary); background: var(--bg); color: var(--text);`、矢印は CSS 三角（`border-top: .8rem solid var(--dg-line)`）、`.ve-flow-edge { display: flex; gap: .6rem; padding-left: 45%; }`。レール（`ve-flow-rail`）は `2.5px solid var(--dg-line)` に太径化。

- [ ] **Step 5: registry/vocabulary/digest 更新**。

- [ ] **Step 6: テスト通過確認** — `python3 -m pytest tests/test_flow_renderer.py tests/test_flow_layout.py -q` → PASS。

- [ ] **Step 7: Commit** — `git commit -am "feat(flow): v2 navy nodes with arrow-adjacent edge labels"`

---

### Task 8: pyramid@2

**Files:**
- Modify: `assets/components/pyramid.css`、`renderers/pyramid.py`、`registry.json`、`component-vocabulary.json`
- Test: `scripts/tests/test_pyramid_renderer.py`

**Interfaces:**
- Consumes: Task 1 トークン。
- Produces: `<div class="ve-pyramid-tiers ve-pyramid-count-N">` 直下に `<div class="ve-pyramid-tier ve-pyramid-level-K">`（K=1..4、1 が頂上）。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_pyramid_v2_emits_level_classes():
    result = render(make_pyramid_ir(tiers=3))
    for k in (1, 2, 3):
        assert f"ve-pyramid-level-{k}" in result.markup

def test_pyramid_css_has_no_fit_content_container():
    css = Path("../assets/components/pyramid.css").read_text(encoding="utf-8")
    assert "fit-content" not in css
    assert "white-space: nowrap" in css and "min-width: max-content" in css
```

- [ ] **Step 2: 失敗確認** — `python3 -m pytest tests/test_pyramid_renderer.py -k v2 -v` → FAIL。

- [ ] **Step 3: CSS 全面書換**（1 文字縦積みバグの構造的根絶）:

```css
figure[data-ve-component="pyramid"] .ve-pyramid-tiers {
  display: grid; gap: 3px; width: min(100%, 24rem);
  margin-inline: auto; justify-items: center; }
figure[data-ve-component="pyramid"] .ve-pyramid-tier {
  display: grid; place-items: center; padding: .5rem 1rem;
  font-weight: 700; white-space: nowrap; min-width: max-content; }
figure[data-ve-component="pyramid"] .ve-pyramid-level-1 { width: 40%; background: var(--dg-primary); color: var(--dg-on-primary); }
figure[data-ve-component="pyramid"] .ve-pyramid-level-2 { width: 70%; background: var(--dg-primary-mid); color: var(--dg-on-primary); }
figure[data-ve-component="pyramid"] .ve-pyramid-level-3 { width: 100%; background: var(--dg-primary-light); color: var(--text); }
figure[data-ve-component="pyramid"] .ve-pyramid-count-4 .ve-pyramid-level-3 { width: 85%; }
figure[data-ve-component="pyramid"] .ve-pyramid-count-4 .ve-pyramid-level-4 { width: 100%; background: var(--dg-neutral); color: var(--text); }
```

- [ ] **Step 4: レンダラでレベルクラスと count クラスを出力**（既存 tier 描画に class 追加のみ）。

- [ ] **Step 5: registry/vocabulary/digest 更新**。

- [ ] **Step 6: テスト通過確認** — `python3 -m pytest tests/test_pyramid_renderer.py -q` → PASS。

- [ ] **Step 7: Commit** — `git commit -am "feat(pyramid): v2 fixed-width tiers, nowrap labels, navy gradation"`

---

### Task 9: stairs@2

**Files:**
- Modify: `assets/components/stairs.css`、`renderers/stairs.py`、`registry.json`、`component-vocabulary.json`
- Test: `scripts/tests/test_stairs_renderer.py`

**Interfaces:**
- Consumes: Task 1 トークン、Task 2 `highlight_id`（現在地の段）。
- Produces: `<div class="ve-stairs-step ve-stairs-done|ve-dg-highlight|ve-stairs-todo">`。現在地の段に `<span class="ve-stairs-here">← 現在地</span>`。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_stairs_v2_marks_current_with_highlight_and_here_label():
    result = render(make_stairs_ir(highlight_id="s3"))
    assert result.markup.count("ve-dg-highlight") == 1
    assert "← 現在地" in result.markup

def test_stairs_v2_tones_split_done_and_todo():
    result = render(make_stairs_ir(highlight_id="s3"))
    assert "ve-stairs-done" in result.markup and "ve-stairs-todo" in result.markup
```

- [ ] **Step 2: 失敗確認** → FAIL。
- [ ] **Step 3: 実装** — highlight_id より前=done（紺）、当該=highlight（teal）、後=todo（neutral）。CSS はモック `.stairs` の namespaced 化（min-height 3〜8.6rem の 5 段組）。既存 stairs IR の現在地指定フィールドがある場合（`current` 等）は `highlight_id` へ移行し、旧フィールドはスキーマから除去。
- [ ] **Step 4: registry/vocabulary/digest 更新**。
- [ ] **Step 5: テスト通過確認** — `python3 -m pytest tests/test_stairs_renderer.py -q` → PASS。
- [ ] **Step 6: Commit** — `git commit -am "feat(stairs): v2 ascending steps with teal current marker"`

---

### Task 10: logic-tree@2（エルボー接続契約）

**Files:**
- Modify: `assets/components/logic-tree.css`（全面書換）、`renderers/logic_tree.py`（構造変更）、`registry.json`、`component-vocabulary.json`
- Test: `scripts/tests/test_logic_tree_renderer.py`

**Interfaces:**
- Consumes: Task 1 トークン。
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

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_logic_tree_v2_nests_children_with_elbow_wrappers():
    result = render(make_logic_tree_ir())  # 枝3・うち1枝に leaf 2
    assert result.markup.count('class="ve-lt-child"') >= 4
    assert 'class="ve-lt-stub"' in result.markup

def test_logic_tree_v2_leafless_branch_has_no_nested_children():
    result = render(make_logic_tree_ir())
    # 市場機会枝（leaf なし）内に ve-lt-children が無い
    branch = re.search(r'<div class="ve-lt-child">(?:(?!ve-lt-child).)*?市場機会.*?</div>',
                       result.markup, re.S).group(0)
    assert "ve-lt-children" not in branch
```

- [ ] **Step 2: 失敗確認** → FAIL。

- [ ] **Step 3: レンダラを上記契約へ書換**（意味 ID・takeaway・certainty/sources notes の既存出力は維持）。

- [ ] **Step 4: CSS 全面書換**（モック `.lt-*` の namespaced 化。スパイン=最初の子の中心〜最後の子の中心）:

```css
figure[data-ve-component="logic-tree"] .ve-lt { display: flex; align-items: center; }
figure[data-ve-component="logic-tree"] .ve-lt-node { padding: .5rem 1rem; font-weight: 700; }
figure[data-ve-component="logic-tree"] .ve-lt-root { background: var(--dg-primary); color: var(--dg-on-primary); text-align: center; }
figure[data-ve-component="logic-tree"] .ve-lt-branch { background: var(--dg-primary-mid); color: var(--dg-on-primary); }
figure[data-ve-component="logic-tree"] .ve-lt-leaf {
  border: 1.5px solid var(--dg-line); color: var(--text);
  font-size: var(--fs-figure); font-weight: 400; padding: .3rem .8rem; }
figure[data-ve-component="logic-tree"] .ve-lt-stub {
  flex: 0 0 1.5rem; border-top: 2px solid var(--dg-line); align-self: center; }
figure[data-ve-component="logic-tree"] .ve-lt-children { display: flex; flex-direction: column; gap: .7rem; }
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

- [ ] **Step 5: registry/vocabulary/digest 更新**。既存 bad フィクスチャ（`component-bad-logic-tree-*.html`）の構造期待を新契約へ更新。

- [ ] **Step 6: テスト通過確認** — `python3 -m pytest tests/test_logic_tree_renderer.py -q` → PASS。

- [ ] **Step 7: Commit** — `git commit -am "feat(logic-tree): v2 fig-7 elbow connectors, no overshoot/gap by construction"`

---

### Task 11: slope@2（端点結合ラベル・teal ハイライト・allowlist 更新）

**Files:**
- Modify: `renderers/slope.py`、`assets/components/slope.css`、`scripts/ve_components/checker.py:39`、`registry.json`、`component-vocabulary.json`
- Test: `scripts/tests/test_slope_renderer.py`, `scripts/tests/test_renderer_svg_gate.py`

**Interfaces:**
- Consumes: Task 1 トークン、Task 2 `highlight_id` / `unit_label`（`slope.unit` を `unit_label` へ改名）。
- Produces: 系列ラベルを終端値と結合（`{to_value_text} {label}` を `x=490, text-anchor=start`）。中央浮遊ラベル（`x=300`）廃止。`highlight_id` の系列だけ `ve-slope-tone-highlight`（teal）、他は紺。`RENDERER_SVG_ALLOWLIST = frozenset({"slope@2"})`（Task 12 で waterfall@2 を追加）。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_slope_v2_merges_series_label_into_endpoint():
    result = render(make_slope_ir(items=[{"id": "s1", "label": "売上",
        "fromValue": "30", "toValue": "40",
        "fromValueText": "30件", "toValueText": "40件"}], highlight_id="s1"))
    assert "40件 売上" in result.markup
    assert 'x="300"' not in result.markup  # 中央浮遊ラベル廃止

def test_svg_gate_accepts_slope_v2_only():
    from ve_components.checker import RENDERER_SVG_ALLOWLIST
    assert "slope@2" in RENDERER_SVG_ALLOWLIST
    assert "slope@1" not in RENDERER_SVG_ALLOWLIST
```

- [ ] **Step 2: 失敗確認** → FAIL。
- [ ] **Step 3: 実装** — slope.py:51-56 の value/label テキスト出力を結合形へ。tone クラスを `highlight_id` 判定に置換（`item.tone` の従来値は `ve-slope-tone-default`=紺へ写像）。CSS で `stroke: var(--dg-primary)` / highlight は `var(--dg-highlight)`、`.ve-slope-value { font-weight: 700 }`、端点に `circle` を追加（allowlist の許可要素集合に `circle` が無ければ checker の許可リストへ追加し、`test_renderer_svg_gate.py` に許可要素の期待を追記）。
- [ ] **Step 4: allowlist を `{"slope@2"}` へ更新し、gate テストの `slope@1` 期待を全て更新**。
- [ ] **Step 5: registry/vocabulary/digest 更新**。
- [ ] **Step 6: テスト通過確認** — `python3 -m pytest tests/test_slope_renderer.py tests/test_renderer_svg_gate.py -q` → PASS。
- [ ] **Step 7: Commit** — `git commit -am "feat(slope): v2 endpoint-merged labels, highlight series, allowlist slope@2"`

---

### Task 12: waterfall@2（renderer-SVG 全面移行）

**Files:**
- Modify: `renderers/waterfall.py`（全面書換）、`assets/components/waterfall.css`（全面書換）、`ve_components/numeric.py`（座標算出追加）、`checker.py`（allowlist へ `waterfall@2` 追加）、`model.py`/スキーマ（`presentation` 除去・`unit_label` 必須・`axis_ticks` 追加）、`registry.json`、`component-vocabulary.json`
- Test: `scripts/tests/test_waterfall_renderer.py`, `tests/test_renderer_svg_gate.py`

**Interfaces:**
- Consumes: Task 2 `unit_label`（必須）、既存 Decimal 機構（`numeric.to_decimal`、`displayPrecision`、ROUND_HALF_UP、`start + Σdelta == end` 整合検査 — すべて維持）。
- Produces: `render_waterfall(section, definition) -> RenderResult`。SVG 契約:
  - `viewBox="0 0 640 360"` 完全一致、整数座標のみ。
  - チャート領域 x∈[70,620]、baseline y=320、天井 y=40。スケールは `y(v) = 320 - round(280 * v / v_max)`（`v_max` は累積最大値を 50 刻みで切上げ）。
  - Y 軸（矢印付き）＋0 起点の目盛ラベル（0 / v_max/3 刻みではなく 50 刻み相当のラベルを `axis_ticks` として IR で宣言必須・checker で軸値と描画の一致検証）。
  - バー: 期首/期末 `class="ve-wf-total"`（紺塗り・値は白抜きでバー内中央）、増加 `ve-wf-plus`（白抜き紺枠・値は紺）、減少 `ve-wf-minus`（橙塗り・白抜き値）だが**絶対値最大の減少 1 本だけ塗り**、他の減少は `ve-wf-minus-soft`（白抜き橙枠・橙値）。
  - 負値は `▲{絶対値のvalueText}`。因子名は増加=バー上 8px、減少=バー下 16px の `class="ve-wf-factor"`。
  - 隣接バー間の水平点線コネクタ `class="ve-wf-connector"`（`stroke-dasharray="3 4"`、走行レベルの y）。
  - figure 冒頭に図ヘッダ（`<p class="ve-fig-title">{caption}</p><p class="ve-fig-unit">単位: {unit_label}</p>`）。
  - `RenderManifest.svg_root_ids=(svg_id,)`（slope@2 と同型）。

- [ ] **Step 1: 失敗するテストを書く**（数値は spec の参照例）:

```python
def _sample_ir():
    return make_waterfall_ir(
        unit_label="億円", start_value="90", end_value="80",
        axis_ticks=["0", "50", "100", "150"],
        deltas=[
            {"id": "d1", "label": "価格改定", "value": "40", "valueText": "40"},
            {"id": "d2", "label": "販促費削減", "value": "20", "valueText": "20"},
            {"id": "d3", "label": "値引き", "value": "-50", "valueText": "50"},
            {"id": "d4", "label": "原価上昇", "value": "-20", "valueText": "20"},
        ])

def test_waterfall_v2_renders_svg_with_fixed_viewbox():
    result = render(_sample_ir())
    assert 'viewBox="0 0 640 360"' in result.markup
    assert result.manifest.svg_root_ids

def test_waterfall_v2_negative_uses_triangle_notation():
    markup = render(_sample_ir()).markup
    assert "▲50" in markup and "▲20" in markup and "-50" not in markup

def test_waterfall_v2_only_largest_decrease_is_filled():
    markup = render(_sample_ir()).markup
    assert markup.count('class="ve-wf-minus"') == 1      # 値引き ▲50 のみ塗り
    assert markup.count('class="ve-wf-minus-soft"') == 1  # 原価上昇はアウトライン

def test_waterfall_v2_emits_dotted_connectors_between_adjacent_bars():
    markup = render(_sample_ir()).markup
    assert markup.count("ve-wf-connector") == 5  # バー6本 → コネクタ5本

def test_waterfall_v2_requires_unit_label():
    with pytest.raises(ValidationError):
        make_waterfall_ir(unit_label=None, start_value="90", end_value="80",
                          axis_ticks=["0"], deltas=[])
```

- [ ] **Step 2: 失敗確認** — `python3 -m pytest tests/test_waterfall_renderer.py -k v2 -v` → FAIL。

- [ ] **Step 3: numeric.py に座標関数を追加**:

```python
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

- [ ] **Step 4: waterfall.py を全面書換** — 累積レベル列（start → 各 delta 適用）を Decimal で計算し、`start + Σdelta == end` 不一致は既存どおり ValidationError。バー x 座標は 6 本固定でなく `n` 本を等間隔配置: `slot_w = 550 // n`（バー幅は `min(70, slot_w - 20)`、n ≤ 7 は密度上限で保証）。各バーの `rect`/値 `text`/因子名 `text`、コネクタ `line`、軸 2 本、`axis_ticks` の目盛ラベル、単位ラベルを slope@2 と同型の f-string SVG で組み立てる。notes（certainty/sources）は slope.py:75-86 と同構造を流用。

- [ ] **Step 5: checker/スキーマ更新** — `RENDERER_SVG_ALLOWLIST = frozenset({"slope@2", "waterfall@2"})`。SVG 許可要素集合に `rect` を追加（無ければ）。スキーマから waterfall の `presentation` を除去し、`unitLabel`・`axisTicks`（string 配列・minItems 1）を required へ。`axis_ticks` の各値が `0..v_max` 範囲の数値文字列であることを validation.py で検査。旧 `ve-wf-start-*`/`ve-wf-len-*` クラス生成コードと CSS を削除。

- [ ] **Step 6: CSS 全面書換**（塗り・線のみ。幾何は SVG 属性）:

```css
figure[data-ve-component="waterfall"] .ve-fig-title { margin: 0; font-weight: 700; font-size: var(--fs-h2); }
figure[data-ve-component="waterfall"] .ve-fig-unit {
  margin: 0 0 .4rem; color: var(--text-faint); font-size: var(--fs-figure); font-weight: 700;
  border-bottom: 1.5px solid var(--border); padding-bottom: .4rem; }
figure[data-ve-component="waterfall"] .ve-wf-axis { stroke: var(--text); stroke-width: 1.5; }
figure[data-ve-component="waterfall"] .ve-wf-connector { stroke: var(--dg-line); stroke-width: 1.5; stroke-dasharray: 3 4; }
figure[data-ve-component="waterfall"] .ve-wf-total { fill: var(--dg-primary); }
figure[data-ve-component="waterfall"] .ve-wf-plus { fill: var(--bg); stroke: var(--dg-primary); stroke-width: 1.5; }
figure[data-ve-component="waterfall"] .ve-wf-minus { fill: var(--dg-negative); }
figure[data-ve-component="waterfall"] .ve-wf-minus-soft { fill: var(--bg); stroke: var(--dg-negative); stroke-width: 1.5; }
figure[data-ve-component="waterfall"] .ve-wf-value-on-fill { fill: #fff; font-weight: 700; font-size: 17px; }
figure[data-ve-component="waterfall"] .ve-wf-value-plus { fill: var(--dg-primary); font-weight: 700; font-size: 17px; }
figure[data-ve-component="waterfall"] .ve-wf-value-minus-soft { fill: var(--dg-negative); font-weight: 700; font-size: 17px; }
figure[data-ve-component="waterfall"] .ve-wf-factor { fill: var(--text); font-weight: 700; font-size: 14px; }
figure[data-ve-component="waterfall"] .ve-wf-tick, figure[data-ve-component="waterfall"] .ve-wf-unit { fill: var(--text); font-size: 14px; }
```

- [ ] **Step 7: registry/vocabulary/digest 更新**（`renderer: "waterfall@2"`）。旧 waterfall bad フィクスチャの期待更新。
- [ ] **Step 8: テスト通過確認** — `python3 -m pytest tests/test_waterfall_renderer.py tests/test_renderer_svg_gate.py tests/test_component_checker.py -q` → PASS。
- [ ] **Step 9: Commit** — `git commit -am "feat(waterfall): v2 renderer-SVG with axis, dotted connectors, triangle notation"`

---

### Task 13: bars@2 新設（拡張ゲート 10 手順）

**Files:**
- Create: `renderers/bars.py`、`assets/components/bars.css`、`scripts/tests/test_bars_renderer.py`、`scripts/tests/component-bad-bars-structure.html`
- Modify: `component-vocabulary.json`、`component-ir.schema.json`、`assembly.schema.json`、`registry.json`、`renderers/__init__.py`、`checker.py`（checkerRules）

**Interfaces:**
- Consumes: Task 1 トークン、Task 2 `unit_label`（必須）/ `highlight_id`。
- Produces: `relationshipKind: "quantitative-comparison"`、capabilities `["single-axis-quantity", "ranked-comparison"]`。IR payload:

```json
{"bars": {"unitLabel": "%", "items": [
  {"id": "b1", "label": "フランス", "value": "45.3", "valueText": "45.3%"}
]}, "highlightId": "b5"}
```

出力契約: 行 = `<div class="ve-bars-row"><span class="ve-bars-label">…</span><span class="ve-bars-track"><span class="ve-bars-fill" style?なし></span><span class="ve-bars-value">…</span></span></div>`。幅は最大値=100% とした整数%クラス `ve-bars-w-{0..100}`（座標直書き検査と両立する既存 waterfall v1 方式を踏襲。事前生成 CSS）。`highlight_id` の行だけ `ve-dg-highlight`。最大 10 行。図ヘッダ（title/unit）は waterfall@2 と同じ `ve-fig-title`/`ve-fig-unit`。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_bars_renders_rows_with_integer_width_class():
    result = render(make_bars_ir(items=[
        {"id": "b1", "label": "フランス", "value": "45.3", "valueText": "45.3%"},
        {"id": "b2", "label": "日本", "value": "7.5", "valueText": "7.5%"},
    ], highlight_id="b2", unit_label="%"))
    assert "ve-bars-w-100" in result.markup   # 最大値の行
    assert "ve-bars-w-17" in result.markup    # round(7.5/45.3*100)=17
    assert result.markup.count("ve-dg-highlight") == 1

def test_bars_rejects_more_than_ten_items():
    with pytest.raises(ValidationError):
        make_bars_ir(items=[{"id": f"b{i}", "label": str(i),
            "value": str(i), "valueText": str(i)} for i in range(11)],
            unit_label="件")
```

- [ ] **Step 2: 失敗確認** → FAIL（コンポーネント未定義）。
- [ ] **Step 3: 拡張ゲート 10 手順を一括実施** — 語彙→スキーマ→model dataclass（`BarsPayload`）→validation（value は Decimal 解釈可・items 1..10・unit_label 必須）→レンダラ（幅% は Decimal で `(v / v_max * 100).to_integral_value(ROUND_HALF_UP)`）→CSS（下記）→digest→TRUSTED_RENDERERS `bars@2`→registry エントリ→checker ルール（`bars-width-classes`: 幅クラスが 0..100 の整数のみ）→bad フィクスチャ。

```css
figure[data-ve-component="bars"] .ve-bars-list { display: grid; gap: .7rem; max-width: 34rem; }
figure[data-ve-component="bars"] .ve-bars-row {
  display: grid; grid-template-columns: 8rem minmax(0, 1fr); gap: 1rem; align-items: center; }
figure[data-ve-component="bars"] .ve-bars-label { font-weight: 700; }
figure[data-ve-component="bars"] .ve-bars-track { display: flex; align-items: center; gap: .5rem; }
figure[data-ve-component="bars"] .ve-bars-fill { height: 1.6rem; background: var(--dg-primary); }
figure[data-ve-component="bars"] .ve-bars-fill.ve-dg-highlight { background: var(--dg-highlight); }
figure[data-ve-component="bars"] .ve-bars-value { font-weight: 700; white-space: nowrap; }
/* 幅クラスは 0..100 を生成スクリプトでなく列挙で持つ（waterfall v1 の ve-wf-len-* と同方式） */
figure[data-ve-component="bars"] .ve-bars-w-0 { width: 0%; }
/* …1% 刻みで 100 まで（既存 waterfall v1 の生成手順をコピーして列挙） */
figure[data-ve-component="bars"] .ve-bars-w-100 { width: 100%; }
```

- [ ] **Step 4: テスト通過確認** — `python3 -m pytest tests/test_bars_renderer.py -q` → PASS。`bash scripts/check.sh` を bars 入り有効フィクスチャで PASS。
- [ ] **Step 5: Commit** — `git commit -am "feat(bars): promote to canonical bars@2 with navy fills and single highlight"`

---

### Task 14: kpi@2 新設（拡張ゲート 10 手順）

**Files:**
- Create: `renderers/kpi.py`、`assets/components/kpi.css`、`scripts/tests/test_kpi_renderer.py`、`scripts/tests/component-bad-kpi-structure.html`
- Modify: Task 13 と同じ 6 ファイル群

**Interfaces:**
- Produces: `relationshipKind: "headline-metrics"`、capabilities `["metric-highlight"]`。IR payload:

```json
{"kpi": {"items": [
  {"id": "k1", "value": "88", "unit": "%", "caption": "本プログラムの満足度"}
]}}
```

出力契約: `<div class="ve-kpi-item"><div class="ve-kpi-ring"><span class="ve-kpi-num">88<small>%</small></span></div><p class="ve-kpi-cap">…</p></div>`。最大 5 個。

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_kpi_renders_ring_number_and_caption():
    result = render(make_kpi_ir(items=[
        {"id": "k1", "value": "88", "unit": "%", "caption": "満足度"}]))
    assert 'class="ve-kpi-ring"' in result.markup
    assert "<small>%</small>" in result.markup and "満足度" in result.markup

def test_kpi_rejects_more_than_five_items():
    with pytest.raises(ValidationError):
        make_kpi_ir(items=[{"id": f"k{i}", "value": str(i), "unit": "件",
                            "caption": str(i)} for i in range(6)])
```

- [ ] **Step 2: 失敗確認** → FAIL。
- [ ] **Step 3: 拡張ゲート 10 手順を一括実施**。CSS:

```css
figure[data-ve-component="kpi"] .ve-kpi-list {
  display: flex; flex-wrap: wrap; gap: 2rem; justify-content: center; }
figure[data-ve-component="kpi"] .ve-kpi-item { display: grid; justify-items: center; gap: 1rem; max-width: 12rem; }
figure[data-ve-component="kpi"] .ve-kpi-ring {
  display: grid; place-items: center; width: 8.5rem; height: 8.5rem;
  border: 5px solid var(--dg-primary); border-radius: 50%; text-align: center; }
figure[data-ve-component="kpi"] .ve-kpi-num {
  font-size: 2.1rem; font-weight: 700; color: var(--dg-primary); line-height: 1.1; }
figure[data-ve-component="kpi"] .ve-kpi-num small { font-size: 1rem; color: var(--text-dim); }
figure[data-ve-component="kpi"] .ve-kpi-cap { text-align: center; font-size: var(--fs-figure); margin: 0; }
```

（`border-radius: 50%` はリング円の本質形状であり「図形に角丸を書かない」規則の対象外。spec の角丸禁止は矩形図形の装飾角丸を指す — この 1 行を design-system.md の Task 15 で例外として明記。）

- [ ] **Step 4: テスト通過確認** — `python3 -m pytest tests/test_kpi_renderer.py -q` → PASS。
- [ ] **Step 5: Commit** — `git commit -am "feat(kpi): promote to canonical kpi@2 ring metrics"`

---

### Task 15: 規範文書の同期（design-system.md / patterns.md / SKILL.md）

**Files:**
- Modify: `references/design-system.md`（トークン節に `--dg-*` 表、色ドクトリンに「図解構造色=紺」「文中強調 1 フレーズ」「ハイライト 1 箇所」「kpi リングの円形例外」、waterfall 節の量子化記述を SVG 契約へ差替）
- Modify: `references/patterns.md`（12 形式の canonical JSON 例を @2 契約へ更新、bars/kpi の例を新規追加、選択ガイドに bars/kpi 行を追加）
- Modify: `SKILL.md`（コンポーネント列挙を 12 形式に、`確定/推定` 表記があれば統一、bars/kpi の意思決定列を追記）

**Interfaces:**
- Consumes: Task 1–14 の確定契約。

- [ ] **Step 1: ドリフト検査をテストとして書く** — `test_v2_core.py` に追加:

```python
def test_docs_mention_all_twelve_components():
    text = Path("../references/patterns.md").read_text(encoding="utf-8")
    for comp in ["matrix", "flow", "enumeration", "chevron", "pyramid", "stairs",
                 "logic-tree", "waterfall", "slope", "evidence-map", "bars", "kpi"]:
        assert f"### {comp}" in text, comp

def test_docs_do_not_use_old_certainty_vocabulary_for_chips():
    ds = Path("../references/design-system.md").read_text(encoding="utf-8")
    assert "--dg-primary" in ds
```

- [ ] **Step 2: 失敗確認 → 文書更新 → PASS 確認** — `python3 -m pytest tests/test_v2_core.py -k docs -v`。
- [ ] **Step 3: Commit** — `git commit -am "docs(ve): sync design-system/patterns/SKILL to visual standard v3"`

---

### Task 16: 統合検証（ギャラリー再生成・4 系統 visual QA・全体グリーン）

**Files:**
- Create: `.visual-explain/2026-07-XX-v3-gallery.html`（12 形式×1 例の IR を `build_explainer.py` でビルド）
- Modify: 必要に応じ `examples/example-proposal.html`（新スタイルで再生成）

**Interfaces:**
- Consumes: Task 1–15 のすべて。

- [ ] **Step 1: 12 形式の IR JSON を書き、ビルド** — `python3 scripts/build_explainer.py --assembly /tmp/v3-gallery.json --output .visual-explain/2026-07-XX-v3-gallery.html`（IR は patterns.md の @2 例 12 個をそのまま連結）。
- [ ] **Step 2: 四層検査** — `bash scripts/check.sh <絶対パス>` → PASS。
- [ ] **Step 3: Playwright 4 系統スクリーンショット** —

```bash
for scheme in light dark; do for vp in 1440,900 390,844; do
  npx playwright screenshot --channel chrome --full-page \
    --viewport-size $vp --color-scheme $scheme --wait-for-timeout 800 \
    "file://$PWD/.visual-explain/2026-07-XX-v3-gallery.html" "shot-$scheme-${vp%%,*}.png"
done; done
```

- [ ] **Step 4: spec の判定基準 (a)〜(d) を目視確認** — (a) 数値・ラベル折返しゼロ (b) 見出しへの重なりゼロ (c) 強調・ハイライト上限遵守 (d) 接続線の途切れ・はみ出しゼロ（logic-tree エルボー / chevron ループ / evidence-map スパイン / waterfall コネクタ）。モックと突合し、乖離があれば該当タスクへ戻って修正。
- [ ] **Step 5: 全体グリーン確認** — `python3 -m pytest tests/ -q` → 全 PASS。`git status` clean。
- [ ] **Step 6: Commit & draft PR** — `git commit -am "test(ve): v3 gallery fixture and visual QA evidence"` → `gh pr create --draft --title "feat: McKinsey-style visual standard v3 (canonical 12 @2)" --body "spec: docs/superpowers/specs/2026-07-13-mckinsey-restyle-design.md"`（merge はユーザー判断）。

---

## 補足: evidence-map@2 は Task 10 の直後に実施

evidence-map は logic-tree と同じエルボー機構（スパイン＋枝）を使うため、Task 10 完了後に同型で実施する（独立タスクとして分けるほどの新規性がないため Task 10 の Step 内に含めず、ここに明示する）:

### Task 10b: evidence-map@2

**Files:** `assets/components/evidence-map.css`、`renderers/evidence_map.py`、`registry.json`、`component-vocabulary.json`、Test: `tests/test_evidence_map_renderer.py`

- [ ] **Step 1: 失敗するテストを書く**:

```python
def test_evidence_map_v2_uses_spine_children():
    result = render(make_evidence_map_ir())
    assert 'class="ve-em-body"' in result.markup
    assert 'class="ve-em-item ve-em-solid"' in result.markup  # 確認済み=実線
```

- [ ] **Step 2: 失敗確認 → 実装** — 結論箱 `ve-em-conclusion`（紺）、`ve-em-body`（左スパイン）、根拠 `ve-em-item ve-em-{solid|dashed|dotted}`（certaintyRef の 3 値と対応、枝線 `::before` はスタブ幅=インデント幅）。CSS はモック `.em-*` の namespaced 化＋logic-tree と同じ first/last 端点規則。
- [ ] **Step 3: registry/vocabulary/digest 更新 → テスト PASS → Commit** — `git commit -am "feat(evidence-map): v2 spine-connected evidence cards"`

---

## Self-Review 結果（作成時実施）

- **Spec coverage:** トークン=T1、記法（強調/▲/ハイライト/語彙/単位）=T2-T3-T12、12 形式=T4-T14（evidence-map=T10b）、文書同期=T15、検証 4 基準=T16。CSS 版 waterfall 廃止=T12 Step 5。旧 fixtures 再生成=T1 Step 4（resplice）＋T16。
- **Placeholder scan:** 「既存流儀に合わせる」類の表現は、実名がタスク間で確定できない既存ヘルパ（`make_*_ir`/`render`）の参照に限定した。新規契約はすべて実名・実値で記載。
- **Type consistency:** クラス接頭辞 `ve-<comp>-`、ハイライトは全形式共通 `ve-dg-highlight`、強調は `dg-em`、図ヘッダは `ve-fig-title`/`ve-fig-unit` で統一（T6/T12/T13 で同名）。確度は `CERTAINTY_LABEL` のみ（T2）。
