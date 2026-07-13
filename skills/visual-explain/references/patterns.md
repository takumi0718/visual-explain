# 構成と図フォーマットの契約

この資料では、固定骨格の `TITLE:BEGIN` と `TITLE:END` の間に非空のプレーンテキスト文書名を持つ `<title>` 要素を1つだけ置き、本文は `CONTENT:BEGIN` と `CONTENT:END` の間だけを編集する。`{{...}}` の未解決プレースホルダーやタイトル内のマークアップは使わない。ほかの領域は1バイトも変更しない。図はここにある HTML 契約どおりに埋め、座標、独自 CSS、独自 JavaScript を追加しない。各セクションは **1つの問い**だけに答え、目安を**主張1行・根拠2〜3行**にする。図・表・短文のうち最短で明確に伝わる1つを主にし、図が短文より明確になる理由がないなら図を使わない。根拠は主張または図の近傍に置く。核心、制約、反証を折りたたみに隠してはならない。

## 共通契約

- **見出しはアクションタイトル**にする。述語を持つ自己完結した主張だけを見出しにし、トピック名（「性能について」「代替案」）を禁じる。「案Aは案Bより速いが検証が要る」のように、見出しだけで何を判断すべきかが分かる一文にする。1見出し＝1洞察、40〜50字を目安にする。資料型テンプレートが必須と定める末尾の固定セクション見出し（「リスクと弱い前提」「不確かな点」「限界・確度」「限界・反証・確度」）は構造上のランドマークであり、アクションタイトル契約の適用外とする。それ以外の全セクション見出しには契約を適用する。
- **horizontal logic 自己検査**: 資料を完成させる前に、見出しだけを上から順に読め。見出しの列だけで承認/却下を判断できなければ、見出しを書き直す。
- **キャプションは takeaway**にする。図のキャプションはその図から持ち帰る1文にし、図の説明文・操作手順・凡例の言い換えを書かない（下記「図のキャプション規約」）。

## Pi/Katsura Qwen 固有の保守的縮退

Pi 上の Katsura Qwen では、必須事実の因果を原因→結果の原文どおりに保持するか引用する。順序が明示的な必須事実でない限り矢印や連番を描かず、許される推論は対象の直近で **推論** と明記する。因果・順序が不確かなら、flow ではなく `matrix`、`terms`、または文章を使う。この追加制約は同モデル専用であり、一般の図契約を緩めない。

## 資料型の構成テンプレート

### 提案承認型

1. 第一画面は `first-screen` を使い、`h1` タイトルに資料全体の主張を1文で置く（述語を持つ1文にしてトピック名を禁じ、40字目安。`<title>` 要素と同文にする）。続けて `subtitle` に**あなたが決めること**を1文で置く（判断のない資料型では「この資料が答える問い」を1文にする）。最後に判断を左右する条件を最大2件だけ置く。同じ判断文を末尾に重複させない。第三者が第一画面を3秒見て「何の話か」「何を判断するか」を答えられる状態にする。
2. 新出用語が多いときだけ、先に用語表を置く。
3. 現状と問題を図で示す。
4. 提案は before/after を等しい大きさで並べる。
5. 検討した代替案とトレードオフを比較表にする。単一案を決め打ちしない。
6. 末尾に「リスクと弱い前提」と「不確かな点」を必ず置く。

### 仕組み理解型

1. TL;DR で仕組みを一言で示す。`subtitle` を使う場合は、あなたが決めることの代わりに「この資料が答える問い」を1文で示す。
2. 新出用語が多いときだけ、先に用語表を置く。
3. 全体地図で zoom-out の構造を示す。
4. 主要フローでデータまたは処理の流れを示す。動きが核心ならステッパーを使う。
5. 判断に不要な検証過程と補足だけを `deep-dive` に入れる。
6. 末尾に「限界・確度」を置き、推論で補った箇所を明示する。

### 調査報告型

1. 結論または推奨を最初に示す。`subtitle` を使う場合は、あなたが決めることの代わりに「この資料が答える問い」を1文で示す。
2. 主要な発見は、1発見につき1ブロックにし、近傍に出典リンクを置く。
3. 定量データが必要なときだけ可視化する。
4. 末尾に「限界・反証・確度」を置く。

## 図のキャプション規約

caption はその図から持ち帰る1文（takeaway）にする。図の説明文（「役割と操作の表」）や操作手順を書かない。読み手が図を1つだけ見て持ち帰るべき結論を書け。

