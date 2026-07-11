# visual-explain canonical v2 コンポーネント拡張 仕様

**ゴール:** 箇条書きで書かれがちな説明（並列の要点・分解・優先構造・手順・段階・増減・2時点変化・論拠）を、canonical IR から機械生成できる 8 コンポーネント（10 図形式）に拡張する。既存の安全アーキテクチャ（自己完結 HTML・固定領域・信頼レジストリ・fail-closed 診断・四層検査）と visual standard v1 の 3 層基準は一切弱めない。

**位置づけ:** ビジュアル基準 v1（2026-07-11 spec、PR #2 / `ee1a010` で実装済み）の次フェーズ。vault 筆頭方針「箇条書きの図解化」（`bullet-lists-should-become-diagrams`）に対応する。

## 前提決定（ユーザーヒアリング 2026-07-11）

| 論点 | 決定 | 帰結 |
|---|---|---|
| 骨格トークン | **不可侵**。コンサル調の配色・スタイル変更は不採用 | 新コンポーネントの CSS は既存トークンの参照のみ。トークンの追加・変更・上書きを提案しない |
| 採用セット | G1/G2 列挙型・G3 ロジックツリー・G5 ピラミッド・F1/F2 チェブロン・F3 階段型・B1 waterfall・B3 slope・E1 evidence-map の 10 図形式（8 コンポーネント） | 下記の個別契約を実装する |
| 縦横の出し分け | 列挙型・チェブロン・waterfall は同一 IR から presentation/orientation 設定で切替 | 意味（relationship）と表現（設定）を分離する既存思想を踏襲 |
| ブロックの中身 | 番号だけでなく概念ラベルにも対応（`blockContent: number | label`） | 列挙型・チェブロンの全バリアントに一貫適用 |
| 中央揃え | 列挙型（縦）とチェブロン（縦）は図全体を中央揃え | 幅は内容にフィット（`fit-content`）。単一幅カラム内での例外的中央配置として v1 の「中央寄せは使わない」規則に**限定的例外**を設ける（図コンテナ内のみ。本文・見出しには適用しない） |
| ループ | チェブロン縦のみ `loop: true` で「最終段→先頭」の戻り 1 本を許可 | 任意の後方遷移は導入しない（state-machine はバックログのまま）。旧 cycle 候補の需要をこの形式が吸収 |
| 見送り | 包含型・Venn・収束型・フェーズゲート・state-machine・swimlane・schedule・criteria-board・decision-tree・compare 昇格・deviation/range/funnel・risk-map | バックログとして本 spec 末尾に記録。実使用の需要観測後に再検討 |

デザイン参照モック（ブレスト成果物・canonical 生成物ではない）: `.visual-explain/2026-07-11-grouping-flow-variants-mock.html`（採用 10 図の最終形）、`.visual-explain/2026-07-11-canonical-v2-candidates-mock.html`（全 16 図パレット）。

## 全体アーキテクチャ方針

### 変えないもの

- 意思決定列（関係宣言 → レジストリ発見 → 明示選択 → 一致理由記録 → ビルド＋四層検証）と fail-closed 原則。生成失敗は診断を返して報告し、互換マークアップへ暗黙に切り替えない。
- IR に HTML/CSS/JavaScript/DOM 操作/座標を書かない。数値・テキスト・宣言のみ。レイアウト計算（waterfall の累積オフセット、slope の座標、階段の高さ）は全てレンダラの責務。
- 共通 IR フィールド（`id` / `relationship` / `selection` / `caption` / `certainty` / `sources` / `accessibility` / takeaway 注釈 3 種）の形。
- コンポーネント資産の所有権: 骨格がトークン・固定領域・固定 JS を所有し、コンポーネントは `[data-ve-component="<id>"]` を根とする名前空間化した最小 CSS のみを所有。**本番レジストリのスクリプト資産は空**（static-first）。
- 新コンポーネントの拡張ゲート 10 手順（design-system.md）を**コンポーネントごとに原子的に**満たす。部分的な本番エントリを残さない。

### 変えるもの

