# Matrix: 罫線の二層化と見出しなし（複数箇条書き）モード 設計

日付: 2026-07-14
対象: `skills/visual-explain` の `matrix@2` コンポーネント

## 背景・目的

現行の dense マトリックスには2つの課題がある。

1. **罫線の太さ**: dense モードでは列見出し `<th scope="col">` と行見出し
   `<th scope="row">` の両方が太い罫線（`1.5px --border-strong`）を持ち、行の区切りが
   過剰に強調される（`matrix.css:20-22`）。McKinsey 系レイアウトの基準では
   「表頭の下だけ強く、行区切りは細く」が正しい。

2. **各項目が複数の箇条書きを持てない**: 箇条書き図解（enumeration / chevron）は
   「紺色の四角（または四角＋三角）＋右に1内容」を前提としており、1項目に複数の並列
   箇条書きを置くとレイアウトが崩れる。一方 matrix セルは `content: string` で
   **1セル＝1行**しか描画できず（`matrix.py:69`）、複数箇条書きを表現できない。

本設計は (1) 罫線を二層化し、(2)「見出し行を消した matrix ＝各項目に複数の並列
箇条書きを置く図解」を新設する。(2) は「見出しなし化」と「セルの複数箇条書き対応」の
2つの直交する追加からなる。

## スコープ外

- enumeration / chevron の挙動は変更しない。これらは「1項目＝1内容」用として据え置く。
- concept モード（`ve-mx-grid`）の描画・バリデーション（セル≤6字）は変更しない。
- レガシー matrix（`skeleton.html` 内）には手を入れない。

## 設計

### 1. 罫線の二層化（CSS のみ）

`assets/components/matrix.css` の `.ve-matrix-scroll th`（20-22行）のセレクタを分割する。

- `.ve-matrix-scroll th[scope="col"]` → `border-bottom: 1.5px solid var(--border-strong)`
  （一番上の見出し。太いまま維持）
- `.ve-matrix-scroll th[scope="row"]` → `border-bottom: 1px solid var(--border)`
  （行見出し。各行の `<td>` と同じ細い罫線に変更）

`color: var(--text); font-weight: 800; text-align: left; padding: …` などの共通宣言は
両者に等しく適用されるよう、`th` 共通ルール＋各 `scope` の `border-bottom` 上書き、の
構成にする。concept モードのセル罫線（`.ve-mx-cell` の `1.5px --dg-primary`）は変更しない。

### 2. セルの複数箇条書き対応（見出しあり・なし両方で使える汎用機能）

`matrixCell.content` を `string │ string[]` に拡張する。

- **Schema** (`references/component-ir.schema.json`, `matrixCell.content`):
  `oneOf: [ {type:string,minLength:1}, {type:array,minItems:1,items:{type:string,minLength:1}} ]`
- **Model** (`scripts/ve_components/model.py`, `MatrixCell.content`):
  `str | tuple[str, ...]`。バリデーションで配列は `tuple` に正規化する。
- **Validation** (`scripts/ve_components/validation.py`):
  - content が文字列: 従来通り非空チェック。
  - content が配列: 各要素が非空文字列であること、要素数 ≥1。
  - **concept モードでは content は文字列必須**（配列なら
    `INVALID_COMPONENT_PAYLOAD`）。既存の「≤6字」チェックは文字列前提のまま維持。
- **Renderer** (`scripts/ve_components/renderers/matrix.py`, dense のみ):
  - content が単一文字列 → 従来通りプレーン1行（既存 example と後方互換、見た目不変）。
  - content が配列 → 各行を `・`付きの箇条書き行として描画。enumeration の
    description（`ve-enum-description` / `・` プレフィックス）に倣い、matrix 用の
    クラス（例: `ve-matrix-bullets` / `ve-matrix-bullet`）で `<td>` 内に列挙する。
    emphasis / refs（certainty・source）は従来通りセル末尾に付与する。
  - concept モードは配列を受け取らない（バリデーションで弾く）。

後方互換: 既存の `example-proposal.assembly.json` は全セルが単一文字列のため描画は不変。

