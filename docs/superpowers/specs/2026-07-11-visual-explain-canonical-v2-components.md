# visual-explain canonical v2 コンポーネント拡張 仕様

**ゴール:** 箇条書きで書かれがちな説明（並列の要点・分解・優先構造・手順・段階・増減・2時点変化・論拠）を、canonical IR から機械生成できる 8 コンポーネント（10 図形式）に拡張する。既存の安全アーキテクチャ（自己完結 HTML・固定領域・信頼レジストリ・fail-closed 診断・四層検査）と visual standard v1 の 3 層基準は一切弱めない。

**位置づけ:** ビジュアル基準 v1（2026-07-11 spec、PR #2 / `ee1a010` で実装済み）の次フェーズ。vault 筆頭方針「箇条書きの図解化」（`bullet-lists-should-become-diagrams`）に対応する。本改訂版は、現行実装（`skills/visual-explain/` の schema / registry / `ve_components/` / tests）との突合監査を反映した提案最終版である（監査結果は末尾「Spec Audit」）。

## 前提決定（ユーザーヒアリング 2026-07-11・承認済み）

| 論点 | 決定 | 帰結 |
|---|---|---|
| 骨格トークン | **不可侵**。コンサル調の配色・スタイル変更は不採用 | 新コンポーネントの CSS は既存トークンの参照のみ。トークンの追加・変更・上書きを提案しない。`skeleton.html` のトークン・固定領域・固定 JS はバイト不可侵 |
| 採用セット | G1/G2 列挙型・G3 ロジックツリー・G5 ピラミッド・F1/F2 チェブロン・F3 階段型・B1 waterfall・B3 slope・E1 evidence-map の 10 図形式（8 コンポーネント） | 下記の個別契約を実装する |
| 縦横の出し分け | 列挙型・チェブロン・waterfall は同一 IR から presentation/orientation 設定で切替 | 意味（relationship）と表現（設定）を分離する既存思想を踏襲 |
| ブロックの中身 | 番号だけでなく概念ラベルにも対応（`blockContent: "number" \| "label"`） | 列挙型・チェブロンの全バリアントに一貫適用 |
| 中央揃え | 列挙型（縦）とチェブロン（縦）は図全体を中央揃え | 幅は内容にフィット（`fit-content`）。図コンテナ内限定の例外として design-system.md の「中央寄せは使わない」に**限定的例外**を明記する（本文・見出しには適用しない） |
| ループ | チェブロン縦のみ `loop: true` で「最終段→先頭」の戻り 1 本を許可 | 任意の後方遷移は導入しない（state-machine はバックログのまま） |
| **renderer-svg** | **明示的な `slope@1` 許可リスト＋レンダラマニフェスト宣言＋checker 照合**。自由 SVG、および script / 外部参照 / `foreignObject` / インラインイベントの SVG 機能は**受理拒否** | 下記「renderer-svg ゲート」節。許可リストは checker が所有する閉集合 `RENDERER_SVG_ALLOWLIST = {"slope@1"}` |
| **waterfall の丸め** | **`displayPrecision` 必須**。数値 JSON 字句は **Decimal として解析**し、**絶対算術誤差 <= displayPrecision/2 のみ受理**。`valueText` は不透明な表示テキスト（値との照合はしない） | 下記「数値の取り扱い」節 |
| スライス進行 | **S3 は継続判断ゲートではない。S1〜S6 を通しで実施**し、S6 後に統合累積レビューを行う | 下記「実装スライス分割」節。旧 spec の「S3 出荷後に需要観測してから S4〜S6」は撤回 |
| 見送り | 包含型・Venn・収束型・フェーズゲート・state-machine・swimlane・schedule・criteria-board・decision-tree・compare 昇格・deviation/range/funnel・risk-map | バックログとして本 spec 末尾に記録 |

デザイン参照モック（ブレスト成果物・canonical 生成物ではない）: `.visual-explain/2026-07-11-grouping-flow-variants-mock.html`（採用 10 図の最終形）、`.visual-explain/2026-07-11-canonical-v2-candidates-mock.html`（全 16 図パレット）。

## 全体アーキテクチャ方針

### 変えないもの

- 意思決定列（関係宣言 → レジストリ発見 → 明示選択 → 一致理由記録 → ビルド＋四層検証）と fail-closed 原則。生成失敗は診断を返して報告し、互換マークアップへ暗黙に切り替えない。
- IR に HTML/CSS/JavaScript/DOM 操作/座標を書かない。数値・テキスト・宣言のみ。レイアウト計算（waterfall の累積オフセット、slope の座標、階段の高さ）は全てレンダラの責務。
- 共通 IR フィールド（`id` / `relationship` / `selection` / `caption` / `certainty` / `sources` / `accessibility` / takeaway 注釈 3 種）の形。
- コンポーネント資産の所有権: 骨格がトークン・固定領域・固定 JS を所有し、コンポーネントは `[data-ve-component="<id>"]` を根とする名前空間化した最小 CSS のみを所有。**本番レジストリのスクリプト資産は空**（static-first）。制御 content スロット内のインライン `style` 属性・`on*` 属性・外部参照の禁止（`_ContentSafetyParser`）もそのまま。
- 新コンポーネントの拡張ゲート 10 手順（design-system.md）を**コンポーネントごとに原子的に**満たす。部分的な本番エントリを残さない。
- 既存 matrix / flow の契約（IR shape・受理条件・レンダラ・checker 挙動）。ただし下記「flow edge.relation のスコープ固定」は、v2 の enum 拡張によって flow の実効的な厳しさが**緩む**ことを防ぐ保全措置であり、現在意味的に有効な入力の受理範囲は変えない。

### 変えるもの

- `component-vocabulary.json` に 8 コンポーネント（ID・contractVersion 1・relationshipKind・capabilities）を追加。`component-ir.schema.json` の `componentId` / `relationshipKind` / `capability` enum を語彙と一致させる（既存ドリフト検査 `test_component_contract.py` がそのまま検証する）。**`assembly.schema.json` は変更不要**（canonical 節は `component-ir.schema.json` への `$ref` 委譲であり、同ファイルが持つ enum は compatibility の provenance のみ）。
- IR スキーマの `oneOf`（payload 排他）を 2 → 10 分岐に拡張。payload キーはコンポーネント ID と同名（`enumeration` / `logic-tree` / `pyramid` / `chevron` / `stairs` / `waterfall` / `slope` / `evidence-map`）。
- レジストリ（`assets/components/registry.json`）に 8 エントリ、`TRUSTED_RENDERERS` に 8 つの `<id>@1`、component CSS 8 ファイル（SHA-256 厳密ダイジェスト）。スクリプト資産は追加しない。
- checker: 新 checkerRules と bad フィクスチャ（下記「四層検査への追加」）。
- patterns.md（語彙・組み立て例・選択ガイド）、design-system.md（密度上限・中央揃え例外・ゲート第 3 手順の文言一般化）、SKILL.md（canonical 節のコンポーネント列挙と選択ガイド）、fixtures.md を各スライスで同期更新。

