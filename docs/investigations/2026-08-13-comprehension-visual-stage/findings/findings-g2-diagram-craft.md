# G2 図モジュール品質

> Worker 2 調査成果物。対象リポジトリ `visual-explain`（read-only）。
> 範囲: 矢印（flow / chevron-loop / logic-tree）と改行（enumeration / chevron description）。
> コード変更・依存追加・サーバ起動は一切行っていない。証拠・推奨のみ。

## 要約（5行以内）

1. 「三角と棒の分離」は**特定の矢印実装 2 箇所**（flow の skip レール、chevron の loop レール）に固有で、どちらも**「棒=要素の border」「三角=独立した `::after`（グリフまたは border-triangle）」を別々に位置決めして貼り合わせる CSS アセンブリ**が原因。
2. 一方で chevron 本体のノッチは `clip-path` 1 枚（原子・分離不可）、flow の隣接矢印は `↓` 1 文字（原子）で、これらは分離しない。つまり問題は「矢印全部」ではなく「レール系の貼り合わせ」に局在する。
3. **幾何（ピクセル位置・三角と棒の接続・矢印がノード中心を指すか）は一切検証されていない。** `validation.py` はトポロジ（前向き辺・ファン幅・レール本数・行予算）のみを検査し、レンダラテストは DOM 文字列（`assertIn "ve-rail-..."` 等）のみを検証する。行レベルの配置は正しく決定論的だが、ピクセルレベルの接続は保証されない。
4. システムは**本来 SVG 矢印を描ける能力**（`slope.py` の `<line>`、`skeleton.html` の `connector JS`＝`<path>`+`<marker>`）を持つが、設計思想「No scripts, no inline styles, no free coordinates」により flow / chevron / logic-tree は CSS のみを選び、SVG を放棄した。三角+棒の脆弱性はこの制約の**直接的な副作用**。
5. 改行崩れは CSS の `overflow` / `hyphens` 起因ではなく、**IR 契約**（`description: tuple[str,...]` の各要素＝1 箇条書き）とレンダラの写像（1 行→1 `<p>`/`<li>` ＋ `::before "・"`）の合成結果。弱いモデルが文章を細断片化すると「変な改行/過剰なビュレット」に見える。

---

## 矢印系の根因候補（コード根拠付き）

### 候補 F1: flow skip レール＝「border の "[" 括弧 ＋ `::after` の ◀ グリフ」の貼り合わせ（最重要）

`assets/components/flow.css:15-16`
```css
.ve-flow-rail { position: relative;
  border-right: 2.5px solid var(--dg-line);
  border-top: 2.5px solid var(--dg-line);
  border-bottom: 2.5px solid var(--dg-line);      /* ←「棒」はこの3辺の括弧 */
  writing-mode: vertical-rl; ... }
.ve-flow-rail::after { content: "\25C0";          /* ←「三角」は ◀ グリフ */
  position: absolute; inset-block-end: -0.15rem; inset-inline-start: -0.5rem;
  color: var(--dg-line); font-size: .7rem; writing-mode: horizontal-tb; }
```

- **棒**＝`.ve-flow-rail` 自身の border 3 辺（右・上・下）で描く "[" 括弧。寸法は grid セル（`grid-row: rs/(rt+1)`）で決まる。
- **三角**＝`::after` の Unicode `◀`（`\25C0`）。`position:absolute` で **負の rem オフセット**（下に 0.15rem・左に 0.5rem）だけ rail box の外側に浮かせている。
- 分離メカニズム: 三角の縦位置は「ターゲットノード行の下端 + 0.15rem」に固定される。ノードの高さはラベルの折り返し次第（`grid-auto-rows: min-content`）で変動するため、三角はターゲット**中央ではなく下端**を指しがち。またオフセットが固定 rem なので、フォントメトリクス（グリフ `.7rem` の描画幅・ベースライン）と border の太さ（2.5px）の組み合わせで、グリフと括弧の角の間に**視覚的な隙間**が開く。これが「三角が棒から離れて見える」正体。
- 上角（skip が**始まる**側）には矢印が一切なく、下端にのみ ◀ があるため、**非対称で未完成な矢印**に見える（美的問題 G3/C にも通ず）。

レンダラ側 `renderers/flow.py:132` はクラス `ve-rail-lane-N ve-rail-{rs}-{rt+1}` を付与するだけで、三角の位置は CSS 任せ。行スパンの計算自体は `flow_layout.py`（`assign_rails` / `_spine_walk`）で**正しく決定論的**に行われる。壊れているのは「行は合っているがピクセルが合っていない」層。

