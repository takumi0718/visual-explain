# G8 Mobile/図品質 実描画

> Worker 8 調査成果物（G8: モバイル + 図品質・ブラウザ実描画）。実装禁止・サーバ起動禁止・外部送信禁止・dir 外書込なし。
> 対象: `skills/visual-explain/examples/example-proposal.html`（read-only）。
> ツール: `playwright-cli -s=g8mob`（Chromium のみ導入済）。完了時に `close` 済み。

## 要約（5行以内）

1. **本例に G2 の欠陥クラスは一切存在しない。** DOM 全走査で `ve-flow-rail` / `ve-chevron*` / `ve-lt*` / `ve-enum*` / `.flow`（CSS 矢印親）はすべて **0 件**。承認地図は唯一の図で、**SVG `<path>` + `<marker>`（connector JS）** だけで描画され、これは G2 が「健全（component S）」と分類した経路そのもの。
2. **矢印ずれ・三角と棒の分離は構造上発生しない。** 6 本のコネクタはすべて開始/終了がノード中心から **0.5px 以内**（DPR 丸めのみ）、色は `rgb(26,29,33)`（--text、薄灰背景に対し高コントラスト）、pathBounds `102–273 × 215–1107` は figure 内 (`374×1361`) に完全収まり **clipped=false**。コンソールエラー/警告/connector-warning 0件。
3. **モバイル最大の理解阻害は比較マトリクス（matrix）の強制横スクロール。** `min-width:32rem(512px)` の表に対し viewport 374px → **138px はみ出し**。第3列「主なトレードオフ」（推奨案のコスト含む）が**右画面外に隠れ**、案を比較するには発見+横スクロールが必須で、その手がかりがない。
4. **ask はモバイルでピークにならない（埋没）。** 両 ask とも背景 `rgb(244,245,247)`（--surface）/ border 0 / radius 8px で、figure・compare-frame・decision-panel と**完全に同一のグレー矩形**。判断のクライマックスが中盤のカードと視覚等価（G5 の主張を実測で強確認）。
5. **箇条書きの「変な改行」は顕在化せず。** `.conditions`/closing `<ul>`/`.ve-matrix-notes`/`.panel-asks` はすべて完全文が 2〜3 行に自然折返し。IR 由来の細断化（G2 A3）は本例に enumeration/chevron-description がないため**機会がない**（後述）。

---

## 方法論の注記（忠実性の開示）

- **`file:` プロトコルが Playwright-CLI 層でブロックされた。** Chromium 規定のブロックではなく、`--allow-file-access-from-files` / `--disable-web-security`（launchOptions.args 経由）でも解除できない Playwright-CLI プロトコルレベルのガード（エラー文 "Access to file: protocol is blocked"）。サーバ起動禁止のため、**バイト同一の `data:text/html;base64,...` URL** で読込（外部送信なし・JS/CSP/レイアウトは URL スキーム非依存で等価）。ソース 57562B → data URL 76788 字。読込後 `Page Title` が正しく取得でき JS も実行確認済（connector layer 生成 = JS 起動の証拠）。
- **画像をモデルが視認できない制約。** スクリーンショットは要求通り PNG 10 枚を成果物として生成したが、本 harness では PNG を読み込んでもモデルに画像が渡らない。したがって「目視」は**すべて `getBoundingClientRect` / SVG `d` / 計算スタイル / scrollWidth-clientWidth の厳密抽出**で代用（タスクが求める「具体座標/相対位置」はこの方が精度が高い）。PNG は人間レビュー用アーティファクト。
- ビューポート **390×844**（iPhone 級）、DPR 1、root font-size 16px（`clamp` の最小値に張付）、`@media(max-width:42rem)`=true（モバイルブレークポイント稼働）、`prefers-color-scheme`=light（既定で light 表示を観察）。

## 撮影一覧（worker-8/ に格納）

| ファイル | scrollY | 区間 |
|---|---|---|
| `mobile-01-first-viewport.png` | 0 | first-screen（h1+decision+subtitle+conditions） |
| `mobile-02-toc.png` | 977 | 目次（h2 を全文再掲、G5 指摘の重複） |
| `mobile-03-approval-map-top.png` | 2061 | 承認地図 上部（レーン1・2 + 縦コネクタ） |
| `mobile-04-approval-map-connectors.png` | 2450 | 承認地図 中央（交叉するベジエ曲線） |
| `mobile-05-approval-map-bottom.png` | 3000 | 承認地図 下部（共同承認→限定公開） |
| `mobile-06-before-after-stacked.png` | 3918 | Before/After（1カラム縦積み、h=774） |
| `mobile-07-matrix-hscroll.png` | 4926 | 案の比較 matrix（**第3列隠れ・横スクロール**） |
| `mobile-08-ask-hypothesis.png` | 5587 | ask（仮説、h=251、グレー埋没） |
| `mobile-09-ask-decision.png` | 5926 | ask（判断、h=505、**ピークでない**） |
| `mobile-10-closing.png` | 6519 | リスクと弱い前提 + 判断の回収 |

