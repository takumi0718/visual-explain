# G5 UX critique と AIスロップ

対象: `/Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/examples/example-proposal.html`（読取のみ。コード変更・サーバ起動・外部送信なし）
レンズ: impeccable `critique.md`（Assessment A を単一コンテキストで実施 = スキル基準では degraded run）/ `bolder.md` / `distill.md` / `animate.md`、UI UX Pro Max 実クエリ×4、bundled detector 1回。

## 要約（5行以内）

1. 「地味さ」の主因は **(c) 文章過多による視覚リズム欠如** であり、肌の問題（a/b）は二次症状。85%のセクションに図がなく（G1計測）、視覚的ピークが一度も来ない単調な文章の連打が「読む気」を削ぐ。
2. AIスロップ仮説は **部分的に支持**: detector が flat-type-hierarchy（slop カテゴリ）を実検出。ただし Inter/紫グラデ/クリーム紙面という典型スロップ記号は**皆無**で、系譜は「Lovable 系スロップ」ではなく **PowerPoint/Office 既定青のコンサル静的美学**（`--dg-primary: #1F4E79` 等は Office 既定パレットそのもの）。
3. first viewport の最大欠陥は階層の平坦さ: h1=30px は本文の1.5倍のみで、「あなたが決めること」が subtitle と同じ 20px に埋没。最もインタラクティブに見える要素がテーマ切替ボタンという逆転。
4. 図モジュール（d）にも欠陥あり: 図の面がカードと同じ `--surface` グレー、コネクタは 2px の細いグレー線で、図が「本文カラムの中のもう一つのグレー帯」に見える。図=本体にするには図の視覚的重さ自体の引き上げが前提。
5. 「見た目を強くする」は文章を削らずに行うと seductive details 化して悪化する（G3 H1 と一致）。推奨トップ5は G3 北極星（図=本体＋条件付きステッパー）と矛盾しない順序で提示。

## Pro Max / detector 実行ログ要約

実実行したコマンドと要点（説明で済ませず全て実打鍵）:

1. `search.py "decision explainer consulting diagram knowledge document" --design-system -p "visual-explain"`
   - 推奨 STYLE: **Exaggerated Minimalism**（oversized typography, high contrast, negative space, "loud minimal"）。KEY EFFECTS: `font-size: clamp(3rem, 10vw, 12rem)`, `font-weight: 900`, `letter-spacing: -0.05em`, massive whitespace。
   - TYPOGRAPHY 提案: Cormorant Garamond / Crimson Pro（scholarly serif）— knowledge document には serif ペアリングというキャラクター付けの選択肢がある、という対照点。
   - AVOID: "Poor navigation + No search"。
   - 要点引用: 現行例の hero 30px/weight700 は推奨方向（巨大・高コントラストな書字）の**対極**にある。
2. `search.py "animation scroll storytelling comprehension" --domain ux`
   - "Continuous Animation: Infinite animations are distracting. Don't: Use for decorative elements"（Severity Medium）。
   - "Smooth Scroll: anchor links should scroll smoothly"（High）/ "Avoid horizontal scrolling"（High）。
   - 要点引用: 装飾的常時アニメ禁止は G3 の「装飾（glow・pulse・ループ）禁止」と独立に一致。
3. `search.py "ai generated bland minimal landing anti-pattern" --domain style`
   - ヒットは AI-Native UI（`#6366F1` "AI Purple"、typing indicator、pulse）、Zero Interface、Minimal & Direct（`max-width: 680px`, single accent, no box-shadow）。
   - 要点引用: Pro Max の「AI っぽい」記号（AI Purple #6366F1・pulse・chat bubble）は現行例に**存在しない**。現行例は Minimal & Direct 系（単一アクセント・shadow なし・狭カラム）に近いが、それは正当なスタイルカテゴリであってスロップではない。
