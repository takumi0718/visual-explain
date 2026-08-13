# Visual-stage deck 設計 spec（visual-explain）

## Overview

visual-explain のビルドパイプライン（`skills/visual-explain/scripts/`・IR・canonical components・skeleton・checker）へ、**Visual-stage deck（案A・2026-08-13 採択）**を実装するための設計 spec。

- **北極星**: 図＝本体＋主張 1 行。動きは**同一図上の typed sequence 1 系統**（経路スポットライト／同一座標ステートレンズ／デルタ累積）に閉じる。
- **決定論境界**: `LLM=what` / trusted library=語彙 / build=how。LLM は how を生成しない。
- **対象見本**: `skills/visual-explain/examples/example-proposal.html`（図あり 2/13 節・図固有は文字量の約 1 割）。
- **採用アプローチ（案A）**: 新 opt-in profile `visual-stage` + canonical IR optional 拡張（`claim` / `sequence` / `assertions`）+ sequence は skeleton 既存 stepper への静的展開（新規 JS ゼロ）。「同一図上」は**同一レイアウトの panel swap（視覚等価）**と定義する。

### v1 must-have（インタビュー確定値）

1. **図先出し・narrative↔図の二重化解消**: 主張 1 行（`claim`）を図に付与し、図が情報を完全に担う。prose は原則削除（削除最小化＝折り畳み・オンデマンド展開は作らない）。
2. **承認地図ステッパー**: flow の `path-spotlight` を v1 主対象とし、1212px で一望不能な承認地図を step 追跡可能にする。
3. **3 モード統合**: 経路スポットライト／同一座標ステートレンズ／デルタ累積を 1 つの `sequence` 機構に統合する。
4. **情報完全性検査**: checker に「prose 削除後も全主張が図に担われているか」の構造検査を追加する。

### Non-goals（v1 外）

- matrix mobile 縮退・ask ピーク化（backlog。matrix mobile 縮退は調査上「成功条件の直接ブロッカー」と位置付けられたが、user が v1 から意図的に除外した項目）。
- 矢印 CSS 貼り合わせ欠陥（flow skip / chevron loop。本見本では未発火・並行バックログ）。
- 新規 JS ランタイム、新 section-kind、入場 fade・stagger・parallax・長文カルーセル・LP 単独モード・2 モード併存。
- 見た目先行の刷新（色・タイポ・入場モーション）、人間読者テストの構築、mobile-first 対応（**desktop-first**。mobile は v2 以降）。

### Hard constraints（全節の前提・抵触禁止）

- **骨格トークン不可侵**: 生成 HTML は `assets/skeleton.html` 由来。可変は TITLE/CONTENT 区間と `VE-CONTROLLED` スロットのみ。skeleton 1 バイトの変更も禁止。
- **決定論フロア**: LLM は what のみ生成。trusted library が語彙、build が how。
- **外部依存ゼロ**: build/check は Python 標準ライブラリのみ（Playwright/Selenium/jsdom・npm/pip パッケージ追加不可）。
- **検証四層**: `check.sh`（legacy checker ＋ component 契約 ＋ 検査群③）が通ること。
- **canonical 12 形式維持**: 新機能は既存 section-kind（first-screen/narrative/canonical/compatibility/ask/closing）と IR で統合し、既存 doc が壊れないこと。
- **生成 HTML は IR→`build_explainer.py` 経由のみ**。手編集禁止・修正は常に IR→再ビルド。
- **JS 追加ゼロ**: sequence は skeleton 固定領域の既存 stepper ランタイムで駆動する。

### 対象リポジトリ構成（実装者向け参照）

- スキルルート: `skills/visual-explain/`
- `assets/skeleton.html`: 骨格。`VE-CONTROLLED` スロットは TITLE / COMPONENT-STYLES / CONTENT / COMPONENT-SCRIPTS の 4 つ。固定領域に汎用 stepper ランタイム（`[data-stepper]` + `[data-step]` パネル、prev/next/全体表示ボタン、`.stepper-status` 自動生成、`visual-explain:stepchange` でコネクタ再描画）が既存。
- `assets/components/registry.json`: component 登録（version 2・CSS digest・capabilities）。
- `references/assembly.schema.json` / `references/component-ir.schema.json` / `references/component-vocabulary.json`: 契約の正本。
- `scripts/build_explainer.py`: ビルド CLI（失敗時は temp file + atomic rename で部分 HTML を残さない）。
- `scripts/ve_components/`: `model.py`（IR dataclass）、`validation.py`（IR 検証）、`assembly.py`、`flatten.py`（スロット注入）、`checker.py`（legacy）、`document_checks.py`（検査群③）、`final_checks.py`、`diagnostics.py`（bounded 診断）、`renderers/`（12 形式の renderer）。
- `scripts/check.sh`: 四層検証のエントリポイント。
- `scripts/tests/`: 既存テスト・bad-* fixture 群。

