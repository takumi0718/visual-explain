# Phase 2: 問いカード・指摘層・回収パネル Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 読者が問いカードで選び、本文ブロックを指して指摘し、末尾の回収パネルからコピー 1 回で固定形のテキストを agent へ返せる資料にする（skeleton v3）。

**Architecture:** skeleton は v2 を `assets/skeleton-v2.html` に凍結し、最新 `assets/skeleton.html` を v3 にする。decision ask の IR に `benefit` / `evidence` / `withdrawn` を足し、`document_sections.py` が問いカードとして描く。新モジュール `ve_components/review_blocks.py` が、ビルドでは content 内のブロックに `data-ve-blk` を連番で付け、checker では同じ規則で期待値を再計算して照合する。回収パネルは全資料に 1 つ生成し、checker は v3 文書にだけ「ちょうど 1 つ」を課す。純関数の回収エンジン（`scripts/tests/runtime/decision_engine.js`）を新しいコピー固定形と指摘の状態に書き換え、skeleton 固定領域へ逐語埋め込みする。指摘層の UI（＋ ボタン・なぞりボタン・入力欄・番号札）は固定領域の `FIXED DECISION COLLECTION JS` に置く。

**Tech Stack:** Python 3 標準ライブラリのみ（`html.parser`, `re`, `dataclasses`, `json`）、node 標準のみ（`node --check` と既存ドライバ）、pytest（開発時のみ）、bash。

**Spec:** `docs/superpowers/specs/2026-10-07-visual-explain-review-loop-design.md` の「Phase 2 — 問いカード・指摘層・回収パネル（skeleton v3）」節、「確定した設計判断」、「Hard constraints」。

## Preflight: spec が決めていない点の裁定

実装者はこの裁定に従う。各タスクの要件に暗黙に含まれる。

1. **assembly の `schemaVersion` は 2 のまま上げない。** 必須フィールドの追加は欠落フィールドの診断の方が直しやすい。238 個の fixture の機械的書き換えも避ける。
2. **`noDefaultReason` は廃止する。** 「未選択＝お任せ＝推奨」が成り立つよう、すべての decision ask に `defaultId` を必須にする。`noDefaultReason` を書くと専用の診断で落とす。モデルの `AskSection.no_default_reason` も削除する。v1/v2 生成物の `ask-no-default-reason` は checker（`validate_ask_blocks`）が引き続き受け付ける。
3. **`benefit` と `tradeoff` はすべての選択肢で必須。** 推奨でない選択肢の `benefit` 欠落は専用の文言（`推奨でない選択肢 '<id>' にも benefit（選ぶ理由）が必要です`）にする。`withdrawn` の選択肢も同じ必須項目を持つ（前の版の選択肢をそのまま残すため）。`defaultId` は取り下げた選択肢を指せない。取り下げていない選択肢は 2 件以上必要。
4. **`evidence` は decision ask ごとに 1 つの文字列で、200 字以内。** `file:line`（正規表現 `[^\s:：「」]+:\d+`）か「」で囲んだ実行結果の引用（`「[^」]+」`）を 1 つ以上含む。カードでは問いの直下に「根拠: …」と出す。
5. **取り下げた選択肢も digest に含める。** `data-ask-option-id` と `data-ask-withdrawn` を持って DOM に残り、選択も回答もできない。
6. **選択中の選択肢をもう一度押すと選択を外し、お任せに戻る。** 選択肢は `role="radio"`、一覧は `role="radiogroup"`。
7. **下書きの保存キーは `ve-review:<documentId>:<schemaVersion>:<digest>:<blockCount>`。** spec の「文書 id と schema 版」に、問いと本文ブロックが変わった再ビルドで古い下書きを別の場所へ復元しないための 2 要素を足す。接頭辞を変えるので v2 文書の下書き（`ve-decision:`）とは混ざらない。
8. **`data-ve-blk` を付けない部分木:** 回収パネル（`section[data-ve-section-kind="decision-panel"]`）、`li[data-ask-option]`、`.ask-kind`、`.ask-memo`、`[data-stepper]`（段階表示は panel ごとに DOM 同一性を検査するため）、`svg` / `template` / `script` / `style`。`figure` は 1 ブロックとして番号を持つが、その子孫には付けない。それ以外では入れ子の対象タグにもそれぞれ番号を付ける。属性は開始タグの `>` の直前に足す。
9. **checker は同じ規則で期待される番号を再計算し、完全一致を求める。** 欠落・重複・飛び番・対象外タグ・除外部分木への付与をすべて落とす。連番の不一致は最初の 1 件だけを報告する。この検査は v3 以降の文書だけに課し、`check_document_structure` の `skeleton_version` 引数は省略時 1（旧規則）とする。
10. **ビルドは最新版の skeleton だけを受け付ける。** v3 の挙動（番号付与・パネル常設）が v1/v2 を宣言する文書に混ざらないようにする。
11. **compatibility の生 HTML に `data-ve-blk` を書くとエラーにする**（narrative は既に `data-ve-*` を禁止している）。
12. **回収パネルの section 種別名は `decision-panel` のまま**にする（v1/v2 の検査がこの名前に依存する）。見出しは「回答と指摘の回収」。decision ask が 0 件の資料では問いの一覧（`ul.panel-asks`）を出さず、指摘件数と全体メモとコピーだけを出す。
13. **指摘はチップの選択が必須。** チップを選ぶまで「追加」は押せない。ひとことは 1 行入力で、連続する空白と改行を 1 つの空白に詰める。補足と全体メモは前後の空白だけを落とし、改行は残す。指摘はブロック番号の昇順、同じ番号の中では追加順に並べる。保存済みの指摘は入力欄の一覧から削除できる。
14. **引用は空白を詰めて前後を落とした後の先頭 40 コードポイント**（`Array.from` で数え、サロゲートペアを割らない）。なぞりが複数ブロックにまたがるときは開始位置のブロックに付ける。
15. **＋ ボタンの位置:** ブロックの左に ボタン幅＋8px 以上の余白があれば左外側、なければブロック右端の内側。入力欄は `li` では li の末尾に、それ以外ではブロックの直後に挿入する。
16. **全ブロックに `tabindex="0"` を付ける**（spec のキーボード操作「ブロックにフォーカスして Enter」を満たすため）。Enter はブロック自身にフォーカスがあるときだけ入力欄を開く。
17. **他の ask（request / hypothesis）は内容を変えない。** 見た目は `.ask` に 1px の枠線を足して揃える。
18. **エンジンのファイル名は `decision_engine.js` のまま**にする。skeleton の `FIXED DECISION ENGINE CORE` 区間との逐語一致テストは最新版 skeleton だけを対象にする。凍結した v1/v2 は旧エンジンを含んだまま SHA-256 で固定する。
19. **Phase 1 の持ち越し小課題**（反復検査の取りこぼしなど）は Phase 2 の spec に無いため、この計画では扱わない。

## Global Constraints

- 外部依存ゼロ: build / check は Python 標準ライブラリのみ。JS テストは node 標準のみ。npm / pip / Playwright / Selenium / Puppeteer / jsdom を追加しない。
- 既存配色のみ: skeleton の既存トークン（`--accent` / `--accent-strong` / `--positive` / `--text-dim` / `--text-faint` / `--border` / `--surface` / `--bg` / `--focus`）と、それを `color-mix(in srgb, <token> 12%, var(--surface))` で薄めた色だけを使う。新しい色相・生の hex を足さない。
- 余白（margin / padding / gap）は `0` / `var(--space-1)`〜`var(--space-7)` / `auto` / `inherit` だけ（`test_skeleton_audit.py` の格子監査）。
- skeleton は版ごとに 1 バイト不変。v1・v2 は凍結ファイルで、checker は文書が宣言する版と照合する。CSP（inline script のみ、外部なし）は変えない。生成コンテンツに script を入れない。UI の JS はすべて v3 skeleton の固定領域に置く。
- 生成 HTML の手編集禁止。見本の修正は IR → `build_explainer.py` で再ビルドする。見本の再ビルドはリポジトリルートを cwd にして相対パスで出力する: `python3 skills/visual-explain/scripts/build_explainer.py --assembly skills/visual-explain/examples/example-proposal.assembly.json --output skills/visual-explain/examples/example-proposal.html`
- 参考にした他者スキルの固有名を、コード・コメント・コミット・文書に書かない。仕組みは一般語（問いカード、指摘層、回収パネル、試問）で表す。
- コードのコメント / docstring は英語、checker 診断とスキル文書は日本語。診断文言は完全一致テストの対象。
- コミットは conventional commits ＋ `(ve)` スコープ。末尾に次の 2 行を付ける:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` / `Claude-Session: https://claude.ai/code/session_01NgfQq9eGiPhoY46Nmdb2Xv`
- テストは必ず `cd skills/visual-explain/scripts && python3 -m pytest tests -q` で実行する（他ディレクトリからは import に失敗する）。各タスクの最後に全テストと `bash check.sh --selftest` を通す。
- `tests/test_visual_stage_baseline_immutability.py` は過去の範囲（`af74036..8459865`）に固定されている。触らない。
- decision ask は 1 資料 4 問まで（5 問以上はエラー）。
- 指摘チップは次の 8 種をこの順で使う: わからない / 図にしてほしい / もっと詳しく / 短くする / 削る / 言い換える / 事実を確認 / ここは良い。
- `data-ve-blk` の対象タグ: `p, h2, h3, li, figure, blockquote, pre, table`。番号は 1 からの DOM 順。
- 引用は先頭 40 字。
- コピーの固定形（spec のまま）:

```
[visual-explain 回答]
資料: <title>
(<path> / id: <id> / schema: <ver> / asks: <digest>)
Q1. <問い>: <選択> / 補足: <自由記述>
Q2. <問い>: (未選択 = お任せ)
全体メモ: <自由記述>
## 指摘
#12 [図にしてほしい] 「<なぞった文字列（先頭 40 字）>」 <ひとこと>
#15 [ここは良い]
---
上の回答を反映して作業を続けてください。お任せの項目は推奨案で確定してください。
```

  空の節（指摘 0 件、全体メモ空）は出さない。補足が空なら ` / 補足:` を省く。クリップボードが使えないときは手動コピー用の表示に切り替える。

## Review Focus

- 同じ文書 id で再ビルドした資料（問いや本文ブロックが変わった）を開いたとき、古い下書きの選択・指摘が別の選択肢や別のブロックに復元されないこと → Task 6 の `test_storage_key_tracks_digest_and_block_count` と `test_restore_drops_stale_entries`。
- `-02` 版で前回の推奨や選択済みの選択肢を `withdrawn` にしたとき、取り下げ案が推奨のまま残ったり回答に出たりしないこと → Task 2 の `test_default_cannot_point_to_withdrawn`、Task 6 の `test_withdrawn_option_cannot_be_selected_or_restored`。
- compatibility の生 HTML に `data-ve-blk` が書かれている、または段階表示（`data-stepper`）を含む図があるとき、重複属性や panel 同一性検査の誤検出でビルドが壊れないこと → Task 4 の `test_compatibility_cannot_carry_block_numbers` と `test_stepper_subtree_is_not_numbered`。
- v1 / v2 で生成済みの資料（decision ask が無く回収パネルも無い、`data-ve-blk` も無い）が、新しい規則の下でも `check.sh` に合格すること → Task 1 の `test_v2_document_passes_both_checkers`、Task 5 の `test_legacy_rule_kept_for_v1_and_v2`、Task 8 の selftest。
- なぞった文字列に改行・連続空白・絵文字（サロゲートペア）が入る、ひとことが空、decision ask が 0 件の資料で指摘だけを返す、といった入力でコピー固定形が崩れないこと → Task 6 の `test_quote_is_normalized_to_40_code_points` と `test_copy_text_without_asks_lists_only_annotations`。

---

## File Map

| File | Responsibility | Task |
|---|---|---|
| `skills/visual-explain/assets/skeleton-v2.html` (create) | 凍結した v2（現 `skeleton.html` のバイト完全コピー） | 1 |
| `skills/visual-explain/assets/skeleton.html` | v3: 版属性、問いカード CSS、エンジン逐語コピー、収集 JS、指摘層 CSS/JS | 1, 3, 5, 6, 7 |
| `skills/visual-explain/scripts/ve_components/skeletons.py` | `LATEST_SKELETON_VERSION = 3` | 1 |
| `skills/visual-explain/scripts/build_explainer.py` | 最新版以外の skeleton を拒否、番号付与、パネル常設 | 1, 4, 5 |
| `skills/visual-explain/scripts/ve_components/model.py` | `AskOption.benefit/withdrawn`、`AskSection.evidence`、`no_default_reason` 削除 | 2 |
| `skills/visual-explain/scripts/ve_components/validation.py` | 問いカードの IR 契約、4 問上限、compatibility の `data-ve-blk` 禁止 | 2, 4 |
| `skills/visual-explain/references/assembly.schema.json` | decision ask の schema | 2 |
| `skills/visual-explain/scripts/ve_components/document_sections.py` | 問いカードと回収パネルの描画 | 2, 3, 5 |
| `skills/visual-explain/scripts/ve_components/review_blocks.py` (create) | `data-ve-blk` の付与と検査（同一の歩行規則） | 4 |
| `skills/visual-explain/scripts/ve_components/document_checks.py` | `skeleton_version` 引数、v3 の番号検査とパネル規則 | 4, 5 |
| `skills/visual-explain/scripts/ve_components/checker.py` | `check_final_document` が宣言版を渡す | 4 |
| `skills/visual-explain/scripts/tests/runtime/decision_engine.js` | 純関数エンジン（状態・指摘・コピー固定形） | 6 |
| `skills/visual-explain/scripts/tests/runtime/decision_engine_driver.js` | 関数以外のエクスポートも返す | 6 |
| `skills/visual-explain/scripts/check.sh` | selftest の追加ケース | 1, 8 |
| `skills/visual-explain/scripts/tests/first_screen_ir.py` | 共有ヘルパ `decision_ask()` | 2 |
| `skills/visual-explain/scripts/tests/v2-proposal-doc.html` (create) | v2 生成物（現見本のバイト完全コピー） | 1 |
| `skills/visual-explain/scripts/tests/structure-bad-v3-*.html` (create) | v3 の selftest fixture 3 本 | 8 |
| `skills/visual-explain/examples/example-proposal.assembly.json` / `.html` | 見本の IR 移行と再ビルド | 1–7 |
| `skills/visual-explain/SKILL.md`, `references/patterns.md`, `references/design-system.md`, `CLAUDE.md` | 文書 | 2, 9 |

---

### Task 1: skeleton v3 の版上げと v2 の凍結

**Files:**
- Create: `skills/visual-explain/assets/skeleton-v2.html`（現 `skeleton.html` のバイト完全コピー）
- Create: `skills/visual-explain/scripts/tests/v2-proposal-doc.html`（現 `examples/example-proposal.html` のバイト完全コピー）
- Modify: `skills/visual-explain/assets/skeleton.html`（2 行目の `data-ve-skeleton="2"` → `"3"`）
- Modify: `skills/visual-explain/scripts/ve_components/skeletons.py`（`LATEST_SKELETON_VERSION`）
- Modify: `skills/visual-explain/scripts/build_explainer.py`（`build_document` 冒頭）
- Modify: `skills/visual-explain/scripts/check.sh`（`run_selftest` の `structure_cases`）
- Modify: `skills/visual-explain/examples/example-proposal.html`（再ビルド）
- Test: `skills/visual-explain/scripts/tests/test_skeleton_versions.py`

**Interfaces:**
- Consumes: `ve_components.skeletons.declared_skeleton_version(markup: str) -> int`、`resolve_skeleton(...)`、`skeleton_file(version, assets_dir)`（Phase 1）。
- Produces: `LATEST_SKELETON_VERSION == 3`。`skeleton_file(2) == assets/skeleton-v2.html`。`build_document(...)` は最新版でない skeleton に `ContractError`（診断 `ビルドは最新の skeleton 版（3）だけを使えます: <版>`）を投げる。fixture `tests/v2-proposal-doc.html`。

- [ ] **Step 1: v2 を凍結し、v2 生成物を fixture として残す（どの変更よりも先に行う）**

```bash
cd skills/visual-explain
cp -p assets/skeleton.html assets/skeleton-v2.html
cp -p examples/example-proposal.html scripts/tests/v2-proposal-doc.html
shasum -a 256 assets/skeleton.html assets/skeleton-v2.html assets/skeleton-v1.html scripts/tests/v2-proposal-doc.html
```
Expected:
```
1f58a12aa50e73a08f4ae12f7ef70bc271f39ebfe53a9910eb9ab14104f03125  assets/skeleton.html
1f58a12aa50e73a08f4ae12f7ef70bc271f39ebfe53a9910eb9ab14104f03125  assets/skeleton-v2.html
7512debf49653053249be88218a2025a2d5374e2c5b289784fb47a0f5d1f720b  assets/skeleton-v1.html
986648508ab300b1c6ce0bb71059e82b20d03f2645d87be76e1788ef2d55aa6a  scripts/tests/v2-proposal-doc.html
```
ハッシュが違う場合は作業ツリーが main 56455d4 と異なる。止めて報告する。

- [ ] **Step 2: 失敗するテストを書く** — `tests/test_skeleton_versions.py` を次の内容で置き換える

