# G6 LP的・動的理解パターン

## 要約（5行以内）

- LPから採るべき本質は「派手な入場」ではなく、**同じ図を保ったまま、順序・差分・因果へ注意を誘導する連続性**である。
- 推奨は G3 を **図主役の visual stage** へ拡張し、経路追跡・状態比較・累積変化を1つの typed sequence 系へ閉じる案。
- スクロールは既定の演出ではなく、1図・3〜6状態の意味系列を進める入力としてのみ例外的に許す。通常は明示ステッパーを使う。
- 長文を分割表示する動きは捨てる。静的初期表示・全体表示・同一図の semantic ID 参照を不変条件にする。
- LP単独への置換は理解より体験を強めやすく、現時点では決定論フロアと引き算に対する費用が大きい。

## Pro Max / 調査ログ要約

### 実行した必須検索

1. `scroll storytelling explainer product education --design-system`
   - Pro Max は **Horizontal Scroll Journey / Motion-Driven** を推奨し、常時見える navigation、progressive reveal、`prefers-reduced-motion`、mobile 簡略化を挙げた。
   - ただし horizontal track・parallax・全節 entrance は、判断資料のバックトラック、静的初期表示、弱モデルの決定論フロアと衝突するため、そのままは採らない。
2. `stepper progressive disclosure motion comprehension --domain ux`
   - 高重要度は reduced motion と excessive motion。1 view で動かす対象は1〜2個に限定する指針だった。
   - easing の指針は実装品質には有用だが、理解の成立条件ではないため IR 語彙には入れない。
3. `landing page motion patterns --domain landing`
   - Scroll-Triggered Storytelling は章構造・progress indicator・mobile 簡略化を勧める。
   - 「time-on-page 3x」は Pro Max 内部データのマーケティング指標で、理解の証拠としては扱わない。

### 追加調査からの判断