- `component-vocabulary.json` / `component-ir.schema.json` / `assembly.schema.json` の enum に 8 コンポーネントと新 relationship kind / capability を追加（ドリフト検査は既存のまま）。
- IR スキーマの `oneOf`（payload 排他）を 2 → 10 分岐に拡張。payload キーはコンポーネント ID と同名。
- レジストリに 8 エントリ、`TRUSTED_RENDERERS` に 8 つの `<id>@1`、checker に各コンポーネントの構造規則と bad フィクスチャを追加。
- patterns.md（語彙・組み立て例）、design-system.md（密度上限）、SKILL.md（図フォーマット列挙と選択ガイド）を各スライスで同期更新。

### チェブロンの位置づけ（設計判断）

ユーザー向け説明では「flow の presentation」と表現したが、実装は**独立コンポーネント `chevron`**（relationshipKind: `ordered-sequence`）とする。理由: (1) payload が線形の steps 配列であり、flow の nodes+edges+レール割当・行予算とは受理条件がまったく異なる。(2) flow renderer に presentation 分岐を足すと両方の fail-closed 契約が濁る。(3) 「分岐・合流が出たら flow へ、線形なら chevron へ」という送り分けを、レジストリの capability 差（`branching` の有無）として表現できる。flow 側の契約は一切変更しない。

## コンポーネント別契約

以下、全コンポーネント共通: contractVersion 1。ラベル・テキストの長さ上限は超過時に受理拒否（fail-closed）。判断色（accent/positive/warning）は下記で明示した箇所以外に使わず、ブロックの地はモノクロ階調のみ。図がコンテンツ幅を超える場合は各自の横スクロールコンテナ内で溢れさせる。

### 1. enumeration（列挙型）— G1/G2

- **relationshipKind:** `parallel-enumeration` ／ **capabilities:** `parallel-itemization`
- **payload:** `items[]`（2〜6 件）。item = `{id, label?, title?, description?}`
- **設定:** `presentation: "list"（縦・既定）| "columns"（横）`、`blockContent: "number"（既定）| "label"`
- **受理条件:**
  - `blockContent: "label"` → 全 item に `label`（16 字以内）必須、`title` 禁止（ラベルが見出しを兼ねる）。
  - `blockContent: "number"` → 番号はレンダラが 1..n を採番（IR に番号を書かない）。`title`（30 字以内）任意。
  - `presentation: "columns"` → items 2〜4 件。`description` は箇条書き 1〜4 行（各 40 字以内）。
  - `description` は全 item で省略可（コンセプトのみ表示）。一部 item だけの省略は不可（全有か全無。歯抜けは受理拒否）。
- **意味制約:** 順序を持たない並列関係であることを宣言する（番号は識別子であって順序ではない）。順序があるなら chevron を選ぶ。
- **表現:** 縦は図全体を中央揃え（`width: fit-content; margin-inline: auto`）。ブロック地は `--text-dim`、文字は `--bg`。横は狭い画面で縦積みに折り返す（意味順維持）。
- **縮退先:** 通常の箇条書き。

### 2. logic-tree（ロジックツリー）— G3

- **relationshipKind:** `hierarchical-decomposition` ／ **capabilities:** `mece-decomposition`
- **payload:** `root{id, label}`＋`branches[]`（2〜4 件）。branch = `{id, label, leaves?[]}`（leaf はテキスト、各 branch 0〜2 件・各 40 字以内）
- **受理条件:** 深さは root → branch → leaf の 2 段固定。ラベルは root 20 字・branch 16 字以内。
- **意味制約:** 「構成の分解」専用。読者がたどる判断の分岐（decision-tree、バックログ）とは区別し、誤用時は checker ではなく patterns.md の選択ガイドで防ぐ。分解の網羅性（MECE）は IR で機械検証できないため、caption または evidence 側で主張し、必要なら確度バッジを付ける。
- **表現:** 左に root、右に branch 列。接続線はレンダラ所有（手書き禁止）。狭い画面では縦積み（root 上・branch 下）。
- **縮退先:** `terms` または入れ子箇条書き。

### 3. pyramid（ピラミッド型）— G5