```python
"""Versioned skeleton resolution: each document is checked against the skeleton it declares."""
from __future__ import annotations

import hashlib
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
REGISTRY = load_registry(COMPONENTS / "registry.json")
TESTS = Path(__file__).resolve().parent
CHECK = TESTS.parent / "check.sh"

FROZEN_SHA256 = {
    "skeleton-v1.html": "7512debf49653053249be88218a2025a2d5374e2c5b289784fb47a0f5d1f720b",
    "skeleton-v2.html": "1f58a12aa50e73a08f4ae12f7ef70bc271f39ebfe53a9910eb9ab14104f03125",
}


class SkeletonVersionTest(unittest.TestCase):
    def test_latest_declares_latest_version(self) -> None:
        self.assertEqual(declared_skeleton_version(LATEST), LATEST_SKELETON_VERSION)
        self.assertEqual(LATEST_SKELETON_VERSION, 3)

    def test_missing_attribute_means_v1(self) -> None:
        self.assertEqual(declared_skeleton_version(V1), 1)

    def test_frozen_v2_declares_two(self) -> None:
        self.assertEqual(declared_skeleton_version(V2), 2)

    def test_frozen_skeletons_are_byte_identical_to_their_release(self) -> None:
        for name, digest in FROZEN_SHA256.items():
            data = (ASSETS / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest, name)

    def test_skeleton_file_mapping(self) -> None:
        self.assertEqual(skeleton_file(3, ASSETS), ASSETS / "skeleton.html")
        self.assertEqual(skeleton_file(2, ASSETS), ASSETS / "skeleton-v2.html")
        self.assertEqual(skeleton_file(1, ASSETS), ASSETS / "skeleton-v1.html")

    def test_resolve_returns_given_when_versions_match(self) -> None:
        self.assertIs(resolve_skeleton(LATEST, LATEST, ASSETS), LATEST)

    def test_resolve_loads_frozen_skeletons(self) -> None:
        self.assertEqual(resolve_skeleton(V1, LATEST, ASSETS), V1)
        self.assertEqual(resolve_skeleton(V2, LATEST, ASSETS), V2)

    def test_resolve_unknown_version_is_none(self) -> None:
        doc = LATEST.replace('data-ve-skeleton="3"', 'data-ve-skeleton="9"', 1)
        self.assertIsNone(resolve_skeleton(doc, LATEST, ASSETS))

    def test_v2_first_screen_has_no_viewport_min_height(self) -> None:
        rule = next(line for line in LATEST.splitlines() if line.strip().startswith(".first-screen {"))
        self.assertNotIn("min-height", rule)


class BackwardCompatibilityTest(unittest.TestCase):
    def test_v1_rendered_fixtures_still_pass_against_latest(self) -> None:
        for name in ("matrix-doc-all-notations.html", "chevron-doc.html"):
            raw = (TESTS / name).read_text("utf-8")
            self.assertEqual(declared_skeleton_version(raw), 1, name)
            diags = check_final_document(raw, LATEST, REGISTRY, components_dir=COMPONENTS)
            self.assertEqual([d.message for d in diags], [], name)

    def test_v2_document_passes_both_checkers(self) -> None:
        path = TESTS / "v2-proposal-doc.html"
        raw = path.read_text("utf-8")
        self.assertEqual(declared_skeleton_version(raw), 2)
        diags = check_final_document(raw, LATEST, REGISTRY, components_dir=COMPONENTS)
        self.assertEqual([d.message for d in diags], [])
        proc = subprocess.run(["bash", str(CHECK), str(path)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_unknown_version_document_fails(self) -> None:
        raw = (TESTS / "matrix-doc-all-notations.html").read_text("utf-8").replace(
            '<html lang="ja"', '<html lang="ja" data-ve-skeleton="9"', 1)
        diags = check_final_document(raw, LATEST, REGISTRY, components_dir=COMPONENTS)
        self.assertIn("未知の skeleton 版です: 9", [d.message for d in diags])


class BuildUsesLatestSkeletonTest(unittest.TestCase):
    def test_build_refuses_frozen_skeleton(self) -> None:
        raw = assembly({"conclusion": "限定対象で開始する。"})
        with self.assertRaises(ContractError) as ctx:
            build_document(raw, REGISTRY, TRUSTED_RENDERERS, V2, COMPONENTS, document_path="x.html")
        self.assertEqual([d.message for d in ctx.exception.diagnostics],
                         ["ビルドは最新の skeleton 版（3）だけを使えます: 2"])

    def test_built_document_declares_latest_version(self) -> None:
        raw = assembly({"conclusion": "限定対象で開始する。"})
        html = build_document(raw, REGISTRY, TRUSTED_RENDERERS, LATEST, COMPONENTS, document_path="x.html")
        self.assertEqual(declared_skeleton_version(html), 3)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_skeleton_versions.py -q`
Expected: FAIL（`LATEST_SKELETON_VERSION` が 2、`ビルドは最新の…` が出ない、など）。

- [ ] **Step 4: v3 に上げる**

`assets/skeleton.html` の 2 行目を次にする:
```html
<html lang="ja" data-theme-storage-key="visual-explain-theme" data-ve-skeleton="3">
```
`ve_components/skeletons.py`: `LATEST_SKELETON_VERSION = 3`。

`build_explainer.py` の import に足す:
```python
from ve_components.diagnostics import ContractError, Diagnostic, FINAL_CHECK_FAILURE, FIXED_REGION_MISMATCH  # noqa: E402
from ve_components.skeletons import LATEST_SKELETON_VERSION, declared_skeleton_version  # noqa: E402
```
`build_document` の先頭（`request = validate_assembly(raw_assembly)` の前）に足す:
```python
    declared = declared_skeleton_version(skeleton_text)
    if declared != LATEST_SKELETON_VERSION:
        raise ContractError([Diagnostic(
            FIXED_REGION_MISMATCH,
            f"ビルドは最新の skeleton 版（{LATEST_SKELETON_VERSION}）だけを使えます: {declared}",
        )])
```

`check.sh` の `structure_cases` の末尾に 1 行足す:
```python
        ("v2-proposal-doc.html", ()),
```

- [ ] **Step 5: 見本を再ビルドして通す**

```bash
cd "$(git rev-parse --show-toplevel)"
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/examples/example-proposal.assembly.json \
  --output skills/visual-explain/examples/example-proposal.html
cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest
```
Expected: `OK: …` と `本文 1279 字 / 図より前 87 字 / 図 3 点`。全テスト PASS。`selftest: 32 passed, 0 failed`。

- [ ] **Step 6: Commit**

```bash
git add skills/visual-explain/assets/skeleton-v2.html skills/visual-explain/assets/skeleton.html \
  skills/visual-explain/scripts/ve_components/skeletons.py skills/visual-explain/scripts/build_explainer.py \
  skills/visual-explain/scripts/check.sh skills/visual-explain/scripts/tests/test_skeleton_versions.py \
  skills/visual-explain/scripts/tests/v2-proposal-doc.html skills/visual-explain/examples/example-proposal.html
git commit -m "feat(ve): freeze skeleton v2 and start skeleton v3"
```

---

### Task 2: 問いカードの IR 契約

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/model.py`（`AskOption`, `AskSection`）
- Modify: `skills/visual-explain/scripts/ve_components/validation.py`（230–252 行の定数、`_validate_ask_decision`、`validate_assembly` のセクションループ直後）
- Modify: `skills/visual-explain/scripts/ve_components/document_sections.py`（`no_default_reason` の分岐を削除）
- Modify: `skills/visual-explain/references/assembly.schema.json`（`askOption`, `askDecisionWithDefault`, `askDecisionNoDefault`, `askSection.oneOf`）
- Modify: `skills/visual-explain/scripts/tests/first_screen_ir.py`（`decision_ask()` を追加）
- Modify (fixture 移行): `tests/test_ask_section.py`, `tests/test_assembly_ask_schema.py`, `tests/test_document_checks.py`, `tests/test_decision_panel.py`, `examples/example-proposal.assembly.json`, `references/patterns.md`
- Test: `skills/visual-explain/scripts/tests/test_question_card_validation.py` (create)

**Interfaces:**
- Consumes: `first_screen_ir.assembly(first, *middle)`, `CANONICAL`（id `sec-map`）, `messages(raw) -> list[str]`（Phase 1）。
- Produces:
  - `AskOption(id: str, label: str, tradeoff: str, benefit: str = "", withdrawn: bool = False)`（位置引数の順は従来どおり）。
  - `AskSection(..., evidence: str = "")`。`no_default_reason` は削除。
  - `first_screen_ir.DECISION_EVIDENCE = "scripts/build_explainer.py:1"`、`first_screen_ir.decision_ask(sid="sec-ask-decision", *, question="限定対象で開始しますか？", default="limited", **extra) -> dict`（選択肢 `limited` / `all`）。
  - 診断（すべて `INVALID_COMPONENT_PAYLOAD`）: 下の Step 3 の表どおり。

- [ ] **Step 1: 共有ヘルパを足す** — `tests/first_screen_ir.py` の `narr` の後に追記

```python
DECISION_EVIDENCE = "scripts/build_explainer.py:1"


def decision_ask(sid: str = "sec-ask-decision", *, question: str = "限定対象で開始しますか？",
                 default: str = "limited", **extra) -> dict:
    """A valid question-card decision ask; tests mutate the returned dict."""
    section = {
        "kind": "ask", "id": sid, "askType": "decision", "question": question,
        "evidence": DECISION_EVIDENCE,
        "options": [
            {"id": "limited", "label": "限定対象で公開する", "benefit": "影響範囲を絞れる",
             "tradeoff": "運用が追加で必要"},
            {"id": "all", "label": "一斉公開する", "benefit": "切替が一度で済む",
             "tradeoff": "影響範囲が最初から広い"},
        ],
        "defaultId": default,
    }
    section.update(extra)
    return section
```

- [ ] **Step 2: 失敗するテストを書く** — `tests/test_question_card_validation.py`

```python
"""問いカード（decision ask）の IR 契約: 利点・代償・根拠・推奨・取り下げ・4問上限。"""
from __future__ import annotations

import unittest

from first_screen_ir import CANONICAL, assembly, decision_ask, messages

_PILOT = {"id": "pilot", "label": "試験導入だけする", "benefit": "学びが早い",
          "tradeoff": "効果が見えにくい", "withdrawn": True}


def _one(ask: dict) -> list[str]:
    return messages(assembly({"conclusion": "限定対象で開始する。"}, ask))


class QuestionCardValidationTest(unittest.TestCase):
    def test_valid_card_passes(self) -> None:
        self.assertEqual(_one(decision_ask()), [])

    def test_non_recommended_option_without_benefit_fails(self) -> None:
        ask = decision_ask()
        del ask["options"][1]["benefit"]
        self.assertEqual(_one(ask), ["推奨でない選択肢 'all' にも benefit（選ぶ理由）が必要です"])

    def test_recommended_option_without_benefit_fails(self) -> None:
        ask = decision_ask()
        del ask["options"][0]["benefit"]
        self.assertEqual(_one(ask), ["decision.options[].benefit は空にできません"])

    def test_blank_tradeoff_fails(self) -> None:
        ask = decision_ask()
        ask["options"][1]["tradeoff"] = " "
        self.assertEqual(_one(ask), ["decision.options[].tradeoff は空にできません"])

    def test_missing_evidence_fails(self) -> None:
        ask = decision_ask()
        del ask["evidence"]
        self.assertEqual(_one(ask), ["decision.evidence は空にできません（file:line か実行結果の引用）"])

    def test_evidence_without_location_or_quote_fails(self) -> None:
        self.assertEqual(_one(decision_ask(evidence="たぶん大丈夫")),
                         ["decision.evidence には file:line か「」で囲んだ実行結果の引用が必要です"])

    def test_evidence_accepts_file_line_and_run_quote(self) -> None:
        for evidence in ("ve_components/validation.py:2925", "pytest の結果「1224 passed」"):
            self.assertEqual(_one(decision_ask(evidence=evidence)), [], evidence)

    def test_evidence_over_200_chars_fails(self) -> None:
        self.assertEqual(_one(decision_ask(evidence="a.py:1 " + "あ" * 200)),
                         ["decision.evidence は200字以内です（207字）"])

    def test_no_default_reason_is_retired(self) -> None:
        ask = decision_ask()
        del ask["defaultId"]
        ask["noDefaultReason"] = "判断材料が拮抗しているため"
        self.assertEqual(_one(ask), [
            "decision.noDefaultReason は廃止されました。推奨案を defaultId で示してください",
            "decision には推奨案の defaultId が必要です",
        ])

    def test_missing_default_fails(self) -> None:
        ask = decision_ask()
        del ask["defaultId"]
        self.assertEqual(_one(ask), ["decision には推奨案の defaultId が必要です"])

    def test_withdrawn_option_is_accepted(self) -> None:
        ask = decision_ask()
        ask["options"].append(dict(_PILOT))
        self.assertEqual(_one(ask), [])

    def test_withdrawn_must_be_boolean(self) -> None:
        ask = decision_ask()
        ask["options"][1]["withdrawn"] = "yes"
        self.assertEqual(_one(ask), ["decision.options[].withdrawn は true / false のいずれかです"])

    def test_default_cannot_point_to_withdrawn(self) -> None:
        ask = decision_ask(default="pilot")
        ask["options"].append(dict(_PILOT))
        self.assertEqual(_one(ask), ["decision.defaultId は取り下げた選択肢を指せません"])

    def test_fewer_than_two_active_options_fails(self) -> None:
        ask = decision_ask()
        ask["options"][1]["withdrawn"] = True
        self.assertEqual(_one(ask), ["decision の取り下げていない選択肢は2件以上必要です"])

    def test_four_decision_asks_pass_and_five_fail(self) -> None:
        def doc(n: int) -> dict:
            asks = [decision_ask(f"sec-q{i}", question=f"問い{i}を選びますか？") for i in range(1, n + 1)]
            first = {"conclusion": "限定対象で開始する。",
                     "overview": {"section": "sec-map",
                                  "markers": [{"n": 1, "label": "最初の問い", "target": "sec-q1"}]}}
            return assembly(first, CANONICAL, *asks)
        self.assertEqual(messages(doc(4)), [])
        self.assertEqual(messages(doc(5)), ["decision ask は1資料4問までです（5問）"])

    def test_parsed_section_carries_card_fields(self) -> None:
        from ve_components.model import AskSection
        from ve_components.validation import validate_assembly
        ask = decision_ask()
        ask["options"].append(dict(_PILOT))
        request = validate_assembly(assembly({"conclusion": "限定対象で開始する。"}, ask))
        card = next(s for s in request.sections if isinstance(s, AskSection))
        self.assertEqual(card.evidence, "scripts/build_explainer.py:1")
        self.assertEqual([(o.id, o.benefit, o.withdrawn) for o in card.options], [
            ("limited", "影響範囲を絞れる", False),
            ("all", "切替が一度で済む", False),
            ("pilot", "学びが早い", True),
        ])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_question_card_validation.py -q`
Expected: FAIL（`未知のフィールド 'benefit'` など）。

- [ ] **Step 4: モデルを変える** — `ve_components/model.py`

```python
@dataclass(frozen=True)
class AskOption:
    id: str
    label: str
    tradeoff: str
    benefit: str = ""
    withdrawn: bool = False
```
`AskSection` から `no_default_reason` を削除し、`verify` の後に `evidence: str = ""` を足す。docstring の decision 行を `decision: question + options + default_id (recommended) + evidence` にする。

- [ ] **Step 5: 検証を書く** — `ve_components/validation.py`

定数（230–252 行付近）を次にする:
```python
_ASK_SECTION_KEYS = {
    "kind", "id", "askType", "question", "options", "defaultId", "noDefaultReason", "evidence",
    "steps", "claim", "verify",
}
_ASK_OPTION_KEYS = {"id", "label", "benefit", "tradeoff", "withdrawn"}
_DECISION_ONLY_KEYS = frozenset({"question", "options", "defaultId", "noDefaultReason", "evidence"})
_MAX_DECISION_ASKS = 4
_MAX_EVIDENCE_CHARS = 200
_EVIDENCE_RE = re.compile(r"[^\s:：「」]+:\d+|「[^」]+」")
```
（`noDefaultReason` を既知キーに残すのは、`未知のフィールド` ではなく廃止の診断を出すため。）

`_validate_ask_decision` を丸ごと次に置き換える:
```python
def _validate_ask_decision(raw: dict, path: str, col: DiagnosticCollector) -> AskSection | None:
    before = len(col.diagnostics)
    question = raw.get("question")
    if not _nonblank_str(question):
        col.add(INVALID_COMPONENT_PAYLOAD, "decision.question は空にできません", path)
    evidence = raw.get("evidence")
    if not _nonblank_str(evidence):
        col.add(INVALID_COMPONENT_PAYLOAD,
                "decision.evidence は空にできません（file:line か実行結果の引用）", path)
    elif len(evidence) > _MAX_EVIDENCE_CHARS:
        col.add(INVALID_COMPONENT_PAYLOAD, f"decision.evidence は200字以内です（{len(evidence)}字）", path)
    elif not _EVIDENCE_RE.search(evidence):
        col.add(INVALID_COMPONENT_PAYLOAD,
                "decision.evidence には file:line か「」で囲んだ実行結果の引用が必要です", path)
    if "noDefaultReason" in raw:
        col.add(INVALID_COMPONENT_PAYLOAD,
                "decision.noDefaultReason は廃止されました。推奨案を defaultId で示してください", path)
    default_id = raw.get("defaultId")
    options_raw = raw.get("options")
    options: list[AskOption] = []
    option_ids: set[str] = set()
    if not isinstance(options_raw, list) or len(options_raw) < 2:
        col.add(INVALID_COMPONENT_PAYLOAD, "decision.options は2件以上必要です", path)
    else:
        for i, item in enumerate(options_raw):
            op = f"{path}.options[{i}]"
            if not isinstance(item, dict):
                col.add(INVALID_COMPONENT_PAYLOAD, "decision.options の各要素はオブジェクトである必要があります", op)
                continue
            _check_keys(item, _ASK_OPTION_KEYS, op, col)
            oid = item.get("id")
            accepted_id = False
            if not _nonblank_str(oid):
                col.add(INVALID_COMPONENT_PAYLOAD, "decision.options[].id は空にできません", op)
            elif oid in option_ids:
                col.add(DUPLICATE_SEMANTIC_ID, f"option id '{oid}' が重複しています", op)
            else:
                option_ids.add(oid)
                accepted_id = True
            label = item.get("label")
            if not _nonblank_str(label):
                col.add(INVALID_COMPONENT_PAYLOAD, "decision.options[].label は空にできません", op)
            tradeoff = item.get("tradeoff")
            if not _nonblank_str(tradeoff):
                col.add(INVALID_COMPONENT_PAYLOAD, "decision.options[].tradeoff は空にできません", op)
            benefit = item.get("benefit")
            if not _nonblank_str(benefit):
                if accepted_id and oid != default_id:
                    col.add(INVALID_COMPONENT_PAYLOAD,
                            f"推奨でない選択肢 '{oid}' にも benefit（選ぶ理由）が必要です", op)
                else:
                    col.add(INVALID_COMPONENT_PAYLOAD, "decision.options[].benefit は空にできません", op)
            withdrawn = item.get("withdrawn", False)
            if not isinstance(withdrawn, bool):
                col.add(INVALID_COMPONENT_PAYLOAD,
                        "decision.options[].withdrawn は true / false のいずれかです", op)
                withdrawn = False
            if accepted_id and _nonblank_str(label) and _nonblank_str(tradeoff) and _nonblank_str(benefit):
                options.append(AskOption(id=oid, label=label, tradeoff=tradeoff,
                                         benefit=benefit, withdrawn=withdrawn))
        if len(options) == len(options_raw) and sum(1 for o in options if not o.withdrawn) < 2:
            col.add(INVALID_COMPONENT_PAYLOAD, "decision の取り下げていない選択肢は2件以上必要です", path)
    if default_id is None:
        col.add(INVALID_COMPONENT_PAYLOAD, "decision には推奨案の defaultId が必要です", path)
    elif not _nonblank_str(default_id):
        col.add(INVALID_COMPONENT_PAYLOAD, "decision.defaultId は空にできません", path)
    elif default_id not in option_ids:
        col.add(INVALID_COMPONENT_PAYLOAD, f"decision.defaultId '{default_id}' が options にありません", path)
    elif any(o.id == default_id and o.withdrawn for o in options):
        col.add(INVALID_COMPONENT_PAYLOAD, "decision.defaultId は取り下げた選択肢を指せません", path)
    if len(col.diagnostics) > before:
        return None
    return AskSection(id=raw["id"], ask_type="decision", question=question,
                      options=tuple(options), default_id=default_id, evidence=evidence)