### 横断基盤の一般化（S1 で実施・全スライスの前提）

現行実装は matrix/flow の 2 枚に**ハードコード**されている箇所が多く、以下の一般化を S1（enumeration）に含める。S1 は「最初のコンポーネント追加」と「n 枚対応への基盤リファクタ」を兼ねる。

1. **payload ディスパッチ:** `validation._validate_canonical_ir` の `has_matrix`/`has_flow` 二値分岐を、「語彙に登録された payload キー集合のうち**ちょうど 1 つ**が存在し、そのキーが `selection.component` と一致する」ディスパッチ表（component ID → payload バリデータ関数の閉じた dict）に置き換える。0 個・2 個以上・selection 不一致は従来どおり `invalid_component_payload`。
2. **`CanonicalIR.semantic_ids()`:** 各 payload の意味 ID（下記の各コンポーネント契約で列挙）を返すよう拡張する。`render_canonical` の「manifest.consumed_semantic_ids == IR の全意味 ID」完全性検査はこの拡張に自動的に乗る。
3. **注釈対象集合:** `_validate_annotations` の許容対象 ID 集合（現行: matrix=cell、flow=node∪edge）を payload ごとに定義する（各コンポーネント契約の「注釈対象」）。
4. **manifest 交差検査:** `assembly.render_canonical` の `generated_relationship_ids` 検査（現行: flow の辺 ID 集合、それ以外は空集合）を維持する。**新 8 コンポーネントは IR に辺を持たないため `generated_relationship_ids = ()` を宣言する**。flow DOM 同値検査（node/edge 三つ組の一致）は従来どおり flow 限定。新コンポーネントのレンダラ出力は **`data-ve-from` / `data-ve-to` / `data-ve-relation` / `data-ve-row-id` / `data-ve-column-id` を一切出さない**（これらを出すと `validate_artifact_semantics` が flow/matrix の形状規則で誤検査するため、禁止を新レンダラの契約とし、artifact 検査でも「flow/matrix 以外のセクションにこれらの属性があれば違反」として固定する）。
5. **注記リスト検査の一般化:** `validate_artifact_semantics` の「`ve-matrix-notes` か `ve-flow-notes` が必要」を、「そのセクションの `data-ve-component` が `<id>` のとき `ve-<id>-notes` が必要」に一般化する（許容クラス名は語彙由来の閉集合。ワイルドカード `ve-*-notes` は使わない）。
6. **診断コードの閉集合:** 新コードを `diagnostics.py` の定数＋`ALL_CODES` に追加する（下記「診断コード」）。`ALL_CODES` 外のコードは `Diagnostic.__post_init__` が拒否するため、追加漏れは即座にテストで露見する。
7. **checkerRules の閉集合:** 新規則名を `registry.KNOWN_CHECKER_RULES` に追加する。追加しない限りレジストリエントリがロード時に `unknown_checker_rule` で fail-closed する。
8. **flow edge.relation のスコープ固定:** `_validate_flow` の `rel not in _ALL_CAPABILITIES` 検査を「rel が flow 自身の語彙 capabilities（`ordered-transition` / `directed-transition` / `branching`）に含まれること」に固定する。schema 側も `flowEdge.relation` を flow capabilities のみの `$defs/flowRelation` に差し替える。v2 で capability enum が 5 → 14（既存 5＋新規 9: `parallel-itemization`・`mece-decomposition`・`priority-layering`・`linear-sequence`・`closed-loop`・`maturity-staging`・`additive-bridging`・`two-point-comparison`・`claim-support-mapping`）に増えても、flow 辺が `maturity-staging` 等を名乗れる抜け穴を作らない。
9. **共通レンダラ DOM 契約:** 新 8 レンダラは matrix/flow と同じ外形を守る — `figure[data-ve-component="<id>"][role="group"][aria-label][aria-describedby]` を根に、`figcaption.ve-<id>-caption`（id=`<instance>-caption`）、`p.ve-<id>-summary`（id=`<instance>-summary`）、`ul.ve-<id>-notes`（certainty/sources を `data-ve-semantic-id` 付き `li` で全件）、payload の全項目に `data-ve-semantic-id`。manifest の `generated_landmark_ids` は `(<instance>-caption, <instance>-summary)`＋（slope のみ）SVG ルート id。全テキストは `html.escape`。script 資産は出さない。

## チェブロンの位置づけ（設計判断）

ユーザー向け説明では「flow の presentation」と表現したが、実装は**独立コンポーネント `chevron`**（relationshipKind: `ordered-sequence`）とする。理由: (1) payload が線形の steps 配列であり、flow の nodes+edges+レール割当・行予算とは受理条件がまったく異なる。(2) flow renderer に presentation 分岐を足すと両方の fail-closed 契約が濁る。(3) レジストリ発見は `relationship.kind` の一致で先に絞られ（kind ⇄ コンポーネントは 1:1）、`ordered-sequence` を宣言すれば候補は chevron のみ、`directed-graph` なら flow のみになる。**送り分けの実体は kind 宣言**であり、「分岐・合流が出たら `directed-graph`（flow）、線形なら `ordered-sequence`（chevron）」を patterns.md の選択ガイドに明文化する（capability `branching` の有無は説明上の目印であって発見機構ではない）。flow 側の契約は一切変更しない。

## 数値の取り扱い（waterfall / slope 共通・承認済み決定）