- takeaway が図の特定のセル/ノード/エッジで証明されるなら、canonical IR の `takeawayTargetIds` でその対象を **1〜3件** 指す。
- 局所の補足は `emphasis` で対象の直近に短く書く（全体で最大3件、対象ごとに1件まで、各ラベル40字以内）。
- 図全体がそのまま主張であり、指すべき単一の対象がないときだけ `takeawayScope: "whole"` を明示する。これは「caption 自体が図全体の takeaway だ」という意思表示で、視覚マーカーは付かない。`takeawayScope: "whole"` と `takeawayTargetIds` は併用できない。

## 共通の文法ブロック

必要な部品だけを使う。全セクションに全部を置く必要はない。

```html
<section>
  <p class="claim">この節で答える主張を1行で書く。</p>
  <figure class="figure">
    <!-- この節の図または表 -->
    <figcaption>この図から持ち帰る1文（takeaway）。説明文を書かない。</figcaption>
  </figure>
  <p class="evidence">根拠を2〜3行で、主張の近くに書く。</p>
  <details class="deep-dive"><summary>補足の検証過程</summary><pre>必要な詳細</pre></details>
</section>
```

### ask ブロック — 未決事項・依頼・検証待ち主張

読み手に判断・行動・検証を求める箇所は ask ブロックで明示する。使い分けは次の1行ずつ。

- **未決事項は `decision`**: これから決める選択。選択肢を2件以上並べ、各選択肢にトレードオフを添える。
- **ユーザーへの依頼は `request`**: 誰が何をするかの手順。各手順に主体（役割）を付ける。
- **検証待ち主張は `hypothesis`**: まだ確証がない主張と、その検証方法。

`decision`。選択肢は2件以上。既定案（推奨）は1件が原則で、`data-ask-default` を付ける。既定案を0件にするなら `.ask-no-default-reason` で理由を書け（既定を示さない理由の明示が必須）。選択チップは青（`--accent`）、既定案は緑（`--positive`）で示される。

```html
<div class="ask" data-ask="decision">
  <p class="ask-kind">判断してください</p>
  <p class="ask-question">注釈を今回に含めますか？</p>
  <ul class="ask-options">
    <li data-ask-option data-ask-default><span>含める</span><span class="ask-tradeoff">変更量が増える</span></li>
    <li data-ask-option><span>次フェーズ</span><span class="ask-tradeoff">効果が遅れる</span></li>
  </ul>
</div>
```

`request`。各手順に `data-ask-role`（`user` / `agent` などの意味ロール）と、表示名の `data-ask-role-label` を付ける。ロールは日本語表示名ではなく意味的な値にする。ask-kind チップはモノクロで、警告色にしない。

```html
<div class="ask" data-ask="request">
  <p class="ask-kind">お願いする動作</p>
  <ol class="ask-steps">
    <li data-ask-role="user" data-ask-role-label="あなた">specをレビューする</li>
    <li data-ask-role="agent" data-ask-role-label="Claude">planを執筆する</li>
  </ol>
</div>
```

`hypothesis`。主張には確度バッジ（`certainty` の3値）を `ask-claim` の中に置き、`ask-verify` で検証方法を書く。ask-kind チップはモノクロ。

```html
<div class="ask" data-ask="hypothesis">
  <p class="ask-kind">検証待ちの仮説</p>
  <p class="ask-claim">見出しだけで判断できる <span class="certainty inferred">推論</span></p>
  <p class="ask-verify">検証方法: 見出し列のみで判断内容を言えるか確認する</p>
</div>
```

## 図フォーマット

### flow — 順序・有向遷移・分岐

番号付きの順序や有向の遷移が意味を持つときに使う。昇格済みの canonical flow は**縦の spine**（読み順に上から下）で描かれ、**分岐・スキップは右側のレール**に載る。受理条件は**前向き（reading order 上で必ず下向き）・並行辺禁止・自己ループ禁止・分岐と合流はそれぞれ3以下・同時レール3以下・行予算28以下（ノード＋隣接リンク＋group ラベル行の合計）**である。これを超える構造は受理されない。受理不能なら flow をやめて `matrix` か文章へ縮退せよ（密度目安は flow 12ノード程度、`design-system.md` を参照）。canonical flow の IR での書き方は末尾の組み立て例を見よ。

互換節や単純な直線手順は、次のインライン `flow` を使ってよい。ノードは直接の兄弟にし、CSS の矢印に任せる。

```html
<ol class="flow">
  <li class="flow-node">入力を受け取る</li>
  <li class="flow-node">内容を検証する</li>
  <li class="flow-node">結果を返す</li>
</ol>
```

### layers — アーキテクチャ・層・レーン

レーン名と、そのレーンのノードカードを対にする。レーン順は処理または責務の順にする。