```

`validate_assembly` のセクションループ（`for i, item in enumerate(sections_raw): …`）の直後、`_validate_document_structure(sections_raw, col)` の前に足す:
```python
    decision_count = sum(1 for s in sections if isinstance(s, AskSection) and s.ask_type == "decision")
    if decision_count > _MAX_DECISION_ASKS:
        col.add(INVALID_COMPONENT_PAYLOAD, f"decision ask は1資料4問までです（{decision_count}問）",
                "assembly.sections")
```

- [ ] **Step 6: 描画側の参照を外す** — `ve_components/document_sections.py`

`_render_decision_body` の `reason = ""` 〜 `if section.no_default_reason: …` の 4 行を削除し、返り値の `f"  </ul>{reason}{memo}\n"` を `f"  </ul>{memo}\n"` にする。`_render_panel_ask_item` の `status = …` を次にする（推奨は常にある）:
```python
    status = f"未選択（既定案: {default_label}）"
```
`grep -rn "no_default_reason\|noDefaultReason" skills/visual-explain/scripts/ve_components` が、`validation.py` の既知キーと廃止診断、`checker.py` の `no_default_reason_texts`（v1/v2 生成物の `ask-no-default-reason` 検査。残す）だけになること。`model.py` の docstring の `(default_id XOR no_default_reason)` も Step 4 で消えていること。

- [ ] **Step 7: schema を更新する**

```bash
cd skills/visual-explain && python3 - <<'PY'
import json
from pathlib import Path
path = Path("references/assembly.schema.json")
schema = json.loads(path.read_text("utf-8"))
d = schema["$defs"]
d["askOption"]["required"] = ["id", "label", "benefit", "tradeoff"]
d["askOption"]["properties"] = {
    "id": {"type": "string", "minLength": 1},
    "label": {"type": "string", "minLength": 1},
    "benefit": {"type": "string", "minLength": 1},
    "tradeoff": {"type": "string", "minLength": 1},
    "withdrawn": {"type": "boolean"},
}
branch = d["askDecisionWithDefault"]
branch["required"] = ["kind", "id", "askType", "question", "evidence", "options", "defaultId"]
branch["properties"]["evidence"] = {"type": "string", "minLength": 1, "maxLength": 200}
del d["askDecisionNoDefault"]
d["askSection"]["oneOf"] = [b for b in d["askSection"]["oneOf"] if b["$ref"] != "#/$defs/askDecisionNoDefault"]
path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", "utf-8")
PY
git diff --stat references/assembly.schema.json
```
Expected: diff は ask 関連の定義だけ（整形差分が全体に出た場合は `git checkout` で戻し、元ファイルのインデント幅に合わせて `indent=` を変えて再実行する）。

- [ ] **Step 8: 既存の decision ask をすべて決定的に移行する**

規則（例外なし）: すべての decision ask 辞書に `"evidence": "scripts/build_explainer.py:1"` を足し、その中の各選択肢 `{"id": …, "label": …, "tradeoff": …}` に `"benefit": "選ぶ理由がある"` を足す。対象は `grep -n '"tradeoff"' skills/visual-explain/scripts/tests/test_*.py` が出す全行（`test_assembly_ask_schema.py` / `test_ask_section.py` / `test_document_checks.py` / `test_decision_panel.py`）。`AskOption(...)` の位置引数の生成はそのままでよい（`benefit` は既定値 `""`）。

個別の書き換え:
- `test_ask_section.py`: `test_decision_without_default_renders_no_default_reason` を次に置き換える。
```python
    def test_decision_with_no_default_reason_is_rejected(self) -> None:
        section = _decision_section(noDefaultReason="判断材料が拮抗しているため")
        del section["defaultId"]
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(section))
        self.assertIn("decision.noDefaultReason は廃止されました。推奨案を defaultId で示してください",
                      [d.message for d in ctx.exception.diagnostics])