4. 追加クエリ `search.py "typography scale visual hierarchy contrast heading body" --domain ux`
   - "Heading Clarity: Headings should stand out from body. Don't: Headings similar to body text"（Medium）、"Font Size Scale: Use consistent modular scale"（Medium）、"Contrast Readability"（High）。
5. detector: `node .../impeccable/scripts/detect.mjs --json example-proposal.html` → **成功（exit 0 でなく findings あり=2 相当の出力）**。検出1件:
   - `flat-type-hierarchy`（category: **slop**, severity: warning, line 95）: "Font sizes are too close together — no clear visual hierarchy. Use fewer sizes with more contrast (aim for at least a 1.25 ratio between steps)." 実測 `Sizes: 14.1px, 16px, 17px, 20px (ratio 1.4:1)`。
   - 要点: 決定論的スキャナが本例を「slop」カテゴリで1件だけ旗を立てた。紫グラデ・絵文字アイコン等の他スロップ規則は**不検出**。

## 地味さの要因順位（a–d）

**順位: (c) > (d) > (b) > (a)**（イシュー「主張と関係が図で先に伝わらず、読む気が削がれる」への寄与度順）

1. **(c) 文章過多による視覚リズム欠如 — 主因。**
   - 証拠: G1 計測で 13 セクション中 11（85%）が図ゼロ、図固有テキストは全体の約10%。`section { margin-block: var(--space-7) }`（5.5rem）が全セクション均一で、文章→文章→文章のメトロノーム的リズム。bolder.md の「Give it its own rhythm（スクロールのピークとして密度・ペースの変化を）」の条件を満たす区間が一つもない。distill.md の "Remove redundant copy: say it once" 違反として TOC が見出し文を全文再掲（159字の重複）。
   - 視覚リズムとは「図・余白・太さのピークがスクロール中に配置されること」であり、その素材（図）が 85% の区間で欠如している以上、肌を変えても単調さは残る。
2. **(d) 図モジュール欠陥 — 第2因。**
   - 証拠: 承認地図 figure は `.figure { background: var(--surface); border: 0 }` で、flow-node も `background: var(--surface); border: 1px solid var(--border)`。つまり**図の面とノードがカード・ask・stepper・decision-panel と同一のグレー語彙**で、図だけが持つべき視覚的重さがない。コネクタは `stroke: currentColor; stroke-width: 2`（`--text-dim` 系の細いグレー線）。matrix のハイライトは `--dg-primary-light: #BDD7EE`（薄い Office 青）で、推奨案セルが静かに埋没。G1 指摘の通りこの2図は `unmigrated-format` の互換節で、canonical 語彙にスイムレーン/before-after がない構造的ギャップもある。
3. **(b) コンサル静的美学 — 第3因（乗数であって根因ではない）。**
   - 証拠: `--dg-primary: #1F4E79 / --dg-emphasis: #2E75B6 / --dg-primary-light: #BDD7EE` は PowerPoint/Office 既定テーマの青系そのもの。`--accent: #2456b3` の企業青、白背景 `#ffffff`、単一カラム `--w-narrative: 45rem`、影ゼロ、radius 一律 .4rem。G3 の結論通り形式（コンサル静的デック）自体は認知科学的に支持されるため根因ではないが、この**既定パレットの無編集さ**が「どこかで見た資料」感を増幅している。
4. **(a) AIスロップ — 第4因（部分的、後述の反証が大きい）。**
   - 証拠: detector の flat-type-hierarchy（slop カテゴリ）が唯一の確定的証拠。システムフォントスタック（`-apple-system, "Segoe UI", Roboto, "Hiragino Sans", "Noto Sans JP"`）は Inter ではないが「無署名の既定サンセリフ」として機能的に等価。ただし典型記号（紫グラデ・クリーム・ガラス・絵文字アイコン・ヒーローイラスト）は全て不在で、「AIスロップが主因」とは言えない（詳細は「AIスロップ仮説の証拠と反証」）。

## 画面区間ごとの欠陥

