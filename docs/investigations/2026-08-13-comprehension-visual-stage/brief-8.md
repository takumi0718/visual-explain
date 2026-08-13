# Worker 8 — G8: Mobile + 図品質 ブラウザ実描画（実装禁止）

## 作業ディレクトリ
この worker cwd のみに成果物・スクショを書いてよい。
対象: `/Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/examples/example-proposal.html`
URL: `file:///Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/examples/example-proposal.html`
先行調査: `/Users/yoshidatakumi/.cache/pi-fleet/runs/20260813-092715.PuYUDO/worker-2/findings-g2-diagram-craft.md`（矢印・改行根因）と `/Users/yoshidatakumi/.cache/pi-fleet/runs/20260813-092715.PuYUDO/worker-5/findings-g5-ux-ai-slop.md`

## ツール
`/Users/yoshidatakumi/.local/share/npm-global/bin/playwright-cli` を `-s=g8mob` で使う。file:// で開く。サーバ起動禁止。

```bash
/Users/yoshidatakumi/.local/share/npm-global/bin/playwright-cli -s=g8mob open "file:///Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/examples/example-proposal.html" --mobile
# または
/Users/yoshidatakumi/.local/share/npm-global/bin/playwright-cli -s=g8mob open "file:///Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/examples/example-proposal.html"
/Users/yoshidatakumi/.local/share/npm-global/bin/playwright-cli -s=g8mob resize 390 844
/Users/yoshidatakumi/.local/share/npm-global/bin/playwright-cli -s=g8mob screenshot --filename=mobile-first.png
# 承認地図・chevron/flow があればそこへスクロールして拡大スクショ
# 可能なら figure 内のコネクタ/矢印周辺を element screenshot
/Users/yoshidatakumi/.local/share/npm-global/bin/playwright-cli -s=g8mob close
```

## 検証仮説
1. G2: 三角と棒の分離は skip/loop レールに局在 → 実描画で見えるか（見えなければ「潜在欠陥」と明記）
2. 箇条書きの変な改行がモバイルで顕在化するか
3. ask がモバイルでピークとして見えるか／埋もれるか
4. 狭幅で図の可読性（横スクロール強制・切れ）があるか

## やってほしいこと
1. mobile first + 図区間 + ask のスクショ
2. 矢印/コネクタの目視（分離・ずれ・中心外れ）を具体座標/相対位置で記述
3. description 箇条書きの折れ方を観察
4. desktop(G7担当)と独立に、「モバイルでの最大の理解阻害」を1文
5. G2 結論の支持/反証/修正

## 禁止
コード変更・サーバ起動・外部送信・dir外書込。完了時 close。

## 成果物
- `findings-g8-browser-mobile-craft.md`
- スクショ PNG 複数

### 必須見出し
```
# G8 Mobile/図品質 実描画
## 要約（5行以内）
## 撮影一覧
## 矢印・コネクタ所見
## 改行・箇条書き所見
## ask / 可読性所見
## G2仮説の更新
## 結論（このグループ単体）
```