```
  `test_digest_depends_only_on_decision_contract` の `no_default_reason="理由"` 2 か所を `default_id="a"` にする。`test_decision_happy_path_renders_and_passes_ask_inspector` の `self.assertIsNone(section.no_default_reason)` を `self.assertEqual(section.evidence, "scripts/build_explainer.py:1")` にする。`test_default_id_and_no_default_reason_together_fail` はそのまま（廃止診断に `noDefaultReason` が含まれるので通る）。
- 移行後に `grep -rn "noDefaultReason\|no_default_reason" skills/visual-explain/scripts/tests/*.py` を実行し、残りが `test_ask_section.py` の 2 テスト（廃止の確認）と `test_assembly_ask_schema.py` の 2 辞書（schema が拒否することの確認）だけであること。
- `test_assembly_ask_schema.py`: `test_decision_requires_question_options_and_exactly_one_default_field` の `self.assertTrue(schema_accepts_ask(with_reason))` を `self.assertFalse(schema_accepts_ask(with_reason))` にし、`with_default` に `"evidence": "scripts/build_explainer.py:1"` を足す。`test_decision_id_and_option_id_have_no_ascii_token_pattern` のループを `for name in ("askDecisionWithDefault",):` にする。
- `test_decision_panel.py`: `test_status_reports_no_default_when_absent` を削除する。
- `examples/example-proposal.assembly.json` の `sec-ask-decision` に次を足す（`question` の直後に `evidence`、各選択肢に `benefit`）:
```json
"evidence": "照合シートの試算「契約例外 12 件のうち 9 件が同じ顧客群に集中」",
```
```json
{"id": "limited", "label": "限定対象で段階公開する", "benefit": "誤りの影響を限定対象に閉じたまま照合の効果を確かめられる", "tradeoff": "対象選定と承認・顧客対応の運用を追加で用意する必要がある"},
{"id": "all", "label": "全顧客へ一斉公開する", "benefit": "告知と請求の切替が一度で済み運用が二重にならない", "tradeoff": "例外や計算誤りの影響範囲が最初から全顧客に及ぶ"}
```
- `references/patterns.md`: 2 つの decision ask の JSON（160 行付近の完全例と 297 行付近の `decision` 断片）に同じ規則で `evidence` と `benefit` を足す。295 行の説明文を次に置き換える:
```markdown
`decision`（問いカード）。選択肢は2件以上で、各選択肢に `benefit`（利点）と `tradeoff`（代償）を必ず書く。推奨は `defaultId`（必須。取り下げた選択肢は指せない）で、カードに「推奨」バッジが付く。読者が選ばなければ「お任せ＝推奨」として回収される。`evidence` には `file:line` か「」で囲んだ実行結果の引用を 200 字以内で書く（事実を読者に聞かないため）。再往復で捨てた案は `"withdrawn": true` で残す（取り消し線付きで表示され、選べない）。decision ask は1資料4問まで。
```

- [ ] **Step 9: 通す**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest`
Expected: 全件 PASS、`selftest: 32 passed, 0 failed`。見本の HTML は描画が変わらないため再ビルド不要（`test_checked_in_html_matches_fresh_build` が PASS すること）。

- [ ] **Step 10: Commit**

```bash
git add skills/visual-explain/scripts/ve_components/model.py skills/visual-explain/scripts/ve_components/validation.py \
  skills/visual-explain/scripts/ve_components/document_sections.py skills/visual-explain/references/assembly.schema.json \
  skills/visual-explain/references/patterns.md skills/visual-explain/examples/example-proposal.assembly.json \
  skills/visual-explain/scripts/tests/first_screen_ir.py skills/visual-explain/scripts/tests/test_question_card_validation.py \
  skills/visual-explain/scripts/tests/test_ask_section.py skills/visual-explain/scripts/tests/test_assembly_ask_schema.py \
  skills/visual-explain/scripts/tests/test_document_checks.py skills/visual-explain/scripts/tests/test_decision_panel.py
git commit -m "feat(ve): require benefit, tradeoff, evidence, and a recommendation on decision asks"
```

---

### Task 3: 問いカードの描画と見た目

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/document_sections.py`（`_render_decision_body`）
- Modify: `skills/visual-explain/assets/skeleton.html`（`<style>` 内の `.ask` 規則群）
- Modify: `skills/visual-explain/scripts/tests/test_ask_section.py`（`test_decision_renders_static_memo_field` の文言）
- Modify: `skills/visual-explain/examples/example-proposal.html`（再ビルド）
- Test: `skills/visual-explain/scripts/tests/test_question_card_render.py` (create)

**Interfaces:**
- Consumes: `AskOption.benefit/withdrawn`, `AskSection.evidence`, `AskSection.default_id`（Task 2）。
- Produces（Task 6 の収集 JS が読む DOM 契約）:
  - 選択肢 `li[data-ask-option][data-ask-option-id]`。推奨は `data-ask-default`、取り下げは `data-ask-withdrawn`。
  - ラベルは `.ask-option-label`、利点 `.ask-benefit`（「利点: 」接頭）、代償 `.ask-tradeoff`（「代償: 」接頭）、推奨バッジ `.ask-badge`、取り下げ注記 `.ask-withdrawn-note`。
  - 問い `p.ask-question` の直後に `p.ask-evidence`（「根拠: 」接頭）。補足欄 `textarea[data-ask-memo]`。
  - CSS クラス `.ask-card-status`（Task 6 の JS が作る状態行）。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_question_card_render.py`

```python
"""問いカードの描画: 推奨バッジ・利点/代償・根拠・取り下げ・補足欄。"""
from __future__ import annotations

import unittest
from pathlib import Path

from ve_components.checker import validate_ask_blocks
from ve_components.document_sections import render_ask
from ve_components.model import AskOption, AskSection

SKELETON = (Path(__file__).resolve().parents[2] / "assets" / "skeleton.html").read_text("utf-8")
STYLE = SKELETON.split("<style>", 1)[1].split("</style>", 1)[0]

CARD = AskSection(
    id="sec-ask-decision", ask_type="decision", question="限定対象で開始しますか？",
    options=(
        AskOption("limited", "限定対象で公開する", "運用が追加で必要", benefit="影響範囲を絞れる"),
        AskOption("all", "一斉公開する", "影響範囲が最初から広い", benefit="切替が一度で済む"),
        AskOption("pilot", "試験導入だけする", "効果が見えにくい", benefit="学びが早い", withdrawn=True),
    ),
    default_id="limited",
    evidence="scripts/build_explainer.py:1",
)


class QuestionCardRenderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.markup = render_ask(CARD).markup

    def test_recommended_option_has_badge_benefit_and_tradeoff(self) -> None:
        self.assertIn(
            '<li data-ask-option data-ask-option-id="limited" data-ask-default>'
            '<span class="ask-option-head"><span class="ask-option-label">限定対象で公開する</span>'
            '<span class="ask-badge">推奨</span></span>'
            '<span class="ask-benefit">利点: 影響範囲を絞れる</span>'
            '<span class="ask-tradeoff">代償: 運用が追加で必要</span></li>',
            self.markup)

    def test_other_option_has_no_badge(self) -> None:
        self.assertIn(
            '<li data-ask-option data-ask-option-id="all">'
            '<span class="ask-option-head"><span class="ask-option-label">一斉公開する</span></span>',
            self.markup)

    def test_withdrawn_option_is_marked(self) -> None:
        self.assertIn(
            '<li data-ask-option data-ask-option-id="pilot" data-ask-withdrawn>'
            '<span class="ask-option-head"><span class="ask-option-label">試験導入だけする</span>'
            '<span class="ask-withdrawn-note">取り下げ</span></span>',
            self.markup)

    def test_evidence_line_follows_question(self) -> None:
        self.assertIn(
            '<p class="ask-question">限定対象で開始しますか？</p>\n'
            '  <p class="ask-evidence">根拠: scripts/build_explainer.py:1</p>',
            self.markup)

    def test_memo_label_is_supplement(self) -> None:
        self.assertIn('<label>補足（任意）<textarea data-ask-memo></textarea></label>', self.markup)

    def test_card_passes_ask_inspector(self) -> None:
        self.assertEqual(validate_ask_blocks(self.markup), [])


class QuestionCardStyleTest(unittest.TestCase):
    def test_badge_uses_positive_tint(self) -> None:
        self.assertIn(
            ".ask-badge { padding: 0 var(--space-1); border-radius: 999px; color: var(--positive); "
            "background: color-mix(in srgb, var(--positive) 12%, var(--surface)); font-size: var(--fs-small); }",
            STYLE)

    def test_withdrawn_label_is_struck_through(self) -> None:
        self.assertIn(".ask-options [data-ask-withdrawn] .ask-option-label { text-decoration: line-through; }", STYLE)

    def test_legacy_default_marker_is_gone(self) -> None:
        self.assertNotIn('content: "既定案"', STYLE)

    def test_all_ask_cards_share_a_border(self) -> None:
        self.assertRegex(STYLE, r"\.ask \{[^}]*border: 1px solid var\(--border\);")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_question_card_render.py -q`
Expected: FAIL（旧マークアップ）。

- [ ] **Step 3: 描画を書く** — `_render_decision_body` を丸ごと次に置き換える

```python
def _render_decision_body(section: AskSection, kind_label: str) -> str:
    options_html: list[str] = []
    for opt in section.options:
        attrs = f'data-ask-option data-ask-option-id="{_esc(opt.id)}"'
        badge = ""
        if opt.id == section.default_id:
            attrs += " data-ask-default"
            badge = '<span class="ask-badge">推奨</span>'
        if opt.withdrawn:
            attrs += " data-ask-withdrawn"
            badge = '<span class="ask-withdrawn-note">取り下げ</span>'
        options_html.append(
            f"<li {attrs}>"
            f'<span class="ask-option-head"><span class="ask-option-label">{_esc(opt.label)}</span>{badge}</span>'
            f'<span class="ask-benefit">利点: {_esc(opt.benefit)}</span>'
            f'<span class="ask-tradeoff">代償: {_esc(opt.tradeoff)}</span>'
            "</li>"
        )
    memo = (
        '\n  <div class="ask-memo">'
        '<label>補足（任意）<textarea data-ask-memo></textarea></label></div>'
    )
    return (
        f'<div class="ask" data-ask="decision">\n'
        f'  <p class="ask-kind">{_esc(kind_label)}</p>\n'
        f'  <p class="ask-question">{_esc(section.question or "")}</p>\n'
        f'  <p class="ask-evidence">根拠: {_esc(section.evidence)}</p>\n'
        f'  <ul class="ask-options">\n'
        f'    {"".join(options_html)}\n'
        f"  </ul>{memo}\n"
        f"</div>"
    )
```
`test_ask_section.py` の `test_decision_renders_static_memo_field` の `'メモ（この判断について）'` を `'補足（任意）'` にする。

- [ ] **Step 4: skeleton の CSS を書く** — `assets/skeleton.html` の `<style>` 内

`.ask { … }` の行を次にする（他の ask もこの枠で揃う）:
```css
    .ask { max-width: var(--w-narrative); margin: var(--space-3) 0; padding: var(--space-3); background: var(--surface); border: 1px solid var(--border); border-radius: .5rem; }
```
次の 4 行
```css
    .ask-options [data-ask-option] { display: grid; grid-template-columns: minmax(8rem, .35fr) 1fr; gap: var(--space-2); padding: var(--space-1); border-radius: .3rem; }
    .ask-options [data-ask-default] { background: color-mix(in srgb, var(--positive) 12%, var(--surface)); }
    .ask-options [data-ask-default] > :first-child::after { content: "既定案"; margin-left: var(--space-1); color: var(--positive); font-size: var(--fs-small); font-weight: 700; }
    .ask-tradeoff, .ask-no-default-reason { color: var(--text-dim); }
```
を次に置き換える:
```css
    .ask-options [data-ask-option] { display: grid; grid-template-columns: 1fr; gap: 0; padding: var(--space-1) var(--space-2); background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); cursor: pointer; }
    .ask-option-head { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-1); font-weight: 700; }
    .ask-option-head::before { content: ""; flex: none; width: .9rem; height: .9rem; border: 2px solid var(--text-dim); border-radius: 50%; }
    .ask-options [data-ask-option][data-ask-selected] .ask-option-head::before { border-color: var(--accent); background: var(--accent); box-shadow: inset 0 0 0 2px var(--bg); }
    .ask-badge { padding: 0 var(--space-1); border-radius: 999px; color: var(--positive); background: color-mix(in srgb, var(--positive) 12%, var(--surface)); font-size: var(--fs-small); }
    .ask-benefit, .ask-tradeoff, .ask-no-default-reason { color: var(--text-dim); font-size: var(--fs-figure); }
    .ask-options [data-ask-withdrawn] { cursor: not-allowed; color: var(--text-faint); background: transparent; }
    .ask-options [data-ask-withdrawn] .ask-option-label { text-decoration: line-through; }
    .ask-options [data-ask-withdrawn] .ask-option-head::before { border-style: dashed; border-color: var(--text-faint); }
    .ask-withdrawn-note { color: var(--text-faint); font-size: var(--fs-small); font-weight: 400; }
    .ask-evidence { margin: 0 0 var(--space-2); color: var(--text-dim); font-size: var(--fs-small); }
    .ask-card-status { margin: var(--space-1) 0 0; color: var(--text-dim); font-size: var(--fs-small); }
```
既存の `.ask-options [data-ask-option][data-ask-selected] { box-shadow: …; background: … }`、`:focus-visible` 規則、42rem 以下の `.ask-options [data-ask-option] { grid-template-columns: 1fr; gap: var(--space-1); }` は残す（`test_skeleton_audit.py` が固定している）。

- [ ] **Step 5: 見本を再ビルドして通す**

```bash
cd "$(git rev-parse --show-toplevel)"
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/examples/example-proposal.assembly.json \
  --output skills/visual-explain/examples/example-proposal.html
cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest
```
Expected: 本文は 1,400 字以下（目安 1,360 字前後）。超えたら見本 IR の `benefit` を短くして再ビルドする。全テスト PASS（`test_skeleton_audit.py` の格子監査・意味色 allowlist・コントラストを含む）、`selftest: 32 passed, 0 failed`。

- [ ] **Step 6: Commit**

```bash
git add skills/visual-explain/scripts/ve_components/document_sections.py skills/visual-explain/assets/skeleton.html \
  skills/visual-explain/scripts/tests/test_question_card_render.py skills/visual-explain/scripts/tests/test_ask_section.py \
  skills/visual-explain/examples/example-proposal.html
git commit -m "feat(ve): render decision asks as question cards with a recommendation badge"
```

---

### Task 4: 指摘層のブロック番号（`data-ve-blk`）

**Files:**
- Create: `skills/visual-explain/scripts/ve_components/review_blocks.py`
- Modify: `skills/visual-explain/scripts/build_explainer.py`（`build_document` の `compose_sections` の直後）
- Modify: `skills/visual-explain/scripts/ve_components/document_checks.py`（`check_document_structure`）
- Modify: `skills/visual-explain/scripts/ve_components/checker.py`（`check_final_document` の `check_document_structure` 呼び出し）
- Modify: `skills/visual-explain/scripts/ve_components/validation.py`（`_validate_compatibility_section`）
- Modify: `skills/visual-explain/scripts/tests/test_closing_section.py`（113–116 行）
- Modify: `skills/visual-explain/scripts/tests/test_document_checks.py`（269 行）, `tests/test_expected_record_plumbing.py`（99 行）, `tests/test_narrative_sections.py`（`_build_composition_and_document` と `test_manifest_to_dom_flags_narrative_section_removed_from_final_dom`）
- Modify: `skills/visual-explain/examples/example-proposal.html`（再ビルド）
- Test: `skills/visual-explain/scripts/tests/test_review_blocks.py` (create)

**Interfaces:**
- Consumes: `first_screen_ir.assembly / narr / decision_ask`（Task 2）、`declared_skeleton_version`（Phase 1）。
- Produces:
  - `review_blocks.BLOCK_ATTR = "data-ve-blk"`、`BLOCK_TAGS: frozenset[str]`。
  - `stamp_review_blocks(markup: str, start: int = 1) -> tuple[str, int]`（付与後の markup と次の番号）。
  - `stamp_review_sections(markups: tuple[str, ...]) -> tuple[str, ...]`。
  - `check_review_blocks(content: str) -> list[Diagnostic]`（`DOCUMENT_STRUCTURE_VIOLATION`、path `"content"`）。診断文言:
    - `data-ve-blk は p / h2 / h3 / li / figure / blockquote / pre / table にだけ付けられます: <{tag}>`
    - `data-ve-blk を付けられない位置にあります: <{tag}>`
    - `data-ve-blk は1からの連番である必要があります（{k} 番目のブロックが {actual}）`（`actual` は値、無ければ `なし`）
  - `check_document_structure(content_markup, *, title=None, expected=None, skeleton_version: int = 1)`。
  - validation 診断 `compatibility に data-ve-blk は書けません（ビルドが付与します）`（`INVALID_COMPATIBILITY_PROVENANCE`）。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_review_blocks.py`

```python
"""指摘層のブロック番号: ビルドの付与と checker の再計算が同じ規則で一致する。"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from build_explainer import build_document
from first_screen_ir import assembly, decision_ask, messages, narr
from ve_components.checker import check_final_document
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.review_blocks import check_review_blocks, stamp_review_blocks

SKILL = Path(__file__).resolve().parents[2]
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS = SKILL / "assets" / "components"
REGISTRY = load_registry(COMPONENTS / "registry.json")
TAGS = "p / h2 / h3 / li / figure / blockquote / pre / table"


def _msgs(content: str) -> list[str]:
    return [d.message for d in check_review_blocks(content)]


def _build(raw: dict) -> str:
    return build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS, document_path="x.html")


class StampTest(unittest.TestCase):
    def test_attribute_goes_before_closing_bracket(self) -> None:
        self.assertEqual(stamp_review_blocks('<p class="x">a</p><h2>b</h2>'),
                         ('<p class="x" data-ve-blk="1">a</p><h2 data-ve-blk="2">b</h2>', 3))

    def test_start_offset(self) -> None:
        self.assertEqual(stamp_review_blocks("<p>a</p>", start=5), ('<p data-ve-blk="5">a</p>', 6))

    def test_nested_list_items_in_dom_order(self) -> None:
        stamped, _ = stamp_review_blocks("<ul><li>a<ul><li>b</li></ul></li><li>c</li></ul>")
        self.assertEqual(re.findall(r'data-ve-blk="(\d+)"', stamped), ["1", "2", "3"])

    def test_figure_is_one_block(self) -> None:
        stamped, _ = stamp_review_blocks(
            "<figure><table><tr><td><p>x</p></td></tr></table><figcaption>c</figcaption></figure><p>y</p>")
        self.assertEqual(stamped,
                         '<figure data-ve-blk="1"><table><tr><td><p>x</p></td></tr></table>'
                         '<figcaption>c</figcaption></figure><p data-ve-blk="2">y</p>')

    def test_stepper_subtree_is_not_numbered(self) -> None:
        markup = '<div data-stepper><div data-step="1"><figure>f</figure><p class="ve-seq-next">n</p></div></div>'
        self.assertEqual(stamp_review_blocks(markup), (markup, 1))

    def test_question_card_ui_parts_are_skipped(self) -> None:
        markup = (
            '<div class="ask" data-ask="decision"><p class="ask-kind">判断してください</p>'
            '<p class="ask-question">Q？</p><ul class="ask-options">'
            '<li data-ask-option data-ask-option-id="a"><span>A</span></li></ul>'
            '<div class="ask-memo"><label>補足<textarea data-ask-memo></textarea></label></div></div>')
        stamped, nxt = stamp_review_blocks(markup)
        self.assertEqual(nxt, 2)
        self.assertIn('<p class="ask-question" data-ve-blk="1">', stamped)
        self.assertIn('<p class="ask-kind">', stamped)
        self.assertIn('<li data-ask-option data-ask-option-id="a">', stamped)

    def test_collection_panel_is_skipped(self) -> None:
        markup = '<section data-ve-section-kind="decision-panel"><h2>回収</h2><p>x</p></section>'
        self.assertEqual(stamp_review_blocks(markup), (markup, 1))


class CheckTest(unittest.TestCase):
    def test_contiguous_numbers_pass(self) -> None:
        self.assertEqual(_msgs('<p data-ve-blk="1">a</p><p data-ve-blk="2">b</p>'), [])

    def test_missing_number(self) -> None:
        self.assertEqual(_msgs('<p data-ve-blk="1">a</p><p>b</p>'),
                         ["data-ve-blk は1からの連番である必要があります（2 番目のブロックが なし）"])

    def test_duplicate_number(self) -> None:
        self.assertEqual(_msgs('<p data-ve-blk="1">a</p><p data-ve-blk="1">b</p>'),
                         ["data-ve-blk は1からの連番である必要があります（2 番目のブロックが 1）"])

    def test_gap_reports_first_mismatch_only(self) -> None:
        self.assertEqual(_msgs('<p data-ve-blk="1">a</p><p data-ve-blk="3">b</p><p data-ve-blk="4">c</p>'),
                         ["data-ve-blk は1からの連番である必要があります（2 番目のブロックが 3）"])

    def test_wrong_tag(self) -> None:
        self.assertEqual(_msgs('<div data-ve-blk="1">a</div>'),
                         [f"data-ve-blk は {TAGS} にだけ付けられます: <div>"])

    def test_excluded_position(self) -> None:
        self.assertEqual(
            _msgs('<section data-ve-section-kind="decision-panel"><p data-ve-blk="1">x</p></section>'),
            ["data-ve-blk を付けられない位置にあります: <p>"])


class BuildTest(unittest.TestCase):
    def test_built_document_numbers_blocks_from_one(self) -> None:
        html = _build(assembly({"conclusion": "限定対象で開始する。"}, narr("sec-a", "現状の確認"), decision_ask()))
        values = [int(v) for v in re.findall(r'data-ve-blk="(\d+)"', html)]
        self.assertEqual(values, list(range(1, len(values) + 1)))
        self.assertIn('<p class="conclusion" data-ve-blk="1">', html)
        self.assertNotIn("<h1 data-ve-blk", html)
        self.assertEqual(check_final_document(html, SKELETON, REGISTRY, components_dir=COMPONENTS), [])

    def test_tampered_numbering_fails_final_check(self) -> None:
        html = _build(assembly({"conclusion": "限定対象で開始する。"}, narr("sec-a", "現状の確認")))
        tampered = html.replace(' data-ve-blk="2"', ' data-ve-blk="3"', 1)
        msgs = [d.message for d in check_final_document(tampered, SKELETON, REGISTRY, components_dir=COMPONENTS)]
        self.assertEqual(msgs, ["data-ve-blk は1からの連番である必要があります（2 番目のブロックが 3）"])

    def test_compatibility_cannot_carry_block_numbers(self) -> None:
        compat = {"kind": "compatibility", "id": "sec-c",
                  "markup": '<div class="figure"><p data-ve-blk="1">x</p></div>',
                  "provenance": {"source": "legacy-html-insertion", "reason": "unmigrated-format",
                                 "format": "layers"}}
        self.assertIn("compatibility に data-ve-blk は書けません（ビルドが付与します）",
                      messages(assembly({"conclusion": "限定対象で開始する。"}, compat)))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_review_blocks.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 've_components.review_blocks'`）。

- [ ] **Step 3: `ve_components/review_blocks.py` を書く**

```python
"""Review-layer block numbering shared by the build (stamp) and the checker.

Both sides walk content markup with the same eligibility rules, so a document
passes only when every eligible block carries its 1-based DOM ordinal in
``data-ve-blk`` and no other element carries the attribute.
"""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

from .diagnostics import DOCUMENT_STRUCTURE_VIOLATION, Diagnostic

BLOCK_ATTR = "data-ve-blk"
BLOCK_TAGS = frozenset({"p", "h2", "h3", "li", "figure", "blockquote", "pre", "table"})
_TAG_LIST = "p / h2 / h3 / li / figure / blockquote / pre / table"
_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})


@dataclass(frozen=True)
class BlockSite:
    tag: str
    insert_at: int        # source index just before the start tag's ">" (or "/>")
    eligible: bool        # must carry the next ordinal
    value: str | None     # current data-ve-blk value, if present


def _starts_excluded_subtree(tag: str, attrs: dict[str, str]) -> bool:
    """UI parts and duplicated stepper panels never get a number, nor do their descendants."""
    classes = set(attrs.get("class", "").split())
    return (
        (tag == "section" and attrs.get("data-ve-section-kind") == "decision-panel")
        or "data-ask-option" in attrs
        or "data-stepper" in attrs
        or "ask-kind" in classes
        or "ask-memo" in classes
        or tag in {"svg", "template", "script", "style"}
    )


class _BlockWalker(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self._line_starts = [0]
        for index, char in enumerate(source):
            if char == "\n":
                self._line_starts.append(index + 1)
        self._stack: list[tuple[str, bool]] = []  # (tag, descendants_excluded)
        self.sites: list[BlockSite] = []

    def handle_starttag(self, tag, attrs):
        self._visit(tag, attrs, self_closing=False)

    def handle_startendtag(self, tag, attrs):
        self._visit(tag, attrs, self_closing=True)

    def handle_endtag(self, tag):
        tag = tag.lower()
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                return

    def _visit(self, tag: str, attrs, *, self_closing: bool) -> None:
        tag = tag.lower()
        attr_map: dict[str, str] = {}
        for name, value in attrs:
            attr_map.setdefault(name.lower(), value or "")
        inherited = bool(self._stack) and self._stack[-1][1]
        excluded = inherited or _starts_excluded_subtree(tag, attr_map)
        if tag in BLOCK_TAGS or BLOCK_ATTR in attr_map:
            self.sites.append(BlockSite(
                tag=tag,
                insert_at=self._insert_position(),
                eligible=tag in BLOCK_TAGS and not excluded,
                value=attr_map.get(BLOCK_ATTR),
            ))
        if not self_closing and tag not in _VOID_TAGS:
            self._stack.append((tag, excluded or tag == "figure"))

    def _insert_position(self) -> int:
        line, col = self.getpos()
        start = self._line_starts[line - 1] + col
        text = self.get_starttag_text() or ""
        trim = 2 if text.endswith("/>") else 1
        return start + len(text) - trim


def _walk(markup: str) -> list[BlockSite]:
    walker = _BlockWalker(markup)
    walker.feed(markup)
    walker.close()
    return walker.sites


def stamp_review_blocks(markup: str, start: int = 1) -> tuple[str, int]:
    """Insert ``data-ve-blk`` on every eligible block; return (markup, next ordinal)."""
    pieces: list[str] = []
    cursor = 0
    number = start
    for site in _walk(markup):
        if not site.eligible:
            continue
        pieces.append(markup[cursor:site.insert_at])
        pieces.append(f' {BLOCK_ATTR}="{number}"')
        cursor = site.insert_at
        number += 1
    pieces.append(markup[cursor:])
    return "".join(pieces), number


def stamp_review_sections(markups: tuple[str, ...]) -> tuple[str, ...]:
    """Number blocks across ordered section markups as one document."""
    stamped: list[str] = []
    number = 1
    for markup in markups:
        text, number = stamp_review_blocks(markup, number)
        stamped.append(text)
    return tuple(stamped)


def check_review_blocks(content: str) -> list[Diagnostic]:
    """Re-derive the expected numbering and report every deviation (first sequence break only)."""
    diagnostics: list[Diagnostic] = []
    expected = 0
    sequence_reported = False
    for site in _walk(content):
        if site.tag not in BLOCK_TAGS:
            diagnostics.append(Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION,
                f"data-ve-blk は {_TAG_LIST} にだけ付けられます: <{site.tag}>", "content"))
            continue
        if not site.eligible:
            if site.value is not None:
                diagnostics.append(Diagnostic(
                    DOCUMENT_STRUCTURE_VIOLATION,
                    f"data-ve-blk を付けられない位置にあります: <{site.tag}>", "content"))
            continue
        expected += 1
        if site.value != str(expected) and not sequence_reported:
            actual = site.value if site.value is not None else "なし"
            diagnostics.append(Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION,
                f"data-ve-blk は1からの連番である必要があります（{expected} 番目のブロックが {actual}）",
                "content"))
            sequence_reported = True
    return diagnostics
```

- [ ] **Step 4: ビルドと checker に配線する**

`build_explainer.py`: import に `from dataclasses import dataclass, replace` と `from ve_components.review_blocks import stamp_review_sections  # noqa: E402` を足し、`composition = compose_sections(items)` の直後に足す:
```python
    composition = replace(composition, sections_markup=stamp_review_sections(composition.sections_markup))
```

`document_checks.py`: import に `from .review_blocks import check_review_blocks` を足す。`check_document_structure` のシグネチャを次にする:
```python
def check_document_structure(
    content_markup: str,
    *,
    title: str | None = None,
    expected=None,
    skeleton_version: int = 1,
) -> list[Diagnostic]:
```
`if structure.misplaced_reserved_attrs: … return diagnostics` ブロックの直後に足す:
```python
    if skeleton_version >= 3:
        diagnostics.extend(check_review_blocks(content_markup))
```
docstring に「`skeleton_version` は文書が宣言する skeleton 版。省略時 1（旧規則）。3 以上でブロック番号を検査する」を英語で 1 文足す。

`checker.py` の `check_final_document` で呼び出しを次にする（`skel` は解決済みの skeleton。未知版のときは最新版の版になる）:
```python
        structure_diagnostics = check_document_structure(
            content, title=_extract_title_text(text), expected=expected_records,
            skeleton_version=declared_skeleton_version(skel),
        )
```

`validation.py`: 定数に `_BLOCK_ATTR_RE = re.compile(r"\sdata-ve-blk\b", re.IGNORECASE)` を足し、`_validate_compatibility_section` の `elif isinstance(markup, str):` ブロックの `scan_author_markup_bans` ループの後に足す:
```python
        if _BLOCK_ATTR_RE.search(markup):
            col.add(INVALID_COMPATIBILITY_PROVENANCE,
                    "compatibility に data-ve-blk は書けません（ビルドが付与します）", path)
```

- [ ] **Step 5: 番号付与で変わる既存アサーションを直す**

`tests/test_closing_section.py` 113–116 行（ビルド済み文書を見ている 4 行）を次にする:
```python
        self.assertRegex(html, r'<h2 data-ve-blk="\d+">リスクと弱い前提</h2>')
        self.assertRegex(html, r'<h2 data-ve-blk="\d+">不確かな点</h2>')
        self.assertRegex(html, r'<li data-ve-blk="\d+">前提Aが弱い</li>')
        self.assertRegex(html, r'<li data-ve-blk="\d+">未確認の利用状況</li>')
```
`tests/test_document_checks.py` の `test_missing_summary_is_diagnosed`（269 行）は結論段落を文字列置換で消しているので、置換元を番号付きの形にする:
```python
            '<p class="conclusion" data-ve-blk="1"><strong>結論:</strong> この提案を採択するか決めます。</p>',
```
（`render_*` を直接呼ぶテストは番号付与を通らないので変えない。`test_overview_nav.py` 34 行は `render_first_screen` の出力なので変えない。）

`tests/test_expected_record_plumbing.py` の差し替え関数のシグネチャを新しい引数に合わせる:
```python
    def recording_check(content_markup: str, *, title=None, expected=None, skeleton_version=1):
```

`tests/test_narrative_sections.py` の `_build_composition_and_document` は build_document の手順を手で再現しているので、番号付与も再現する。import に `from dataclasses import replace` と `from ve_components.review_blocks import stamp_review_sections` を足し、`composition = compose_sections(items)` の直後に足す:
```python
    composition = replace(composition, sections_markup=stamp_review_sections(composition.sections_markup))
```
同じファイルの `test_manifest_to_dom_flags_narrative_section_removed_from_final_dom` は、番号付き markup を消すようにする（`removed.markup` は番号付与前の文字列なので文書に現れない）:
```python
    removed = composition.narrative[-1]
    stamped = next(m for m in composition.sections_markup
                   if f'data-ve-instance="{removed.instance_id}"' in m)
    mutated = document.replace(stamped, "")
```

- [ ] **Step 6: 見本を再ビルドして通す**

```bash
cd "$(git rev-parse --show-toplevel)"
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/examples/example-proposal.assembly.json \
  --output skills/visual-explain/examples/example-proposal.html
cd skills/visual-explain/scripts && python3 -m pytest tests/test_review_blocks.py -q && python3 -m pytest tests -q && bash check.sh --selftest
```
Expected: 全件 PASS（段階表示の `test_visual_stage_*` と `test_checker_sequence_panels.py` を含む）、`selftest: 32 passed, 0 failed`。段階表示系で panel 同一性の失敗が出たら、`_starts_excluded_subtree` の `data-stepper` 除外が効いていない。他の失敗は、ビルド済み文書に対する `'<p …>'` / `'<li>'` 形の完全一致アサーションなので、Step 5 と同じ正規表現形に直す。

- [ ] **Step 7: Commit**

```bash
git add skills/visual-explain/scripts/ve_components/review_blocks.py skills/visual-explain/scripts/build_explainer.py \
  skills/visual-explain/scripts/ve_components/document_checks.py skills/visual-explain/scripts/ve_components/checker.py \
  skills/visual-explain/scripts/ve_components/validation.py skills/visual-explain/scripts/tests/test_review_blocks.py \
  skills/visual-explain/scripts/tests/test_closing_section.py skills/visual-explain/scripts/tests/test_document_checks.py \
  skills/visual-explain/scripts/tests/test_expected_record_plumbing.py skills/visual-explain/scripts/tests/test_narrative_sections.py \
  skills/visual-explain/examples/example-proposal.html
git commit -m "feat(ve): number reviewable blocks with data-ve-blk and verify the sequence"
```

---

### Task 5: 回収パネルの常設

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/document_sections.py`（`render_decision_panel`, `_render_panel_ask_item`）
- Modify: `skills/visual-explain/scripts/build_explainer.py`（パネルの追加）
- Modify: `skills/visual-explain/scripts/ve_components/document_checks.py`（`_check_decision_panel` と呼び出し）
- Modify: `skills/visual-explain/assets/skeleton.html`（`.panel-review-count` の 1 行）
- Modify: `skills/visual-explain/scripts/tests/test_decision_panel.py`, `tests/test_document_checks.py`, `tests/test_narrative_sections.py`
- Modify: `skills/visual-explain/examples/example-proposal.html`（再ビルド）

**Interfaces:**
- Consumes: `stamp_review_blocks`（Task 4）、`check_document_structure(..., skeleton_version)`（Task 4）、`compute_ask_digest` / `compute_ask_digest_from_pairs`（既存）。
- Produces:
  - `render_decision_panel(asks, document, schema_version, document_path, *, occupied_ids=frozenset()) -> WrappedDocumentSection`（常に返す。`None` は返さない）。
  - パネルの DOM 契約（Task 6 が読む）: `section[data-ve-section-kind="decision-panel"]` に `data-ve-document-id` / `data-ve-schema-version` / `data-ve-ask-digest` / `data-ve-document-path`。内側 `section.decision-panel` に、decision ask があるときだけ `ul.panel-asks > li[data-ve-panel-ask]`（`.panel-question` / `[data-ve-panel-status]` / `[data-ve-panel-memo]`）、常に `p.panel-review-count[data-ve-panel-review-count]`（初期文言「指摘 0 件」）と `textarea[data-ve-panel-global-memo]`。
  - v3 の診断: パネル 0 個 `回収パネルがありません`、2 個以上 `回収パネルはちょうど1個必要です`。位置・digest・自己表明属性の診断は既存文言のまま。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_decision_panel.py`:
- `test_returns_none_for_zero_decision_asks` を次に置き換える:
```python
    def test_panel_without_decision_asks_has_no_ask_list(self) -> None:
        panel = render_decision_panel((_REQUEST_ASK,), _DOC, 2, "out.html")
        self.assertIn('data-ve-section-kind="decision-panel"', panel.markup)
        self.assertNotIn('class="panel-asks"', panel.markup)
        self.assertIn('<p class="panel-review-count" data-ve-panel-review-count>指摘 0 件</p>', panel.markup)
        self.assertIn(f'data-ve-ask-digest="{compute_ask_digest((_REQUEST_ASK,))}"', panel.markup)
```
- `test_no_panel_when_no_decision_ask` を次に置き換える:
```python
    def test_panel_present_without_decision_ask(self) -> None:
        doc = build_document(
            _assembly(decision_ask=False), REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS_DIR,
            document_path="out.html",
        )
        self.assertEqual(doc.count('<section data-ve-section-kind="decision-panel"'), 1)
        self.assertLess(doc.index('data-ve-section-kind="closing"'),
                        doc.index('<section data-ve-section-kind="decision-panel"'))
        from ve_components.checker import check_final_document
        self.assertEqual(check_final_document(doc, SKELETON, REGISTRY, components_dir=COMPONENTS_DIR), [])
```
- `test_renders_panel_for_one_decision_ask` の `'aria-label="判断の回収"'` を `'aria-label="回答と指摘の回収"'`、`"<h2>判断の回収</h2>"` を `"<h2>回答と指摘の回収</h2>"`、`"未選択（既定案: 案B）"` を `"未選択（お任せ = 推奨: 案B）"` にする。

`tests/test_document_checks.py`: import に `from ve_components.review_blocks import stamp_review_blocks` を足し、`DecisionPanelStructureTest` の後に次のクラスを足す:
```python
class CollectionPanelV3Test(unittest.TestCase):
    """skeleton v3: 回収パネルは decision ask の有無に関わらずちょうど1つ。"""

    def _check(self, content: str) -> list[str]:
        stamped, _ = stamp_review_blocks(content)
        return _msgs(check_document_structure(stamped, title=None, skeleton_version=3))

    def test_panel_without_decision_ask_is_clean(self) -> None:
        digest = compute_ask_digest_from_pairs(())
        self.assertEqual(self._check(_FIRST_BLOCK + _CLOSING_BLOCK + _panel_block(digest)), [])

    def test_missing_panel_is_reported(self) -> None:
        self.assertEqual(self._check(_FIRST_BLOCK + _CLOSING_BLOCK), ["回収パネルがありません"])

    def test_two_panels_are_reported(self) -> None:
        digest = compute_ask_digest_from_pairs(())
        content = (_FIRST_BLOCK + _CLOSING_BLOCK + _panel_block(digest)
                   + _panel_block(digest, instance_id="sec-decision-panel-2"))
        self.assertEqual(self._check(content), ["回収パネルはちょうど1個必要です"])

    def test_decision_digest_is_still_checked(self) -> None:
        content = _FIRST_BLOCK + _ask_block() + _CLOSING_BLOCK + _panel_block("0" * 16)
        self.assertEqual(self._check(content), ["回収パネルの ask 契約ダイジェストが一致しません"])

    def test_legacy_rule_kept_for_v1_and_v2(self) -> None:
        digest = compute_ask_digest_from_pairs(())
        content = _FIRST_BLOCK + _CLOSING_BLOCK + _panel_block(digest)
        for version in (1, 2):
            self.assertEqual(
                _msgs(check_document_structure(content, title=None, skeleton_version=version)),
                ["decision ask がないのに回収パネルがあります"], version)
```
同じファイルで、`build_document` の出力を検査している次の 6 テストの `check_document_structure(…, title=…)` に `skeleton_version=3` を足す（ビルド済み文書は v3。足さないと旧規則の「decision ask がないのに回収パネルがあります」が出る）: `test_built_decision_document_with_panel_has_no_structure_diagnostics`、`test_built_typed_document_has_no_structure_diagnostics`、`test_external_link_marker_mismatch_is_diagnosed`、`test_missing_summary_is_diagnosed`、`test_invalid_type_vocabulary_is_diagnosed`、`test_self_closed_svg_elements_in_a_real_canonical_document_are_permitted`。合成 content（`_FIRST_BLOCK` など）を検査するテストは旧規則の確認なので変えない。

`tests/test_narrative_sections.py` の `_build_composition_and_document`（build_document の手順の手書き再現）にパネルを足す。import に `render_decision_panel` を足し、`for section in request.sections:` ループの直後（`compose_sections` の前）に足す:
```python
    items.append(render_decision_panel(
        tuple(s for s in request.sections if isinstance(s, AskSection)),
        request.document, request.schema_version, "doc.html",
        occupied_ids=frozenset(i.instance_id for i in items)))
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_decision_panel.py tests/test_document_checks.py -q`
Expected: FAIL（パネルが生成されない、`回収パネルがありません` が出ない）。

- [ ] **Step 3: パネルの描画を書く** — `document_sections.py`

`render_decision_panel` を次にする（docstring も更新）:
```python
def render_decision_panel(
    asks: tuple[AskSection, ...],
    document: DocumentMetadata,
    schema_version: int,
    document_path: str,
    *,
    occupied_ids: frozenset[str] | set[str] = frozenset(),
) -> WrappedDocumentSection:
    """Build the collection panel inserted after closing (always exactly one).

    It lists decision asks when there are any, and always carries the
    annotation count and the global memo. Selection sync, drafts, and the
    copy control are the skeleton's fixed collection JS.
    """
    decisions = tuple(a for a in asks if a.ask_type == "decision")
    digest = compute_ask_digest(asks)
    instance_id = _allocate_instance_id(_PANEL_INSTANCE_ID_PREFIX, occupied_ids)
    asks_html = ""
    if decisions:
        items_html = "".join(_render_panel_ask_item(a) for a in decisions)
        asks_html = f'  <ul class="panel-asks">\n    {items_html}\n  </ul>\n'
    body = (
        '<section class="decision-panel" aria-label="回答と指摘の回収">\n'
        "  <h2>回答と指摘の回収</h2>\n"
        f"{asks_html}"
        '  <p class="panel-review-count" data-ve-panel-review-count>指摘 0 件</p>\n'
        '  <div class="ask-memo"><label>全体メモ'
        "<textarea data-ve-panel-global-memo></textarea></label></div>\n"
        '  <p class="panel-note">選択・指摘の保存とコピーは、ブラウザの'
        "JavaScript が有効なときに使えます。</p>\n"
        "</section>"
    )
    markup = (
        f'<section data-ve-section-kind="decision-panel"'
        f' data-ve-document-id="{_esc(document.id)}"'
        f' data-ve-schema-version="{schema_version}"'
        f' data-ve-ask-digest="{_esc(digest)}"'
        f' data-ve-document-path="{_esc(document_path)}"'
        f' id="{_esc(instance_id)}">\n'
        f"{body}\n"
        f"</section>"
    )
    return WrappedDocumentSection(instance_id=instance_id, markup=markup)
```
`_render_panel_ask_item` の `status` を `f"未選択（お任せ = 推奨: {default_label}）"` にする。

`build_explainer.py` の `if panel is not None:\n        items.append(panel)` を `items.append(panel)` にする。

`skeleton.html` の `.panel-status { … }` の行の直後に足す:
```css
    .panel-review-count { margin: var(--space-1) 0 0; color: var(--text-dim); }
```

- [ ] **Step 4: checker の規則を書く** — `document_checks.py`

`_check_decision_panel` のシグネチャを `def _check_decision_panel(structure: _DocStructure, skeleton_version: int = 1) -> list[Diagnostic]:` にし、`ask_nodes` / `panel_nodes` の計算の後から `if len(panel_nodes) != 1:` の前までを次に置き換える:
```python
    if skeleton_version < 3:
        if not ask_nodes:
            if panel_nodes:
                return [Diagnostic(
                    DOCUMENT_STRUCTURE_VIOLATION,
                    "decision ask がないのに回収パネルがあります",
                    "content",
                )]
            return []
        if not panel_nodes:
            return [Diagnostic(
                DOCUMENT_STRUCTURE_VIOLATION,
                "decision ask があるのに回収パネルがありません",
                "content",
            )]
    elif not panel_nodes:
        return [Diagnostic(DOCUMENT_STRUCTURE_VIOLATION, "回収パネルがありません", "content")]
```
docstring に「v3 以降はパネルが常にちょうど1つ。v1/v2 は decision ask の有無と一致すること」を英語で足す。`check_document_structure` の呼び出しを `diagnostics.extend(_check_decision_panel(structure, skeleton_version))` にする。

- [ ] **Step 5: 見本を再ビルドして通す**

```bash
cd "$(git rev-parse --show-toplevel)"
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/examples/example-proposal.assembly.json \
  --output skills/visual-explain/examples/example-proposal.html
cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest
```
Expected: 全件 PASS。`selftest: 32 passed, 0 failed`（既存の `structure-bad-panel-*.html` は v1 文書なので旧規則のまま）。

- [ ] **Step 6: Commit**

```bash
git add skills/visual-explain/scripts/ve_components/document_sections.py skills/visual-explain/scripts/build_explainer.py \
  skills/visual-explain/scripts/ve_components/document_checks.py skills/visual-explain/assets/skeleton.html \
  skills/visual-explain/scripts/tests/test_decision_panel.py skills/visual-explain/scripts/tests/test_document_checks.py \
  skills/visual-explain/scripts/tests/test_narrative_sections.py skills/visual-explain/examples/example-proposal.html
git commit -m "feat(ve): always emit exactly one collection panel in skeleton v3 documents"
```

---

### Task 6: 回収エンジンとコピー固定形

**Files:**
- Modify: `skills/visual-explain/scripts/tests/runtime/decision_engine.js`（全面書き換え）
- Modify: `skills/visual-explain/scripts/tests/runtime/decision_engine_driver.js`
- Modify: `skills/visual-explain/assets/skeleton.html`（`FIXED DECISION ENGINE CORE` 区間と `FIXED DECISION COLLECTION JS` 区間）
- Modify: `skills/visual-explain/scripts/tests/test_decision_engine_js.py`（全面書き換え）
- Modify: `skills/visual-explain/scripts/tests/test_skeleton_audit.py`（`DecisionOptionCardInteractionTest`）
- Modify: `skills/visual-explain/examples/example-proposal.html`（再ビルド）

**Interfaces:**
- Consumes: Task 3 のカード DOM 契約、Task 4 の `[data-ve-blk]`、Task 5 のパネル DOM 契約。
- Produces（`globalThis.veDecisionEngine`、node では `module.exports`）:
  - 定数 `CHIPS: string[8]`（Global Constraints の順）、`QUOTE_LIMIT = 40`。
  - contract 型: `{documentId, schemaVersion, digest, title, documentPath, blockCount: number, asks: [{id, question, defaultId, options: [{id, label, withdrawn: boolean}]}]}`。
  - state 型: `{selections: {askId: optionId}, memos: {askId: string}, globalMemo: string, annotations: [{blk: number, chip: string, quote: string, note: string}]}`。
  - `storageKey(contract) -> "ve-review:<documentId>:<schemaVersion>:<digest>:<blockCount>"`
  - `emptyState()`, `selectOption(state, askId, optionId, contract)`（同じ選択肢で解除、取り下げ・未知は無視）, `setMemo(state, askId, text)`, `setGlobalMemo(state, text)`
  - `normalizeQuote(text) -> string`, `addAnnotation(state, blk, chip, quote, note, contract)`, `removeAnnotation(state, index)`, `annotationsFor(state, blk) -> [{index, chip, quote, note}]`
  - `restoreState(raw, contract)`, `serializeState(state)`, `cardStatus(ask, state) -> "選択: <label>" | "お任せ（推奨: <label>）"`, `nextChipIndex(current, key, total) -> number`（矢印・Home・End 以外は -1）, `formatCopyText(contract, state)`, `findPanelRow(rows, askId)`
  - 収集 JS の内部名（Task 7 が使う）: `engine`, `panel`, `main`, `blocks`, `contract`, `state`（`let`）, `persist()`, `statusLines`（`Map`）, `render()`。`render()` は末尾で `[data-ve-panel-review-count]` を「指摘 N 件」に更新する。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_decision_engine_js.py` を次の内容で置き換える

```python
"""回収エンジン純関数の検証（node 標準のみ・npm 依存なし）。"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

NODE = shutil.which("node")
RUNTIME = Path(__file__).resolve().parent / "runtime"
DRIVER = RUNTIME / "decision_engine_driver.js"
SKELETON = RUNTIME.parents[2] / "assets" / "skeleton.html"

CHIPS = ["わからない", "図にしてほしい", "もっと詳しく", "短くする", "削る", "言い換える", "事実を確認", "ここは良い"]
CLOSING = "上の回答を反映して作業を続けてください。お任せの項目は推奨案で確定してください。"

CONTRACT = {
    "documentId": "doc-1", "schemaVersion": 2, "digest": "0123456789abcdef",
    "title": "料金改定は限定対象で段階公開する", "documentPath": "examples/demo.html", "blockCount": 12,
    "asks": [
        {"id": "ask-1", "question": "対象範囲をどちらにしますか？", "defaultId": "opt-b",
         "options": [{"id": "opt-a", "label": "案A", "withdrawn": False},
                     {"id": "opt-b", "label": "案B", "withdrawn": False},
                     {"id": "opt-w", "label": "案W", "withdrawn": True}]},
        {"id": "ask-2", "question": "開始時期はいつにしますか？", "defaultId": "opt-c",
         "options": [{"id": "opt-c", "label": "今月", "withdrawn": False},
                     {"id": "opt-d", "label": "来月", "withdrawn": False}]},
    ],
}
HEADER = [
    "[visual-explain 回答]",
    "資料: 料金改定は限定対象で段階公開する",
    "(examples/demo.html / id: doc-1 / schema: 2 / asks: 0123456789abcdef)",
]
NO_ASKS = dict(CONTRACT, asks=[], digest="fedcba9876543210")
CONTRACT_PROTO = dict(CONTRACT, asks=[
    {"id": "__proto__", "question": "汚染に耐えますか？", "defaultId": "opt-p",
     "options": [{"id": "opt-p", "label": "はい", "withdrawn": False},
                 {"id": "opt-q", "label": "いいえ", "withdrawn": False}]}])
CONTRACT_DELIM = dict(CONTRACT, asks=[
    {"id": "ask,1", "question": "境界文字でも動きますか？", "defaultId": "opt=1",
     "options": [{"id": "opt=1", "label": "動く", "withdrawn": False},
                 {"id": "opt=2", "label": "動かない", "withdrawn": False}]}])


def run_calls(calls: list[dict]) -> list:
    proc = subprocess.run([NODE, str(DRIVER)], input=json.dumps(calls).encode("utf-8"),
                          capture_output=True, timeout=30)
    assert proc.returncode == 0, proc.stderr.decode("utf-8")
    return json.loads(proc.stdout)


@unittest.skipUnless(NODE, "node が無い環境ではスキップ（完了ゲートでは非スキップ実行が必須）")
class ReviewEngineJsTest(unittest.TestCase):
    def test_chips_are_the_eight_kinds_in_order(self) -> None:
        self.assertEqual(run_calls([{"fn": "CHIPS"}]), [CHIPS])

    def test_storage_key_tracks_digest_and_block_count(self) -> None:
        key, other = run_calls([{"fn": "storageKey", "args": [CONTRACT]},
                                {"fn": "storageKey", "args": [dict(CONTRACT, blockCount=13)]}])
        self.assertEqual(key, "ve-review:doc-1:2:0123456789abcdef:12")
        self.assertNotEqual(key, other)

    def test_selecting_twice_returns_to_omakase(self) -> None:
        once, twice = run_calls([
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-a", CONTRACT], "assign": True},
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-a", CONTRACT], "assign": True},
        ])
        self.assertEqual(once["selections"], {"ask-1": "opt-a"})
        self.assertEqual(twice["selections"], {})

    def test_withdrawn_option_cannot_be_selected_or_restored(self) -> None:
        (state,) = run_calls([{"fn": "selectOption", "args": ["$state", "ask-1", "opt-w", CONTRACT]}])
        self.assertEqual(state["selections"], {})
        raw = json.dumps({"selections": {"ask-1": "opt-w"}})
        (restored,) = run_calls([{"fn": "restoreState", "args": [raw, CONTRACT]}])
        self.assertEqual(restored["selections"], {})

    def test_restore_drops_stale_entries(self) -> None:
        raw = json.dumps({
            "selections": {"ask-1": "opt-z", "ask-9": "opt-a", "ask-2": "opt-d"},
            "memos": {"ask-9": "古い"}, "globalMemo": "残す",
            "annotations": [
                {"blk": 3, "chip": "削る", "quote": "q", "note": "n"},
                {"blk": 13, "chip": "削る", "quote": "", "note": ""},
                {"blk": 2, "chip": "その他", "quote": "", "note": ""},
                {"blk": "2", "chip": "削る", "quote": "", "note": ""},
                "broken",
            ],
        })
        (restored,) = run_calls([{"fn": "restoreState", "args": [raw, CONTRACT]}])
        self.assertEqual(restored["selections"], {"ask-2": "opt-d"})
        self.assertEqual(restored["memos"], {})
        self.assertEqual(restored["globalMemo"], "残す")
        self.assertEqual(restored["annotations"], [{"blk": 3, "chip": "削る", "quote": "q", "note": "n"}])

    def test_restore_tolerates_broken_input(self) -> None:
        empty = {"selections": {}, "memos": {}, "globalMemo": "", "annotations": []}
        for raw in [None, "not json", "[]", "42"]:
            (restored,) = run_calls([{"fn": "restoreState", "args": [raw, CONTRACT]}])
            self.assertEqual(restored, empty)

    def test_serialize_restore_roundtrip(self) -> None:
        results = run_calls([
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-a", CONTRACT], "assign": True},
            {"fn": "addAnnotation", "args": ["$state", 5, "短くする", "引用", "長い", CONTRACT], "assign": True},
            {"fn": "serializeState", "args": ["$state"]},
        ])
        (restored,) = run_calls([{"fn": "restoreState", "args": [results[-1], CONTRACT]}])
        self.assertEqual(restored["selections"], {"ask-1": "opt-a"})
        self.assertEqual(restored["annotations"], [{"blk": 5, "chip": "短くする", "quote": "引用", "note": "長い"}])

    def test_add_annotation_rejects_unknown_chip_and_out_of_range_block(self) -> None:
        a, b, c = run_calls([
            {"fn": "addAnnotation", "args": ["$state", 0, "削る", "", "", CONTRACT]},
            {"fn": "addAnnotation", "args": ["$state", 13, "削る", "", "", CONTRACT]},
            {"fn": "addAnnotation", "args": ["$state", 1, "その他", "", "", CONTRACT]},
        ])
        for state in (a, b, c):
            self.assertEqual(state["annotations"], [])

    def test_quote_is_normalized_to_40_code_points(self) -> None:
        emoji = "\U0001F600" * 41
        flat, long = run_calls([
            {"fn": "normalizeQuote", "args": ["  限定対象で\n\n段階  公開する  "]},
            {"fn": "normalizeQuote", "args": [emoji]},
        ])
        self.assertEqual(flat, "限定対象で 段階 公開する")
        self.assertEqual(long, "\U0001F600" * 40)

    def test_remove_annotation_and_annotations_for(self) -> None:
        results = run_calls([
            {"fn": "addAnnotation", "args": ["$state", 4, "削る", "", "", CONTRACT], "assign": True},
            {"fn": "addAnnotation", "args": ["$state", 4, "言い換える", "", "x", CONTRACT], "assign": True},
            {"fn": "addAnnotation", "args": ["$state", 7, "ここは良い", "", "", CONTRACT], "assign": True},
            {"fn": "annotationsFor", "args": ["$state", 4]},
            {"fn": "removeAnnotation", "args": ["$state", 0], "assign": True},
            {"fn": "removeAnnotation", "args": ["$state", 9]},
        ])
        self.assertEqual(results[3], [{"index": 0, "chip": "削る", "quote": "", "note": ""},
                                      {"index": 1, "chip": "言い換える", "quote": "", "note": "x"}])
        self.assertEqual([a["chip"] for a in results[4]["annotations"]], ["言い換える", "ここは良い"])
        self.assertEqual(results[5], results[4])

    def test_card_status(self) -> None:
        unselected, selected = run_calls([
            {"fn": "cardStatus", "args": [CONTRACT["asks"][0], "$state"]},
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-a", CONTRACT], "assign": True},
        ])
        (after,) = run_calls([{"fn": "cardStatus", "args": [CONTRACT["asks"][0], selected]}])
        self.assertEqual(unselected, "お任せ（推奨: 案B）")
        self.assertEqual(after, "選択: 案A")

    def test_next_chip_index(self) -> None:
        calls = [{"fn": "nextChipIndex", "args": args} for args in (
            [0, "ArrowRight", 8], [7, "ArrowRight", 8], [0, "ArrowLeft", 8], [3, "ArrowDown", 8],
            [3, "ArrowUp", 8], [3, "Home", 8], [3, "End", 8], [3, "a", 8])]
        self.assertEqual(run_calls(calls), [1, 0, 7, 4, 2, 0, 7, -1])

    def test_copy_text_full_format(self) -> None:
        calls = [
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-a", CONTRACT], "assign": True},
            {"fn": "setMemo", "args": ["$state", "ask-1", "  撤回条件を先に固める  "], "assign": True},
            {"fn": "setMemo", "args": ["$state", "ask-2", "   "], "assign": True},
            {"fn": "setGlobalMemo", "args": ["$state", "全体の所感"], "assign": True},
            {"fn": "addAnnotation", "args": ["$state", 12, "図にしてほしい", "  限定対象で\n段階公開する  ", "表にしてほしい", CONTRACT], "assign": True},
            {"fn": "addAnnotation", "args": ["$state", 3, "ここは良い", "", "", CONTRACT], "assign": True},
            {"fn": "formatCopyText", "args": [CONTRACT, "$state"]},
        ]
        expected = "\n".join(HEADER + [
            "Q1. 対象範囲をどちらにしますか？: 案A / 補足: 撤回条件を先に固める",
            "Q2. 開始時期はいつにしますか？: (未選択 = お任せ)",
            "全体メモ: 全体の所感",
            "## 指摘",
            "#3 [ここは良い]",
            "#12 [図にしてほしい] 「限定対象で 段階公開する」 表にしてほしい",
            "---",
            CLOSING,
        ])
        self.assertEqual(run_calls(calls)[-1], expected)

    def test_copy_text_minimal_has_no_empty_sections(self) -> None:
        (text,) = run_calls([{"fn": "formatCopyText", "args": [CONTRACT, "$state"]}])
        self.assertEqual(text, "\n".join(HEADER + [
            "Q1. 対象範囲をどちらにしますか？: (未選択 = お任せ)",
            "Q2. 開始時期はいつにしますか？: (未選択 = お任せ)",
            "---",
            CLOSING,
        ]))

    def test_copy_text_keeps_supplement_on_unselected_ask(self) -> None:
        calls = [
            {"fn": "setMemo", "args": ["$state", "ask-2", "一行目\n二行目"], "assign": True},
            {"fn": "formatCopyText", "args": [CONTRACT, "$state"]},
        ]
        self.assertIn("Q2. 開始時期はいつにしますか？: (未選択 = お任せ) / 補足: 一行目\n二行目",
                      run_calls(calls)[-1])

    def test_copy_text_without_asks_lists_only_annotations(self) -> None:
        calls = [
            {"fn": "addAnnotation", "args": ["$state", 1, "削る", "", "  ", NO_ASKS], "assign": True},
            {"fn": "formatCopyText", "args": [NO_ASKS, "$state"]},
        ]
        self.assertEqual(run_calls(calls)[-1], "\n".join([
            "[visual-explain 回答]",
            "資料: 料金改定は限定対象で段階公開する",
            "(examples/demo.html / id: doc-1 / schema: 2 / asks: fedcba9876543210)",
            "## 指摘",
            "#1 [削る]",
            "---",
            CLOSING,
        ]))

    def test_proto_ask_id_survives_select_memo_and_restore(self) -> None:
        results = run_calls([
            {"fn": "selectOption", "args": ["$state", "__proto__", "opt-p", CONTRACT_PROTO], "assign": True},
            {"fn": "setMemo", "args": ["$state", "__proto__", "懸念あり"], "assign": True},
            {"fn": "serializeState", "args": ["$state"]},
            {"fn": "formatCopyText", "args": [CONTRACT_PROTO, "$state"]},
        ])
        self.assertEqual(results[1]["selections"], {"__proto__": "opt-p"})
        (restored,) = run_calls([{"fn": "restoreState", "args": [results[2], CONTRACT_PROTO]}])
        self.assertEqual(restored["memos"], {"__proto__": "懸念あり"})
        self.assertIn("Q1. 汚染に耐えますか？: はい / 補足: 懸念あり", results[3])

    def test_delimiter_char_ids_round_trip(self) -> None:
        results = run_calls([
            {"fn": "selectOption", "args": ["$state", "ask,1", "opt=1", CONTRACT_DELIM], "assign": True},
            {"fn": "serializeState", "args": ["$state"]},
        ])
        (restored,) = run_calls([{"fn": "restoreState", "args": [results[-1], CONTRACT_DELIM]}])
        self.assertEqual(restored["selections"], {"ask,1": "opt=1"})

    def test_find_panel_row_matches_by_dataset_value(self) -> None:
        rows = [
            {"dataset": {"vePanelAsk": "決定\"1"}, "marker": "row-quote-japanese"},
            {"dataset": {"vePanelAsk": " 2ask"}, "marker": "row-leading-space-digit"},
        ]
        first, second, none = run_calls([
            {"fn": "findPanelRow", "args": [rows, "決定\"1"]},
            {"fn": "findPanelRow", "args": [rows, " 2ask"]},
            {"fn": "findPanelRow", "args": [rows, "b"]},
        ])
        self.assertEqual(first["marker"], "row-quote-japanese")
        self.assertEqual(second["marker"], "row-leading-space-digit")
        self.assertIsNone(none)

    def test_engine_sources_pass_node_check(self) -> None:
        for name in ("decision_engine.js", "decision_engine_driver.js"):
            proc = subprocess.run([NODE, "--check", str(RUNTIME / name)], capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))

    def test_skeleton_inline_scripts_pass_node_check(self) -> None:
        bodies = re.findall(r"<script>(.*?)</script>", SKELETON.read_text("utf-8"), re.S)
        self.assertGreaterEqual(len(bodies), 3)
        with tempfile.TemporaryDirectory() as tmp:
            for index, body in enumerate(bodies):
                path = Path(tmp) / f"inline-{index}.js"
                path.write_text(body, "utf-8")
                proc = subprocess.run([NODE, "--check", str(path)], capture_output=True)
                self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
```

`test_skeleton_audit.py` の `DecisionOptionCardInteractionTest` のうち `test_option_item_becomes_the_interactive_surface` と `test_aria_pressed_syncs_on_the_item_itself` を次の 4 テストに置き換える（他のテストはそのまま）:
```python
    def test_option_item_is_a_radio(self):
        block = self._collection_block()
        self.assertIn("list.setAttribute('role', 'radiogroup')", block)
        self.assertIn("item.setAttribute('role', 'radio')", block)
        self.assertIn("item.setAttribute('tabindex', '0')", block)
        self.assertIn("item.addEventListener('click', select)", block)

    def test_aria_checked_syncs_on_the_item_itself(self):
        block = self._collection_block()
        self.assertIn("item.setAttribute('aria-checked', String(selected))", block)
        self.assertNotIn("aria-pressed", block)

    def test_withdrawn_option_is_not_interactive(self):
        self.assertIn("item.setAttribute('aria-disabled', 'true')", self._collection_block())

    def test_copy_button_label(self):
        self.assertIn("copyButton.textContent = '回答と指摘をコピー';", self._collection_block())
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_decision_engine_js.py tests/test_skeleton_audit.py -q`
Expected: FAIL（`engine[call.fn] is not a function`、旧コピー形、`role', 'button'` など）。

- [ ] **Step 3: ドライバを直す** — `tests/runtime/decision_engine_driver.js` のループ本体を次にする

```js
  for (const call of calls) {
    const args = (call.args || []).map((a) => (a === "$state" ? state : a));
    const target = engine[call.fn];
    const result = typeof target === "function" ? target(...args) : target;
    if (call.assign) state = result;
    results.push(result === undefined ? null : result);
  }
```

- [ ] **Step 4: エンジンを書く** — `tests/runtime/decision_engine.js` を次の内容で置き換える

```js
/* Review-collection pure core for visual-explain.
   This file is the source of truth; assets/skeleton.html embeds it verbatim
   between the FIXED DECISION ENGINE CORE markers (byte-equality is enforced
   by test_skeleton_audit.py). No DOM, no timers, no I/O here. */
