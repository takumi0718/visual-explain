# G1 文章依存の解剖

対象: `/Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/examples/example-proposal.html`
（併せて同ディレクトリの `example-proposal.assembly.json`、`SKILL.md`、`references/patterns.md`、`references/component-vocabulary.json` を参照）

## 要約（5行以内）

1. コンテンツ13セクション中、図（`compatibility`/`canonical`）を含むのは2セクションのみ（15%）。first-screen・ask×2・closing・decision-panel・narrative×5は**すべて図ゼロ**で、成功条件（ほぼ読まず理解）の要である冒頭の主張・決定・条件も含め文章に100%依存する。
2. 「主張を支える最小単位」14個のうち、図だけ／図+短ラベルで足りるのは2〜3個のみで、残り10個超は本文段落が必須（表は末尾に添付）。
3. 図（layers/matrix）自体の文字数は約209字、対して段落・見出し・キャプション・注記の合計は約1,600字超（全体約2,052字の約8割）。図は分量的にも脇役。
4. H2寄りの決定的証拠: assembly.json でこの「canonical 見本」自身が承認地図図・Before/After比較の2箇所を `kind:"compatibility"`・`reason:"unmigrated-format"` として**未移行の文章寄り互換節**のまま出荷しており、しかも直前の`narrative`claimが図の主張を先取りして二重化している。テンプレの運用（narrative優先・migration未完了）が本体化の一因という仮説を支持する具体証拠。
5. ただし反証もある: `patterns.md`は「図が短文より明確になる理由がないなら図を使わない」と明記し、また`component-vocabulary.json`にはスイムレーン/before-after専用の canonical component が存在しない。文章依存の一部は思想的に許容された選択、一部は語彙のギャップであり、単純な「運用のさぼり」と断定はできない。

## 計測

### セクション構成（読み順、13セクション + 目次）

| # | kind | id/instance | 見出し | 本文段落 p | 箇条書き li | 図 figure | 表 table |
|---|------|-------------|--------|-----------|-------------|-----------|----------|
| 1 | first-screen | sec-first-screen | h1×1 | 2 | 2 | 0 | 0 |
| 2 | toc | (nav) | – | 0 | 5 | 0 | 0 |
| 3 | narrative | sec-current-problem | h2×1 | 3 | 0 | 0 | 0 |
| 4 | narrative | sec-approval-map-intro | h2×1 | 1 | 0 | 0 | 0 |
| 5 | compatibility(layers) | sec-approval-map | – | 0 | 0 | 1 | 0 |
| 6 | narrative | sec-approval-map-evidence | – | 1 | 0 | 0 | 0 |
| 7 | narrative | sec-before-after-intro | h2×1 | 1 | 0 | 0 | 0 |
| 8 | compatibility(compare) | sec-before-after-compare | h3×2 | 4 | 0 | 0 | 0 |
| 9 | narrative | sec-alternatives-intro | h2×1 | 0 | 0 | 0 | 0 |
| 10 | canonical(matrix) | sec-alternatives | – | 1 | 2 | 1 | 1 |
| 11 | ask(hypothesis) | sec-ask-hypothesis | – | 3 | 0 | 0 | 0 |
| 12 | ask(decision) | sec-ask-decision | – | 2 | 2 | 0 | 0 |
| 13 | closing | sec-closing | h2×2 | 0 | 4 | 0 | 0 |
| 14 | decision-panel | example-proposal | h2×1 | 1 | 1 | 0 | 0 |

図（figure）を含むのは #5・#10 の2セクションのみ。全13コンテンツセクション中 **2/13 = 約15%**。first-screen・toc・narrative×5・ask×2・closing・decision-panel の**11セクション（85%）は図が皆無**。

### 文字数（全角文字ベース、空白除去後カウント）

セクション別合計（本文含む全テキスト、certainty バッジ語含む）:

| セクション | 文字数 |
|---|---|
| first-screen | 181 |
| toc（目次リンク文＝見出しの再掲） | 159 |
| narrative: current-problem | 195 |
| narrative: approval-map-intro | 77 |
| compatibility: approval-map（layers図） | 316 |
| narrative: approval-map-evidence | 56 |
| narrative: before-after-intro | 66 |
| compatibility: before-after-compare | 157 |
| narrative: alternatives-intro | 35 |
| canonical: alternatives（matrix図） | 330 |
| ask: hypothesis | 103 |
| ask: decision | 121 |
| closing | 155 |
| decision-panel | 101 |
| **合計** | **2,052** |

