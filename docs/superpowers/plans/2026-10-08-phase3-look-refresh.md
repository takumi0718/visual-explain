# Phase 3: 見た目の刷新（skeleton v4）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 「静かな精密」の方向で資料の見た目を磨く。第一画面（1280×900）に題名・結論・全体図・番号一覧が収まり、主ボタンが一目で分かり、テーマ切替はアイコンだけになり、スマホでは 16px 余白と案ごとのカードで読める（skeleton v4）。あわせて Phase 1 の解析器の取りこぼしと、Phase 2 までの小さな負債を片付ける。

**Architecture:** skeleton は v3 を `assets/skeleton-v3.html` に凍結し、最新 `assets/skeleton.html` を v4 にする。見た目の変更はすべて v4 の固定領域（CSS と固定 JS）に置く。component CSS（`matrix.css` / `chevron.css`）は**変更しない**: 資産ダイジェストは版をまたいで共有されるため、変えると v1〜v3 の生成物が `資産 'matrix.css' のダイジェストが一致しません` で落ちる。matrix のカード化と chevron の修正は、v4 skeleton の `[data-ve-section-kind] figure[data-ve-component=…]` という詳細度の高いセレクタで component CSS を上書きする。matrix レンダラは列見出しを各セルの `data-ve-col-label` に写し、カード表示の見出しに使う。反復ゲートとビルド報告の「図より前」は `metrics.visible_chars` という 1 つの数え方に揃える。

**Tech Stack:** Python 3 標準ライブラリのみ（`html.parser`, `re`, `dataclasses`, `json`）、node 標準のみ（既存の `node --check` テスト）、pytest（開発時のみ）、bash。目視確認だけローカルの headless Chrome を使う（依存にもテストにもしない）。

**Spec:** `docs/superpowers/specs/2026-10-07-visual-explain-review-loop-design.md` の「Phase 3 — 見た目の刷新（skeleton v4）」節、「確定した設計判断」、「Hard constraints」。

## Preflight: spec が決めていない点・spec 間の矛盾の裁定

実装者はこの裁定に従う。各タスクの要件に暗黙に含まれる。

1. **component CSS と registry は変えない。** spec は「matrix の component CSS を更新し、registry の digest を更新」と書くが、`checker.py` の `_validate_asset_slot` は埋め込み資産の本文ハッシュを現行 registry の digest と照合する。`tests/v2-proposal-doc.html` と凍結する v3 見本は旧 `matrix.css` を埋め込んでいるので、digest を変えると Hard constraint「既存の生成物は引き続き検査に通る」に反する。そこでカード化・chevron 修正・図キャプションの書体は v4 skeleton に置く（版ごとに自然に分かれる）。`matrix.css` の digest `fe9fd5f8…` と `chevron.css` の digest `afdb6d3b…` を Task 1 のテストで固定する。
2. **component CSS を上書きするセレクタは `[data-ve-section-kind]` で始める。** `main` / `html` / `body` / `:root` / `*` を含むセレクタに寸法系プロパティ（width / padding / margin / display など）を書くと、visual-stage 資料の「1212px skeleton」監査（`document_checks.check_visual_stage_css`）が落ちる（試作で確認済み）。canonical の図は必ず `section[data-ve-section-kind]` の中にあるので、`[data-ve-section-kind]` を前置すれば component CSS（`figure[data-ve-component=…] …`）より詳細度が 1 段高くなる。
3. **`main` の上余白を `var(--space-2)` に変える**ため、同じ監査の許可表 `permitted_skeleton_layout` に `("main", "padding", "var(--space-2) 0 var(--space-6)")` を足す。v3 以前の値（`var(--space-4) 0 var(--space-6)`）も残す（凍結した v3 で検査される文書があるため）。
4. **書体の段:** `--fs-hero: 1.953rem` / `--fs-h2: 1.563rem` / `--fs-h3: 1.25rem`（新設）/ `--fs-body: 1rem` / `--fs-small: .8rem` / `--fs-figure: .8rem`（図の中身は「補助」の段に寄せる）。`.claim` は h2 と同じ大きさだと見出しと競うので `--fs-h3` にする。component の図キャプション（各 CSS が `--fs-h2` を指定）は v4 skeleton で `--fs-h3` に上書きする（1.563rem のままだと全体図が 900px に収まらないことを試作で確認した）。
5. **主ボタンの文字色は `var(--bg)`。** spec は「白文字」だが、ダークテーマの `--accent` は淡い青（#85aef2）なので白では読めない。ライトでは `--bg` が白、ダークでは濃色になる。コントラストはライト 6.87 / ダーク 7.91（hover の `--accent-strong` 上は 9.43 / 10.08）で、監査表に足す。
6. **「①から答える」ボタンは足さない。** 現行に該当ボタンは無く、spec が定めるのはボタンの見た目だけである。主ボタンの部品 `.button-primary` を用意し、今回はコピーボタンだけに付ける。
7. **テーマ切替:** 保存キー（`data-theme-storage-key="visual-explain-theme"`）と「初回は OS、押したら保存」の既存挙動は変えない。「自動」は置かない。アイコンは**現在の**テーマを示す（ライトで太陽、ダークで月）。表示の切替は CSS が `aria-pressed` を見て行い、JS は `aria-pressed` と、`aria-label` / `title`（`テーマ: ライト（ダークに切替）` の形。現在の状態と押したときの動作の両方を言う）だけを更新する。JS 実行前の静的な文言は `テーマを切り替える`。SVG は固定領域に直接書く（checker の SVG 検査は content スロットだけが対象）。
8. **背景面（`--surface`）は全体図にだけ敷く。** 全体図は「直後に overview-nav が続く canonical セクション」の `figure` として CSS で特定する。問いカード（`.ask`）・回収パネル・legacy の `.figure`・`details.deep-dive` は `--bg` に 1px の `--border` に変える。図の中の部品（flow ノード、kpi カードなど）の面は変えない。全体図の中では matrix の張り出し（二層幅）を止める（`margin-inline: 0`）。
9. **番号一覧は 1 行に並べる**（`display: flex; flex-wrap: wrap`）。縦積みのままだと 1280×900 で一覧が折り返し線の下に出る。
10. **＋ ボタンの位置:** 左に余白（ボタン幅＋8px）があれば左外側（従来どおり）。無ければ、本文系ブロック（`p, li, h2, h3, blockquote`）は 52rem 以下の画面で右に `var(--space-4)` の余白を確保し、その余白の中に置く。`figure / table / pre` はブロック右上の**外側の上**に置く。どの場合も左端を画面内に収める。52rem は、本文カラム 45rem の左右に ボタン幅＋8px が確保できなくなる幅の上限である。
11. **chevron は横型だけを直す。** 6 段で折り返さないよう、42rem より広い画面では 1 行の grid（列は等分）にし、`subgrid` で全段の箱の高さを揃える。縦型は箱と説明文の対で 1 行になる配置なので、行ごとに高さが違うのは内容どおりであり、変えない。42rem 以下は component CSS の縦積みのまま。
12. **動きは `@media (prefers-reduced-motion: no-preference)` の中にだけ書く。** 対象は `button`、問いカードの選択肢、番号の丸印で、`background-color / border-color / color / box-shadow` の 150ms だけ。既存の reduce 用の規則は残す。
13. **Phase 1 の持ち越し課題の検証結果:**
    - 反復検査の解析器が `span` 以外の確度バッジ（例 `<strong class="certainty">`）の後ろを読み飛ばす — **実在**（`_skip` が `</span>` でしか減らない）。
    - 終了タグの省略（`<li>a<li>b</ul>`）で段落を取りこぼす — **実在**。
    - 同一文の検査が文末記号の無い文と図の中の文を無視する — **実在**。文末記号の無い末尾も 1 文として扱う。図については、narrative と compatibility の `figcaption` を対象に加える。canonical の図の中身（セル・ノード名）は、同じ語を複数の案に書くのが正当なので対象外のまま（裁定）。
    - 「図より前」の数が反復ゲートと metrics で違う — **実在**（ゲートは句読点を除いて文末記号を足し戻し、narrative の h2/h3/p/li だけ数える。metrics は h1 と結論も数える）。spec の定義「最初の図より前の本文（h1 と結論を除く）」に両方を揃え、数え方は `metrics.visible_chars`（空白以外の文字）1 つにする。見本の報告は `図より前 87 字` → `図より前 0 字` になる。
    - metrics が自己閉じの void タグ（`<br/>`）で親を pop する — **実在**（`HTMLParser` 既定の `handle_startendtag` が `handle_endtag` を呼ぶ）。
    - overview の番号 `n` が不正なとき診断が 2 つ出る — **実在**（`n は整数` の後に `連番` も出る）。
    - `last_h2` が図の後に戻らない — **実在**（図 → 図と続くと、2 つ目の図のキャプションが前の図の前にあった h2 と比べられる）。
    - `build_explainer` が `sections[0]` を first-screen と決め打ちしている — **実害なし、課題から外す。** `validate_assembly` は `_validate_document_structure` で first-screen が先頭にちょうど 1 つあることを検査し、`col.raise_if_any()` で失敗させるので、ビルドに届く request の `sections[0]` は必ず `FirstScreenSection` である。Task 7 で切り出す `compose_document` の docstring にこの前提を書く。
14. **`tests/test_narrative_sections.py` の手書きパイプライン**（overview-nav の挿入と narrative のアンカー id が抜けた複製）は、`build_explainer.compose_document` を切り出して呼ぶ形に置き換える。
15. **compatibility の `data-ve-blk` 禁止は parser で判定する。** 現行の正規表現 `\sdata-ve-blk\b` は本文テキストの「 data-ve-blk」や `data-ve-blk-note` 属性にも当たる。
16. **UI 評価（critique）の採点表は 19/36 の時点で記録が残っていない。** 本計画では 9 観点 × 0〜4 点（Task 8）で採点し、28 点以上を合格とする。
17. **目視確認:** 1280 幅は headless Chrome を直接使う。headless Chrome はウィンドウを約 500px 未満に縮められないため、390 幅は作業用ディレクトリに置いた iframe の枠（幅 390）で撮る。どちらもリポジトリに足さない。

## Global Constraints

- 外部依存ゼロ: build / check は Python 標準ライブラリのみ。JS テストは node 標準のみ。npm / pip / Playwright / Selenium / Puppeteer / jsdom を追加しない。headless Chrome は手元の目視確認だけに使い、テストや依存にしない。
- 既存配色のみ: skeleton の既存トークン（`--accent` / `--accent-strong` / `--positive` / `--text` / `--text-dim` / `--text-faint` / `--border` / `--border-strong` / `--surface` / `--bg` / `--focus`）と、それを `color-mix(in srgb, <token> 12%, var(--surface))` で薄めた色だけを使う。新しい色相・生の hex を足さない。番号の色は青系（`--accent`）。
- 余白（margin / padding / gap）は `0` / `var(--space-1)`〜`var(--space-7)` / `auto` / `inherit` だけ（`test_skeleton_audit.py` の格子監査）。
- skeleton は版ごとに 1 バイト不変。v1・v2・v3 は凍結ファイルで、checker は文書が宣言する版と照合する。CSP は変えない。UI の JS はすべて v4 skeleton の固定領域に置く。無限アニメーションは禁止。
- component CSS（`assets/components/*.css`）と `registry.json` は変更しない（裁定 1）。
- 生成 HTML の手編集禁止。見本の修正は IR → 再ビルド。見本の再ビルドはリポジトリルートを cwd にして相対パスで出力する: `python3 skills/visual-explain/scripts/build_explainer.py --assembly skills/visual-explain/examples/example-proposal.assembly.json --output skills/visual-explain/examples/example-proposal.html`
- 参考にした他者スキルの固有名を、コード・コメント・コミット・文書に書かない。仕組みは一般語（問いカード、指摘層、回収パネル、試問）で表す。
- コードのコメント / docstring は英語、checker 診断とスキル文書は日本語。診断文言は完全一致テストの対象。
- コミットは conventional commits ＋ `(ve)` スコープ。末尾に次の 2 行を付ける:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` / `Claude-Session: https://claude.ai/code/session_01NgfQq9eGiPhoY46Nmdb2Xv`
- テストは必ず `cd skills/visual-explain/scripts && python3 -m pytest tests -q` で実行する。各タスクの最後に全テストと `bash check.sh --selftest` を通す。着手時点の基準値: `1289 passed, 155 subtests passed`、`selftest: 35 passed, 0 failed`（ブランチ `feat/review-loop-phases-2-4`、HEAD `f3a680b`）。
- `tests/test_visual_stage_baseline_immutability.py` は過去の範囲（`af74036..8459865`）に固定されている。触らない。
- skeleton の編集は「old → new」の完全一致置換で行う。各 old 文字列は現行 skeleton にちょうど 1 回現れる（試作で確認済み）。

## Review Focus

