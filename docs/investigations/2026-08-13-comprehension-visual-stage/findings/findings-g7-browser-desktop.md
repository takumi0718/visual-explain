# G7 Desktop 実描画

## 要約（5行以内）

- 1440×900 の実描画では h1 は明確に主役であり、「h1 が埋没」は反証。ただし最上部の大きな空白にテーマ切替だけが置かれ、初動の注意を奪う点は支持する。
- first-screen 後はリンク目次と文章ブロックが続き、図に到達するまで視覚的な変調がないため、文章連打の仮説は支持する。
- 承認地図はカードと背景色が完全に同一だが、実際には巨大な面と黒い矢印で視覚ピークになる。「図が埋没」は部分支持に弱める。
- 紫グラデーション等の AI スロップ記号は見えない。flat hierarchy は本文周辺には残るが、desktop のタイトル階層全体には当てはまらない。
- 要因順位は **(c) > (d) > (b) > (a) を維持**するが、(d) の問題は「ピーク不足」より「1画面で一望不能・図内の面差不足」へ修正する。

## 撮影一覧

すべて Chromium、viewport 1440×900、devicePixelRatio 1、light theme の実描画。HTTP サーバは使用せず、指定 `file://` を Playwright セッション `g7desk` で表示した。

| 画像 | scrollY | 対象 |
|---|---:|---|
| [desktop-first-viewport.png](./desktop-first-viewport.png) | 0 | first viewport |
| [desktop-narrative.png](./desktop-narrative.png) | 850 | 目次と first-screen 後の narrative |
| [desktop-approval-map-top.png](./desktop-approval-map-top.png) | 1760 | 承認地図の上〜中段 |
| [desktop-approval-map-bottom.png](./desktop-approval-map-bottom.png) | 2320 | 承認地図の中〜下段と説明文 |
| [desktop-matrix.png](./desktop-matrix.png) | 3970 | 選択肢 matrix |
| [desktop-ask.png](./desktop-ask.png) | 4700 | 仮説カードと判断 ask |
| [desktop-closing.png](./desktop-closing.png) | 5520 | closing と decision panel 導入 |
| [desktop-decision-panel.png](./desktop-decision-panel.png) | 5841（最大付近） | decision panel と footer |

## first viewport 所見

対象: [desktop-first-viewport.png](./desktop-first-viewport.png)

- **h1 は埋没していない。** 太い黒文字、2行、34.5px で中央寄りの大面積を占め、本文 18.4px に対して約1.88倍。画面内の内容領域では最も強い要素である。
- 一方、ページ最上部には約250pxの白い余白があり、その中で右上のテーマ切替（約393×51px、薄灰の面）だけが独立している。ページに入った瞬間の視線はテーマ切替へ行きやすいが、h1 と同時に見れば h1 の方が強い。したがって G5 の「テーマ切替が目立つ」は支持、「そのため h1 が埋没」は反証。
- `.decision` は `.subtitle` と同じ要素（`class="subtitle decision"`）で23px/400。先頭の青太字「あなたが決めること」は視認できるが、続く別の `.subtitle` も23px/400で、判断・説明間の書字階層は平坦である。
- first-screen は見出し、判断文、説明文、条件箇条書きのすべてが文章。色や太さの差はあるものの、関係を先読みできる図的アンカーはない。
- h1→判断文は実測約59.9px、判断文→次の説明文は約36.8px離れ、窮屈ではない。問題は余白不足でなく、余白の中に置かれる情報形式がすべて文章である点。

## スクロール区間所見

### narrative

対象: [desktop-narrative.png](./desktop-narrative.png)

- 1〜5の目次リンクの直後に、太字の主張、太字の補足、薄い根拠文が反復する。同じ左端・同じ幅・同程度の文字サイズで続き、実描画でも「読む順序」は分かるが「見ただけの意味」は得にくい。
- 小さな「未確認」「推論」バッジと左罫線は変化を作るものの、視覚ピークと呼べるほどではない。図に到達するまでの文章連打という G5 仮説を支持する。
- 画面内で次セクションの主張まで見えるためスクロールは進むが、構造が変わらず、内容を読まない場合は各節の差が消える。

### 承認地図 figure