### first viewport（`.first-screen`, min-height 60vh）
- **階層平坦**: h1=30px（本文16pxの1.5倍のみ）、`.decision`=20px、`.subtitle`=20px、`.conditions`=16px dim。「あなたが決めること」（資料の存在理由）が副題と**同サイズ**で埋没。detector の flat-type-hierarchy がまさにこの区間を直撃。Pro Max "Heading Clarity: Don't: Headings similar to body text" 違反。
- **視覚的アンカー皆無**: 主張・決定・前提条件の3ブロック全てがプレーンテキスト（G1 #1-3）。60vh 確保した画面に図・関係線・数値が一つもなく、認知負荷チェックリストの "Visual hierarchy: Is it immediately clear what's most important?" が Fail。
- **逆転した焦点**: 画面上で最もボタンらしい要素が右上のテーマ切替（ユーティリティ）。判断行よりユーティリティが目立つ。Nielsen #6（Recognition rather than recall）低: 認識できる視覚的手がかりがなく、全て「読んで想起」させる。
- **コピーの二重化**: `.decision` 行と `.subtitle` 行がほぼ同文（「未確認の契約例外を含む料金改定を…限定対象で」が2連続）。distill.md "say it once" 違反。

### スクロール中盤（toc → narrative×5 → 図×2）
- **メトロノーム・リズム**: h2（20px）→ claim（20px bold）→ evidence（16px dim）の反復が5連続し、セクション間マージンも均一 5.5rem。bolder.md の skeleton test（コピーを剥がしても構造だけで意味が伝わるか）に Fail — コピーを消すと全セクションが同じグレーの帯になる。
- **TOC の重複再掲**: 目次が h2 全文を複製（159字）。同じ文を2回読ませるだけで構造の俯瞰（図的サマリー）を提供しない。Nielsen #1（現在地の表示）も TOC にアクティブ状態がなく弱い。
- **図の没個性化**: 承認地図が登場しても、面・ノード・コネクタ全てが周囲のカードと同じグレー/細線で「ピーク」にならない。evidence 文「文章だけでは…追いにくいため、この見本では関係を図にしています」は読者の理解に寄与しない自己言及（G1 #8）で、extraneous load（認知負荷チェックリスト "Minimal choices" 以前の純粋なノイズ）。
- **Before/After は図の皮を被った文章**: `.compare` 2カラムだが中身は完結文×4、関係線・差分強調なし（G1 #10）。ワーキングメモリ規則上、読者は Before 文を保持したまま After 文を読む「Memory Bridge」を強いられる。

### ask 付近（hypothesis → decision → closing → decision-panel）
- **決定がピークになっていない**: `.ask` は他カードと同一の `--surface` + radius .5rem。資料全体のクライマックス（判断してください）が視覚的に中盤のカードと同重さ。peak-end rule の「peak」が不在。impeccable critique の emotional journey 観点で最大の欠陥。
- **既定案の強調が弱い**: `data-ask-default` は `color-mix(in srgb, var(--positive) 12%, var(--surface))` の薄緑のみ。選択肢2件（≤4 で認知負荷は適正）だが、推奨の視覚的確信度が低い。
- **重複の再々掲**: decision-panel が ask の質問文を3度目に再掲（first-screen → ask → panel）。distill.md の redundancy 除去対象。
- **終端の印象**: closing はプレーン箇条書き、フッタは「AI が生成した資料」の小字。peak-end rule の「end」が事務的に閉じる。Nielsen #1 は stepper 不在のため進行感なし（ただし判断資料では必須ではない）。

## AIスロップ仮説の証拠と反証

