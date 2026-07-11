# visual-explain ビジュアル基準 v1 仕様

**ゴール:** 意思決定者（ユーザー本人）が本文を読まずに「図＋メッセージ行」だけで承認/却下を判断でき、理解に必要な認知負荷が最小になる、再利用可能なビジュアル基準を定義し、skeleton・matrix/flow コンポーネント・flow renderer に適用する。

**位置づけ:** コンポーネント基盤（2026-07-10 spec、PR #1 / 5c420a1 で実装済み）の上に載る、初のビジュアル設計フェーズ。安全アーキテクチャ（自己完結 HTML・CSP・固定領域ハッシュ・信頼レジストリ・fail-closed 診断・renderer 信頼境界の DOM 照合）は弱めない。

## 前提決定（ユーザーヒアリング 2026-07-11）

| 論点 | 決定 | 帰結 |
|---|---|---|
| 読者と状況 | 自分＝意思決定者を最優先 | 最短時間で判断材料を掴む動線を最優先する |
| 理解の合格基準 | 図＋メッセージ行で判断可能 | 見出し＝主張の完全文、図＝その証拠。本文は深掘り用 |
| 密度哲学 | ハイブリッド | 第一画面は疎（Apple 的）、根拠セクションは密（コンサル的） |
| スコープ | 基準策定＋既存面の刷新 | skeleton・matrix/flow・flow renderer まで。図解の種類拡充は次フェーズ |
| 色とトーン | モノクロ基調＋意味色のみ | 装飾色ゼロ。「色が付いていれば必ず判断上の意味がある」 |
| 判断・依頼・仮説 | 図解対象に含める | 未決事項・ユーザーへの依頼・検証待ち仮説を統一記法ブロックで描き、checker で構造を保証する |
| 図上注釈 | 今回に含める（ユーザー決定 2026-07-11） | matrix/flow 限定の最小注釈 IR を追加する |

## 設計根拠と出典の区分

5仮説を調査し、いずれも支持する資料を得た（2026-07-11）。出典は等級を区別する。

**一次資料**: IBCS 公式（ibcs.com、ISO 24896 として標準化）／Apple Human Interface Guidelines（developer.apple.com: Typography・Layout）／FT Visual Vocabulary（github.com/Financial-Times/chart-doctor）。
**二次資料**: McKinsey 流スライド設計の解説（a1slides.com・deckary.com）／Tufte data-ink の解説（infovis-wiki.net）／IBCS 解説（Wikipedia）／FT Burn-Murdoch 注釈研究の紹介（gijn.org）／5秒ルール解説（customerscience.com.au）。原典（Minto『The Pyramid Principle』、Zelazny『Say It With Charts』、Tufte『The Visual Display of Quantitative Information』）は未参照であり、主張は二次資料経由。
**実務慣行**: 8pt スペーシンググリッドは業界慣行であり、Apple HIG が明文で規定するものではない。
**設計上の独自決定**: 3層への責務分離、意味色を判断状態に限定する規則、ask ブロック記法、疎/密2モード。

1. **アクションタイトル** — 見出し＝洞察の完全文、見出し列だけで議論が完結する horizontal logic（Minto ピラミッド原則、二次資料）。FT の視線追跡でも読者は最初にタイトルを見る（二次資料）。
2. **統一記法** — IBCS「UNIFY: 同じ意味は常に同じ見た目」（一次資料）。Zelazny は全メッセージを5比較型に還元（二次資料）。IBCS CONDENSE は根拠部の高密度を支持する（一次資料）。
3. **Apple 的洗練の分解** — 単一フォント族＋ウェイト階層、整列と適応の重視（HIG Typography / Layout、一次資料）。
4. **モノクロ＋意味色** — Tufte data-ink 原則: non-data-ink を消し、色は意味の強調のみ（二次資料）。
5. **3段階読解パス** — 「5秒ルール」と progressive disclosure（二次資料）。

追加発見: FT Visual Vocabulary の9カテゴリは relationship.kind → capabilities 選択機構と同型で、将来の拡充語彙になる。FT の知見では図上注釈が理解と記憶を最も改善する — annotation を今回スコープに含める根拠。

限界: Mayer 系・視線追跡系の知見は教育/報道文脈の実験に基づく参考値であり、本用途での効果量を約束しない。既存 design-system.md の「効果を約束しない」規律を維持する。

## 基準本体: 3層統合基準

責務を3層に分離する。層の境界検証: 表層を将来差し替えても構造層・記法層の規範は変わらないこと。

### 構造層 — 何を・どの順で（コンサル由来）