- v1〜v3 で生成済みの資料（旧 `matrix.css` / `chevron.css` を埋め込んだもの）が、v4 の導入後も `check.sh` と `check_final_document` に合格すること → Task 1 の `test_v3_document_passes_both_checkers`、`test_component_assets_are_not_modified`、selftest の `v2-proposal-doc.html` / `v3-proposal-doc.html`。
- ダークテーマで主ボタン（`--accent` 面）の文字と hover 面の文字が読めること → Task 3 の `ContrastAuditTest` に足す 2 組（`bg`/`accent`、`bg`/`accent-strong`）。
- 列見出しを隠した matrix（`showColumnHeaders: false`）がスマホのカード表示で、作者が隠した見出しを勝手に出さないこと → Task 4 の `test_headerless_matrix_has_no_card_labels`。
- visual-stage 資料が v4 skeleton でも 1212px の幅監査を通り、凍結した v3 skeleton でも通り続けること → Task 2 の `test_frozen_v3_skeleton_still_satisfies_the_width_contract` と `test_no_layout_rule_targets_main_by_name`。
- 外部リンク（ドメイン札が付く）や確度バッジを含む本文と decision ask が図より前にある資料で、ビルドが報告する「図より前 M 字」と反復ゲートが数える字数が一致すること → Task 6 の `test_gate_and_report_count_the_same_text`。

---

## File Map

| File | Responsibility | Task |
|---|---|---|
| `skills/visual-explain/assets/skeleton-v3.html` (create) | 凍結した v3（現 `skeleton.html` のバイト完全コピー） | 1 |
| `skills/visual-explain/assets/skeleton.html` | v4: 版属性、書体と余白、操作部品、テーマ切替、モバイル、chevron、動き、＋ の位置 | 1–5 |
| `skills/visual-explain/scripts/ve_components/skeletons.py` | `LATEST_SKELETON_VERSION = 4` | 1 |
| `skills/visual-explain/scripts/ve_components/document_checks.py` | 1212px 監査の許可表に v4 の `main` padding | 2 |
| `skills/visual-explain/scripts/ve_components/renderers/matrix.py` | セルに `data-ve-col-label` | 4 |
| `skills/visual-explain/scripts/ve_components/metrics.py` | `visible_chars`、void タグ修正、first-screen を「図より前」から除外 | 6 |
| `skills/visual-explain/scripts/ve_components/repetition.py` | 解析器の書き直し、`chars_before_first_figure`、文末無し文、figcaption、`last_h2` のリセット | 6 |
| `skills/visual-explain/scripts/ve_components/validation.py` | overview の `n` の二重診断、compatibility の `data-ve-blk` を parser で判定 | 6, 7 |
| `skills/visual-explain/scripts/build_explainer.py` | `compose_document` の切り出し | 7 |
| `skills/visual-explain/scripts/check.sh` | selftest に `v3-proposal-doc.html` | 1 |
| `skills/visual-explain/scripts/tests/v3-proposal-doc.html` (create) | v3 生成物（現見本のバイト完全コピー） | 1 |
| `skills/visual-explain/scripts/tests/fixtures/bad-vs-duplicate-document-assertion-id.assembly.json` | 2 つ目の図のキャプションを別の文にする | 6 |
| `skills/visual-explain/scripts/tests/test_skeleton_versions.py` | v4、v3 凍結、資産 digest の固定、古いテスト名の改名 | 1 |
| `skills/visual-explain/scripts/tests/test_skeleton_audit.py` | 書体・第一画面・操作部品・テーマ・モバイル・chevron の固定、コントラスト、色の allowlist | 2–5 |
| `skills/visual-explain/scripts/tests/test_visual_stage_sequence_structure.py` | 幅監査の改変例を v4 の値に、v3 の継続合格 | 2 |
| `skills/visual-explain/scripts/tests/test_matrix_renderer.py` | 列ラベル | 4 |
| `skills/visual-explain/scripts/tests/test_matrix_stairs_sequence_renderer.py` | matrix の byte-exact ハッシュ更新 | 4 |
| `skills/visual-explain/scripts/tests/test_metrics.py`, `test_repetition.py`, `test_first_screen_section.py` | 持ち越し課題の回帰テスト | 6 |
| `skills/visual-explain/scripts/tests/test_review_blocks.py`, `test_narrative_sections.py` | parser 判定、実パイプライン呼び出し | 7 |
| `skills/visual-explain/examples/example-proposal.html` | 各タスクで再ビルド | 1–6 |
| `skills/visual-explain/SKILL.md`, `references/design-system.md`, `CLAUDE.md` | 文書 | 9 |

---

### Task 1: skeleton v4 の版上げと v3 の凍結

**Files:**
- Create: `skills/visual-explain/assets/skeleton-v3.html`, `skills/visual-explain/scripts/tests/v3-proposal-doc.html`
- Modify: `skills/visual-explain/assets/skeleton.html`（2 行目）, `skills/visual-explain/scripts/ve_components/skeletons.py`, `skills/visual-explain/scripts/check.sh`, `skills/visual-explain/examples/example-proposal.html`（再ビルド）
- Test: `skills/visual-explain/scripts/tests/test_skeleton_versions.py`

**Interfaces:**
- Consumes: `declared_skeleton_version(markup) -> int`、`resolve_skeleton(candidate, skeleton, assets_dir) -> str | None`、`skeleton_file(version, assets_dir) -> Path`、`build_document(...)` の版チェック（診断 `ビルドは最新の skeleton 版（N）だけを使えます: <版>`）。いずれも既存。
- Produces: `LATEST_SKELETON_VERSION == 4`。`skeleton_file(3) == assets/skeleton-v3.html`。fixture `tests/v3-proposal-doc.html`。以降のタスクは v4 の `assets/skeleton.html` を編集する。

- [ ] **Step 1: v3 を凍結し、v3 生成物を fixture として残す（どの変更よりも先に行う）**

```bash
cd skills/visual-explain
cp -p assets/skeleton.html assets/skeleton-v3.html
cp -p examples/example-proposal.html scripts/tests/v3-proposal-doc.html
shasum -a 256 assets/skeleton.html assets/skeleton-v3.html scripts/tests/v3-proposal-doc.html
```
Expected:
```
92629e1398a374c7090452ff5f5a8b03f4e18ce44e8103678843e84745031592  assets/skeleton.html
92629e1398a374c7090452ff5f5a8b03f4e18ce44e8103678843e84745031592  assets/skeleton-v3.html
26f25a122127858ec95582bd77b4fa499dfc6c2f585833b4b3a86eadc6310b9a  scripts/tests/v3-proposal-doc.html
```
ハッシュが違う場合は作業ツリーが `f3a680b` と異なる。止めて報告する。

- [ ] **Step 2: 失敗するテストを書く** — `tests/test_skeleton_versions.py` を次の内容で置き換える

```python
"""Versioned skeleton resolution: each document is checked against the skeleton it declares."""
from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from build_explainer import build_document
from first_screen_ir import assembly
from ve_components.checker import check_final_document
from ve_components.diagnostics import ContractError
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.skeletons import (
    LATEST_SKELETON_VERSION,
    declared_skeleton_version,
    resolve_skeleton,
    skeleton_file,
)

SKILL = Path(__file__).resolve().parents[2]
ASSETS = SKILL / "assets"
COMPONENTS = ASSETS / "components"
LATEST = (ASSETS / "skeleton.html").read_text("utf-8")
V1 = (ASSETS / "skeleton-v1.html").read_text("utf-8")
V2 = (ASSETS / "skeleton-v2.html").read_text("utf-8")
V3 = (ASSETS / "skeleton-v3.html").read_text("utf-8")
REGISTRY = load_registry(COMPONENTS / "registry.json")
TESTS = Path(__file__).resolve().parent
CHECK = TESTS.parent / "check.sh"

FROZEN_SHA256 = {
    "skeleton-v1.html": "7512debf49653053249be88218a2025a2d5374e2c5b289784fb47a0f5d1f720b",
    "skeleton-v2.html": "1f58a12aa50e73a08f4ae12f7ef70bc271f39ebfe53a9910eb9ab14104f03125",
    "skeleton-v3.html": "92629e1398a374c7090452ff5f5a8b03f4e18ce44e8103678843e84745031592",
}
# Asset digests are shared by every skeleton version: changing a component CSS
# file would fail every older document that embeds it (preflight ruling 1).
FROZEN_ASSET_DIGESTS = {
    "matrix.css": "fe9fd5f86063dcb93790a9549a7630a162d674082446e2dd5f86c540bd6b692c",
    "chevron.css": "afdb6d3b748a45e67714851bdb8033993fadd7bc27a9a5295f46fef77c6720f8",
}


class SkeletonVersionTest(unittest.TestCase):
    def test_latest_declares_latest_version(self) -> None:
        self.assertEqual(declared_skeleton_version(LATEST), LATEST_SKELETON_VERSION)
        self.assertEqual(LATEST_SKELETON_VERSION, 4)

    def test_missing_attribute_means_v1(self) -> None:
        self.assertEqual(declared_skeleton_version(V1), 1)

    def test_frozen_versions_declare_themselves(self) -> None:
        self.assertEqual(declared_skeleton_version(V2), 2)
        self.assertEqual(declared_skeleton_version(V3), 3)

    def test_frozen_skeletons_are_byte_identical_to_their_release(self) -> None:
        for name, digest in FROZEN_SHA256.items():
            data = (ASSETS / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest, name)

    def test_skeleton_file_mapping(self) -> None:
        self.assertEqual(skeleton_file(4, ASSETS), ASSETS / "skeleton.html")
        self.assertEqual(skeleton_file(3, ASSETS), ASSETS / "skeleton-v3.html")
        self.assertEqual(skeleton_file(2, ASSETS), ASSETS / "skeleton-v2.html")
        self.assertEqual(skeleton_file(1, ASSETS), ASSETS / "skeleton-v1.html")

    def test_resolve_returns_given_when_versions_match(self) -> None:
        self.assertIs(resolve_skeleton(LATEST, LATEST, ASSETS), LATEST)

    def test_resolve_loads_frozen_skeletons(self) -> None:
        self.assertEqual(resolve_skeleton(V1, LATEST, ASSETS), V1)
        self.assertEqual(resolve_skeleton(V2, LATEST, ASSETS), V2)
        self.assertEqual(resolve_skeleton(V3, LATEST, ASSETS), V3)

    def test_resolve_unknown_version_is_none(self) -> None:
        doc = LATEST.replace('data-ve-skeleton="4"', 'data-ve-skeleton="9"', 1)
        self.assertIsNone(resolve_skeleton(doc, LATEST, ASSETS))

    def test_latest_first_screen_has_no_viewport_min_height(self) -> None:
        rule = next(line for line in LATEST.splitlines() if line.strip().startswith(".first-screen {"))
        self.assertNotIn("min-height", rule)


class BackwardCompatibilityTest(unittest.TestCase):
    def test_v1_rendered_fixtures_still_pass_against_latest(self) -> None:
        for name in ("matrix-doc-all-notations.html", "chevron-doc.html"):
            raw = (TESTS / name).read_text("utf-8")
            self.assertEqual(declared_skeleton_version(raw), 1, name)
            diags = check_final_document(raw, LATEST, REGISTRY, components_dir=COMPONENTS)
            self.assertEqual([d.message for d in diags], [], name)

    def _passes_both_checkers(self, name: str, version: int) -> None:
        path = TESTS / name
        raw = path.read_text("utf-8")
        self.assertEqual(declared_skeleton_version(raw), version)
        diags = check_final_document(raw, LATEST, REGISTRY, components_dir=COMPONENTS)
        self.assertEqual([d.message for d in diags], [])
        proc = subprocess.run(["bash", str(CHECK), str(path)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_v2_document_passes_both_checkers(self) -> None:
        self._passes_both_checkers("v2-proposal-doc.html", 2)

    def test_v3_document_passes_both_checkers(self) -> None:
        self._passes_both_checkers("v3-proposal-doc.html", 3)

    def test_component_assets_are_not_modified(self) -> None:
        registry = json.loads((COMPONENTS / "registry.json").read_text("utf-8"))
        digests = {asset["path"]: asset["digest"]
                   for component in registry["components"] for asset in component["assets"]}
        for path, digest in FROZEN_ASSET_DIGESTS.items():
            self.assertEqual(digests[path], digest, path)
            self.assertEqual(hashlib.sha256((COMPONENTS / path).read_bytes()).hexdigest(), digest, path)

    def test_unknown_version_document_fails(self) -> None:
        raw = (TESTS / "matrix-doc-all-notations.html").read_text("utf-8").replace(
            '<html lang="ja"', '<html lang="ja" data-ve-skeleton="9"', 1)
        diags = check_final_document(raw, LATEST, REGISTRY, components_dir=COMPONENTS)
        self.assertIn("未知の skeleton 版です: 9", [d.message for d in diags])


class BuildUsesLatestSkeletonTest(unittest.TestCase):
    def test_build_refuses_frozen_skeleton(self) -> None:
        raw = assembly({"conclusion": "限定対象で開始する。"})
        with self.assertRaises(ContractError) as ctx:
            build_document(raw, REGISTRY, TRUSTED_RENDERERS, V3, COMPONENTS, document_path="x.html")
        self.assertEqual([d.message for d in ctx.exception.diagnostics],
                         ["ビルドは最新の skeleton 版（4）だけを使えます: 3"])

    def test_built_document_declares_latest_version(self) -> None:
        raw = assembly({"conclusion": "限定対象で開始する。"})
        html = build_document(raw, REGISTRY, TRUSTED_RENDERERS, LATEST, COMPONENTS, document_path="x.html")
        self.assertEqual(declared_skeleton_version(html), 4)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_skeleton_versions.py -q`
