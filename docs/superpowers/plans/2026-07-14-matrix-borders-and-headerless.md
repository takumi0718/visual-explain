# Matrix 罫線二層化・見出しなし（複数箇条書き）モード Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** matrix@2 の dense モードで「表頭の下だけ太罫」に変え、セルに複数の並列箇条書きを置ける「見出しなしマトリックス」を追加する。

**Architecture:** 既存の `matrix@2` コンポーネント（schema / model / validation / renderer / CSS）を拡張する。3つの独立した変更 — (1) 罫線 CSS の二層化、(2) セル content の `string│string[]` 拡張、(3) `showColumnHeaders` オプション — を順に足し、最後にドキュメントと語彙を更新する。

**Tech Stack:** Python 3（dataclass ベースの IR、標準ライブラリのみ）、静的 HTML/CSS レンダラ、JSON Schema（`component-ir.schema.json`）、unittest/pytest。

## Global Constraints

- **テスト実行ディレクトリ**: すべてのテストは `skills/visual-explain/scripts` から実行する（例: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_matrix_renderer.py -q`）。`ve_components` を import 解決するため。
- **CSS 名前空間**: `assets/components/matrix.css` の全ルール行は `figure[data-ve-component="matrix"]` で始めること。`test_css_namespaced_and_scrollable` が全行を検査する。`overflow-x: auto` の宣言も残すこと。
- **CSS 変更プロトコル**: `matrix.css` を変更したら必ず (a) `assets/components/registry.json` の `matrix.css` の `digest`（sha256）を再計算して更新し、(b) `examples/example-proposal.html` を再ビルドする。手順は各タスク内に明記。これを怠ると `check.sh` の四層チェッカー（digest 照合）が失敗する。
- **concept モード不変**: `presentation: "concept"`（`ve-mx-grid`）の描画・「セル≤6字」バリデーションは変更しない。concept では content は文字列必須。
- **安全性**: 外部参照・インラインスタイル・スクリプトを出力しない。著者テキストは全て `html.escape` でエスケープする。
- **後方互換**: 既存 `examples/example-proposal.assembly.json`（全セル単一文字列）の意味的描画は罫線 CSS 以外変わらないこと。

---

### Task 1: 罫線の二層化（表頭のみ太罫）

現在 dense モードでは列見出し `<th scope="col">` と行見出し `<th scope="row">` の両方が太罫（`1.5px --border-strong`）を持つ。列見出しのみ太罫に維持し、行見出しは本文セルと同じ細罫（`1px --border`）にする。

**Files:**
- Modify: `skills/visual-explain/assets/components/matrix.css:20-22`
- Modify: `skills/visual-explain/assets/components/registry.json`（matrix.css digest）
- Modify: `skills/visual-explain/examples/example-proposal.html`（再ビルド）
- Test: `skills/visual-explain/scripts/tests/test_matrix_renderer.py`

**Interfaces:**
- Consumes: なし（CSS のみ）
- Produces: CSS クラス構造は不変。`th[scope="col"]` が太罫、`th[scope="row"]` が細罫。

- [ ] **Step 1: 失敗するテストを書く**

`skills/visual-explain/scripts/tests/test_matrix_renderer.py` の末尾（`if __name__` の前）に追加:

```python
class MatrixBorderTest(unittest.TestCase):
    def _css(self) -> str:
        return (SKILL / "assets" / "components" / "matrix.css").read_text("utf-8")

    def test_only_column_header_has_strong_bottom_rule(self) -> None:
        css = self._css()
        self.assertIn('th[scope="col"]', css)
        self.assertIn('th[scope="row"]', css)
        # 列見出しは太罫（--border-strong）を維持
        self.assertRegex(
            css, r'th\[scope="col"\][^}]*border-bottom:\s*1\.5px solid var\(--border-strong\)'
        )
        # 行見出しは本文セルと同じ細罫（--border）に変更
        self.assertRegex(
            css, r'th\[scope="row"\][^}]*border-bottom:\s*1px solid var\(--border\)'
        )
        # 汎用 th ルールは全 th に太罫を当てない
        self.assertNotRegex(css, r'\.ve-matrix-scroll th \{[^}]*border-bottom:\s*1\.5px')
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_matrix_renderer.py::MatrixBorderTest -q`
Expected: FAIL（`th[scope="col"]` が CSS に存在しない）

- [ ] **Step 3: matrix.css の th ルールを分割**

`skills/visual-explain/assets/components/matrix.css` の現在の 20-22 行:

```css
figure[data-ve-component="matrix"] .ve-matrix-scroll th {
  color: var(--text); font-weight: 800; text-align: left;
  border-bottom: 1.5px solid var(--border-strong); padding: var(--space-1) var(--space-2) var(--space-1) 0; }