```html
<div class="layers">
  <section class="lane" data-lane>
    <p class="lane-label">利用者</p>
    <div class="lane-nodes"><div class="flow-node">要求</div></div>
  </section>
  <section class="lane" data-lane>
    <p class="lane-label">処理</p>
    <div class="lane-nodes"><div class="flow-node">検証</div></div>
  </section>
</div>
```

### compare — before/after・代替案対比

必ず2つの同等なフレームを並べ、各フレームに見出しを付ける。

```html
<div class="compare">
  <section class="compare-frame"><h3>Before</h3><p>現状の制約</p></section>
  <section class="compare-frame"><h3>After</h3><p>変更後の状態</p></section>
</div>
```

### matrix — トレードオフ・監査・ステータス

比較軸を列見出しにしたセマンティックな表を使う。縦罫線は使わず、横罫線だけで行を区切る。選択案は `option-card` と `data-tone="accent"` を組み合わせ、淡い背景だけで示す。選択案でも文字色、罫線色、枠色は変えない。セル内の記号だけに意味を持たせない。1画面あたり10行程度を目安にし、超えるなら軸を見直すか表を分ける。

```html
<div class="matrix">
  <table>
    <thead><tr><th class="matrix-label" scope="col">案</th><th class="matrix-label" scope="col">利点</th><th class="matrix-label" scope="col">制約</th></tr></thead>
    <tbody><tr class="option-card" data-tone="accent"><th class="matrix-label" scope="row">案A</th><td class="matrix-cell">速い</td><td class="matrix-cell">検証が必要</td></tr></tbody>
  </table>
</div>
```

### timeline — 経緯・ロードマップ

時点と出来事を対にし、時系列の順に置く。

```html
<ol class="timeline">
  <li class="timeline-item"><time datetime="2026-01">2026年1月</time><p>調査開始</p></li>
  <li class="timeline-item"><time datetime="2026-02">2026年2月</time><p>判断予定</p></li>
</ol>
```

### kpi — 効果・指標

値、指標名、必要なら比較基準を近接させる。確定していない値を確定値として表示しない。

```html
<div class="kpi">
  <article class="kpi-card"><span class="kpi-value">42%</span><p>完了率</p></article>
  <article class="kpi-card"><span class="kpi-value">3日</span><p>処理時間</p></article>
</div>
```

### bars — 定量比較

量の比較にだけ使う。横棒の長さは `--value` に百分率で宣言し、座標を計算しない。数値をテキストでも併記する。

```html
<div class="bars">
  <div class="bar-row"><span>案A</span><span class="bar-track"><span class="bar-fill" style="--value: 64%"></span></span><strong>64%</strong></div>
  <div class="bar-row"><span>案B</span><span class="bar-track"><span class="bar-fill" style="--value: 38%"></span></span><strong>38%</strong></div>
</div>
```

### terms — 用語表

新出用語が多いときだけ、本文より前に置く。用語と一言の意味を対にする。

```html
<dl class="terms">
  <div class="term"><dt>ノード</dt><dd>処理または状態を表すカード。</dd></div>
  <div class="term"><dt>レーン</dt><dd>責務ごとに分けた行。</dd></div>
</dl>
```

### クラスとスロットの一覧

各図は次の親子関係を守る。内容だけを各スロットへ入れ、要素の座標や順序を CSS 以外で制御しない。

| 図 | コンテナ | 必須スロット |
| --- | --- | --- |
| flow | `flow` | 直接の子として順序どおりの `flow-node` |
| layers | `layers` | `lane` ごとに `lane-label` と `lane-nodes`、その中に `flow-node` |
| compare | `compare` | 直接の子として2個の `compare-frame` |
| matrix | `matrix` | セマンティックな `table`、`matrix-label` の見出し、`matrix-cell` の内容セル、比較対象は `option-card` |
| timeline | `timeline` | 時系列順の `timeline-item`、各項目の `time` と内容 |
| kpi | `kpi` | `kpi-card` ごとの `kpi-value` と指標名 |
| bars | `bars` | `bar-row` ごとのラベル、`bar-track` 内の `bar-fill`、数値 |
| terms | `terms` | `term` ごとの `dt` と `dd` |

## 広い画面での二層幅

`figure` に包んだ legacy の `flow` / `matrix` は、広い画面で本文カラムの中心軸から左右対称に張り出す（コンポーネント `matrix` も同様。詳細は `design-system.md` の幅の節）。裸の `flow` / `matrix` は本文幅のまま。張り出しを意図するなら `figure` に包め。張り出しコンテナ内では matrix の table は本文カラム幅を上限に伸び、疎な表は張り出し幅までは広がらない。

## コネクタ宣言