---

## 1. IR 契約拡張（profile `visual-stage`・`claim`・`sequence`・`assertions`・step 上限）

### assembly.schema.json

- `documentProfile` enum を `["strict", "extended", "visual-stage"]` に拡張する**のみ**。`schemaVersion: 1`・他の section 定義は不変。
- `model.py` の `DocumentMetadata.profile` と `validation.py` の profile 検証が追随する。

### component-ir.schema.json

トップレベル `properties` に optional を 3 件追加（`claim`・`sequence`・`assertions`）。`required` と既存 `oneOf`（payload 排他）は**一切触らない**。

- **`claim`**: string・minLength 1・maxLength 80。図が担う主張 1 行。
- **`sequence`**: object（`additionalProperties: false`、required `["mode", "steps"]`）。
  - `mode`: enum `["path-spotlight", "state-lens", "delta-accumulate"]`（1 図 1 mode・混在不可）。
  - `steps`: array・minItems 2・**maxItems 8（step 上限を schema で強制）**。
  - 各 step: required `["id", "label", "targetIds"]` のみ（`additionalProperties: false`。v1 では step 内に emphasis を持たない。強調は `targetIds` のみで駆動し、段階ごとの追加装飾が必要になった場合は後続 version で契約ごと拡張する）。
    - `id`: string・pattern `^[a-z0-9][a-z0-9-]{0,31}$`。step の識別子（予告・診断に使用。manifest の consumed 集合には含めない）。
    - `label`: string・minLength 1・maxLength 40。「次の段階」予告ラベルに使う（空ラベルは schema で拒否し、予告行が空になることを防ぐ）。
    - `targetIds`: string 配列・minItems 1・uniqueItems true。その step で強調する **payload 内 semantic id** のみを列挙する。
  - **id 名前空間の分離**: payload の semantic id 空間と step id 空間は別とする。`targetIds` の dangling 参照検査は **payload の semantic id のみ**を参照可能集合とし、step id を参照した場合は validation error とする。step id は `semantic_ids()` には含めず、文書内一意性は validation 層の専用検査で担保する（model.py の分離規則と一致）。
- sequence には HTML/CSS/class/座標に相当するフィールドを**持たせない**（LLM=what のみ。mode・対象 id・ラベルだけ）。
- **`assertions`**: array（visual-stage の canonical では required・minItems 1。profile 条件付きのため validation が強制する）。**主張 inventory の正本**であり、prose 削除の前後に依存せず IR 上に独立して宣言される。各要素は object（`additionalProperties: false`・required `["id", "text", "coverIds"]`）:
  - `id`: string・pattern `^[a-z0-9][a-z0-9-]{0,31}$`（assertion id 空間は payload・step とも分離）。
  - `text`: string・minLength 1・maxLength 80。主張文（what のみ）。
  - `coverIds`: string 配列・minItems 1・uniqueItems true。その主張を担う payload 内 semantic id（参照可能集合は payload id のみ）。
  - `claim` のテキストはいずれかの assertion の `text` と一致すること（主張 1 行は inventory の一要素であり、inventory と無関係な claim を禁止）。

### 語彙の正本（component-vocabulary.json）

- sequence mode enum と capability `"typed-sequence"` を追加し、schema は verbatim コピー（`test_component_contract.py` の drift 検査に自動で乗る）。
- sequence を持つ IR は `relationship.capabilities` と `selection.matchedCapabilities` に `typed-sequence` を含めることを validation が要求する。
- registry は対象 component（§2 の許可表にある 5 形式）の `capabilities` に `typed-sequence` を**追加**するだけで version 2 を維持（capability 追加は後方互換。既存 IR は宣言しないため検証結果不変。capability は生成 HTML に埋め込まれず、既存エントリの CSS digest も不変）。

### model.py

- `CanonicalIR` に `claim: Optional[str]`・`sequence: Optional[SequenceDeclaration]`・`assertions: Optional[Tuple[Assertion, ...]]` を追加。
- `SequenceDeclaration(mode, steps)` / `SequenceStep(id, label, target_ids)` / `Assertion(id, text, cover_ids)` は frozen dataclass。
- step id と assertion id は **payload の semantic id 体系には載せない**（`semantic_ids()`・manifest の `consumed_semantic_ids` のいずれにも含めない）。これらは IR レベルの識別子であり、文書内一意性は validation 層の専用検査で担保し、DOM への出現は要求しない（manifest-to-DOM gate の対象外とし、既存の消費検査を壊さない）。
- `targetIds` の dangling 参照は既存 `takeawayTargetIds` と同型の検査で fail-closed とするが、参照可能集合は payload の semantic id に限定する（step id は参照不可）。