```

を次に置き換える:

```css
figure[data-ve-component="matrix"] .ve-matrix-scroll th {
  color: var(--text); font-weight: 800; text-align: left;
  padding: var(--space-1) var(--space-2) var(--space-1) 0; }
figure[data-ve-component="matrix"] .ve-matrix-scroll th[scope="col"] { border-bottom: 1.5px solid var(--border-strong); }
figure[data-ve-component="matrix"] .ve-matrix-scroll th[scope="row"] { border-bottom: 1px solid var(--border); vertical-align: top; }
```

- [ ] **Step 4: digest 再計算と example 再ビルド**

Run:
```bash
cd skills/visual-explain
NEW=$(shasum -a 256 assets/components/matrix.css | cut -d' ' -f1)
python3 - "$NEW" <<'PY'
import re, sys, pathlib
new = sys.argv[1]
p = pathlib.Path("assets/components/registry.json")
txt = p.read_text()
txt = re.sub(
    r'("path":\s*"matrix\.css",\s*"digest":\s*")[0-9a-f]{64}(")',
    lambda m: m.group(1) + new + m.group(2), txt,
)
p.write_text(txt)
print("matrix.css digest ->", new)
PY
python3 scripts/build_explainer.py \
  --assembly examples/example-proposal.assembly.json \
  --output examples/example-proposal.html
```
Expected: `matrix.css digest -> <64桁hex>` と `OK: .../examples/example-proposal.html`

- [ ] **Step 5: テストと関連スイートを実行して通過を確認**

Run:
```bash
cd skills/visual-explain/scripts && python3 -m pytest tests/test_matrix_renderer.py -q
```
Expected: PASS（`MatrixBorderTest` を含む全件 / `MatrixBuildTest` が check.sh を通す）

- [ ] **Step 6: コミット**

```bash
cd /Users/yoshidatakumi/workspace/visual-explain
git add skills/visual-explain/assets/components/matrix.css \
        skills/visual-explain/assets/components/registry.json \
        skills/visual-explain/examples/example-proposal.html \
        skills/visual-explain/scripts/tests/test_matrix_renderer.py
