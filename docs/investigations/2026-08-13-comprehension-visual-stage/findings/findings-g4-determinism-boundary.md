# G4 決定論モジュールの境界

## 要約（5行以内）
- 境界は「LLM は意味だけ、信頼部品は表現語彙だけ、ビルドは描画と挙動のすべて」とする。
- canonical 12 の品質フロアは、閉じた IR、明示選択、allowlist renderer、hash 付き資産、固定 skeleton、最終 DOM 検査の連鎖で成立している。
- 色・形・座標・CSS・JS・モーション時間を LLM に返すと、この連鎖を迂回してフロアが崩れる。
- 動きは時間・順序・状態変化が核心のときだけ、typed step sequence 1系統へ閉じる。スクロール入場演出は既定で持たない。
- 現行 stepper は実行ロジックこそ固定だが互換 HTML 経路なので、canonical と同等の弱モデル向け保証にはまだ含めない。

## 現行品質フロア地図

| 境界 | 現在の保証 | 証拠 | 残る限界 |
|---|---|---|---|
| **skeleton 固定域** | skeleton はテーマ、トークン、レスポンシブ、フォーカス、`prefers-reduced-motion`、固定 connector/stepper/decision JS、CSP を所有する。TITLE と3つの controlled slot 以外は skeleton と完全一致を要求する。 | `assets/skeleton.html`; `scripts/ve_components/checker.py:138`; `scripts/ve_components/flatten.py:78` | CSP は自己完結のため inline style/script を許す。安全性の本体は CSP 単独ではなく、固定域照合と資産 hash である。skeleton 自体の変更は人間レビューとテスト品質に依存する。 |
| **assembly / component IR** | `additionalProperties: false` の型付き JSON。canonical IR は HTML/CSS/JS/DOM/SVG/座標系フィールドを持てず、関係、capability、選択、caption、確度、出典、アクセシビリティ、意味データだけを受ける。first-screen は先頭、closing は末尾。 | `references/assembly.schema.json`; `references/component-ir.schema.json`; `scripts/ve_components/validation.py:121,336,343,368` | 内部整合性は検査できても、LLM が宣言した因果・順序・数値が原資料に対して真かは検査できない。narrative の文章量や「3秒理解」はハード保証されない。 |
| **registry / 選択** | 12形式の ID・version・関係種・capability・意味責務・入出力・checker rule・renderer・資産 digest を閉じたレジストリで管理。候補化は集合包含だけで、ランキングやヒューリスティックを持たず、候補集合から明示選択する。 | `assets/components/registry.json`; `scripts/ve_components/registry.py:1-7`; `scripts/ve_components/selection.py:1-6` | component の新設・責務変更が誤って承認されれば、その誤りが決定論的に量産される。よって registry は「モデル生成物」ではなく人間承認済み部品表でなければならない。 |
| **canonical renderer** | `TRUSTED_RENDERERS` の閉じた allowlist だけが HTML を生成する。manifest の component/version、意味 ID、関係 ID、資産 ID/digest を IR と照合する。flow は辺の脱落・反転・捏造も照合する。SVG は slope/waterfall のみ、要素・属性・整数座標・viewBox を閉じる。 | `scripts/ve_components/renderers/__init__.py:24`; `scripts/ve_components/assembly.py:84-163`; `scripts/ve_components/checker.py:45,1358` | renderer の実装バグはあり得るため、allowlist だけでなく bad fixture と目視が必要。自由 SVG は通常経路のフロア外。 |
| **controlled assets** | CSS/JS は registry 宣言済みの slot・component/version・SHA-256 と完全一致するものだけ注入できる。生 CSS/JS、外部参照、未知資産、改竄ファイルは fail-closed。現行12形式の script asset と dependency はともに空。 | `scripts/ve_components/checker.py:526`; `scripts/ve_components/flatten.py:35-57`; `references/design-system.md:207`; registry 実査で script asset 0件 | 基盤は将来の hash 付き script を許せるが、現行 canonical の品質フロアは static-first。動的部品を追加するなら script だけでなく IR・renderer・manifest・checker を原子的に追加する必要がある。 |
| **composer / flattener / final checker** | 順序を保って構成し、同一資産だけを dedupe。ビルド後に content safety、provenance、artifact semantics、renderer SVG、表記、文書構造、manifest-to-DOM を再検査し、成功後だけ atomic write する。 | `scripts/build_explainer.py:78-144`; `scripts/ve_components/assembly.py:296-337`; `scripts/ve_components/checker.py:1772-1798`; `scripts/ve_components/final_checks.py` | checker は JS を実行しない。このため自由 JS を許すと、検査後の DOM 変更や自動再生を静的検査だけでは保証できない。 |
| **禁止事項 / 縮退** | skeleton 直編集、生成 HTML 手直し、独自 CSS/JS/座標、装飾 glow/pulse/常時ループを禁止。弱モデルが契約を守れない場合は matrix/terms/短文へ縮退し、見栄え目的の SVG・動きを足さない。 | `SKILL.md:45-47,100,140-142` | 規約だけの禁止は、経路が自由 HTML を許す箇所では機械保証より弱い。互換経路は明示的に canonical 成功と区別すべきである。 |