用途別の内訳（重複クラスで再集計、certainty語等の微小差はあり）:

| 分類 | 文字数 | 備考 |
|---|---|---|
| 見出し文（h1+h2、TOCの再掲は除く） | 205 | h1=36, h2合計=169。すべて述語を持つ完結文＝読む前提 |
| TOC（見出し文の重複再掲） | 159 | 見出しと実質同一内容を2回読ませる |
| claim/evidence/subtitle/conditions等の本文段落 | 882 | narrative・first-screen・ask・closingの地の文 |
| Before/After比較の地の文（compare-frame内 p×4） | （上に含む、131） | 図的レイアウトだが中身は完全にプレーン文章 |
| 図固有テキスト（flow-node・lane-label・matrix cell/header） | 209 | 図がなければ消える純粋な図データ |
| 図キャプション（figcaption・matrix caption/summary） | 105 | 「持ち帰る1文」規約により文章化必須 |
| 図付随の注記（matrix notes: 推論・出典） | 113 | 図の外側にぶら下がる文章 |

図固有テキスト209字は全体2,052字の**約10%**。キャプション・注記（218字）を図側に含めても約16%。残り8割超は「文章を読まないと分からない」情報。

### first-screen / ask / closing の図依存度

- **first-screen**: h1（主張）・decision（あなたが決めること）・subtitle（シナリオ）・conditions（2条件）まですべてプレーン段落/リスト。図・アイコン・関係線は皆無。資料全体で最も読まれる可能性が高い画面が100%文章依存。
- **ask（hypothesis / decision）**: 2セクションとも図なし。decisionのoption+tradeoffは短文2件のペアで多少表的だが、視覚的な差別化（色分け以上の構造化、アイコン等）はなく実質は箇条書き。
- **closing**: 完全にプレーン箇条書き（4項目）。図・強調表現なし。

## 主張単位ごとの情報源判定表

「主張を支える最小単位」を出現順に列挙し、理解に必要な情報源を判定した（(a)図だけ／(b)図+短いラベル／(c)本文段落必須）。

| # | 単位 | 内容（要約） | 判定 | 根拠 |
|---|------|--------------|------|------|
| 1 | h1（資料全体の主張） | 承認地図で照合し限定対象で段階公開する | (c) | 図・アイコンなし、36字の完結文のみ |
| 2 | decision行 | 何を決めるか | (c) | プレーン文 |
| 3 | conditions（2件） | 前提条件 | (c) | 箇条書きのみ、視覚的対応物なし |
| 4 | TOC（5リンク） | 各セクション見出しの再掲 | (c) | 見出し文をもう一度読ませる。図的サマリー無し |
| 5 | current-problem claim | 別々確認だと検証できない | (c) | 図なし。次の図はまだ登場しない |
| 6 | approval-map-intro claim | 承認者が根拠と顧客影響を共同承認で照合 | (c)→(b)の先取り | この claim 自体は図なしだが、直後の図とほぼ同内容を先に文章で言ってしまっている（二重化。詳細は次項） |
| 7 | 承認地図の図（layers, #5〜7の後） | 4レーン7ノードの関係 | **(b)** | lane-label＋flow-nodeの短文＋figcaptionで関係はほぼ伝わる。ただし#6のclaimが同じ主張を先に文章で述べているため実質は(c)相当の読書量になっている |
| 8 | approval-map-evidence | 「文章では追いにくいので図にした」というメタ説明 | (c) | 読者の理解に直接寄与しない自己言及文。図にもならない純粋な運用コメント |
| 9 | before-after-intro claim | 比較対象は見た目でなく関係 | (c) | 図なし |
| 10 | Before/After比較（4文） | 部門別確認 vs 共同承認地図 | (c) | 2カラムのCSSレイアウトだが中身は4つの完結文。関係線・アイコン・矢印は一切なし＝**「図の形をした文章」** |
| 11 | alternatives-intro | 限定対象の段階公開だけが機会を残す | (c) | 見出しのみ、claim文なし（唯一 claim を持たない narrative） |
| 12 | 案の比較（matrix図） | 3案×2軸の比較表 | **(b)** | セル14〜25字の短文＋figcaptionの1文takeawayで、表だけでほぼ完結。notes（推論・出典）は補足であり主要理解には必須でない |
| 13 | ask-hypothesis | 承認地図の方が不整合を早く見つけられる（推論）＋検証方法 | (c) | 図なし、2文の地の文 |
| 14 | ask-decision（質問+2選択肢） | 限定対象で開始するか | (b)寄り | 選択肢+トレードオフの短い対構造だが、視覚的には単なるリスト。表化すれば(a)に近づける余地あり |
| 15 | closing（リスク2件・不確か2件） | 撤回条件・未検証事項 | (c) | 図なし |
| 16 | decision-panel | 判断の回収 | (c) | 図なし |