Expected: FAIL（`LATEST_SKELETON_VERSION` が 3、`skeleton_file(4)` が `skeleton-v4.html` を返す、など）。

- [ ] **Step 4: v4 に上げる**

`assets/skeleton.html` の 2 行目:
```html
<html lang="ja" data-theme-storage-key="visual-explain-theme" data-ve-skeleton="3">
```
→
```html
<html lang="ja" data-theme-storage-key="visual-explain-theme" data-ve-skeleton="4">
```
`ve_components/skeletons.py`: `LATEST_SKELETON_VERSION = 3` → `LATEST_SKELETON_VERSION = 4`。

`check.sh` の `structure_cases` で `("v2-proposal-doc.html", ()),` の次の行に足す:
```python
        ("v3-proposal-doc.html", ()),
```

- [ ] **Step 5: 見本を再ビルドして通す**

```bash
cd "$(git rev-parse --show-toplevel)"
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/examples/example-proposal.assembly.json \
  --output skills/visual-explain/examples/example-proposal.html
cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest
```
Expected: `OK: …` と `本文 1373 字 / 図より前 87 字 / 図 3 点`。全テスト PASS（失敗 0）。`selftest: 36 passed, 0 failed`。

- [ ] **Step 6: Commit**

```bash
git add skills/visual-explain/assets/skeleton-v3.html skills/visual-explain/assets/skeleton.html \
  skills/visual-explain/scripts/ve_components/skeletons.py skills/visual-explain/scripts/check.sh \
  skills/visual-explain/scripts/tests/test_skeleton_versions.py skills/visual-explain/scripts/tests/v3-proposal-doc.html \
  skills/visual-explain/examples/example-proposal.html
git commit -m "feat(ve): freeze skeleton v3 and start skeleton v4"
```

---

### Task 2: 書体の段・余白・第一画面の収まり

**Files:**
- Modify: `skills/visual-explain/assets/skeleton.html`（`<style>` 内）
- Modify: `skills/visual-explain/scripts/ve_components/document_checks.py`（`permitted_skeleton_layout`）
- Modify: `skills/visual-explain/examples/example-proposal.html`（再ビルド）
- Test: `skills/visual-explain/scripts/tests/test_skeleton_audit.py`, `skills/visual-explain/scripts/tests/test_visual_stage_sequence_structure.py`

**Interfaces:**
- Consumes: Task 1 の v4 skeleton。
- Produces: トークン `--fs-h3`。セレクタ規約「component CSS の上書きは `[data-ve-section-kind]` で始める」（Task 4・5 も従う）。テスト用ヘルパ `_style()`（`test_skeleton_audit.py` のモジュール関数。skeleton の `<style>` の中身を返す）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_skeleton_audit.py` の `_HEX = re.compile(...)` の直前に足す:
```python
def _style():
    return SKELETON.split("<style>", 1)[1].split("</style>", 1)[0]
```

既存の `class TypeScaleTest` を丸ごと次で置き換える:
```python
class TypeScaleTest(unittest.TestCase):
    def test_five_step_scale_tokens_exist(self):
        for token in ("--fs-hero: 1.953rem", "--fs-h2: 1.563rem", "--fs-h3: 1.25rem", "--fs-body: 1rem",
                      "--fs-small: .8rem", "--fs-figure: .8rem"):
            self.assertIn(token, SKELETON)

    def test_headings_and_captions_use_the_scale(self):
        style = _style()
        self.assertIn("h1 { margin: 0; font-size: var(--fs-hero);", style)
        self.assertIn("h3 { font-size: var(--fs-h3); font-weight: 700; line-height: var(--lh-heading);", style)
        self.assertIn(".claim { margin-bottom: var(--space-2); font-size: var(--fs-h3); font-weight: 700; }", style)
        self.assertIn("[data-ve-section-kind] figure[data-ve-component] > figcaption[class] "
                      "{ font-size: var(--fs-h3); }", style)


class FirstScreenFoldTest(unittest.TestCase):
    """v4: h1, conclusion, overview figure and markers fit the first 900px at 1280px."""

    def test_sections_use_space_5(self):
        style = _style()
        self.assertIn("section { min-width: 0; margin-block: var(--space-5); }", style)
        self.assertNotIn("var(--space-7)", style)

    def test_no_leading_whitespace_above_h1(self):
        style = _style()
        self.assertIn("main { width: min(100% - var(--space-4), var(--w-narrative)); margin: 0 auto; "
                      "padding: var(--space-2) 0 var(--space-6); }", style)
        self.assertIn('[data-ve-section-kind="first-screen"] { margin-block: 0 var(--space-3); }', style)
        self.assertIn(".first-screen { display: grid; gap: var(--space-2); padding: 0; margin-block: 0;", style)

    def test_overview_figure_hugs_its_markers(self):
        style = _style()
        self.assertIn('[data-ve-section-kind="canonical"]:has(+ [data-ve-section-kind="overview-nav"]) '
                      "{ margin-bottom: var(--space-2); }", style)
        self.assertIn(".overview-markers ol { list-style: none; margin: 0; padding: 0; display: flex; "
                      "flex-wrap: wrap; gap: var(--space-1) var(--space-3); }", style)

    def test_surface_is_only_under_the_overview_figure(self):
        style = _style()
        self.assertIn('[data-ve-section-kind="canonical"]:has(+ [data-ve-section-kind="overview-nav"]) > figure '
                      "{ margin-block: 0; padding: var(--space-3); background: var(--surface); "
                      "border-radius: var(--radius); }", style)
        for selector in (".ask {", ".decision-panel {", "details.deep-dive {", ".figure {"):
            rule = next(line for line in style.splitlines() if line.strip().startswith(selector))
            self.assertNotIn("var(--surface)", rule, selector)
            self.assertIn("1px solid var(--border)", rule, selector)

    def test_no_layout_rule_targets_main_by_name(self):
        # The visual-stage 1212px audit treats any selector naming main/html/body/:root
        # as main sizing; component overrides must use the [data-ve-section-kind] prefix.
        for chunk in _style().split("}"):
            if "{" not in chunk:
                continue
            selector = chunk.rsplit("{", 1)[0].split("{")[-1].strip()
            if selector in {"main", "html", "body", ":root", "*", "*, *::before, *::after"} \
                    or selector.startswith((":root", "@media")):
                continue
            self.assertIsNone(re.search(r"(?<![-\w])(main|html|body)(?![-\w])|:root", selector), selector)
```

`tests/test_visual_stage_sequence_structure.py` の `test_width_contract_rechecks_skeleton_main_content_width_and_inline_padding` のパラメタのうち
```python
        SKELETON.replace(
            "padding: var(--space-4) 0 var(--space-6)",
            "padding: var(--space-4) 5rem var(--space-6)",
        ),
```
を次にする:
```python
        SKELETON.replace(
            "padding: var(--space-2) 0 var(--space-6)",
            "padding: var(--space-2) 5rem var(--space-6)",
        ),
```
同じファイルの末尾（`if __name__` があればその前）に足す:
```python
def test_frozen_v3_skeleton_still_satisfies_the_width_contract() -> None:
    v3 = (ROOT / "assets" / "skeleton-v3.html").read_text("utf-8")
    assert not [item.message for item in check_visual_stage_css(VISUAL_STAGE_CSS, v3)
                if "skeleton" in item.message]
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_skeleton_audit.py tests/test_visual_stage_sequence_structure.py -q`
Expected: FAIL（`TypeScaleTest`・`FirstScreenFoldTest` の各テスト、置換が当たらない幅監査パラメタ）。`test_frozen_v3_…` と `test_no_layout_rule_targets_main_by_name` はこの時点で PASS してよい（v3 の値は許可表にあり、`main` を含む上書きはまだ無い）。

- [ ] **Step 3: skeleton の `<style>` を置換する（各 old はちょうど 1 回現れる）**

(a) 書体トークン
```
      --fs-hero: 1.875rem; --fs-h2: 1.25rem; --fs-body: 1rem; --fs-small: .8125rem; --fs-figure: .875rem;
```
→
```
      --fs-hero: 1.953rem; --fs-h2: 1.563rem; --fs-h3: 1.25rem; --fs-body: 1rem; --fs-small: .8rem; --fs-figure: .8rem;
```

(b) main と section
```
    main { width: min(100% - var(--space-4), var(--w-narrative)); margin: 0 auto; padding: var(--space-4) 0 var(--space-6); }
    section { min-width: 0; margin-block: var(--space-7); }
```
→
```
    main { width: min(100% - var(--space-4), var(--w-narrative)); margin: 0 auto; padding: var(--space-2) 0 var(--space-6); }
    section { min-width: 0; margin-block: var(--space-5); }
```

(c) 見出し
```
    h1 { font-size: var(--fs-hero); font-weight: 700; line-height: var(--lh-heading); max-width: var(--w-narrative); }
    h2 { font-size: var(--fs-h2); font-weight: 700; line-height: var(--lh-heading); max-width: var(--w-narrative); }
```
→
```
    h1 { margin: 0; font-size: var(--fs-hero); font-weight: 700; line-height: var(--lh-heading); max-width: var(--w-narrative); }
    h2 { font-size: var(--fs-h2); font-weight: 700; line-height: var(--lh-heading); max-width: var(--w-narrative); }
    h3 { font-size: var(--fs-h3); font-weight: 700; line-height: var(--lh-heading); max-width: var(--w-narrative); }
```

(d) 第一画面
```
    .first-screen { display: grid; gap: var(--space-3); padding: var(--space-4) 0 var(--space-2); margin-block: 0; background: transparent; border-left: 0; }
```
→
```
    .first-screen { display: grid; gap: var(--space-2); padding: 0; margin-block: 0; background: transparent; border-left: 0; }
    [data-ve-section-kind="first-screen"] { margin-block: 0 var(--space-3); }
```

(e) 全体図と番号一覧の間隔・全体図の面・図キャプション
```
    [data-ve-section-kind="first-screen"] + [data-ve-section-kind="canonical"], [data-ve-section-kind="canonical"] + [data-ve-section-kind="overview-nav"] { margin-top: var(--space-2); }
```
→
```
    [data-ve-section-kind="first-screen"] + [data-ve-section-kind="canonical"] { margin-top: var(--space-3); }
    [data-ve-section-kind="canonical"]:has(+ [data-ve-section-kind="overview-nav"]) { margin-bottom: var(--space-2); }
    [data-ve-section-kind="canonical"] + [data-ve-section-kind="overview-nav"] { margin-top: var(--space-2); }
    [data-ve-section-kind="canonical"]:has(+ [data-ve-section-kind="overview-nav"]) > figure { margin-block: 0; padding: var(--space-3); background: var(--surface); border-radius: var(--radius); }
    [data-ve-section-kind="canonical"]:has(+ [data-ve-section-kind="overview-nav"]) > figure .ve-matrix-scroll { margin-inline: 0; }
    [data-ve-section-kind] figure[data-ve-component] > figcaption[class] { font-size: var(--fs-h3); }
```

(f) 番号一覧
```
    .overview-markers ol { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-1); }
```
→
```
    .overview-markers ol { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: var(--space-1) var(--space-3); }
```

(g) 主張行
```
    .claim { margin-bottom: var(--space-2); font-size: var(--fs-h2); font-weight: 700; }
```
→
```
    .claim { margin-bottom: var(--space-2); font-size: var(--fs-h3); font-weight: 700; }
```

(h) legacy の図
```
    .figure { position: relative; min-width: 0; margin: var(--space-3) 0; padding: var(--space-3); background: var(--surface); border: 0; border-radius: .5rem; overflow: auto; }
```
→
```
    .figure { position: relative; min-width: 0; margin: var(--space-3) 0; padding: var(--space-3); background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); overflow: auto; }
```

(i) 折りたたみ
```
    details.deep-dive { margin-top: var(--space-2); padding: var(--space-1) var(--space-2); background: var(--surface); border: 0; border-radius: .4rem; }
```
→
```
    details.deep-dive { margin-top: var(--space-2); padding: var(--space-1) var(--space-2); background: transparent; border: 1px solid var(--border); border-radius: var(--radius); }
```

(j) 問いカード
```
    .ask { max-width: var(--w-narrative); margin: var(--space-3) 0; padding: var(--space-3); background: var(--surface); border: 1px solid var(--border); border-radius: .5rem; }
```
→
```
    .ask { max-width: var(--w-narrative); margin: var(--space-3) 0; padding: var(--space-3); background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); }
```

(k) 回収パネル
```
    .decision-panel { max-width: var(--w-narrative); padding: var(--space-3); background: var(--surface); border-radius: .5rem; }
```
→
```
    .decision-panel { max-width: var(--w-narrative); padding: var(--space-3); background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); }
```

- [ ] **Step 4: 1212px 監査の許可表に v4 の値を足す**

`ve_components/document_checks.py` の `permitted_skeleton_layout` で
```python
        ("main", "padding", "var(--space-4) 0 var(--space-6)"),
```
の直後に 1 行足す:
```python
        ("main", "padding", "var(--space-2) 0 var(--space-6)"),
```

- [ ] **Step 5: 見本を再ビルドして通す**

```bash
cd "$(git rev-parse --show-toplevel)"
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/examples/example-proposal.assembly.json \
  --output skills/visual-explain/examples/example-proposal.html
cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest
```
Expected: `本文 1373 字 / 図より前 87 字 / 図 3 点`。全テスト PASS。`selftest: 36 passed, 0 failed`。

- [ ] **Step 6: 目視で第一画面の収まりを確かめる（テストにしない）**

```bash
SCRATCH="$(mktemp -d)"
DOC="$(git rev-parse --show-toplevel)/skills/visual-explain/examples/example-proposal.html"
perl -e 'alarm 40; exec @ARGV' "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-first-run --user-data-dir="$SCRATCH/profile" \
  --window-size=1280,900 --screenshot="$SCRATCH/fold-1280.png" "file://$DOC"
echo "$SCRATCH/fold-1280.png"
```
画像を開いて確認する: h1 の上の空白は約 70px 以内、h1 → 結論ボックス → 面を敷いた全体図 → ①②③ の 1 行が 900px 以内に全部見える（試作では番号一覧の下端が約 880px）。図キャプションは h2 より小さい。収まらない場合は止めて報告する（CSS 値を独断で変えない）。

- [ ] **Step 7: Commit**

```bash
git add skills/visual-explain/assets/skeleton.html skills/visual-explain/scripts/ve_components/document_checks.py \
  skills/visual-explain/scripts/tests/test_skeleton_audit.py skills/visual-explain/scripts/tests/test_visual_stage_sequence_structure.py \
  skills/visual-explain/examples/example-proposal.html
git commit -m "feat(ve): tighten the type scale and fit the first screen above the fold"
```

---

### Task 3: 操作部品・テーマ切替・動き

**Files:**
- Modify: `skills/visual-explain/assets/skeleton.html`（`<style>`、テーマボタンの HTML、`FIXED THEME CONTROL JS`、`FIXED DECISION COLLECTION JS`）
- Modify: `skills/visual-explain/examples/example-proposal.html`（再ビルド）
- Test: `skills/visual-explain/scripts/tests/test_skeleton_audit.py`

**Interfaces:**
- Consumes: Task 2 の `_style()`、`DecisionOptionCardInteractionTest._collection_block`（既存）。
- Produces: CSS 部品 `.button-primary`、`.theme-toggle`、`.theme-icon-sun` / `.theme-icon-moon`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_skeleton_audit.py` の `PAIRS` で `("accent-strong", "surface", 4.5, "指摘の番号札/面"),` の直後に 2 行足す:
```python
    ("bg", "accent", 4.5, "主ボタン文字/accent 面"),
    ("bg", "accent-strong", 4.5, "主ボタン文字/hover 面"),
```

`test_semantic_colors_only_on_judgment_selectors` の `allowed` タプルの末尾（`"[data-ve-annotated]",` の後）に足す:
```python
            # 主ボタン（accent = この資料で最初に押す操作。コピーだけに付ける）
            ".button-primary",
```

ファイル末尾の `if __name__ == "__main__":` の前に足す:
```python
class ControlsV4Test(unittest.TestCase):
    _collection_block = DecisionOptionCardInteractionTest._collection_block

    def test_primary_and_secondary_buttons(self):
        style = _style()
        self.assertIn("button { font: inherit; color: inherit; background: transparent; "
                      "border: 1px solid var(--border); border-radius: var(--radius);", style)
        self.assertIn(".button-primary { background: var(--accent); border-color: var(--accent); "
                      "color: var(--bg); font-weight: 700; }", style)
        self.assertIn(".button-primary:hover:not(:disabled) { background: var(--accent-strong); "
                      "border-color: var(--accent-strong); }", style)
        self.assertIn("copyButton.className = 'button-primary';", self._collection_block())

    def test_option_hover_and_selected(self):
        style = _style()
        self.assertIn(".ask-options [data-ask-option]:not([data-ask-withdrawn]):not([data-ask-selected]):hover "
                      "{ border-color: var(--text-faint); }", style)
        self.assertIn(".ask-options [data-ask-option][data-ask-selected] { border-color: var(--accent); "
                      "box-shadow: inset 0 0 0 1px var(--accent);", style)

    def test_dead_no_default_reason_selector_removed(self):
        self.assertNotIn("ask-no-default-reason", _style())

    def test_js_only_note_hidden_after_init(self):
        self.assertIn("panel.querySelectorAll('.panel-note').forEach((note) => { note.hidden = true; });",
                      self._collection_block())

    def test_transitions_respect_reduced_motion(self):
        style = _style()
        self.assertEqual(style.count("transition:"), 1)
        gate = style.split("@media (prefers-reduced-motion: no-preference) {", 1)
        self.assertEqual(len(gate), 2)
        self.assertIn("transition: background-color 150ms ease, border-color 150ms ease, "
                      "color 150ms ease, box-shadow 150ms ease;", gate[1].split("\n    }", 1)[0])
        self.assertNotIn("infinite", style)


class ThemeToggleTest(unittest.TestCase):
    def _theme_js(self):
        return SKELETON.split("/* FIXED THEME CONTROL JS: DO NOT MODIFY. */", 1)[1].split("</script>", 1)[0]

    def test_icon_only_round_button(self):
        button = re.search(r"<button[^>]*data-theme-toggle[^>]*>(.*?)</button>", SKELETON, re.S)
        self.assertIsNotNone(button)
        tag = button.group(0).split(">", 1)[0]
        for attr in ('class="theme-toggle"', 'aria-label="テーマを切り替える"',
                     'title="テーマを切り替える"', 'aria-pressed="false"'):
            self.assertIn(attr, tag)
        inner = button.group(1)
        self.assertEqual(re.sub(r"<[^>]+>", "", inner).strip(), "")
        self.assertIn('class="theme-icon-sun"', inner)
        self.assertIn('class="theme-icon-moon"', inner)
        self.assertEqual(inner.count('aria-hidden="true"'), 2)
        self.assertNotIn("#", inner)
        style = _style()
        self.assertIn(".theme-toggle { display: inline-grid; place-items: center; width: 32px; height: 32px; "
                      "padding: 0; border-radius: 50%; color: var(--text-dim); }", style)
        self.assertIn('.theme-toggle[aria-pressed="true"] .theme-icon-sun, '
                      '.theme-toggle[aria-pressed="false"] .theme-icon-moon { display: none; }', style)

    def test_label_describes_state_and_action(self):
        js = self._theme_js()
        self.assertIn("const text = `テーマ: ${label(current)}（${label(next)}に切替）`;", js)
        self.assertIn("button.setAttribute('aria-label', text);", js)
        self.assertIn("button.setAttribute('title', text);", js)
        self.assertIn("button.setAttribute('aria-pressed', String(current === 'dark'));", js)
        self.assertNotIn("textContent", js)

    def test_two_states_only_and_storage_key_kept(self):
        self.assertIn('data-theme-storage-key="visual-explain-theme"', SKELETON)
        js = self._theme_js()
        self.assertIn("window.localStorage.setItem(root.dataset.themeStorageKey, theme);", js)
        self.assertNotIn("auto", js)
        self.assertNotIn("removeItem", js)
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_skeleton_audit.py -q`
Expected: FAIL（`ControlsV4Test`・`ThemeToggleTest` の各テスト）。コントラスト 2 組は既に満たすので PASS してよい。

- [ ] **Step 3: `<style>` を置換する**

(a) ボタンの基本形と主ボタン
```
    button { font: inherit; color: inherit; background: var(--surface); border: 0; border-radius: .4rem; padding: var(--space-1) var(--space-2); cursor: pointer; }
    button:hover:not(:disabled) { background: var(--border); }
```
→
```
    button { font: inherit; color: inherit; background: transparent; border: 1px solid var(--border); border-radius: var(--radius); padding: var(--space-1) var(--space-2); cursor: pointer; }
    button:hover:not(:disabled) { background: var(--surface); border-color: var(--text-faint); }
    .button-primary { background: var(--accent); border-color: var(--accent); color: var(--bg); font-weight: 700; }
    .button-primary:hover:not(:disabled) { background: var(--accent-strong); border-color: var(--accent-strong); }
```

(b) 動き（既存の reduce 規則の直後に足す）
```
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { scroll-behavior: auto !important; transition-duration: 0.01ms !important; }
    }
```
→
```
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { scroll-behavior: auto !important; transition-duration: 0.01ms !important; }
    }

    @media (prefers-reduced-motion: no-preference) {
      button, .ask-options [data-ask-option], .overview-markers .marker-n { transition: background-color 150ms ease, border-color 150ms ease, color 150ms ease, box-shadow 150ms ease; }
    }
```

(c) テーマ切替の見た目
```
    .theme-control { display: flex; justify-content: flex-end; width: min(100% - var(--space-4), var(--w-narrative)); margin: var(--space-2) auto 0; }
```
→
```
    .theme-control { display: flex; justify-content: flex-end; width: min(100% - var(--space-4), var(--w-narrative)); margin: var(--space-2) auto 0; }
    .theme-toggle { display: inline-grid; place-items: center; width: 32px; height: 32px; padding: 0; border-radius: 50%; color: var(--text-dim); }
    .theme-toggle svg { width: 18px; height: 18px; }
    .theme-toggle[aria-pressed="true"] .theme-icon-sun, .theme-toggle[aria-pressed="false"] .theme-icon-moon { display: none; }
```

(d) 使われていない選択子を消す
```
    .ask-benefit, .ask-tradeoff, .ask-no-default-reason { color: var(--text-dim); font-size: var(--fs-figure); }
```
→
```
    .ask-benefit, .ask-tradeoff { color: var(--text-dim); font-size: var(--fs-figure); }
```

(e) 選択肢のホバーと選択中
```
    .ask-options [data-ask-option][data-ask-selected] { box-shadow: inset 0 0 0 2px var(--accent); background: color-mix(in srgb, var(--accent) 12%, var(--surface)); }
```
→
```
    .ask-options [data-ask-option]:not([data-ask-withdrawn]):not([data-ask-selected]):hover { border-color: var(--text-faint); }
    .ask-options [data-ask-option][data-ask-selected] { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); background: color-mix(in srgb, var(--accent) 12%, var(--surface)); }
```

- [ ] **Step 4: テーマボタンの HTML と JS を置換する**

(a) ボタン（`<div class="theme-control">` の中の 1 行。置換後も 1 行で書く）
```
    <button type="button" data-theme-toggle aria-pressed="false">現在のテーマを確認中です。</button>
```
→
```
    <button type="button" class="theme-toggle" data-theme-toggle aria-pressed="false" aria-label="テーマを切り替える" title="テーマを切り替える"><svg class="theme-icon-sun" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg><svg class="theme-icon-moon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg></button>
```

(b) `FIXED THEME CONTROL JS` の `render` の中
```
      button.textContent = `現在のテーマ: ${label(current)}。${label(next)}に切り替える`;
```
→
```
      const text = `テーマ: ${label(current)}（${label(next)}に切替）`;
      button.setAttribute('aria-label', text);
      button.setAttribute('title', text);
```

(c) `FIXED DECISION COLLECTION JS` の冒頭
```
    if (!engine || !panel || !main) return;
```
→
```
    if (!engine || !panel || !main) return;
    panel.querySelectorAll('.panel-note').forEach((note) => { note.hidden = true; });
```

(d) コピーボタン
```
    copyButton.textContent = '回答と指摘をコピー';
```
→
```
    copyButton.className = 'button-primary';
    copyButton.textContent = '回答と指摘をコピー';
```

- [ ] **Step 5: 見本を再ビルドして通す**

Task 2 Step 5 と同じコマンド。Expected: `本文 1373 字 / 図より前 87 字 / 図 3 点`。全テスト PASS（`test_decision_engine_js.py` の `test_skeleton_inline_scripts_pass_node_check` を含む）。`selftest: 36 passed, 0 failed`。

- [ ] **Step 6: Commit**

```bash
git add skills/visual-explain/assets/skeleton.html skills/visual-explain/scripts/tests/test_skeleton_audit.py \
  skills/visual-explain/examples/example-proposal.html
git commit -m "feat(ve): give the copy action an accent button and the theme switch an icon"
```

---

### Task 4: モバイル（16px 余白・matrix のカード化・＋ の位置）

**Files:**
- Modify: `skills/visual-explain/assets/skeleton.html`（`@media (max-width: 42rem)` の先頭、`FIXED DECISION COLLECTION JS` の `place` / `showAdd`）
- Modify: `skills/visual-explain/scripts/ve_components/renderers/matrix.py`（`_render_dense_table`）
- Modify: `skills/visual-explain/examples/example-proposal.html`（再ビルド）
- Test: `skills/visual-explain/scripts/tests/test_skeleton_audit.py`, `skills/visual-explain/scripts/tests/test_matrix_renderer.py`, `skills/visual-explain/scripts/tests/test_matrix_stairs_sequence_renderer.py`