分岐または合流が必要な `flow` / `layers` では、図全体を `figure` に入れるか、親要素に `data-connect-scope` を付けて接続スコープを作れ。その**子孫**の `flow` または `layers` に `data-connect` を置き、`始点ID->終点ID` をカンマ区切りで宣言せよ。`data-connect` をスコープ要素自身に置くな。`data-connect-scope` と `data-connect` を同じ要素に置くな。ID はその図の中で解決される。複数の図で同じ ID を再利用してはならない。

```html
<figure class="figure">
  <ol class="flow" data-connect="request->validate, validate->respond">
    <li class="flow-node" id="request">要求</li>
    <li class="flow-node" id="validate">検証</li>
    <li class="flow-node" id="respond">応答</li>
  </ol>
  <figcaption>隣接する処理だけを接続する。</figcaption>
</figure>
```

接続は同じレーン内の隣接ノード、または隣接レーン間だけに限定する。障害物回避や交差の解消はしない。これで表せない複雑なグラフは図を分割する。ノードの位置、接続点、線、矢印を手で描いてはならない。固定のコネクタ処理が辺の中点、曲線、矢印、再描画、視覚的な警告を扱い、`connection-text visually-hidden` の接続テキストも生成するため、これらを手で追加または変更してはならない。

ライブラリで表せない場合だけ自由なインライン SVG を使う。その直前に SVG を使う理由を HTML コメントで残し、座標直書きではなくデザイン規則に従う。同じ需要が繰り返すなら、新しい図フォーマットへの昇格を検討する。

## カノニカルな matrix / flow / enumeration / chevron / pyramid / stairs / logic-tree / waterfall / slope / evidence-map / mixed の組み立て例

昇格済みの `matrix`、`flow`、`enumeration`、`chevron`、`pyramid`、`stairs`、`logic-tree`、`waterfall`、`slope`、`evidence-map` は canonical IR から生成する。IR には HTML/CSS/JavaScript/座標を書かない。`build_explainer.py --assembly <IR> --output <html>` でビルドし、`check.sh <html>` で四層検証する。ほかの形式と弱モデル劣化はラベル付き互換節として同じ組み立てに入る。takeaway 注釈を使うなら `takeawayTargetIds`（1〜3件）/ `emphasis`（全体で最大3件、対象ごとに1件まで、各40字以内）/ `takeawayScope: "whole"` を上記「図のキャプション規約」に従って IR に足す。

### 箇条書き種別 → 図（選択ガイド）

- **並列列挙（順序なし）** → `enumeration`（`parallel-enumeration` / `parallel-itemization`）。番号は識別子であり順序の宣言ではない。
- **線形順序（分岐なし）** → `chevron`（`ordered-sequence` / `linear-sequence`）。順序のテスト: 「並べ替えても意味が変わらない」なら enumeration、「順序が本質」なら chevron。
- **分岐・合流は `directed-graph`（flow）、線形は `ordered-sequence`（chevron）** — `relationship.kind` で送り分ける。capability `branching` の有無は説明上の目印であり、発見機構ではない。
- **構成の分解** → `logic-tree`（`hierarchical-decomposition` / `mece-decomposition`）。**読者がたどる判断分岐は decision-tree（バックログ）** — 誤用は選択ガイドで防ぐ。MECE 性は機械検証できないため caption / certainty で主張する。
- **優先の階層（上ほど重要・少ない）** → `pyramid`（`layered-priority` / `priority-layering`）。**単なる並列3項目は enumeration、優先構造だけ pyramid** — pyramid は誤用しない。
- **到達したら留まる状態（成熟度・移行フェーズ）** → `stairs`（`staged-maturity` / `maturity-staging`）。**流れる工程は chevron**。
- **加算的ブリッジ（開始→増減→終了）** → `waterfall`（`additive-bridge` / `additive-bridging`）。`orientation: "bars"`（行型・既定）は狭い画面向き、`orientation: "columns"`（横並び縦棒）は広い画面向き。**columns は狭い画面では bars を推奨**（レンダラは縮退せず横スクロールで溢れさせる）。
- **2時点比較（同一単位の before/after）** → `slope`（`two-point-change` / `two-point-comparison`）。**3点以上の時系列は timeline か文章へ** — item は最大5件だが各 item は2値のみ。
- **結論と根拠の1段マッピング** → `evidence-map`（`claim-support` / `claim-support-mapping`）。**根拠の根拠は図を分割** — 階層は1段のみ。

### matrix（二軸分類・交差比較）