(function (global) {
  "use strict";

  const CHIPS = ["わからない", "図にしてほしい", "もっと詳しく", "短くする", "削る", "言い換える", "事実を確認", "ここは良い"];
  const QUOTE_LIMIT = 40;
  const CLOSING_LINE = "上の回答を反映して作業を続けてください。お任せの項目は推奨案で確定してください。";

  function storageKey(contract) {
    // Digest and block count make a rebuilt document with changed asks or
    // blocks start clean instead of restoring drafts onto the wrong targets.
    return "ve-review:" + contract.documentId + ":" + contract.schemaVersion + ":" +
      contract.digest + ":" + contract.blockCount;
  }

  function emptyMap() {
    // Object.create(null) keeps ask ids like "__proto__" as ordinary own
    // properties instead of tripping the Object.prototype accessor.
    return Object.create(null);
  }

  function emptyState() {
    return { selections: emptyMap(), memos: emptyMap(), globalMemo: "", annotations: [] };
  }

  function findAsk(contract, askId) {
    for (const ask of contract.asks) if (ask.id === askId) return ask;
    return null;
  }

  function findOption(ask, optionId) {
    for (const option of ask.options) if (option.id === optionId) return option;
    return null;
  }

  function activeOption(ask, optionId) {
    const option = typeof optionId === "string" ? findOption(ask, optionId) : null;
    return option && !option.withdrawn ? option : null;
  }

  function findPanelRow(rows, askId) {
    // Match by dataset equality so arbitrary ids never build a CSS selector.
    for (const row of rows) if (row.dataset.vePanelAsk === askId) return row;
    return null;
  }

  function cloneWith(state, patch) {
    return {
      selections: Object.assign(emptyMap(), state.selections, patch.selections || emptyMap()),
      memos: Object.assign(emptyMap(), state.memos, patch.memos || emptyMap()),
      globalMemo: patch.globalMemo !== undefined ? patch.globalMemo : state.globalMemo,
      annotations: patch.annotations !== undefined ? patch.annotations : state.annotations.slice(),
    };
  }

  function selectOption(state, askId, optionId, contract) {
    // Radio-like choice; choosing the selected option again returns to the
    // recommendation ("お任せ"). Withdrawn and unknown options are ignored.
    const ask = findAsk(contract, askId);
    if (!ask || !activeOption(ask, optionId)) return state;
    const next = cloneWith(state, {});
    if (next.selections[askId] === optionId) delete next.selections[askId];
    else next.selections[askId] = optionId;
    return next;
  }

  function setMemo(state, askId, text) {
    const next = cloneWith(state, {});
    next.memos[askId] = String(text);
    return next;
  }

  function setGlobalMemo(state, text) {
    return cloneWith(state, { globalMemo: String(text) });
  }

  function flatten(text) {
    return String(text == null ? "" : text).replace(/\s+/g, " ").trim();
  }

  function normalizeQuote(text) {
    // Count code points so a surrogate pair is never split.
    return Array.from(flatten(text)).slice(0, QUOTE_LIMIT).join("");
  }

  function addAnnotation(state, blk, chip, quote, note, contract) {
    if (!Number.isInteger(blk) || blk < 1 || blk > contract.blockCount) return state;
    if (CHIPS.indexOf(chip) < 0) return state;
    const annotations = state.annotations.slice();
    annotations.push({ blk: blk, chip: chip, quote: normalizeQuote(quote), note: flatten(note) });
    return cloneWith(state, { annotations: annotations });
  }

  function removeAnnotation(state, index) {
    if (!Number.isInteger(index) || index < 0 || index >= state.annotations.length) return state;
    const annotations = state.annotations.slice();
    annotations.splice(index, 1);
    return cloneWith(state, { annotations: annotations });
  }

  function annotationsFor(state, blk) {
    const found = [];
    state.annotations.forEach(function (item, index) {
      if (item.blk === blk) found.push({ index: index, chip: item.chip, quote: item.quote, note: item.note });
    });
    return found;
  }

  function restoreState(raw, contract) {
    // Stale or foreign entries never survive: unknown asks, unknown or
    // withdrawn options, out-of-range blocks, and unknown chips are dropped.
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (error) {
      return emptyState();
    }
    if (!parsed || typeof parsed !== "object") return emptyState();
    let state = emptyState();
    for (const ask of contract.asks) {
      const selected = parsed.selections ? parsed.selections[ask.id] : undefined;
      if (activeOption(ask, selected)) state.selections[ask.id] = selected;
      const memo = parsed.memos ? parsed.memos[ask.id] : undefined;
      if (typeof memo === "string") state.memos[ask.id] = memo;
    }
    if (typeof parsed.globalMemo === "string") state.globalMemo = parsed.globalMemo;
    if (Array.isArray(parsed.annotations)) {
      for (const item of parsed.annotations) {
        if (!item || typeof item !== "object") continue;
        const quote = typeof item.quote === "string" ? item.quote : "";
        const note = typeof item.note === "string" ? item.note : "";
        state = addAnnotation(state, item.blk, item.chip, quote, note, contract);
      }
    }
    return state;
  }

  function serializeState(state) {
    return JSON.stringify(state);
  }

  function defaultLabel(ask) {
    const option = ask.defaultId ? findOption(ask, ask.defaultId) : null;
    return option ? option.label : "";
  }

  function cardStatus(ask, state) {
    const option = activeOption(ask, state.selections[ask.id]);
    return option ? "選択: " + option.label : "お任せ（推奨: " + defaultLabel(ask) + "）";
  }

  function nextChipIndex(current, key, total) {
    if (total <= 0) return -1;
    if (key === "ArrowRight" || key === "ArrowDown") return current < 0 ? 0 : (current + 1) % total;
    if (key === "ArrowLeft" || key === "ArrowUp") return current <= 0 ? total - 1 : current - 1;
    if (key === "Home") return 0;
    if (key === "End") return total - 1;
    return -1;
  }

  function askLine(ask, index, state) {
    const option = activeOption(ask, state.selections[ask.id]);
    let line = "Q" + (index + 1) + ". " + ask.question + ": " + (option ? option.label : "(未選択 = お任せ)");
    const memo = typeof state.memos[ask.id] === "string" ? state.memos[ask.id].trim() : "";
    if (memo) line += " / 補足: " + memo;
    return line;
  }

  function annotationLine(item) {
    let line = "#" + item.blk + " [" + item.chip + "]";
    if (item.quote) line += " 「" + item.quote + "」";
    if (item.note) line += " " + item.note;
    return line;
  }

  function formatCopyText(contract, state) {
    const lines = [
      "[visual-explain 回答]",
      "資料: " + contract.title,
      "(" + contract.documentPath + " / id: " + contract.documentId +
        " / schema: " + contract.schemaVersion + " / asks: " + contract.digest + ")",
    ];
    contract.asks.forEach(function (ask, index) { lines.push(askLine(ask, index, state)); });
    const globalMemo = typeof state.globalMemo === "string" ? state.globalMemo.trim() : "";
    if (globalMemo) lines.push("全体メモ: " + globalMemo);
    const ordered = state.annotations
      .map(function (item, order) { return { item: item, order: order }; })
      .sort(function (a, b) { return a.item.blk - b.item.blk || a.order - b.order; });
    if (ordered.length) {
      lines.push("## 指摘");
      ordered.forEach(function (entry) { lines.push(annotationLine(entry.item)); });
    }
    lines.push("---");
    lines.push(CLOSING_LINE);
    return lines.join("\n");
  }

  const engine = {
    CHIPS, QUOTE_LIMIT, storageKey, emptyState, selectOption, setMemo, setGlobalMemo,
    normalizeQuote, addAnnotation, removeAnnotation, annotationsFor, restoreState,
    serializeState, cardStatus, nextChipIndex, formatCopyText, findPanelRow,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = engine;
  else global.veDecisionEngine = engine;
})(globalThis);
```

- [ ] **Step 5: skeleton にエンジンを逐語で埋め込む**

```bash
cd skills/visual-explain && python3 - <<'PY'
from pathlib import Path
skel = Path("assets/skeleton.html")
text = skel.read_text("utf-8")
core = Path("scripts/tests/runtime/decision_engine.js").read_text("utf-8")
begin = "/* FIXED DECISION ENGINE CORE:BEGIN (verbatim copy of scripts/tests/runtime/decision_engine.js) */\n"
end = "\n  /* FIXED DECISION ENGINE CORE:END */"
head, rest = text.split(begin, 1)
_, tail = rest.split(end, 1)
skel.write_text(head + begin + core.rstrip("\n") + "\n" + end + tail, "utf-8")
PY
```

- [ ] **Step 6: 収集 JS を書き換える** — `assets/skeleton.html` の `  /* FIXED DECISION COLLECTION JS: DO NOT MODIFY. */` の行から、最後の `  </script>` の直前までを次に置き換える

```js
  /* FIXED DECISION COLLECTION JS: DO NOT MODIFY. */
  (() => {
    const engine = globalThis.veDecisionEngine;
    const panel = document.querySelector('section[data-ve-section-kind="decision-panel"]');
    const main = document.querySelector('main');
    if (!engine || !panel || !main) return;
    const blocks = Array.from(main.querySelectorAll('[data-ve-blk]'));
    const askSections = Array.from(document.querySelectorAll(
      'section[data-ve-section-kind="ask"][data-ve-ask-type="decision"][id]'));
    const textOf = (node) => (node ? node.textContent : '').trim();
    const contract = {
      documentId: panel.dataset.veDocumentId || '',
      schemaVersion: panel.dataset.veSchemaVersion || '',
      digest: panel.dataset.veAskDigest || '',
      title: document.title,
      documentPath: panel.dataset.veDocumentPath || '',
      blockCount: blocks.length,
      asks: askSections.map((section) => {
        const defaultItem = section.querySelector('[data-ask-default]');
        return {
          id: section.id,
          question: textOf(section.querySelector('.ask-question')),
          defaultId: defaultItem ? (defaultItem.dataset.askOptionId || null) : null,
          options: Array.from(section.querySelectorAll('[data-ask-option]')).map((item) => ({
            id: item.dataset.askOptionId || '',
            label: textOf(item.querySelector('.ask-option-label')),
            withdrawn: item.hasAttribute('data-ask-withdrawn'),
          })),
        };
      }),
    };
    let storage = null;
    let state = engine.emptyState();
    try {
      storage = window.localStorage;
      state = engine.restoreState(storage.getItem(engine.storageKey(contract)), contract);
    } catch {
      storage = null; // 永続化だけを失い、選択と指摘は動き続ける。
    }
    const persist = () => {
      if (!storage) return;
      try { storage.setItem(engine.storageKey(contract), engine.serializeState(state)); } catch {}
    };
    const statusLines = new Map();
    const render = () => {
      contract.asks.forEach((ask) => {
        const section = document.getElementById(ask.id);
        if (!section) return;
        section.querySelectorAll('[data-ask-option]').forEach((item) => {
          if (item.hasAttribute('data-ask-withdrawn')) return;
          const selected = state.selections[ask.id] === item.dataset.askOptionId;
          if (selected) item.setAttribute('data-ask-selected', '');
          else item.removeAttribute('data-ask-selected');
          item.setAttribute('aria-checked', String(selected));
        });
        const line = statusLines.get(ask.id);
        if (line) line.textContent = engine.cardStatus(ask, state);
        const row = engine.findPanelRow(
          Array.from(panel.querySelectorAll('li[data-ve-panel-ask]')), ask.id);
        if (!row) return;
        const status = row.querySelector('[data-ve-panel-status]');
        if (status) status.textContent = engine.cardStatus(ask, state);
        const memoRow = row.querySelector('[data-ve-panel-memo]');
        if (memoRow) {
          const memo = (state.memos[ask.id] || '').trim();
          memoRow.hidden = !memo;
          memoRow.textContent = memo ? `補足: ${memo}` : '';
        }
      });
      const count = panel.querySelector('[data-ve-panel-review-count]');
      if (count) count.textContent = `指摘 ${state.annotations.length} 件`;
    };
    askSections.forEach((section) => {
      const list = section.querySelector('.ask-options');
      if (list) {
        list.setAttribute('role', 'radiogroup');
        list.setAttribute('aria-label', textOf(section.querySelector('.ask-question')));
      }
      section.querySelectorAll('[data-ask-option]').forEach((item) => {
        item.setAttribute('role', 'radio');
        if (item.hasAttribute('data-ask-withdrawn')) {
          item.setAttribute('aria-disabled', 'true');
          item.setAttribute('aria-checked', 'false');
          return;
        }
        item.setAttribute('tabindex', '0');
        const select = () => {
          state = engine.selectOption(state, section.id, item.dataset.askOptionId, contract);
          persist(); render();
        };
        item.addEventListener('click', select);
        item.addEventListener('keydown', (event) => {
          if (event.key !== 'Enter' && event.key !== ' ') return;
          event.preventDefault();
          select();
        });
      });
      const line = document.createElement('p');
      line.className = 'ask-card-status';
      line.setAttribute('aria-live', 'polite');
      if (list) list.after(line);
      statusLines.set(section.id, line);
      const memoField = section.querySelector('textarea[data-ask-memo]');
      if (memoField) {
        memoField.value = state.memos[section.id] || '';
        memoField.addEventListener('input', () => {
          state = engine.setMemo(state, section.id, memoField.value);
          persist(); render();
        });
      }
    });
    const globalField = panel.querySelector('textarea[data-ve-panel-global-memo]');
    if (globalField) {
      globalField.value = state.globalMemo || '';
      globalField.addEventListener('input', () => {
        state = engine.setGlobalMemo(state, globalField.value);
        persist();
      });
    }
    const copyButton = document.createElement('button');
    copyButton.type = 'button';
    copyButton.textContent = '回答と指摘をコピー';
    const copyStatus = document.createElement('p');
    copyStatus.className = 'panel-copy-status';
    copyStatus.setAttribute('aria-live', 'polite');
    const fallback = document.createElement('pre');
    fallback.className = 'panel-copy-fallback';
    fallback.hidden = true;
    copyButton.addEventListener('click', async () => {
      const text = engine.formatCopyText(contract, state);
      try {
        await navigator.clipboard.writeText(text);
        fallback.hidden = true;
        copyStatus.textContent = 'コピーしました。エージェントへ貼り付けてください。';
      } catch {
        fallback.textContent = text;
        fallback.hidden = false;
        copyStatus.textContent = 'クリップボードを使えないため、以下を手動でコピーしてください。';
      }
    });
    panel.querySelector('.decision-panel')?.append(copyButton, copyStatus, fallback);
    render();
  })();

```
（置き換え後も、最後の `  </script>` / `</body>` / `</html>` はそのまま残る。）

- [ ] **Step 7: 見本を再ビルドして通す**

```bash
cd "$(git rev-parse --show-toplevel)"
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/examples/example-proposal.assembly.json \
  --output skills/visual-explain/examples/example-proposal.html
cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest
```
Expected: 全件 PASS（node がある環境で `test_decision_engine_js.py` がスキップされないこと: `python3 -m pytest tests/test_decision_engine_js.py -q -rs` の出力に `skipped` が無い）。`selftest: 32 passed, 0 failed`。

- [ ] **Step 8: Commit**

```bash
git add skills/visual-explain/scripts/tests/runtime/decision_engine.js skills/visual-explain/scripts/tests/runtime/decision_engine_driver.js \
  skills/visual-explain/assets/skeleton.html skills/visual-explain/scripts/tests/test_decision_engine_js.py \
  skills/visual-explain/scripts/tests/test_skeleton_audit.py skills/visual-explain/examples/example-proposal.html
git commit -m "feat(ve): collect answers and annotations into the fixed reply format"
```

---

### Task 7: 指摘層の操作 UI

**Files:**
- Modify: `skills/visual-explain/assets/skeleton.html`（`<style>` に指摘層 CSS、`FIXED DECISION COLLECTION JS` に指摘層ブロック）
- Modify: `skills/visual-explain/scripts/tests/test_skeleton_audit.py`（意味色 allowlist、コントラスト対、新テスト）
- Modify: `skills/visual-explain/examples/example-proposal.html`（再ビルド）

**Interfaces:**
- Consumes: Task 6 の収集 JS 内部名（`engine`, `main`, `blocks`, `contract`, `state`, `persist`, `statusLines`, `render`）、エンジンの `CHIPS` / `normalizeQuote` / `addAnnotation` / `removeAnnotation` / `annotationsFor` / `nextChipIndex`。
- Produces: 実行時 DOM のみ（`button.review-add`, `button.review-pick`, `div.review-editor`, `span.review-tag`, ブロックの `data-ve-annotated` と `tabindex="0"`）。生成 HTML には何も足さない。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_skeleton_audit.py`

`test_semantic_colors_only_on_judgment_selectors` の `allowed` タプルの末尾に足す:
```python
            # 指摘層の選択チップと番号札（accent = 読者が指した場所・選んだ種類の強調）
            ".review-",
            # 指摘済みブロックの左縦線（accent = 読者が指した場所）
            "[data-ve-annotated]",
```
`PAIRS` の末尾に足す:
```python
    ("accent-strong", "surface", 4.5, "指摘の番号札/面"),
```
ファイル末尾（`if __name__` の前）に足す:
```python
class ReviewLayerSkeletonTest(unittest.TestCase):
    """指摘層: ＋ ボタン・なぞりボタン・ブロック直下の入力欄・番号札は固定領域の JS が作る。"""

    def _collection_block(self):
        begin = "/* FIXED DECISION COLLECTION JS: DO NOT MODIFY. */"
        return SKELETON.split(begin, 1)[1].split("</script>", 1)[0]

    def test_review_layer_hooks_exist(self):
        block = self._collection_block()
        for needle in (
            "block.setAttribute('tabindex', '0')",
            "if (event.target !== block || event.key !== 'Enter') return;",
            "chip.setAttribute('role', 'radio')",
            "chips.setAttribute('role', 'radiogroup')",
            "makeButton('review-add', '＋')",
            "makeButton('review-pick', '指摘')",
            "document.addEventListener('selectionchange'",
            "engine.addAnnotation(state, n, editor.chip, editor.quote, note.value, contract)",
            "      renderReview();\n",
        ):
            self.assertIn(needle, block)

    def test_annotated_block_uses_accent_line(self):
        style = SKELETON.split("<style>", 1)[1].split("</style>", 1)[0]
        self.assertIn(
            "[data-ve-blk][data-ve-annotated] { border-left: 3px solid var(--accent); "
            "padding-left: var(--space-1); }", style)
        self.assertIn(
            '.review-chip[aria-checked="true"] { border-color: var(--accent); color: var(--accent-strong); '
            "background: color-mix(in srgb, var(--accent) 12%, var(--surface)); }", style)
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_skeleton_audit.py -q`
Expected: FAIL（`ReviewLayerSkeletonTest` の 2 件）。

- [ ] **Step 3: CSS を足す** — `assets/skeleton.html` の `<style>` 内、`    footer { … }` の行の直前に挿入

```css
    [data-ve-blk]:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
    [data-ve-blk][data-ve-annotated] { border-left: 3px solid var(--accent); padding-left: var(--space-1); }
    .review-tag { margin-right: var(--space-1); color: var(--accent-strong); font-size: var(--fs-small); font-weight: 700; user-select: none; }
    .review-add, .review-pick { position: absolute; z-index: 3; min-width: 1.75rem; padding: 0 var(--space-1); border: 1px solid var(--border); background: var(--bg); color: var(--text-dim); font-size: var(--fs-small); line-height: 1.75; }
    .review-editor { display: grid; gap: var(--space-1); max-width: var(--w-narrative); margin: var(--space-1) 0 var(--space-2); padding: var(--space-2); background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); font-size: var(--fs-figure); }
    .review-head { margin: 0; color: var(--text-dim); }
    .review-chips, .review-actions { display: flex; flex-wrap: wrap; gap: var(--space-1); }
    .review-chip { padding: 0 var(--space-1); border: 1px solid var(--border); border-radius: 999px; background: var(--bg); }
    .review-chip[aria-checked="true"] { border-color: var(--accent); color: var(--accent-strong); background: color-mix(in srgb, var(--accent) 12%, var(--surface)); }
    .review-note { font: inherit; color: inherit; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); padding: var(--space-1); }
    .review-list { display: grid; gap: var(--space-1); margin: 0; padding: 0; list-style: none; }
    .review-list li { display: flex; flex-wrap: wrap; gap: var(--space-1); align-items: center; }
```

- [ ] **Step 4: 指摘層の JS を足す** — `FIXED DECISION COLLECTION JS` 内

(a) `render` の中の `      const count = panel.querySelector('[data-ve-panel-review-count]');` の直前に 1 行挿入する:
```js
      renderReview();
```

(b) `    const statusLines = new Map();` の直後に次のブロックを挿入する:
```js
    // 指摘層: ＋ ボタン、なぞりの「指摘」ボタン、ブロック直下の入力欄、番号札。
    const blockNumber = (block) => Number(block.dataset.veBlk);
    const tags = new Map();
    let editor = null;
    let addTarget = null;
    let pick = null;
    const makeButton = (className, label) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = className;
      button.textContent = label;
      button.hidden = true;
      document.body.append(button);
      return button;
    };
    const addButton = makeButton('review-add', '＋');
    const pickButton = makeButton('review-pick', '指摘');
    const place = (button, rect, below) => {
      button.hidden = false;
      const width = button.offsetWidth;
      let left;
      if (below) left = rect.left;
      else if (rect.left >= width + 8) left = rect.left - width - 4;
      else left = rect.right - width;
      const top = below ? rect.bottom + 4 : rect.top;
      button.style.left = `${Math.round(window.scrollX + left)}px`;
      button.style.top = `${Math.round(window.scrollY + top)}px`;
    };
    const showAdd = (block) => {
      if (editor && editor.block === block) return;
      addTarget = block;
      addButton.setAttribute('aria-label', `#${blockNumber(block)} に指摘を付ける`);
      place(addButton, block.getBoundingClientRect(), false);
    };
    const closeEditor = (refocus) => {
      if (!editor) return;
      const { block, root } = editor;
      root.remove();
      editor = null;
      if (refocus) block.focus();
    };
    const openEditor = (block, quote) => {
      closeEditor(false);
      addButton.hidden = true;
      pickButton.hidden = true;
      const n = blockNumber(block);
      const root = document.createElement('div');
      root.className = 'review-editor';
      root.setAttribute('role', 'group');
      root.setAttribute('aria-label', `#${n} への指摘`);
      const head = document.createElement('p');
      head.className = 'review-head';
      const chips = document.createElement('div');
      chips.className = 'review-chips';
      chips.setAttribute('role', 'radiogroup');
      chips.setAttribute('aria-label', '指摘の種類');
      const chipButtons = engine.CHIPS.map((label) => {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'review-chip';
        chip.setAttribute('role', 'radio');
        chip.textContent = label;
        return chip;
      });
      chips.append(...chipButtons);
      const note = document.createElement('input');
      note.type = 'text';
      note.className = 'review-note';
      note.placeholder = 'ひとこと（任意）';
      note.setAttribute('aria-label', 'ひとこと（任意）');
      const add = document.createElement('button');
      add.type = 'button';
      add.textContent = '追加';
      const close = document.createElement('button');
      close.type = 'button';
      close.textContent = '閉じる';
      const actions = document.createElement('div');
      actions.className = 'review-actions';
      actions.append(add, close);
      const list = document.createElement('ul');
      list.className = 'review-list';
      root.append(head, chips, note, actions, list);
      editor = { block, root, list, chip: '', quote: engine.normalizeQuote(quote) };
      const reset = () => {
        editor.chip = '';
        chipButtons.forEach((chip, i) => {
          chip.setAttribute('aria-checked', 'false');
          chip.tabIndex = i === 0 ? 0 : -1;
        });
        add.disabled = true;
        head.textContent = editor.quote ? `#${n} 「${editor.quote}」` : `#${n}`;
      };
      const check = (index) => {
        editor.chip = engine.CHIPS[index];
        chipButtons.forEach((chip, i) => {
          chip.setAttribute('aria-checked', String(i === index));
          chip.tabIndex = i === index ? 0 : -1;
        });
        add.disabled = false;
        chipButtons[index].focus();
      };
      chipButtons.forEach((chip, index) => {
        chip.addEventListener('click', () => check(index));
        chip.addEventListener('keydown', (event) => {
          const next = engine.nextChipIndex(index, event.key, chipButtons.length);
          if (next < 0) return;
          event.preventDefault();
          check(next);
        });
      });
      add.addEventListener('click', () => {
        if (!editor || !editor.chip) return;
        state = engine.addAnnotation(state, n, editor.chip, editor.quote, note.value, contract);
        editor.quote = '';
        note.value = '';
        reset();
        persist(); render();
        chipButtons[0].focus();
      });
      note.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        add.click();
      });
      close.addEventListener('click', () => closeEditor(true));
      root.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;
        event.preventDefault();
        closeEditor(true);
      });
      reset();
      if (block.tagName === 'LI') block.append(root);
      else block.after(root);
      render();
      chipButtons[0].focus();
    };
    const renderReview = () => {
      blocks.forEach((block) => {
        const n = blockNumber(block);
        const count = engine.annotationsFor(state, n).length;
        let tag = tags.get(n);
        if (count && !tag) {
          tag = document.createElement('span');
          tag.className = 'review-tag';
          tag.setAttribute('aria-hidden', 'true');
          tag.textContent = `#${n}`;
          if (block.tagName === 'TABLE') block.before(tag);
          else block.prepend(tag);
          tags.set(n, tag);
        } else if (!count && tag) {
          tag.remove();
          tags.delete(n);
        }
        if (count) block.setAttribute('data-ve-annotated', '');
        else block.removeAttribute('data-ve-annotated');
      });
      if (!editor) return;
      const n = blockNumber(editor.block);
      editor.list.replaceChildren(...engine.annotationsFor(state, n).map((item) => {
        const row = document.createElement('li');
        const label = document.createElement('span');
        label.textContent = `[${item.chip}]${item.quote ? ` 「${item.quote}」` : ''}${item.note ? ` ${item.note}` : ''}`;
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.textContent = '削除';
        remove.setAttribute('aria-label', `[${item.chip}] の指摘を削除`);
        remove.addEventListener('click', () => {
          state = engine.removeAnnotation(state, item.index);
          persist(); render();
        });
        row.append(label, remove);
        return row;
      }));
    };
    blocks.forEach((block) => {
      block.setAttribute('tabindex', '0');
      block.addEventListener('pointerenter', (event) => {
        if (event.pointerType === 'mouse') showAdd(block);
      });
      block.addEventListener('click', (event) => {
        if (event.target.closest('.review-editor, a, button, input, textarea, summary')) return;
        const selection = window.getSelection();
        if (selection && !selection.isCollapsed) return;
        if (event.target.closest('[data-ve-blk]') === block) showAdd(block);
      });
      block.addEventListener('keydown', (event) => {
        if (event.target !== block || event.key !== 'Enter') return;
        event.preventDefault();
        openEditor(block, '');
      });
    });
    addButton.addEventListener('click', () => { if (addTarget) openEditor(addTarget, ''); });
    pickButton.addEventListener('pointerdown', (event) => event.preventDefault());
    pickButton.addEventListener('click', () => { if (pick) openEditor(pick.block, pick.quote); });
    document.addEventListener('selectionchange', () => {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed || !selection.rangeCount) {
        pickButton.hidden = true;
        return;
      }
      const range = selection.getRangeAt(0);
      const node = range.startContainer;
      const start = node.nodeType === 1 ? node : node.parentElement;
      const block = start ? start.closest('[data-ve-blk]') : null;
      if (!block || start.closest('.review-editor')) {
        pickButton.hidden = true;
        return;
      }
      pick = { block, quote: selection.toString() };
      place(pickButton, range.getBoundingClientRect(), true);
    });