### 後方互換（IR 層）

- 全追加は optional のため既存 IR（`example-proposal.assembly.json` 含む）は無変更で valid・描画不変。
- **`profile != visual-stage` で `claim`/`sequence`/`assertions` を使った場合は validation error**（opt-in 強制。既存 profile の挙動は完全不変）。
- **visual-stage では `takeawayTargetIds` / `emphasis` を validation error** とする（強調は sequence の spotlight に一本化し、panel 1「強調なし完成図」との二義性と二重強調を排除）。
- 未知 mode・step 超過・dangling 参照も全て診断付き validation error で build 失敗。

---

## 2. レンダラ拡張と sequence の静的展開

### stepper への載せ替え（静的展開手順）

sequence を持つ canonical IR の renderer は、figure を 1 つではなく **panel 列**として描画する。

- **panel 1**: 完成図（強調なし・全情報）。renderer が自動先頭生成する。
- **panel k+1**（k=1..N、N=len(steps)≤8）: stage k のバリアント。
- 全 panel は**同一レイアウト・同一 DOM 構造**で、強調状態のみが異なる（panel swap＝視覚的に同一図上のレンズ）。「同一」の比較は次の**正規化規則**で定義する: 比較対象は要素木（タグ名・子要素の順序）・属性・テキストノードとし、次を正規化（除外）する — (a) `data-step` 属性値、(b) **id 参照の正規化**: 次の閉じた allowlist の属性・値形式から panel 接尾辞 `--p<p>` を除去して基底 id に正規化する — 属性: `id`・`href`・`xlink:href`・`for`・`aria-labelledby`・`aria-describedby`・`aria-owns`・connector が使用する data 参照属性（renderer が使用する属性名を validation 定数として列挙）。値形式: 上記属性の値に加え、`url(#...)` 形式を取りうる属性（`clip-path`・`mask`・`filter`・`marker-start`・`marker-mid`・`marker-end`・`fill`・`stroke`）および inline `style` 属性内の `url(#...)`。`aria-labelledby` 等の空白区切り IDREF リストは各トークンに適用。allowlist 外の参照形式を renderer が新規に使うことは禁止、(c) 強調状態 class（allowlist: `ve-seq-dim`・`ve-seq-spot`・`ve-takeaway-target`）と stepper 状態（**閉じた列挙**: 属性 `hidden`・`aria-hidden`・`aria-current`・`tabindex`、class `is-current`。これらは比較前に除去し値は問わない。runtime/renderer がこれ以外の状態属性・class を使う場合は本規則の改訂が必要）、(d) 予告行要素（`ve-seq-next` class を持つ要素の子孫テキスト）。これら以外に差異があれば構造検査で error。
- **panel 内 ID の名前空間**: renderer は panel p（p=1..N+1）内の全 DOM id に接尾辞 `--p<p>` を付与して複製する（例: `node-approve--p3`）。接尾辞の付与と参照書換えの対象は正規化規則 (b) の閉じた allowlist と**同一の集合**とし、connector 等の内部参照は同一 panel 内の接尾辞付き id のみを指す。文書内 ID 一意性検査は接尾辞付き id に対して従来どおり実施し、semantic id の一意性・payload 対応は panel 1 を正本として判定する。
- ラッパ: `<div data-stepper data-total-steps="N+1">`。各 panel は `data-step="1..N+1"`。操作部は skeleton 契約どおり `button[data-step-action="previous|next|all"]`。
- **無操作の不変条件**: panel 1＝完成図で構造的に担保し、「全体表示」ボタンが全段階の同時表示を担う。
- **予告は二重**: next ボタンは `data-next-label` に汎用文（例:「次へ: 次の段階を強調表示」）を置き（skeleton は静的 1 ラベルのみ対応）、**各 panel 内の末尾に renderer が「次の段階: 」＋ IR の次 step の `label` を連結した予告行を生成**して結果予告を具体化する（最終 panel は「これで全段階です」。いずれも renderer が IR の値から生成する確定文字列であり、placeholder ではない）。
- status の開始/終了/総数予告は skeleton 既存の `.stepper-status` が担う（**skeleton runtime が実行時に自動生成するため、renderer は生成 markup に含めない**。静的検査でも要求しない。§4 参照）。
- flow のレール/コネクタは skeleton が stepchange で再描画するため panel swap 後も追従する。
- 各 panel は**それ自体が既存 component 契約を満たす完全な component instance**として描画する（SVG 個数・項目数・必須構造を panel 内で完結）。component 契約検査の panel 単位適用は §4 のとおり。

### 3 モードの意味論