```json
{
  "schemaVersion": 1,
  "document": {"id": "doc-matrix", "title": "権限モデルの二軸整理", "summary": "役割と操作の交差で許可範囲を判断する。"},
  "sections": [
    {
      "kind": "canonical",
      "ir": {
        "id": "sec-doc-matrix",
        "relationship": {"kind": "two-axis", "capabilities": ["two-axis-classification", "intersection-comparison"]},
        "selection": {"component": "matrix", "version": 1, "matchedCapabilities": ["two-axis-classification", "intersection-comparison"]},
        "caption": "閲覧者は書き込みだけ不可、それ以外は全許可",
        "takeawayTargetIds": ["d-c4"],
        "certainty": [{"id": "d-cert", "level": "confirmed", "statement": "管理者の全操作は仕様で確定。"}],
        "sources": [{"id": "d-src", "label": "権限仕様 v3"}],
        "accessibility": {"label": "許可マトリクス", "summary": "行が役割、列が操作の表。"},
        "matrix": {
          "rows": [{"id": "d-admin", "label": "管理者"}, {"id": "d-viewer", "label": "閲覧者"}],
          "columns": [{"id": "d-read", "label": "読み取り"}, {"id": "d-write", "label": "書き込み"}],
          "cells": [
            {"id": "d-c1", "rowId": "d-admin", "columnId": "d-read", "content": "許可", "certaintyRef": "d-cert", "sourceRef": "d-src"},
            {"id": "d-c2", "rowId": "d-admin", "columnId": "d-write", "content": "許可", "certaintyRef": "d-cert", "sourceRef": "d-src"},
            {"id": "d-c3", "rowId": "d-viewer", "columnId": "d-read", "content": "許可", "certaintyRef": "d-cert", "sourceRef": "d-src"},
            {"id": "d-c4", "rowId": "d-viewer", "columnId": "d-write", "content": "不可", "certaintyRef": "d-cert", "sourceRef": "d-src"}
          ]
        }
      }
    }
  ]
}
```

### flow（順序・有向遷移・分岐）

前向き・fan 3以下・レール3以下・行予算28以下を守る。超える構造は受理されないため、matrix か文章へ縮退する。

```json
{
  "schemaVersion": 1,
  "document": {"id": "doc-flow", "title": "レビュー承認の流れ", "summary": "承認に至る順序と分岐を判断する。"},
  "sections": [
    {
      "kind": "canonical",
      "ir": {
        "id": "sec-doc-flow",
        "relationship": {"kind": "directed-graph", "capabilities": ["ordered-transition", "directed-transition"]},
        "selection": {"component": "flow", "version": 1, "matchedCapabilities": ["ordered-transition", "directed-transition"]},
        "caption": "一次レビューの合意なしに承認へ進めない",
        "takeawayTargetIds": ["f-e2"],
        "certainty": [{"id": "f-cert", "level": "confirmed", "statement": "起案から一次レビューへの遷移は確定。"}],
        "sources": [{"id": "f-src", "label": "レビュー運用手順"}],
        "accessibility": {"label": "承認フロー", "summary": "起案・一次レビュー・承認の順の有向グラフ。"},
        "flow": {
          "nodes": [{"id": "f-draft", "label": "起案"}, {"id": "f-review", "label": "一次レビュー"}, {"id": "f-approve", "label": "承認"}],
          "edges": [
            {"id": "f-e1", "from": "f-draft", "to": "f-review", "relation": "ordered-transition", "label": "提出"},
            {"id": "f-e2", "from": "f-review", "to": "f-approve", "relation": "directed-transition", "label": "合意"}
          ],
          "startId": "f-draft"
        }
      }
    }
  ]
}
```

### enumeration（並列列挙）

2〜6項目（`presentation: "columns"` は2〜4）。`blockContent: "number"` では番号はレンダラが採番し、全 item に `title` が必要。`description` は任意補足で、全 item で省略するか全 item で指定する（歯抜け不可）。list（縦）は説明をコンセプトの右、columns（横）は下に置く。

```json
{
  "schemaVersion": 1,
  "document": {"id": "doc-enum", "title": "並列項目の列挙", "summary": "順序を持たない並列関係を示す。"},
  "sections": [
    {
      "kind": "canonical",
      "ir": {
        "id": "sec-doc-enum",
        "relationship": {"kind": "parallel-enumeration", "capabilities": ["parallel-itemization"]},
        "selection": {"component": "enumeration", "version": 1, "matchedCapabilities": ["parallel-itemization"]},
        "caption": "検討対象の並列項目",
        "certainty": [{"id": "e-cert", "level": "confirmed", "statement": "3項目は同一会議で合意された範囲。"}],
        "sources": [{"id": "e-src", "label": "議事録 2026-06"}],
        "accessibility": {"label": "並列項目の列挙", "summary": "番号付きの縦リストで3項目を並列に示す。"},
        "enumeration": {
          "items": [
            {"id": "e-a", "title": "権限モデル", "description": ["役割ごとの操作範囲を見直す"]},
            {"id": "e-b", "title": "監査ログ", "description": ["必要な保持期間を決める"]},
            {"id": "e-c", "title": "通知チャネル", "description": ["通知経路を統合する"]}
          ],
          "presentation": "list",
          "blockContent": "number"
        }
      }
    }
  ]
}
```