### 支持する証拠（コード根拠）
1. **flat-type-hierarchy（決定論的検出、category=slop）**: `--fs-hero: 1.875rem / --fs-h2: 1.25rem / --fs-body: 1rem / --fs-figure: .875rem / --fs-small: .8125rem`。実測比 1.4:1 でステップ間 1.25 倍未満。「少ないサイズ数で強いコントラスト」の原則に反し、5サイズが近接して存在。
2. **無署名タイポグラフィ**: システムフォントスタックのみ。Inter ではないが「何も選ばなかった」点でスロップの機能的等価物。Pro Max が knowledge document に serif ペアリング（Cormorant/Crimson）を提案しうるのと対照的。
3. **一律のカード語彙**: flow-node / compare-frame / kpi-card / term / ask / stepper / decision-panel が全て `background: var(--surface)` + `border-radius: .4–.5rem` + ボーダーほぼなし。「グレーの面の反復」は AI 生成 LP のカード過多と同じ視覚結果を生む（ただし枚数は少ない）。
4. **意味色の希釈**: `[data-tone]` が全て `color-mix(... 12%, var(--surface))` の薄 tint。色が意味を運ぶ設計だが、彩度が低すぎて符号として機能しにくい。
5. **動きゼロ**: transition/animation は reduced-motion リセット以外に存在しない（ボタン hover ですら transition なし）。「安全で地味なデフォルト」の極致。

### 反証（スロップ断定を弱める証拠）
1. **典型スロップ記号の全欠如**: 紫グラデーション（AI Purple #6366F1）・クリーム紙面・ガラスモーフィズム・絵文字アイコン・ヒーロー装飾・box-shadow・過大 radius が**一つもない**。detector も slop 規則で1件しか立てていない。
2. **系譜は PowerPoint であり Lovable ではない**: `--dg-*` パレット（#1F4E79/#2E75B6/#BDD7EE/#F2F2F2/#7F7F7F）は Office 既定テーマの色。これは「AI が無難に生成した美」ではなく「コンサル納品物の既定美」の写し。
3. **クラフトの床が高い**: ダークモード 3 経路（OS 追従/明示 light/明示 dark）、`prefers-reduced-motion`、`:focus-visible` 3px アウトライン、aria 属性群、certainty バッジの実線/破線/点線による意味符号化、CSP による自己完結。スロップは通常この床を持たない。
4. **フッタの自己言及**: 「AI が生成した資料」と明示している点はメタ的には正直だが、印象として「AIっぽさ」を強化する要因ではある（逆説的な支持証拠でもある）。

**判定**: 「AIスロップが原因の一つ」は **weak support**。確かに flat な書字階層・無署名フォント・均質カードというスロップ的平坦さは存在するが、それは AI 生成の手癖というより「コンサル既定 + 型で守られた最小主義」の帰結であり、ユーザー仮説の「安全で地味なデフォルト美」の中身は (b) の Office 系既定美学に大部分が帰属する。スロップ対策（色・フォント・装飾の変更）だけではイシューは解決しない。

## 見た目強化が文章依存を悪化させるリスク

G3 の H1（文章量を減らさないまま動き・装飾を足しても成功条件に届かない）と seductive details / coherence principle の証拠に基づき、以下の「強化」は**悪化**させる:

1. **スクロール連動リビール・パララックスの追加**: 文章量そのままに演出を足すと、読むコストに演出の注意コストが加算される（coherence principle 違反）。Pro Max も "Continuous Animation … Don't: Use for decorative elements"。animate.md の "A generic fade-and-rise, hover lift, parallax layer, or scroll reveal is not a thesis" に該当。
2. **first-screen への装飾的ヒーロー画像/イラスト**: 主張と無関係な視覚物は seductive details の原型。60vh の空白を「絵」で埋めると、図=本体化の余地を恒久的に潰す。
3. **図への色彩・グラデ強化**: 現行の `data-tone` は色=意味の符号系。装飾色を足すと符号の S/N が落ち、コネクタの意味（関係）が色の洪水に溺れる。
4. **タイポの巨大化だけ（bolder の誤用）**: bolder.md の skeleton test 通り、コピーを剥がして構造が語らないなら「boldness is in the text size, not the design」。h1 を 60px にしても文章の壁が大きくなるだけで、二重化・TOC 再掲・図不在は解消しない。
5. **カードへの影・ガラス・ボーダー追加**: 均質カードを豪華にすると「グレーの帯」が「飾られた帯」になるだけで、図と文章の主従は変わらない。distill.md の "Remove decorations that don't serve hierarchy" に逆反。
6. **自動再生・ループする図のアニメーション**: G3 の動き判定木（自動再生禁止）と Pro Max の双方に違反。判断資料のバックトラックを阻害する。