- **relationshipKind:** `layered-priority` ／ **capabilities:** `priority-layering`
- **payload:** `tiers[]`（3〜4 件、**上から下の順**）。tier = `{id, label, sub?}`（label 12 字・sub 30 字以内）
- **受理条件:** 先頭 tier ＝頂点＝最優先。幅はレンダラが段階計算（IR に幅を書かない）。
- **意味制約:** 「上に行くほど少なく・重要」という優先構造があるときだけ使う。単なる並列 3 項目は enumeration の仕事（patterns.md の選択ガイドに明記）。
- **表現:** 頂点 tier のみ `--border-strong` 地で強調（構造の合図であり判断色ではない）。他 tier は `--text-dim` 地。
- **縮退先:** enumeration（縦）。

### 4. chevron（チェブロン型）— F1/F2

- **relationshipKind:** `ordered-sequence` ／ **capabilities:** `linear-sequence`, `closed-loop`
- **payload:** `steps[]`（2〜6 件、宣言順＝実行順）。step = `{id, label?, title?, description?}`
- **設定:** `orientation: "vertical"（既定）| "horizontal"`、`blockContent: "number" | "label"`（規則は enumeration と同一）、`loop: false（既定）| true`
- **受理条件:**
  - `loop: true` は `orientation: "vertical"` のみ。戻り辺は「最終 step → 先頭 step」の 1 本だけをレンダラが描く（IR に辺を書かない）。それ以外の後方遷移が必要な説明は受理せず、flow か文章へ送る診断を返す。
  - `orientation: "horizontal"` → steps 3〜6 件、`title` 禁止、`description` は箇条書き 1〜2 行（各 30 字以内）。
  - `description` の全有/全無規則は enumeration と同一。
- **意味制約:** 分岐・合流のない線形順序専用。分岐が要るなら flow（capability `branching` を持つのは flow のみ、という差でレジストリ発見が自然に送り分ける）。
- **表現:** 縦は下向きチェブロン（clip-path はコンポーネント CSS 所有）で図全体を中央揃え。ループは左レール＋下向き矢頭で、レールはレンダラ所有。横は左に切り欠きのある矢羽で、狭い画面では縦積みへ折り返す（ループなし形式のみなので折返しで意味は壊れない）。
- **縮退先:** インライン `flow`（`<ol class="flow">`）または番号付き箇条書き。

### 5. stairs（階段型）— F3

- **relationshipKind:** `staged-maturity` ／ **capabilities:** `maturity-staging`
- **payload:** `stages[]`（3〜5 件、低い段から高い段の順）。stage = `{id, label, note?, current?}`（label 14 字・note 20 字以内）
- **受理条件:** `current: true` は最大 1 件。踏み面の高さはレンダラが等差で計算（IR に高さを書かない）。
- **意味制約:** 各段が「到達したら留まる状態」（成熟度・移行フェーズ）のときに使う。流れる工程は chevron。
- **表現:** `current` 段の踏み面のみ `--accent`（現在地強調はトークン契約上の正当用途）。ただし色だけに意味を持たせず、`current` 段の note にテキストでの現在地表記を必須にする（note がなければ受理拒否）。最終段の強調はしない（v1 モックの「最終段=強」は誤解を招くため不採用）。
- **縮退先:** `timeline` または enumeration。

### 6. waterfall（ウォーターフォール）— B1

- **relationshipKind:** `additive-bridge` ／ **capabilities:** `additive-bridging`
- **payload:** `start{id, label, value, valueText}`＋`steps[]`＋`end{id, label, value, valueText}`。step = `{id, label, delta, valueText, tone}`
  - `value` / `delta` は数値（レンダラのスケール計算用）、`valueText` は表示テキスト（単位込み・必須。棒だけで値を伝えない）。
  - `tone: "positive" | "warning" | "neutral"` を**ステップごとに宣言必須**。増減の符号と良し悪しを分離する（増加が常に悪ではない）。start/end はモノクロ固定。
- **設定:** `orientation: "bars"（行型・既定）| "columns"（横並び型・縦棒ブリッジ）`
- **受理条件:**
  - **整合検証: `start.value + Σ delta == end.value`**（許容誤差は表示精度の半単位）。不一致は受理拒否 — 数の合わない橋を描かない。
  - `orientation: "bars"` → steps 1〜4 件（全 3〜6 行）。`orientation: "columns"` → steps 1〜7 件（全 3〜9 列）。ラベルは 12 字以内（columns では 2 行折返しまで）。