### 候補 F2: flow 隣接矢印＝`↓` 1 文字（原子・分離しない）

`renderers/flow.py:88` → `<span class="ve-flow-arrow" aria-hidden="true">↓</span>`、`flow.css:12` は `color/font-weight` のみ。
単一グリフなので「三角と棒の分離」は**起こらない**。`ve-flow-link` は `display:grid; grid-template-columns: auto auto 1fr`（`flow.css:13`）で矢印・ラベル・関係を整列させ、位置は安定。**ここは健全。**

### 候補 C1: chevron loop レール＝4 部品の手調整アセンブリ（レスポンシブで脱同期）

`assets/components/chevron.css:10-21`
```css
.ve-chevron-loop-rail { position:absolute; left:.5rem; top:.5rem; bottom:.2rem;
  width: calc(var(--chv-cx) - .5rem);
  border: 2.5px solid var(--dg-line); border-right: 0; }       /* 部品1: 括弧 */
.ve-chevron-loop-rail::before { ...; top:-2.5px; right:-2.5px;
  height:.95rem; border-right: 2.5px solid var(--dg-line); }   /* 部品2: 折返し縦線 */
.ve-chevron-loop-rail::after { ...; top: calc(.95rem - 2.5px); right:-.6rem;
  border:.6rem solid transparent; border-top:.85rem solid var(--dg-line);
  border-bottom:0; }                                           /* 部品3: border-triangle 矢印 */
.ve-chevron-loop-tail { position:absolute; left: calc(var(--chv-cx) - 1.25px);
  bottom:.2rem; height:1rem; border-left:2.5px solid var(--dg-line); } /* 部品4: 末尾縦線 */
```

- 戻り経路を**4 つの独立要素**（括弧 border / `::before` 折返し / `::after` 矢印 / `loop-tail`）で貼り合わせ。矢印（部品3）は固定 rem（`top: calc(.95rem - 2.5px)`）で、第1ステップの box 上端（`padding-top: 2.3rem`）に**手動で寸法合わせ**している。
- **レスポンシブ脱同期（決定的）**: `@media (max-width:42rem)`（`chevron.css:54-57`）は `--chv-cx: 50%`・`padding-left:1.8rem` に変えるが、矢印の `top`（`::after`）も `loop-tail` の位置も**再導出しない**。狭画面では `--chv-cx` が 9rem→50% に変わるため、部品4（`left: calc(50% - 1.25px)`）とステップの concept box（grid 13rem／狭では 1fr）がずれ、**部品同士がバラける**。これが「三角と棒が離れる」の最も再現性の高い経路。
- なお loop は `chevron.loop==True and orientation=="vertical"`（`renderers/chevron.py:74`）でのみ描画。水平 chevron では部品0〜3 は一切出ない。

### 候補 C2: chevron 本体ノッチ＝`clip-path` 1 枚（原子・分離しない）

`chevron.css:31`（縦）/ `:49`（横）。ノッチは box と同一要素の clip なので**分離不可・健全**。
水平 chevron はステップ間に**明示的な矢印を持たず**、ノッチ形状のみで方向を暗示する（頑健だが、方向が控えめに見える要因）。

### 候補 L1: logic-tree＝elbow 線のみ・矢印（三角）なし

`assets/components/logic-tree.css:11-24`
```css
.ve-lt-stub { flex:0 0 1.5rem; border-top:2px solid var(--dg-line); align-self:center; } /* 根→子の水平線 */
.ve-lt-child::before { ...; left:0; top:50%; width:1.5rem; border-top:2px solid var(--dg-line); } /* 各子への水平stub */
.ve-lt-child::after { ...; left:0; top:0; bottom:0; border-left:2px solid var(--dg-line); }       /* 兄弟をつなぐ縦線 */
.ve-lt-child:first-child::after { top:50%; } .ve-lt-child:last-child::after { top:0; bottom:50%; }
```

- 「三角と棒の分離」は**該当なし**（三角が存在しない）。純粋な線の elbow。
- 残るリスクは**線の位置ずれ**のみ: `::before`（水平stub）は `top:50%`、縦線 `::after` は `top:0;bottom:0`。`.ve-lt-child` は `display:flex; align-items:center`（`logic-tree.css:14-15`）なのでノードは中央に来るが、**分岐ノードの高さが子孫列の高さに依存**するため、深さの異なる枝では stub とノード中心の相対関係が揺らぐ余地がある（軽微）。`overflow-x:auto`（`:10`）で広がりは吸収。

### 候補 S（参考）: システムは SVG 矢印を描けるが、これらのコンポーネントは使わない