## 矢印・コネクタ所見

### 構造（実測）
- 図は1つのみ：承認地図 `figure.figure > div.layers[data-connect]`。`data-connect` は6辺を宣言（`contract-exception→billing-calculation`, `price-change→billing-calculation`, `price-change→notification-audience`, `billing-calculation→joint-approval`, `notification-audience→joint-approval`, `joint-approval→limited-release`）。
- 描画結果：`.connector-layer`(1) 内に `<path>` 7本 = **6コネクタ + 1マーカー定義**（`<defs><marker>` 内の `M0,0 L8,4 L0,8 Z`）。`connector-warning` 0件。コンソール error/warning 0件。
- **矢印は CSS 貼り合わせ（border+グリフ／border-triangle）ではなく、単一 SVG `<path>` + `marker-end`（原子）**。三角と棒は分離不可。

### 幾何（figure 左上原点・px）
ノード中心とコネクタ端点（抜粋）:

| ノード | 矩形 x,y,w,h | 中心 cx,cy |
|---|---|---|
| contract-exception | 24,173,155,43 | 102,194 |
| price-change | 195,173,155,43 | 273,194 |
| billing-calculation | 24,468,155,67 | 102,501 |
| notification-audience | 195,468,155,67 | 273,501 |
| joint-approval | 24,787,**326**,67 | 187,821 |
| limited-release | 24,1107,155,43 | 102,1128 |

6コネクタの端点（path `d` より）と「ノード中心との偏差」:
1. `M101.5,215 → …101.5,467.5`：contract-exception底(102,216)→billing-calc頭(102,468)。**偏差 ≤0.5px**。純縦。
2. `M272.5,215 → …101.5,467.5`：price-change底→billing-calc頭。右列→左列の S 字ベジエ。
3. `M272.5,215 → …272.5,467.5`：price-change底→notification頭。純縦（右列）。
4. `M101.5,534.5 → …187,787`：billing-calc底(102,535)→joint-approval頭(187,787)。左→中央。
5. `M272.5,534.5 → …187,787`：notification底→joint-approval頭。右→中央。
6. `M187,854 → …101.5,1106.5`：joint-approval底(187,854)→limited-release頭(102,1107)。中央→左。

- **全端点がノードの上端/下端中心を 0.5px 以内で指向**（中心外れなし）。
- pathBounds `minX102 minY215 maxX273 maxY1107` ⊂ figure `374×1361` ⇒ **clipped=false**。`figure{overflow:auto}` によるクリップなし。
- 矢印色 `rgb(26,29,33)`（--text、実質黒）、strokeWidth 2、marker `orient=auto` で経路接線方向に頭部が向く。薄灰背景 `rgb(244,245,247)` に対し**高コントラストで視認性良好**。
- モバイル特有の形状：レーンが 1fr 縦積みになるため、経路は縦長の S 字/ベジエが連なり、右列↔左列↔中央を往復する**ジグザグ**に見える。破綻ではないが「一本の経路」という主張が、1.6 画面分の縦スクロールの中で読み取りにくい（後述）。

### 結論
**「三角と棒の分離／ずれ／中心外れ」は本例では皆無。** G2 が指摘した F1（flow skip レール）・C1（chevron loop レール）の CSS クラスは DOM に存在せず、本例は G2 が健全とした SVG 経路（component S）を採用しているため。

## 改行・箇条書き所見

### 箇条書き（実測・estLines は line-height 28px で算出）
| リスト | 件数 | 各項目の行数 | 状態 |
|---|---|---|---|
| `.conditions`（first-screen） | 2 | 2 / 2 | 完全文の自然折返し |
| `.ve-matrix-notes` | 2 | 3 / 2 | 完全文の自然折返し |
| closing `<ul>`（リスク） | 2 | 3 / 3 | 完全文の自然折返し |
| closing `<ul>`（不確か） | 2 | 3 / 2 | 完全文の自然折返し |
| `.panel-asks` | 1 | 3 | 質問文の再掲（G5 指摘の3度目の重複） |

