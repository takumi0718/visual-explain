# 判断資料 v3: 表現拡張と判断回収（二段構え設計）

日付: 2026-07-16
状態: 外部レビュー反映済み（利用者再レビュー待ち）

## 背景と目的

visual-explain の当初意図は「どんなに弱いモデルでもクオリティを保つ」＝品質の底上げであり、上位モデルの表現を制限することは本意ではなかった。しかし現行アーキテクチャは下限保証の仕組み（固定 12 形式・自由 HTML/CSS/JS 禁止・SVG 最小許可リスト）が上限も封じており、Anthropic の記事 "The unreasonable effectiveness of HTML" が示す水準（表現力・読み進める構造・判断がエージェントへ返るループ）に届かない。

本設計のゴール（North Star）:

> 読者が資料の上だけで判断材料を得て、判断を下し、その判断がエージェントに戻る——読む→決める→返すのループが 1 枚の自己完結 HTML で閉じること。

前提の確認（利用者ヒアリング済み）: 読者は利用者自身のみ。用途は説明・判断資料のみ（コードレビュー資料・編集ツール・共有ホスティングはスコープ外）。対応モデルは二段構え（強モデル向けの拡張と、弱モデル向けの現行保証の両立）。

## 決定事項の要約

| 論点 | 決定 | 補足 |
| --- | --- | --- |
| 表現解放のメカニズム | ハイブリッド | 検証済み部品の語彙拡張が主経路、extended 限定の freeform セクションが逃がし弁 |
| 判断コピーの出力 | 判断＋文脈の構造化ブロック | 資料タイトル・パス・各 ask の問い→選択→メモ・未解決事項を含む |
| 判断回収の動線 | 末尾回収パネル | 「リスクと弱い前提」「不確かな点」を通過した後にのみコピー導線を置く |
| 目次 | 冒頭インライン目次 | ビルド時自動生成・静的アンカーのみ・サイドバー案はスコープ外 |
| 図の検証開示 | 読者向け表示はしない | 理由は下記「検証開示を不要とした理由」。provenance は data 属性で機械可読に記録 |
| 後方互換 | 破壊的変更で一気に移行 | 旧方式（narrative への first-screen 生 HTML）は受理しない |
| ask の種別 | 現行 3 種を維持 | askType（decision / request / hypothesis）の discriminated union。回収対象は decision のみ |
| 非隣接コネクタ解放 | 延期（スコープ外） | 現行ベジェ描画は障害物回避を持たず品質が成立しない。extended の複雑トポロジーは freeform SVG が担う |

### 検証開示を不要とした理由（記録）

図ごとの「機械検証済み / モデル描画」バッジは検討の末に不採用とした。

1. checker が保証するのは形の整合（検算・参照解決）であり内容の真実性ではない。IR の数値はモデルが書くため、「機械検証済み」表示は「内容が正しい」と誤読され偽の安心を与える害の方が大きい。
2. 判断に効く信頼情報は既存の確度ラベル（確認済み/推論/未確認）が対象の直近で既に担っており、図の出自ラベルは冗長。
3. 読者は利用者自身で、生成過程を知っている。

ただし freeform セクションには provenance を data 属性として機械可読に記録する（compatibility 節の既存パターンの延長）。将来共有用途が生まれた場合、表示への昇格余地を残す。

## スコープ外

共有・ホスティング、スライダー等の編集 UI、diff・コードレビュー資料、タブ、サイドバー目次、シンタックスカラー（code 部品 v1）、宣言的グラフ部品（ノード＋エッジ＋自動レイアウト）、コネクタの非隣接接続解放（経路探索の設計なしでは品質が成立しないため延期）、汎用 HTML 作業環境（将来の兄弟スキル）。

## アーキテクチャ

### IR 拡張

- `document.type: "proposal" | "system" | "research"` — 資料型を IR で宣言する。
- `document.profile: "strict" | "extended"` — strict は現行の固定語彙のみ（弱モデル向け）、extended は拡張語彙＋freeform 可（強モデル向け）。生成 HTML は profile と type を data 属性で自己表明し、`check.sh` は表明に応じた検査を適用する。SKILL.md の弱モデル縮退規則（Pi/Katsura）が strict への誘導を担う。
- 型付きセクションの新設。構造の正しさはレンダラが構成的に保証する。
  - `kind: "first-screen"` — 判断文・条件（最大 2 件）を構造化フィールドで受ける。見出し（h1）と `<title>` は `document.title` から導出し、重複フィールドを持たない（**タイトルの正本は `document.title` のみ**）。summary は `document.summary` から描画する。subtitle は資料型で切り替える: proposal は「あなたが決めること」の判断文、system / research は「この資料が答える問い」。
  - `kind: "closing"` — 資料型別の必須節（proposal: リスクと弱い前提／不確かな点、system: 限界・確度、research: 限界・反証・確度）を配列で受ける。空配列は拒否。
  - `kind: "ask"` — `askType: "decision" | "request" | "hypothesis"` の discriminated union として現行 3 種の契約（checker `_ASK_KINDS`）を引き継ぐ。decision は問い・選択肢（ラベル＋トレードオフ）・既定案（任意）・メモ欄を持ち、判断回収の対象になる。request / hypothesis は現行契約どおりの静的表示で、回収パネルには入らない。
  - `kind: "freeform"` — extended 限定。provenance（出自・理由）必須。