- `renderers/slope.py:53-76` は `<svg>` 内に `<line>` を描き、`renderer-svg` gate で検証される（決定論的 SVG 幾何）。
- `assets/skeleton.html:317-` の「FIXED CONNECTOR JS」は `<path>` cubic-bezier ＋ `<marker id="connector-arrow">`（`M0,0 L8,4 L0,8 Z`）で**矢印がパスと一体化**（分離不可）。
- しかし connector JS は `[data-connect]`／`.figure`（旧記法）専用で、`data-ve-component` 系レンダラは `data-connect` を**一切出力しない**（`rg data-connect renderers/` → 空）。flow/chevron/logic-tree はこの堅牢な SVG 経路を使わず、CSS 貼り合わせを選んだ。

---

## 改行崩れの切り分け

対象: enumeration / chevron の description。CSS・IR・レンダラの 3 層を切り分けた結果、**主因は IR 契約＋レンダラ写像**で、CSS(overflow/hyphens) 起因ではない。

| 層 | 観察 | 判定 |
|---|---|---|
| CSS `overflow`/`hyphens`/`word-break` | enumeration.css に該当プロパティ**なし**。`.ve-enum-block` は `minmax(0,1fr)`（`:7`）、columns は `minmax(10rem,1fr)`（`:5`）で**はみ出し防止済み** | **関与なし** |
| IR 契約 | `EnumerationItem.description: tuple[str,...]`（`model.py`）。要素 = 「1 行」の意味 | **主因** |
| レンダラ写像 | enumeration: 1 行→1 `<p class="ve-enum-desc">`、`::before{content:"・"}`（`enumeration.py:28-37`, `enumeration.css:17-20`）。chevron: 1 行→1 `<li>`、`::before{content:"・"}`（`chevron.py:28-37`, `chevron.css` description） | **主因** |
| 表示結果 | 各 IR 行が**すべて独立のビュレット**になる。1 文を複数行に分けると「過剰なビュレット/変な改行」に見える | 契約の副作用 |

補足:
- columns（`presentation:"columns"`）でカラム幅 ~10rem になると、1 行の日本語が**数文字ごとに折り返す**。`text-indent:-1.1rem; padding-left:1.1rem`（`:18`）のハンギングインデントは継続行も揃うため**レイアウト崩れではない**が、視覚的に「詰まった細切れ」に見える。これも IR の行分割が増幅要因。
- chevron description は `<ul><li>` なので、ステップ box（`min-height:6.5rem`, `chevron.css:30`）の横にビュレットリストが並ぶ。行数が多いと box とリストの高さが不揃いになり、整列が乱れて見える（grid `align-items:center` で中央揃えされるため致命的ではない）。

**結論**: 「変な改行」は CSS バグではなく、**「文章を行に分割する」IR 抽象と「行=ビュレット」レンダラ契約の組合せ**。弱いモデルが文章を細かく割くと顕在化する。

---

## A/B/C 分類

### (A) バグ／契約欠落

- **A1［flow レール矢印の幾何不保証］**: トポロジ（`flow_layout.check_topology`/`check_row_budget`、`validation.py:1854-1867`）と行スパン（`flow.py:132` の `ve-rail-{s}-{e}`）は正しいが、**三角(`::after`)が棒に接するか／ターゲットを指すかを検証する契約が存在しない**。レンダラテスト（`test_flow_renderer.py`）も `assertIn "ve-rail-..."` 等の DOM 文字列検査のみでピクセルを含まない。→ 矢印ずれを検出する品質フロアが無い。
- **A2［chevron loop のレスポンシブ非再計算］**: `@media(max-width:42rem)`（`chevron.css:54-57`）が `--chv-cx`・`padding-left` を変える一方、矢印(`::after` `top`)・`loop-tail`(`left`) を再導出しない。狭画面で部品がバラける**再現性のある不具合**。
- **A3［description の行=ビュレット契約］**: `tuple[str,...]` 各要素が無条件でビュレット 1 件になる（`enumeration.py:37`, `chevron.py:36-37`）。**「流れる文章」か「箇条書き」かを区別する抽象が無い**ため、IR の分割粒度がそのまま表示の細断化になる。

### (B) 意図的制約の副作用