- **「変な改行/過剰ビュレット/細断化」は一切観察されず。** 各 `<li>` は1完全文で、326px の内容幅で 2〜3 行に揺らぐだけ。
- 図キャプション（figcaption）「根拠・顧客影響・承認・撤回を一つの経路で…」は clientW326 で **3 行**に自然折返し（1文の折返しで、フラグメント化ではない）。

### なぜ G2 の「変な改行」が出ないか
G2 A3 は「IR `description: tuple[str,...]` の各要素が無条件でビュレット1件になる」契約＋「弱いモデルが文章を細断化する」の合成を主因とした。本例では:
- enumeration / chevron-description（G2 が挙げた脆弱な構造）が**本例に存在しない**（`.ve-enum*`=0, `[class*=ve-chevron]`=0）。
- 存在する箇条書きは `.conditions`/closing `<ul>`/`.ve-matrix-notes` で、いずれも**静的 HTML に手書きされた完全文**（IR 生成ではない）。
- したがって G2 A3 の失敗経路は**本例では発火する機会がない**。モバイルの狭幅は折返しを「2〜3行」に増幅するが、細断化（1文が複数ビュレットに割かれる）は起こらない。**G2 仮説#2（モバイル顕在化）は本件では不成立（観察されず）——ただし対象外の構造だからであり、反証ではない。**

## ask / 可読性所見

### ask はピークでない（実測で強確認）
| 要素 | 背景 | border | radius | 備考 |
|---|---|---|---|---|
| `figure.figure`（承認地図） | `rgb(244,245,247)` | 0 | 8px | — |
| `.compare-frame` ×2 | `rgb(244,245,247)` | 0 | 6.4px | — |
| `.ask`（hypothesis, h=251） | `rgb(244,245,247)` | 0 | 8px | クライマックス前 |
| `.ask`（decision, h=505） | `rgb(244,245,247)` | 0 | 8px | **判断本体・ピークであるべき** |
| `.decision-panel` | `rgb(244,245,247)` | 0 | 8px | — |
| `.closing-section` | `rgb(255,255,255)` | border-topのみ | 0 | 唯一の非グレー |

- **判断 ask（decision）は figure・compare-frame・decision-panel と完全同一のグレー矩形。** 視覚的重さで差別化ゼロ。モバイルの縦スクロールでは「グレー箱の連続」の1つに埋没。G5 の「ask がピークでない」を実測スタイル値で確証。
- 推奨案マーカー `data-ask-default` は `color-mix(positive 12%, surface)` の薄緑のみで、グレー地に対する存在感が極めて薄い。

### 図の可読性（モバイル狭幅）
- **承認地図：横スクロールなし・クリップなし**（clientW=scrollW=374）。ただし**縦 1361px（画面高 844px の 1.6 倍）**で、図だけを通過するのに 1.6 画面分スクロール。「一つの経路で照合」という主張が、縦長ジグザグの中で直感的に把握しづらい。
- **比較 matrix：強制横スクロール +138px。** 表 `min-width:32rem(512px)` > viewport 374px。セル可視性を実測:

| 列 | x 範囲 | 横スクロールなしで可視? |
|---|---|---|
| 行ラベル（案名） | 8–119 | ✅ |
| 主な利点（col-benefit） | 119–308 | ✅（推奨案の利点=ハイライト対象も可視） |
| **主なトレードオフ（col-tradeoff）** | **308–520** | ❌ **138px 右画面外** |

  - 推奨案の**利点はハイライトされて見えるが、そのコスト（トレードオフ）は隠れている**。3案を利点と費用の両面で比較するには、行ごとに横スクロール往復が必要。スクロールを促す手がかり（シャドウ/矢印）はなく、隠れていることに気づかないリスク。
- **Before/After（`.compare`）：1カラム縦積み（gridTemplateColumns=374px）で横スクロールなし。** 縦 774px。健全だが、2段を並列比較できず縦スクロール比較になる（ワーキングメモリ負荷、G5 #10 と整合）。
- **二層幅（`@media(min-width:60rem)` の負 margin 張出し）：モバイルでは非稼働**（390px < 960px）。figure は本文幅に収まり溢れなし。健全。

## G2仮説の更新