- `narrative` は自由散文用に残る。first-screen・closing・ask を narrative の生 HTML で書く旧方式は受理しない。
- 目次は IR に書かない。ビルド時に決定的に自動生成し、見出しを持つセクションが 5 個以上のとき first-screen 直後に挿入する。対象は見出しを持つ本文セクション（first-screen と目次自身は含まず、closing は含む）。アンカーにはセクションの既存 instance ID を使う（文書内一意は checker が既に保証）。階層はフラット 1 段とし、重複する見出し文字列は ID で区別されるため許容する。
- 文書構造の不変条件（validation と検査群③の両方で強制する）:
  - first-screen はちょうど 1 個で先頭。closing はちょうど 1 個で利用者記述セクションの最後（回収パネルはレンダラが closing の後に生成する）。closing より後に利用者記述セクションは置けない。
  - h1 を持てるのは first-screen（`document.title` 由来）だけ。narrative / freeform に h1・`<title>`・予約 class・予約 data 属性は書けない。
  - 予約 data 属性（`data-ve-*`、`data-connect(-scope)`、`data-stepper` / `data-step(-action)`、`data-ask*`、`data-theme*`、`data-lane`、`data-tone`）はレンダラ出力と compatibility 節にのみ許し、narrative / freeform では拒否する（固定 JS の意図しない駆動と判断回収出力への偽装注入を防ぐ）。

### checker の 4 検査群

| 検査群 | strict | extended |
| --- | --- | --- |
| ① 安全性（script 注入・イベント属性・外部フェッチ禁止） | 常時 | 常時 |
| ② 自己完結性（単一ファイル・外部読込なし） | 常時 | 常時 |
| ③ 正直さ・構造（型別必須節、h1 一意、`<title>`＝first-screen h1 一致、判断文 1 文、確度語彙、summary 描画、外部リンクの可視ドメイン表示） | 常時 | 常時 |
| ④ レイアウト統制（canonical 部品語彙への限定※、SVG 許可リスト、インライン style 禁止） | 適用 | freeform 内のみ緩和 |

※ 部品語彙: 既存 12 形式＋新設 `code` は両 profile、`image` は extended のみ。

検査群③は新設であり、canonical 経路で資料型検査がスキップされる既知の穴（構造なし資料が PASS する）を塞ぐ。検査は IR 段階（validation）と生成物段階（check.sh 単体実行）の両方で行い、同じ判定を再現する。

機械保証の限界を明記する: 検査群③が保証するのは構造と語彙（節の存在・一意性・確度語彙の統一）までであり、主張の意味的な正しさ（どの主張に確度ラベルが必要か、ラベルは妥当か）は目視 QA の責務として SKILL.md のチェックリストに残る。

### 外部リンクの解放（両 profile）

`href` のみ、閉じた scheme 許可で解放する: 許すのは `https:` の絶対 URL と資料内アンカー（`#`）だけ。`javascript:` / `data:` / `file:` / protocol-relative（`//`）/ 相対 URL は明示的に拒否する（相対 URL は外部ファイル参照であり自己完結を破る）。`src` は禁止を維持する（読込が発生しないため自己完結と両立）。可視ドメイン表示（例: 「Anthropic 公式記事 ‹claude.com›」）はモデル入力ではなく、レンダラが URL を解析した hostname から生成する。これにより SKILL.md 調査報告型の「出典リンクを近傍に置く」と checker の矛盾が解消される。

## 部品と表現

### 新 canonical 部品