いずれも stage ごとの強調対象は IR の `targetIds` が what として明示し、renderer は強調の how のみ担う。強調状態 class は**閉じた allowlist**に固定する: 対象には `ve-seq-spot`、非対象には `ve-seq-dim`。`ve-takeaway-target` は visual-stage では takeaway を禁止するため sequence panel 内には出現しない（allowlist に残すのは既存 profile の描画との共存のため）。これ以外の強調 class を renderer が新設することは禁止。強調集合の定義は mode ごとに次のとおり固定し、renderer ごとの独自解釈を禁止する。

- **`path-spotlight`**: stage k の強調集合 = step k の `targetIds` のノード **＋ renderer が導出する辺**（flow payload の辺のうち、当 step のノード列を順に結ぶ辺、および先行 step の末尾ノードと当 step の先頭ノードを結ぶ接続辺）。辺の導出は payload の辺情報から決定論的に行い、IR は辺を指定しない（孤立したノード群だけが点灯する実装を排除）。非対象のノード・辺は `ve-seq-dim`。経路の部分集合を段階的に照らす。承認地図ステッパーの中核。
- **`state-lens`**: stage k の強調集合 = step k の `targetIds` のみ（非累積）。同一座標のまま状態（現在地・該当セル）だけを段階移動する。
- **`delta-accumulate`**: 各 step の `targetIds` はその段階で**新たに積み上げる差分**を表し、stage k の強調集合 = steps 1..k の `targetIds` の **union**（累積は renderer が計算する）。**各差分は非空（schema の minItems 1）かつ先行する全 step の `targetIds` と重複しない**こと（validation error。同じ id の再指定で累積が変化しない段階を禁止し、各段階の単調増加を保証）。未到達項目（steps k+1..N の対象）は描画したまま `ve-seq-dim` とする（非表示にはしない＝全 panel のレイアウト同一性を維持）。

### mode×component 許可表（v1・validation.py の定数。非許可は validation error）

| mode | flow | matrix | stairs | waterfall | bars | 他 7 形式 |
|---|---|---|---|---|---|---|
| path-spotlight | ✓（主対象） | – | – | – | – | – |
| state-lens | ✓ | ✓ | ✓ | – | – | – |
| delta-accumulate | – | – | – | ✓ | ✓ | – |

- **mode 別の対象種別制約**（validation が検査）: `path-spotlight` の `targetIds` は flow の**ノード** id のみ、`state-lens` は**状態を持つ要素**（matrix のセル・stairs のステップ・flow のノード）の id のみ、`delta-accumulate` は**定量項目**（waterfall の項目・bars のバー）の id のみを許す。certainty・source・group 等の注記要素や辺 id を対象にした IR は validation error（出典注記だけを移動・累積する IR を構造的に排除）。

### 承認地図（flow+path-spotlight）の成功条件

**経路不変条件**（validation が flow payload の辺情報から検証）:

- 各 step の `targetIds` は経路上で連続したノード列とし、**1 step あたり ≤4 ノード**を上限とする。
- **step 間接続**: step k+1 の先頭ノードは step k の末尾ノードの直接の後続（辺で接続）であること。全 step の `targetIds` は互いに素（重複なし）で、連結すると一本の連続した承認経路をなすこと。互いに離れた部分列の寄せ集めは validation error。

**レイアウト契約**（1212px overflow の構造的担保）:

- flow+path-spotlight では renderer がノードを **1 行 ≤4 の折返し配置**で描画し、`visual-stage.css` がコンテナに flex-wrap と最大幅（利用可能内幅の 100%）を強制する。ノード幅は `min-width` ではなく**固定の flex-basis／max-width（定数 W）**で上限化し、ラベルは `overflow-wrap: anywhere` で折り返す（長いラベルによる幅の拡張を構造的に禁止。ノード高は可変）。対象要素は `box-sizing: border-box` を必須とする。合格条件: **4W＋gap×3 ≤ C**（C = 利用可能内幅。skeleton のコンテンツ領域トークンから導出する: main の max-width − 左右 padding − border。viewport 幅 1212px そのものではなく skeleton トークン由来の実内幅を使う）。W・gap・C はすべて CSS の固定値とし、checker が `visual-stage.css` と skeleton の当該トークンを静的に読み取り検算する（panel 化だけでは図の横幅は変わらないため、幅の上限化を契約として明示する）。
- connector は skeleton 既存の再描画（resize/stepchange）が折返し後の配置に追従する。
- **connector markup 契約**: visual-stage の flow 分岐は、skeleton 固定の connector runtime が解釈する markup を各 panel に出力する — panel 内に `data-connect-scope`、ノード要素に DOM id、辺要素に `data-connect` 属性。id・参照は panel 接尾辞規則（`--p<p>`）で書き換え、参照は同一 panel 内に閉じる。既存 flow の semantic checker は panel 単位で適用する（§4）。
- 自動ブラウザ計測は外部依存ゼロの制約上 v1 では行わず、1212px 幅での overflow 非発生と視線追従性の最終確認は §5 の目視確認手順で人間が行う。