git commit -m "style(ve): make only the top column-header row use the strong bottom rule"
```

---

### Task 2: セルの複数箇条書き対応（見出しあり・なし両方で使える）

`matrixCell.content` を `string │ string[]` に拡張する。配列のとき dense セルは `・`付き複数行として描画する。単一文字列は従来通りプレーン1行（後方互換）。concept モードは文字列のみ許可する。

**Files:**
- Modify: `skills/visual-explain/references/component-ir.schema.json:175`（matrixCell.content）
- Modify: `skills/visual-explain/scripts/ve_components/model.py:76`（MatrixCell.content 型）
- Modify: `skills/visual-explain/scripts/ve_components/validation.py:587-601, 616-622`
- Modify: `skills/visual-explain/scripts/ve_components/renderers/matrix.py`（dense セル描画）
- Modify: `skills/visual-explain/assets/components/matrix.css`（箇条書きスタイル追加）
- Modify: `skills/visual-explain/assets/components/registry.json`（digest 再計算）
- Modify: `skills/visual-explain/examples/example-proposal.html`（再ビルド）
- Test: `skills/visual-explain/scripts/tests/test_matrix_renderer.py`

**Interfaces:**
- Consumes: Task 1 の CSS 構造（th 分割）。
- Produces:
  - `MatrixCell.content: str | tuple[str, ...]`（validation が配列を `tuple` に正規化）
  - renderer ヘルパ `_cell_content_html(content) -> str`（dense で使用）
  - dense の複数行セルは `<ul class="ve-matrix-bullets"><li>…</li></ul>` を出力
  - concept は content 配列を `INVALID_COMPONENT_PAYLOAD` で拒否

- [ ] **Step 1: 失敗するテストを書く**

`test_matrix_renderer.py` の末尾に追加:

```python
class MatrixBulletCellTest(unittest.TestCase):
    def test_dense_cell_renders_bullet_list_for_array_content(self) -> None:
        raw = json.loads((TESTS / "component-valid-matrix.json").read_text("utf-8"))
        raw["sections"][0]["ir"]["matrix"]["cells"][0]["content"] = ["一つ目", "二つ目"]
        ir = validate_canonical_section(raw["sections"][0]["ir"])
        markup = render_matrix(CanonicalSection(ir=ir), MATRIX_DEF).markup
        self.assertIn('class="ve-matrix-bullets"', markup)
        self.assertIn("<li>一つ目</li>", markup)
        self.assertIn("<li>二つ目</li>", markup)

    def test_dense_cell_string_content_stays_plain(self) -> None:
        markup = render_fixture().markup  # 既定フィクスチャは全て文字列
        self.assertNotIn("ve-matrix-bullets", markup)

    def test_array_cell_content_is_escaped(self) -> None:
        raw = json.loads((TESTS / "component-valid-matrix.json").read_text("utf-8"))
        raw["sections"][0]["ir"]["matrix"]["cells"][0]["content"] = ["a<b>&\"x\""]
        ir = validate_canonical_section(raw["sections"][0]["ir"])
        markup = render_matrix(CanonicalSection(ir=ir), MATRIX_DEF).markup
        self.assertNotIn("a<b>", markup)
        self.assertIn("a&lt;b&gt;", markup)

    def test_concept_rejects_array_content(self) -> None:
        raw = json.loads((TESTS / "component-valid-matrix-concept.json").read_text("utf-8"))
        raw["sections"][0]["ir"]["matrix"]["cells"][0]["content"] = ["a", "b"]
        with self.assertRaises(ContractError):
            validate_canonical_section(raw["sections"][0]["ir"])
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_matrix_renderer.py::MatrixBulletCellTest -q`
Expected: FAIL（配列 content が `ve-matrix-bullets` を出力しない）

- [ ] **Step 3: schema を拡張**

`skills/visual-explain/references/component-ir.schema.json` の `matrixCell` の content（現在 175 行）:

```json
        "content": {"type": "string", "minLength": 1},
```

を次に置き換える:

```json
        "content": {
          "oneOf": [
            {"type": "string", "minLength": 1},
            {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}}
          ]
        },
```

- [ ] **Step 4: model の型を更新**

`skills/visual-explain/scripts/ve_components/model.py` の `MatrixCell`（76 行）:

```python
    content: str
```

を次に置き換える:

```python
    content: str | tuple[str, ...]
```

- [ ] **Step 5: validation を更新**

`skills/visual-explain/scripts/ve_components/validation.py` の content チェック（現在 587-588 行）:

```python
        if not _nonblank_str(item.get("content")):
            col.add(INVALID_COMPONENT_PAYLOAD, "cell.content は空にできません", p)
```

を次に置き換える:

```python
        content_raw = item.get("content")
        if isinstance(content_raw, list):
            if not content_raw or not all(_nonblank_str(x) for x in content_raw):
                col.add(INVALID_COMPONENT_PAYLOAD, "cell.content の配列要素は空にできません", p)
            content_val: object = tuple(x for x in content_raw if isinstance(x, str))
        elif _nonblank_str(content_raw):
            content_val = content_raw
        else:
            col.add(INVALID_COMPONENT_PAYLOAD, "cell.content は空にできません", p)
            content_val = content_raw
```

続く `MatrixCell(...)` 生成（現在 598-601 行）の `content=item.get("content")` を `content=content_val` に変更:

```python
        cells.append(MatrixCell(
            id=cid, row_id=rid, column_id=colid, content=content_val,
            certainty_ref=item.get("certaintyRef"), source_ref=item.get("sourceRef"),
        ))