- **アクションタイトル契約**: すべてのセクション見出しは、述語を持つ自己完結した主張とし、1つの洞察だけを述べる。主語は対象が一意に特定できる場合に省略してよい（日本語の自然さを優先）。トピック名（「現状分析」等）を禁止する。長さは40〜50字を目安とする（30px・narrative 幅との整合）。
- **1主張＝1主要証拠オブジェクト**: 各セクションは1つの主張と、それを証明する主要証拠オブジェクト1つ（図・表・数値・短文のいずれか）を持つ。既存 patterns.md の「図が短文より明確になる理由がないなら図を使わない」規律を維持し、図を強制しない。
- **Horizontal logic 自己検査**: 生成時、見出しだけを上から順に読んで議論が完結し承認/却下を判断できるかを検査する。patterns.md に生成時チェックリストとして規定する。
- **3段階読解パス**: 3秒＝第一画面（提案1文＋あなたが決めること1文＋条件最大2件）／30秒＝アクションタイトル＋主要証拠の拾い読み／3分＝本文根拠・確度・出所・deep-dive。既存の first-screen 契約と deep-dive 構造を継承する。
- **密度の2モード**: 第一画面は疎モード、根拠セクションは密モード。スペーシングトークンで切り替え、恣意的な余白指定を許さない。

### 記法層 — どう描くか（IBCS/FT/Tufte 由来）

- **統一記法**: 同じ意味は資料内・資料間で常に同じ見た目。skeleton トークンを再定義する。
- **色は判断状態専用**: 意味色3系統 — 選択＝青／推奨＝緑／警告＝橙 — を判断状態にのみ使う。装飾色は0。
- **確度は色と分離**: 確度3値（確認済み/推論/未確認）はモノクロのテキストバッジ（ラベル＋グレー階調＋線種差）で表し、意味色を再利用しない。色チャネルの多義化を禁止する。色だけで意味を完結させない既存規律（本文にも理由を書く）を維持する。
- **Takeaway キャプション**: 図の caption を「説明文」から「その図から持ち帰る1文（takeaway）」へ昇格させる（規約変更）。
- **図上注釈（matrix/flow 限定の最小 IR）**: caption の結論が図のどこで証明されるかを指せるようにする。契約を次に固定する:
  - `takeawayTargetIds`: takeaway が指す semantic ID 配列。**原則1〜3件**。0件は takeaway が図全体を対象とする場合のみ許可し、その場合は `takeawayScope: "whole"` の明示を必須にする（暗黙の0件は validation エラー）。
  - `emphasis`: `[{targetId, label}]` の配列（最大3件）。`label` は40字以内の局所注釈で、対象の直近に描画する。
  - 対象 ID の制約: matrix ではセル ID のみ、flow ではノード/エッジ ID のみを許可。`takeawayTargetIds` と `emphasis.targetId` それぞれで重複禁止。存在しない ID は fail。
  - 強調は意味色ではなくモノクロの強勢（太字・面）で表す。注釈内容は accessibility summary にも反映する。`label` と caption の同文重複は禁止（Redundancy 規律）。
  - 語彙・IR スキーマ・validation・renderer・checker・テストを同期して拡張する。汎用 annotation 言語や自由座標は導入しない。
- **判断・依頼・仮説の記法（ask ブロック）**: 意思決定対象を本文の散文に埋めず、統一記法のブロックとして描く。3種は判別可能な別契約（discriminated union）とし、種別ごとに要求を分ける:
  - **decision**: 問い（完全文）＋選択肢2件以上（各1行のトレードオフ付き）＋推奨0または1件。推奨1件を原則とし、推奨なしの場合は「推奨しない理由」1文を必須にする（根拠のない推奨をでっち上げない）。
  - **request**: 手順リスト。各項目は意味役割 `user` / `agent` / `third-party` のいずれか＋動作を持つ。表示ラベル（「あなた」「Claude」等）は文書側の表記であり、記法上の役割は意味役割で固定する（他エージェントでの再利用を壊さない）。
  - **hypothesis**: 主張文＋現在の確度（3値）＋検証方法1文。
  - 実装は skeleton の固定 CSS クラス＋patterns.md の文法ブロック。**checker に種別ごとの構造検証を追加する**: decision は問い・選択肢数・推奨の一意性（0件時は理由の存在）、request は役割ラベルの妥当性、hypothesis は確度と検証方法の存在を DOM 構造で検査し、不備は fail-closed 診断にする。canonical コンポーネント化（document-level ask block）は次フェーズ候補として記録する。
- **将来語彙の文書化**: FT 9カテゴリ＋Zelazny 5比較型を、次フェーズのコンポーネント拡充順序の根拠として references に文書化する（実装しない）。