### 3. 見出し行を消すオプション

`matrixPayload` に `showColumnHeaders: boolean`（既定 `true`）を追加する。

- **Schema**: `matrixPayload.properties.showColumnHeaders`
  `{type:boolean, default:true}`。`optionalInputs` に追記。
- **Model**: `MatrixPayload.show_column_headers: bool = True`。
- **Validation**:
  - `showColumnHeaders=false` は **dense モードでのみ有効**。concept と併用したら
    `INVALID_COMPONENT_PAYLOAD` を発行し、安全側として `show_column_headers` を
    `True` に強制する（見出しありで描画）。
  - 列（columns）は cell 配置のため引き続き必須（`minItems:1`）。1列でも複数列でも可。
    見出しは描画されないが `label` は schema 上は必須のまま（未使用でも可）。
- **Renderer** (dense):
  - `show_column_headers=false` のとき `<thead>`（コーナーセル＋列見出し `<th scope=col>`）を
    出力しない。`<tbody>` の行見出し `<th scope="row">` と本文セルはそのまま。
  - リクエスト1の CSS 変更により、見出しなし時も行区切りは細い罫線で表示される
    （Image 2 の見た目に一致）。

装飾方針（合意済み）: 行見出し左の丸マーカーは付けない（太字テキストのみ）。ハイライトは
既存のセル `ve-dg-highlight`（`highlightId`）機能をそのまま使う。

### 4. 整合性・ビルド

- `assets/components/registry.json` の `matrix.css` の `digest`（sha256）を
  変更後の CSS で再計算して更新する。`optionalInputs` に `showColumnHeaders` を追記。
- `examples/example-proposal.html` を `build_explainer.py` で再ビルドする
  （埋め込み CSS 本文と `data-ve-digest` が checker で照合されるため）。
  既存例のセルは単一文字列なので出力の意味的差分は罫線 CSS のみ。

### 5. ドキュメント（位置づけ）

「各項目が複数の並列箇条書きを持つ」場合の推奨図を **見出しなしマトリックス** とする。

- `references/patterns.md`: 「箇条書き種別 → 図」選択ガイドに分岐を追加
  （1項目1内容 → enumeration/chevron、1項目に複数の並列箇条書き → 見出しなし matrix）。
  見出しなし＋複数箇条書きセルの記法例を追記。
- `references/design-system.md`: matrix の罫線二層（表頭のみ太罫）と見出しなしモードを明記。
- `references/component-vocabulary.json`: matrix の capability / optionalInputs を更新。
- `SKILL.md`: 選択文と matrix の説明を更新。

## テスト

`scripts/tests/test_matrix_renderer.py`（および関連 contract テスト）に追加:

1. 罫線: dense 出力の列見出し `th[scope=col]` と行見出し `th[scope=row]` が
   意図した border を持つこと（CSS はレンダラ出力の構造で担保、必要なら CSS 文字列を確認）。
2. 複数箇条書きセル: `content` が配列のとき `・`付き複数行が `<td>` 内に描画されること。
   単一文字列のとき従来通り1行であること（後方互換）。
3. 見出しなし: `showColumnHeaders=false` で `<thead>` が出力されないこと、
   行見出し・本文セルが残ること。
4. バリデーション: concept モードで content 配列 → エラー。
   concept モードで `showColumnHeaders=false` → エラー発行かつ true に強制。
5. 既存 4層チェッカー・`test_component_contract.py`・`test_skeleton_audit.py` が通ること。
6. digest 再計算後、`examples/example-proposal.html` 再ビルドで checker が通ること。

## 受け入れ基準

- Image 1: 見出しあり dense matrix で、一番上の列見出しの下だけ太罫、行区切りは細罫。
- Image 2: `showColumnHeaders=false` かつ各セルが複数箇条書きの1列 matrix が、
  太字行見出し＋各グループの細い区切り＋`・`付き複数箇条書きで描画される。
- 既存 `example-proposal.html` の意味的描画は罫線 CSS 以外変わらない。
- `scripts/check.sh`（4層チェッカー・contract・renderer テスト）が全て通る。