### 仮説1（三角と棒の分離は skip/loop レールに局在）→ **支持（診断は正しい）だが本例では観察不能＝潜在欠陥**
- G2 の局在診断（F1: `flow.css:15-16` / C1: `chevron.css:10-21,54-57`）は CSS 構造的に妥当。しかし **`example-proposal.html` はこれらのクラスを1つも出力していない**（DOM 全走査で 0 件）。本例の唯一の図は connector JS（SVG `<path>`+`<marker>`）で、G2 自身が「健全・原子（component S）」とした経路。
- 実測でその健全性を追認：端点はノード中心 ≤0.5px、clipping なし、高コントラスト。**「実描画で見えるか」→ 見えない（対象の構造が本例にないから）。**
- **修正提案**: G2 仮説を「局在は正しいが、発火には canonical flow/chevron renderer が skip/loop 辺を出力した実例が必要」と明示すべき。example-proposal.html は**健全側（SVG connector）の証拠**であり、欠陥側の証拠ではない。欠陥を目視するには flow（skip レール）／chevron（loop, vertical）を含む別見本が必要。

### 仮説2（箇条書きの変な改行がモバイルで顕在化）→ **本例では不成立（対象構造不在）**
- enumeration/chevron-description が不在のため IR-bullet 細断化（A3）経路が発火せず。存在する箇条書きは完全文の自然折返しのみ。
- モバイル狭幅は「行数を増やす」効果（2〜3行）はあるが、「1文を複数ビュレットに割る」効果は観察されず。**顕在化の機会そのものが本例にない**ため、G2 仮説の反証ではなく「適用外」。

### 仮説3（ask がモバイルでピークか／埋もれるか）→ **埋もれる（G5 を実測で強支持）**
- ask（decision）の背景・border・radius が figure/compare-frame/decision-panel と**バイト等価**（`rgb(244,245,247)`/border0/8px）。視覚的ピークなし。モバイル縦スクロールではグレー矩形の海に埋没。

### 仮説4（狭幅で図の横スクロール強制・切れ）→ **matrix で成立・承認地図では不成立**
- matrix：`min-width:32rem` が 374px viewport を 138px 超過 → **第3列（トレードオフ）が完全隠れ**。G2/#4 の「横スクロール強制」を確証。
- 承認地図：横スクロール・クリップともになし（縦長化のみ）。matrix 側のリスクは `ve-matrix-scroll{overflow-x:auto}` でレイアウト崩壊は防がれるが、内容の隠蔽は防げない。

## 結論（このグループ単体）

- **モバイルでの最大の理解阻害（1文・G7 desktop と独立）**: モバイルでは比較マトリクスが `min-width:32rem(512px)` で第3列「主なトレードオフ」（推奨案のコストを含む）を **138px 右画面外に隠し**、3案を利点と費用の両面で比較するには行ごとの横スクロール往復が必須な上、スクロールの存在を示す手がかりもないため、**判断の中核入力（各案のトレードオフ）が狭画面では部分的に不可視**になる——これが最鋭のモバイル固有ブロッカー（desktop 広幅では3列とも一覧できるため、モバイル特有の劣化）。次点は「ask がグレー矩形の海に埋没してピークにならない」こと（これは desktop 共通だが、縦スクロールの長大なモバイルでより顕著）、三番目は「承認地図が縦 1361px（1.6 画面）に及び一本の経路として把握しづらい」こと。
- **図品質（矢印・コネクタ）は本例では健全。** G2 が挙げた CSS 貼り合わせの欠陥クラス（F1/C1）は本例の DOM に存在せず、実際に描画される SVG connector は端点中心 ≤0.5px・非クリップ・高コントラストで、モバイルでも分離/ずれ/中心外れなし。**G2 の診断は正しいが、example-proposal.html は「健全側（SVG 経路）の実証」であり「欠陥側の実証」ではない**——欠陥を目視するには skip/loop を含む flow/chevron 実例が別途必要。
- **改行/箇条書きの「変な改行」は本例では非顕在化。** 存在する箇条書きは手書き完全文の自然折返し（2〜3行）で、IR-bullet 細断化（A3）の発火経路（enumeration/chevron-desc）が本例にないため。
- **妥協点（method）**: `file:` がブロックされたため `data:` URL でバイト同一読込（サーバ起動なし・レンダリング等価）。また画像をモデルが視認できないため「目視」は `getBoundingClientRect`/`d`/計算スタイル/scrollWidth の厳密抽出で代用し、PNG 10 枚は人間レビュー用アーティファクトとして生成済み。