- **解析:** `build_explainer.py` の `json.loads` を `parse_float=decimal.Decimal` で行う。整数字句は従来どおり `int`（`parse_int` は変更しない — `selection.version` 等の `_is_int` 検査を壊さないため）。
- **受理型:** 数値フィールド（`value` / `delta` / `fromValue` / `toValue` / `displayPrecision`）は **`int` または `Decimal` のみ受理**。`bool` は従来どおり拒否し、**binary `float` インスタンスも拒否**する（CLI 経路では発生しない。Python API/テストから float を渡した場合、半単位比較が二進誤差で不定になるため fail-closed）。違反は当該コンポーネントの structure violation 診断。
- **waterfall 整合検証:** `abs(start.value + Σ steps[].delta − end.value) <= displayPrecision / 2` を **Decimal の正確な算術**で判定する（`<=` は含む）。`displayPrecision` は waterfall payload 直下の**必須**フィールドで、正の `int | Decimal`（例: `1`、`0.1`）。不一致は `waterfall_arithmetic_mismatch` で受理拒否 — 数の合わない橋を描かない。
- **`valueText` は不透明:** 単位・桁区切り込みの表示テキスト（必須・非空）。`value`/`delta` との数値照合・再フォーマットは**しない**。棒・線だけで値を伝えず、`valueText` を必ず可視表示する。
- **レイアウトの量子化:** レンダラは Decimal でスケール計算した後、幾何を**整数百分率に量子化**して出力する（丸めは `Decimal.quantize(Decimal("1"), rounding=ROUND_HALF_UP)` で固定）。表示値は常に `valueText` 由来なので、幾何の 1% 量子化は情報を失わない。
- **正規化ドメイン（waterfall）:** スケール対象集合は累積値列 `c_0 = start.value`・`c_i = c_{i-1} + delta_i`（i=1..n）・`end.value` に**基線 0 を常に加えた**全体。負の累積値・0 交差を許す。`range = max − min`、各値の百分率 = `(v − min) / range × 100` の量子化。`delta` が 0 の step は許可する（増減なしは `valueText` で明示）。`range == 0`（全対象値が 0）は描く情報がないため `waterfall_structure_violation` で受理拒否。
- **正規化ドメイン（slope）:** スケール対象集合は全 item の `fromValue`・`toValue` のみ。基線 0 は**含めない**（2 時点比較で 0 起点は意味を持たない。0 は値域に入る場合のみ自然に現れる）。負値を許す。`range == 0`（全値同一）は受理し、全点を値域バンドの垂直中央へ写像する決定的規則とする（フラットな線＋`valueText` が「変化なし」を表現する）。
- **クランプ禁止:** min → 0%・max → 100% に正確に写像されるため、量子化後の百分率・SVG 座標は構成上必ず域内（[0,100]・viewBox 内）に収まる。域外の値が算出された場合は黙ってクランプせず `renderer_failure` とする（レンダラ欠陥の fail-closed 検出）。
- **境界テスト（必須ケース）:** min/max 端点の 0%/100% 写像・負の累積値・0 交差・`delta` 0・waterfall `range == 0` の拒否・slope `range == 0` の中央写像（Y=110）・slope の端点/方向写像（min → Y=200・max → Y=20、増加は `y2 < y1`・減少は `y2 > y1`。slope 契約節の必須テスト）・ROUND_HALF_UP の .5 境界・整合誤差がちょうど `displayPrecision/2` の受理とその直上の拒否。

## レイアウト出力の制約（inline style 禁止との整合）

制御 content スロットでは checker がインライン `style` 属性を禁止している（`_ContentSafetyParser`・変更しない）。したがって旧 spec の「カスタムプロパティ（`--start`/`--len`）として出力」は**採用できない**。代わりに flow のレール（`ve-rail-{s}-{e}` 事前生成クラス）と同じ**クラス駆動**方式を全コンポーネントに適用する:

- **waterfall:** `waterfall.css` に `ve-wf-start-0` … `ve-wf-start-100`、`ve-wf-len-0` … `ve-wf-len-100` の事前生成クラス（計 202 規則）を持ち、レンダラは量子化した百分率をクラス名で割り当てる。bars（行型）は横方向、columns（縦棒型）は縦方向に同じクラスを軸を変えて解釈する（orientation コンテナクラスで切替）。破線コネクタも同クラス系（前バーの端 → 次バー）で描く。
- **stairs / pyramid:** 段数が 3〜5 / 3〜4 の閉じた範囲なので、コンテナの `ve-stairs-count-{3..5}` / `ve-pyramid-count-{3,4}` と項目の index クラスの組合せで高さ・幅を全列挙する。
- **enumeration / chevron / logic-tree:** flex/grid ＋ clip-path（コンポーネント CSS 所有）のみで、per-item の計算値を持たない。
- **slope:** SVG の幾何**属性**（`x1` / `y1` / `cx` / `viewBox` 等）はインライン style ではないため checker 契約と両立する。座標はレンダラが固定 viewBox（`0 0 600 220`）内へ線形正規化し整数に量子化する。

いずれも「レイアウト計算はレンダラの責務・IR に座標を書かない」を満たしつつ、出力は静的クラス／SVG 属性のみで、既存の安全規則を 1 つも緩めない。

## renderer-svg ゲート（承認済み決定の具体設計)

canonical レンダラが SVG を出力する初のケース（slope）を、**二重ゲート＋機能拒否**で閉じる。なお現行実装では、legacy の「自由 SVG には理由コメント必須」規則は `check.sh` の型付き legacy 文書検査（`pattern_checks`）にのみ存在し、**コンポーネント文書では実行されない**。よって renderer-svg は legacy 規則からの「切り分け」ではなく、コンポーネント checker に新設する規則である（legacy 単体文書の理由コメント規則は従来どおり存置）。

1. **許可リスト（checker 所有）:** `checker.py` に `RENDERER_SVG_ALLOWLIST = frozenset({"slope@1"})` を定数として持つ。content スロット内の `<svg>` は、「`data-ve-component`@`data-ve-contract-version` が許可リストに含まれる canonical セクションの内側」でのみ受理する。それ以外の場所（許可外 canonical セクション・compatibility セクション・セクション外）にある `<svg>` は `renderer_svg_violation` で拒否する（**自由 SVG の受理拒否**。コンポーネント文書内での SVG 持込経路を互換節経由も含めて全て閉じる）。
2. **マニフェスト宣言:** `RenderManifest` に `svg_root_ids: tuple[str, ...] = ()` を追加する（既定空タプルなので既存レンダラは無変更）。slope レンダラは SVG ルートに `id="<instance>-svg"` を付与し、`svg_root_ids` と `generated_landmark_ids` の両方で宣言する。
3. **組み立て時交差検査（`render_canonical`）:** レンダラ markup 中の `<svg>` ルート数・id 集合が `manifest.svg_root_ids` と一致しない、または `svg_root_ids` が非空なのに `component.key` が許可リスト外 — いずれも `renderer_failure` で拒否する。宣言なしの SVG 出力も同様。
4. **artifact 単独検査（manifest なしの `check_component_html.py` 経路）:** 許可セクション内でも `<svg>` はセクションあたり 1 個・`id="<instance>-svg"` 必須・`<svg>` の入れ子禁止とし、SVG サブツリーに**要素許可リスト** `{svg, g, line, circle, text, title, desc}` を適用する。属性は**要素ごとの閉じた完全一致許可リスト**で検査し、リスト外の属性は名前を問わず `renderer_svg_violation` で拒否する（「その他の幾何属性」のような暗黙カテゴリを設けない）:
   - `svg`: `id`・`class`・`viewBox`・`preserveAspectRatio`・`role`・`aria-label`・`aria-describedby`
   - `g`: `class`・`data-ve-semantic-id`・`data-ve-takeaway`
   - `line`: `class`・`x1`・`y1`・`x2`・`y2`
   - `circle`: `class`・`cx`・`cy`・`r`・`data-ve-semantic-id`・`data-ve-takeaway`
   - `text`: `class`・`x`・`y`・`text-anchor`
   - `title` / `desc`: 属性なし

   **名前空間の扱い:** 名前空間宣言（`xmlns`・`xmlns:*`）およびコロンを含む属性名（`xlink:href` 等）は一括拒否する（インライン SVG に xmlns は不要であり、参照系属性の別名経路をカテゴリごと閉じる）。

   **属性値の文法（閉じた完全検査）:** スカラー座標属性（`x`・`y`・`x1`・`y1`・`x2`・`y2`・`cx`・`cy`）は量子化済み整数 `^-?[0-9]+$`、半径 `r` は非負整数 `^[0-9]+$` のみ。`viewBox` はスカラー整数文法では**なく**、slope が要求する固定 4 整数形との**完全一致** `0 0 600 220` として別個に検査する。`preserveAspectRatio` は列挙値 `xMidYMid meet` のみ、`text-anchor` は列挙値 `start` / `middle` / `end` のみ許可する。これら以外の値はすべて `renderer_svg_violation`（値文法にも暗黙カテゴリを設けない）。これにより `script` / `foreignObject` / `use` / `image` / `animate` / `animateTransform` / `animateMotion` / `set` の各要素、`on*` / `style` / `href` / `xlink:href` の各属性は定義上すべて拒否される（許可リスト外）。