- **`code`**（両 profile）: 言語名・コード行・行アノテーション（行番号に紐付く注記。決定的レンダリング）・takeaway caption。シンタックスカラーは v1 では実装しない。
- **`image`**（extended 限定）: data: URI 埋め込みのみ。`alt`・caption・出所を必須フィールドとする。skeleton の CSP を `img-src data:` へ改定する。入力契約: MIME は PNG / JPEG / WebP の許可リスト（**SVG data URI は script を持ち得るため拒否**）、base64 は厳密 decode して magic bytes を宣言 MIME と照合、サイズは decode 後のバイト数で計測、画像寸法・総ピクセル数にも上限を置く。警告基準（1 画像 500KB・文書合計 2MB）とは別に、絶対拒否上限（1 画像 2MB・文書合計 8MB）を設ける。
- 目次: 部品ではなくビルド処理。上記のとおり。

### SVG の解放

- レンダラ用 SVG 許可リストに `path` / `polyline` / `marker` を追加する（矢印表現の土台）。整数座標・viewBox 固定・要素/属性完全一致の既存ゲートは維持。信頼済みレンダラの語彙拡張であり両 profile 共通。
- skeleton コネクタ JS の「隣接ノードのみ接続可」制約は解除しない（スコープ外へ移動）。現行実装は障害物回避を持たない単純なベジェ曲線で、非隣接接続ではノード貫通・交差を目視以外で防げない。extended での複雑トポロジーは freeform SVG が担う。

### freeform セクション（extended 限定）

「任意の HTML」ではなく、**広いが閉じた許可リスト契約**とする。freeform は信頼済み固定 JS と同じ文書に同居するため、開いた契約は信頼境界を壊す。

- 許可リスト（閉集合。拡張は許可リストへの明示追加で行う）:
  - HTML: 見出し（h2〜h4）・段落・リスト・表・`figure` / `figcaption`・`div` / `span`・`details` / `summary` 等の構造タグ許可リスト。
  - インライン `style` 属性: CSS プロパティの許可リストに限る。値に `url(` / `expression(` を含むものは拒否。`position:absolute`＋複数 px の既存禁止も維持。
  - インライン SVG: 要素の許可リスト（図形・`path`・テキスト・`marker` 等）。`foreignObject`・`use`・SMIL 系（`animate` / `animateTransform` / `set`）・`script` は拒否。
- 禁止のまま: `script`、イベント属性、外部参照、`<style>` タグ（グローバル汚染防止）、固定領域マーカー、予約 data 属性（IR 拡張の不変条件を参照）。検査群①②③は freeform 内にも全適用され、確度ラベルと正直さの規則は免除されない。
- provenance はモデルの markup ではなく、**レンダラが freeform の wrapper 要素に付与する**（モデルは出自を偽装できない）。
- 義務: SVG 理由コメント（既存規則の踏襲）、目視 QA。
- 使用条件: canonical 12 形式で表せないこと。同型の freeform が繰り返されたら部品昇格を検討する（freeform は昇格候補の観測装置を兼ねる）。

### 判断回収エンジン（skeleton 固定 JS）

- ask はどの資料型にも 0 個以上置ける。回収パネルは ask が 1 個以上あるときだけ生成する（ask ゼロの資料に空パネルは出さない）。
- ask レンダラは選択肢・メモ欄を data 属性つきの静的 HTML として出力し、skeleton 側の固定 JS（テーマトグル・ステッパーと同格の信頼済み領域）が選択・メモ・回収を担う。モデルは JS を書かない。
- 末尾回収パネル: closing 節の後に置き、全 ask の「問い→選択→メモ」サマリー・全体メモ欄・「判断をプロンプトとしてコピー」ボタンを持つ。読み順の最後にのみコピー導線を置くことで「リスクを見てから判断を出す」構造をレイアウトで強制する。
- **既定案は選択済みとして扱わない。** 読者が明示的に選ぶまで ask は未選択であり、コピー出力には「未選択（既定案: 案B）」と出力する（資料は判断を代行しないという原則の実装）。
- コピー出力（構造化ブロック形式）。受け取るエージェントが資料を開かなくても判断を再現できることを目標に、次を含める:

  ```
  [visual-explain 判断結果]
  資料: <document.title>
  (<ファイルパス> / id: <document.id> / schema: <schemaVersion> / asks: <ask 契約ダイジェスト>)
  問い: <ask の問い>
  → 選択: <選択肢ラベル>（既定案どおり / 既定案から変更 / 既定案なし） — トレードオフ: <選択肢の tradeoff 1 行>
  → メモ: <ask ごとのメモ>
  未選択: <未選択の ask（既定案: X）>
  リスク要約: <closing のリスク・不確かな点の見出し列挙>
  全体メモ: <パネルの自由記述>
  ```