**経路差の重要点:** canonical は `IR → 選択 → trusted renderer → manifest → final DOM` をすべて通る。一方 compatibility は provenance と content safety を通るが、canonical の選択・renderer・manifest をバイパスする。`stepper` は現在 compatibility 起点 (`SKILL.md:176`) であり、固定 skeleton JS が動作を担っていても、ステップ数・ラベル・全体表示・核心の静的残存を canonical と同じ強さでは検証していない。narrative では `data-step*` が予約属性として禁止されているため、弱モデルが stepper を使う入口は実質この互換経路になる。

なお調査中に `bash scripts/check.sh --selftest` を実行し、組み込み selftest は **31 passed / 0 failed** だった。これは固定域・安全性・一部文書構造の回帰確認であり、「ほぼ読まず理解」や事実正確性の証明ではない。

## 層別の推奨境界表

| 層 | 主分類 | LLM に許すもの | 信頼部品 / 決定論側へ閉じるもの | 推奨理由 |
|---|---|---|---|---|
| **文章 / IR 内容** | **LLM自由生成（閉じた意味スロット内のみ）** | 主張、短いラベル、値、出典参照、確度、関係種の enum、既存 component の明示選択。 | セクション種、順序、件数・文字数上限、必須 summary/caption/closing、escape、DOM 化。弱モデル経路では自由 narrative HTML を動きの入力にせず、typed field へ限定する。 | LLM の本来の役割は「何を伝えるか」。ただし自由散文や markup まで許すと H1 の文章過多を機械的に止められない。因果・順序の真偽は checker で証明不能なので、不確かな場合は静的な matrix/列挙へ縮退する。 |
| **図コンポーネント形状** | **完全決定論**（部品追加時のみ人間承認） | component ID と意味データだけ。 | DOM 形状、クラス、SVG 幾何、コネクタ、読み順、responsive、caption/注記配置、fallback、manifest。新形状は人間が一式を承認してから allowlist 化する。 | 同じ意味が毎回同じ形になり、弱いモデルが CSS・SVG・座標を発明できない。canonical 12 の現行方式を維持する。 |
| **色・タイポ・余白トークン** | **完全決定論**（値変更は人間承認） | 原則なし。意味上必要な `highlightId` や閉じた tone enum を最大1箇所だけ。 | token 値、テーマ、コントラスト、type scale、8px grid、幅、色の意味割当、focus、dark mode。 | 表層の自由度は主張理解に寄与しにくく、コントラスト・階層・一貫性を壊しやすい。文書ごとの theme/style 指定は不要。 |
| **スクロール / 入場モーション** | **完全決定論、既定 OFF** | なし。duration、delay、easing、距離、stagger、発火閾値を IR に持たせない。 | 静的初期表示を不変条件にする。将来 one-shot reveal を持つとしても、全資料共通の1仕様・reduced-motion 時即時表示・再生失敗時静的表示に固定する。 | 入場演出は関係の時間展開ではなく装飾になりやすく、H3 の対象外。スクロール連動で核心を隠すと「無操作で理解」を壊すため、最小セットにも含めない。 |
| **インタラクティブデモ（工程再生）** | **人間承認の信頼部品 + 完全決定論の実行** | typed step の ID、短いラベル、既存図の target ID、開始/終了/全体表示用の意味データだけ。 | DOM、状態機械、前/次/全体表示、キーボード/ARIA、reduced-motion、静的 fallback、最大 step 数、参照整合、script hash、manifest/checker。timer と autoplay は持たない。 | 工程再生は H3 に合うが、自由 JS は検査後に意味を変えられる。LLM は状態内容だけを書き、状態遷移の仕組みは1個の信頼済み部品に閉じる。パラメータ因果は当面 `compare` の静的並置を優先する。 |

