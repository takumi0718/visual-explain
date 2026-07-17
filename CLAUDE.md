# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## リポジトリ概要

visual-explain は、複雑な提案・仕組み・調査結果を自己完結型の単一 HTML 資料へ変換する Agent Skill。実体は `skills/visual-explain/` 以下にあり、エージェント向けワークフロー定義（`SKILL.md`）と、決定論的な Python ビルド/検証パイプライン（`scripts/`）の二層で構成される。外部アセット・ビルド依存・追加パッケージは意図的に排除しており、ビルドと検証は Python 標準ライブラリだけで動く（開発時の pytest のみ例外）。

## コマンド

```bash
# 全テスト（666件前後）— 必ず scripts/ から python3 -m pytest のモジュール形式で実行する。
# テストは ve_components を cwd 経由で import するため、他ディレクトリからは collection が失敗する。
cd skills/visual-explain/scripts && python3 -m pytest tests -q

# 単一ファイル / 単一テスト
python3 -m pytest tests/test_matrix_renderer.py -q
python3 -m pytest tests/test_component_checker.py -k <name> -q

# checker のセルフテスト（fixture との診断メッセージ完全一致を検証）
bash skills/visual-explain/scripts/check.sh --selftest

# 資料のビルド（assembly IR JSON → 単一 HTML。全検査通過後のみ atomic write）
python3 skills/visual-explain/scripts/build_explainer.py --assembly <IR.json> --output <絶対パス>

# 生成 HTML の検証（経路自動検出・四層）。legacy 直書き文書のみ --type を明示
bash skills/visual-explain/scripts/check.sh <html>
bash skills/visual-explain/scripts/check.sh <html> --type <proposal|system|research>
```

CI はない。マージ前はテスト全通過と `check.sh --selftest` を手元で確認する。

## アーキテクチャ

### 不可侵の骨格（最重要の不変条件）

生成 HTML は `assets/skeleton.html` から作られ、可変になれるのは次の 3 種類のスロットだけ。

- `<!-- TITLE:BEGIN/END -->` と `<!-- CONTENT:BEGIN/END -->` の区間（生成コンテンツ）
- `VE-CONTROLLED:COMPONENT-STYLES / COMPONENT-SCRIPTS` スロット（ビルド時にハッシュ検証済みのコンポーネントアセットを注入）

それ以外の固定領域は checker が skeleton と SHA-256 でバイト一致比較する。つまり skeleton の 1 バイトの変更もチェッカー・全テスト・既存生成物に波及する。生成 HTML を手で直すことは禁止で、修正は常に IR を直して再ビルドする。

### ビルドパイプライン（`scripts/build_explainer.py` → `ve_components/`）

assembly IR（JSON）を入力に、次の単一経路で HTML を生成する。

```
validation.py（schema/契約検証・型付きセクション位置不変条件）
→ registry.py（relationship 宣言による候補絞り込み＝集合包含のみ・明示選択の検証）
→ document_sections.py（first-screen / closing / ask / 目次の信頼レンダラ）＋ renderers/（canonical）
→ assembly.py + flatten.py（canonical/compatibility/narrative/typed 共通の composer/flattener）
→ checker.py + document_checks.py + final_checks.py（最終検査・検査群③）→ 全通過後にのみ atomic write
```

- セクションは `first-screen`（先頭・ちょうど1）/ `narrative`（限定 HTML の散文）/ `canonical`（IR 宣言の図）/ `compatibility`（legacy HTML・`provenance` 必須）/ `ask` / `closing`（末尾・ちょうど1）で、読み順に並ぶ。`document.type` / `document.profile` は IR 必須で、first-screen wrapper の data 属性として自己表明する。
- `askType: "decision"` の ask を1件以上含む資料は、`document_sections.py` が closing の後に「判断の回収」パネル（`decision-panel`）を自動生成する。パネルは IR に書かず、DOM 上の decision ask option-id から `compute_ask_digest_from_pairs` で計算した digest を自己保持し、検査群③（後述）が最終文書段階で再照合する。
- canonical 12 形式: `matrix` / `flow` / `enumeration` / `chevron` / `pyramid` / `stairs` / `logic-tree` / `waterfall` / `slope` / `evidence-map` / `bars` / `kpi`。定義は `assets/components/registry.json`、CSS は `assets/components/*.css`。
- 設計判断: 関係（`relationship.kind`）と `capabilities` は IR で明示宣言する。散文からの推測・自動選択・ランキングはしない。canonical 生成の失敗は診断を返して報告し、compatibility へ暗黙に縮退しない。first-screen / closing / ask を narrative 生 HTML で書く旧方式は受理しない。
- 数値の扱い: waterfall は Decimal ＋ `displayPrecision` 必須で、binary float は fail-closed（`numeric.py`）。
- レンダラ発 SVG は二重ゲート（allowlist は `slope@1` のみ・要素/属性完全一致・viewBox 固定・整数座標。`test_renderer_svg_gate.py`）。

### 検証（`check.sh` — 四層）

依存ゼロのスタンドアロン検証器。埋め込み Python の legacy checker（固定領域一致・title 検証・禁止タグ/イベント属性/外部 URL/無限アニメーション/座標直書きの検出）を通した後、`check_component_html.py` がコンポーネント契約（registry 準拠・アセットハッシュ・semantic ID など）を検査する。component 文書では **検査群③**（`document_checks.py`）が文書型自己表明・h1 一意（first-screen 内）・closing 必須見出し・summary 描画・外部リンクのドメインマーカーに加え、decision-panel の存在（decision ask の有無との整合）・個数・closing 後の位置・digest 整合・自己表明属性（`data-ve-document-id` / `data-ve-schema-version` / `data-ve-document-path`）に加え、構造予約属性（`data-ve-section-kind` / `data-ve-ask-type` は `section`、`data-ve-panel-ask` は `li`）が指定タグ以外に付与されていないかを検証する（compatibility 等の非構造セクションに紛れ込んだ偽装パネル/ask の fail-closed）。component マーカーのない pre-migration 文書は legacy 型（proposal/system/research）を自動検出する。

### テスト構成（`scripts/tests/`）

fixture は命名規約を持つ: `component-valid-*.json` / `component-bad-*.json`（IR fixture）、`bad-*.html`（legacy checker 用）、`*-doc.html`（レンダリング済み文書）。期待される診断メッセージは日本語文字列の完全一致で検証されるため、診断文言を変えるとテストと `check.sh --selftest` の期待値更新が必要になる。

### ドキュメントの正本

- `skills/visual-explain/SKILL.md` — エージェント向けワークフローの正本（ゲート 3 条件・資料型・10 手順・保存規約）。パイプラインの挙動を変えたらここも更新する。
- `references/patterns.md` — IR の書き方と図の契約、完全な JSON 例、コンポーネント選択ガイド。
- `references/assembly.schema.json` / `component-ir.schema.json` — IR の schema。
- `references/design-system.md` — 目視確認の規範（描画規則はレンダラが保証する）。
- `docs/superpowers/specs/` と `plans/` — 日付つき設計文書。設計判断の経緯はここを見る。

## 規約

- 生成資料の出力先はリポジトリ内 `.visual-explain/`（git 管理外）。
- コミットは conventional commits ＋ `(ve)` スコープ（例: `feat(ve): ...`）。
- コードのコメント/docstring は英語、checker 診断とスキル文書は日本語。
- スキル利用時の外部依存ゼロは不変。Playwright / Selenium / Puppeteer / jsdom・npm パッケージ・pip パッケージを追加しない。開発時の JS テストは node 標準のみで実行する。