```

- [ ] **Step 5: 見本を再ビルドし、自動テストを通す**

```bash
cd "$(git rev-parse --show-toplevel)"
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/examples/example-proposal.assembly.json \
  --output skills/visual-explain/examples/example-proposal.html
cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest
```
Expected: 全件 PASS（`test_skeleton_inline_scripts_pass_node_check` で構文、格子監査・意味色・コントラストを含む）。`selftest: 32 passed, 0 failed`。

- [ ] **Step 6: ブラウザで操作を確かめる（手動。自動化ツールは足さない）**

`open skills/visual-explain/examples/example-proposal.html`（Chrome か Safari）で次を確かめ、結果を報告に書く:
1. 問いカード: 推奨に「推奨」バッジ、状態行が「お任せ（推奨: 限定対象で段階公開する）」。選択肢を押すと丸印が塗られ状態行が「選択: …」、もう一度押すとお任せに戻る。Tab で選択肢へ移り Enter / Space で選べる。
2. 段落にマウスを乗せると左に ＋。押すと段落の直下に 8 チップ＋ひとこと欄。チップを選ぶまで「追加」は押せない。矢印キーでチップが移る。Esc で閉じて段落にフォーカスが戻る。
3. 段落の文字をなぞると下に「指摘」。押すと入力欄の見出しに `#N 「なぞった文字」`。追加すると段落に左の青線と `#N` 札。同じ段落に 2 件目を足せる。一覧の「削除」で消える。
4. 段落に Tab でフォーカスし Enter で入力欄が開く。
5. 再読み込み後も選択・補足・指摘・全体メモが残る。
6. 「回答と指摘をコピー」の貼り付け結果が Global Constraints の固定形どおり（`[visual-explain 回答]` で始まり、`---` と締めの 1 文で終わる）。
7. 幅 390px（開発者ツール）で ＋ が画面内（段落の右端）に出る。ダークテーマでも線・札・チップが読める。
不具合があれば JS / CSS を直し、Step 5 からやり直す。