- **B1［no-coordinates 制約 → CSS アセンブリ矢印］**: flow.py docstring（`renderers/flow.py:6-9`）「No scripts, no inline styles, no free coordinates: layout is entirely class-driven so the checker can re-derive every node and edge from the DOM」。座標禁止が**.border + グリフ + border-triangle の貼り合わせ**を強制し、三角と棒の分離可能性を生む。システムは SVG 能力（slope, connector JS）を持つが、この制約下では flow/chevron/logic-tree に採用できない。
- **B2［決定論的 class 駆動 → 行は合うがピクセルは合わない］**: `ve-rail-{s}-{e}` を事前生成（`MAX_SPINE_ROWS=28`, `flow_layout.py`）して checker 再導出可能にした代償として、**ピクセル幾何を CSS に委ね**、検証対象から外した。
- **B3［行=ビュレットは“並列項目”の意図的表現］**: enumeration は「並列項目の列挙」（`enumeration-doc.html` タイトル）が本来用途。ビュレット化は意図的だが、**弱いモデルが説明文まで箇条化**すると副作用として顕在化する。

### (C) デザイン美学の未熟

- **C1［非対称・未完成なレール矢印］**: flow レールは「[」括弧＋下端にのみ ◀。上角に矢印が無く、**途切れた/未完成**に見える（`flow.css:15-16`）。
- **C2［ループの 4 部品視覚ノイズ］**: chevron loop は border・stub 2 本・border-triangle が重なり、**線の太さ(2.5px)と三角形(.85rem)のバランスが荒い**（`chevron.css:10-21`）。
- **C3［logic-tree の無方向］**: 矢印が一本も無く、位置のみで方向を暗示。分解図としては最小限だが、有向関係では**曖昧さ**残る（`logic-tree.css`）。
- **C4［コネクタの色・太さが機能一色］**: 全コネクタ `--dg-line:#7F7F7F`・2〜2.5px で平坦。関係の種類（順序/分岐/ループ）を**色や太さで差別化しない**ため、図としての情報量が低い。

---

## 文章依存イシューとの独立度

**概ね独立（局所的に重複）。**

- 矢印の幾何（F1/F2/C1）と logic-tree の線（L1）を直しても、**本文（narrative/caption/summary/description）のテキスト量は減らない**。したがって「文章をほぼ読まずに理解」の主たる障壁（テキスト過多）は**残る**。→ 独立。
- ただし flow/chevron/logic-tree は**まさに“関係”を伝える図**であり、これらの矢印が壊れていると関係が視覚で伝わらず、**ユーザーはテキストラベルを読まねば関係を理解できない**。成功条件「主張と関係が頭に入る」の“関係”側を支えるのがこのグループ。→ 矢印品質は**必要条件**（関係の視覚化）だが**十分条件ではない**（文章削減は別件）。
- **重複ポイント（約 20–30%）**: A3（description 行=ビュレット契約）。これは“図の部品”である description が**テキストの塊**でもある。ここを“図寄りの短ラベル”に変えれば、図品質向上とテキスト負荷軽減が**同時に**進む。G1（文章依存）とここだけ交差する。
- 結論: G2 を完遂しても文章依存イシューは**根本には解消しない**が、“関係が視覚で伝わる”という必要条件を満たし、description 契約（A3）の改善に限っては文章依存の改善にも寄与する。

---

## 結論（このグループ単体）

- 「矢印ずれ・三角と棒の分離」は**品質フロア欠陥（A1/A2）と意図的制約の副作用（B1/B2）の合成**で、**表現力不足（SVG を使わない選択）が根**。局所は flow skip レール（`flow.css:15-16`）と chevron loop レール（`chevron.css:10-21,54-57`）の 2 箇所のみ。それ以外（隣接 `↓`・chevron ノッチ `clip-path`）は原子で健全。
- 「箇条書きの変な改行」は CSS バグではなく**IR 契約（行=ビュレット）とレンダラ写像の副作用（A3/B3）**。CSS は `minmax(0,1fr)` ではみ出しを正しく処理済み。
- 品質フロアの**最大の穴は「幾何検証の不在」**: トポロジは検証するがピクセル接続を検証しない（`validation.py`・レンダラテストともに）。これが「弱いモデルでも品質フロアを守る」という設計目標に対する**構造的ギャップ**。
- 推奨方向（実装禁止・調査のみ）: (1) 矢印を CSS 貼り合わせから**単一ベクタ**（既存の SVG 能力／connector JS の marker 方式）に寄せる、もしくは clip-path のように要素一体化する；(2) ループ系の rem 手調整を**変数化しレスポンシブで再導出**する；(3) description 契約に「prose/list 判別」を導入しビュレット化を条件付ける；(4) 幾何（三角-棒の接続・ノード中心への指向）を** checker で静的検証可能な契約**として定義する。いずれも設計思想（no-coordinates／決定論的／checker 再導出可能）との整合を要する。