対象: [desktop-approval-map-top.png](./desktop-approval-map-top.png)、[desktop-approval-map-bottom.png](./desktop-approval-map-bottom.png)

- 実描画では幅828px・高さ約1212pxの大きな薄灰面が現れ、黒い2pxの矢印が縦方向に収束する。これはページ中で明確な視覚ピークであり、「ピークが一度もない」は反証する。
- ただし高さがviewport 900pxを超えるため、最上段の根拠と最下段の公開・保護を同時に見られない。経路全体の理解にはスクロール中の記憶保持が必要で、「ほぼ読まず一望」には届かない。
- figure 面と各 flow node はともに `rgb(244, 245, 247)`。ノードは1pxの薄い枠だけで面から分離されるため、図内の階層は弱い。一方、矢印は G5 の「細いグレー」ではなく、実測 `rgb(26, 29, 33)` の黒・2pxで十分に見える。
- ノード文言を読めば合流構造は追えるが、レーンや矢印自体に意味ラベルがなく、文字を飛ばすと「複数入力が共同承認へ集約し、公開と監視へ分岐する」以上の意味は得にくい。
- 下端直後の「文章だけでは…この見本では関係を図にしています」は図の内容を進めず、視覚ピーク後に再び説明文へ戻る。

### matrix

対象: [desktop-matrix.png](./desktop-matrix.png)

- 3案×利点/トレードオフの比較は1画面内に収まり、列と行の対応も崩れていない。承認地図より一望性は高い。
- ただし実質は文章表であり、各セルを読まないと案の差が分からない。提案行も全セル `background-color: transparent` で、先頭ラベルの太字以外に推奨案を即時識別する面色はない。
- 表の下に注記が続き、さらに次の仮説カードが見えるため、比較結果より文章密度の印象が残る。

### ask

対象: [desktop-ask.png](./desktop-ask.png)

- 仮説カードと判断カードはいずれも同じ薄灰面・同じ角丸で、別種の内容だが同じ視覚語彙に見える。
- 判断カード内では「判断してください」の青いラベルと、既定案の薄緑面が明確で、選択肢は2件に絞られている。ページ中では比較的スキャンしやすい区間である。
- それでも質問、運用条件、全顧客案のリスク、メモ欄まで文章が連続し、ask を理解するには読み込みが必要。判断のクライマックスとしての強さは「全くない」ではなく「カード群の中では強いが、専用ピークにはなっていない」。

### closing / decision panel

対象: [desktop-closing.png](./desktop-closing.png)、[desktop-decision-panel.png](./desktop-decision-panel.png)

- closing は細い枠線内の2見出し＋箇条書きで、リスクと不確実性を読みやすく整理しているが、再び文章だけの構造になる。
- 直後の decision panel は薄灰の大カードで、先の ask と同じ質問を文中に再掲する。回答回収より「もう一つの説明カード」に見え、終端の焦点が分散する。
- footer の「AI が生成した資料」は小さく控えめ。紫・グラデーション・ガラス・過大な角丸・装飾イラストなどの典型的 AI スロップ記号は、全スクリーンショットで確認できない。

## 実測スタイル（computed）

環境値: viewport `1440×900`、DPR `1`、root/body font-size `18.4px`、document `1440×6723px`（横 overflow なし）。

| 対象 | font-size / weight / line-height | background | 主要余白・寸法 |
|---|---|---|---|
| `h1` | `34.5px / 700 / 50.025px` | `transparent` | margin `23.115px 0`、padding `0`、`828×100.03px` |
| `.subtitle` 1件目（同時に `.decision`） | `23px / 400 / 40.25px` | `transparent` | margin/padding `0`、`828×80.5px` |
| `.subtitle` 2件目 | `23px / 400 / 40.25px` | `transparent` | margin/padding `0`、`828×80.5px` |
| `.decision` | `23px / 400 / 40.25px` | `transparent` | `.subtitle` 1件目と同一DOM要素 |
| `.first-screen` | `18.4px / 400 / 32.2px` | `transparent` | margin `101.2px 0`、padding `73.6px 0`、gap `36.8px`、`828×638.42px` |
| 承認地図 `figure.figure` | `18.4px / 400 / 32.2px` | `rgb(244, 245, 247)` | margin `27.6px 0`、padding `27.6px`、radius `9.2px`、`828×1211.83px` |
| matrix `figure` | `18.4px / 400 / 32.2px` | `transparent` | margin `27.6px 0`、padding `0`、`828×534.02px` |