5. **フィクスチャ要件:** 上記は bad フィクスチャで各カテゴリ最低 1 件ずつ失敗を固定する — 許可外要素（`rect` 等）・許可外属性（`transform` 等）・名前空間属性（`xlink:href`）・`xmlns` 宣言・非整数座標値・`<svg>` の入れ子・許可外セクション（compatibility 含む）の `<svg>`・`foreignObject`。加えて**境界の valid フィクスチャ**（viewBox 端 `0` / `600` / `220` ちょうどの座標、負座標なしの最小構成）で受理側の境界を固定する。
6. **表現規則:** SVG 内テキストは component CSS のクラス経由で `--fs-figure` 相当を維持し、各 item の両端に値（`fromValueText` / `toValueText`）を必ず併記する。色は tone → 既存トークンの写像のみ。

この設計により「マニフェスト宣言＋許可リストの二重ゲート」が組み立て経路と artifact 単独経路の両方で成立し、「なんでも SVG」への抜け穴を閉じる。

## コンポーネント別契約

全コンポーネント共通: contractVersion 1。文字数上限は **Unicode コードポイント数（Python `len()`）**で数え、超過は受理拒否（fail-closed）。判断色（accent/positive/warning）は下記で明示した箇所以外に使わず、ブロックの地はモノクロ階調のみ（tone `neutral` は専用トークンではなくモノクロ階調への写像）。図がコンテンツ幅を超える場合は各自の横スクロールコンテナ内で溢れさせる。payload のフィールド名はすべて `validation.FORBIDDEN_AUTHORING_KEYS`（`x`/`y`/`width`/`svg`/`style` 等）と衝突しないことを確認済み。各 payload の「意味 ID」に挙げた ID は `semantic_ids()` に載り、DOM で `data-ve-semantic-id` として消費され、文書内で一意でなければならない（既存の重複検査に乗る）。

### 1. enumeration（列挙型）— G1/G2

- **relationshipKind:** `parallel-enumeration` ／ **capabilities:** `parallel-itemization`
- **payload:** `items[]`（2〜6 件）。item = `{id, label?, title?, description?}`。`description` は文字列配列（箇条書き行）。
- **設定:** `presentation: "list"（縦・既定）| "columns"（横）`、`blockContent: "number"（既定）| "label"`
- **受理条件:**
  - `blockContent: "label"` → 全 item に `label`（16 字以内）必須、`title` 禁止（ラベルが見出しを兼ねる）。
  - `blockContent: "number"` → 番号はレンダラが 1..n を採番（IR に番号を書かない）。`title`（30 字以内）任意。ただし**最小可視内容契約**: number モードの各 item は `title` か `description` の少なくとも一方を持つ（番号だけの空ブロックを受理しない）。`description` の全有/全無規則により、description を全無にする場合は全 item に `title` が必須になる。違反は `enumeration_structure_violation`。
  - `presentation: "columns"` → items 2〜4 件。`description` は 1〜4 行（各 40 字以内）。`presentation: "list"` の `description` は 1〜3 行（各 60 字以内）。
  - `description` は全 item で省略可（コンセプトのみ表示）。一部 item だけの省略は不可（全有か全無。歯抜けは `enumeration_structure_violation`）。
- **意味 ID / 注釈対象:** items の `id`。
- **意味制約:** 順序を持たない並列関係の宣言（番号は識別子であって順序ではない）。順序があるなら chevron。
- **表現:** 縦は図全体を中央揃え（`width: fit-content; margin-inline: auto` — 図コンテナ内限定例外）。ブロック地は `--text-dim`、文字は `--bg`。横は狭い画面で縦積みに折り返す（意味順維持）。
- **縮退先:** 通常の箇条書き。

### 2. logic-tree（ロジックツリー）— G3

- **relationshipKind:** `hierarchical-decomposition` ／ **capabilities:** `mece-decomposition`
- **payload:** `root{id, label}`＋`branches[]`（2〜4 件）。branch = `{id, label, leaves?[]}`。leaf = `{id, text}`（各 branch 0〜2 件・text 40 字以内）。
- **受理条件:** 深さは root → branch → leaf の 2 段固定。ラベルは root 20 字・branch 16 字以内。
- **意味 ID:** root・branches・leaves の `id` ／ **注釈対象:** 同左。
- **意味制約:** 「構成の分解」専用。読者がたどる判断の分岐（decision-tree、バックログ）とは区別し、誤用は checker ではなく patterns.md の選択ガイドで防ぐ。MECE 性は機械検証できないため caption / evidence 側で主張し、必要なら確度バッジを付ける。
- **表現:** 左に root、右に branch 列。接続線はレンダラ所有（grid＋境界線ベース。手書き・`data-ve-from/to` 禁止）。狭い画面では縦積み（root 上・branch 下）。
- **縮退先:** `terms` または入れ子箇条書き。

### 3. pyramid（ピラミッド型）— G5

- **relationshipKind:** `layered-priority` ／ **capabilities:** `priority-layering`
- **payload:** `tiers[]`（3〜4 件、**上から下の順**）。tier = `{id, label, sub?}`（label 12 字・sub 30 字以内）
- **受理条件:** 先頭 tier ＝頂点＝最優先。幅はレンダラが段階計算（IR に幅を書かない。実装は count×index の事前生成クラス）。
- **意味 ID / 注釈対象:** tiers の `id`。
- **意味制約:** 「上に行くほど少なく・重要」という優先構造があるときだけ使う。単なる並列 3 項目は enumeration の仕事（patterns.md の選択ガイドに明記）。
- **表現:** 頂点 tier のみ `--border-strong` 地で強調（構造の合図であり判断色ではない）。他 tier は `--text-dim` 地。
- **縮退先:** enumeration（縦）。

### 4. chevron（チェブロン型）— F1/F2