### chevron（線形順序）

2〜6段（`orientation: "horizontal"` は3〜6段）。`blockContent: "number"` では番号をレンダラが採番し、全 step に `title` が必要。`description` は任意補足で全有/全無。縦型は説明をコンセプトの右、横型は下に置く。`loop: true` は縦型のみで `closed-loop` capability と併用し、レールはコンセプト列だけに沿わせる。縦型 `description` は1〜3行・各40字以内、横型は1〜2行・各30字以内。

```json
{
  "schemaVersion": 1,
  "document": {"id": "doc-chevron", "title": "処理フローの4段階", "summary": "縦型チェブロンで線形順序を示す。"},
  "sections": [
    {
      "kind": "canonical",
      "ir": {
        "id": "sec-doc-chevron",
        "relationship": {"kind": "ordered-sequence", "capabilities": ["linear-sequence"]},
        "selection": {"component": "chevron", "version": 1, "matchedCapabilities": ["linear-sequence"]},
        "caption": "受付から報告までの4段",
        "certainty": [{"id": "c-cert", "level": "confirmed", "statement": "4段は運用手順書に準拠。"}],
        "sources": [{"id": "c-src", "label": "運用手順書 v3"}],
        "accessibility": {"label": "処理フローのチェブロン", "summary": "縦型の番号付き4段で線形順序を示す。"},
        "chevron": {
          "steps": [
            {"id": "c-intake", "title": "受付", "description": ["依頼を記録する", "担当を割り当てる"]},
            {"id": "c-verify", "title": "検証", "description": ["入力を確認する", "不足を差し戻す"]},
            {"id": "c-execute", "title": "実行", "description": ["手順に従い処理する", "結果を保存する"]},
            {"id": "c-report", "title": "報告", "description": ["完了を記録する", "関係者へ通知する"]}
          ],
          "orientation": "vertical",
          "blockContent": "number",
          "loop": false
        }
      }
    }
  ]
}
```

横型 number モードも番号＋`title`を図形内に置き、説明は下へ分離する。全 step から`description`を省略した場合は、空の説明欄を生成せずコンセプトだけを表示する。

### pyramid（優先階層）

3〜4層（上から下＝頂点から基盤）。`label` 12字以内、`sub` 30字以内。頂点層のみ強調面。幅は `ve-pyramid-count-{3,4}` と `ve-pyramid-index-{n}` の列挙クラスで割り当てる。

```json
{
  "schemaVersion": 1,
  "document": {"id": "doc-pyramid", "title": "優先度の階層", "summary": "上ほど重要な4層を示す。"},
  "sections": [
    {
      "kind": "canonical",
      "ir": {
        "id": "sec-doc-pyramid",
        "relationship": {"kind": "layered-priority", "capabilities": ["priority-layering"]},
        "selection": {"component": "pyramid", "version": 1, "matchedCapabilities": ["priority-layering"]},
        "caption": "優先度の4層ピラミッド",
        "certainty": [{"id": "p-cert", "level": "confirmed", "statement": "4層は経営会議で合意。"}],
        "sources": [{"id": "p-src", "label": "戦略方針 v2"}],
        "accessibility": {"label": "優先度ピラミッド", "summary": "上から下へ4層の優先度を示す。"},
        "pyramid": {
          "tiers": [
            {"id": "p-apex", "label": "最優先事項"},
            {"id": "p-high", "label": "重要施策", "sub": "四半期で追う重点領域"},
            {"id": "p-mid", "label": "維持管理"},
            {"id": "p-base", "label": "基盤整備"}
          ]
        }
      }
    }
  ]
}
```

### stairs（成熟度階段）

3〜5段（低い段から高い段）。`label` 14字以内、`note` 20字以内。`current: true` は最大1件で `note` 必須。現在地段のみ accent。高さは `ve-stairs-count-{3..5}` と `ve-stairs-index-{n}` の列挙クラスで割り当てる。