### パイプライン統合箇所（非侵襲）

- **claim の描画は全 12 形式共通の共通層**（renderers 共通ヘルパ。canonical section 先頭・figure または stepper ラッパの直前に `<p class="ve-claim">` を挿入する単一関数）として実装し、各 renderer は figure 生成結果をこのヘルパに通す。個別 renderer への claim 分岐は持たせない（12 形式すべてで claim が一貫して描画されることを構造で保証）。
- sequence の静的展開のみ、`renderers/flow.py` 等の対象 5 形式に「sequence 有無の内部分岐」を追加し、既存 figure 生成関数を強調セット違いで呼び直す。
- **`build_explainer.py` は変更不要**。stepper markup は CONTENT スロット内の section markup、script 追加なし。`assembly.py` の変更は **IR の新フィールド（claim/sequence/assertions）を model へ parse し `CompositionResult.expected` へそのまま運ぶ pass-through のみ**に限定する（分岐・描画ロジックは追加しない）。`flatten.py` には **dedup キー変更の 1 点のみ**加える（後述の shared CSS 契約）。
- spotlight/dim・claim 用の CSS は**新規 asset `assets/components/visual-stage.css` に集約**し、既存 12 形式の CSS ファイルは**1 行も変更しない**（→ 既存 doc 再ビルドで注入 `<style>` が変わらず、§5 のバイト一致条件が成立する）。
- **強調 CSS のレイアウト不変契約**: 強調状態 class（`ve-seq-dim`・`ve-seq-spot`・`ve-takeaway-target`）が使ってよいプロパティは paint-only に限定する（allowlist: `opacity`・`outline`・`outline-offset`・`box-shadow`・`color`・`background-color`・`fill`・`stroke`）。`border`・`padding`・`margin`・`font-*`・`display`・`width`・`height`・`transform` 等のレイアウト影響プロパティは禁止し、checker が `visual-stage.css` を静的スキャンして違反を error とする（強調切替で reflow しない＝同一座標を構造で担保）。
- `registry.json` への変更: 現行 registry 契約（top-level は `registryVersion`/`components` のみ・asset は component 所属）を維持し、`visual-stage.css` を **全 12 component それぞれの宣言 asset として同一 asset id `visual-stage`・同一 digest で追加**する（既存 CSS ファイルとその digest は不変）。対象 5 形式への `typed-sequence` capability 追加。version 2 維持。component 非所属の shared エントリは導入しない（registry スキーマ不変）。
- renderer は `claim`/`sequence`/`assertions` を持つ IR を描画するときだけ `visual-stage.css` を出力 asset に含める（既存 IR の描画では出力されず、既存 doc のバイト一致を維持）。
- **shared CSS の dedup 契約**: 複数種類の canonical が同一文書で `visual-stage` asset を出力しうるため、`flatten.py` の dedup キーを現行の `(component_id, version, asset.id, digest)` から **`(asset.id, digest)`** へ変更し、controlled-asset checker は slot 内の同一 asset id を **digest が一致する場合に限り** 1 つの `<style>` へ集約して許可する（digest 不一致の同名 asset は従来どおり error）。この変更は既存 doc では同一 asset id の複数 component 参照が発生しないため挙動不変。
- manifest の `consumed_semantic_ids` は従来どおり payload の semantic id のみを対象とする（step id・assertion id は含めない。§1 の分離規則と一致）。

---

## 3. 図先出し構成と prose 削除の文書ルール

### claim の描画位置

- **正規 markup を 1 つに固定する**: canonical section の CONTENT は、先頭に `<p class="ve-claim">` を 1 回だけ置き、直後に図本体を配置する。図本体は、sequence なしなら単一の `<figure data-ve-component>`、sequence ありなら `<div data-stepper>` ラッパ（各 panel は完全な `<figure data-ve-component>` instance）。**claim は figure の外・直前に置き、figure の入れ子は作らない**（accessibility tree と DOM 契約を全 12 形式で一意にする）。装飾は新規 asset `visual-stage.css` の class のみ（既存 component CSS は不変）。
- claim は図の一部として扱い、キャプション・図上・図下の別配置は取らない（1 箇所に固定して二重化を構造的に排除）。
- stepper 化された図でも claim は **stepper ラッパの外・直上に 1 回だけ**描画し、全 panel で共有する（panel ごとの重複描画は禁止）。

### first-screen での図先出し構成