- **relationshipKind:** `ordered-sequence` ／ **capabilities:** `linear-sequence`, `closed-loop`
- **payload:** `steps[]`（2〜6 件、宣言順＝実行順）。step = `{id, label?, title?, description?}`
- **設定:** `orientation: "vertical"（既定）| "horizontal"`、`blockContent: "number" | "label"`（規則は enumeration と同一）、`loop: false（既定）| true`
- **受理条件:**
  - `loop: true` は `orientation: "vertical"` のみ。戻り辺は「最終 step → 先頭 step」の 1 本だけをレンダラが描く（IR に辺を書かない）。それ以外の後方遷移が必要な説明は受理せず、flow か文章へ送る診断を返す。
  - **capability 整合:** `loop: true` ⇔ relationship.capabilities に `closed-loop` を含む（片方だけは `chevron_structure_violation`）。`linear-sequence` は常に必須。
  - `orientation: "vertical"` → `description` は 1〜3 行（各 40 字以内）。
  - `orientation: "horizontal"` → steps 3〜6 件、`title` 禁止、`description` は 1〜2 行（各 30 字以内）。
  - **最小可視内容契約**（enumeration と同一）: `blockContent: "number"` の各 step は `title` か `description` の少なくとも一方を持つ。`orientation: "horizontal"` は `title` 禁止のため、**number モードの横チェブロンでは `description` が全 step で必須**になる（全有/全無規則と併せて一意に定まる）。違反は `chevron_structure_violation`。
  - `description` の全有/全無規則は enumeration と同一。
- **意味 ID / 注釈対象:** steps の `id`。
- **意味制約:** 分岐・合流のない線形順序専用。分岐が要るなら relationship.kind を `directed-graph` にして flow（前掲「チェブロンの位置づけ」）。
- **表現:** 縦は下向きチェブロン（clip-path はコンポーネント CSS 所有）で図全体を中央揃え。ループは左レール＋下向き矢頭で、レールはレンダラ所有・`data-ve-from/to` なし。`loop: true` のとき、visually-hidden の文（「最終段〈label〉から先頭段〈label〉へ戻る」相当）を flow の辺文と同様に出力し、線だけに意味を持たせない。横は左に切り欠きのある矢羽で、狭い画面では縦積みへ折り返す（横形式はループなしなので折返しで意味は壊れない）。
- **縮退先:** インライン `flow`（`<ol class="flow">`）または番号付き箇条書き。

### 5. stairs（階段型）— F3

- **relationshipKind:** `staged-maturity` ／ **capabilities:** `maturity-staging`
- **payload:** `stages[]`（3〜5 件、低い段から高い段の順）。stage = `{id, label, note?, current?}`（label 14 字・note 20 字以内）
- **受理条件:** `current: true` は最大 1 件。`current: true` の stage には `note`（現在地のテキスト表記）必須 — なければ `stairs_structure_violation`。踏み面の高さはレンダラが等差で計算（count×index クラス）。
- **意味 ID / 注釈対象:** stages の `id`。
- **意味制約:** 各段が「到達したら留まる状態」（成熟度・移行フェーズ）のときに使う。流れる工程は chevron。
- **表現:** `current` 段の踏み面のみ `--accent`（現在地強調はトークン契約上の正当用途）。色だけに意味を持たせない（note 必須が対）。最終段の強調はしない（v1 モックの「最終段=強」は誤解を招くため不採用）。
- **縮退先:** `timeline` または enumeration。

### 6. waterfall（ウォーターフォール）— B1

- **relationshipKind:** `additive-bridge` ／ **capabilities:** `additive-bridging`
- **payload:** `displayPrecision`（必須・正数）＋`start{id, label, value, valueText}`＋`steps[]`＋`end{id, label, value, valueText}`。step = `{id, label, delta, valueText, tone}`
  - `value` / `delta` は数値（`int | Decimal`。スケール計算用）、`valueText` は表示テキスト（単位込み・必須・非空・16 字以内。不透明 — 値との照合はしない）。
  - `tone: "positive" | "warning" | "neutral"` を**ステップごとに宣言必須**。増減の符号と良し悪しを分離する（増加が常に悪ではない）。start/end はモノクロ固定。
- **設定:** `orientation: "bars"（行型・既定）| "columns"（横並び型・縦棒ブリッジ）`
- **受理条件:**
  - **整合検証:** `abs(start.value + Σ delta − end.value) <= displayPrecision / 2`（Decimal 算術・前掲「数値の取り扱い」）。不一致は `waterfall_arithmetic_mismatch`。
  - `orientation: "bars"` → steps 1〜4 件（全 3〜6 行）。`orientation: "columns"` → steps 1〜7 件（全 3〜9 列）。ラベルは 12 字以内（columns では 2 行折返しまで）。
- **意味 ID / 注釈対象:** start・steps・end の `id`。
- **表現:** 累積オフセット・浮動バー位置・破線コネクタは全てレンダラが計算し、**事前生成の整数百分率クラス**（前掲「レイアウト出力の制約」）として出力する。columns は狭い画面で bars へ**レンダラが縮退しない**（静的 HTML のため）— 横スクロールコンテナで溢れさせ、生成時の選択ガイドで bars を推奨する。
- **縮退先:** `bars`（既存互換）または matrix。

### 7. slope（スロープ）— B3

- **relationshipKind:** `two-point-change` ／ **capabilities:** `two-point-comparison`
- **payload:** `axes{fromLabel, toLabel}`（各 8 字以内）＋`unit`（**必須**・非空・8 字以内）＋`items[]`（1〜5 件）。item = `{id, label, fromValue, toValue, fromValueText, toValueText, tone}`（label 12 字・valueText 各 12 字以内・非空）
  - `tone: "positive" | "warning" | "neutral"` 宣言必須（改善/悪化/不変の判断はデータからの自動判定にしない）。
- **受理条件:** 2 時点のみ（3 点以上は timeline/文章へ）。「同一単位」は payload レベルの単一必須フィールド `unit` の**構造で機械的に保証**する — 全 item が 1 つの `unit` を共有する形しか表現できないため、単位混在は IR 上で構成不能。`unit` は表示用の宣言であり `valueText` との照合は**しない**（valueText は不透明のまま）。レンダラは `unit` を summary または `ve-slope-notes` に可視表示する。per-item unit（異単位混在・per-item 正規化）はバックログ。数値は `int | Decimal`（前掲「数値の取り扱い」）。
- **意味 ID / 注釈対象:** items の `id`（axes はラベルのみで ID を持たない）。
- **表現（決定的ジオメトリ）:** レンダラは固定 viewBox `0 0 600 220` の SVG を決定的に生成する（renderer-svg ゲート前掲・要素/属性許可リスト内）。ジオメトリは次で確定する:
  - **X 座標:** from 列は **X=120**、to 列は **X=480** に固定（左右マージンはラベル・valueText 用）。
  - **値バンド:** 上端 **Y=20**・下端 **Y=200**（高さ 180）。
  - **Y 写像（反転）:** `y(v) = 200 − round((v − min) / range × 180)`。round は Decimal `quantize(Decimal("1"), ROUND_HALF_UP)`。これにより **max が視覚的に上（Y=20）・min が下（Y=200)** に写像される。
  - **range 0:** 全点を **Y=110**（バンド垂直中央）へ写像する（「数値の取り扱い」の決定的規則）。
  テキストは SVG 内でも `--fs-figure` 相当を維持し、値は両端に必ず併記。
