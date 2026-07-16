# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## リポジトリ概要

visual-explain は、複雑な提案・仕組み・調査結果を自己完結型の単一 HTML 資料へ変換する Agent Skill。実体は `skills/visual-explain/` 以下にあり、エージェント向けワークフロー定義（`SKILL.md`）と、決定論的な Python ビルド/検証パイプライン（`scripts/`）の二層で構成される。外部アセット・ビルド依存・追加パッケージは意図的に排除しており、ビルドと検証は Python 標準ライブラリだけで動く（開発時の pytest のみ例外）。

## コマンド

```bash
# 全テスト（578件）— 必ず scripts/ から python3 -m pytest のモジュール形式で実行する。
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
validation.py（schema/契約検証）
→ registry.py（relationship 宣言による候補絞り込み＝集合包含のみ・明示選択の検証）
→ renderers/（コンポーネントごとの信頼レンダラ）
→ assembly.py + flatten.py（canonical/compatibility/narrative 共通の composer/flattener）
→ checker.py + final_checks.py（最終検査）→ 全通過後にのみ atomic write
```

- セクションは `narrative`（限定 HTML の散文）/ `canonical`（IR 宣言の図）/ `compatibility`（legacy HTML・`provenance` 必須）の 3 種で、読み順に並ぶ。
- canonical 12 形式: `matrix` / `flow` / `enumeration` / `chevron` / `pyramid` / `stairs` / `logic-tree` / `waterfall` / `slope` / `evidence-map` / `bars` / `kpi`。定義は `assets/components/registry.json`、CSS は `assets/components/*.css`。
- 設計判断: 関係（`relationship.kind`）と `capabilities` は IR で明示宣言する。散文からの推測・自動選択・ランキングはしない。canonical 生成の失敗は診断を返して報告し、compatibility へ暗黙に縮退しない。
- 数値の扱い: waterfall は Decimal ＋ `displayPrecision` 必須で、binary float は fail-closed（`numeric.py`）。
- レンダラ発 SVG は二重ゲート（allowlist は `slope@1` のみ・要素/属性完全一致・viewBox 固定・整数座標。`test_renderer_svg_gate.py`）。

### 検証（`check.sh` — 四層）

依存ゼロのスタンドアロン検証器。埋め込み Python の legacy checker（固定領域一致・title 検証・禁止タグ/イベント属性/外部 URL/無限アニメーション/座標直書きの検出）を通した後、`check_component_html.py` がコンポーネント契約（registry 準拠・アセットハッシュ・semantic ID など）を検査する。component マーカーのない pre-migration 文書は legacy 型（proposal/system/research）を自動検出する。

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
