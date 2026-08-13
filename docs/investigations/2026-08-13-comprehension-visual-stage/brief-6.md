# Worker 6 — G6: LP的・動的理解パターン（イシュー解決前提・実装禁止）

## 作業ディレクトリ
この worker の cwd のみに成果物を書いてよい。
読む対象（read-only）:
- `/Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/examples/example-proposal.html`
- 先行調査: `/Users/yoshidatakumi/.cache/pi-fleet/runs/20260813-092715.PuYUDO/worker-3/findings-g3-north-star.md` `/Users/yoshidatakumi/.cache/pi-fleet/runs/20260813-092715.PuYUDO/worker-4/findings-g4-determinism-boundary.md` `/Users/yoshidatakumi/.cache/pi-fleet/runs/20260813-092715.PuYUDO/worker-1/findings-g1-text-dependence.md`（必須）／`/Users/yoshidatakumi/.cache/pi-fleet/runs/20260813-092715.PuYUDO/worker-2/findings-g2-diagram-craft.md`（任意）
- UI UX Pro Max: `/Users/yoshidatakumi/.agents/skills/ui-ux-pro-max`
- impeccable animate: `/Users/yoshidatakumi/.agents/skills/impeccable/reference/animate.md`
- SKILL.md 動き判定: `/Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/SKILL.md`

## ミッションの再定義（重要）
ユーザーは「LPブランド」が欲しいのではなく、**動的で視覚的に理解したい**。
G3は LPリズム単独を却下した。あなたの仕事は却下を盲信せず、
**「ほぼ読まず理解」を満たしつつ、LPが提供する“動的理解”の利点を取り込む具体パターン**を提案すること。
ゼロベースでよい。ただし弱いモデル品質フロア（決定論モジュール）と引き算は守る。

## 必須ツール利用
```bash
python3 /Users/yoshidatakumi/.agents/skills/ui-ux-pro-max/scripts/search.py "scroll storytelling explainer product education" --design-system -p "visual-explain-dynamic"
python3 /Users/yoshidatakumi/.agents/skills/ui-ux-pro-max/scripts/search.py "stepper progressive disclosure motion comprehension" --domain ux
python3 /Users/yoshidatakumi/.agents/skills/ui-ux-pro-max/scripts/search.py "landing page motion patterns" --domain landing
```
Webの読み取り専用調査は可。外部送信・アカウント操作は禁止。

## やってほしいこと
1. LPが「動的理解」に効く要素を分解（入場演出／スクロール物語／ステッパー／ピン留め／ハイライト追跡／ビフォーアフター切替 等）。各要素について:
   - 成功条件への寄与（高/中/低/負）
   - 文章依存を減らすか増やすか
   - 決定論モジュール化の難易度
   - AIスロップ化リスク
2. **採用候補パターンを3〜5個**（名前・読者体験・必要なIR語彙・禁止事項）。装飾スクロール入場は既定採用しない前提で、例外条件があれば書く
3. G3北極星（コンサル骨格＋条件付きステッパー）を **拡張**する案と、**置き換える**案を各1つ。推奨を1つ選び理由
4. 「動かすことで長文を小分けにする」アンチパターンを明示的に捨て、代わりに図が本体になる動的パターンを優先
5. 仮説改訂案: H1/H3 をユーザー意図（動的理解）を踏まえてどう言い直すべきか1段落

## 禁止
コード変更・依存追加・サーバ起動・実装・dir外書込。

## 成果物
`findings-g6-dynamic-comprehension.md`

### 必須見出し
```
# G6 LP的・動的理解パターン
## 要約（5行以内）
## Pro Max / 調査ログ要約
## LP要素の分解評価表
## 採用候補パターン（3〜5）
## G3拡張案 vs 置換案と推奨
## 捨てるアンチパターン
## 仮説の改訂提案
## 結論（このグループ単体）
```