```

そして concept モードの長さチェック（現在 616-622 行）:

```python
        for i, cell in enumerate(cells):
            if len(cell.content) >= 7:
                col.add(
                    MATRIX_CONCEPT_LENGTH,
                    f"concept セルの content は6文字以下である必要があります (found {len(cell.content)})",
                    f"{path}.cells[{i}].content",
                )
```

を次に置き換える（配列は concept で拒否）:

```python
        for i, cell in enumerate(cells):
            if not isinstance(cell.content, str):
                col.add(
                    INVALID_COMPONENT_PAYLOAD,
                    "concept セルの content は文字列である必要があります",
                    f"{path}.cells[{i}].content",
                )
                continue
            if len(cell.content) >= 7:
                col.add(
                    MATRIX_CONCEPT_LENGTH,
                    f"concept セルの content は6文字以下である必要があります (found {len(cell.content)})",
                    f"{path}.cells[{i}].content",
                )
```

- [ ] **Step 6: renderer に箇条書きヘルパを追加し dense で使用**

`skills/visual-explain/scripts/ve_components/renderers/matrix.py` の `_esc` 定義（19-20 行）の直後に追加:

```python
def _cell_content_html(content) -> str:
    if isinstance(content, (list, tuple)):
        items = "".join(f'<li>{_esc(line)}</li>' for line in content)
        return f'<ul class="ve-matrix-bullets">{items}</ul>'
    return _esc(content)
```

そして dense テーブルのセル出力（現在 69 行）の `{_esc(cell.content)}` を `{_cell_content_html(cell.content)}` に変更:

```python
            cells.append(
                f'<td{cls_attr} data-ve-semantic-id="{_esc(cell.id)}" data-ve-row-id="{_esc(row.id)}"'
                f' data-ve-column-id="{_esc(col.id)}"{takeaway_attr}>{_cell_content_html(cell.content)}'
                f'{emphasis_html}{refs_html}</td>'
            )
```

（concept グリッド側の `_esc(cell.content)`（115・120 行）は文字列前提のため変更しない。）

- [ ] **Step 7: matrix.css に箇条書きスタイルを追加**

`skills/visual-explain/assets/components/matrix.css` の td ルール（`.ve-matrix-scroll td { … }`）の直後に次を追加:

```css
figure[data-ve-component="matrix"] .ve-matrix-bullets { margin: 0; padding: 0; list-style: none; }
figure[data-ve-component="matrix"] .ve-matrix-bullets li { margin: 0; padding-left: 1.1rem; text-indent: -1.1rem; }
figure[data-ve-component="matrix"] .ve-matrix-bullets li::before { content: "・"; }
figure[data-ve-component="matrix"] .ve-matrix-bullets li + li { margin-top: var(--space-1); }
```

- [ ] **Step 8: digest 再計算と example 再ビルド**

Run:
```bash
cd skills/visual-explain
NEW=$(shasum -a 256 assets/components/matrix.css | cut -d' ' -f1)
python3 - "$NEW" <<'PY'
import re, sys, pathlib
new = sys.argv[1]
p = pathlib.Path("assets/components/registry.json")
txt = p.read_text()
txt = re.sub(
    r'("path":\s*"matrix\.css",\s*"digest":\s*")[0-9a-f]{64}(")',
    lambda m: m.group(1) + new + m.group(2), txt,
)
p.write_text(txt)
print("matrix.css digest ->", new)
PY
python3 scripts/build_explainer.py \
  --assembly examples/example-proposal.assembly.json \
  --output examples/example-proposal.html
```
Expected: `matrix.css digest -> <64桁hex>` と `OK: .../examples/example-proposal.html`

- [ ] **Step 9: テストとスイートを実行して通過を確認**

Run:
```bash
cd skills/visual-explain/scripts && python3 -m pytest tests/test_matrix_renderer.py tests/test_component_contract.py -q
```
Expected: PASS（`MatrixBulletCellTest` 含む全件）

- [ ] **Step 10: コミット**

```bash
cd /Users/yoshidatakumi/workspace/visual-explain
git add skills/visual-explain/references/component-ir.schema.json \
        skills/visual-explain/scripts/ve_components/model.py \
        skills/visual-explain/scripts/ve_components/validation.py \
        skills/visual-explain/scripts/ve_components/renderers/matrix.py \
        skills/visual-explain/assets/components/matrix.css \
        skills/visual-explain/assets/components/registry.json \
        skills/visual-explain/examples/example-proposal.html \
        skills/visual-explain/scripts/tests/test_matrix_renderer.py