- **表現:** 累積オフセット・浮動バー位置・破線コネクタ（前バーの上端/下端から次バーへ）は全てレンダラが計算し、コンポーネント CSS のカスタムプロパティ（`--start`/`--len`/`--base` 相当）として出力する。columns は狭い画面で bars へ**レンダラが縮退しない**（静的 HTML のため）— 代わりに横スクロールコンテナで溢れさせ、生成時の選択ガイドで bars を推奨する。
- **縮退先:** `bars`（既存互換）または matrix。

### 7. slope（スロープ）— B3

- **relationshipKind:** `two-point-change` ／ **capabilities:** `two-point-comparison`
- **payload:** `axes{fromLabel, toLabel}`（各 8 字以内）＋`items[]`（1〜5 件）。item = `{id, label, fromValue, toValue, fromValueText, toValueText, tone}`
  - `tone: "positive" | "warning" | "neutral"` 宣言必須（改善/悪化/不変の判断はデータからの自動判定にしない）。
- **受理条件:** 2 時点のみ（3 点以上は timeline/文章へ）。items の値は同一単位・同一スケールで正規化可能であること（異単位混在は per-item 正規化: 各 item の from/to を相対で描き、絶対比較を示唆しない旨を accessibility.summary に書く — 初版は**同一単位のみ受理**とし、異単位はバックログ）。
- **表現:** レンダラが決定的に SVG を生成する（座標は値から線形正規化）。**canonical レンダラが SVG を出す初のケース**であり、checker の「自由 SVG には理由コメント必須」規則とは区別する: レンダラ生成 SVG はマニフェストで宣言し、checker はマニフェスト宣言済み SVG を「自由 SVG」扱いしない（新規則 `renderer-svg`）。テキスト（両端の値・項目名）は SVG 内でも `--fs-figure` 相当を維持し、値は両端に必ず併記。
- **縮退先:** matrix（before/after の 2 列表）。

### 8. evidence-map（論拠地図）— E1

- **relationshipKind:** `claim-support` ／ **capabilities:** `claim-support-mapping`
- **payload:** `conclusion{id, label}`（30 字以内）＋`evidence[]`（2〜4 件）。evidence = `{id, label, certaintyRef, sourceRef?}`
  - `certaintyRef` は**必須**で、共通フィールド `certainty[]` 内の assertion を参照する。未解決参照は受理拒否。
- **受理条件:** 結論 1 件・階層 1 段のみ（根拠の根拠は描かない。必要なら図を分割）。
- **表現:** 支持リンクの線種は参照先の確度から導出する（confirmed=実線・inferred=破線・unverified=点線。v1 の確度線種契約をリンクに適用）。線種だけに意味を持たせず、各 evidence カード内に既存のモノクロ確度バッジを必ず表示する。結論カードは `--border-strong` の枠で強調。
- **縮退先:** 文章＋確度バッジ（既存記法）。

## 四層検査への追加

- **IR/選択層:** 8 コンポーネントの payload スキーマ検証、enum ドリフト検査（語彙 ⇄ スキーマ ⇄ レジストリ）、各受理条件（件数・長さ・全有全無・current 最大 1・certaintyRef 解決・waterfall 整合）を validation に追加。診断コードは既存の命名に倣い `<component>_structure_violation` 系で追加する。
- **コンポーネント/マニフェスト層:** 各レンダラは全意味 ID を消費するマニフェストを返す（既存契約）。slope はマニフェストに SVG 出力を宣言する。
- **最終文書層:** checkerRules に共通規則（static-content / semantic-ids / escaping / no-external-reference / responsive-order）＋コンポーネント固有規則（`enumeration-structure` / `logic-tree-structure` / `pyramid-structure` / `chevron-structure` / `stairs-structure` / `waterfall-consistency` / `slope-structure`＋`renderer-svg` / `evidence-map-references`）を追加。各規則に最低 1 つの bad フィクスチャで失敗を固定する。
- **密度上限（design-system.md 追記）:** enumeration 6 項目（columns 4）・logic-tree 枝 4・pyramid 4 層・chevron 6 段・stairs 5 段・waterfall 行型 6 行/横並び 9 列・slope 5 項目・evidence-map 根拠 4 件。超過は分割か縮退。