```json
{
  "schemaVersion": 1,
  "document": {"id": "doc-stairs", "title": "成熟度の階段", "summary": "5段で成熟度と現在地を示す。"},
  "sections": [
    {
      "kind": "canonical",
      "ir": {
        "id": "sec-doc-stairs",
        "relationship": {"kind": "staged-maturity", "capabilities": ["maturity-staging"]},
        "selection": {"component": "stairs", "version": 1, "matchedCapabilities": ["maturity-staging"]},
        "caption": "成熟度の5段階",
        "certainty": [{"id": "s-cert", "level": "confirmed", "statement": "5段は成熟度モデルに準拠。"}],
        "sources": [{"id": "s-src", "label": "成熟度モデル v1"}],
        "accessibility": {"label": "成熟度階段", "summary": "低い段から高い段へ5段の成熟度を示す。"},
        "stairs": {
          "stages": [
            {"id": "s-1", "label": "未整備"},
            {"id": "s-2", "label": "部分導入"},
            {"id": "s-3", "label": "標準化", "current": true, "note": "ここにいる"},
            {"id": "s-4", "label": "最適化"},
            {"id": "s-5", "label": "自律運用"}
          ]
        }
      }
    }
  ]
}
```

### logic-tree（構成の分解）

2〜4枝。`root.label` 20字以内、`branch.label` 16字以内、`leaf.text` 40字以内。各枝の leaf は0〜2件。深さは root → branch → leaf の2段固定。接続線はレンダラ所有（grid＋境界線、`data-ve-from/to` 禁止）。狭い画面では root 上・枝下の縦積み（DOM 順序は root が先）。

```json
{
  "schemaVersion": 1,
  "document": {"id": "doc-logic-tree", "title": "構成の分解", "summary": "3枝で全体テーマを分解する。"},
  "sections": [
    {
      "kind": "canonical",
      "ir": {
        "id": "sec-doc-logic-tree",
        "relationship": {"kind": "hierarchical-decomposition", "capabilities": ["mece-decomposition"]},
        "selection": {"component": "logic-tree", "version": 1, "matchedCapabilities": ["mece-decomposition"]},
        "caption": "全体テーマの3枝分解",
        "certainty": [{"id": "lt-cert", "level": "inferred", "statement": "分解はレビューで合意（MECE は機械未検証）。"}],
        "sources": [{"id": "lt-src", "label": "分解メモ v1"}],
        "accessibility": {"label": "ロジックツリー", "summary": "左に全体、右に枝と詳細を示す。"},
        "logic-tree": {
          "root": {"id": "lt-root", "label": "全体テーマ"},
          "branches": [
            {"id": "lt-a", "label": "市場機会"},
            {"id": "lt-b", "label": "実装負債", "leaves": [{"id": "lt-b1", "text": "レガシー連携"}]},
            {"id": "lt-c", "label": "運用体制", "leaves": [{"id": "lt-c1", "text": "オンコール"}, {"id": "lt-c2", "text": "権限委譲"}]}
          ]
        }
      }
    }
  ]
}
```

### waterfall（加算的ブリッジ）

`displayPrecision` は必須。数値は `int | Decimal` のみ（`build_explainer.py` は `parse_float=Decimal`）。`valueText` は不透明な表示テキストで、`value`/`delta` との照合はしない。幾何（百分率クラス）は補助的で、値の伝達は `valueText` が主である。

```json
{
  "schemaVersion": 1,
  "document": {"id": "doc-waterfall", "title": "件数ブリッジ", "summary": "開始から増減を経て終了へ。"},
  "sections": [{
    "kind": "canonical",
    "ir": {
      "id": "sec-doc-waterfall",
      "relationship": {"kind": "additive-bridge", "capabilities": ["additive-bridging"]},
      "selection": {"component": "waterfall", "version": 1, "matchedCapabilities": ["additive-bridging"]},
      "caption": "件数の増減ブリッジ",
      "certainty": [{"id": "wf-cert", "level": "confirmed", "statement": "台帳と一致。"}],
      "sources": [{"id": "wf-src", "label": "件数台帳"}],
      "accessibility": {"label": "ウォーターフォール", "summary": "開始値から増減を経て終了値へ。"},
      "waterfall": {
        "displayPrecision": 1,
        "orientation": "bars",
        "start": {"id": "wf-start", "label": "開始", "value": 30, "valueText": "30件"},
        "steps": [
          {"id": "wf-s1", "label": "減少", "delta": -50, "tone": "warning", "valueText": "−50件"},
          {"id": "wf-s2", "label": "回復", "delta": 45, "tone": "positive", "valueText": "+45件"}
        ],
        "end": {"id": "wf-end", "label": "終了", "value": 25, "valueText": "25件"}
      }
    }
  }]
}
```

### slope（2時点比較）