git commit -m "feat(ve): support multi-bullet matrix cells via string-or-array content"
```

---

### Task 3: 見出しなしオプション（showColumnHeaders）

`matrixPayload` に `showColumnHeaders`（既定 `true`）を追加する。`false`（dense 専用）で列見出し行（`<thead>`）を出力しない。

**Files:**
- Modify: `skills/visual-explain/references/component-ir.schema.json`（matrixPayload）
- Modify: `skills/visual-explain/scripts/ve_components/model.py:81-87`（MatrixPayload）
- Modify: `skills/visual-explain/scripts/ve_components/validation.py:135, 608-627`
- Modify: `skills/visual-explain/scripts/ve_components/renderers/matrix.py:39-77, 143-150`
- Modify: `skills/visual-explain/assets/components/registry.json`（matrix optionalInputs）
- Create: `skills/visual-explain/scripts/tests/component-valid-matrix-headerless.json`
- Test: `skills/visual-explain/scripts/tests/test_matrix_renderer.py`

**Interfaces:**
- Consumes: Task 2 の `_cell_content_html`（見出しなしフィクスチャは配列 content を使う）。
- Produces:
  - `MatrixPayload.show_column_headers: bool = True`
  - `_render_dense_table(..., show_column_headers)` — `False` で `<thead>` と `ve-matrix-corner` を出力しない
  - concept + `showColumnHeaders=false` は `INVALID_COMPONENT_PAYLOAD` で拒否し `True` に強制

- [ ] **Step 1: 見出しなしフィクスチャを作成**

Create `skills/visual-explain/scripts/tests/component-valid-matrix-headerless.json`:

```json
{
  "schemaVersion": 1,
  "document": {
    "id": "matrix-headerless-demo",
    "title": "見出しなしマトリックスの例",
    "summary": "各領域に複数の並列箇条書きを置く見出しなしマトリックス。"
  },
  "sections": [
    {
      "kind": "canonical",
      "ir": {
        "id": "sec-headerless-matrix",
        "relationship": {
          "kind": "two-axis",
          "capabilities": ["two-axis-classification", "intersection-comparison"]
        },
        "selection": {
          "component": "matrix",
          "version": 2,
          "matchedCapabilities": ["two-axis-classification", "intersection-comparison"]
        },
        "caption": "領域ごとの論点",
        "accessibility": {
          "label": "領域ごとの論点一覧",
          "summary": "各行が領域を表し、セルに複数の論点を並列に列挙する見出しなしの表。"
        },
        "matrix": {
          "showColumnHeaders": false,
          "rows": [
            {"id": "row-strategy", "label": "戦略・ビジョン"},
            {"id": "row-marketing", "label": "マーケティング"}
          ],
          "columns": [
            {"id": "col-points", "label": "論点"}
          ],
          "cells": [
            {"id": "cell-strategy", "rowId": "row-strategy", "columnId": "col-points", "content": ["国としての戦略的目標・ビジョンの設定", "各自治体・医療機関・支援企業等の明確な役割・目標設定"]},
            {"id": "cell-marketing", "rowId": "row-marketing", "columnId": "col-points", "content": ["医療渡航先としての知名度・認知度の向上", "患者から選ばれるための情報提供の充実"]}
          ]
        }
      }
    }
  ]
}
```

- [ ] **Step 2: 失敗するテストを書く**

`test_matrix_renderer.py` の末尾に追加:

```python
class MatrixHeaderlessTest(unittest.TestCase):
    def test_headerless_dense_omits_thead(self) -> None:
        markup = render_fixture("component-valid-matrix-headerless").markup
        self.assertNotIn("<thead>", markup)
        self.assertNotIn("ve-matrix-corner", markup)
        # 行見出しと本文セルは残る
        self.assertIn('scope="row"', markup)
        self.assertIn("ve-matrix-bullets", markup)

    def test_headed_matrix_still_has_thead(self) -> None:
        markup = render_fixture().markup
        self.assertIn("<thead>", markup)

    def test_headerless_concept_is_rejected(self) -> None:
        raw = json.loads((TESTS / "component-valid-matrix-concept.json").read_text("utf-8"))
        raw["sections"][0]["ir"]["matrix"]["showColumnHeaders"] = False
        with self.assertRaises(ContractError):
            validate_canonical_section(raw["sections"][0]["ir"])