- 選択とメモは localStorage に永続化する。キーは `document.id + schemaVersion + ask 契約ダイジェスト`（ダイジェストはビルド時に ask ID と選択肢 ID から計算し、data 属性として埋め込む）。復元時、現行の選択肢 ID に存在しない値は破棄する（資料を再生成して選択肢が変わった場合に古い選択を復元しない）。クリップボード API 不可時はパネル内に整形テキストを表示して手動コピーへ縮退。localStorage 不可時は永続化のみ失われ選択は機能する。
- 無操作の不変条件を維持する: JS 無効でも ask は既定案つきの静的表示として読め、回収パネルは要約表示として成立する。

## データフロー

IR（type / profile / 型付きセクション）→ validation（type を知った上で必須節の存在を IR 段階で検査）→ canonical は registry 選択・freeform は安全検査 → レンダラ（first-screen / closing / ask / 目次を新設）→ composer / flattener（目次の自動挿入）→ 最終検査（①②③常時＋④ profile 依存）→ atomic write。

## エラー処理

- canonical 生成失敗・freeform 検査失敗: 診断を返して報告する。暗黙縮退・暗黙修正はしない（現行方針の維持）。
- strict 文書への freeform 混入、型別必須節の欠落: IR 段階でビルド拒否（生成前に落とす）。
- 回収 JS: クリップボード不可 → パネル内テキスト表示、localStorage 不可 → 永続化のみ喪失。

## テスト戦略

- skeleton 改定は固定領域ハッシュを変えるため、全 HTML fixture を resplice ツールで一括再生成する。改定は Phase 2（回収 JS）と Phase 3（CSP）の 2 回発生し、その都度再生成する。ここが最大の機械的コスト。
- 検査群③の bad fixture には、2026-07-16 の検証で作成した「構造なしでも PASS するすり抜け資料」(第一画面なし・末尾節なし・h1 重複・title 不一致)を流用する。
- 新部品は既存慣例(component-valid/bad-*.json ＋ renderer/checker ユニットテスト)を踏襲する。
- 判断回収 JS は実ブラウザでの自動受入テストを Phase 2 の完了条件とする（Playwright・開発時専用依存。スキル利用時のゼロ依存は不変）。検証シナリオ: ①複数 ask の選択・変更・再読み込み後の復元 ②キーボード操作とフォーカス順 ③クリップボード成功／拒否時の手動コピー縮退 ④localStorage 例外時の縮退 ⑤JS 無効時の静的表示 ⑥日本語・改行・長文メモのコピー結果の完全性 ⑦選択肢を変更した再生成文書で古い選択を復元しないこと。file:// と http:// の両方で実行する（localStorage / Clipboard API の実行環境差を検証）。コネクタ・ステッパー等の既存 JS は従来どおり静的検査＋目視 QA。
- `check.sh --selftest` に検査群③のケースを追加する。

## 後方互換ポリシー

破壊的変更で一気に移行する。利用者は 1 名で既存資料は再生成可能であり、二方式並存は checker を複雑にするだけである。examples・fixtures・SKILL.md・references/patterns.md・references/design-system.md・CLAUDE.md を同時改訂する。

## フェーズ分割（spec 1 本・実装計画 3 本）

1. **Phase 1 基盤**: IR 拡張（type / profile / 型付き first-screen・closing・ask の静的表示）＋検査群再編＋外部リンク解放＋summary 描画＋目次。既知 3 欠陥（構造検査欠落・summary 未表示・見本の h1 重複）はここで消滅する。
2. **Phase 2 判断回収**: ask 選択 UI・末尾回収パネル・固定 JS・永続化・ブラウザ受入テスト。
3. **Phase 3 表現拡張**: code / image 部品・CSP 改定・SVG 許可リスト拡張・freeform セクション。

順序の理由: ask の型定義（Phase 1）が回収エンジン（Phase 2）の前提。freeform は checker 再編（Phase 1）に依存。表現拡張は互いに独立なので最後にまとめる。

## 既知欠陥との対応表（2026-07-16 検証で実証）

| 欠陥 | 本設計での扱い |
| --- | --- |
| canonical 経路に資料型の構造検査がない（構造なし資料が PASS） | 検査群③の新設＋型付きセクションで構成的に消滅（Phase 1） |
| 外部出典リンクが canonical 経路で禁止（SKILL.md と矛盾） | href のみ両 profile 解放＋可視ドメイン表示（Phase 1） |
| document.summary が必須なのに未表示 | first-screen の構造化フィールドとして描画（Phase 1） |
| 公式見本 example-proposal の h1 重複 | 型付き first-screen ではセクション見出しが h2 になり再発不能。見本は再生成（Phase 1） |