```json
{
  "schemaVersion": 1,
  "document": {"id": "doc-slope", "title": "2時点比較", "summary": "同一単位で開始と終了を比較する。"},
  "sections": [{
    "kind": "canonical",
    "ir": {
      "id": "sec-doc-slope",
      "relationship": {"kind": "two-point-change", "capabilities": ["two-point-comparison"]},
      "selection": {"component": "slope", "version": 1, "matchedCapabilities": ["two-point-comparison"]},
      "caption": "主要指標の推移",
      "certainty": [{"id": "sl-cert", "level": "confirmed", "statement": "台帳値。"}],
      "sources": [{"id": "sl-src", "label": "月次台帳"}],
      "accessibility": {"label": "スロープ", "summary": "2時点の値変化。"},
      "slope": {
        "axes": {"fromLabel": "開始", "toLabel": "終了"},
        "unit": "件",
        "items": [{
          "id": "sl-1", "label": "売上", "fromValue": 10, "toValue": 40,
          "fromValueText": "10件", "toValueText": "40件", "tone": "positive"
        }]
      }
    }
  }]
}
```

### evidence-map（論拠地図）

```json
{
  "schemaVersion": 1,
  "document": {"id": "doc-em", "title": "論拠地図", "summary": "結論と根拠の対応。"},
  "sections": [{
    "kind": "canonical",
    "ir": {
      "id": "sec-doc-em",
      "relationship": {"kind": "claim-support", "capabilities": ["claim-support-mapping"]},
      "selection": {"component": "evidence-map", "version": 1, "matchedCapabilities": ["claim-support-mapping"]},
      "caption": "移行判断の論拠",
      "certainty": [
        {"id": "em-cert", "level": "confirmed", "statement": "監査済み。"},
        {"id": "em-inf", "level": "inferred", "statement": "推定。"}
      ],
      "sources": [{"id": "em-src", "label": "報告書"}],
      "accessibility": {"label": "論拠地図", "summary": "結論1件と根拠2件。"},
      "evidence-map": {
        "conclusion": {"id": "em-conc", "label": "移行を開始すべき"},
        "evidence": [
          {"id": "em-e1", "label": "コスト増加", "certaintyRef": "em-cert", "sourceRef": "em-src"},
          {"id": "em-e2", "label": "期間見積", "certaintyRef": "em-inf"}
        ]
      }
    }
  }]
}
```

### mixed（matrix ＋ 互換 ＋ flow）

canonical セクションと互換節を1つの資料に順序どおり並べる。互換節は `provenance` に `source=legacy-html-insertion` と `reason`（`unmigrated-format` か `weak-model-degradation`）と `format` を持ち、canonical の選択・レジストリ・レンダラをバイパスして同じ組み立てに入る。

```json
{
  "schemaVersion": 1,
  "document": {"id": "doc-mixed", "title": "混在資料", "summary": "canonical と互換を並べる。"},
  "sections": [
    {
      "kind": "canonical",
      "ir": {
        "id": "sec-mx",
        "relationship": {"kind": "two-axis", "capabilities": ["two-axis-classification"]},
        "selection": {"component": "matrix", "version": 1, "matchedCapabilities": ["two-axis-classification"]},
        "caption": "管理者は読み取りを許可される",
        "takeawayScope": "whole",
        "certainty": [{"id": "mx-c", "level": "confirmed", "statement": "確定。"}],
        "sources": [{"id": "mx-s", "label": "権限仕様"}],
        "accessibility": {"label": "許可マトリクス", "summary": "行が役割、列が操作。"},
        "matrix": {
          "rows": [{"id": "mx-r", "label": "管理者"}],
          "columns": [{"id": "mx-col", "label": "読み取り"}],
          "cells": [{"id": "mx-cell", "rowId": "mx-r", "columnId": "mx-col", "content": "許可"}]
        }
      }
    },
    {
      "kind": "compatibility",
      "id": "sec-legacy",
      "markup": "<div class=\"layers\"><div class=\"lane\"><span class=\"lane-label\">入力</span><div class=\"lane-nodes\"><div class=\"flow-node\">受付</div></div></div></div>",
      "provenance": {"source": "legacy-html-insertion", "reason": "unmigrated-format", "format": "layers"}
    },
    {
      "kind": "canonical",
      "ir": {
        "id": "sec-fl",
        "relationship": {"kind": "directed-graph", "capabilities": ["ordered-transition"]},
        "selection": {"component": "flow", "version": 1, "matchedCapabilities": ["ordered-transition"]},
        "caption": "起案は承認へ進む",
        "takeawayScope": "whole",
        "certainty": [{"id": "fl-c", "level": "confirmed", "statement": "確定。"}],
        "sources": [{"id": "fl-s", "label": "運用手順"}],
        "accessibility": {"label": "承認フロー", "summary": "起案・承認の順。"},
        "flow": {
          "nodes": [{"id": "fl-a", "label": "起案"}, {"id": "fl-b", "label": "承認"}],
          "edges": [{"id": "fl-e", "from": "fl-a", "to": "fl-b", "relation": "ordered-transition"}],
          "startId": "fl-a"
        }
      }
    }
  ]
}
```