**集計**: (a) 0/16、(b) 2〜3/16（約15〜19%）、(c) 13〜14/16（約80%超）。
図が実際に主役として機能しているのは「承認地図（layers）」と「案の比較（matrix）」の2箇所のみで、しかもその前後を narrative の claim/evidence が挟み込み、同じ主張を文章でも述べている（#6→#7、#9→#10 の構造）。

## H1/H2 への証拠と反証

### H1（地味さ・静的さは二次症状で、文章量そのものが問題）を支持する証拠
- 全体2,052字のうち図固有データはわずか約10%（209字）。動きやアニメーションを足しても、残り9割の文章量は変わらない。
- first-screen・ask・closingという「最も読まれるべき/意思決定に直結する」3セクション種別が**すべて図ゼロ**。ここに動的演出を加えても「ほぼ読まず理解」には届かない。文章そのものを図に変換する必要がある。
- 図がある2箇所でも、直前のnarrative claimが図の主張を先に文章で言ってしまう二重化構造（#6→#7、#9→#10）があり、「動きの有無」以前に「同じ情報を2回、しかも先に文章で提示する」設計になっている。

### H2（コンサル形式ではなく、運用/テンプレが文章本体になっているズレ）を支持する証拠
1. **assembly.jsonのprovenanceが動かぬ証拠**: `sec-approval-map`と`sec-before-after-compare`はどちらも`"reason": "unmigrated-format"`。SKILL.mdは互換節を「弱モデル劣化または未移行時のみ」と規定しており、この“canonical見本”自身が「未移行」状態のまま公開されている。つまり運用（マイグレーション未完了のまま出荷）が文章依存を固定化している。
2. **canonical component は同じ文書内の別箇所で機能している**: `sec-alternatives`は`canonical`の`matrix`を使い、実際に(b)判定（図+短ラベルで足りる）を達成できている。同じ文書内に「図が主役になれる実例」と「文章に頼ったまま出荷された実例」が併存しており、失敗はフォーマット選択の運用/優先順位の問題であって、コンサル形式や図解そのものの限界ではない。
3. **narrative claim と 図キャプションの二重化**: `sec-approval-map-intro`のclaim「承認者は、根拠と顧客影響を共同承認で照合し、限定対象で公開します」と、直後の図の`figcaption`「根拠・顧客影響・承認・撤回を一つの経路でたどれるため、部門をまたぐ不整合に気づける。」は主旨が重複している。テンプレ運用が「先に文章で主張→次に図で追認」という順序をデフォルトにしており、「図＝本体、文章＝最小キャプション」になっていない。
4. **Before/Afterが「図の皮を被った文章」**: `.compare`は2カラムのCSSレイアウト（視覚的には比較図に見える）だが、中身は接続線もアイコンも構造化フィールドもない4つの完結文。データとして`kind:"compatibility"`かつ`format:"compare"`＝legacy専用フォーマットであり、そもそも12種のcanonical componentに「before/after」に相当するものがない（後述の反証も参照）。テンプレのセクション種別語彙が「narrativeで書けてしまう」経路を用意していることが、文章化の温床になっている。
5. **TOCが見出し文をそのまま複製**: 目次の5リンクは各`h2`のテキストをそのまま流用しており、読者は同じ主張文を目次と本文見出しで2回読む。これはコンサル資料の目次慣行そのものではなく、実装（`build_explainer`のTOC生成方法）に起因する重複。

