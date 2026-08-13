> 保管先（正本）: `docs/investigations/2026-08-13-comprehension-visual-stage/`
>
> **方針裁定: 案A Visual-stage deck 採択（2026-08-13）**

# visual-explain 統合調査レポート — ほぼ読まず理解できるか

日付: 2026-08-13  
Run: `~/.cache/pi-fleet/runs/20260813-092715.PuYUDO`  
対象見本: `skills/visual-explain/examples/example-proposal.html`  
方法: 書籍ワークフロー（イシュー見極め→仮説→非依存調査）＋ UI UX Pro Max / impeccable レンズ＋ playwright-cli 実描画  
実装: なし（調査のみ）

---

## 1. 確定イシューと成功条件

| 項目 | 内容 |
|---|---|
| **イシュー** | 主張と関係が図で先に伝わる設計になっておらず、資料が文章依存になっている（読む気が削がれる） |
| **成功条件** | 文章をほぼ読まずに、主張と関係が頭に入る |
| **ユーザー意図の補正** | 「LPブランド」欲ではなく、**動的・視覚的に関係をつかみたい**。イシュー解決が大前提 |

### 仮説（改訂後）

- **H1′**: 動きが散文の表示順しか変えないなら成功条件に届かない。動きが図の状態・対応・因果を外在化し、その分の散文を削除できるなら、動的理解は直接寄与する。
- **H2**: コンサル形式そのものが悪ではなく、「図＝補助・文章＝本体」の運用／テンプレが本体のズレ。canonical 語彙ギャップも一部寄与。
- **H3′**: 同一図の semantic ID に結びついた有限状態を、手動・可逆・全体表示・静的 fallback で進めるときに動きは効く。入力は step 既定、scroll は同一状態機械の代替のみ。

---

## 2. 証拠の統合（G1–G8）

### 文章依存（G1・G7）

- 見本は 13 セクション中 **図ありは 2（15%）**。主張単位の大半が本文段落必須。
- 文字量でも図固有は約 1 割。canonical 見本自身が承認地図・Before/After を `unmigrated-format` の互換節のまま出荷し、直前 narrative が図主張を先取りする二重化がある。
- **Desktop 実描画**: 「h1 埋没」は反証（34.5px/700 で主役）。問題は first-screen〜narrative が**すべて文章**で、図到達まで視覚変調がないこと。承認地図はピークになるが **1212px で一望不能**。

### 図モジュール品質（G2・G8）

- 「三角と棒の分離」は CSS 貼り合わせ（flow skip / chevron loop）に局在する構造欠陥として妥当。
- **ただし本見本にはそのクラスが 0 件**。承認地図は SVG path+marker で健全（端点偏差 ≤0.5px）。欠陥の目視には別 fixture が必要。
- 箇条書き細断化（IR description→無条件ビュレット）も本見本では発火機会なし。
- **Mobile 最大障害は matrix**: `min-width:32rem` により第3列「トレードオフ」が +138px 画面外。判断のコスト情報が隠れる。

### 北極星と動き（G3・G4・G6）

- LPリズム単独・操作デモ単独・2モード併存は却下（理解優位の証拠弱・弱モデルフロア二重化）。
- 推奨骨格: **コンサル静的デック（図＝本体・主張1行）＋ 関係の時間展開に限る typed sequence**。
- G6 拡張名: **Visual-stage deck** — 経路スポットライト／同一座標ステートレンズ／デルタ累積を sequence 1系統に閉じる。入場 fade・全節 stagger・長文カルーセルは捨てる。
- 境界: `LLM=what` / `trusted library=語彙` / `build=how`。スクロール入場は既定 OFF。

### 見た目・AIスロップ（G5・G7）

- 地味さの主因順位（実描画更新後も）: **(c) 文章過多で視覚リズム欠如 > (d) 図の一望性・内部階層 > (b) Office青のコンサル既定美 > (a) AIスロップ**。
- AIスロップは **弱支持**（flat secondary hierarchy・均質カード）。典型記号（紫グラデ等）は皆無。系譜は Lovable 系より **PowerPoint/Office 既定青**。
- ask / decision-panel は figure と同色グレー矩形で**ピークでない**（mobile で特に埋没）。