**Interfaces:**
- Consumes: `_render_dense_table(..., show_column_headers, panel)`（既存）、Task 2 の `_style()`。
- Produces: dense matrix の各 `td`（`data-ve-column-id` を持つもの）に `data-ve-col-label="<列見出しのエスケープ済み文字列>"`。列見出しを表示しない matrix では付けない。matrix の contract version は 2 のまま。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_matrix_renderer.py` の末尾（`if __name__` の前）に足す:
```python
class MatrixCardLabelTest(unittest.TestCase):
    """v4 mobile cards print each cell's column label from data-ve-col-label."""

    def test_every_cell_carries_its_column_label(self) -> None:
        labels = {c.id: c.label for c in load_fixture_ir().matrix.columns}
        cells = [tag for tag in re.findall(r"<td\b[^>]*>", render_fixture().markup)
                 if "data-ve-column-id" in tag]
        self.assertEqual(len(cells), 4)
        for tag in cells:
            column = re.search(r'data-ve-column-id="([^"]+)"', tag).group(1)
            self.assertIn(f'data-ve-col-label="{labels[column]}"', tag)

    def test_headerless_matrix_has_no_card_labels(self) -> None:
        markup = render_fixture("component-valid-matrix-headerless").markup
        self.assertNotIn("data-ve-col-label", markup)
```

`tests/test_matrix_stairs_sequence_renderer.py` の `test_legacy_rendering_remains_byte_exact` の matrix のハッシュ
```python
            "dd263127f89af1b365ea1d190e5dd50c43ddae2ef653a533f3543d14c229224c",
```
を次にする（列ラベル属性を足した出力。試作で算出済み）:
```python
            "8a7a5aad2b2127dd0cbeabc6812323c61cf0de4178324c9e156de59614ea12ef",
```

`tests/test_skeleton_audit.py` の末尾（`if __name__` の前）に足す:
```python
class MobileV4Test(unittest.TestCase):
    _collection_block = DecisionOptionCardInteractionTest._collection_block

    def _mobile(self):
        return _style().split("@media (max-width: 42rem) {", 1)[1]

    def test_sixteen_pixel_gutter(self):
        style = _style()
        self.assertIn("main { width: min(100% - var(--space-4), var(--w-narrative));", style)
        self.assertNotIn("100% - var(--space-2)", style)

    def test_dense_matrix_becomes_cards(self):
        mobile = self._mobile()
        prefix = '[data-ve-section-kind] figure[data-ve-component="matrix"] .ve-matrix-scroll'
        for needle in (
            f"{prefix} {{ overflow-x: visible; }}",
            f"{prefix} :is(table, tbody, tr, th, td) {{ display: block; width: auto; min-width: 0; }}",
            f"{prefix} tr {{ margin: 0 0 var(--space-2); padding: var(--space-2); "
            "border: 1px solid var(--border); border-radius: var(--radius); }",
            f"{prefix} td[data-ve-col-label]::before {{ content: attr(data-ve-col-label); display: block; "
            "color: var(--text-dim); font-size: var(--fs-small); font-weight: 700; }",
        ):
            self.assertIn(needle, mobile)

    def test_text_blocks_reserve_room_for_the_add_button(self):
        gate = _style().split("@media (max-width: 52rem) {", 1)
        self.assertEqual(len(gate), 2)
        self.assertIn("[data-ve-section-kind] :is(p, li, h2, h3, blockquote)[data-ve-blk] "
                      "{ padding-right: var(--space-4); }", gate[1].split("\n    }", 1)[0])

    def test_add_button_never_covers_text(self):
        block = self._collection_block()
        for needle in (
            "const place = (button, rect, below, block) => {",
            "if (block && /^(FIGURE|TABLE|PRE)$/.test(block.tagName)) top = rect.top - button.offsetHeight - 4;",
            "left = Math.max(0, Math.min(left, document.documentElement.clientWidth - width));",
            "place(addButton, block.getBoundingClientRect(), false, block);",
        ):
            self.assertIn(needle, block)
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_matrix_renderer.py tests/test_matrix_stairs_sequence_renderer.py tests/test_skeleton_audit.py -q`
Expected: FAIL（`MatrixCardLabelTest`、byte-exact、`MobileV4Test`）。

- [ ] **Step 3: matrix レンダラに列ラベルを足す**

`ve_components/renderers/matrix.py` の `_render_dense_table` で
```python
    body_rows = []
    for row in matrix.rows:
        cells = [f'<th scope="row" data-ve-semantic-id="{_esc(row.id)}">{_esc(row.label)}</th>']
```
→
```python
    def label_attr(col) -> str:
        # Mobile cards print the column label above each cell; hidden headers stay hidden.
        return f' data-ve-col-label="{_esc(col.label)}"' if show_column_headers else ""

    body_rows = []
    for row in matrix.rows:
        cells = [f'<th scope="row" data-ve-semantic-id="{_esc(row.id)}">{_esc(row.label)}</th>']
```
同じ関数の空セル
```python
                    f'<td data-ve-row-id="{_esc(row.id)}" data-ve-column-id="{_esc(col.id)}"'
                    f' aria-label="該当なし">—</td>'
```
→
```python
                    f'<td data-ve-row-id="{_esc(row.id)}" data-ve-column-id="{_esc(col.id)}"{label_attr(col)}'
                    f' aria-label="該当なし">—</td>'
```
値のあるセル
```python
                f' data-ve-column-id="{_esc(col.id)}"{takeaway_attr}>{_cell_content_html(cell.content)}'
```
→
```python
                f' data-ve-column-id="{_esc(col.id)}"{label_attr(col)}{takeaway_attr}>{_cell_content_html(cell.content)}'
```

- [ ] **Step 4: skeleton の 42rem 規則を置換する**

```
    @media (max-width: 42rem) {
      main { width: min(100% - var(--space-2), var(--w-narrative)); padding-top: var(--space-2); }
      .theme-control { width: min(100% - var(--space-2), var(--w-narrative)); }
      .theme-control button { max-width: 100%; white-space: normal; }
```
→
```
    @media (max-width: 52rem) {
      [data-ve-section-kind] :is(p, li, h2, h3, blockquote)[data-ve-blk] { padding-right: var(--space-4); }
    }

    @media (max-width: 42rem) {
      [data-ve-section-kind] figure[data-ve-component="matrix"] .ve-matrix-scroll { overflow-x: visible; }
      [data-ve-section-kind] figure[data-ve-component="matrix"] .ve-matrix-scroll :is(table, tbody, tr, th, td) { display: block; width: auto; min-width: 0; }
      [data-ve-section-kind] figure[data-ve-component="matrix"] .ve-matrix-scroll thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); }
      [data-ve-section-kind] figure[data-ve-component="matrix"] .ve-matrix-scroll tr { margin: 0 0 var(--space-2); padding: var(--space-2); border: 1px solid var(--border); border-radius: var(--radius); }
      [data-ve-section-kind] figure[data-ve-component="matrix"] .ve-matrix-scroll th[scope="row"] { padding: 0 0 var(--space-1); border-bottom: 0; }
      [data-ve-section-kind] figure[data-ve-component="matrix"] .ve-matrix-scroll td { padding: var(--space-1) 0 0; border-bottom: 0; }
      [data-ve-section-kind] figure[data-ve-component="matrix"] .ve-matrix-scroll td[data-ve-col-label]::before { content: attr(data-ve-col-label); display: block; color: var(--text-dim); font-size: var(--fs-small); font-weight: 700; }