- visual-stage 文書は**先頭節が `first-screen` であること**を validation が要求する。
- visual-stage 文書は `first-screen`（decision＋conditions・契約不変）の**直後に主図となる canonical 節を 1 つ配置**することを validation が要求する（first-screen と主図の間に narrative を挟むと error）。「図到達まで視覚変調なし」（調査 G1/G7）を構造で解消する。
- 主図は `claim`・`assertions` 必須・`sequence` 任意。

### prose 削除最小化の文書ルール（visual-stage のみ適用・validation で強制）

- **残すもの**: first-screen の decision/conditions、closing blocks、ask 節（契約どおり不変）、および図が担えない文脈（背景・制約・用語の前提）だけを記述する narrative。
- **削るもの**: 図の claim を言い換える文、図の内容を列挙・説明する文（「下図のように…」「3 つの柱は…」等）。これらは図が完全に担うため prose 側を削除する。折り畳み・オンデマンド展開は作らない。
- **narrative の上限**: visual-stage では narrative 節は **0〜2 節・各 markup はプレーンテキスト換算 200 字以内**。超過は validation error。上限値は定数として `validation.py` に保持。
- 二重化の判定支援（claim と narrative の語句重複の検査）は §4 の情報完全性検査に統合する。

### visual-stage の節構成と役割

`first-screen`＝判断と条件の提示（不変）→ `canonical(+claim[, +sequence])`＝主張の本体（図＝本体＋主張 1 行）→ `narrative`（任意・最小）＝図が担えない文脈のみ → `ask`＝判断要求（不変・ピーク化は v1 外）→ `closing`＝結論ブロック（不変）。

- canonical 節は複数置いてよいが、**visual-stage の canonical は `claim` と `assertions` の両方を必須**とする（いずれかの欠落も validation error。図先出し・主張 1 行の北極星を全図に適用）。
- **visual-stage では `compatibility` 節を validation error** とする（arbitrary markup 経由で「図＝本体」・prose 上限・情報完全性検査を回避する抜け道を塞ぐ）。
- 既存 profile（strict/extended）にはこれらの規則を一切適用しない。

---

## 4. checker 拡張（情報完全性検査と四層統合）

### 統合方針

- 新規検査はすべて `document_checks.py`（検査群③・文書型を data 属性で読む層）に **profile 条件付き検査として追加**する。
- **検査入力の経路を 2 系統に分けて定義する**:
  - (a) **build 時経路**: `build_explainer.py` が final checking へ渡す `expected`（CompositionResult）を通じて元 IR を受け取り、IR↔HTML 照合（claim 転記一致・targetIds 実在・カバー率）を行う。既存の受け渡し経路に乗せるため `check.sh` の引数・呼び出し構成は不変。
  - (b) **HTML 単体経路**: HTML のみを検査する経路では、描画 DOM の構造（`.ve-claim` 要素・panel 接尾辞規則・stepper 属性）を検査入力とし、IR を必要とする照合（claim テキスト一致等）は build 時経路でのみ実行する。**`data-ve-claim` 属性は使わない**（claim の DOM 契約は `<p class="ve-claim">` 要素に統一し、renderer と checker が同一契約を参照する）。
- `profile != visual-stage` の文書では新検査は**一切発火しない**（早期 return）ことで、既存 doc・既存テストの通過を構造的に保証する。
- legacy checker の固定領域・禁則検査（トークン・禁則タグ等）には手を入れない。一方、`checker.py` の **component 意味検査は panel-aware 化が必須**: `check_final_document()` が呼ぶ `validate_artifact_semantics()`（canonical 全体での項目数計数）と `validate_renderer_svg()`（canonical あたり SVG 1 個・id=`<instance>-svg` の要求）は、stepper 化された canonical では **各 `[data-step]` panel の部分木を「接尾辞付き id を持つ独立した component instance」として panel 単位に適用**するよう変更する（CLI・build 時経路の双方が同関数を呼ぶため、ここを変えないと正常な複数 panel が新規検査より先に失敗する）。manifest の `generated_landmark_ids` / `svg_root_ids` も panel 別契約とし、接尾辞付き id（例: `<instance>-svg--p2`）を panel ごとに列挙する。`check.sh` の呼び出し構成は不変。

### 検査 1: 情報完全性検査（visual-stage のみ）

「全主張が図に担われている」を、**主張 inventory（`assertions`・正本）との照合**として構造的に検証する。inventory は prose とは独立に IR 上へ明示宣言される（§1）ため、inventory と無関係な claim、図に担われない主張、主張に担われない図要素を検出できる。