### 図 vs カードの背景色

| 要素 | computed background-color |
|---|---|
| 承認地図 `figure.figure` | `rgb(244, 245, 247)` = `#f4f5f7` |
| `.flow-node` 全7件 | `rgb(244, 245, 247)` |
| `.compare-frame` 全2件 | `rgb(244, 245, 247)` |
| `.ask` 全2件 | `rgb(244, 245, 247)` |
| `.decision-panel` | `rgb(244, 245, 247)` |
| matrix `figure` | `transparent` |

**判定:** G5 の「承認地図とカードの背景色が同一」は実測で支持。さらに承認地図の外面と内部ノードまで完全に同色である。ただし実視覚では図の大きさと黒いコネクタがカードとの差を作るため、「同色なので図全体が埋没」までは支持しない。

補足実測:

- 承認地図のコネクタ: `stroke: rgb(26, 29, 33)`、`stroke-width: 2px`、fillなし。
- flow node: font-size `16.1px`、padding `9.2px 18.4px`、border `1px solid rgb(226, 229, 233)`。
- theme button: font-size `18.4px`、background `rgb(244, 245, 247)`、padding `9.2px 18.4px`、約`393.19×50.58px`。
- ask 既定案だけは薄緑面 `color(srgb 0.856157 0.895843 0.885333)`。matrix の提案行には対応する背景強調がない。

## G5仮説の更新

| G5仮説 | 実描画判定 | 更新内容 |
|---|---|---|
| 1. first viewport の階層が平坦（h1 が埋没、テーマ切替が目立つ） | **部分支持 / h1埋没は反証** | h1 は34.5px・700で明確な主役。テーマ切替は上部余白で先に目に入る。平坦さは h1 ではなく、23px/400で揃う判断文と説明文の間にある。 |
| 2. 文章連打で視覚ピークがない | **前半は支持、全体は反証** | narrative までは文章の反復。承認地図は巨大面＋黒矢印で明確なピーク。ただし登場が遅く、1画面に収まらない。 |
| 3. 図がカードと同じグレー帯で埋没 | **色は支持、埋没は部分支持** | 背景色は完全同一。ノードも図面と同色で内部階層は弱いが、図そのものはサイズとコネクタで目立つ。matrix の方が文章表として平坦。 |
| 4. AI典型記号はないが flat hierarchy はある | **前半支持、後半を限定** | AI典型記号は見当たらない。flat hierarchy は secondary text/カード語彙にはあるが、desktop の h1→本文階層には当てはまらない。 |

### 要因順位

**更新後も `(c) > (d) > (b) > (a)` を維持。**

1. **(c) 文章過多による視覚リズム欠如** — first-screen、narrative、matrix、closing の大半で、読むことが理解の前提になっているため首位を維持。
2. **(d) 図モジュール欠陥** — 「図が視覚ピークにならない」という強い主張は撤回する。一方、承認地図が1画面に収まらない、図面とノードが同色、matrix の推奨行が無着色という、ほぼ読まず理解するうえで直接的な欠点が残るため2位を維持。
3. **(b) コンサル静的美学** — 白地、企業青、細線、薄灰カードという印象は実描画でも強い。ただし可読性は高く、理解阻害への直接寄与は (d) より小さい。
4. **(a) AIスロップ** — footer の自己申告以外に典型記号はなく、desktop では h1 の階層も成立。最下位を維持し、支持はさらに弱める。

## 結論（このグループ単体）

Desktop 上の最大障害は、**最初の判断から選択肢までの因果が1画面の視覚構造に統合されず、読者が複数画面の文章と図ラベルを読み継がないと全体像を復元できないこと**である。

実描画により、G5 の主因順位は維持する一方、「h1 が埋没」「視覚ピークが一度もない」「コネクタがグレーで弱い」はそれぞれ反証または弱められた。承認地図は確かにピークだが、1212pxの縦長構造と同色面のため一望性が低く、成功条件「ほぼ読まず理解」にはなお届かない。コード変更・依存追加・HTTPサーバ起動・外部送信は行っておらず、`g7desk` ブラウザセッションは撮影後に close 済み。
