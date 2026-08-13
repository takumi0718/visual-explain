# Visual-stage deck 実装 plan（visual-explain）

正本 spec: 本 worker dir の `spec.md`（294行）。seed: run dir の `seed-card.md`。本 plan は spec を実装対象とする。

repo root = `<repo-root>`。以下の対象ファイルパスはすべて repo root からの相対パス（`skills/visual-explain/...`）。

## Goal

visual-explain のビルドパイプラインへ Visual-stage deck（案A）を実装する。

- 新 opt-in profile `visual-stage` と canonical IR optional 拡張（`claim` / `sequence` / `assertions`）。
- sequence は skeleton 既存 stepper への静的展開（新規 JS ゼロ）。3 モード（path-spotlight / state-lens / delta-accumulate）を 1 機構に統合。
- 図＝本体＋主張 1 行: 全 12 形式共通の claim 描画層、prose 削除最小化の文書ルール、情報完全性検査。
- 完了条件（spec §5）: ① example-proposal 再ビルドが現行 HTML とバイト一致、② 既存テスト 1 行も修正せず全通過、③ `check.sh` 無修正通過。この 3 点の同時成立。

## Architecture Decisions

- **opt-in profile による隔離**: `documentProfile` enum に `visual-stage` を追加するだけ。`profile != visual-stage` で `claim`/`sequence`/`assertions` を使えば validation error。既存 profile（strict/extended）の挙動は完全不変。新規検査はすべて profile ゲート付きで、既存文書には不発。
- **IR 拡張は optional のみ**: component-ir.schema.json の `required` と既存 `oneOf`（payload 排他）には一切触れない。`claim`（1–80字）、`sequence`（mode + steps 2–8、step は id/label/targetIds のみ・additionalProperties false）、`assertions`（id/text/coverIds）を追加。sequence に HTML/CSS/class/座標に相当するフィールドは持たせない（LLM=what のみ）。
- **id 名前空間の 3 分離**: payload の semantic id 空間・step id 空間・assertion id 空間を分離。step id / assertion id は `semantic_ids()` にも manifest の `consumed_semantic_ids` にも含めない。`targetIds`/`coverIds` の参照可能集合は payload の semantic id のみ。
- **sequence = 静的 panel 展開**: renderer が figure を panel 列として描画する。panel 1 = 完成図（強調なし・renderer が自動先頭生成）、panel k+1 = stage k。全 panel は同一レイアウト・同一 DOM 構造で強調状態のみ異なる。panel 内 DOM id には接尾辞 `--p<p>` を付与し、参照書換えは spec §2 の閉じた allowlist（id/href/xlink:href/for/aria-*・url(#...) 形式属性・inline style 内 url(#...)）と同一集合に限定する。
- **強調は閉じた class allowlist**: 対象 `ve-seq-spot`・非対象 `ve-seq-dim`（`ve-takeaway-target` は既存 profile との共存のため allowlist に残すが visual-stage では出現しない）。強調 CSS は paint-only プロパティ（opacity/outline/outline-offset/box-shadow/color/background-color/fill/stroke）に限定し、checker が静的スキャンで強制（reflow 禁止＝同一座標の構造的担保）。
- **mode 別の強調意味論を固定**: path-spotlight = step のノード＋payload 辺情報から決定論的に導出する辺。state-lens = 当 step の targetIds のみ（非累積）。delta-accumulate = steps 1..k の union（各差分は非空かつ先行 step と不重複）。renderer ごとの独自解釈を禁止。
- **mode×component 許可表を validation 定数に閉じ込める**: path-spotlight=flow のみ、state-lens=flow/matrix/stairs、delta-accumulate=waterfall/bars。mode 別対象種別制約（ノード/状態要素/定量項目）も validation で検査。非許可はすべて validation error。
- **claim は全 12 形式共通の単一ヘルパ**: canonical section 先頭・figure または stepper ラッパの直前に `<p class="ve-claim">` を 1 回だけ挿入する共通関数。個別 renderer に claim 分岐を持たせない。figure 入れ子禁止。stepper 化時もラッパ外・直上に 1 回のみ。
- **CSS は新規 asset に集約**: `assets/components/visual-stage.css` を新設し、既存 12 形式の CSS ファイルは 1 行も変更しない。registry は全 12 component の宣言 asset として同一 asset id `visual-stage`・同一 digest で追加（registry スキーマ不変・version 2 維持）。renderer は新フィールドを持つ IR の描画時のみ出力 asset に含める。
- **dedup キー変更は 1 点のみ**: 実施箇所は `assembly.py::compose_sections()`（dedup キー `(component_id, version, asset.id, digest)` → `(asset.id, digest)`）。flatten.py は不変。controlled-asset checker は同一 asset id を digest 一致時のみ単一 `<style>` へ集約許可。既存 doc では同一 asset id の複数 component 参照が発生しないため挙動不変。
- **パイプライン非侵襲**: `build_explainer.py` 変更不要。`assembly.py` の変更は新フィールドの parse pass-through・dedup キー変更・`CompositionResult` への expected record 追加と `compose_sections()` での集約に限定。renderer の asset 出力は「新フィールドを持つ IR のみ visual-stage.css を含める」条件付き選択を共通層で強制し、既存 IR への CSS 混入を防ぐ。`checker.py` の component 意味検査（`validate_artifact_semantics` / `validate_renderer_svg`）は stepper 化 canonical では panel 単位適用へ変更し、manifest の `generated_landmark_ids` / `svg_root_ids` は接尾辞付き id の panel 別契約とする。`check.sh` の呼び出し構成・引数・終了コードは不変。
- **checker 拡張は document_checks.py に集約**: 情報完全性検査・語句重複検査・sequence 構造検査を profile 条件付きで追加。検査入力は build 時経路（expected 経由の IR↔HTML 照合）と HTML 単体経路（DOM 構造）の 2 系統。`data-ve-claim` 属性は使わず `<p class="ve-claim">` 要素に統一。
- **fail-closed**: すべての新規制約違反は build 失敗。診断は `diagnostics.py` の bounded 出力に乗せる。既存の atomic rename により部分 HTML を残さない。

## Global Constraints

- **skeleton 不変**: `assets/skeleton.html` は 1 バイトも変更しない。可変は TITLE/CONTENT 区間と `VE-CONTROLLED` スロットのみ。stepper ランタイム（`[data-stepper]` + `[data-step]`・prev/next/all ボタン・`.stepper-status` 自動生成・`visual-explain:stepchange`）は skeleton 固定領域の既存物をそのまま利用する。
- **JS 禁止**: 新規 JavaScript はゼロ。sequence は既存 stepper ランタイムで駆動する静的 markup のみ。renderer は `.stepper-status` を生成 markup に含めない（skeleton runtime が実行時生成）。
- **決定論フロア**: LLM=what / trusted library=語彙 / build=how。IR は mode・対象 id・ラベル・主張文のみを持ち、描画 how（座標・class・辺導出・累積計算）はすべて renderer/validation の決定論ロジックに閉じる。
- **検証四層**: `check.sh`（legacy checker ＋ component 契約 ＋ 検査群③）が通ること。呼び出し構成・引数・終了コード契約を変えない。
- **既存 doc 不変**: `examples/example-proposal.assembly.json` 再ビルドが現行 `example-proposal.html` とバイト一致。既存テスト・既存 fixture は 1 行も修正しない（追加テスト・fixture はすべて新規ファイルとし、既存ファイルへの追記も禁止。T17 で git diff による検証を行う）。既存 12 形式の CSS ファイル不変。canonical 12 形式・既存 section-kind を維持し、新 section-kind は作らない。
- **外部依存ゼロ**: build/check/fixture/テストは Python 標準ライブラリのみ。Playwright/Selenium/jsdom・npm/pip パッケージ追加は禁止。1212px の最終確認は人間の目視手順とする。
- **生成 HTML は IR→`build_explainer.py` 経由のみ**。手編集禁止。修正は常に IR→再ビルド。

## Tasks

### T1: schema 3 件の拡張

- 対象: `skills/visual-explain/references/assembly.schema.json`、`skills/visual-explain/references/component-ir.schema.json`、`skills/visual-explain/references/component-vocabulary.json`
- 変更: assembly の `documentProfile` enum に `visual-stage` を追加するのみ（schemaVersion 1・他定義不変）。component-ir のトップレベル properties に optional の `claim`（string 1–80）・`sequence`（required `[mode,steps]`・additionalProperties false・mode enum 3 値・steps minItems 2/maxItems 8・step は required `[id,label,targetIds]`・additionalProperties false・id pattern `^[a-z0-9][a-z0-9-]{0,31}$`・label minLength 1/maxLength 40・targetIds minItems 1/uniqueItems）・`assertions`（minItems 1・要素は required `[id,text,coverIds]`・additionalProperties false・id pattern 同左・text 1–80・coverIds minItems 1/uniqueItems）を追加。`required` と既存 `oneOf` は不変。vocabulary に sequence mode enum と capability `typed-sequence` を schema verbatim で追加。
- 検証: `python3 -c "import json; [json.load(open(p)) for p in ['skills/visual-explain/references/assembly.schema.json','skills/visual-explain/references/component-ir.schema.json','skills/visual-explain/references/component-vocabulary.json']]" && bash skills/visual-explain/scripts/check.sh --selftest`

### T2: model.py の IR dataclass 拡張

- 対象: `skills/visual-explain/scripts/ve_components/model.py`
- 変更: `CanonicalIR` に `claim: Optional[str]`・`sequence: Optional[SequenceDeclaration]`・`assertions: Optional[Tuple[Assertion, ...]]` を追加。`SequenceDeclaration(mode, steps)` / `SequenceStep(id, label, target_ids)` / `Assertion(id, text, cover_ids)` を frozen dataclass として定義。step id・assertion id は `semantic_ids()` に含めない（payload id 空間との分離）。
- 検証: `python3 -m pytest skills/visual-explain/scripts/tests/ -x -q`

### T3: validation.py の profile ゲートと sequence 検査群

- 対象: `skills/visual-explain/scripts/ve_components/validation.py`
- 変更: まず parse/構築の責務所在を正しく取る — raw canonical IR の検証・dataclass 構築は `_validate_canonical_ir()` が担うため、新フィールド（claim/sequence/assertions）の parse と `CanonicalIR(...)` への設定は本タスクでここに実装する（`assembly.py` は構築済み `CanonicalSection` しか受け取らず、ここを通さないと新フィールドは renderer に到達しない）。あわせて profile 検証に `visual-stage` を追加し、非 visual-stage での claim/sequence/assertions 使用を error に。visual-stage では `takeawayTargetIds`/`emphasis`・compatibility 節を error に。mode×component 許可表・mode 別対象種別制約・step id 一意性/pattern・assertion id の文書内一意性・targetIds dangling（payload id のみ参照可）・delta-accumulate の先行 step 不重複・path-spotlight の経路不変条件（1 step ≤4 ノード・step 間辺接続・全 step 互いに素）・claim≡いずれかの assertion・coverIds dangling・narrative 上限（0–2 節・各 200 字以内・定数化）・先頭 first-screen＋直後に主図 canonical・visual-stage canonical の claim/assertions 必須を実装。sequence 保持 IR は `typed-sequence` capability を relationship/selection に要求。
- 検証: `python3 -m pytest skills/visual-explain/scripts/tests/ -x -q`

### T4: registry・dedup キー変更（assembly.py）・expected record 配管

- 対象: `skills/visual-explain/assets/components/registry.json`、`skills/visual-explain/scripts/ve_components/assembly.py`、`skills/visual-explain/scripts/ve_components/checker.py`（呼び出し口のみ）
- 変更: (1) registry は全 12 component の宣言 asset に同一 id `visual-stage`・同一 digest で visual-stage.css を追加し、対象 5 形式（flow/matrix/stairs/waterfall/bars）の capabilities に `typed-sequence` を追加（version 2 維持・既存 CSS/digest 不変）。(2) dedup キー変更の実施箇所は `assembly.py::compose_sections()`（現行キー `(component_id, version, asset.id, digest)` → `(asset.id, digest)`。flatten.py は不変）。controlled-asset checker は digest 一致時のみ同一 asset id を単一 `<style>` へ集約許可。(3) assembly は構築済み `CanonicalSection` からの受け渡しのみとし（raw IR の parse/dataclass 構築は T3 の `_validate_canonical_ir()` が担当）、`CompositionResult` に expected record（canonical ごとの component id・instance id・payload semantic id 集合・claim/assertions/sequence）を保持する欄を新設して `compose_sections()` で集約、`checker.py` の `check_final_document()` から `check_document_structure` 系へ expected を渡す引数経路を追加（T12 の coverIds 実在・union カバー・T14 の mode×component 再検査の照合キーはこの record で賄う。`check.sh` の引数・終了コード不変。分岐・描画ロジックは追加しない）。
- 検証: `bash skills/visual-explain/scripts/check.sh --selftest`

### T5: renderer 共通層（claim ヘルパ＋条件付き asset 選択）

- 対象: `skills/visual-explain/scripts/ve_components/renderers/`（共通ヘルパ新設 + 12 renderer の呼び出し口）
- 変更: (1) canonical section 先頭・figure/stepper ラッパ直前に `<p class="ve-claim">` を 1 回だけ挿入する単一の共通関数を実装し、全 12 renderer が figure 生成結果をこのヘルパに通す構造にする。個別 renderer に claim 分岐は持たせない。figure 入れ子禁止・stepper 時はラッパ外直上に 1 回のみ。(2) renderer 共通層に「IR が claim/sequence/assertions のいずれかを持つ場合のみ visual-stage.css を出力 asset に含める」条件付き asset 選択を実装し、全 12 renderer がこの共通判定を通す（現行の無条件全件注入のままでは既存 IR にも新 CSS が混入しバイト一致を破るため）。ヘルパと条件判定の unit test を本タスクで追加する。
- 検証: `python3 -m pytest skills/visual-explain/scripts/tests/ -x -q`

### T6: visual-stage.css 新規 asset

- 対象: `skills/visual-explain/assets/components/visual-stage.css`（新規）
- 変更: `ve-seq-spot`/`ve-seq-dim` の強調スタイル（paint-only: opacity/outline/outline-offset/box-shadow/color/background-color/fill/stroke のみ）、`.ve-claim` の装飾、flow+path-spotlight の折返し配置（flex-wrap・固定 flex-basis/max-width W・`overflow-wrap: anywhere`・`box-sizing: border-box`）を定義。W・gap・C（skeleton トークン由来の利用可能内幅）は固定値とし 4W＋gap×3 ≤ C を満たす。既存 12 形式の CSS は不変。
- 検証: `bash skills/visual-explain/scripts/check.sh --selftest`

### T7: sequence 静的展開コア（panel 生成基盤）

- 対象: `skills/visual-explain/scripts/ve_components/renderers/`（sequence 展開の共通基盤）
- 変更: sequence 付き IR の figure を panel 列として描画する共通ロジックを実装。panel 1 = 完成図（強調なし）を自動先頭生成、panel k+1 = stage k。全 panel 同一レイアウト・同一 DOM 構造。panel 内 DOM id に `--p<p>` 接尾辞を付与し、参照書換えは閉じた allowlist（id/href/xlink:href/for/aria-labelledby/aria-describedby/aria-owns・connector data 参照属性・url(#...) 形式属性・inline style 内 url(#...)）に限定（属性名は validation 定数として列挙）。ラッパ `<div data-stepper data-total-steps="N+1">`・各 panel `data-step`・操作部 `button[data-step-action="previous|next|all"]`（next ボタンは `data-next-label` に汎用文）を skeleton 契約どおり生成。各 panel 末尾に「次の段階: 」＋次 step label の予告行（最終 panel は「これで全段階です」）を IR の値から生成。強調集合の計算（mode 別意味論）もここに集約。panel 展開時は各 renderer の `RenderManifest`（`generated_landmark_ids`/`svg_root_ids`）を接尾辞付き panel 別 ID 群として生成し、`render_canonical()` が final checker より前に行う renderer markup 内 SVG ID と manifest の厳密比較を panel 構造のまま通過させる（T11 の checker 変更だけではここで先に失敗するため、本タスクの責務とする）。panel 展開の unit test を本タスクで追加する。
- 検証: `python3 -m pytest skills/visual-explain/scripts/tests/ -x -q`

### T8: flow.py の sequence 分岐（path-spotlight / state-lens）

- 対象: `skills/visual-explain/scripts/ve_components/renderers/flow.py`
- 変更: sequence 有無の内部分岐を追加し、既存 figure 生成関数を強調セット違いで呼び直す。path-spotlight では当 step のノード列を順に結ぶ辺＋先行 step 末尾→当 step 先頭の接続辺を payload 辺情報から決定論的に導出して強調。ノードを 1 行 ≤4 の折返し配置で描画。connector markup 契約（panel 内 `data-connect-scope`・ノード DOM id・辺 `data-connect`）を各 panel に出力し、id・参照は `--p<p>` 接尾辞で同一 panel 内に閉じる。辺導出の unit test を本タスクで追加する。
- 検証: `python3 -m pytest skills/visual-explain/scripts/tests/ -x -q`

### T9: matrix.py / stairs.py の sequence 分岐（state-lens）

- 対象: `skills/visual-explain/scripts/ve_components/renderers/matrix.py`、`skills/visual-explain/scripts/ve_components/renderers/stairs.py`
- 変更: sequence 有無の内部分岐を追加し、state-lens の強調セット（当 step の targetIds のみ・非累積）で既存 figure 生成を呼び直す。対象は matrix のセル・stairs のステップの id のみ（validation が種別を担保）。各 panel はそれ自体が component 契約を満たす完全な instance。両形式の強調セット unit test を本タスクで追加する。
- 検証: `python3 -m pytest skills/visual-explain/scripts/tests/ -x -q`

### T10: waterfall.py / bars.py の sequence 分岐（delta-accumulate）

- 対象: `skills/visual-explain/scripts/ve_components/renderers/waterfall.py`、`skills/visual-explain/scripts/ve_components/renderers/bars.py`
- 変更: sequence 有無の内部分岐を追加し、delta-accumulate の強調セット（steps 1..k の union・renderer が累積計算）で既存 figure 生成を呼び直す。未到達項目は描画したまま `ve-seq-dim`（非表示にしない＝レイアウト同一性維持）。対象は定量項目 id のみ。両形式の累積強調 unit test を本タスクで追加する。
- 検証: `python3 -m pytest skills/visual-explain/scripts/tests/ -x -q`

### T11: checker.py の panel-aware 化

- 対象: `skills/visual-explain/scripts/ve_components/checker.py`
- 変更: `check_final_document()` が呼ぶ `validate_artifact_semantics()`（項目数計数）と `validate_renderer_svg()`（canonical あたり SVG 1 個・id=`<instance>-svg`）を、stepper 化 canonical では各 `[data-step]` panel の部分木へ panel 単位に適用するよう変更。manifest の `generated_landmark_ids` / `svg_root_ids` を接尾辞付き id（例: `<instance>-svg--p2`）の panel 別契約にする。文書内 ID 一意性は接尾辞付き id に対して従来どおり実施し、semantic id の一意性・payload 対応は panel 1 を正本として判定する。legacy 固定領域・禁則検査には手を入れない。CLI・build 時経路の双方が同関数を呼ぶ構成は維持。
- 検証: `bash skills/visual-explain/scripts/check.sh --selftest`

### T12: document_checks.py 検査 1（情報完全性・profile ゲート付き）

- 対象: `skills/visual-explain/scripts/ve_components/document_checks.py`
- 変更: visual-stage のみ発火する情報完全性検査を追加（非 visual-stage では早期 return）。IR 情報は T4 の引数経路経由で `check_final_document()` から受け取る expected record を入力とする。全 canonical の claim/assertions 保有・claim≡いずれかの assertion・IR claim テキストの `.ve-claim` への一致出現（build 時経路で expected から照合）・全 assertion の coverIds 実在・payload 全 semantic id の union カバー・sequence の targetIds 実在と step id 一意・narrative 上限を fail-closed で検査。診断は diagnostics.py 経由で bounded 出力。
- 検証: `python3 -m pytest skills/visual-explain/scripts/tests/ -x -q`（profile ゲートで既存テストに不発であることを確認。検出系・非検出系の unit test は T17）

### T13: document_checks.py 検査 2（claim/narrative 語句重複）

- 対象: `skills/visual-explain/scripts/ve_components/document_checks.py`
- 変更: 各 canonical の全 assertion の text（claim 含む inventory 全文）と narrative markup のプレーンテキストを照合。比較前に HTML entity デコード→Unicode NFKC→空白・句読点・記号除去を施し、10 文字以上の共通部分文字列を error とする固定アルゴリズムで実装。照合対象は assertion text のみ（narrative 同士・closing は対象外）。許容例外リストは持たない。
- 検証: `python3 -m pytest skills/visual-explain/scripts/tests/ -x -q`（同上・検出系 unit test は T17）

### T14: document_checks.py 検査 3（sequence 構造）＋ CSS 静的スキャン

- 対象: `skills/visual-explain/scripts/ve_components/document_checks.py`
- 変更: 描画結果の再検証として、step 数 ≤8・panel 数 = steps+1・mode×component 許可表・`data-step` 連番と `data-total-steps` 一致・stepper 契約（`[data-stepper]`・prev/next/all ボタン）・panel 1 が強調 class を持たない完成図・panel 内 id の `--p<p>` 接尾辞と panel 内閉鎖参照・正規化規則適用後の panel DOM 同一性を検査（`.stepper-status` は要求しない）。あわせて visual-stage.css の静的スキャンを実装。paint-only allowlist 検査の適用範囲は**強調 class（`ve-seq-spot`/`ve-seq-dim`/`ve-takeaway-target`）の宣言ブロックのみ**とし（セレクタを解析して対象ブロックを特定）、`.ve-claim` 装飾や flow 折返し配置（flex-basis/max-width 等の通常 layout ルール）は対象外とする。対象ブロック内で border/padding/margin/font-\*/display/width/height/transform 等を検出したら error。加えて幅定数の検算（4W＋gap×3 ≤ C・C は skeleton のコンテンツ領域トークンから導出）。
- 検証: `python3 -m pytest skills/visual-explain/scripts/tests/ -x -q`（同上・検出系 unit test は T17）

### T15: 正常系 fixture 6 件（許可表の全組合せ）

- 対象: `skills/visual-explain/scripts/tests/`（fixture 追加）
- 変更: visual-stage profile の assembly fixture を 6 件追加（すべて新規ファイル）: flow+path-spotlight（承認地図ステッパー。basename を `vs-flow-path-spotlight.assembly.json` に固定し T17 の目視確認から参照）・flow+state-lens・matrix+state-lens・stairs+state-lens・waterfall+delta-accumulate・bars+delta-accumulate。ビルド成功・stepper 構造・panel 1 完成図・claim 描画・panel id 接尾辞に加え、各 mode の強調意味論（各 panel の `ve-seq-spot` 基底 id 集合が契約どおり・非対象が `ve-seq-dim`・path-spotlight の辺導出）を検証するテストを追加。あわせて claim のみ・sequence なし IR を全 12 形式について生成し `.ve-claim` が section 先頭に 1 回だけ描画される parametrized test を追加。
- 検証: `python3 -m pytest skills/visual-explain/scripts/tests/ -x -q -k visual_stage`

### T16: bad fixture（違反条件ごとに独立・計 46 件）

- 対象: `skills/visual-explain/scripts/tests/`（bad-* fixture 追加・すべて新規ファイル）
- 変更: **1 違反 = 1 fixture** とし、各 fixture に期待診断を個別定義する（複数違反の同居は先発診断で通過するため禁止・境界値の両側も別件とする）。対象条件（各 1 件・計 46）: step 9 件超過／steps 1 件（minItems 2 違反）／非許可 mode×component（bars+path-spotlight）／dangling targetId／targetIds が step id を参照／step id 重複／step id pattern 違反／step への未知フィールド混入／label 空文字列／label 41 字超過／targetIds 空配列／targetIds 内重複／mode 別対象種別違反（state-lens が source 注記 id を参照）／visual-stage で compatibility 節／claim 欠落／assertions 欠落／assertions 空配列／assertion id pattern 違反／assertion id 文書内重複／assertion text 空／assertion text 81 字超過／coverIds 空配列／coverIds 内重複／coverId dangling／claim がいずれの assertion text とも不一致／カバー率不足／delta-accumulate で先行 step と重複／path-spotlight で step 間が辺非接続／path-spotlight で step 間 targetIds 重複／narrative 3 節／narrative 200 字超過／claim と narrative の語句重複／非 claim assertion text の narrative 残存／非 visual-stage で claim 使用／非 visual-stage で sequence 使用／非 visual-stage で assertions 使用／visual-stage で takeawayTargetIds 使用／visual-stage で emphasis 使用／required 欠落 8 件（sequence.mode・sequence.steps・step.id・step.label・step.targetIds・assertion.id・assertion.text・assertion.coverIds の各欠落）。
- 検証: `python3 -m pytest skills/visual-explain/scripts/tests/ -x -q -k bad`

### T17: 回帰保証の最終確認（完了条件ゲート）

- 対象: `skills/visual-explain/scripts/tests/`（checker unit test 追加）＋ 既存検証の無修正通過確認
- 変更: 情報完全性・語句重複・sequence 構造・paint-only 静的スキャン・幅定数検算の各検査に検出系・非検出系（既存 profile では不発）の unit test を追加。最終ゲートとして 3 点を同時確認: ① `example-proposal.assembly.json` 再ビルドが現行 `example-proposal.html` とバイト一致、② 既存テスト全通過（1 行も修正しない）、③ `check.sh` 無修正通過。1212px 目視確認は次の artifact と checklist で人間が実行: 生成コマンド `python3 skills/visual-explain/scripts/build_explainer.py skills/visual-explain/scripts/tests/fixtures/vs-flow-path-spotlight.assembly.json /tmp/visual-stage-flow-path-spotlight.html`（fixture パスは T15 で固定・既存 fixture 配置規約に従う。pytest 一時生成物ではなく永続ファイルを明示生成）→ 生成 HTML を 1212px 幅のブラウザで開き checklist (a) 各 panel で overflow 非発生 (b) step 切替で強調経路を追跡可能 (c) 予告行と status が可読、を確認 → 合否を `/tmp/visual-stage-flow-path-spotlight.checklist.txt` に記録。さらに「既存テスト不変」の検証手順として、追加テスト・fixture はすべて新規ファイルとし（既存ファイルへの追記禁止）、`git diff --exit-code -- skills/visual-explain/scripts/tests/ skills/visual-explain/examples/` で既存ファイルの変更が 0 件であることを確認する（untracked の新規ファイルは対象外）。
- 検証: `bash skills/visual-explain/scripts/check.sh --selftest && python3 -m pytest skills/visual-explain/scripts/tests/ -q && python3 skills/visual-explain/scripts/build_explainer.py skills/visual-explain/examples/example-proposal.assembly.json /tmp/example-proposal.rebuilt.html && cmp /tmp/example-proposal.rebuilt.html skills/visual-explain/examples/example-proposal.html`

## Dependency Order

1. **T1（schema）** → すべての土台。契約の正本を先に固定する。
2. **T2（model.py）** → T1 に依存。IR 構造の parse 層。
3. **T3（validation.py）** → T1・T2 に依存。profile ゲート・許可表・経路不変・文書ルールの検査層。
4. **T6（visual-stage.css）** → T1–T3 と独立。registry が本ファイルの digest を参照するため、T4 より先に内容を確定する。
5. **T4（registry/assembly dedup/expected 配管）** → T1–T3・T6 に依存。asset 登録（digest 確定済み）と pass-through・expected 経路の確立。
6. **T5（renderer 共通層）** → T2 に依存。claim ヘルパと条件付き asset 選択。
7. **T7（sequence 展開コア）** → T2・T3 に依存。T8–T10 の共通基盤。
8. **T8（flow）/ T9（matrix,stairs）/ T10（waterfall,bars）** → T5・T6・T7 に依存。3 つは相互独立で並行可能。
9. **T11（checker panel-aware 化）** → T7–T10 に依存。panel 構造が確定してから意味検査を追随させる（ここを先に変えないと正常な複数 panel が新規検査より先に失敗する）。
10. **T12・T13・T14（document_checks 3 検査）** → T3・T5–T10 に依存。3 タスクは同一ファイル `document_checks.py` を変更し profile gate・DOM parse・診断経路を共有するため**順次実行（T12→T13→T14）**とし、共通部分を重複実装しない。
11. **T15（正常 fixture 6）** → T1–T14 の実装完了後。許可表全組合せの統合検証。
12. **T16（bad fixture 46）** → T1・T3・T12–T14 の検査実装完了後。T15 と並行可能。
13. **T17（回帰ゲート）** → 全タスク完了後の最終ゲート。example バイト一致・pytest 全通過・check.sh --selftest の 3 点同時成立で完了。

## Coverage Mapping

| spec 項目 | タスク |
|---|---|
| §1 assembly.schema profile enum 拡張 | T1 |
| §1 component-ir.schema claim/sequence/assertions（sequence/step/assertion の required・step 上限 8・step id pattern・label 1–40・minItems/uniqueItems 各種・additionalProperties false） | T1 |
| §1 新フィールドの parse・CanonicalIR 構築（責務: validation.py の `_validate_canonical_ir()`） | T3 |
| §1 assertion id の文書内一意性（validation 専用検査） | T3 |
| §1 component-vocabulary（mode enum・typed-sequence・verbatim コピー） | T1 |
| §1 sequence 保持 IR への typed-sequence capability 要求（relationship/selection） | T3 |
| §1 model.py（claim/sequence/assertions・frozen dataclass・id 名前空間分離） | T2 |
| §1 後方互換（opt-in 強制・takeaway/emphasis 禁止・未知 mode/dangling の fail-closed） | T3 |
| §2 sequence 静的展開（panel 1 完成図・同一レイアウト・正規化規則・`--p<p>` 接尾辞・予告行二重化・data-next-label・stepper ラッパ・操作部ボタン） | T7 |
| §2 文書内 ID 一意性（接尾辞付き id）・semantic id 判定の panel 1 正本化 | T11 |
| §2 RenderManifest の panel 別 ID 群（render_canonical の事前厳密比較を panel 構造で通過） | T7 |
| §2 3 モード意味論（path-spotlight 辺導出・state-lens 非累積・delta-accumulate union） | T7・T8・T9・T10 |
| §2 mode×component 許可表・mode 別対象種別制約 | T3 |
| §2 経路不変条件（≤4 ノード/step・step 間辺接続・互いに素） | T3 |
| §2 レイアウト契約（1 行 ≤4 折返し・固定 W・overflow-wrap・4W＋gap×3 ≤ C） | T6・T8・T14 |
| §2 connector markup 契約（data-connect-scope・data-connect・panel 内閉鎖参照） | T8 |
| §2 claim 共通層（全 12 形式・単一関数・figure 外直前 1 回） | T5 |
| §2 visual-stage.css 集約・paint-only 契約・既存 CSS 不変 | T6・T14 |
| §2 registry 変更（全 12 component 同一 asset id/digest・capability 追加・version 2 維持） | T4 |
| §2 dedup キー変更（実施箇所: assembly.py::compose_sections・flatten.py 不変）・controlled-asset checker 集約許可 | T4 |
| §2 renderer 条件付き asset 出力（新フィールド保持 IR のみ visual-stage.css を注入） | T5 |
| §2 assembly.py pass-through・build_explainer.py 不変 | T4 |
| §4 expected record（component id・instance id・payload semantic id 集合を含む・CompositionResult 拡張・compose_sections 集約・checker への引数受け渡し） | T4・T12 |
| §3 claim 描画位置の正規 markup 固定 | T5 |
| §3 first-screen 直後の主図 canonical 配置要求 | T3 |
| §3 prose 削除最小化（narrative 0–2 節・200 字以内・compatibility 禁止・canonical の claim/assertions 必須） | T3 |
| §4 checker.py panel-aware 化（validate_artifact_semantics/validate_renderer_svg・manifest panel 別契約） | T11 |
| §4 検査 1 情報完全性（claim≡assertion・IR↔HTML 照合・coverIds 実在・union カバー・narrative 上限） | T12 |
| §4 検査 2 語句重複（entity デコード→NFKC→記号除去→10 文字閾値・inventory 全文照合） | T13 |
| §4 検査 3 sequence 構造（panel 数・連番・stepper 契約・panel 1 完成図・接尾辞・DOM 同一性） | T14 |
| §4 CSS 静的スキャン（paint-only は強調 class 宣言ブロックのみ対象・幅定数検算） | T14 |
| §4 既存 doc 通過の保証（profile ゲート不発・CSS 不変・registry/flatten 挙動不変） | T3・T4・T6・T12–T14・T17 |
| §5 正常 fixture 6 件（許可表網羅・強調意味論検証） | T15 |
| §5 claim 共通層 parametrized test（全 12 形式） | T15 |
| §5 bad fixture（1 違反 = 1 fixture・計 46 件・required 欠落と境界値両側を含む） | T16 |
| §5 既存テスト/fixture 変更ゼロの git diff 検証（追加は新規ファイルのみ） | T17 |
| §5 checker unit test（検出系・非検出系） | T17 |
| §5 回帰 3 条件（example バイト一致・既存テスト無修正・check.sh 無修正） | T17 |
| §5 1212px 目視確認（永続 HTML の生成コマンド・checklist・記録先） | T17 |
| §5 fail-closed・bounded 診断・atomic rename 利用 | T3・T12–T14 |

DELIVERABLE: written