```

- [ ] **Step 3: テストを実行して失敗を確認**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_matrix_renderer.py::MatrixHeaderlessTest -q`
Expected: FAIL（`showColumnHeaders` 未対応 / `<thead>` が常に出力される）

- [ ] **Step 4: schema に showColumnHeaders を追加**

`skills/visual-explain/references/component-ir.schema.json` の `matrixPayload.properties` の `presentation` 行（現在 155 行）:

```json
        "presentation": {"enum": ["concept", "dense"], "default": "dense"}
```

を次に置き換える:

```json
        "presentation": {"enum": ["concept", "dense"], "default": "dense"},
        "showColumnHeaders": {"type": "boolean", "default": true}
```

- [ ] **Step 5: model に show_column_headers を追加**

`skills/visual-explain/scripts/ve_components/model.py` の `MatrixPayload`（81-87 行）:

```python
@dataclass(frozen=True)
class MatrixPayload:
    rows: tuple[AxisEntry, ...]
    columns: tuple[AxisEntry, ...]
    cells: tuple[MatrixCell, ...]
    highlight_id: Optional[str] = None
    presentation: str = "dense"
```

を次に置き換える:

```python
@dataclass(frozen=True)
class MatrixPayload:
    rows: tuple[AxisEntry, ...]
    columns: tuple[AxisEntry, ...]
    cells: tuple[MatrixCell, ...]
    highlight_id: Optional[str] = None
    presentation: str = "dense"
    show_column_headers: bool = True
```

- [ ] **Step 6: validation に showColumnHeaders を追加**

`skills/visual-explain/scripts/ve_components/validation.py` の `_MATRIX_KEYS`（135 行）:

```python
_MATRIX_KEYS = {"rows", "columns", "cells", "highlightId", "presentation"}
```

を次に置き換える:

```python
_MATRIX_KEYS = {"rows", "columns", "cells", "highlightId", "presentation", "showColumnHeaders"}
```

次に、presentation バリデーション後・`return MatrixPayload(...)` の前（現在 608-627 行の間、concept チェックの後）に `show_column_headers` の検証を追加する。`return MatrixPayload(...)`（現在 623-627 行）:

```python
    return MatrixPayload(
        rows=rows, columns=columns, cells=tuple(cells),
        highlight_id=highlight_id if isinstance(highlight_id, str) else None,
        presentation=presentation,
    )
```

を次に置き換える:

```python
    show_column_headers = raw.get("showColumnHeaders", True)
    if not isinstance(show_column_headers, bool):
        col.add(INVALID_COMPONENT_PAYLOAD, "showColumnHeaders は真偽値である必要があります", path)
        show_column_headers = True
    if presentation == "concept" and show_column_headers is False:
        col.add(INVALID_COMPONENT_PAYLOAD, "showColumnHeaders=false は dense モードでのみ有効です", path)
        show_column_headers = True
    return MatrixPayload(
        rows=rows, columns=columns, cells=tuple(cells),
        highlight_id=highlight_id if isinstance(highlight_id, str) else None,
        presentation=presentation,
        show_column_headers=show_column_headers,
    )
```

- [ ] **Step 7: renderer で thead を条件出力**

`skills/visual-explain/scripts/ve_components/renderers/matrix.py` の `_render_dense_table` シグネチャ（39 行）に `show_column_headers` を追加:

```python
def _render_dense_table(matrix, cert_by_id, src_by_id, cell_by_key, takeaway, emphasis_by_id, highlight_id, show_column_headers):
```

同関数末尾の return（現在 73-77 行）:

```python
    return (
        f'<div class="ve-matrix-scroll">'
        f'<table><thead><tr><td class="ve-matrix-corner" aria-hidden="true"></td>{head_cells}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody></table></div>'
    )
```