## 実装スライス分割

各スライスは拡張ゲート 10 手順を原子的に満たし、`check.sh` と全テストが緑の状態で完結する（1 スライス＝1 PR 目安）。

| スライス | 内容 | 根拠 |
|---|---|---|
| S1 | **enumeration**（list/columns・blockContent・中央揃え） | 最低難度で「ブロック」表現と新コンポーネント追加の型（語彙→スキーマ→レンダラ→レジストリ→checker→フィクスチャ）を確立する |
| S2 | **chevron**（vertical/horizontal・blockContent・loop） | S1 のブロック部品思想を順序系に展開。loop レールが唯一の新規レイアウト要素 |
| S3 | **pyramid ＋ stairs** | いずれも低難度の静的形状。S1/S2 で確立した型の量産検証 |
| S4 | **logic-tree** | 接続線をレンダラ所有で描く最初のケース（flow のコネクタ資産とは独立） |
| S5 | **waterfall**（bars/columns・整合検証） | 数値スケール計算と受理時整合検証という新しい検証カテゴリ |
| S6 | **slope ＋ evidence-map** | レンダラ生成 SVG（`renderer-svg` 規則）と確度参照の結合。最も検査変更が大きいため最後 |

各スライスで patterns.md / design-system.md / SKILL.md の該当節を同時更新し、canonical 例（IR JSON）を patterns.md に追加する。全スライス完了後に selftest / canonical example を拡張して回帰を固定する。

## リスクと弱い前提

- **選択の曖昧化:** 語彙が 2→10 relationship kind に増え、生成側モデルが誤った kind を宣言するリスク。対策: patterns.md に「箇条書き種別 → 図」の選択ガイド（logic-tree の分解 vs decision の区別、enumeration vs chevron の `ordered` 判定、pyramid の誤用禁止）を明文化。レジストリ発見は集合包含のみなので、kind を正しく宣言すれば候補は一意に絞れる。
- **中央揃え例外:** v1 の「中央寄せは使わない」との整合。図コンテナ内限定の例外として design-system.md に明記しないと、将来の生成が本文まで中央寄せする恐れ。
- **レンダラ生成 SVG:** 既存 checker の自由 SVG 規則との切り分け（`renderer-svg`）が新設計。ここの設計を誤ると「なんでも SVG」への抜け穴になる — マニフェスト宣言＋レンダラ許可リストの二重ゲートで閉じる。
- **waterfall の浮動小数:** delta 合計の等値判定は表示精度ベースの許容誤差で行う。仕様は「表示精度の半単位」だが、実装時に丸め規約（単位換算を IR に持ち込まない）を確定する必要がある。
- **未検証の前提:** 8 コンポーネントの実使用頻度は未観測。S1〜S3（低難度 5 図）出荷後に実使用で需要を確かめてから S4〜S6 を進める判断余地を残す。

## バックログ（見送り・再検討条件つき）

包含型（Venn 矩形版）・Venn・収束型（converging-flow）・フェーズゲート型（gated-phases）・criteria-board・decision-tree・compare 昇格・role-sequence・deviation-bars・range・funnel・risk-map（matrix の placement 拡張として実現可能性あり）・state-machine（後方遷移の一般解。chevron loop で不足する実需要が 2 件以上出たら設計議論を起こす）・swimlane-flow（role-sequence の需要観測後）・schedule。

## 参照

- 採用モック: `.visual-explain/2026-07-11-grouping-flow-variants-mock.html`（最終形）／`.visual-explain/2026-07-11-canonical-v2-candidates-mock.html`（全パレット）
- 決定記録: vault `canonical-v2-adopted-set`・`skeleton-tokens-are-inviolable-v2`・`bullet-lists-should-become-diagrams`
- 既存契約: `references/component-vocabulary.json`・`references/component-ir.schema.json`・`assets/components/registry.json`・`references/design-system.md`（拡張ゲート 10 手順）・`scripts/ve_components/`