**境界の短式:** `LLM = what`、`human-approved library = allowed visual/behavior vocabulary`、`deterministic build = how`。LLM に自由にしてよいのは、escape され、上限があり、既存 ID/enum で参照整合を検査できる意味データまでである。

## 緩和時の失敗モード

| 緩和 | 具体的な失敗 | なぜ既存フロアを壊すか |
|---|---|---|
| 弱いモデルに CSS を書かせる | `font-size` を縮めて文章を詰め込む、absolute 座標で重なる、mobile で横溢れ、token を上書きする、色だけで確度を表す、`display:none` で核心を隠す。 | hash 済み CSS と token 所有権を迂回し、静的 DOM が正しくても見え方が壊れる。 |
| 弱いモデルに JS を書かせる | 自動再生、無限 timer、スクロール hijack、検査後の DOM 書換え、必須文の遅延挿入、クリック不能化、localStorage/clipboard の想定外利用。 | checker は script を実行しない。現在の CSP は固定 inline JS を許すため、自由 JS の安全性を CSP だけでは止められない。 |
| motion の duration/easing/stagger を IR に開放する | 1節ずつ長く待たせる、全要素を順番に出して結局文章を読ませる、弱モデルごとにリズムが変わる、reduced-motion を忘れる。 | 見た目のランダム性を再導入し、H1 の文章量を温存したまま閲覧時間だけ増やす。 |
| scroll reveal で初期状態を非表示にする | JS 無効・Observer 未発火・印刷・途中アンカー遷移で核心が見えない。 | 「操作しなくても核心に到達」「static-first」を破る。失敗時に情報が消える progressive enhancement の逆になる。 |
| stepper を互換 HTML のまま量産する | `data-total-steps` と panel 数の不一致、開始/終了予告なし、次ボタンが結果を予告しない、「全体表示」欠落、必要事実を未到達 step にだけ置く。 | 固定 JS は動いても、入力 DOM の意味契約と無操作不変条件が canonical manifest/checker で保証されない。 |
| 自由 SVG / 座標を一般解禁する | 文字切れ、重なり、矢印の逆転、狭幅で判読不能、不可視要素や外部参照の混入。 | slope/waterfall の閉じた SVG grammar と renderer 所有の幾何を失う。 |
| registry にランキング・テーマ・animation metadata を入れる | 同じ関係からモデルや順序により別 component/演出が選ばれ、誤った「おすすめ」が固定化される。 | 現在の集合包含 + 明示選択という再現可能性が崩れる。 |
| token を文書単位で選ばせる | “重要そう”という理由で全要素を accent、任意フォント、低コントラスト、余白の細分化。 | 意味色と視覚階層が競合し、「一流コンサル的な簡潔さ」より装飾選択が前面に出る。 |
| 自由 narrative を動きの source of truth にする | 散文から runtime が段階・因果を推測し、原文にない順序を作る。 | checker が検証できる明示 relation/semantic ID を失い、弱モデルの言い換え誤差が動きとして強調される。 |
| checker を「通すため」に弱める | 壊れた component の近似 class、欠落 ID、hash 不一致、未登録 script を許容する。 | fail-closed の連鎖に穴が開き、以降の全資料で品質低下が再現される。壊れた部品は外すべきで、検査を緩めて延命すべきでない。 |