- **必須テスト:** 端点写像（min → Y=200・max → Y=20）、増加 item（`toValue > fromValue`）は `y2 < y1`・減少 item は `y2 > y1` になる方向性、`range == 0` → 全点 Y=110、X=120/480 の固定を単体テストで固定する。
- **縮退先:** matrix（before/after の 2 列表）。

### 8. evidence-map（論拠地図）— E1

- **relationshipKind:** `claim-support` ／ **capabilities:** `claim-support-mapping`
- **payload:** `conclusion{id, label}`（30 字以内）＋`evidence[]`（2〜4 件）。evidence = `{id, label, certaintyRef, sourceRef?}`（label 40 字以内）
  - `certaintyRef` は**必須**で、共通フィールド `certainty[]` 内の assertion `id` を参照する。`sourceRef` は任意で `sources[]` の `id` を参照する。未解決参照は `evidence_map_structure_violation` で受理拒否（既存 matrix の `certaintyRef` は未解決でも黙って非表示になる先例だが、evidence-map は線種の意味が参照解決に依存するため厳格化する。matrix 側は変更しない）。
- **受理条件:** 結論 1 件・階層 1 段のみ（根拠の根拠は描かない。必要なら図を分割）。
- **意味 ID / 注釈対象:** conclusion・evidence の `id`。
- **表現:** 支持リンクの線種は参照先の確度から導出する（confirmed=実線・inferred=破線・unverified=点線。v1 の確度線種契約をリンクに適用）。リンクは CSS 境界線で描き `data-ve-from/to` を持たない。evidence カードは `data-ve-certainty-ref`（＋任意 `data-ve-source-ref`）属性を持ち、checker が DOM 上で解決可能性を照合する。線種だけに意味を持たせず、各 evidence カード内に既存のモノクロ確度バッジを必ず表示する。結論カードは `--border-strong` の枠で強調。
- **縮退先:** 文章＋確度バッジ（既存記法）。

## 四層検査への追加

- **IR/選択層（`validation.py`）:** 8 payload のバリデータ関数（件数・長さ・全有全無・current 最大 1・loop⇔closed-loop・certaintyRef/sourceRef 解決・waterfall 整合・数値型）。診断コードは下記の閉集合に追加する。
- **コンポーネント/マニフェスト層（`assembly.render_canonical`）:** 全意味 ID 消費・landmark・asset digest の既存検査に自動的に乗る（`semantic_ids()` 拡張前提）。新コンポーネントは `generated_relationship_ids = ()`・`script_asset_ids = ()`。slope のみ `svg_root_ids` を宣言し、SVG 交差検査を受ける。
- **最終文書層（`checker.py`）:** `validate_artifact_semantics` に per-component の閉じたディスパッチ表（component ID → DOM 構造検査関数）を追加し、各コンポーネントの構造不変条件を DOM 単独で再検査する — 項目数の範囲、`ve-<id>-notes` の存在（一般化済み検査）、`valueText` の可視出力、stairs `current` の note、evidence の `data-ve-certainty-ref` 解決、renderer-svg 許可リスト＋SVG 機能拒否、flow/matrix 以外での `data-ve-from/to/relation`・`data-ve-row-id/column-id` の禁止。
- **checkerRules（registry エントリ表記＋`KNOWN_CHECKER_RULES` 追加）:** 共通規則（`static-content` / `semantic-ids` / `escaping` / `no-external-reference` / `responsive-order`）＋固有規則 `enumeration-structure` / `logic-tree-structure` / `pyramid-structure` / `chevron-structure` / `stairs-structure` / `waterfall-consistency` / `slope-structure`＋`renderer-svg` / `evidence-map-references`。**各固有規則に最低 1 つの bad フィクスチャ**で失敗を固定する（renderer-svg は「renderer-svg ゲート」節のフィクスチャ要件 — 許可外要素/属性・名前空間・非整数座標・入れ子・許可外セクション等の各カテゴリ＋境界 valid — に従う）。
- **診断コード（`diagnostics.ALL_CODES` へ追加する閉集合）:** `enumeration_structure_violation`・`logic_tree_structure_violation`・`pyramid_structure_violation`・`chevron_structure_violation`・`stairs_structure_violation`・`waterfall_structure_violation`・`waterfall_arithmetic_mismatch`・`slope_structure_violation`・`evidence_map_structure_violation`・`renderer_svg_violation`。
- **密度上限（design-system.md 追記）:** enumeration 6 項目（columns 4）・logic-tree 枝 4（leaf 各 2）・pyramid 4 層・chevron 6 段・stairs 5 段・waterfall 行型 6 行/横並び 9 列・slope 5 項目・evidence-map 根拠 4 件。超過は分割か縮退。
- **check.sh の埋め込み legacy 検査**（禁止タグ・`animate` 系・イベント属性・URL スキーム・ネスト整合）はコンポーネント文書にも従来どおり適用される。新レンダラ出力はこれも通過しなければならない（追加作業ではなく既存ゲートの明示）。

## ドキュメント同期（各スライスの原子的更新対象）

- **patterns.md:** 「箇条書き種別 → 図」選択ガイド（logic-tree の分解 vs decision の区別、enumeration vs chevron の順序判定、pyramid の誤用禁止、waterfall bars/columns の推奨、chevron/flow の kind 送り分け）＋当該コンポーネントの canonical IR JSON 組み立て例。
- **design-system.md:** 密度上限、図コンテナ内中央揃えの限定的例外、renderer-svg ゲートの要旨。拡張ゲート第 3 手順の文言を「既存コンポーネントが使わない**共通** IR フィールドを追加しない（payload 固有フィールドはコンポーネント拡張レビューの対象）」に一般化する（本 spec がその拡張レビューにあたる）。
- **SKILL.md:** 「カノニカルな matrix / flow コンポーネント」節をコンポーネント一般の節に改め、追加済みコンポーネントと選択ガイドへの参照を列挙する。
- **fixtures.md:** 追加フィクスチャの目録と意図。

## 実装スライス分割

各スライスは拡張ゲート 10 手順を**原子的に**満たし、`check.sh --selftest`・当該 bad/valid フィクスチャ・**全 pytest** が緑の状態で完結する（1 スライス＝1 TDD 裏付きドラフト PR。人間ゲートなしの push/PR 作成/merge はしない）。**S3 は継続判断ゲートではない。S1〜S6 を通しで実施する（承認済み決定）。**