### H2への反証・留保
1. **patterns.mdの明文規約**: 「図・表・短文のうち最短で明確に伝わる1つを主にし、図が短文より明確になる理由がないなら図を使わない」。つまりテンプレは短文を積極的に許容しており、「文章＝補助」という設計ではなく「短ければ文章でよい」という設計思想。個々の`claim`（1行想定）が短文である限り、契約違反ではない。問題があるとすれば「1行のはずのclaimが実際には図と重複している」ことであり、「文章を使うこと自体」ではない。
2. **canonical語彙のギャップ**: `component-vocabulary.json`の12種に、承認地図のような**多レーン（スイムレーン）構造**や**before/after定性比較**に直接対応する`relationshipKind`が存在しない（`flow`は`directed-graph`で分岐はあるがレーン概念なし、`matrix`は二軸分類、`slope`は定量二点比較）。したがって`sec-approval-map`と`sec-before-after-compare`が`compatibility`に落ちたのは、単純な「運用のサボり」ではなく、**canonical側の表現力不足**という語彙のギャップに起因する可能性がある。これはH2を「テンプレ運用の問題」から一部「コンポーネント語彙設計の問題」へと再配置する材料であり、次調査（他グループ）で検証すべき。
3. **Pi/Katsura Qwen固有の保守的縮退**: patterns.mdは弱モデル向けに「因果・順序が不確かなら flow ではなく matrix・terms・または文章を使う」と明記しており、モデルの確信度に応じて文章に縮退することを**仕様として許容**している。今回のexampleが実際にこの縮退経路を通ったか（弱モデル生成か）は`provenance.reason`だけでは判別できず（`unmigrated-format`であって`weak-model-degradation`ではない）、追加調査が必要。

## 盲点・追加で調べるべき点

- 他のcanonical component（flow/enumeration/chevron等）を使った別exampleが repo 内にあれば、そちらでは同種の「claimと図キャプションの二重化」が起きていないか比較すべき（本example固有の問題か、テンプレ全体の傾向か切り分けが必要）。
- `scripts/check.sh`の検査ルール（特に検査群③）が、narrative claimと図の主張重複を検出できる仕組みを持つか未確認。持たないなら、今回発見した二重化は機械的に防げていないことになり、H2の「運用のズレ」をさらに補強する。
- `sources.md`・`design-system.md`に「1画面あたりの許容文字数」「読了時間の目標値」等、定量的な文章量上限の規約があるか未確認（今回は`patterns.md`の定性規約のみ確認）。数値規約が存在しない場合、そもそも「文章量超過」を機械検査で止められない構造的欠陥がある可能性。
- 本exampleが「proposal / strict profile」であることの影響（`extended`profileや`system`/`research`typeでは narrative/canonical比率が変わるか）は未検証。他typeのexampleが repo にあれば同様の計測をすべき。
- 目次（TOC）の重複再掲が`build_explainer.py`の仕様なのか、このexample特有の書き方なのかはスクリプトを読んでいないため未確認。

## 結論（このグループ単体）

`example-proposal.html`は、13コンテンツセクション中11（85%）が図を持たず、文字量でも図固有データは全体の約1割にとどまる。「主張を支える最小単位」16個のうち図だけ／図+短ラベルで足りるのは2〜3個（15〜19%）にすぎず、資料の理解は依然として本文段落に依存している（H1を支持）。加えて、この“canonical見本”自身が承認地図とBefore/After比較の2箇所を「未移行の互換節」のまま出荷し、しかも図の直前にほぼ同内容のnarrative claimを置く二重化構造を持つことから、単なる「コンサル形式の限界」ではなく「narrative優先・migration未完了という運用/テンプレのズレ」が文章本体化の具体的原因の一つであることが、このexample単体から確認できる（H2を支持）。ただし、patterns.mdの「短文でよい」規約とcanonical component語彙のスイムレーン/before-after非対応という構造的ギャップも同時に存在するため、H2を「運用の怠慢」と単純化せず、「テンプレ運用のズレ」と「canonical語彙の表現力不足」の両方を原因候補として扱うべきである。