を次に置き換える:

```python
    thead = (
        f'<thead><tr><td class="ve-matrix-corner" aria-hidden="true"></td>{head_cells}</tr></thead>'
        if show_column_headers else ""
    )
    return (
        f'<div class="ve-matrix-scroll">'
        f'<table>{thead}'
        f'<tbody>{"".join(body_rows)}</tbody></table></div>'
    )
```

そして `render_matrix` の dense 呼び出し（現在 147-150 行）:

```python
    else:
        body = _render_dense_table(
            matrix, cert_by_id, src_by_id, cell_by_key, takeaway, emphasis_by_id, highlight_id,
        )
```

を次に置き換える:

```python
    else:
        body = _render_dense_table(
            matrix, cert_by_id, src_by_id, cell_by_key, takeaway, emphasis_by_id, highlight_id,
            matrix.show_column_headers,
        )
```

- [ ] **Step 8: registry の matrix optionalInputs を更新**

`skills/visual-explain/assets/components/registry.json` の matrix コンポーネントの `optionalInputs`（現在 `["certainty", "sources", "presentation", "highlightId"]`）に `"showColumnHeaders"` を追加する。編集後は次の形:

```json
      "optionalInputs": [
        "certainty",
        "sources",
        "presentation",
        "highlightId",
        "showColumnHeaders"
      ],
```

- [ ] **Step 9: テストとスイートを実行して通過を確認**

Run:
```bash
cd skills/visual-explain/scripts && python3 -m pytest tests/test_matrix_renderer.py tests/test_component_contract.py -q
```
Expected: PASS（`MatrixHeaderlessTest` 含む全件）

- [ ] **Step 10: 見出しなしフィクスチャがフルパイプラインを通ることを確認**

Run:
```bash
cd skills/visual-explain
python3 scripts/build_explainer.py \
  --assembly scripts/tests/component-valid-matrix-headerless.json \
  --output /tmp/ve-headerless.html \
&& bash scripts/check.sh /tmp/ve-headerless.html \
; rm -f /tmp/ve-headerless.html
```
Expected: `OK: /tmp/ve-headerless.html` と最終行 `PASS`

- [ ] **Step 11: コミット**

```bash
cd /Users/yoshidatakumi/workspace/visual-explain
git add skills/visual-explain/references/component-ir.schema.json \
        skills/visual-explain/scripts/ve_components/model.py \
        skills/visual-explain/scripts/ve_components/validation.py \
        skills/visual-explain/scripts/ve_components/renderers/matrix.py \
        skills/visual-explain/assets/components/registry.json \
        skills/visual-explain/scripts/tests/component-valid-matrix-headerless.json \
        skills/visual-explain/scripts/tests/test_matrix_renderer.py
git commit -m "feat(ve): add showColumnHeaders option for headerless matrices"
```

---

### Task 4: ドキュメントと語彙の更新・最終検証

見出しなし＋複数箇条書きマトリックスを「1項目に複数の並列箇条書きを持つ場合の推奨図」として位置づける。enumeration/chevron は「1項目＝1内容」用として据え置く。

**Files:**
- Modify: `skills/visual-explain/references/patterns.md`（選択ガイド `256-268`、matrix 例 `270-306`）
- Modify: `skills/visual-explain/references/design-system.md`（matrix 罫線・見出しなし `78-85`）
- Modify: `skills/visual-explain/references/component-vocabulary.json`（matrix capability/optionalInputs）
- Modify: `skills/visual-explain/SKILL.md`（選択文 `148-150`）

**Interfaces:**
- Consumes: Task 1-3 で確定した挙動（罫線二層・content 配列・showColumnHeaders）。
- Produces: ドキュメントのみ（コードへの影響なし）。

- [ ] **Step 1: patterns.md の選択ガイドに分岐を追加**

`skills/visual-explain/references/patterns.md` の「箇条書き種別 → 図」選択ガイド（256-268 行付近）に、次の判断を明示する一文を追記する（前後の記法に合わせる）:

> 各項目が「1つの内容」なら enumeration（順序なし）/ chevron（順序あり）。各項目が **複数の並列箇条書き** を持つなら、**見出しなしマトリックス**（`matrix@2`, `presentation: "dense"`, `showColumnHeaders: false`, セル `content` を配列）を使う。enumeration/chevron は紺色の図形の右に1内容のみを想定しており、1項目に複数内容を置くとレイアウトが崩れる。

さらに matrix 例節（270-306 行付近）の後に、見出しなし＋配列 content の最小 IR 例を追記する:

```json
"matrix": {
  "showColumnHeaders": false,
  "rows": [{"id": "r1", "label": "戦略・ビジョン"}],
  "columns": [{"id": "c1", "label": "論点"}],
  "cells": [
    {"id": "cell1", "rowId": "r1", "columnId": "c1",
     "content": ["国としての戦略的目標・ビジョンの設定", "各自治体・医療機関・支援企業等の明確な役割・目標設定"]}
  ]
}
```

- [ ] **Step 2: design-system.md に罫線二層・見出しなしを明記**

`skills/visual-explain/references/design-system.md` の matrix 基準（78-85 行付近）に次の2点を追記する:
- dense マトリックスの横罫線は「表頭（列見出し）の下だけ太罫（`--border-strong`）、行見出し・行区切りは細罫（`--border`）」。
- `showColumnHeaders: false` で列見出し行を消した見出しなしマトリックスを作れる。各セルは `content` を配列にすると `・`付きの複数箇条書きになる。「1項目に複数の並列箇条書き」を置く用途で用いる。

- [ ] **Step 3: component-vocabulary.json の matrix を更新**

`skills/visual-explain/references/component-vocabulary.json` の matrix エントリに、`showColumnHeaders` を扱えること（optionalInputs 相当）とセル content が配列を取れることが反映されるよう追記する。既存エントリの表現・キー構造に合わせ、`optionalInputs`（もしくは相当フィールド）へ `showColumnHeaders` を加える。

- [ ] **Step 4: SKILL.md の選択文を更新**

`skills/visual-explain/SKILL.md` の 148-150 行付近（箇条書き系の選択文）に、「1項目に複数の並列箇条書き → 見出しなしマトリックス（`showColumnHeaders: false` ＋ セル `content` 配列）」を1行で追記する。

- [ ] **Step 5: 全テストと check.sh セルフテストを実行**

Run:
```bash
cd skills/visual-explain/scripts && python3 -m pytest tests/ -q
bash ../scripts/check.sh --selftest
```
Expected: pytest 全件 PASS、`selftest: N passed, 0 failed`

- [ ] **Step 6: example が最新 CSS で再ビルド済みか最終確認**

Run:
```bash
cd skills/visual-explain
python3 scripts/build_explainer.py \
  --assembly examples/example-proposal.assembly.json \
  --output /tmp/ve-example-check.html \
&& diff -q /tmp/ve-example-check.html examples/example-proposal.html \
; rm -f /tmp/ve-example-check.html
```
Expected: 差分なし（`diff -q` が無出力）。差分が出たら `examples/example-proposal.html` を再ビルド結果で更新する。

- [ ] **Step 7: コミット**

```bash
cd /Users/yoshidatakumi/workspace/visual-explain
git add skills/visual-explain/references/patterns.md \
        skills/visual-explain/references/design-system.md \
        skills/visual-explain/references/component-vocabulary.json \
        skills/visual-explain/SKILL.md
git commit -m "docs(ve): position headerless multi-bullet matrix for multi-item bullet lists"
```

---

## 受け入れ基準（全タスク完了時）

- **Image 1**: 見出しあり dense マトリックスで、一番上の列見出しの下だけ太罫、行区切り（行見出し含む）は細罫。
- **Image 2**: `showColumnHeaders: false` かつ各セルが配列 content の1列マトリックスが、太字行見出し＋各グループの細い区切り＋`・`付き複数箇条書きで描画される。
- 既存 `example-proposal.html` の意味的描画は罫線 CSS 以外変わらない。
- `cd skills/visual-explain/scripts && python3 -m pytest tests/ -q` が全件通過。
- `bash skills/visual-explain/scripts/check.sh --selftest` が 0 failed。
