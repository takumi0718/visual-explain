# Worker 7 — G7: Desktop ブラウザ実描画検証（実装禁止）

## 作業ディレクトリ
この worker cwd のみに成果物・スクショを書いてよい。
対象 HTML（read-only）: `/Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/examples/example-proposal.html`
URL: `file:///Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/examples/example-proposal.html`
先行調査（読取）: `/Users/yoshidatakumi/.cache/pi-fleet/runs/20260813-092715.PuYUDO/worker-5/findings-g5-ux-ai-slop.md`

## ツール
`/Users/yoshidatakumi/.local/share/npm-global/bin/playwright-cli`（playwright-cli）を使う。サーバ起動は不要（file:// で開く）。
セッション名は衝突回避のため `-s=g7desk` を付ける。

手順の骨格:
```bash
/Users/yoshidatakumi/.local/share/npm-global/bin/playwright-cli -s=g7desk open "file:///Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/examples/example-proposal.html"
/Users/yoshidatakumi/.local/share/npm-global/bin/playwright-cli -s=g7desk resize 1440 900
/Users/yoshidatakumi/.local/share/npm-global/bin/playwright-cli -s=g7desk screenshot --filename=desktop-first-viewport.png
# スクロールして主要区間を撮る（first-screen後の narrative、承認地図 figure、matrix、ask、closing）
/Users/yoshidatakumi/.local/share/npm-global/bin/playwright-cli -s=g7desk eval "window.scrollTo(0, document.body.scrollHeight*0.25)"
/Users/yoshidatakumi/.local/share/npm-global/bin/playwright-cli -s=g7desk screenshot --filename=desktop-mid-1.png
# …必要分…
/Users/yoshidatakumi/.local/share/npm-global/bin/playwright-cli -s=g7desk close
```
スクショは cwd に残す。完了前にブラウザを close。

## 検証仮説（実描画で支持/反証）
G5主張:
1. first viewport の階層が平坦（h1 が埋没、テーマ切替が目立つ）
2. 文章連打で視覚ピークがない
3. 図がカードと同じグレー帯で埋没（視覚的重さ不足）
4. AIスロップ典型記号（紫グラデ等）は無いが flat hierarchy はある

## やってほしいこと
1. 上記スクショを撮り、各画像について目視所見を書く（コード推測で済まさない）
2. computed style を eval で採取: h1 / .subtitle / .decision / figure 背景色・font-size・主要な余白
3. 「図 vs カード」の背景色が同一か実測
4. G5 の要因順位 (c)>(d)>(b)>(a) を実描画で更新（維持/入れ替え）
5. 成功条件「ほぼ読まず理解」に対する desktop 上の最大障害を1文

## 禁止
コード変更・依存追加・HTTPサーバ起動・外部送信・dir外書込。

## 成果物
- `findings-g7-browser-desktop.md`
- スクショ PNG 複数（ファイル名を md から参照）

### 必須見出し
```
# G7 Desktop 実描画
## 要約（5行以内）
## 撮影一覧
## first viewport 所見
## スクロール区間所見
## 実測スタイル（computed）
## G5仮説の更新
## 結論（このグループ単体）
```