---

## 3. So What?（方針への意味合い）

1. **先に解くべきは「肌」でも「LP化」でもなく、主従逆転（図＝本体）と、関係図の一望／時間展開。**
2. **動きは採用してよいが、対象を絞る。** 装飾スクロールではなく、同一図上の trace/compare/accumulate。
3. **見た目強化は主従逆転の後。** 図の視覚的重さ→書字階層→askピーク。色・フォント変更だけではイシューは解けない。
4. **品質フロア欠陥（矢印CSS）は並行バックログ。** 本見本では観測されず、優先度は文章依存・matrixモバイルより下。
5. **モバイル matrix は成功条件の直接ブロッカー。** 狭幅でトレードオフを隠すのは判断資料として不合格寄与が大きい。

---

## 4. 選択肢（方針裁定）

### 案 A — Visual-stage deck（推奨）

- 骨格: 図＝本体＋主張1行。動きは typed `sequence-stepper` 1系統（経路／差分／累積）。
- 既定で捨てる: 全節 fade、parallax、長文分割表示、LP単独モード。
- 最初の実装スコープ案（参考）: (1) 見本の narrative↔図 二重化解消と図先出し (2) 承認地図を1画面要約＋ステッパー (3) matrix モバイル縮退 (4) ask ピーク化（トークン差別化）
- 長所: 成功条件・弱モデルフロア・ユーザーの「動的理解」意図を同時に満たしやすい。
- 短所: ページ全体の「LP没入感」は弱い。

### 案 B — Single-canvas walkthrough（野心）

- 主要判断を1枚の persistent atlas に統合し、3〜6 scene を step/scroll。
- 長所: 文章セクション重複を構造的に削れる。
- 短所: 新規 IR/checker が大きい。弱モデルで品質急落リスク。A の比較評価後に昇格すべき。

### 案 C — 見た目先行（非推奨）

- 色・タイポ・入場モーションを先に刷新。
- 長所: 地味さの主観は早く変わる可能性。
- 短所: H1′ に反し、文章依存を残したまま seductive details 化しやすい。実描画でもピーク不足の主因は文章連打。

### 案 D — 現状維持＋局所バグのみ

- matrix モバイルと矢印CSS局所だけ直す。
- 長所: 小さい。
- 短所: 成功条件に届かない。

---

## 5. 推奨

**案 A（Visual-stage deck）を北極星に採択する。**

理由: 計測（G1）・認知科学比較（G3）・決定論境界（G4）・動的理解の再定義（G6）・実描画（G7/G8）が同じ方向を指す。ユーザーの「動的に理解したい」は入場演出ではなく **同一図の意味状態操作** として満たせる。

採択後の次工程（このレポートでは実行しない）: brainstorming → `docs/superpowers/specs/YYYY-MM-DD-visual-stage-deck-design.md` → writing-plans。

---

## 6. 成果物パス

| ID | ファイル |
|---|---|
| G1 | `worker-1/findings-g1-text-dependence.md` |
| G2 | `worker-2/findings-g2-diagram-craft.md` |
| G3 | `worker-3/findings-g3-north-star.md` |
| G4 | `worker-4/findings-g4-determinism-boundary.md` |
| G5 | `worker-5/findings-g5-ux-ai-slop.md` |
| G6 | `worker-6/findings-g6-dynamic-comprehension.md` |
| G7 | `worker-7/findings-g7-browser-desktop.md` + PNG |
| G8 | `worker-8/findings-g8-browser-mobile-craft.md` + PNG |
| 本統合 | `SYNTHESIS-visual-explain-comprehension-2026-08-13.md` |

UI UX Pro Max: `~/.agents/skills/ui-ux-pro-max/`（global 導入済）