## 動きを入れる場合の最小信頼部品

動きは**時間・順序・状態変化そのものが核心**の場合だけ、次の3部品に限定する。名前と責務は提案であり、コード追加の許可を意味しない。

1. **`sequence-ir@1`** — 2〜6段の意味契約。step ID、短いラベル、開始/終了、既存 canonical semantic ID への highlight 参照、初期表示する全体要約を持つ。CSS/JS/座標/timing/autoplay フィールドは持たない。
2. **`sequence-stepper@1`** — 人間承認済みの renderer + 最小 CSS + runtime の原子的部品。静的な全体像を先に描画し、JS は前へ・次へ・全体表示の有限状態機械だけを担当する。自動再生、loop、scroll-jacking、任意 callback、ネットワークを持たない。ボタンは次の結果を予告し、ARIA とキーボード、`prefers-reduced-motion` を固定する。
3. **`sequence-check@1`** — IR 上限、step/target 参照、開始/終了/全体表示、DOM/manifest、hash 済み script asset、無操作時の静的要約の存在を fail-closed で検査する。意味的に必要な事実が隠れていないかは、機械検査に加えて目視項目として残す。

この3部品で「工程を1段ずつ見る」と「既存図中の highlight を移す」を同じ機構で扱う。別の `scroll-reveal`、`timeline-player`、`simulation-engine` は作らない。既存 skeleton 内 stepper ロジックは参考にはなるが、互換 HTML の自由形をそのまま品質フロアと見なさない。

## 捨てる案（引き算）

- **全セクションのフェードイン / stagger** — 関係を説明せず、読む待ち時間を増やすため捨てる。
- **parallax、sticky scrollytelling、scroll-snap、スクロール量連動再生** — 閲覧制御を奪い、印刷・アンカー・reduced-motion・小画面を複雑化するため捨てる。
- **GSAP / Lottie / D3 / Canvas / WebGL / 動画・GIF** — 外部依存、別レンダリング系、資産管理、アクセシビリティ面を増やす割に成功条件へ直結しないため捨てる。
- **任意 keyframe DSL、文書ごとの easing/duration/theme** — LLM の表層選択を再導入するため捨てる。
- **autoplay、常時 loop、pulse、glow、particle、背景アニメーション** — 装飾であり H3 を満たさないため捨てる。
- **汎用 slider / toggle / sandbox / ノーコード demo engine** — 状態空間と checker を急増させるため捨てる。パラメータ因果はまず静的 `compare` で並置する。
- **自由 SVG をアニメーションする万能図** — 座標・意味・動作の3自由度が同時に開き、最も弱モデル劣化しやすいため捨てる。
- **動きで長文を小分け表示する方式** — 文章依存を隠すだけで H1 を解かないため捨てる。先に claim/relationship を図へ移し、文章を削る。
- **component ごとの専用 player** — `flow-player`、`chevron-player` 等の重複を作らず、時間軸は空間図と直交する `sequence-stepper@1` 1系統に閉じる。

## 結論（このグループ単体）

弱いモデルの品質フロアを守れる境界は、**LLM の自由を意味内容と既存語彙の選択までに止め、形・token・DOM・座標・CSS・JS・時間パラメータをすべて信頼済み決定論側へ置く**位置である。特に motion は見た目の属性ではなく、検証対象の「意味を持つ状態遷移」として扱う必要がある。

したがって H3 を採る最小案は、スクロール入場演出ではなく、typed sequence を手動で進める単一 stepper だけである。初期表示に核心と全体像を残し、操作は関係を時間展開して理解を深める追加経路に限定する。現行 compatibility stepper はこの方向の種だが、typed IR・trusted renderer・manifest・専用 checker が揃うまでは canonical 12 と同じ保証領域には数えない。

この境界なら H2 の「図＝本体」を強めつつ、H1 の文章依存を motion で覆い隠さない。逆に自由 CSS/JS、全体 reveal、汎用 demo engine を許す案は、技術の引き算と決定論の双方に反するため採らない。