```
（`main` の 8px 余白の上書きを消すと、全幅で `100% - var(--space-4)`＝左右 16px になる。列見出しの `thead` は画面読み上げのために視覚的にだけ隠す。）

- [ ] **Step 5: ＋ ボタンの位置を直す**

`FIXED DECISION COLLECTION JS` の
```
    const place = (button, rect, below) => {
      button.hidden = false;
      const width = button.offsetWidth;
      let left;
      if (below) left = rect.left;
      else if (rect.left >= width + 8) left = rect.left - width - 4;
      else left = rect.right - width;
      const top = below ? rect.bottom + 4 : rect.top;
```
→
```
    const place = (button, rect, below, block) => {
      button.hidden = false;
      const width = button.offsetWidth;
      let left;
      let top = below ? rect.bottom + 4 : rect.top;
      if (below) left = rect.left;
      else if (rect.left >= width + 8) left = rect.left - width - 4;
      else {
        // No room on the left: text blocks reserve right padding for the button;
        // figures, tables and code get it just above their top-right corner.
        left = rect.right - width;
        if (block && /^(FIGURE|TABLE|PRE)$/.test(block.tagName)) top = rect.top - button.offsetHeight - 4;
      }
      left = Math.max(0, Math.min(left, document.documentElement.clientWidth - width));
```
（直後の `button.style.left = …` / `button.style.top = …` の 2 行はそのまま。）

`showAdd` の
```
      place(addButton, block.getBoundingClientRect(), false);
```
→
```
      place(addButton, block.getBoundingClientRect(), false, block);
```

- [ ] **Step 6: 見本を再ビルドして通す**

Task 2 Step 5 と同じコマンド。Expected: `本文 1373 字 / 図より前 87 字 / 図 3 点`。全テスト PASS。`selftest: 36 passed, 0 failed`。

- [ ] **Step 7: 390 幅で目視確認する（テストにしない）**

```bash
SCRATCH="$(mktemp -d)"
DOC="$(git rev-parse --show-toplevel)/skills/visual-explain/examples/example-proposal.html"
printf '<!doctype html><body style="margin:0"><iframe src="file://%s" width="390" height="2400" style="border:0"></iframe>' "$DOC" > "$SCRATCH/narrow.html"
perl -e 'alarm 40; exec @ARGV' "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-first-run --user-data-dir="$SCRATCH/profile" \
  --window-size=600,2400 --screenshot="$SCRATCH/narrow-390.png" "file://$SCRATCH/narrow.html"
echo "$SCRATCH/narrow-390.png"
```
確認: 左右の余白が 16px。全体図の matrix は横スクロールせず、案ごとのカード（行見出しが題、各セルの上に「主な利点」「主なトレードオフ」）が縦に並ぶ。本文段落の右に約 2rem の空きがある（＋ はそこに出る。ホバー・タップは静止画に写らないので、実ブラウザで段落をタップして ＋ が文字に重ならないことを 1 度確かめる）。

- [ ] **Step 8: Commit**

```bash
git add skills/visual-explain/assets/skeleton.html skills/visual-explain/scripts/ve_components/renderers/matrix.py \
  skills/visual-explain/scripts/tests/test_matrix_renderer.py skills/visual-explain/scripts/tests/test_matrix_stairs_sequence_renderer.py \
  skills/visual-explain/scripts/tests/test_skeleton_audit.py skills/visual-explain/examples/example-proposal.html
git commit -m "feat(ve): use a 16px gutter, matrix cards, and a clear add button on phones"
```

---

### Task 5: 横型 chevron を 1 行・同じ高さにする

**Files:**
- Modify: `skills/visual-explain/assets/skeleton.html`（`<style>`）
- Modify: `skills/visual-explain/examples/example-proposal.html`（再ビルド。見本に chevron は無いが skeleton が変わる）
- Test: `skills/visual-explain/scripts/tests/test_skeleton_audit.py`

**Interfaces:**
- Consumes: chevron レンダラの横型の構造（`ol.ve-chevron-steps.ve-chevron-horizontal > li.ve-chevron-step > (div.ve-chv-box, ul.ve-chevron-description?, span.ve-emphasis?)`。1 段の子は最大 3 つなので subgrid は 3 行）。
- Produces: なし。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_skeleton_audit.py` の末尾（`if __name__` の前）に足す

```python
class ChevronV4Test(unittest.TestCase):
    def test_horizontal_steps_share_one_row_and_equal_heights(self):
        gate = _style().split("@media (width > 42rem) {", 1)
        self.assertEqual(len(gate), 2)
        block = gate[1].split("\n    }", 1)[0]
        prefix = '[data-ve-section-kind] figure[data-ve-component="chevron"] .ve-chevron-horizontal'
        for needle in (
            f"{prefix} {{ display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); "
            "grid-template-rows: auto auto auto; }",
            f"{prefix} .ve-chevron-step {{ display: grid; grid-row: span 3; grid-template-rows: subgrid; "
            "align-items: stretch; min-width: 0; max-width: none; }",
            f"{prefix} .ve-chv-box {{ align-content: center; }}",
        ):
            self.assertIn(needle, block)
        self.assertNotIn("flex-wrap", block)
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_skeleton_audit.py -k Chevron -q`
Expected: FAIL（`@media (width > 42rem)` が無い）。

- [ ] **Step 3: skeleton に規則を足す**（Task 4 の後、`@media (max-width: 42rem) {` はちょうど 1 回現れる）

```
    @media (max-width: 42rem) {
```
→
```
    @media (width > 42rem) {
      [data-ve-section-kind] figure[data-ve-component="chevron"] .ve-chevron-horizontal { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); grid-template-rows: auto auto auto; }
      [data-ve-section-kind] figure[data-ve-component="chevron"] .ve-chevron-horizontal .ve-chevron-step { display: grid; grid-row: span 3; grid-template-rows: subgrid; align-items: stretch; min-width: 0; max-width: none; }
      [data-ve-section-kind] figure[data-ve-component="chevron"] .ve-chevron-horizontal .ve-chv-box { align-content: center; }
    }

    @media (max-width: 42rem) {
```
（42rem 以下は component CSS の縦積みに任せる。`align-items: stretch` は component CSS の `.ve-chevron-step { align-items: center }` を打ち消して箱を行の高さまで伸ばす。）

- [ ] **Step 4: 見本を再ビルドして通す**

Task 2 Step 5 と同じコマンド。Expected: `本文 1373 字 / 図より前 87 字 / 図 3 点`。全テスト PASS。`selftest: 36 passed, 0 failed`。

- [ ] **Step 5: 6 段の横型を目視確認する（テストにしない）**

```bash
SCRATCH="$(mktemp -d)"
ROOT="$(git rev-parse --show-toplevel)"
python3 - "$ROOT/skills/visual-explain/scripts/tests/component-valid-chevron-horizontal.json" "$SCRATCH/chev6.json" <<'PY'
import copy, json, sys
raw = json.load(open(sys.argv[1], encoding="utf-8"))
section = next(s for s in raw["sections"] if s.get("kind") == "canonical")
base = section["ir"]["chevron"]["steps"][0]
titles = ["要件確定", "設計確認と関係部署の合意", "実装", "結合試験", "限定公開", "全体公開"]
steps = []
for i, title in enumerate(titles, start=1):
    step = copy.deepcopy(base)
    step["id"], step["title"], step["description"] = f"h{i}", title, [f"{title}を進める"]
    steps.append(step)
section["ir"]["chevron"]["steps"] = steps
json.dump(raw, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
PY
python3 "$ROOT/skills/visual-explain/scripts/build_explainer.py" --assembly "$SCRATCH/chev6.json" --output "$SCRATCH/chev6.html"
perl -e 'alarm 40; exec @ARGV' "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-first-run --user-data-dir="$SCRATCH/profile" \
  --window-size=1280,900 --screenshot="$SCRATCH/chev6.png" "file://$SCRATCH/chev6.html"
echo "$SCRATCH/chev6.png"
```
確認: 6 段が 1 行に並び、2 段目（長い題で 3 行に折り返す）を含めて全段の箱が同じ高さで、文字は箱の縦中央にある。説明文の行も揃う。

- [ ] **Step 6: Commit**

```bash
git add skills/visual-explain/assets/skeleton.html skills/visual-explain/scripts/tests/test_skeleton_audit.py \
  skills/visual-explain/examples/example-proposal.html
git commit -m "fix(ve): keep horizontal chevrons on one row with equal step heights"
```

---

### Task 6: Phase 1 の解析器の取りこぼしを直す

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/metrics.py`（全面置換）
- Modify: `skills/visual-explain/scripts/ve_components/repetition.py`（全面置換）
- Modify: `skills/visual-explain/scripts/ve_components/validation.py`（`_validate_overview`）
- Modify: `skills/visual-explain/scripts/tests/fixtures/bad-vs-duplicate-document-assertion-id.assembly.json`（`sections[2].ir.caption`）
- Modify: `skills/visual-explain/examples/example-proposal.html`（再ビルド。HTML は変わらないはずだが、報告値の確認のため実行する）
- Test: `skills/visual-explain/scripts/tests/test_metrics.py`, `skills/visual-explain/scripts/tests/test_repetition.py`, `skills/visual-explain/scripts/tests/test_first_screen_section.py`

**Interfaces:**
- Consumes: `render_ask(section) -> WrappedDocumentSection`（`document_sections.py`）、`insert_link_domain_markers(markup) -> str`（`assembly.py`）。どちらも関数内で遅延 import する（`validation` → `repetition` の import 時の循環を避ける）。
- Produces: `metrics.visible_chars(markup: str) -> int`、`repetition.chars_before_first_figure(sections: tuple[object, ...]) -> int`。`TextMetrics.chars_before_figure` は first-screen を数えない。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_metrics.py` を次で置き換える:
```python
from __future__ import annotations

import unittest

from ve_components.metrics import TextMetrics, format_metrics, text_metrics, visible_chars

DOC = (
    "<html><body><!-- VE-CONTROLLED:CONTENT:BEGIN -->"
    '<section data-ve-section-kind="first-screen"><h1>題名です</h1></section>'
    '<section data-ve-section-kind="narrative"><p>前置き<br/>です</p></section>'
    '<section data-ve-section-kind="canonical"><p>図の中</p></section>'
    '<section data-ve-section-kind="narrative"><p>本文 です。</p></section>'
    '<section data-ve-section-kind="decision-panel"><p>回収<br/><br/>パネルは数えない</p></section>'
    "<!-- VE-CONTROLLED:CONTENT:END --></body></html>"
)


class MetricsTest(unittest.TestCase):
    def test_counts(self) -> None:
        # h1 counts toward the body but not toward "before the first figure".
        self.assertEqual(text_metrics(DOC),
                         TextMetrics(body_chars=4 + 5 + 3 + 5, chars_before_figure=5, figures=1))

    def test_self_closing_void_tags_do_not_pop_the_parent(self) -> None:
        self.assertEqual(visible_chars("<p>a b<br/>c<br/></p><p>d</p>"), 4)

    def test_format(self) -> None:
        self.assertEqual(format_metrics(TextMetrics(1400, 80, 3)), "本文 1400 字 / 図より前 80 字 / 図 3 点")


if __name__ == "__main__":
    unittest.main()
```

`tests/test_repetition.py` の import 部を次にする:
```python
import copy
import unittest
from pathlib import Path

from build_explainer import build_document
from first_screen_ir import CANONICAL, assembly as _assembly, decision_ask, messages as _msgs, narr as _narr
from ve_components.metrics import text_metrics
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.repetition import bigram_jaccard, chars_before_first_figure, normalize_sentence
from ve_components.validation import validate_assembly

SKILL = Path(__file__).resolve().parents[2]
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS = SKILL / "assets" / "components"
REGISTRY = load_registry(COMPONENTS / "registry.json")
SENTENCE = "これは説明用の想定であり実在の状況ではありません。"


def _compat(markup: str) -> dict:
    return {"kind": "compatibility", "id": "sec-c", "markup": markup,
            "provenance": {"source": "legacy-html-insertion", "reason": "unmigrated-format", "format": "layers"}}
```
（`from __future__ import annotations` と docstring は残す。）ファイル末尾の `if __name__` の前に足す:
```python
class ParserGapTest(unittest.TestCase):
    def test_badge_on_non_span_does_not_hide_later_text(self) -> None:
        body = f'<p>前置き<strong class="certainty inferred">推論</strong></p><p>{SENTENCE}</p>'
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "背景", body), _narr("sec-b", "前提", f"<p>{SENTENCE}</p>"))
        self.assertIn(f"同じ文が2回出てきます: 「{SENTENCE}」", _msgs(raw))

    def test_omitted_end_tags_still_count(self) -> None:
        body = f"<ul><li>{SENTENCE}<li>別の項目です。</ul>"
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "背景", body), _narr("sec-b", "前提", f"<p>{SENTENCE}</p>"))
        self.assertIn(f"同じ文が2回出てきます: 「{SENTENCE}」", _msgs(raw))

    def test_unterminated_duplicate_is_caught(self) -> None:
        item = "請求計算と告知対象の照合手順"
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "背景", f"<ul><li>{item}</li></ul>"),
                        _narr("sec-b", "前提", f"<ul><li>{item}</li></ul>"))
        self.assertIn(f"同じ文が2回出てきます: 「{item}」", _msgs(raw))

    def test_compatibility_figure_caption_counts(self) -> None:
        compat = _compat(f'<figure class="figure"><figcaption>{SENTENCE}</figcaption><p>図</p></figure>')
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", "背景", f"<p>{SENTENCE}</p>"), compat)
        self.assertIn(f"同じ文が2回出てきます: 「{SENTENCE}」", _msgs(raw))

    def test_heading_is_forgotten_after_a_figure(self) -> None:
        heading = "限定公開だけが影響確認の機会を残しつつ改定を進められる"
        canon = copy.deepcopy(CANONICAL)
        canon["ir"]["caption"] = heading + "。"
        raw = _assembly({"conclusion": "限定対象で開始する。"},
                        _narr("sec-a", heading, "<p>補足。</p>"),
                        _compat('<figure class="figure"><figcaption>承認の流れ。</figcaption><p>図</p></figure>'),
                        canon)
        self.assertNotIn("図のキャプションが直前の見出しの言い換えです（sec-map）。キャプションには「何を見るか」を書いてください",
                         _msgs(raw))


class PreFigureCountParityTest(unittest.TestCase):
    def test_gate_and_report_count_the_same_text(self) -> None:
        body = ('<p class="claim">請求、告知、例外を<a href="https://example.com/a">同じ表</a>で照合する。'
                '<span class="certainty inferred">推論</span></p>')
        raw = _assembly({"conclusion": "限定対象で開始する。"}, _narr("sec-a", "背景", body),
                        decision_ask(), CANONICAL)
        request = validate_assembly(raw)
        html = build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS, document_path="x.html")
        gate = chars_before_first_figure(request.sections)
        self.assertGreater(gate, 0)
        self.assertEqual(gate, text_metrics(html).chars_before_figure)
```

`tests/test_first_screen_section.py` の `OverviewValidationTest` の `test_markers_must_be_sequential` の後に足す:
```python
    def test_bad_marker_n_is_reported_once(self) -> None:
        first = self._first(markers=[{"n": "1", "label": "背景", "target": "sec-a"},
                                     {"n": 2, "label": "決定", "target": "sec-a"}])
        msgs = _messages(_assembly(first, CANONICAL, _narr("sec-a", "背景の見出し")))
        self.assertIn("first-screen.overview.markers[].n は整数である必要があります", msgs)
        self.assertNotIn("first-screen.overview.markers の n は1からの連番である必要があります", msgs)
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_metrics.py tests/test_repetition.py tests/test_first_screen_section.py -q`
Expected: FAIL（`visible_chars` / `chars_before_first_figure` の ImportError で収集段階から失敗、`test_bad_marker_n_is_reported_once`）。

- [ ] **Step 3: `ve_components/metrics.py` を置き換える**

```python
"""Reader-facing text volume of a built document (reported, never enforced).

``visible_chars`` is the single counting rule for "text before the first
figure": the build report and the repetition gate both use it, so the number
an author sees after a build is the number the gate enforces.
"""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

_BEGIN = "<!-- VE-CONTROLLED:CONTENT:BEGIN -->"
_END = "<!-- VE-CONTROLLED:CONTENT:END -->"
_FIGURE_KINDS = frozenset({"canonical", "compatibility"})
_EXCLUDED_KINDS = frozenset({"decision-panel"})
_NOT_BEFORE_FIGURE_KINDS = frozenset({"first-screen"})
_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})


@dataclass(frozen=True)
class TextMetrics:
    body_chars: int
    chars_before_figure: int
    figures: int


class _Counter(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str | None] = []
        self.body = self.before = self.figures = 0
        self.seen_figure = False

    def handle_starttag(self, tag, attrs):
        if tag in _VOID_TAGS:
            return
        kind = dict(attrs).get("data-ve-section-kind") if tag == "section" else None
        if kind in _FIGURE_KINDS:
            self.figures += 1
            self.seen_figure = True
        self.stack.append(kind if kind else (self.stack[-1] if self.stack else None))

    def handle_startendtag(self, tag, attrs):
        # <br/> must not pop the parent; <span/> opens and closes nothing.
        if tag in _VOID_TAGS:
            return
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in _VOID_TAGS:
            return
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        kind = self.stack[-1] if self.stack else None
        if kind in _EXCLUDED_KINDS:
            return
        n = sum(1 for ch in data if not ch.isspace())
        self.body += n
        if not self.seen_figure and kind not in _NOT_BEFORE_FIGURE_KINDS:
            self.before += n


def _count(markup: str) -> _Counter:
    counter = _Counter()
    counter.feed(markup)
    counter.close()
    return counter


def visible_chars(markup: str) -> int:
    """Non-whitespace characters of the text in ``markup`` (tags and comments excluded)."""
    return _count(markup).body


def text_metrics(document: str) -> TextMetrics:
    start, end = document.find(_BEGIN), document.find(_END)
    content = document[start + len(_BEGIN):end] if 0 <= start < end else ""
    counter = _count(content)
    return TextMetrics(counter.body, counter.before, counter.figures)


def format_metrics(m: TextMetrics) -> str:
    return f"本文 {m.body_chars} 字 / 図より前 {m.chars_before_figure} 字 / 図 {m.figures} 点"
```

- [ ] **Step 4: `ve_components/repetition.py` を置き換える**

```python
"""Build-time repetition gate over validated assembly sections.

Rejects restating the same claim: h2 vs its claim line, a figure caption vs the
preceding h2, a sentence repeated anywhere, and long prose before the first
figure when the document has no overview.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

from .model import AskSection, CanonicalSection, ClosingSection, CompatibilitySection, FirstScreenSection, NarrativeSection

SIMILARITY_THRESHOLD = 0.6
MAX_CHARS_BEFORE_FIGURE = 200
_MIN_DUPLICATE_CHARS = 10
_NOISE_RE = re.compile(r"[\s、。，．,.！？!?「」『』（）()・:：;；\-—]")
# A trailing run without a terminator is a sentence too, so unterminated
# list items and labels take part in the duplicate check.
_SENTENCE_RE = re.compile(r"[^。！？!?]+(?:[。！？!?]|$)")
_BLOCK_TAGS = frozenset({"h2", "h3", "p", "li", "figcaption"})
# Start tags that end an open <p> whose </p> the author omitted.
_P_CLOSERS = frozenset({
    "p", "h2", "h3", "h4", "li", "ul", "ol", "dl", "div", "section", "figure",
    "figcaption", "table", "blockquote", "pre", "details", "nav",
})
_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})


def normalize_sentence(text: str) -> str:
    return _NOISE_RE.sub("", text)


def bigram_jaccard(a: str, b: str) -> float:
    def grams(s: str) -> set[str]:
        s = normalize_sentence(s)
        return {s[i:i + 2] for i in range(len(s) - 1)} or {s}
    ga, gb = grams(a), grams(b)
    return len(ga & gb) / len(ga | gb) if ga | gb else 0.0


class _Blocks(HTMLParser):
    """Collect (tag, classes, text) for h2/h3/p/li/figcaption.

    Any element with class ``certainty`` is skipped with its whole subtree,
    whatever its tag. Omitted ``</p>`` and ``</li>`` are implied the way a
    browser implies them for these cases, and an end tag closes every element
    opened after its start tag.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, frozenset[str], str]] = []
        # (tag, classes, text parts for block tags else None, starts a skipped subtree)
        self._stack: list[tuple[str, frozenset[str], list[str] | None, bool]] = []

    def _skipping(self) -> bool:
        return any(entry[3] for entry in self._stack)

    def _pop(self) -> None:
        tag, classes, parts, _skip = self._stack.pop()
        if parts is not None:
            self.blocks.append((tag, classes, "".join(parts).strip()))

    def handle_starttag(self, tag, attrs):
        if self._stack and self._stack[-1][0] == "p" and tag in _P_CLOSERS:
            self._pop()
        if tag == "li" and self._stack and self._stack[-1][0] == "li":
            self._pop()
        if tag in _VOID_TAGS:
            return
        classes = frozenset(" ".join(v or "" for k, v in attrs if k == "class").split())
        skip = "certainty" in classes
        collect = tag in _BLOCK_TAGS and not skip and not self._skipping()
        self._stack.append((tag, classes, [] if collect else None, skip))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if not any(entry[0] == tag for entry in self._stack):
            return
        while self._stack:
            closing = self._stack[-1][0] == tag
            self._pop()
            if closing:
                return

    def handle_data(self, data):
        if self._skipping():
            return
        for entry in reversed(self._stack):
            if entry[2] is not None:
                entry[2].append(data)
                return

    def close(self) -> None:
        super().close()
        while self._stack:
            self._pop()


def _blocks(markup: str) -> list[tuple[str, frozenset[str], str]]:
    parser = _Blocks()
    parser.feed(markup)
    parser.close()
    return parser.blocks


def chars_before_first_figure(sections: tuple[object, ...]) -> int:
    """Visible characters before the first figure, counted like the build report.

    The first-screen (h1 and conclusion) is excluded. Narrative and ask
    sections are measured on the markup the build emits for them, including
    the link-domain markers the build appends to external links.
    """
    from .assembly import insert_link_domain_markers
    from .document_sections import render_ask
    from .metrics import visible_chars

    total = 0
    for section in sections:
        if isinstance(section, (CanonicalSection, CompatibilitySection)):
            break
        if isinstance(section, NarrativeSection):
            total += visible_chars(insert_link_domain_markers(section.markup))
        elif isinstance(section, AskSection):
            total += visible_chars(render_ask(section).markup)
    return total


def check_repetition(sections: tuple[object, ...]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    sentences: list[str] = []
    last_h2: str | None = None
    seen_figure = False
    first = sections[0] if sections and isinstance(sections[0], FirstScreenSection) else None

    for section in sections:
        if isinstance(section, FirstScreenSection):
            sentences += _SENTENCE_RE.findall(section.conclusion)
        elif isinstance(section, NarrativeSection):
            blocks = _blocks(section.markup)
            for i, (tag, classes, text) in enumerate(blocks):
                if tag == "h2":
                    last_h2 = text
                    nxt = blocks[i + 1] if i + 1 < len(blocks) else None
                    if nxt and "claim" in nxt[1] and bigram_jaccard(text, nxt[2]) >= SIMILARITY_THRESHOLD:
                        out.append((f"見出しと主張行がほぼ同じ文です（{section.id}）。主張行を削るか、見出しと別の情報を書いてください",
                                    section.id))
                if tag in {"p", "li", "figcaption"}:
                    sentences += _SENTENCE_RE.findall(text)
        elif isinstance(section, CanonicalSection):
            seen_figure = True
            caption = section.ir.caption or ""
            if last_h2 and bigram_jaccard(caption, last_h2) >= SIMILARITY_THRESHOLD:
                out.append((f"図のキャプションが直前の見出しの言い換えです（{section.ir.id}）。キャプションには「何を見るか」を書いてください",
                            section.ir.id))
            sentences += _SENTENCE_RE.findall(caption)
            last_h2 = None  # a later figure is not "right after" this heading
        elif isinstance(section, CompatibilitySection):
            seen_figure = True
            for tag, _classes, text in _blocks(section.markup):
                if tag == "figcaption":
                    sentences += _SENTENCE_RE.findall(text)
            last_h2 = None
        elif isinstance(section, AskSection):
            for text in (section.question, section.claim.text if section.claim else None, section.verify):
                if text:
                    sentences += _SENTENCE_RE.findall(text)
        elif isinstance(section, ClosingSection):
            for block in section.blocks:
                for item in block.items:
                    sentences += _SENTENCE_RE.findall(item)

    counts: dict[str, tuple[int, str]] = {}
    for s in sentences:
        key = normalize_sentence(s)
        if len(key) < _MIN_DUPLICATE_CHARS:
            continue
        n, original = counts.get(key, (0, s))
        counts[key] = (n + 1, original)
    for n, original in counts.values():
        if n >= 2:
            out.append((f"同じ文が{n}回出てきます: 「{original.strip()}」", "assembly.sections"))

    has_overview = first is not None and first.overview is not None
    if seen_figure and not has_overview:
        chars = chars_before_first_figure(sections)
        if chars > MAX_CHARS_BEFORE_FIGURE:
            out.append((f"最初の図より前の本文が{chars}字あります（上限200字）", "assembly.sections"))
    return out
```
（既存の `test_too_much_text_before_first_figure` の期待値 224 は新しい数え方でも 224 のまま: 見出し「背景」2 字 ＋ 121 字 ＋ 101 字。）

- [ ] **Step 5: overview の `n` の二重診断を直す** — `ve_components/validation.py` の `_validate_overview`

```python
    markers: list[OverviewMarker] = []
    for i, item in enumerate(markers_raw):
```
→
```python
    markers: list[OverviewMarker] = []
    bad_n = False
    for i, item in enumerate(markers_raw):
```
```python
            col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.overview.markers[].n は整数である必要があります", mp)
            continue
```
→
```python
            col.add(INVALID_COMPONENT_PAYLOAD, "first-screen.overview.markers[].n は整数である必要があります", mp)
            bad_n = True
            continue
```
```python
    if [m.n for m in markers] != list(range(1, len(markers) + 1)):
```
→
```python
    # A non-integer n is already reported; its gap must not also read as a sequence error.
    if not bad_n and [m.n for m in markers] != list(range(1, len(markers) + 1)):
```

- [ ] **Step 6: 文末無しの重複に当たる fixture を直す**

`tests/fixtures/bad-vs-duplicate-document-assertion-id.assembly.json` は 2 つの図に同じキャプション「起案から公開までの承認経路」を持つ（文末記号が無いため、これまで重複検査をすり抜けていた）。`sections[2]`（`ir.id` が `flow-path-second`。ファイル内で 2 つ目の `"caption"`、170 行目付近）の `ir.caption` だけを次に変える:
```json
"caption": "公開後の差し戻し経路"
```
（このケースの検査対象は assertion id の重複で、キャプションは関係しない。`test_visual_stage_baseline_immutability.py` は固定範囲の外の変更を見ない。）

- [ ] **Step 7: 通す**

```bash
cd "$(git rev-parse --show-toplevel)"
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/examples/example-proposal.assembly.json \
  --output skills/visual-explain/examples/example-proposal.html
git diff --stat -- skills/visual-explain/examples/example-proposal.html
cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest
```
Expected: `本文 1373 字 / 図より前 0 字 / 図 3 点`（全体図が第一画面の直後に来るため）。見本 HTML の差分は無い。全テスト PASS。`selftest: 36 passed, 0 failed`。

- [ ] **Step 8: Commit**

```bash
git add skills/visual-explain/scripts/ve_components/metrics.py skills/visual-explain/scripts/ve_components/repetition.py \
  skills/visual-explain/scripts/ve_components/validation.py \
  skills/visual-explain/scripts/tests/fixtures/bad-vs-duplicate-document-assertion-id.assembly.json \
  skills/visual-explain/scripts/tests/test_metrics.py skills/visual-explain/scripts/tests/test_repetition.py \
  skills/visual-explain/scripts/tests/test_first_screen_section.py
git commit -m "fix(ve): count text before the first figure one way and close parser gaps"
```

---

### Task 7: 小さな負債の片付け（compatibility の判定・ビルドの組み立て）

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/validation.py`（`_BLOCK_ATTR_RE` の置き換え）
- Modify: `skills/visual-explain/scripts/build_explainer.py`（`compose_document` の切り出し）
- Test: `skills/visual-explain/scripts/tests/test_review_blocks.py`, `skills/visual-explain/scripts/tests/test_narrative_sections.py`

**Interfaces:**
- Consumes: `AssemblyRequest`（`ve_components.model`）、`compose_sections` / `stamp_review_sections` / `flatten_document`（既存）。
- Produces: `build_explainer.compose_document(request: AssemblyRequest, registry: Registry, renderers, *, document_path: str) -> CompositionResult`（review ブロック番号付与済み）。`build_document` はこれを呼ぶ。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_review_blocks.py` の `BuildTest.test_compatibility_cannot_carry_block_numbers` の後に足す:
```python
    def _compat_messages(self, markup: str) -> list[str]:
        compat = {"kind": "compatibility", "id": "sec-c", "markup": markup,
                  "provenance": {"source": "legacy-html-insertion", "reason": "unmigrated-format",
                                 "format": "layers"}}
        return messages(assembly({"conclusion": "限定対象で開始する。"}, compat))

    def test_prose_mentioning_the_attribute_is_not_a_block_number(self) -> None:
        msgs = self._compat_messages('<div class="figure"><p>属性 data-ve-blk はビルドが付けます</p></div>')
        self.assertNotIn("compatibility に data-ve-blk は書けません（ビルドが付与します）", msgs)

    def test_similar_attribute_name_is_not_a_block_number(self) -> None:
        msgs = self._compat_messages('<div class="figure"><p data-ve-blk-note="x">本文</p></div>')
        self.assertNotIn("compatibility に data-ve-blk は書けません（ビルドが付与します）", msgs)

    def test_upper_case_attribute_is_still_rejected(self) -> None:
        msgs = self._compat_messages('<div class="figure"><p DATA-VE-BLK="2">本文</p></div>')
        self.assertIn("compatibility に data-ve-blk は書けません（ビルドが付与します）", msgs)
```

`tests/test_narrative_sections.py`:
- import 部の `from build_explainer import build_document` を `from build_explainer import build_document, compose_document` にする。
- import 部から `from dataclasses import replace`、`from ve_components.review_blocks import stamp_review_sections` を消す（以下の置き換えで使わなくなる）。ほかの import（`compose_sections` / `process_*_section` / `flatten_document` / `CanonicalSection` / `NarrativeSection` など）はそのまま残してよい（未使用になるものがあっても害は無い）。
- 関数 `_build_composition_and_document` を丸ごと次で置き換える:
```python
def _build_composition_and_document(raw):
    # The real build pipeline, stopping before the final check so the test can
    # pass the CompositionResult to check_final_document as ``expected``.
    request = validate_assembly(raw)
    composition = compose_document(request, REGISTRY, TRUSTED_RENDERERS, document_path="doc.html")
    document = flatten_document(composition, SKELETON, COMPONENTS_DIR, request.document.title)
    return composition, document
```
- ファイル末尾に足す:
```python
def test_compose_document_is_the_build_pipeline():
    raw = json.loads((TESTS_DIR / "component-valid-narrative-mixed.json").read_text("utf-8"))
    _composition, document = _build_composition_and_document(raw)
    assert document == build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS_DIR,
                                      document_path="doc.html")
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_review_blocks.py tests/test_narrative_sections.py -q`
Expected: FAIL（`compose_document` の ImportError、本文テキストと `data-ve-blk-note` の 2 テスト）。

- [ ] **Step 3: compatibility の判定を parser にする** — `ve_components/validation.py`

`_BLOCK_ATTR_RE = re.compile(r"\sdata-ve-blk\b", re.IGNORECASE)` の行を消し、`class _PlainTextParser(HTMLParser):` の直前に足す:
```python
class _BlockNumberAttrParser(HTMLParser):
    """Find a start tag carrying an attribute named exactly ``data-ve-blk``."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if any((name or "").lower() == "data-ve-blk" for name, _value in attrs):
            self.found = True

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def _has_block_number_attr(markup: str) -> bool:
    parser = _BlockNumberAttrParser()
    parser.feed(markup)
    parser.close()
    return parser.found
```
compatibility の検査の
```python
        if _BLOCK_ATTR_RE.search(markup):
```
→
```python
        if _has_block_number_attr(markup):
```

- [ ] **Step 4: `compose_document` を切り出す** — `build_explainer.py`

import 部の `from ve_components.model import (` の括弧内に `AssemblyRequest,` を足す（先頭に置く）。

`build_document` を次の 2 関数で置き換える（`_section_instance_id` の後）:
```python
def compose_document(request: AssemblyRequest, registry: Registry, renderers, *,
                     document_path: str) -> CompositionResult:
    """Render every validated section in reading order and number review blocks.

    Validation guarantees sections[0] is the first-screen and, when it declares
    an overview, sections[1] is the overview figure; the marker list goes right
    after that figure and the collection panel goes last.
    """
    occupied_ids = frozenset(_section_instance_id(section) for section in request.sections)
    first = request.sections[0]
    nav = build_overview_nav(first, occupied_ids=occupied_ids)
    marked = {m.target for m in first.overview.markers} if first.overview is not None else set()
    items = []
    for section in request.sections:
        if isinstance(section, CanonicalSection):
            items.append(process_canonical_section(section, registry, renderers))
        elif isinstance(section, NarrativeSection):
            items.append(process_narrative_section(
                section, include_anchor_id=section.id in marked))
        elif isinstance(section, FirstScreenSection):
            items.append(render_first_screen(section, request.document))
        elif isinstance(section, ClosingSection):
            items.append(render_closing(section))
        elif isinstance(section, AskSection):
            items.append(render_ask(section))
        else:
            items.append(process_compatibility_section(section))
    panel = render_decision_panel(
        tuple(s for s in request.sections if isinstance(s, AskSection)),
        request.document, request.schema_version, document_path,
        occupied_ids=occupied_ids | ({nav.instance_id} if nav is not None else frozenset()))
    items.append(panel)
    if nav is not None:
        # first-screen [0], overview canonical [1], then the marker list.
        items.insert(2, nav)
    composition = compose_sections(items)
    return replace(composition, sections_markup=stamp_review_sections(composition.sections_markup))


def build_document(raw_assembly, registry: Registry, renderers, skeleton_text: str,
                   components_dir: Path, *, document_path: str) -> CompositionResult | str:
    """Validate, compose, flatten, and finally check. Raises on any failure."""
    declared = declared_skeleton_version(skeleton_text)
    if declared != LATEST_SKELETON_VERSION:
        raise ContractError([Diagnostic(
            FIXED_REGION_MISMATCH,
            f"ビルドは最新の skeleton 版（{LATEST_SKELETON_VERSION}）だけを使えます: {declared}",
        )])
    request = validate_assembly(raw_assembly)
    composition = compose_document(request, registry, renderers, document_path=document_path)
    document = flatten_document(composition, skeleton_text, components_dir, request.document.title)
    diagnostics = check_final_document(document, skeleton_text, registry, expected=composition,
                                       components_dir=components_dir)
    if diagnostics:
        raise ContractError(diagnostics)
    return document
```

- [ ] **Step 5: 通す**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest`
Expected: 全テスト PASS（`test_example_proposal.py` の再ビルド一致を含む。出力は変わらない）。`selftest: 36 passed, 0 failed`。

- [ ] **Step 6: Commit**

```bash
git add skills/visual-explain/scripts/ve_components/validation.py skills/visual-explain/scripts/build_explainer.py \
  skills/visual-explain/scripts/tests/test_review_blocks.py skills/visual-explain/scripts/tests/test_narrative_sections.py
git commit -m "refactor(ve): share the build composition with tests and parse compatibility block numbers"
```

---

### Task 8: 全体の目視確認と UI 評価

**Files:**
- なし（確認のみ。問題が見つかった場合は該当タスクの範囲で直し、そのタスクのテストを足してから別コミットにする）

**Interfaces:**
- Consumes: Task 1〜7 の成果。
- Produces: UI 評価の点数（PR 説明に書く）。

- [ ] **Step 1: 全検査**

```bash
cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest
bash check.sh "$(git rev-parse --show-toplevel)/skills/visual-explain/examples/example-proposal.html"
for f in tests/v2-proposal-doc.html tests/v3-proposal-doc.html tests/chevron-doc.html tests/matrix-doc-all-notations.html; do bash check.sh "$f" || echo "FAIL: $f"; done
```
Expected: 全テスト PASS、`selftest: 36 passed, 0 failed`、各 `check.sh` が成功（`FAIL:` が出ない）。

- [ ] **Step 2: ライト / ダーク × 1280 / 390 の 4 枚を撮る**

```bash
SCRATCH="$(mktemp -d)"
DOC="$(git rev-parse --show-toplevel)/skills/visual-explain/examples/example-proposal.html"
sed 's/<html lang="ja" /<html lang="ja" data-theme="dark" /' "$DOC" > "$SCRATCH/dark.html"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
for theme in light dark; do
  src="$DOC"; [ "$theme" = dark ] && src="$SCRATCH/dark.html"
  perl -e 'alarm 40; exec @ARGV' "$CHROME" --headless=new --disable-gpu --no-first-run \
    --user-data-dir="$SCRATCH/profile" --window-size=1280,900 --screenshot="$SCRATCH/$theme-1280.png" "file://$src"
  printf '<!doctype html><body style="margin:0"><iframe src="file://%s" width="390" height="2400" style="border:0"></iframe>' "$src" > "$SCRATCH/$theme-narrow.html"
  perl -e 'alarm 40; exec @ARGV' "$CHROME" --headless=new --disable-gpu --no-first-run \
    --user-data-dir="$SCRATCH/profile" --window-size=600,2400 --screenshot="$SCRATCH/$theme-390.png" "file://$SCRATCH/$theme-narrow.html"
done
ls "$SCRATCH"/*.png
```
（ダーク版は作業用コピーにだけ `data-theme="dark"` を足す。リポジトリの HTML は触らない。）

- [ ] **Step 3: UI 評価を文脈を持たない subagent に頼む**

4 枚の画像の場所と次の採点表だけを渡す（本計画や spec は渡さない）。各観点 0〜4 点、合計 36 点:
1. 視覚階層（どこから見るかが一目で分かる）
2. 第一画面（題名・結論・全体図・①②③ が最初の画面にある）
3. 余白とリズム
4. 書体の段（大きさの差が意味の差になっている）
5. 色の規律（色が意味を持つ所にだけ使われている）
6. 操作部品の分かりやすさ（主ボタン・選択肢・テーマ切替）
7. 状態表示（選択中・推奨・指摘済みが区別できる）
8. スマホでの読みやすさ（余白・表のカード化・はみ出しが無い）
9. 一貫性（同じ意味の部品が同じ見た目）

合格は 28 点以上。28 点未満なら、点の低い観点と subagent の指摘を報告して止める（CSS を独断で変えない）。

- [ ] **Step 4: 結果を記録する**

点数と観点別の内訳を、この Phase の PR 説明に貼る。コミットは無い。

---

### Task 9: スキル文書の更新

**Files:**
- Modify: `skills/visual-explain/references/design-system.md`, `skills/visual-explain/SKILL.md`, `CLAUDE.md`

**Interfaces:**
- Consumes: Task 1〜7 の挙動。
- Produces: なし。

各置換の old は、Phase 2 の文書更新（`f3a680b`）後の現行文書にちょうど 1 回現れる。

- [ ] **Step 1: `references/design-system.md` を更新する**

(a) トークン（`--surface` の用途）
```
- `--surface`: カード・図・折りたたみの面
```
→
```
- `--surface`: 第一画面の全体図の面と、図の中の部品（ノード・カード）の面。問いカード・回収パネル・legacy の図・折りたたみには敷かない
```

(b) タイプスケール 5 行
```
- `--fs-hero`（1.875rem）: h1・第一画面の主張・KPI 値
- `--fs-h2`（1.25rem）: h2・節の主張（`.claim`）・図キャプション・第一画面の結論ボックス `.conclusion`（本文サイズ・`--text`・左に `--accent` の罫線。内部の `strong` は「結論:」の見出し語）
- `--fs-body`（1rem）: 本文
- `--fs-figure`（.875rem／14px・400）: 図解コンテンツ（ノード・セル・レーン・凡例・比較枠・タイムライン・KPIカード本体・用語カードなど図の中身）
- `--fs-small`（.8125rem）: フッター・チップ・補足注記
```
→
```
- 段は 1.25 倍刻み（skeleton v4）。
- `--fs-hero`（1.953rem）: h1・KPI 値
- `--fs-h2`（1.563rem）: h2
- `--fs-h3`（1.25rem）: h3・節の主張（`.claim`）・図キャプション
- `--fs-body`（1rem）: 本文・第一画面の結論ボックス `.conclusion`（`--text`・左に `--accent` の罫線。内部の `strong` は「結論:」の見出し語）
- `--fs-figure`（.8rem）: 図解コンテンツ（ノード・セル・レーン・凡例・比較枠・タイムライン・KPIカード本体・用語カードなど図の中身）
- `--fs-small`（.8rem）: フッター・チップ・補足注記
```

(c) 節の縦マージン
```
`section` の縦マージンは `--space-7`。
```
→
```
`section` の縦マージンは `--space-5`（v4）。第一画面は上に余白を持たず、全体図と番号一覧は `--space-2` で詰める。
```

(d) 表層の面の規則
```
- **枠線は面で代替**: カード・図・折りたたみは枠線ではなく `--surface` の面で区切れ。罫線は表の横罫と節の境目に限定する。
```
→
```
- **面は全体図だけ**: `--surface` の面は第一画面の全体図にだけ敷く。問いカード・回収パネル・legacy の図・折りたたみは `--bg` に 1px の `--border` で区切る。
- **操作部品**: 主ボタン（回答と指摘のコピー）は `--accent` 塗りに `--bg` の文字。ほかのボタンは枠線だけ。テーマ切替は右上の 32px の丸ボタンで、現在のテーマを太陽 / 月のアイコンで示し、文言は `aria-label` と `title`（「テーマ: ライト（ダークに切替）」）に持つ。「自動」は無い。状態変化の遷移は 150ms で、動きを減らす設定では付かない。
```

(e) 指摘層の行
```
- **指摘層**: ＋ ボタンと「指摘」ボタンは枠線だけの小さなボタンで、本文の色を変えない。入力欄は指したブロックの直下に開き、指摘済みブロックは左の `--accent` 縦線と `#N` 札で示す。
```
→
```
- **指摘層**: ＋ ボタンと「指摘」ボタンは枠線だけの小さなボタンで、本文の色を変えない。＋ は左に余白があればブロックの左外側、無い画面（52rem 以下）では段落・見出し・項目が右に確保した余白の中、図・表・コードでは右上の外側に出て、文字に重ならない。入力欄は指したブロックの直下に開き、指摘済みブロックは左の `--accent` 縦線と `#N` 札で示す。
```

(f) 表のレイアウト不変条件
```
- 表は `matrix` の中のセマンティックな `table` として書け。小さい画面で横スクロールできることを前提に、列を増やしすぎるな。
```
→
```
- 表は `matrix` の中のセマンティックな `table` として書け。42rem 以下では、列見出しを持つ matrix は行ごとのカード（行見出しが題、各セルの上に列見出し）に切り替わる。横型 chevron は 42rem より広い画面で 1 行に並び、全段の箱の高さが揃う。左右の余白はどの幅でも 16px。
```

- [ ] **Step 2: `SKILL.md` を更新する**

```
成功時の「本文 N 字 / 図より前 M 字 / 図 K 点」を見て、文字量を確かめる。
```
→
```
成功時の「本文 N 字 / 図より前 M 字 / 図 K 点」を見て、文字量を確かめる（図より前 M 字は h1 と結論を除いた字数で、200 字の上限と同じ数え方）。
```
```
回収パネル（decision-panel。v3 文書では常にちょうど1つ）
```
→
```
回収パネル（decision-panel。v3 以降の文書では常にちょうど1つ）
```

- [ ] **Step 3: `CLAUDE.md` を更新する**

```
v3 は問いカード・指摘層・回収パネルの固定 JS を持ち、v2 は `assets/skeleton-v2.html` に凍結した。
```
→
```
v3 は問いカード・指摘層・回収パネルの固定 JS を持つ。v4 は見た目の刷新（1.25 倍刻みの書体、主ボタン、アイコンのテーマ切替、16px 余白、matrix のカード化、横型 chevron）で、v2・v3 は `assets/skeleton-v2.html` / `assets/skeleton-v3.html` に凍結した。component CSS の digest は全版で共有されるため、見た目の変更は skeleton 側に置き、`assets/components/*.css` は変えない。
```
```
checker は同じ規則で再計算して照合する（v3 文書のみ）。
```
→
```
checker は同じ規則で再計算して照合する（v3 以降の文書のみ）。
```
```
decision-panel の存在（v3 文書はちょうど1つ、v1/v2 は decision ask の有無との整合）
```
→
```
decision-panel の存在（v3 以降の文書はちょうど1つ、v1/v2 は decision ask の有無との整合）
```

- [ ] **Step 4: 文書に他者スキル名が無いことと、テストが通ることを確かめる**

```bash
cd "$(git rev-parse --show-toplevel)"
git diff -U0 -- CLAUDE.md skills/visual-explain/SKILL.md skills/visual-explain/references/design-system.md | grep '^+' | head -40
cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest
```
Expected: 追加行に外部の固有名が無い。全テスト PASS。`selftest: 36 passed, 0 failed`。

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md skills/visual-explain/SKILL.md skills/visual-explain/references/design-system.md
git commit -m "docs(ve): describe the skeleton v4 look and the unified pre-figure count"
```