| スライス | 内容 | 根拠 |
|---|---|---|
| S1 | **横断基盤の一般化**（payload ディスパッチ・semantic_ids・注釈対象・notes 検査一般化・manifest 検査整理・ALL_CODES/KNOWN_CHECKER_RULES・flow edge.relation スコープ固定）＋ **enumeration**（list/columns・blockContent・中央揃え） | 最低難度のコンポーネントで「n 枚対応の基盤」と追加の型（語彙→スキーマ→バリデータ→レンダラ→CSS→レジストリ→checker→フィクスチャ→docs）を確立する |
| S2 | **chevron**（vertical/horizontal・blockContent・loop・loop⇔closed-loop 整合） | S1 のブロック部品思想を順序系に展開。loop レールが唯一の新規レイアウト要素 |
| S3 | **pyramid ＋ stairs** | いずれも低難度の静的形状（count×index クラス）。S1/S2 で確立した型の量産検証 |
| S4 | **logic-tree** | 接続線をレンダラ所有で描く最初のケース（flow のコネクタ資産とは独立） |
| S5 | **waterfall**（bars/columns・displayPrecision・Decimal 整合検証・百分率クラス量子化） | 数値スケール計算と受理時整合検証という新しい検証カテゴリ。`build_explainer.py` の `parse_float=Decimal` 化を含む |
| S6 | **slope ＋ evidence-map** | レンダラ生成 SVG（renderer-svg ゲート一式・`RenderManifest.svg_root_ids`）と確度参照の結合。最も検査変更が大きいため最後 |

各スライスで patterns.md / design-system.md / SKILL.md / fixtures.md の該当節を同時更新し、canonical 例（IR JSON）を patterns.md に追加する。**S6 完了後**、selftest / canonical example を拡張して回帰を固定した上で**統合累積レビュー**を行う。Critical/Important 指摘が出た場合は、単一ブランチ・回数上限つきの是正タスク（Cursor 実装＋Codex レビュー）で対応し、Claude fable で再レビューして指摘ゼロか 3 ラウンドの収束上限まで繰り返す。ブランチ横断の自動修正はしない。指摘が残らない状態でのみ完了とする。

## テスト戦略

- **単体（pytest, `scripts/tests/`）:** スライスごとに `test_<component>_renderer.py`（DOM 外形・意味 ID・manifest 完全性・量子化の決定性）と validation 受理/拒否ケース（bad IR フィクスチャ `component-bad-<component>-*.json`）。waterfall は Decimal 境界（誤差ちょうど半単位で受理・半単位超で拒否・float 拒否）を必須ケースとする。
- **ドリフト:** 既存 `test_component_contract.py` の語彙⇄スキーマ一致検査は enum 追加に自動追随する。レジストリ⇄語彙はロード時検査（`load_registry`）が担う。
- **最終文書:** 新 checker 規則ごとに bad HTML フィクスチャ（`component-bad-*.html` / `bad-*.html` 命名踏襲）で失敗を固定し、`test_component_checker.py` に期待診断を追加する。
- **統合:** スライスごとに valid assembly フィクスチャを `build_explainer.py` でビルドした生成 HTML を tests に固定し、`check.sh` 通過を検証する。**生成 HTML はライト/ダーク両テーマで人間が目視検査できる状態**（骨格のテーマ切替がそのまま効く自己完結 HTML）で PR に含める。
- **selftest:** `check.sh --selftest`（legacy 経路）は無変更で緑を維持する。

## リスクと弱い前提

- **選択の曖昧化:** relationship kind が 2→10 に増え、生成側モデルが誤った kind を宣言するリスク。対策: patterns.md の選択ガイド明文化。レジストリ発見は kind 一致＋集合包含のみなので、kind を正しく宣言すれば候補は一意。
- **中央揃え例外:** design-system.md に「図コンテナ内限定」と明記しないと、将来の生成が本文まで中央寄せする恐れ。S1 の docs 同期に含める。
- **renderer-svg:** 許可リスト・マニフェスト・機能拒否の三点が揃って初めて閉じる。どれか 1 つでも欠けた状態の中間コミットを残さない（S6 の原子性）。
- **量子化の粒度:** 幾何の 1% 量子化は視覚上十分という前提。valueText 常時表示が正確性の一次経路であり、幾何は補助である旨を design-system.md に記す。
- **基盤一般化の回帰:** S1 のディスパッチ化・検査一般化は matrix/flow の既存挙動を変えないことを既存テスト全緑で担保する（挙動変更は flow edge.relation のスコープ固定のみで、これは専用テストで意図を固定する）。
- **未検証の前提:** 8 コンポーネントの実使用頻度は未観測。ただし進行はスライス途中で止めず S6 まで実施し、需要検証は出荷後の実使用観測で行う（承認済み決定）。

## バックログ（見送り・再検討条件つき）

包含型（Venn 矩形版）・Venn・収束型（converging-flow）・フェーズゲート型（gated-phases）・criteria-board・decision-tree・compare 昇格・role-sequence・deviation-bars・range・funnel・risk-map（matrix の placement 拡張として実現可能性あり）・state-machine（後方遷移の一般解。chevron loop で不足する実需要が 2 件以上出たら設計議論を起こす）・swimlane-flow（role-sequence の需要観測後）・schedule・slope の異単位混在（per-item 正規化）。

## 参照

- 採用モック: `.visual-explain/2026-07-11-grouping-flow-variants-mock.html`（最終形）／`.visual-explain/2026-07-11-canonical-v2-candidates-mock.html`（全パレット）
- 決定記録: vault `canonical-v2-adopted-set`・`skeleton-tokens-are-inviolable-v2`・`bullet-lists-should-become-diagrams`
- 既存契約: `references/component-vocabulary.json`・`references/component-ir.schema.json`・`references/assembly.schema.json`・`assets/components/registry.json`・`references/design-system.md`（拡張ゲート 10 手順）・`scripts/ve_components/`・`scripts/check.sh`・`scripts/tests/`

## Spec Audit

現行実装（read-only 監査対象: `~/workspace/visual-explain/skills/visual-explain/`）との突合で見つかった矛盾・実装阻害の欠落・曖昧契約と、その本 spec 内での解決。

**解決済みの矛盾**