- [ ] **Step 7: Commit**

```bash
git add skills/visual-explain/assets/skeleton.html skills/visual-explain/scripts/tests/test_skeleton_audit.py \
  skills/visual-explain/examples/example-proposal.html
git commit -m "feat(ve): let readers annotate any block with a chip and a short note"
```

---

### Task 8: v3 の selftest fixture と後方互換の固定

**Files:**
- Create: `skills/visual-explain/scripts/tests/structure-bad-v3-panel-missing.html`
- Create: `skills/visual-explain/scripts/tests/structure-bad-v3-blk-gap.html`
- Create: `skills/visual-explain/scripts/tests/structure-bad-v3-blk-tag.html`
- Modify: `skills/visual-explain/scripts/check.sh`（`structure_cases`）
- Test: `skills/visual-explain/scripts/tests/test_selftest_cases.py` (create)

**Interfaces:**
- Consumes: 最終の v3 skeleton（Task 7 完了後。fixture は固定領域ごと v3 skeleton を含むため、skeleton を変えたら作り直す）、`first_screen_ir.assembly / narr`。
- Produces: selftest 35 件（legacy 25 ＋ 構造 10）。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_selftest_cases.py`

```python
"""check.sh --selftest が v1 / v2 / v3 の構造ケースを含めて全件通る。"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

CHECK = Path(__file__).resolve().parents[1] / "check.sh"


class SelftestTest(unittest.TestCase):
    def test_selftest_passes_with_v3_cases(self) -> None:
        proc = subprocess.run(["bash", str(CHECK), "--selftest"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("selftest: 35 passed, 0 failed", proc.stdout)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_selftest_cases.py -q`
Expected: FAIL（`selftest: 32 passed`）。

- [ ] **Step 3: fixture を決定的に生成する**

```bash
cd skills/visual-explain/scripts && python3 - <<'PY'
import re
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from build_explainer import build_document
from first_screen_ir import assembly, narr
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS

skill = Path("..").resolve()
skeleton = (skill / "assets" / "skeleton.html").read_text("utf-8")
components = skill / "assets" / "components"
registry = load_registry(components / "registry.json")
raw = assembly({"conclusion": "限定対象で開始する。"}, narr("sec-a", "現状の確認"))
html = build_document(raw, registry, TRUSTED_RENDERERS, skeleton, components,
                      document_path="tests/structure-v3.html")
tests = Path("tests")
no_panel = re.sub(r'\n    <section data-ve-section-kind="decision-panel".*?</section>\n</section>', "",
                  html, count=1, flags=re.S)
gap = html.replace(' data-ve-blk="2"', ' data-ve-blk="3"', 1)
tag = html.replace('<section class="first-screen"', '<section data-ve-blk="99" class="first-screen"', 1)
for name, text in (("panel-missing", no_panel), ("blk-gap", gap), ("blk-tag", tag)):
    assert text != html, name
    (tests / f"structure-bad-v3-{name}.html").write_text(text, "utf-8")
PY
```

- [ ] **Step 4: selftest にケースを足す** — `check.sh` の `structure_cases` の末尾（Task 1 の `v2-proposal-doc.html` の後）に足す

```python
        ("structure-bad-v3-panel-missing.html", ("回収パネルがありません",)),
        ("structure-bad-v3-blk-gap.html", ("data-ve-blk は1からの連番である必要があります（2 番目のブロックが 3）",)),
        ("structure-bad-v3-blk-tag.html", ("data-ve-blk は p / h2 / h3 / li / figure / blockquote / pre / table にだけ付けられます: <section>",)),
```

- [ ] **Step 5: 通す**

Run: `cd skills/visual-explain/scripts && bash check.sh --selftest && python3 -m pytest tests -q`
Expected: `selftest: 35 passed, 0 failed`、全件 PASS。

- [ ] **Step 6: Commit**

```bash
git add skills/visual-explain/scripts/check.sh skills/visual-explain/scripts/tests/test_selftest_cases.py \
  skills/visual-explain/scripts/tests/structure-bad-v3-panel-missing.html \
  skills/visual-explain/scripts/tests/structure-bad-v3-blk-gap.html \
  skills/visual-explain/scripts/tests/structure-bad-v3-blk-tag.html
git commit -m "test(ve): pin skeleton v3 panel and block-number checks in the selftest"
```

---

### Task 9: スキル文書の更新

**Files:**
- Modify: `skills/visual-explain/SKILL.md`（ワークフロー手順 5・6・9・10 と新手順、末尾節の回収パネル段落、目視チェックの最後の項目）
- Modify: `skills/visual-explain/references/patterns.md`（「decision ask の回収パネル（Phase 2）」節）
- Modify: `skills/visual-explain/references/design-system.md`（29 行の意味色の文、「回収パネル（decision ask）の目視規範」節）
- Modify: `CLAUDE.md`（リポジトリルート）

- [ ] **Step 1: SKILL.md のワークフロー**

手順 5 の「`askType: "decision"` の ask は回収パネルの対象になる。パネルは末尾 `closing` の後にビルドが自動生成し、選択肢とラベルを ask の option から引き写す。」を次に置き換える:
```markdown
`askType: "decision"` の ask は問いカードになる。各選択肢に `benefit`（利点）と `tradeoff`（代償）、ask に `defaultId`（推奨）と `evidence`（`file:line` か「」で囲んだ実行結果の引用）を必ず書く。事実は読者に聞かず根拠で示し、読者には判断だけを聞く。decision ask は1資料4問まで。回収パネルは decision ask の有無に関わらず末尾 `closing` の後にビルドが1つ自動生成し、本文の各ブロックにはビルドが指摘用の番号（`data-ve-blk`）を付ける。
```
手順 6 の検査群③の括弧内に「、本文ブロック番号の連番」を足し、「decision ask を含む文書では判断の回収パネル」を「回収パネル（v3 文書では常にちょうど1つ）」にする。

手順 8（保存する）の後を次の 5 手順にする（旧 9・10 は 10・11 に繰り下げ、内容を一部更新）:
```markdown
9. **試問する:** 資料を開く前に、文脈を持たない general-purpose subagent に資料の絶対パスと読者宣言 1 行だけを渡し、次の 5 問で検査する。同期で結果を待つ。
   1. 選択肢の弁別（各選択肢を選んだときの違いを資料だけから説明できるか）
   2. 根拠の引用の有無
   3. 実質 1 択の検出（推奨でない選択肢を選ぶ理由が読めるか）
   4. 音読と 30 秒 3 文要約
   5. 説明なしの内輪語の列挙

   decision ask の無い解説資料では 1〜3 を省く。落ちた問いは「絵を足す / 問いを落とす / 言い換える」で IR を直して再ビルドし、同じ subagent に差分だけを送って再判定する。計 2 巡で打ち切る。
10. **開く:** `open-url "<絶対パス>"` を第一選択にする。なければ `open` または `xdg-open` を使う。起動の成功・失敗を問わず、資料の**絶対パスを必ず表示**する。GUI 表示は best effort であり、終了コード 0 でも表示を保証しない。
11. **ターミナルで要約する:** 資料の要点を 3 行、ファイルパス、そして「問いカードで選び、気になる段落は ＋ か文字のなぞりで指摘し、末尾の『回答と指摘をコピー』で貼り戻してほしい」を表示する。
12. **待つ:** 資料をブラウザで開いたら、回答の貼り戻しが届くまで実装を始めない。
13. **反映する:** `[visual-explain 回答]` で始まる固定形を読み、`(未選択 = お任せ)` の問いは推奨案で確定する。`## 指摘` の `#N` は資料の `data-ve-blk="N"` のブロックを指す。設計が変わる指摘なら `<topic>-02` で作り直し、捨てた案は選択肢の `"withdrawn": true` で残す。生成した資料は証跡として消さない。
```
「末尾節」節の最後の段落（「decision ask を含む資料は、末尾節のさらに後に…」）を次に置き換える:
```markdown
全資料の末尾節のさらに後に、ビルドが回収パネルを1つ自動生成する。パネルは問いカードの選択・補足・指摘・全体メモを集計してコピーする UI であり、推奨（`defaultId`）は**選択済みとして扱わない**。読者が選ばなかった問いは「お任せ＝推奨」として回収される。下書きはブラウザの localStorage に自動保存され、保存できない環境でも画面は動く。
```
目視チェックの最後の項目を次にする:
```markdown
- [ ] 回収パネルが closing の後に1つだけあり、推奨（`defaultId`）が選択済み扱いされていない。問いカードの各選択肢に利点・代償があり、推奨でない選択肢を選ぶ理由が読める。
```

- [ ] **Step 2: patterns.md** — 「### decision ask の回収パネル（Phase 2）」節の見出しと本文を、次の 4 連バッククォートの内側でそのまま置き換える

````markdown
### 回収パネルと指摘層

全資料の末尾節の後に、ビルドが回収パネルを1つ自動生成する（decision ask が0件でも出る）。パネルを IR に書いてはならない。本文の `p` / `h2` / `h3` / `li` / `figure` / `blockquote` / `pre` / `table` にはビルドが `data-ve-blk="N"`（1 からの DOM 順）を付け、読者はブロックを指して 8 種のチップ（わからない / 図にしてほしい / もっと詳しく / 短くする / 削る / 言い換える / 事実を確認 / ここは良い）とひとことを付けられる。問いカードの UI 部品・回収パネル・段階表示の内側には番号を付けない。`data-ve-blk` は予約属性で、narrative にも compatibility にも書けない。コピーされる固定形は次のとおり。

```text
[visual-explain 回答]
資料: <title>
(<path> / id: <id> / schema: <ver> / asks: <digest>)
Q1. <問い>: <選択> / 補足: <自由記述>
Q2. <問い>: (未選択 = お任せ)
全体メモ: <自由記述>
## 指摘
#12 [図にしてほしい] 「<なぞった文字列（先頭 40 字）>」 <ひとこと>
#15 [ここは良い]
---
上の回答を反映して作業を続けてください。お任せの項目は推奨案で確定してください。
```

`#N` は資料内の `data-ve-blk="N"` を指す。`(未選択 = お任せ)` は推奨案で確定する。空の節（指摘 0 件、全体メモ空）は出さず、補足が空なら ` / 補足:` を省く。
````

（`test_component_contract.py` は patterns.md の ```` ```json ```` ブロックのうち `"schemaVersion"` を含むものだけを検証するので、この ```` ```text ```` ブロックは対象外。）

- [ ] **Step 3: design-system.md**

29 行の「（ask ブロックでは）意味色が出るのは `decision` の選択チップ（選択＝`--accent`）と `decision` の既定案（推奨＝`--positive`）だけである。」を次にする:
```markdown
（ask ブロックでは）意味色が出るのは問いカードの選択中の丸印と枠（選択＝`--accent`）と「推奨」バッジ（推奨＝`--positive` を薄めた面に `--positive` の文字）だけである。取り下げた選択肢は `--text-faint` と取り消し線で示す。指摘層では、指摘済みブロックの左縦線と選択中のチップ（読者が指した場所＝`--accent`）、番号札（`--accent-strong`）だけが意味色を持つ。
```
「## 回収パネル（decision ask）の目視規範」節の見出しを「## 回収パネルと指摘層の目視規範」にし、本文の最初の段落と「選択状態」の項目を次に置き換える:
```markdown
全資料の末尾節のさらに後に、ビルドが回収パネル（`.decision-panel`、`data-ve-section-kind="decision-panel"`）を1つ自動生成する。IR にパネル自体を書く必要はない。

- **選択状態**: 選択中の選択肢だけが丸印の塗りと `--accent` の内枠・淡背景（`[data-ask-selected]`）を持つ。推奨（`defaultId`）は「推奨」バッジで示し、選択済み扱いにしない。未選択の問いはカードとパネルに「お任せ（推奨: …）」と出る。
- **指摘層**: ＋ ボタンと「指摘」ボタンは枠線だけの小さなボタンで、本文の色を変えない。入力欄は指したブロックの直下に開き、指摘済みブロックは左の `--accent` 縦線と `#N` 札で示す。
```
（「配置」の項目はそのまま残す。）

- [ ] **Step 4: CLAUDE.md**

「不可侵の骨格」節に Phase 1 で足した文の直後へ、v3 を 1 文足す:
```markdown
v3 は問いカード・指摘層・回収パネルの固定 JS を持ち、v2 は `assets/skeleton-v2.html` に凍結した。
```
「ビルドパイプライン」節の `askType: "decision"` の段落を次に置き換える:
```markdown
- 回収パネル（`decision-panel`）は `document_sections.py` が closing の後に常に1つ生成する（v3）。パネルは IR に書かず、DOM 上の decision ask option-id から `compute_ask_digest_from_pairs` で計算した digest を自己保持し、検査群③が再照合する。content 内の `p, h2, h3, li, figure, blockquote, pre, table` には `review_blocks.py` が `data-ve-blk`（1 からの連番）を付け、checker は同じ規則で再計算して照合する（v3 文書のみ）。decision ask は `benefit` / `tradeoff` / `defaultId` / `evidence` 必須、1資料4問まで。
```
検査群③の説明文の「decision-panel の存在（decision ask の有無との整合）」を「decision-panel の存在（v3 文書はちょうど1つ、v1/v2 は decision ask の有無との整合）・本文ブロック番号の連番」にする。コマンド節の「全テスト（666件前後）」の件数を、この Step の直前に `cd skills/visual-explain/scripts && python3 -m pytest tests -q` を実行して最終行に出た passed の件数に置き換える（例: 1300 件なら「全テスト（1300件前後）」）。「SKILL.md — … 10 手順 …」を「13 手順」にする。

- [ ] **Step 5: 確認と Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
grep -n "noDefaultReason\|既定案なし\|判断の回収\|10 手順" CLAUDE.md skills/visual-explain/SKILL.md \
  skills/visual-explain/references/patterns.md skills/visual-explain/references/design-system.md
cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest
cd "$(git rev-parse --show-toplevel)"
git add CLAUDE.md skills/visual-explain/SKILL.md skills/visual-explain/references/patterns.md \
  skills/visual-explain/references/design-system.md
git commit -m "docs(ve): document question cards, the review layer, and the reply loop"
```
Expected: grep は、`patterns.md` / `design-system.md` に残る旧版（v1/v2）の説明として意図した行以外ゼロ。全テスト PASS（`test_component_contract.py` の patterns.md の JSON 検証を含む）、`selftest: 35 passed, 0 failed`。
