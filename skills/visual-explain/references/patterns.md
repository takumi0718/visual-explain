# 構成と図フォーマットの契約

この資料では、固定骨格の `CONTENT:BEGIN` と `CONTENT:END` の間だけを編集する。図はここにある HTML 契約どおりに埋め、座標、独自 CSS、独自 JavaScript を追加しない。各セクションは **1つの問い**だけに答え、目安を**主張1行・根拠2〜3行**にする。図・表・短文のうち最短で明確に伝わる1つを主にし、図が短文より明確になる理由がないなら図を使わない。根拠は主張または図の近傍に置く。核心、制約、反証を折りたたみに隠してはならない。

## 資料型の構成テンプレート

### 提案承認型

1. 第一画面は `first-screen` を使い、提案または推奨を1文、**あなたが決めること**を1文、判断を左右する条件を最大2件だけ置く。同じ判断文を末尾に重複させない。第三者が第一画面を3秒見て「何の話か」「何を判断するか」を答えられる状態にする。
2. 新出用語が多いときだけ、先に用語表を置く。
3. 現状と問題を図で示す。
4. 提案は before/after を等しい大きさで並べる。
5. 検討した代替案とトレードオフを比較表にする。単一案を決め打ちしない。
6. 末尾に「リスクと弱い前提」と「不確かな点」を必ず置く。

### 仕組み理解型

1. TL;DR で仕組みを一言で示す。
2. 新出用語が多いときだけ、先に用語表を置く。
3. 全体地図で zoom-out の構造を示す。
4. 主要フローでデータまたは処理の流れを示す。動きが核心ならステッパーを使う。
5. 判断に不要な検証過程と補足だけを `deep-dive` に入れる。
6. 末尾に「限界・確度」を置き、推論で補った箇所を明示する。

### 調査報告型

1. 結論または推奨を最初に示す。
2. 主要な発見は、1発見につき1ブロックにし、近傍に出典リンクを置く。
3. 定量データが必要なときだけ可視化する。
4. 末尾に「限界・反証・確度」を置く。

## 共通の文法ブロック

必要な部品だけを使う。全セクションに全部を置く必要はない。

```html
<section>
  <p class="claim">この節で答える主張を1行で書く。</p>
  <figure class="figure">
    <!-- この節の図または表 -->
    <figcaption>図だけでは伝わらない最小限の補足。</figcaption>
  </figure>
  <p class="evidence">根拠を2〜3行で、主張の近くに書く。</p>
  <details class="deep-dive"><summary>補足の検証過程</summary><pre>必要な詳細</pre></details>
</section>
```

## 図フォーマット

### flow — 直線パイプライン・手順

番号付きの順序が意味を持つときに使う。ノードは直接の兄弟にし、CSS の矢印に任せる。

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

比較軸を列見出しにしたセマンティックな表を使う。セル内の記号だけに意味を持たせない。

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