- Impeccable `animate.md` は、Read モードの motion を state・relationship・continuity の説明へ限定し、generic fade-rise / parallax / section reveal を motion thesis と認めない。scroll-driven motion は **scroll関係自体が意味を運ぶ場合だけ**、かつ default content visible を要求する。
- Narrative Visualization の実証では、animated conditions は engagement を高めたが、stepper と scroller の engagement 差は有意でなかった。つまり「スクロールであること」より、navigation・visual feedback・内容の整合が重要である。[McKenna et al., Visual Narrative Flow](https://narrative-flow.github.io/paper/visual-narrative-flow.pdf)
- 医療 visual story の比較では、click navigation の方が scrolling より直感的と評価され、scrollytelling は過去節への戻りが悪く評価された。判断資料の照合用途では強い反証になる。[Mittenentzwei et al. 2023](https://sbruckner.github.io/assets/pdf/Mittenentzwei-2023-IUB.pdf)
- practitioner 調査は scrollytelling を、注意を保てる一方で、長い線形経路を強制する「double-edged sword」と整理する。[Evaluating narrative visualization](https://pmc.ncbi.nlm.nih.gov/articles/PMC10064970/)
- animation の利点は「変化の具体的特徴そのものを学ぶ」課題で強く、空間配置の理解では静的図が有力である。[Ploetzner et al. 2021](https://link.springer.com/article/10.1007/s11251-021-09541-w)
- 統合された連続静止フレームは animation と同等の理解を示し、状態間の直接比較を助ける場合がある。したがって **動的部品の静的 fallback は劣化ではなく、理解上の対等候補**である。[Boucheix & Lowe](https://www.sciencedirect.com/science/article/abs/pii/S0959475208000340)
- progressive disclosure は二次情報には効くが、頻繁に必要な情報は初期表示すべきで、相互依存する比較を別ステップへ分断すると悪化する。[NN/g Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/)
- `example-proposal.html` は stepper runtime を固定骨格に持つが、実コンテンツでは未使用。図を含む節は少なく、動きを足せる土台があっても「図＝本体」になっていない。現行 stepper は compatibility 起点で、canonical 12 と同等のフロアではない。

## LP要素の分解評価表

評価軸の「寄与」は成功条件 **ほぼ読まずに主張と関係が入る** への寄与。「決定論化」は semantic IR → trusted renderer → checker まで閉じる難易度である。

| LP的要素 | 成功条件への寄与 | 文章依存 | 決定論モジュール化 | AIスロップ化リスク | 判定・成立条件 |
| --- | --- | --- | --- | --- | --- |
| **入場演出**（fade / rise / stagger） | **低〜負** | 原則不変。長文を順番に出すと増える | 低。ただし非表示初期状態を防ぐ契約が必要 | **高** | 既定不採用。関係を運ばず、待ち時間と演出感だけを足す |
| **スクロール物語**（章ごとの scene change） | **中**。状態系列が核心なら高 | 図が scene の本体なら減る。通常の「本文＋背景変化」は増える | **高** | **高** | scroll量と意味状態が1対1、全体像・戻り・mobile fallback がある場合だけ候補 |
| **ステッパー** | **高**（順序・状態・因果）／空間比較には低 | 図中 highlight を進めれば減る。文章 panel を送るだけなら増える | **中**。現行 compatibility はフロア外、typed sequence 化が前提 | 中 | 2〜6段、手動、開始/終了/総数/全体表示、次結果ラベル、静的要約が必須 |
| **ピン留め visual stage** | **高**（同じ図の文脈を保持） | 図の状態差が主役なら減る | **高**。sticky解除、狭幅、印刷、アンカー、reduced motion が難所 | 中〜高 | 「文章が流れ、図が飾り」は不可。1つの図が複数状態の共通座標になるときだけ |
| **ハイライト追跡**（node / edge / cell） | **高** | **減らす**。関係を色・線・近接で直接示せる | **中**。既存 semantic ID 参照と固定 tone に閉じやすい | 低〜中 | 同時強調を絞り、未強調状態でも全体トポロジを見せる。色だけに依存しない |
| **before / after 切替** | **高**（差分が核心） | **減らす**。同位置対応なら説明文を差分へ置換できる | **中**。state pair と対応 ID が必要 | 低〜中 | 同一座標・同一尺度・変化箇所の明示が条件。無操作時は並置または差分一覧を残す |
| **累積ビルドアップ** | **高**（加算・構成・因果鎖） | **減らす**。各段の delta が図中に現れる場合 | 中 | 中 | final form を最初から薄く見せ、変化した対象だけ強調。要素の出現自体を驚きにしない |
| **progress / chapter rail** | **中**（現在地と全体量） | 中立 | **低** | 低 | 内容を説明はしないが迷子を防ぐ。scene 数から自動生成し自由装飾しない |
| **scroll-snap / horizontal journey** | **低〜負** | 中立〜増 | 高 | 高 | 判断資料の戻り・小画面・キーボードと衝突。表現対象自体が水平移動でない限り捨てる |
| **parallax / pulse / glow / autoplay loop** | **負** | 増える | 低〜中 | **最高** | 意味を運ばず注意を奪うため禁止。ブランド感や「動的に見える」は例外理由にならない |

**装飾スクロール入場の例外条件:** 原則なし。唯一の例外は、静的初期表示を保ったまま、資料全体で1回だけ行う authored focal moment が「状態Aから状態Bへの変化」そのものを示し、除去すると関係理解が落ちる場合である。それでも reveal ではなく state transition として扱い、typed state、手動再実行、reduced-motion 時の同値な静的比較を要求する。

## 採用候補パターン（3〜5）

以下は実装案ではなく、将来の決定論部品を評価するための表現契約案である。全候補に共通して、LLM は意味データだけ、形・DOM・色・座標・CSS・JS・timing は信頼側へ閉じる。

### 1. セマンティック経路スポットライト

- **読者体験:** 最初から flow / layers / evidence-map の全体を見渡す。`次へ: 共同承認を確認` のような操作で、現在の node・edge と次の到達先だけが順に強調される。最後は全体表示へ戻る。
- **必要な IR 語彙:** `baseComponentRef`、`sequence`、`stepId`、`label`、`targetSemanticIds`、`relationSemanticIds`、`startId`、`endId`、`overviewTakeaway`。
- **禁止事項:** 自動再生、未到達 step だけに必須事実を置く、自由な path / 座標、pulse、複数経路の同時点滅、散文から順序を推測する。
- **向く題材:** 承認経路、因果鎖、状態遷移、データフロー。G1 の「承認地図」に最も直接効く。

### 2. 同一座標ステートレンズ

- **読者体験:** Before と After を同じ構造・同じ位置で切り替え、変わった node / edge / value だけが残像ではなく明示的な差分として現れる。既定表示では2状態の縮約並置も見える。
- **必要な IR 語彙:** `statePair`、`beforeState`、`afterState`、`correspondence`、`changedIds`、`addedIds`、`removedIds`、`invariantIds`、`stateTakeaways`。
- **禁止事項:** Before/After で配置・尺度を変える、画像スライダーを汎用採用する、差分を文章段落だけで説明する、hover 専用、切替後しか必須情報が見えない状態。
- **向く題材:** 組織変更、責務移管、構成差、現状/提案、同一単位の2時点比較。G1 の「図の形をした文章」を置換できる。

### 3. デルタ累積ビルド

- **読者体験:** 最終形の輪郭を最初から見た上で、各段で追加・減少・分解された差分だけを追う。waterfall なら値、logic-tree なら枝、flow なら通過条件が1段ずつ意味を持つ。
- **必要な IR 語彙:** `baseComponentRef`、`finalStateSummary`、`deltaSteps`、`deltaType`（add / remove / change / activate）、`targetSemanticIds`、`valueBefore`、`valueAfter`、`cumulativeTakeaway`。
- **禁止事項:** 白紙から派手に組み上げる、同時に多数を動かす、最終形を隠す、加算でない関係をビルドアップに偽装する、任意 easing / duration。
- **向く題材:** 加算ブリッジ、原因別増減、構成の形成、段階的リスク増加。

### 4. 固定図スクロール・チャプター（条件付き候補）

- **読者体験:** 1つの visual stage が画面内に留まり、3〜6個の短い chapter marker を進むと、同じ図の semantic state が切り替わる。scroll はページを飾るのでなく、状態系列を前後にスクラブする入力になる。現在地と全体数を常時示す。
- **必要な IR 語彙:** パターン1〜3と同じ `sequence` を再利用し、追加は `navigationMode: scroll-or-step` と `chapterLabel` のみ。scroll threshold、距離、duration は IR に持たせない。
- **禁止事項:** 横スクロール、scroll-jacking、本文カードを大量に流す、section fade-in、parallax、スクロール方向で意味が逆転する不可逆挙動、mobile でも pin を強制する。
- **例外採用条件:** (1) 1図の空間配置を保つことが理解の核心、(2) 3〜6状態が明示済み、(3) desktop scroll と click stepper が同じ状態機械、(4) mobile / keyboard / reduced-motion / print は静的全体表示または stepper、(5) 戻る操作が完全に可逆。この5条件を1つでも満たさなければパターン1〜3へ縮退する。

## G3拡張案 vs 置換案と推奨

| 案 | 骨格 | LPから取り込む利点 | 決定論フロア | 主な弱点 |
| --- | --- | --- | --- | --- |
| **拡張案: Visual-stage deck** | G3 の assertion–evidence / コンサル骨格を維持。ただし動的節は「主張文→図」ではなく **1行takeaway＋大きな図が本体**。typed sequence 1系統が、経路追跡・状態レンズ・デルタ累積の3表現を existing semantic ID 上で動かす | 同じ visual context の保持、progress、reader-paced な焦点移動、cause→result の即時フィードバック | **守りやすい**。canonical component を base にし、sequence は参照だけ。静的初期表示と全体表示を検査できる | ページ全体の LP 的没入感は弱い。現行 compatibility stepper を canonical 化する前提がある |
| **置換案: Single-canvas visual walkthrough** | 長い deck をやめ、資料の主要判断を1枚の persistent visual atlas に統合。3〜6 scene を scroll / step で巡り、末尾にリスクと意思決定だけを独立表示 | LPの連続性・没入・一貫した空間記憶を最大化。文章 section の重複を構造的に削れる | **新規フロアが必要**。複数関係を1図へ統合する atlas IR、scene checker、responsive/static storyboard fallback が要る | 1図への詰め込み、モバイル縮退、部分参照、事実の異種関係を誤って一続きにする危険。弱モデルで品質が急落しやすい |

**推奨: 拡張案 `Visual-stage deck`。**

これは G3 の「条件付きステッパー」を単に言い換える案ではない。動きを例外的な補助から、**図が本体である節の三つの意味操作（trace / compare / accumulate）**へ具体化し、LPの価値である連続性・焦点誘導・進行感を取り込む。一方で page-level scroll choreography は要求しないため、G4 の `LLM = what / trusted library = vocabulary / build = how` を保てる。置換案は北極星候補として価値があるが、まず同一内容で Visual-stage deck と Single-canvas を比較し、「3秒で主張」「関係の再説明」「前状態への復帰時間」で人間評価してから昇格すべきである。

## 捨てるアンチパターン

1. **長文カルーセル:** 400字を4枚の100字へ分け、次へ操作で読ませる。文章依存を隠しただけなので捨てる。
2. **スクロール字幕＋背景図:** 左右どちらかに文章を流し、図は雰囲気だけ変える。text backbone のままで図が証拠にならないため捨てる。
3. **初期非表示 reveal:** 読者がスクロールするまで node、結論、リスクを隠す。無操作不変条件・印刷・JS失敗を壊すため捨てる。
4. **図の連続差し替え:** scene ごとにレイアウトを変え、motion でつながったように見せる。対応関係を毎回再学習させるため捨てる。
5. **文字を一語ずつ強調する kinetic typography:** 視線を拘束するが関係を外在化しない。ほぼ読まず理解の逆なので捨てる。
6. **操作のための操作:** slider、drag、hover、sandbox を「動的だから」追加する。意味状態が有限 enum で表せない探索 UI は捨てる。
7. **全節 fade / stagger / parallax:** 理解を運ばず、AI生成LPの既視感を強める。資料全体の既定から外す。
8. **stepper ごとの専用 player:** flow-player、compare-player、waterfall-player を別実装にしない。時間軸は空間図と直交する typed sequence 1系統に閉じる。

代わりに優先するのは、**図の全体を最初から見せ、同一座標上で semantic target の経路・差分・累積だけを変える**パターンである。動きは散文の pagination ではなく、図が保持する関係を知覚可能にするために使う。

## 仮説の改訂提案

H1 は「文章量を減らさず動きを足しても届かない」から、**「動きが散文の表示順しか変えないなら届かない。だが動きが図そのものの状態・対応・因果を外在化し、その分の散文を削除できるなら、動的理解は成功条件へ直接寄与する」**へ改訂する。H3 は「時間・順序・状態変化が核心なら効く」から、**「読者が学ぶべき対象が変化の具体的特徴であり、同一図の semantic ID に結びついた有限状態として、手動・可逆・全体表示・静的同値 fallback を備えるときに効く。入力は step を既定とし、scroll は同じ状態機械を進める代替入力に限る」**へ改訂する。これによりユーザーの意図を「LP風にしたい」ではなく「動く図で関係をつかみたい」と正しく扱える。

## 結論（このグループ単体）

LPの有効成分は、入口の派手さでも長いスクロールでもなく、**一つの視覚文脈を保ちながら、意味のある変化へ注意を導くこと**である。採るべきは経路スポットライト、同一座標ステートレンズ、デルタ累積ビルドであり、条件を満たす1図だけ固定図スクロール・チャプターを許す。

推奨は G3 の置換ではなく、Visual-stage deck への実質拡張である。図を補助から本体へ昇格し、動きを typed sequence に閉じることで、ユーザーの「動的で視覚的に理解したい」と、弱いモデルでも守れる決定論フロアを同時に満たせる。Single-canvas 置換は将来の比較対象として残すが、現時点で既定にすると1図への詰め込みと runtime 複雑化が、理解上の利点を上回る可能性が高い。