1. **inline style 禁止 vs カスタムプロパティ出力（実装阻害）:** 旧 spec は waterfall のレイアウトを `style="--start:…"` 相当で出すとしていたが、checker（`_ContentSafetyParser`）は content スロットのインライン `style` 属性を無条件拒否する。→ flow のレールと同じ**事前生成クラス駆動**（整数百分率量子化）に全面変更（「レイアウト出力の制約」節）。安全規則は緩めない。
2. **renderer-svg の位置づけ:** 旧 spec は legacy「自由 SVG 理由コメント」規則からの切り分けとしたが、その規則はコンポーネント文書では実行されない（`check.sh` の `pattern_checks` は type 付き legacy 文書限定）。→ コンポーネント checker への**新設ゲート**として具体設計（許可リスト・`svg_root_ids` マニフェスト・要素/属性許可リスト・bad フィクスチャ）。承認済み決定（slope@1 限定・unsafe SVG 機能拒否）をそのまま実装可能な形にした。
3. **S3 継続判断ゲート:** 旧 spec 末尾の「S1〜S3 出荷後に需要観測してから S4〜S6」は承認済み決定（S3 で止めず S6 まで、S6 後に統合累積レビュー＋回数上限つき単一ブランチ是正）と矛盾。→ 削除し、承認済みの進行・是正プロセスを「実装スライス分割」に明記。
4. **assembly.schema.json の enum 追加:** 旧 spec は同ファイルへの enum 追加を要求していたが、canonical 節は `component-ir.schema.json` への `$ref` 委譲で、同ファイル固有の enum は compatibility provenance のみ。→ 「変更不要」に訂正。
5. **チェブロン送り分けの機構:** 旧 spec は「capability `branching` の有無でレジストリ発見が送り分ける」としたが、`narrow_candidates` は relationship.kind の一致で先に絞る（kind⇄コンポーネントは 1:1）。→ kind 宣言が送り分けの実体である旨に訂正。

**解決済みの実装阻害の欠落**

6. **matrix/flow ハードコードの一般化:** payload 排他判定・`semantic_ids()`・注釈対象集合・`generated_relationship_ids` 交差検査・`ve-matrix-notes|ve-flow-notes` 必須検査が全て 2 枚前提で実装されており、そのままでは新コンポーネントの合法文書が**必ず**最終検査に落ちる。→ 「横断基盤の一般化」節として S1 のスコープに明記。
7. **閉集合の拡張漏れ:** 診断コード（`ALL_CODES`）と checker 規則名（`KNOWN_CHECKER_RULES`）は閉集合で、追加登録しない限り新コード発行／新レジストリエントリのロードが fail-closed で失敗する。→ 追加すべき具体名を列挙。
8. **Decimal の解析地点:** 承認済み決定「数値 JSON 字句を Decimal として解析」の実装点は `build_explainer.py` の `json.loads(parse_float=Decimal)`（`parse_int` は不変で `_is_int` 検査を保護）。Python API 経由の binary float は拒否。→ 「数値の取り扱い」節に確定。
9. **新レンダラの DOM 契約:** `validate_artifact_semantics` が要求する figcaption・意味 ID・注記リスト、および `data-ve-from/to`・`data-ve-row-id` を出すと flow/matrix 形状規則で誤検査される制約。→ 「共通レンダラ DOM 契約」＋属性禁止として明文化。

**解決済みの曖昧契約**

10. **flow `edge.relation` のスコープ:** 現行はグローバル capability 集合で検査しており、enum 拡張で flow 辺が新コンポーネントの capability を名乗れてしまう。→ flow 自身の capabilities に固定（実効的厳しさの保全であり、意味的に有効な既存入力の受理範囲は不変）。
11. **文字数の数え方:** Unicode コードポイント（`len()`）で確定。欠けていた上限（evidence label 40 字・slope item label 12 字・valueText 12〜16 字）を補充。
12. **loop と capability の整合:** `loop: true` ⇔ `closed-loop` 宣言の相互必須を追加。
13. **tone "neutral" の写像:** 専用トークンはなく、モノクロ階調への写像であることを明記（トークン不可侵と整合）。
14. **evidence-map の参照厳格化と matrix 先例:** 既存 matrix は未解決 `certaintyRef` を黙って非表示にするが、evidence-map は線種の意味が参照に依存するため受理拒否とする。matrix 側は変更しない（既存契約不変の原則）。
15. **拡張ゲート第 3 手順の文言:** 「matrix/flow が使わない IR フィールドを追加しない」は 8 コンポーネント追加と字義衝突する。本 spec がゲートの言う「コンポーネント拡張レビュー」に相当し、docs 同期で文言を一般化する。

**残存する人間判断:** なし。承認済み決定（renderer-svg 許可リスト方式・waterfall Decimal 半単位・S6 まで通し実施＋統合レビュー）で本監査の全論点は解決可能だった。なお解釈を 1 点固定した: 「自由 SVG の受理拒否」はコンポーネント文書の content スロット全体（compatibility 節経由の持込を含む）に適用する。互換節に SVG を許すと許可リストが迂回可能になるためで、fail-closed 原則からこの解釈を採った（legacy 単体文書の理由コメント付き SVG は従来どおり）。これが意図と異なる場合のみ差し戻しを求める。

---

ADOPTED: R1-1 — waterfall/slope の数値正規化を決定的規則として明文化（waterfall は基線 0 を常に含め負値・0 交差許可・range 0 は受理拒否、slope は 0 を含めず range 0 は垂直中央写像、クランプ禁止＝域外は renderer_failure、境界テスト必須ケースを列挙）。「数値の取り扱い」節。
ADOPTED: R1-2 — slope に payload 必須フィールド `unit`（非空・8 字以内）を追加し、「同一単位」を単一フィールド共有の構造で機械的に保証。`valueText` は不透明のまま照合せず、異単位混在（per-item unit）はバックログ。slope 契約節。
ADOPTED: R1-3 — number モードの最小可視内容契約を追加: enumeration/chevron の各 item/step は `title` か `description` の少なくとも一方が必須（番号だけの空ブロックを受理しない）。title 禁止の横チェブロン number モードでは description が全 step 必須に一意化。各契約節。
ADOPTED: R1-4 — 縦チェブロンの `description` を 1〜3 行・各 40 字以内と明示（横は従来どおり 1〜2 行・各 30 字以内）。chevron 契約節。
ADOPTED: R1-5 — renderer-svg の属性検査を要素別の閉じた完全一致許可リストに確定（暗黙カテゴリなし）、名前空間宣言とコロン含み属性名を一括拒否、数値属性は整数のみ、bad フィクスチャ 8 カテゴリ＋境界 valid フィクスチャを必須化。「renderer-svg ゲート」節。
ADOPTED: R2-I1 — renderer-svg の数値文法を内部整合な閉集合に修正: `viewBox` はスカラー整数ではなく固定 4 整数形 `0 0 600 220` との完全一致として別個検査、`preserveAspectRatio` は `xMidYMid meet`、`text-anchor` は `start`/`middle`/`end` の列挙値のみ、スカラー座標は `^-?[0-9]+$`（`r` は `^[0-9]+$`）を維持。「renderer-svg ゲート」節。
ADOPTED: R2-I2 — slope の固定 viewBox ジオメトリを決定的に確定: from X=120・to X=480、値バンド Y=20（上端）〜Y=200（下端）、反転 Y 写像 `y(v)=200−round((v−min)/range×180)`（ROUND_HALF_UP）で max が視覚的に上、range 0 は全点 Y=110、端点写像と増加/減少の方向性を必須テスト化。slope 契約節＋「数値の取り扱い」境界テスト。
ADOPTED: R2-M1 — capability enum の増分を訂正: 5 → 14（既存 5＋新規 9 を明示列挙）。「横断基盤の一般化」節。

STATUS: complete