### 表層 — どう見せるか（Apple HIG 由来）

- **タイポグラフィ**: システムフォント単一族。階層はサイズ＋ウェイトのみ。4段タイプスケールを skeleton に固定する: 第一画面主張 30px/700・セクション主張 20px/700・本文 16px/400・補助 13px/400（rem 基準で実装し、この4値は実装時に変更しない）。本文の行長は日本語約40字を上限とする。行間は本文 1.7〜1.8・見出し 1.4〜1.5 をトークン化し、段落間隔もスケールから取る。
- **二段階幅と整列**: 幅を役割で2段階にする — narrative カラム（本文・見出し・キャプション）は 720px、evidence カンバス（多列 matrix・分岐 flow・注釈付き比較図）は最大 1040px。両者は同じ左端の整列線を共有し、中央寄せは第一画面の演出にも使わない。狭幅（モバイル）では evidence は横スクロールコンテナまたは縦変換に縮退する。文章の可読幅とコンサル的一覧性を両立させる。
- **余白リズム**: 8px 基準のスペーシンググリッドをトークン化（8/16/24/32/48/64/88px。CSS の px であり pt ではない）。疎/密2モードはこのスケール内の割当差で表現する。グリッド一致の監査対象は margin・padding・gap に限定する（border 幅・フォントサイズ・行高には要求しない）。
- **Deference**: 枠線・罫線を最小化する。区切りは余白と見出しウェイトで表現。カード枠線は淡い面（surface 背景＋角丸）で代替。細い横罫線は表の行区切りのみに残す。縦罫線禁止・見出し行のみ強い罫線、の既存規律を維持する。
- **適応と密度上限**: 狭幅（モバイル）では表・flow が横スクロールコンテナに収まり、本文は折返しで破綻しないこと。長い日本語見出しの折返し規則（`text-wrap: balance` 相当の静的配慮）を定める。matrix は1画面あたり行数の目安上限（10行程度）、flow はノード数の目安上限（12ノード程度）を規範として design-system.md に記す。
- **両テーマのコントラスト**: ライト/ダーク双方の全トークン組合せ（本文/背景・意味色/その背景・確度バッジ・補助本文）で、通常文字 4.5:1 以上・大きい文字（20px/700 以上）3:1 以上・意味を持つ非文字要素 3:1 以上を満たす。実装時にコントラスト比の計算検査（スクリプト）を fixture 検証に含める。

### flow renderer の視覚構造契約（今回スコープ）

現行 renderer はノード一覧とエッジ文一覧を別々に出力しており（flow.py）、同じ関係を二度読むリスト構造でトポロジーを視覚的に読ませられない。CSS 再スタイルだけでは不足するため、renderer を以下の決定論的レイアウト契約で刷新する。

**v1 描画可能トポロジー（受理条件の fail-closed 化）**: 現行 validation は `ordered-transition` 宣言時のみ循環を禁止し（validation.py:159）、一般の directed-graph では循環・後退エッジ・任意の合流を受理する。これは CSS 中心の spine/branch レイアウトで交差なく描ける範囲を超えるため、canonical flow の受理条件を v1 レイアウト契約に一致させる:

- **前向き制約**: reading order（未指定時はノード宣言順）を線形基準とし、全エッジは source が target より前にあること。後退エッジ・自己ループを禁止 → 循環は宣言 capability に依らず構造的に全面禁止。同一ノード対の並行辺も禁止する（描画の一意性を保つ。関係が複数あるならラベルに併記する）。
- **分岐/合流上限**: ノードあたり fan-out 最大3・fan-in 最大3。
- **スキップ接続**: 隣接しないノードへの前向きエッジは許可。renderer が右側レールへ決定論的に割り当て、同時に必要なレール数が3を超える場合は bounded diagnostic（`flow_topology_too_complex`）で fail する。
- **group 間エッジ**: 前向き制約により自動的に単純化される（前方の group へのみ接続可）。
- **縮退**: 受理不能なトポロジーは、既存規約（Katsura 縮退規則）どおり matrix・terms・文章での表現に author が切り替える。silent fallback はしない。
- これは受理範囲の**縮小**（強化）であり、checker/validation の既存規則は弱めない。既存 fixture への影響はテストと同期して更新する。

**レイアウト契約**:

- **spine**: reading order のノード列を縦の主軸として1視野に描く。
- **branch**: 分岐エッジは主軸からの視覚的接続（CSS 描画のコネクタ）として、分岐先ノードと同一視野で表す。自由座標・SVG パス生成・JS レイアウトは導入しない。
- **group**: 既存の group を視覚的なレーン/ブロックとして描く。
- **edge label / relation**: エッジのラベルと関係種別はコネクタの直近に置く（離れた凡例を作らない）。
- **reading order**: DOM 順は宣言された reading order を保持し、逆転しない。
- **アクセシビリティと照合の維持**: `.ve-flow-node`・`data-ve-from/-to/-relation` の抽出契約（checker の DOM 照合）を保ち、エッジの文章表現は visually-hidden の代替テキストとして残す（可視層での二重表示は Redundancy 規律により禁止）。checker/`extract_flow_dom` の変更が必要な場合はテストと同期し、信頼境界を弱めない。

## 実装スコープ

| 対象 | 変更 |
|---|---|
| `skills/visual-explain/assets/skeleton.html` | トークン再定義（モノクロ階調＋判断状態3色）、4段タイプスケール、8pt スペーシング、疎/密モード、整列規則、ask ブロック用固定 CSS |
| `skills/visual-explain/scripts/ve_components/renderers/flow.py` | 視覚構造契約（spine/branch/group/edge label/reading order）での刷新。IR は維持 |
| `skills/visual-explain/scripts/ve_components/renderers/matrix.py` | takeawayTargetIds / emphasis の描画対応 |
| 語彙・スキーマ・validation | `component-vocabulary.json`・`component-ir.schema.json`・validation に最小注釈フィールドと v1 トポロジー制約（前向き・fan上限・レール上限）を追加 |
| checker | ask ブロック構造検証の追加、flow 抽出契約の同期、注釈対象 ID の実在検証。既存規則は弱めない |
| `skills/visual-explain/assets/components/`（matrix/flow アセット） | 新トークンでの再スタイル。レジストリの SHA-256 ダイジェスト更新を伴う |
| `references/design-system.md` | 3層基準として全面改訂（生成規範・密度上限・コントラスト基準） |
| `references/patterns.md` | アクションタイトル契約・horizontal logic 自己検査・takeaway キャプション規約・ask ブロック文法・注釈の使い方の追加 |
| `references/`（出典台帳） | 本 spec の設計根拠の台帳を追加: 正確なタイトル・URL/書誌・参照日・支持する規則・一次/二次の別 |
| `scripts/tests/`（fixtures） | 検証マトリクス（下記）への拡充と新 skeleton への同期 |
| `examples/example-proposal.html` | 新基準での再生成（canonical example） |

**変更しないもの**: CSP、固定領域検証の仕組み、選択アルゴリズム（narrow/explicit-select）、build_explainer パイプラインの段構成、compatibility 経路の安全規則。

**非ゴール**: 汎用 annotation 言語・自由座標、新規図解コンポーネント（layers/compare/timeline 等）、ask の canonical コンポーネント化、JavaScript による表現、ブラウザスクリーンショット比較の自動化、理解度の定量測定プロトコル（ユーザー方針により導入しない）。

## 成功基準と検証

- 既存テストスイート＋拡充後 fixtures がすべて緑。`check.sh` が canonical example で PASS。
- **検証 fixture マトリクス**（すべて light/dark × 広幅/狭幅 で確認）:
  1. 長い日本語アクションタイトル（折返し・整列の破綻なし）
  2. 疎な第一画面＋高密度 matrix の混在文書
  3. 直線 flow と分岐＋group 入り flow
  4. 選択・推奨・警告・確度バッジ・ask 3種・注釈が同時出現する文書（色多義・overflow・整列の監査）
- **3秒テスト**: 第一画面を3秒見て「何の話か」「何を判断するか」を答えられる。
- **見出しのみ判断テスト**: canonical example の見出し列と主要証拠のみで判断内容を言える（言えなければ構造層の規範を改訂する）。定量の正答率測定は行わない（ユーザー方針）。
- **色＝意味監査**: 生成物に装飾色が存在しない。色が付く要素はすべて選択/推奨/警告のいずれかに対応し、確度バッジはモノクロである。
- **8px グリッド監査**: margin・padding・gap がスケール外の値を持たない（border 幅・フォントサイズ・行高は対象外）。
- **コントラスト監査**: 全トークン組合せを light/dark 双方で計算検査し、4.5:1 / 3:1（大文字・非文字）を満たす。
- ユーザーによるブラウザ目視スモーク（fixture マトリクスの代表4文書、ライト/ダーク両テーマ）。

## ロールバック

マイルストーンごとに独立コミットし、直近マイルストーンの revert で戻せること。生成済み HTML 文書の修正や checker 規則の弱体化をロールバック手段にしない（基盤 spec と同じ規律）。