共通構造: **「見た目の強化」が文章量・二重化・図の主従に触れない限り、全て extraneous load の増加になる。**

## 推奨優先順位トップ5（指針のみ）

G3 推奨（図=本体＋条件付きステッパー、単一モード）と矛盾しない順序。実装はしない。

1. **主従逆転を先に: first-screen と narrative の図本体化（肌に触れない）。** first-screen に承認地図の縮約版（4レーン7ノードの骨格）を置き、`.decision`/`.subtitle` の二重化と TOC 全文再掲を削る（distill: say it once）。narrative claim が図の主張を先取りする二重化（G1 #6→#7, #9→#10）を「図が先、文は最小キャプション」に転換する。これは見た目変更ではなく情報配置の変更で、seductive details リスクがゼロ。
2. **図モジュールの視覚的重さを引き上げ、図>カード>文章の階層を作る。** 図の面を `--surface` から区別（例: border-strong の輪郭か背景の反転）、コネクタを太く/アクセント色に、matrix の推奨セルハイライトを 12% tint より強い符号に。図が「もう一つのグレー帯」でなくなって初めて、図=本体が視覚的に成立する。
3. **書字階層の再設計（detector 直撃箇所、機械検査可能）。** ステップ間 ≥1.25 倍を契約化（例: hero 2.5–3rem / h2 1.5rem / body 1rem に再配分し、fs-small/figure は現状維持）。Pro Max "Heading Clarity"・detector の 1.25 比ルールにそのまま対応し、テストでフロアを守れる。フォント変更（serif 化等）は後回しでよい——階層のコントラストが先。
4. **ask/decision をスクロールのピークとして一段だけ「bolder」に。** bolder.md の「システムが既に持つ語彙をフル強度で」に従い、新規プリミティブを足さず、border-strong・accent・余白の非対称（セクションマージンの変化）で decision カードだけを頂点にする。peak-end rule の peak をここに固定し、decision-panel への質問文3度目の再掲は削る。
5. **条件付きステッパーを承認地図にのみ適用（G3 の時間展開パターン1「段階ハイライト」）。** 全体を常時表示したまま、読者ペースで経路を1段ずつ点灯。自動再生・スクロール連動・装飾ループは禁止（Pro Max / animate.md / G3 動き判定木と整合）。それ以外の区間には動きを入れない。

## 結論（このグループ単体）

- イシュー（図で先に伝わらず読む気が削がれる）の主因は **(c) 文章過多による視覚リズム欠如** であり、**(d) 図モジュールの没個性化** がそれを補強している。肌の要因 (b)(a) は二次症状であり、(a) AIスロップは flat-type-hierarchy（detector 実検出）と無署名フォント・均質カードの点で部分的に支持されるが、典型記号の欠如と `--dg-*` の Office 系出自から、主たる系譜は「AI スロップ」ではなく「コンサル既定美学の無編集採用」と判定する。
- したがって対処の順序は「文章を削り図を本体化 → 図の視覚的重さ → 書字階層 → ask のピーク化 → 限定ステッパー」であり、装飾・色彩・動きの追加を先行させると seductive details 化して悪化する。これは G1（文章依存の計測）・G3（北極星 D）と矛盾しない。
- 本グループ単体の留保: ブラウザでの実描画確認は行っていない（サーバ起動禁止のため）。コネクタ描画・二層幅の張り出し（60rem 以上）の実視覚は静的読み取りによる推定であり、描画確認は別グループのブラウザ検証に委ねる。また impeccable critique 本来の dual-agent 手順には従えていない（本 run は単一コンテキストの調査タスクのため degraded 相当）。
