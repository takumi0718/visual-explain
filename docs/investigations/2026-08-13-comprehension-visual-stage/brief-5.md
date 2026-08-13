# Worker 5 — G5: UX critique + AIスロップ診断（実装禁止・調査のみ）

## 作業ディレクトリ
この worker の cwd のみに成果物を書いてよい。
読む対象（read-only）:
- 例資料: `/Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/examples/example-proposal.html`
- 骨格CSS等: `/Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/assets/`
- 先行調査: `/Users/yoshidatakumi/.cache/pi-fleet/runs/20260813-092715.PuYUDO/worker-1/findings-g1-text-dependence.md` `/Users/yoshidatakumi/.cache/pi-fleet/runs/20260813-092715.PuYUDO/worker-3/findings-g3-north-star.md`（必要なら F2/F4 も）
- UI UX Pro Max: `/Users/yoshidatakumi/.agents/skills/ui-ux-pro-max/SKILL.md` と `scripts/search.py`
- impeccable: `/Users/yoshidatakumi/.agents/skills/impeccable/reference/critique.md` / `animate.md` / `bolder.md` / `distill.md`（読取のみ）

## 確定イシューと成功条件
- イシュー: 主張と関係が図で先に伝わらず、文章依存で読む気が削がれる
- 成功条件: 文章をほぼ読まずに、主張と関係が頭に入る
- ユーザー追加仮説: **AIスロップ（安全で地味なデフォルト美）も原因の一つ**
- ユーザー意図: LPそのものへの固執ではなく、**動的・視覚的に理解したい**（イシュー解決が大前提）

## 必須ツール利用
1. UI UX Pro Max を実際に叩く（説明だけで済ませない）:
```bash
python3 /Users/yoshidatakumi/.agents/skills/ui-ux-pro-max/scripts/search.py "decision explainer consulting diagram knowledge document" --design-system -p "visual-explain"
python3 /Users/yoshidatakumi/.agents/skills/ui-ux-pro-max/scripts/search.py "animation scroll storytelling comprehension" --domain ux
python3 /Users/yoshidatakumi/.agents/skills/ui-ux-pro-max/scripts/search.py "ai generated bland minimal landing anti-pattern" --domain style
```
必要なら追加クエリ可。出力の要点を成果物に引用。

2. impeccable の critique レンズで example-proposal を評価（コード変更・サーバー常駐不要）。
   Assessment A（デザインレビュー）を自分で行い、可能なら:
```bash
node /Users/yoshidatakumi/.agents/skills/impeccable/scripts/detect.mjs --json /Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/examples/example-proposal.html
```
を1回だけ試す（失敗したら理由を書いて続行）。

## やってほしいこと
1. 「地味さ」を分解: (a) AIスロップ（Inter系/紫グラデ/クリーム紙面/カード過多/弱いhierarchy） (b) コンサル静的美学 (c) 文章過多による視覚リズム欠如 (d) 図モジュール欠陥 — どれが主因か順位付け＋証拠
2. first viewport / スクロール中盤 / ask 付近で、認知負荷と視覚階層の具体欠陥を列挙（Nielsen/heuristics短く）
3. AIスロップ仮説の支持/反証（skeleton token・タイポ・余白・色のコード根拠）
4. 「見た目を強くする」が文章依存を悪化させうる失敗（seductive details）を明示
5. G3推奨（図＝本体＋条件付きステッパー）と矛盾しない **見た目改善の優先順位トップ5**（実装せず指針のみ）

## 禁止
コード変更・依存追加・サーバ起動・外部送信・dir外書込・実装。

## 成果物
`findings-g5-ux-ai-slop.md`

### 必須見出し
```
# G5 UX critique と AIスロップ
## 要約（5行以内）
## Pro Max / detector 実行ログ要約
## 地味さの要因順位（a–d）
## 画面区間ごとの欠陥
## AIスロップ仮説の証拠と反証
## 見た目強化が文章依存を悪化させるリスク
## 推奨優先順位トップ5（指針のみ）
## 結論（このグループ単体）
```