- 全 canonical 節が `claim` と `assertions`（minItems 1）を持つこと（§3 の規則の checker 側担保）。
- `claim` のテキストがいずれかの assertion の `text` と一致すること。
- IR の `claim` テキストが描画 HTML の `.ve-claim` に**一致して出現**すること（IR→HTML の落失検出。build 時経路で expected から照合）。
- **主張→図 対応検査**: 全 assertion の `coverIds` が payload の semantic id に実在すること（各主張が少なくとも 1 つの図内要素に担われていること）。
- **カバー率検査**: payload の全 semantic id が、全 assertion の `coverIds` の union でカバーされること。未カバーの id は「図に情報要素があるのにいずれの主張にも担われていない」として error。
- sequence 付き図では、全 step の `targetIds` 和集合が payload の semantic id に**すべて実在**し、かつ step id が文書内で一意であること。
- narrative 節が §3 の上限（0〜2 節・各 200 字以内）を守ること。
- いずれも違反は fail-closed で build 失敗・診断は `diagnostics.py` 経由で bounded に出力。
- **v1 の限界（既知）**: inventory は IR 作者の自己宣言であるため、「主張を prose と図の両方から同時に落とす」欠落や、assertion の内容と参照先図要素の意味的対応の正しさ自体は構造検査では検出できない。v1 の情報完全性は構造カバー（coverIds 実在・union カバー・claim≡いずれかの assertion）を契約とし、意味照合・削除前の独立正本との照合は v2 課題とする。

### 検査 2: claim/narrative 語句重複検査（二重化検出）

- 各 canonical の**全 assertion の `text`（`claim` を含む inventory 全文）**を narrative markup のプレーンテキストと照合し、主張文の転記・列挙文の残存を検出する（claim 以外の assertion を narrative に残す逃げ道を塞ぐ）。判定アルゴリズムを固定する: 比較前に両テキストへ **HTML entity デコード → Unicode NFKC 正規化 → 空白・句読点・記号の除去**を施し、そのうえで **10 文字以上の共通部分文字列**を検出したら error。固有名詞・専門句の単発出現は正規化後 10 文字未満なら検出されない。10 文字以上の一致は主張の転記とみなし、許容例外リストは持たない（v1 は prose 原則削除のため narrative 側の書き換えで解消する。fail-closed を維持）。
- 完全一致の強制ではなく閾値ベースの **error**（v1 は prose 原則削除のため厳格に）。
- 日付・数値など図にも prose にも出てよい語句は、assertion の `text` 自体のみを照合対象にすることで誤検出を抑える（narrative 同士・closing との重複は対象外）。
- **位置付け**: 本検査は文字列レベルの補助線であり、言い換え（パラフレーズ）の完全検出は保証しない。二重化・情報欠落の主担保は検査 1 のカバー率検査と narrative 上限（§3）が担い、本検査はその補完として運用する。

### 検査 3: sequence 構造検査

schema/validation 層で既に弾くが、checker でも描画結果を再検証する。

- step 数 ≤8（panel 数 = steps+1 の一致）。
- mode×component 許可表（§2 の表）違反なし。
- `data-step` の連番・`data-total-steps` 一致。
- stepper 契約（`[data-stepper]` ラッパ・prev/next/all ボタン）の存在。`.stepper-status` は skeleton runtime が実行時に自動生成するため、生成 markup への含有・静的検査のいずれでも要求しない。
- panel 1 が強調 class（allowlist: `ve-seq-spot`・`ve-seq-dim`・`ve-takeaway-target`）を持たない完成図であること。
- 各 panel 内の DOM id が接尾辞規則 `--p<p>` に従うこと、および connector 等の内部参照が同一 panel 内の id のみを指すこと。
- 各 panel の DOM が §2 の正規化規則（`data-step`・id 接尾辞・強調状態 class・予告行を除外）適用後に同一であること（同一レイアウトの構造的証明）。

### 既存 doc 通過の保証

1. 新検査は profile ゲートで既存文書に不発。
2. CSS は新規 asset `visual-stage.css` への集約により既存 12 形式の CSS ファイル不変。
3. registry への変更は全 12 component への同一 asset（`visual-stage`・同一 digest）宣言追加と capability 追加のみで、既存 CSS ファイルとその digest・既存エントリの検証結果は不変。flatten の dedup キー変更も既存 doc では同一 asset id の複数 component 参照が発生しないため挙動不変（renderer が条件付きでのみ出力するため、既存 doc の生成物には注入されない）。
4. 既存テスト（`test_component_contract.py`・bad-* fixture 群・example-proposal 再ビルド比較）を `check.sh` で無修正通過させることを完了条件に含める。

---

## 5. 後方互換・検証計画・失敗時の扱い

### 後方互換（回帰保証）

完了条件は次の 3 点の同時成立とする。

1. **既存 doc の描画不変**: `examples/example-proposal.assembly.json` を再ビルドし、生成 HTML が現行 `example-proposal.html` と**バイト一致**すること（一致しなければ何かが侵襲している証拠として fail）。
2. **既存テスト無修正通過**: `scripts/tests/` 配下の全テストを **1 行も修正せず**全通過させる。テスト修正が必要になった時点で後方互換違反として設計を見直す。
3. **`check.sh` 無修正通過**: 四層の呼び出し構成・引数・終了コード契約を変えない。

### v1 検証計画（新規テスト）

- **IR fixture（正常系）**: visual-stage profile の assembly fixture を追加し、**許可表の全 mode×component 組合せを網羅**する: flow+path-spotlight（承認地図ステッパー）、flow+state-lens、matrix+state-lens、stairs+state-lens、waterfall+delta-accumulate、bars+delta-accumulate の 6 件。ビルド成功・stepper 構造・panel 1 完成図・claim 描画・panel id 接尾辞に加え、**各 mode の強調意味論**を検証する: 各 panel で `ve-seq-spot` を持つ要素の基底 id 集合が契約どおりであること（path-spotlight/state-lens は当 step の `targetIds`＋導出辺、delta-accumulate は steps 1..k の prefix union）、非対象要素が `ve-seq-dim` を持つこと、path-spotlight で強調辺が辺導出規則どおり生成されること。connector の再描画そのものは skeleton 既存ランタイムの責務とし、構造検査（stepper 契約・data 属性の存在）と 1212px 目視で担保する。
- **claim 共通層の parametrized test**: claim のみ・sequence なしの IR を **全 12 形式それぞれについて**生成し、共通ヘルパ経由で `<p class="ve-claim">` が section 先頭に 1 回だけ描画されることを形式ごとに検証する（特定形式の renderer がヘルパ適用を漏らしても検出できるようにする）。
- **bad fixture（異常系）**: 以下の各 1 件が**期待診断で build 失敗**することを検証。
  - step 9 件超過
  - 非許可 mode×component（例: bars+path-spotlight）
  - dangling targetId（payload に存在しない id）
  - `targetIds` が step id を参照（payload 外参照・名前空間分離違反）
  - step id 重複 / step id が pattern 違反
  - step への未知フィールド混入（`additionalProperties: false` の検証）
  - step の label が空文字列（minLength 1 の検証）
  - mode 別対象種別違反（例: state-lens の targetIds が source 注記 id を参照）
  - visual-stage で compatibility 節を使用
  - visual-stage で claim または assertions 欠落
  - assertion の coverId が payload に存在しない（主張→図 対応の dangling）
  - claim がいずれの assertion の text とも一致しない
  - payload semantic id のカバー率不足（主張 inventory に担われない id が残存）
  - delta-accumulate で先行 step と targetIds が重複
  - path-spotlight で step 間が辺接続していない / step 間で targetIds が重複
  - narrative 3 節 / 200 字超過
  - claim/narrative 語句重複
  - narrative に非 claim assertion の text を残存（inventory 全文照合の検証）
  - 非 visual-stage での claim/sequence 使用
- **checker unit test**: 情報完全性・重複・sequence 構造・強調 CSS のレイアウト不変（paint-only allowlist の静的スキャン）・幅定数（4W＋gap×3 ≤ C。C は skeleton トークン由来の利用可能内幅）の各検査に対し、検出系・非検出系（既存 profile では不発）の両方を用意。
- **確認手順**: `scripts/check.sh` を実行し、legacy・component 契約・検査群③・新規検査の全層が通ることを 1 コマンドで確認する（外部依存ゼロ・stdlib のみ）。
- **1212px 目視確認**: flow+path-spotlight fixture の生成 HTML を 1212px 幅のブラウザで人間が開き、(a) 各 panel で overflow が発生しないこと、(b) step 切替で強調経路を追えること、(c) 予告行と status が読めることを確認する（自動計測は外部依存ゼロの制約上 v1 では行わない）。

### 失敗時の扱い（fail-closed と安全装置）

- すべての新規制約違反は **build 失敗**（警告で通さない）。`build_explainer.py` 既存の atomic rename により、失敗時に部分 HTML が残らないことをそのまま利用する。
- 診断は `diagnostics.py` の bounded 出力に乗せ、違反種別・対象節 id・期待値/実測を 1 件ずつ明示する（traceback を出さない既存契約に従う）。
- **設計上の安全装置**:
  - (a) opt-in 強制（非 visual-stage での claim/sequence/assertions は validation error）により既存文書へ新規則が漏れない。
  - (b) mode×component 許可表を validation 定数に閉じ込め、対象外形式への sequence 適用を構造的に禁止。
  - (c) step 上限 8 を schema maxItems と checker の二重で強制。
  - (d) panel 1＝完成図の自動生成により、JS 無効・stepper 非動作時でも全情報が常に表示される（無操作の不変条件）。
  - (e) sequence は IR に what のみ持たせ、描画 how は renderer に閉じるため、LLM 出力の逸脱は schema 層で確実に弾かれる。

STATUS: done
