# Phase 4: 個別図（13 番目の canonical 形式 `grid-diagram`）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 格子上の配置まで agent が宣言し、座標・線・色はビルドが決める 13 番目の canonical 形式 `grid-diagram` を足す。全体図にしたときは ①②③ をノード上に描き、decision ask の選択肢には小図を付けられる。同梱見本の主図（疎で、入ってくる矢印の無いノードがあった legacy `.layers` 図）を `grid-diagram` の全体図に作り直す。

**Architecture:** 幾何は新モジュール `ve_components/grid_layout.py` だけが決め、validation（配置検査 5 種）・レンダラ（座標と経路）・checker（viewBox の期待値）が同じ関数を呼ぶ。IR は他の形式と同じく `"grid-diagram"` キーの下に置き、registry / vocabulary / schema / `TRUSTED_RENDERERS` / renderer-svg ゲート / 成果物検査を拡張ゲート（design-system.md「新コンポーネントの拡張ゲート」）どおり 1 タスクで原子的に登録する。SVG の要素・属性の許可集合は増やさず、allowlist に `grid-diagram@2` を足し、viewBox だけを figure の `data-ve-grid="列x行"` から計算する式にする。skeleton は変えない（v4 のまま、v5 は作らない）。見た目はすべて新規ファイル `assets/components/grid-diagram.css` に置き、既存の component CSS と registry の既存 digest は 1 バイトも変えない。

**Tech Stack:** Python 3 標準ライブラリのみ（`dataclasses`, `html`, `html.parser`, `re`, `json`, `hashlib`）、pytest（開発時のみ）、bash。目視確認だけ手元の headless Chrome を使う（依存にもテストにもしない）。

**Spec:** `docs/superpowers/specs/2026-10-07-visual-explain-review-loop-design.md` の「Phase 4 — 個別図（13 番目の canonical 形式 `grid-diagram`）」節、「確定した設計判断」、「Hard constraints」。

## Preflight: spec が決めていない点・spec と現行コードの食い違いの裁定

実装者はこの裁定に従う。各タスクの要件に暗黙に含まれる。本計画のコードは、`6e0e534` を写した作業用コピーで Task 1〜7 を順に適用して全テストと selftest が通ることを確認済みである（Task 8 の目視も同じ試作で実施済み）。

1. **IR の置き場所:** spec の IR 例は `grid` / `nodes` / … を IR 直下に書くが、現行の canonical IR はコンポーネント名のキーの下にペイロードを置く（`"slope": {…}`）。`_PAYLOAD_KEYS`（vocabulary のキー集合）による 1 ペイロード検査・`selection.component` との一致検査をそのまま使うため、`"grid-diagram": {"grid", "nodes", "regions", "edges", "markers"}` とする。spec 例の IR 直下の `claim` は現行どおり visual-stage profile 専用のまま。
2. **契約版は 2:** spec 例は `"version": 1` だが、vocabulary の `contractVersions` は `[2]` だけで、`_validate_selection` は vocabulary の `contractVersion` と照合する。`selection.version: 2`、renderer キーは `grid-diagram@2`。
3. **関係の宣言:** spec どおり `relationship.kind = "spatial-layout"`、capability は `"spatial-placement"` の 1 つだけ（`typed-sequence` は持たない＝sequence は既存規則で拒否される）。
4. **id は必須:** spec 例の `edges` には id が無いが、意味 ID はマニフェスト（`consumed_semantic_ids`）と最終 DOM 照合の背骨なので、ノード・囲み・線のすべてに `id` を必須とする。マーカーは id を持たず、番号 `n` で識別する。
5. **SVG の受け入れ方（二重ゲート）:** `RENDERER_SVG_ALLOWLIST` に `"grid-diagram@2"` を足す。要素は既存の許可集合（`svg` / `g` / `rect` / `line` / `circle` / `text` / `title` / `desc`）だけを使い、属性の許可表も変えない（角丸は CSS の `rx` プロパティで描く。属性 `rx` は足さない）。固定 viewBox の代わりに、figure の `data-ve-grid="CxR"` から `grid_layout.viewbox(C, R)` で期待値を計算し、`_SvgSubtreeParser` に `expected_viewbox` として渡す（spec「checker も同じ式で期待値を計算する」）。build 側の `render_canonical` は従来どおり `svg_root_ids` と allowlist を照合する。`<desc>` は使わない（`<title>` は `accessibility.label`）。
6. **幾何（spec は「1 マスの寸法を固定」とだけ言う）:** 1 マス 150×96、ノードはマスから左右 16・上下 22 内側（1 マスのノードは 118×52）、囲みはマスから 4 内側。すべて整数。SVG 内の文字は 13px（ノード）/ 11px（線・囲みのラベル）/ 12px（番号）で、これは viewBox 単位である。rem で書くとルート文字サイズで実寸が変わり、収まり検査（文字数×13 ≤ 幅）と一致しなくなる。
7. **線の経路:** 2 つのノードの横の範囲が重なれば垂直の直線、縦の範囲が重なれば水平の直線。どちらでもなければ「水平→垂直」を先に試し、端点以外のノードを横切るか線ラベルの置き場が無ければ「垂直→水平」を試す。両方だめなら診断を返す。自動の再配置はしない（spec と Non-goals「自動レイアウト」）。
8. **文字の収まり:** ノード `label` は 14 字以内（spec）。1 行に入らなければ、空白（半角か全角）がちょうど 1 つあればそこで、無ければ中央で 2 行に折る。各行が「(ノード幅−12)÷13」字を超えたら「ラベルがノードに収まりません」。線 `label` は 10 字以内（spec）で、最も長い区間の上（水平）か右（垂直）に置き、どのノードとも重ならず viewBox の内側に収まる場所が無ければ「線のラベルを置く場所がありません」。囲み `label` は 8 字以内（spec は無言）で、囲みの幅から 40（左余白と、角のノードの番号の丸）を引いた幅に収まること。
9. **上限（spec は無言）:** 格子は列・行とも 1〜6（spec）。ノード 2〜12、線 0〜16、囲み 0〜4、番号 1〜5（書くなら）。囲み同士は重ねない。同じ向きの重複線と、逆向きの線（同じ経路に重なって描かれ、どのラベルがどちらの線か読めない）は拒否する。1 つのノードに番号は 1 つまで。
10. **色（既存トークンだけ）:** `base` は `--dg-primary-light` の面に `--text`、`primary` は `--dg-primary` の面に `--dg-on-primary`（spec の対応どおり）、`warning` は `--bg` の面に `--dg-negative` の 2px 枠。線・矢じり・囲みの破線は `--dg-line`、線と囲みのラベルは `--text-dim`。番号は `--accent` の丸に `--bg` の数字（Phase 3 の主ボタンと同じ組み合わせ。コントラストは Phase 3 の監査済み）。`tone` を省略したら `base`。
11. **番号（markers）は全体図にだけ:** ①②③ は資料の目次を兼ねる（確定した設計判断）。番号の意味が 2 通りにならないよう、`markers` は `first-screen.overview.section` が指す grid-diagram にだけ書ける。その図は overview と同じ番号をすべて持つ（無い・足りない・余るは拒否）。spec の `ask` は任意で残し、書くなら同じ番号の `overview.markers[].target` と一致しなければ拒否する（二重の真実を作らない）。番号一覧（overview-nav）は従来どおり図の直後に出る（spec「番号一覧も併記する」）。見本は `ask` を書かない（`test_section_markers.py` が見本の overview の行き先を書き換えるため）。
12. **takeaway 注釈は非対応:** `takeawayTargetIds` / `emphasis` を書くと、既存の診断 `注釈対象が未登録のペイロード 'grid-diagram'` で落ちる（`ANNOTATION_TARGETS` に登録しない）。強調は `tone` で宣言する。visual-stage profile の `claim` / `assertions` は使える（`coverIds` はノード・囲み・線の id）。
13. **選択肢の小図:** `decision.options[].figure` は grid-diagram と同じ形で、`grid` は 3×3 以内、ノード 1〜9、`markers` は書けない、図の中で id は一意。spec「見た目が違う選択肢は両方に図を付ける」を、取り下げていない選択肢が 1 つでも図を持つなら全員が持つ、という fail-closed 規則にする（取り下げた選択肢は対象外）。小図は `data-ve-semantic-id` を持たず（canonical の図ではない）、SVG の id は `<ask id>-opt-<選択肢の番号>-svg`（選択肢 id は任意文字列なので使わない）。図は `li[data-ask-option]` の中、代償の行の後に置く（既存規則で指摘ブロック番号の対象外になる）。canonical の grid-diagram が無い資料でも `grid-diagram.css` を積むため、`assembly.add_option_figure_assets` が style 資産に足す。checker は ask セクションの SVG を「decision ask の `figure[data-ve-thumb]` の中に 1 つずつ、3×3 以内」に限って許す。
14. **skeleton と既存資産は触らない:** 見た目はすべて新規 `grid-diagram.css`。registry には新エントリを足すだけで、既存エントリと digest は変えない。新エントリは共有資産 `visual-stage` も宣言する（`test_stage_deck_registry_contract.py` が全コンポーネントに要求する）。
15. **読み上げ一覧は字数に数えない:** レンダラは図の直後に、ノード・線・番号を並べた `ul.ve-gd-relations.visually-hidden` を出す（spec「読み上げ用に…自動生成」）。`metrics` は `.visually-hidden` の中を本文字数に数えない（目で読む文字ではない）。これが無いと見本の本文が 1,425 字になり、`test_example_proposal.py` の上限 1,400 字を超える（変更後は 1,138 字）。
16. **見本の作り直し:** spec の IR 例はまさに見本の承認地図であり、北極星は「第一画面で結論と全体図が見える」なので、承認地図を first-screen 直後の全体図（overview）にする。旧全体図の matrix `sec-alternatives` は削る（3 案の利点・代償の行は decision の問いカードと選択肢の小図が言い直しているので、spec が減らそうとした反復になる）。legacy `.layers` 節も削る。撤回条件に線を足し、全ノードが線でつながる。1280×900 で番号一覧（①②③）が約 868px に収まることを試作で確認した。
17. **スマホ:** SVG は最小幅（列数×7.5rem）を保ち、`.ve-gd-canvas` の中で横にスクロールする（dense matrix と同じ扱い）。番号は番号一覧にも文字で出る。
18. **selftest:** `grid-diagram-doc.html`（合格）と `component-bad-grid-viewbox.html`（viewBox 不一致の 1 診断）を足し、36 → 38 件。
19. **目視の手順:** headless Chrome は `alarm 40` で終了コード 142 を返すことがあるが、PNG は書かれている（更新時刻で確認する）。毎回新しい `--user-data-dir` を使う。ダーク表示は作業用ディレクトリに写した HTML の `<html` に `data-theme="dark"` を足して撮る。390 幅は iframe の枠で撮る。

## Global Constraints

- 外部依存ゼロ: build / check は Python 標準ライブラリのみ。JS テストは node 標準のみ。npm / pip / Playwright / Selenium / Puppeteer / jsdom を追加しない。headless Chrome は手元の目視確認だけに使い、テストや依存にしない。
- 既存配色のみ: skeleton の既存トークン（`--accent` / `--text` / `--text-dim` / `--bg` / `--dg-primary` / `--dg-primary-light` / `--dg-on-primary` / `--dg-negative` / `--dg-line` ほか既存のもの）と、それを `color-mix` で薄めた色だけ。新しい色相・生の hex を足さない。番号の色は青系（`--accent`）。
- 決定論フロア: agent は格子・マス・ラベル・つながりだけを書き、座標・経路・色・DOM はビルドが決める。IR に `x` / `y` / `width` / `path` などの生成系フィールドを書くと既存の `認可されない生成系フィールド` で落ちる。
- skeleton は版ごとに 1 バイト不変。Phase 4 は skeleton を変えない（v4 のまま）。既存の `assets/components/*.css` と `registry.json` の既存エントリ・digest を変えない（新ファイルと新エントリだけ）。
- 生成 HTML の手編集禁止。見本の再ビルドはリポジトリルートを cwd にして相対パスで出力する: `python3 skills/visual-explain/scripts/build_explainer.py --assembly skills/visual-explain/examples/example-proposal.assembly.json --output skills/visual-explain/examples/example-proposal.html`
- 参考にした他者スキルの固有名を、コード・コメント・コミット・文書に書かない。仕組みは一般語（問いカード、指摘層、回収パネル、全体図、番号一覧）で表す。
- コードのコメント / docstring は英語、checker 診断とスキル文書は日本語。診断文言は完全一致テストの対象。
- コミットは conventional commits ＋ `(ve)` スコープ。末尾に次の 2 行を付ける:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` / `Claude-Session: https://claude.ai/code/session_01NgfQq9eGiPhoY46Nmdb2Xv`
- テストは必ず `cd skills/visual-explain/scripts && python3 -m pytest tests -q` で実行する。各タスクの最後に全テストと `bash check.sh --selftest` を通す。着手時点の基準値: `1360 passed, 166 subtests passed`、`selftest: 36 passed, 0 failed`（ブランチ `feat/review-loop-phases-2-4`、HEAD `6e0e534`）。各タスクの完了時の期待値は、各タスク末尾に書いた件数（基準値からの累計）。基準値が違う場合は差分（＋件数）で判断する。
- `tests/test_visual_stage_baseline_immutability.py` は過去の範囲に固定されている。触らない。
- 編集は「old → new」の完全一致置換で行う。各 old 文字列は対象ファイルにちょうど 1 回現れる（`6e0e534` で確認済み）。1 回でなければ止めて報告する。

## Review Focus

- 右上の端のマス（最終列・先頭行）に置いたノードに番号を付けても、丸が viewBox からはみ出さないこと → Task 1 の `test_marker_circle_stays_inside_the_viewbox_at_the_top_right_cell`。
- 最終列の縦の線に長いラベルを付けたとき、ラベルが図の外へはみ出して描かれるのではなく、診断が返ること → Task 1 の `test_label_that_would_leave_the_picture_is_reported`。
- 同じ 2 ノードを逆向きにも結んだとき、2 本の線が重なって描かれる（どのラベルがどちらか読めない）のではなく、診断が返ること → Task 2 の `test_reverse_edge_would_draw_on_top_of_the_first`。
- ノード名に `&` や `<` を含めても、SVG の文字・読み上げ一覧の両方でエスケープされ、四層検査を通ること → Task 3 の `test_author_text_is_escaped_everywhere`。
- decision ask の id に空白や引用符が入っていても（既存の r3 回帰で許されている）、選択肢の小図の SVG id と checker の id 規則が一致して合格すること → Task 5 の `test_ask_id_with_quotes_and_spaces_still_passes`。

---

## File Map

| File | Responsibility | Task |
|---|---|---|
| `skills/visual-explain/scripts/ve_components/grid_layout.py` (create) | 幾何: viewBox、ノード・囲みの矩形、ラベルの折り返し、線の経路と矢じり、番号の位置、配置検査 | 1 |
| `skills/visual-explain/scripts/ve_components/model.py` | `GridNode` / `GridRegion` / `GridEdge` / `GridMarker` / `GridDiagramPayload`（1）、`CanonicalIR.grid_diagram`（3）、`AskOption.figure`（5） | 1, 3, 5 |
| `skills/visual-explain/scripts/ve_components/diagnostics.py` | `GRID_DIAGRAM_STRUCTURE_VIOLATION` | 2 |
| `skills/visual-explain/scripts/ve_components/validation.py` | ペイロード検査 `_validate_grid_diagram` / `validate_grid_diagram`（2）、canonical への配線（3）、番号の文書横断検査（4）、選択肢の小図（5） | 2–5 |
| `skills/visual-explain/references/component-vocabulary.json`, `component-ir.schema.json` | 13 番目の語彙と schema | 3 |
| `skills/visual-explain/references/assembly.schema.json` | `askOption.figure` | 5 |
| `skills/visual-explain/scripts/ve_components/renderers/grid_diagram.py` (create) | SVG と読み上げ一覧の描画（3）、選択肢の小図（5） | 3, 5 |
| `skills/visual-explain/scripts/ve_components/renderers/__init__.py`, `registry.py` | `TRUSTED_RENDERERS` と checker rule 名 | 3 |
| `skills/visual-explain/assets/components/grid-diagram.css` (create), `registry.json` | 見た目と新エントリ（digest `1522386e…`） | 3 |
| `skills/visual-explain/scripts/ve_components/checker.py` | allowlist、viewBox の式、成果物検査（3）、ask 内の小図ゲート（5） | 3, 5 |
| `skills/visual-explain/scripts/ve_components/metrics.py` | `.visually-hidden` を字数に数えない | 3 |
| `skills/visual-explain/scripts/ve_components/document_sections.py`, `assembly.py`, `build_explainer.py` | 小図の描画と資産の追加 | 5 |
| `skills/visual-explain/scripts/check.sh` | selftest に 2 件 | 3 |
| `skills/visual-explain/scripts/tests/test_grid_layout.py` (create) | 幾何の単体テスト | 1 |
| `skills/visual-explain/scripts/tests/test_grid_diagram_validation.py` (create) | 構造と配置検査 5 種 | 2 |
| `skills/visual-explain/scripts/tests/component-valid-grid-diagram.json` (create), `grid-diagram-doc.html` (create), `component-bad-grid-viewbox.html` (create) | 合格 fixture と selftest 文書 | 3 |
| `skills/visual-explain/scripts/tests/test_grid_diagram_renderer.py` (create) | 登録・DOM・最終検査 | 3 |
| `skills/visual-explain/scripts/tests/test_grid_diagram_overview.py` (create) | 全体図の番号 | 4 |
| `skills/visual-explain/scripts/tests/test_grid_diagram_thumbnails.py` (create) | 選択肢の小図 | 5 |
| `skills/visual-explain/scripts/tests/test_metrics.py`, `test_renderer_svg_gate.py`, `test_stage_deck_registry_contract.py`, `test_selftest_cases.py` | 既存テストの期待値更新 | 3 |
| `skills/visual-explain/examples/example-proposal.assembly.json`, `example-proposal.html`, `tests/test_example_proposal.py` | 見本の作り直し | 6 |
| `skills/visual-explain/SKILL.md`, `references/patterns.md`, `references/design-system.md`, `CLAUDE.md`, `tests/test_component_contract.py` | 文書（12 → 13 形式） | 7 |

---

### Task 1: 幾何モジュール `grid_layout.py` と型

**Files:**
- Create: `skills/visual-explain/scripts/ve_components/grid_layout.py`
- Modify: `skills/visual-explain/scripts/ve_components/model.py`（`EvidenceMapPayload` の直後）
- Test: `skills/visual-explain/scripts/tests/test_grid_layout.py`

**Interfaces:**
- Consumes: なし（`model.py` の既存 `dataclass` / `Optional` の import をそのまま使う）。
- Produces:
  - `model.GridNode(id, label, col, row, span_cols=1, span_rows=1, tone="base")`、`model.GridRegion(id, label, from_col, from_row, to_col, to_row)`、`model.GridEdge(id, source, target, label="")`、`model.GridMarker(n, target, ask=None)`、`model.GridDiagramPayload(cols, rows, nodes, regions=(), edges=(), markers=())`（すべて frozen dataclass）。
  - `grid_layout`: 定数 `COL_W=150` / `ROW_H=96` / `MARKER_R=10` / `MAX_GRID=6` / `MAX_THUMB_GRID=3`、`Rect(x0, y0, x1, y1)`（`width` / `height` / `cx` / `cy` / `overlaps`）、`EdgeRoute(points, label_at)`、`viewbox(cols, rows) -> str`、`node_rect(node) -> Rect`、`region_rect(region) -> Rect`、`node_cells(node)` / `region_cells(region) -> frozenset[tuple[int, int]]`、`split_label(label, capacity) -> tuple[str, ...] | None`、`node_label_lines(node) -> tuple[str, ...] | None`、`node_label_positions(node, lines) -> tuple[tuple[int, int], ...]`、`region_label_fits(region) -> bool`、`region_label_position(region) -> tuple[int, int]`、`marker_position(node) -> tuple[int, int]`、`route_edge(edge, rects, width, height) -> EdgeRoute | str`（str は診断文）、`arrow_lines(points) -> tuple[tuple[int, int, int, int], ...]`、`check_layout(payload) -> list[str]`（配置検査の診断文。空なら描ける）。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_grid_layout.py` を作る

````python
"""Phase 4: pure grid-diagram geometry shared by validation, renderer and checker."""
from __future__ import annotations

import unittest

from ve_components.grid_layout import (
    EdgeRoute,
    Rect,
    arrow_lines,
    check_layout,
    marker_position,
    node_label_lines,
    node_label_positions,
    node_rect,
    region_rect,
    route_edge,
    split_label,
    viewbox,
)
from ve_components.model import GridDiagramPayload, GridEdge, GridNode, GridRegion


def node(node_id: str, col: int, row: int, label: str = "ノード", span=(1, 1)) -> GridNode:
    return GridNode(id=node_id, label=label, col=col, row=row, span_cols=span[0], span_rows=span[1])


def payload(nodes, edges=(), regions=(), cols=4, rows=3) -> GridDiagramPayload:
    return GridDiagramPayload(cols=cols, rows=rows, nodes=tuple(nodes), regions=tuple(regions), edges=tuple(edges))


class GeometryTest(unittest.TestCase):
    def test_viewbox_is_150_by_96_per_cell(self) -> None:
        self.assertEqual(viewbox(4, 3), "0 0 600 288")
        self.assertEqual(viewbox(1, 1), "0 0 150 96")
        self.assertEqual(viewbox(6, 6), "0 0 900 576")

    def test_node_rect_is_inset_inside_its_cells(self) -> None:
        self.assertEqual(node_rect(node("a", 1, 1)), Rect(16, 22, 134, 74))
        self.assertEqual(node_rect(node("b", 3, 2)), Rect(316, 118, 434, 170))
        self.assertEqual(node_rect(node("c", 2, 1, span=(2, 2))), Rect(166, 22, 434, 170))

    def test_region_rect_frames_the_cell_range(self) -> None:
        region = GridRegion(id="r", label="法務", from_col=1, from_row=1, to_col=2, to_row=1)
        self.assertEqual(region_rect(region), Rect(4, 4, 296, 92))

    def test_marker_sits_on_the_top_right_corner(self) -> None:
        self.assertEqual(marker_position(node("b", 3, 2)), (434, 118))

    def test_marker_circle_stays_inside_the_viewbox_at_the_top_right_cell(self) -> None:
        cx, cy = marker_position(node("a", 4, 1))
        self.assertEqual((cx, cy), (584, 22))
        self.assertLessEqual(cx + 10, 600)
        self.assertGreaterEqual(cy - 10, 0)


class LabelTest(unittest.TestCase):
    def test_short_label_is_one_centred_line(self) -> None:
        a = node("a", 1, 1, label="共同承認")
        self.assertEqual(node_label_lines(a), ("共同承認",))
        self.assertEqual(node_label_positions(a, ("共同承認",)), ((75, 53),))

    def test_long_label_breaks_at_its_single_space(self) -> None:
        a = node("a", 1, 1, label="請求計算と 対象顧客")
        self.assertEqual(node_label_lines(a), ("請求計算と", "対象顧客"))
        self.assertEqual(node_label_positions(a, ("請求計算と", "対象顧客")), ((75, 45), (75, 61)))

    def test_long_label_without_space_breaks_in_the_middle(self) -> None:
        self.assertEqual(split_label("告知対象と文面の確認", 8), ("告知対象と", "文面の確認"))

    def test_label_that_fits_on_no_two_lines_is_rejected(self) -> None:
        self.assertIsNone(split_label("法務・請求・顧客対応が 照合", 8))

    def test_wider_span_holds_a_longer_line(self) -> None:
        wide = node("a", 1, 1, label="全顧客へ一斉公開する前", span=(2, 1))
        self.assertEqual(node_label_lines(wide), ("全顧客へ一斉公開する前",))


class RouteTest(unittest.TestCase):
    def rects(self, *nodes):
        return {n.id: node_rect(n) for n in nodes}

    def test_same_row_is_one_horizontal_line(self) -> None:
        a, b = node("a", 1, 1), node("b", 3, 1)
        route = route_edge(GridEdge(id="e", source="a", target="b"), self.rects(a, b), 600, 288)
        self.assertEqual(route, EdgeRoute(points=((134, 48), (316, 48)), label_at=None))

    def test_same_column_is_one_vertical_line(self) -> None:
        a, b = node("a", 2, 3), node("b", 2, 1)
        route = route_edge(GridEdge(id="e", source="a", target="b"), self.rects(a, b), 600, 288)
        self.assertEqual(route.points, ((225, 214), (225, 74)))

    def test_diagonal_goes_horizontal_first_then_vertical(self) -> None:
        a, b = node("a", 1, 1), node("b", 3, 2)
        route = route_edge(GridEdge(id="e", source="a", target="b"), self.rects(a, b), 600, 288)
        self.assertEqual(route.points, ((134, 48), (375, 48), (375, 118)))

    def test_blocked_horizontal_first_falls_back_to_vertical_first(self) -> None:
        a, b, blocker = node("a", 1, 1), node("b", 3, 2), node("x", 2, 1)
        route = route_edge(GridEdge(id="e", source="a", target="b"), self.rects(a, b, blocker), 600, 288)
        self.assertEqual(route.points, ((75, 74), (75, 144), (316, 144)))

    def test_both_routes_blocked_is_reported(self) -> None:
        a, b = node("a", 1, 2), node("b", 2, 1)
        blockers = (node("x", 2, 2), node("y", 1, 1))
        route = route_edge(GridEdge(id="e", source="a", target="b"), self.rects(a, b, *blockers), 600, 288)
        self.assertEqual(route, "辺 'e' は他のノードを横切らずに引けません（折れは1回まで）")

    def test_label_sits_above_the_longest_horizontal_segment(self) -> None:
        a, b = node("a", 1, 1), node("b", 3, 1)
        route = route_edge(GridEdge(id="e", source="a", target="b", label="照合"), self.rects(a, b), 600, 288)
        self.assertEqual(route.label_at, (225, 41, "middle"))

    def test_label_that_cannot_avoid_nodes_is_reported(self) -> None:
        a, b = node("a", 1, 1), node("b", 2, 1)
        route = route_edge(GridEdge(id="e", source="a", target="b", label="三文字"), self.rects(a, b), 600, 288)
        self.assertEqual(route, "辺 'e' のラベルを置く場所がありません")

    def test_label_that_would_leave_the_picture_is_reported(self) -> None:
        a, b = node("a", 4, 1), node("b", 4, 3)
        route = route_edge(GridEdge(id="e", source="a", target="b", label="十文字のラベルです"),
                           self.rects(a, b), 600, 288)
        self.assertEqual(route, "辺 'e' のラベルを置く場所がありません")

    def test_arrowhead_is_two_short_strokes_at_the_end(self) -> None:
        self.assertEqual(arrow_lines(((134, 48), (316, 48))), ((310, 52, 316, 48), (310, 44, 316, 48)))
        self.assertEqual(arrow_lines(((375, 48), (375, 118))), ((371, 112, 375, 118), (379, 112, 375, 118)))


class CheckLayoutTest(unittest.TestCase):
    def test_clean_layout_has_no_messages(self) -> None:
        nodes = (node("a", 1, 1), node("b", 3, 2))
        self.assertEqual(check_layout(payload(nodes, edges=(GridEdge("e", "a", "b"),))), [])

    def test_out_of_grid_overlap_region_and_label_rules(self) -> None:
        nodes = (
            node("a", 1, 1),
            node("b", 1, 1),
            node("c", 4, 3, span=(2, 1)),
            node("d", 2, 2, label="法務・請求・顧客対応が 照合"),
        )
        regions = (
            GridRegion(id="r1", label="法務", from_col=1, from_row=1, to_col=2, to_row=1),
            GridRegion(id="r2", label="請求", from_col=2, from_row=1, to_col=2, to_row=2),
            GridRegion(id="r3", label="外", from_col=4, from_row=3, to_col=5, to_row=3),
        )
        self.assertEqual(check_layout(payload(nodes, regions=regions)), [
            "ノード 'c' が格子の外にあります",
            "囲み 'r3' が格子の外にあります",
            "ノード 'a' と 'b' が同じマスを占めています",
            "囲み 'r1' と 'r2' が重なっています",
            "ノード 'd' のラベルがノードに収まりません",
        ])

    def test_node_straddling_a_region_border_is_reported(self) -> None:
        nodes = (node("a", 1, 1, span=(2, 1)), node("b", 1, 3))
        regions = (GridRegion(id="r", label="法務", from_col=1, from_row=1, to_col=1, to_row=2),)
        self.assertEqual(check_layout(payload(nodes, regions=regions)),
                         ["ノード 'a' が囲み 'r' の境界をまたいでいます"])

    def test_region_label_wider_than_its_frame_is_reported(self) -> None:
        regions = (GridRegion(id="r", label="とても長い囲みの名前", from_col=1, from_row=1, to_col=1, to_row=1),)
        self.assertEqual(check_layout(payload((node("a", 2, 1), node("b", 3, 1)), regions=regions)),
                         ["囲み 'r' のラベルが囲みに収まりません"])

    def test_edge_checks_run_only_on_an_otherwise_valid_layout(self) -> None:
        nodes = (node("a", 1, 2), node("b", 2, 1), node("x", 2, 2), node("y", 1, 1))
        self.assertEqual(check_layout(payload(nodes, edges=(GridEdge("e", "a", "b"),))),
                         ["辺 'e' は他のノードを横切らずに引けません（折れは1回まで）"])


if __name__ == "__main__":
    unittest.main()
````

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_grid_layout.py -q`
Expected: collection error（`ImportError: cannot import name 'GridDiagramPayload'` または `ModuleNotFoundError: No module named 've_components.grid_layout'`）

- [ ] **Step 3: 型を足す**

`skills/visual-explain/scripts/ve_components/model.py` — old:

````python
    evidence: tuple[EvidenceItem, ...]


# ---------------------------------------------------------------------------
# Stage-deck declarations
````

new:

````python
    evidence: tuple[EvidenceItem, ...]


@dataclass(frozen=True)
class GridNode:
    """A labelled box placed on 1-based grid cells (col, row), spanning cells."""
    id: str
    label: str
    col: int
    row: int
    span_cols: int = 1
    span_rows: int = 1
    tone: str = "base"  # base | primary | warning


@dataclass(frozen=True)
class GridRegion:
    """A labelled enclosure covering the inclusive cell range from..to."""
    id: str
    label: str
    from_col: int
    from_row: int
    to_col: int
    to_row: int


@dataclass(frozen=True)
class GridEdge:
    id: str
    source: str
    target: str
    label: str = ""


@dataclass(frozen=True)
class GridMarker:
    """Overview number ``n`` drawn on node ``target``; ``ask`` optionally names the ask section."""
    n: int
    target: str
    ask: Optional[str] = None


@dataclass(frozen=True)
class GridDiagramPayload:
    cols: int
    rows: int
    nodes: tuple[GridNode, ...]
    regions: tuple[GridRegion, ...] = ()
    edges: tuple[GridEdge, ...] = ()
    markers: tuple[GridMarker, ...] = ()


# ---------------------------------------------------------------------------
# Stage-deck declarations
````

- [ ] **Step 4: `grid_layout.py` を作る**

````python
"""Pure geometry for the grid-diagram component.

The author declares cells; this module alone turns cells into integer SVG
coordinates, routes each edge as an orthogonal path with at most one bend,
and reports every placement the renderer cannot draw cleanly. Validation,
the renderer, and the final checker all import these functions, so the
build and the check compute the same numbers. Nothing here auto-repairs a
layout: a failed check returns a message and the author re-places.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

COL_W = 150
ROW_H = 96
NODE_INSET_X = 16
NODE_INSET_Y = 22
NODE_FONT = 13
NODE_PAD_X = 6
EDGE_FONT = 11
EDGE_PAD = 4
REGION_INSET = 4
REGION_FONT = 11
# Left padding (8) plus room at the right for a marker circle on a corner node.
REGION_LABEL_RESERVE = 40
ARROW_LEN = 6
ARROW_HALF = 4
MARKER_R = 10
MAX_GRID = 6
MAX_THUMB_GRID = 3
_BREAK_CHARS = (" ", "　")


@dataclass(frozen=True)
class Rect:
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0

    @property
    def cx(self) -> int:
        return (self.x0 + self.x1) // 2

    @property
    def cy(self) -> int:
        return (self.y0 + self.y1) // 2

    def overlaps(self, other: "Rect") -> bool:
        return (self.x0 < other.x1 and other.x0 < self.x1
                and self.y0 < other.y1 and other.y0 < self.y1)


@dataclass(frozen=True)
class EdgeRoute:
    points: tuple[tuple[int, int], ...]      # 2 (straight) or 3 (one bend) points
    label_at: tuple[int, int, str] | None    # (x, y, text-anchor) when the edge has a label


def viewbox(cols: int, rows: int) -> str:
    return f"0 0 {cols * COL_W} {rows * ROW_H}"


def node_rect(node) -> Rect:
    x0 = (node.col - 1) * COL_W + NODE_INSET_X
    y0 = (node.row - 1) * ROW_H + NODE_INSET_Y
    return Rect(x0, y0, x0 + node.span_cols * COL_W - 2 * NODE_INSET_X,
                y0 + node.span_rows * ROW_H - 2 * NODE_INSET_Y)


def region_rect(region) -> Rect:
    x0 = (region.from_col - 1) * COL_W + REGION_INSET
    y0 = (region.from_row - 1) * ROW_H + REGION_INSET
    return Rect(x0, y0, region.to_col * COL_W - REGION_INSET, region.to_row * ROW_H - REGION_INSET)


def node_cells(node) -> frozenset[tuple[int, int]]:
    return frozenset((c, r) for c in range(node.col, node.col + node.span_cols)
                     for r in range(node.row, node.row + node.span_rows))


def region_cells(region) -> frozenset[tuple[int, int]]:
    return frozenset((c, r) for c in range(region.from_col, region.to_col + 1)
                     for r in range(region.from_row, region.to_row + 1))


def split_label(label: str, capacity: int) -> tuple[str, ...] | None:
    """One line when it fits; else two lines at the single space or the middle; None if not."""
    if len(label) <= capacity:
        return (label,)
    breaks = [i for i, ch in enumerate(label) if ch in _BREAK_CHARS]
    if len(breaks) == 1:
        lines = (label[:breaks[0]], label[breaks[0] + 1:])
    else:
        half = (len(label) + 1) // 2
        lines = (label[:half], label[half:])
    if any(not line or len(line) > capacity for line in lines):
        return None
    return lines


def node_label_lines(node) -> tuple[str, ...] | None:
    rect = node_rect(node)
    return split_label(node.label, (rect.width - 2 * NODE_PAD_X) // NODE_FONT)


def node_label_positions(node, lines: Sequence[str]) -> tuple[tuple[int, int], ...]:
    rect = node_rect(node)
    if len(lines) == 1:
        return ((rect.cx, rect.cy + 5),)
    return ((rect.cx, rect.cy - 3), (rect.cx, rect.cy + 13))


def region_label_fits(region) -> bool:
    return len(region.label) * REGION_FONT <= region_rect(region).width - REGION_LABEL_RESERVE


def region_label_position(region) -> tuple[int, int]:
    rect = region_rect(region)
    return (rect.x0 + 8, rect.y0 + 14)


def marker_position(node) -> tuple[int, int]:
    """Circle centre on the node's top-right corner."""
    rect = node_rect(node)
    return (rect.x1, rect.y0)


def _segment_hits(a: tuple[int, int], b: tuple[int, int], rect: Rect) -> bool:
    (xa, ya), (xb, yb) = a, b
    if ya == yb:
        return rect.y0 <= ya <= rect.y1 and min(xa, xb) < rect.x1 and max(xa, xb) > rect.x0
    return rect.x0 <= xa <= rect.x1 and min(ya, yb) < rect.y1 and max(ya, yb) > rect.y0


def _label_box(a: tuple[int, int], b: tuple[int, int], label: str) -> tuple[Rect, tuple[int, int, str]]:
    width = len(label) * EDGE_FONT + 2 * EDGE_PAD
    (xa, ya), (xb, yb) = a, b
    if ya == yb:
        mx = (xa + xb) // 2
        left = mx - width // 2
        return Rect(left, ya - 18, left + width, ya - 4), (mx, ya - 7, "middle")
    my = (ya + yb) // 2
    return Rect(xa + 2, my - 9, xa + 2 + width, my + 5), (xa + 6, my + 4, "start")


def _candidates(a: Rect, b: Rect) -> list[tuple[tuple[int, int], ...]]:
    if max(a.x0, b.x0) < min(a.x1, b.x1):
        x = (max(a.x0, b.x0) + min(a.x1, b.x1)) // 2
        return [((x, a.y1), (x, b.y0)) if a.y1 <= b.y0 else ((x, a.y0), (x, b.y1))]
    if max(a.y0, b.y0) < min(a.y1, b.y1):
        y = (max(a.y0, b.y0) + min(a.y1, b.y1)) // 2
        return [((a.x1, y), (b.x0, y)) if a.x1 <= b.x0 else ((a.x0, y), (b.x1, y))]
    right, down = b.cx > a.cx, b.cy > a.cy
    horizontal_first = ((a.x1 if right else a.x0, a.cy), (b.cx, a.cy), (b.cx, b.y0 if down else b.y1))
    vertical_first = ((a.cx, a.y1 if down else a.y0), (a.cx, b.cy), (b.x0 if right else b.x1, b.cy))
    return [horizontal_first, vertical_first]


def route_edge(edge, rects: dict[str, Rect], width: int, height: int) -> EdgeRoute | str:
    """Route one edge; return the route or the diagnostic message explaining why it cannot."""
    source, target = rects[edge.source], rects[edge.target]
    others = [rect for node_id, rect in rects.items() if node_id not in (edge.source, edge.target)]
    clear = [points for points in _candidates(source, target)
             if not any(_segment_hits(p, q, rect)
                        for p, q in zip(points, points[1:]) for rect in others)]
    if not clear:
        return f"辺 '{edge.id}' は他のノードを横切らずに引けません（折れは1回まで）"
    if not edge.label:
        return EdgeRoute(points=clear[0], label_at=None)
    bounds = Rect(0, 0, width, height)
    for points in clear:
        segments = list(zip(points, points[1:]))
        longest = max(segments, key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
        box, anchor = _label_box(longest[0], longest[1], edge.label)
        inside = bounds.x0 <= box.x0 and box.x1 <= bounds.x1 and bounds.y0 <= box.y0 and box.y1 <= bounds.y1
        if inside and not any(box.overlaps(rect) for rect in rects.values()):
            return EdgeRoute(points=points, label_at=anchor)
    return f"辺 '{edge.id}' のラベルを置く場所がありません"


def arrow_lines(points: Sequence[tuple[int, int]]) -> tuple[tuple[int, int, int, int], ...]:
    """Two short strokes forming the arrowhead at the last point."""
    (px, py), (ex, ey) = points[-2], points[-1]
    dx, dy = (ex > px) - (ex < px), (ey > py) - (ey < py)
    bx, by = ex - dx * ARROW_LEN, ey - dy * ARROW_LEN
    return ((bx - dy * ARROW_HALF, by + dx * ARROW_HALF, ex, ey),
            (bx + dy * ARROW_HALF, by - dx * ARROW_HALF, ex, ey))


def check_layout(payload) -> list[str]:
    """Every reason the declared placement cannot be drawn; empty when it can."""
    messages: list[str] = []
    placed = []
    for node in payload.nodes:
        if (node.col < 1 or node.row < 1 or node.col + node.span_cols - 1 > payload.cols
                or node.row + node.span_rows - 1 > payload.rows):
            messages.append(f"ノード '{node.id}' が格子の外にあります")
        else:
            placed.append(node)
    regions = []
    for region in payload.regions:
        if region.from_col < 1 or region.from_row < 1 or region.to_col > payload.cols or region.to_row > payload.rows:
            messages.append(f"囲み '{region.id}' が格子の外にあります")
        else:
            regions.append(region)
    owner: dict[tuple[int, int], str] = {}
    clashes: list[tuple[str, str]] = []
    for node in placed:
        for cell in sorted(node_cells(node)):
            other = owner.setdefault(cell, node.id)
            if other != node.id and (other, node.id) not in clashes:
                clashes.append((other, node.id))
    messages.extend(f"ノード '{a}' と '{b}' が同じマスを占めています" for a, b in clashes)
    for region in regions:
        cells = region_cells(region)
        for node in placed:
            shared = node_cells(node) & cells
            if shared and shared != node_cells(node):
                messages.append(f"ノード '{node.id}' が囲み '{region.id}' の境界をまたいでいます")
    for i, first in enumerate(regions):
        for second in regions[i + 1:]:
            if region_cells(first) & region_cells(second):
                messages.append(f"囲み '{first.id}' と '{second.id}' が重なっています")
    for node in placed:
        if node_label_lines(node) is None:
            messages.append(f"ノード '{node.id}' のラベルがノードに収まりません")
    for region in regions:
        if not region_label_fits(region):
            messages.append(f"囲み '{region.id}' のラベルが囲みに収まりません")
    if messages:
        return messages
    rects = {node.id: node_rect(node) for node in payload.nodes}
    width, height = payload.cols * COL_W, payload.rows * ROW_H
    for edge in payload.edges:
        route = route_edge(edge, rects, width, height)
        if isinstance(route, str):
            messages.append(route)
    return messages
````

- [ ] **Step 5: テストが通ることを確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_grid_layout.py -q`
Expected: `24 passed`

- [ ] **Step 6: 全体を確認してコミットする**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest`
Expected: `1384 passed, 166 subtests passed` / `selftest: 36 passed, 0 failed`

```bash
git add skills/visual-explain/scripts/ve_components/grid_layout.py skills/visual-explain/scripts/ve_components/model.py skills/visual-explain/scripts/tests/test_grid_layout.py
git commit -m "$(cat <<'EOF'
feat(ve): add the grid geometry that places, routes and checks a grid diagram

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NgfQq9eGiPhoY46Nmdb2Xv
EOF
)"
```

---

### Task 2: ペイロード検査（構造＋配置検査 5 種）

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/diagnostics.py`, `skills/visual-explain/scripts/ve_components/validation.py`
- Test: `skills/visual-explain/scripts/tests/test_grid_diagram_validation.py`

**Interfaces:**
- Consumes: Task 1 の型と `grid_layout.check_layout` / `MAX_GRID` / `MAX_THUMB_GRID`。既存の `_check_keys` / `_is_int` / `_nonblank_str` / `DiagnosticCollector`。
- Produces: 診断コード `GRID_DIAGRAM_STRUCTURE_VIOLATION = "grid_diagram_structure_violation"`。`validation._validate_grid_diagram(raw, path, col, *, thumbnail=False) -> GridDiagramPayload | None`（Task 3 の canonical 配線と Task 5 の小図が呼ぶ）、`validation.validate_grid_diagram(raw, *, thumbnail=False) -> GridDiagramPayload`（失敗時は `ContractError`）。この時点では vocabulary に無いので canonical IR からは選べない（拡張ゲートどおり、選択可能になるのは Task 3）。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_grid_diagram_validation.py` を作る

````python
"""Phase 4: grid-diagram payload parsing and the five fail-closed layout checks."""
from __future__ import annotations

import copy
import unittest

from ve_components.diagnostics import ContractError
from ve_components.model import GridEdge, GridMarker, GridNode, GridRegion
from ve_components.validation import validate_grid_diagram

GRID = "grid_diagram_structure_violation"

BASE = {
    "grid": {"cols": 4, "rows": 3},
    "nodes": [
        {"id": "exception", "label": "契約例外", "cell": [1, 1]},
        {"id": "approval", "label": "共同承認", "cell": [3, 2], "tone": "primary"},
        {"id": "rollback", "label": "撤回条件", "cell": [4, 3], "tone": "warning"},
    ],
    "regions": [{"id": "legal", "label": "法務", "from": [1, 1], "to": [2, 1]}],
    "edges": [{"id": "e1", "from": "exception", "to": "approval", "label": "照合"}],
    "markers": [{"n": 2, "target": "approval"}],
}


def messages(raw: dict, *, thumbnail: bool = False) -> list[str]:
    with unittest.TestCase().assertRaises(ContractError) as ctx:
        validate_grid_diagram(raw, thumbnail=thumbnail)
    return [d.message for d in ctx.exception.diagnostics]


def changed(**overrides) -> dict:
    raw = copy.deepcopy(BASE)
    raw.update(overrides)
    return raw


class ParseTest(unittest.TestCase):
    def test_valid_payload_becomes_typed_records(self) -> None:
        payload = validate_grid_diagram(BASE)
        self.assertEqual((payload.cols, payload.rows), (4, 3))
        self.assertEqual(payload.nodes[0], GridNode(id="exception", label="契約例外", col=1, row=1))
        self.assertEqual(payload.nodes[1].tone, "primary")
        self.assertEqual(payload.regions, (GridRegion("legal", "法務", 1, 1, 2, 1),))
        self.assertEqual(payload.edges, (GridEdge("e1", "exception", "approval", "照合"),))
        self.assertEqual(payload.markers, (GridMarker(n=2, target="approval"),))

    def test_span_and_default_tone(self) -> None:
        raw = changed(nodes=[{"id": "a", "label": "全体", "cell": [1, 1], "span": [2, 1]},
                             {"id": "b", "label": "部分", "cell": [4, 1]}], regions=[], edges=[], markers=[{"n": 1, "target": "a"}])
        payload = validate_grid_diagram(raw)
        self.assertEqual((payload.nodes[0].span_cols, payload.nodes[0].span_rows, payload.nodes[0].tone), (2, 1, "base"))

    def test_coordinates_are_never_authored(self) -> None:
        raw = changed()
        raw["nodes"][0]["x"] = 10
        self.assertIn("認可されない生成系フィールド 'x'", messages(raw))


class StructureTest(unittest.TestCase):
    def test_grid_bounds(self) -> None:
        self.assertIn("grid.cols と grid.rows は1〜6の整数です", messages(changed(grid={"cols": 7, "rows": 3})))
        self.assertIn("grid.cols と grid.rows は1〜6の整数です", messages(changed(grid={"cols": True, "rows": 3})))

    def test_node_count_and_fields(self) -> None:
        self.assertIn("nodes は2〜12件の配列である必要があります",
                      messages(changed(nodes=BASE["nodes"][:1], edges=[], markers=[{"n": 1, "target": "exception"}])))
        raw = changed()
        raw["nodes"][0].update(label="十五文字を超えるとても長いノード名", cell=[0, 1], tone="red")
        self.assertEqual(messages(raw)[:3], [
            "node.label は1〜14字です",
            "node.cell は [列, 行] の1以上の整数2個です",
            "未知の tone 'red'",
        ])

    def test_edge_references_and_labels(self) -> None:
        raw = changed(edges=[
            {"id": "e1", "from": "ghost", "to": "approval"},
            {"id": "e2", "from": "approval", "to": "approval"},
            {"id": "e3", "from": "exception", "to": "approval", "label": "十一文字のラベルです！"},
            {"id": "e4", "from": "exception", "to": "approval"},
        ])
        self.assertEqual(messages(raw), [
            "edge.from 'ghost' がノードにありません",
            "edge.from と edge.to は別のノードである必要があります",
            "edge.label は10字以内です",
            "辺 'exception' → 'approval' が重複しています",
        ])

    def test_reverse_edge_would_draw_on_top_of_the_first(self) -> None:
        raw = changed(edges=[{"id": "e1", "from": "exception", "to": "approval"},
                             {"id": "e2", "from": "approval", "to": "exception"}])
        self.assertEqual(messages(raw), ["辺 'approval' → 'exception' は逆向きの辺と重なります"])

    def test_region_fields(self) -> None:
        raw = changed(regions=[{"id": "r", "label": "法務", "from": [2, 1], "to": [1, 1]}])
        self.assertEqual(messages(raw), ["region.from は region.to の左上にある必要があります"])

    def test_marker_rules(self) -> None:
        raw = changed(markers=[{"n": 6, "target": "approval"}, {"n": 1, "target": "ghost"},
                               {"n": 1, "target": "rollback", "ask": " "}])
        self.assertEqual(messages(raw), [
            "marker.n は1〜5の整数です",
            "marker.target 'ghost' がノードにありません",
            "marker.n 1 が重複しています",
            "marker.ask は空にできません",
        ])
        twice = changed(markers=[{"n": 1, "target": "approval"}, {"n": 2, "target": "approval"}])
        self.assertEqual(messages(twice), ["ノード 'approval' に番号が2つあります"])


class LayoutCheckTest(unittest.TestCase):
    """The spec's five checks: overlap, enclosure, crossing, label length, references/out-of-grid."""

    def test_overlap(self) -> None:
        raw = changed()
        raw["nodes"][2]["cell"] = [3, 2]
        self.assertEqual(messages(raw), ["ノード 'approval' と 'rollback' が同じマスを占めています"])

    def test_enclosure(self) -> None:
        raw = changed()
        raw["nodes"][0]["span"] = [1, 2]
        raw["regions"][0]["to"] = [2, 1]
        self.assertEqual(messages(raw), ["ノード 'exception' が囲み 'legal' の境界をまたいでいます"])

    def test_crossing(self) -> None:
        raw = changed()
        raw["nodes"].append({"id": "wall", "label": "壁", "cell": [2, 1]})
        raw["nodes"].append({"id": "wall2", "label": "壁2", "cell": [1, 2]})
        self.assertEqual(messages(raw), ["辺 'e1' は他のノードを横切らずに引けません（折れは1回まで）"])

    def test_label_length(self) -> None:
        raw = changed()
        raw["nodes"][1]["label"] = "法務・請求・顧客対応が 照合"
        self.assertEqual(messages(raw), ["ノード 'approval' のラベルがノードに収まりません"])

    def test_out_of_grid(self) -> None:
        raw = changed()
        raw["nodes"][2]["cell"] = [5, 3]
        raw["regions"][0]["to"] = [2, 4]
        self.assertEqual(messages(raw), ["ノード 'rollback' が格子の外にあります", "囲み 'legal' が格子の外にあります"])


class ThumbnailTest(unittest.TestCase):
    def test_thumbnail_is_three_by_three_at_most_and_has_no_markers(self) -> None:
        small = {"grid": {"cols": 3, "rows": 1},
                 "nodes": [{"id": "a", "label": "限定公開", "cell": [1, 1]}]}
        self.assertEqual(len(validate_grid_diagram(small, thumbnail=True).nodes), 1)
        self.assertIn("grid.cols と grid.rows は1〜3の整数です",
                      messages(changed(grid={"cols": 4, "rows": 1}), thumbnail=True))
        self.assertIn("未知のフィールド 'markers'", messages(changed(), thumbnail=True))

    def test_thumbnail_ids_must_be_unique_within_the_picture(self) -> None:
        raw = {"grid": {"cols": 3, "rows": 1},
               "nodes": [{"id": "a", "label": "一", "cell": [1, 1]}, {"id": "a", "label": "二", "cell": [3, 1]}]}
        self.assertIn("図の id 'a' が重複しています", messages(raw, thumbnail=True))


if __name__ == "__main__":
    unittest.main()
````

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_grid_diagram_validation.py -q`
Expected: collection error（`ImportError: cannot import name 'validate_grid_diagram'`）

- [ ] **Step 3: 診断コードを足す**（`diagnostics.py`）

`skills/visual-explain/scripts/ve_components/diagnostics.py` — old:

````python
KPI_STRUCTURE_VIOLATION = "kpi_structure_violation"
````

new:

````python
KPI_STRUCTURE_VIOLATION = "kpi_structure_violation"

# Phase 4 — grid-diagram structure and layout codes.
GRID_DIAGRAM_STRUCTURE_VIOLATION = "grid_diagram_structure_violation"
````

`skills/visual-explain/scripts/ve_components/diagnostics.py` — old:

````python
    KPI_STRUCTURE_VIOLATION,
    NOTATION_EMPHASIS_LIMIT,
````

new:

````python
    KPI_STRUCTURE_VIOLATION,
    GRID_DIAGRAM_STRUCTURE_VIOLATION,
    NOTATION_EMPHASIS_LIMIT,
````

- [ ] **Step 4: import を足す**（`validation.py`）

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
    KPI_ITEM_LIMIT,
    ContractError,
````

new:

````python
    KPI_ITEM_LIMIT,
    GRID_DIAGRAM_STRUCTURE_VIOLATION,
    ContractError,
````

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
from .flow_layout import assign_rails, check_row_budget, check_topology, edge_spans, order_index
````

new:

````python
from .flow_layout import assign_rails, check_row_budget, check_topology, edge_spans, order_index
from .grid_layout import MAX_GRID, MAX_THUMB_GRID, check_layout
````

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
    EvidenceMapPayload,
    FirstScreenSection,
````

new:

````python
    EvidenceMapPayload,
    GridDiagramPayload,
    GridEdge,
    GridMarker,
    GridNode,
    GridRegion,
    FirstScreenSection,
````

- [ ] **Step 5: 検査本体を「Payload dispatch」節の直前に足す**（`validation.py`）

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
# ---------------------------------------------------------------------------
# Payload dispatch (S1 generalization)
````

new:

````python
# ---------------------------------------------------------------------------
# grid-diagram (Phase 4)
# ---------------------------------------------------------------------------

_GRID_DIAGRAM_KEYS = {"grid", "nodes", "regions", "edges", "markers"}
_GRID_THUMB_KEYS = {"grid", "nodes", "regions", "edges"}
_GRID_SIZE_KEYS = {"cols", "rows"}
_GRID_NODE_KEYS = {"id", "label", "cell", "span", "tone"}
_GRID_REGION_KEYS = {"id", "label", "from", "to"}
_GRID_EDGE_KEYS = {"id", "from", "to", "label"}
_GRID_MARKER_KEYS = {"n", "target", "ask"}
_GRID_TONES = frozenset({"base", "primary", "warning"})
_MAX_GRID_NODE_LABEL = 14
_MAX_GRID_EDGE_LABEL = 10
_MAX_GRID_REGION_LABEL = 8
_MAX_GRID_EDGES = 16
_MAX_GRID_REGIONS = 4
_MAX_GRID_MARKERS = 5


def _grid_pair(value: object) -> tuple[int, int] | None:
    if isinstance(value, list) and len(value) == 2 and all(_is_int(v) and v >= 1 for v in value):
        return value[0], value[1]
    return None


def _validate_grid_diagram(raw: object, path: str, col: DiagnosticCollector, *,
                           thumbnail: bool = False) -> GridDiagramPayload | None:
    """Parse a grid-diagram payload, then run the shared layout checks (fail-closed)."""
    if not isinstance(raw, dict):
        col.add(INVALID_COMPONENT_PAYLOAD, "grid-diagram はオブジェクトである必要があります", path)
        return None
    before = len(col.diagnostics)
    _check_keys(raw, _GRID_THUMB_KEYS if thumbnail else _GRID_DIAGRAM_KEYS, path, col)
    max_grid = MAX_THUMB_GRID if thumbnail else MAX_GRID
    grid = raw.get("grid")
    cols = rows = 0
    if not isinstance(grid, dict):
        col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "grid は cols と rows を持つオブジェクトである必要があります", path)
    else:
        _check_keys(grid, _GRID_SIZE_KEYS, f"{path}.grid", col)
        cols, rows = grid.get("cols"), grid.get("rows")
        if not (_is_int(cols) and _is_int(rows) and 1 <= cols <= max_grid and 1 <= rows <= max_grid):
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION,
                    f"grid.cols と grid.rows は1〜{max_grid}の整数です", f"{path}.grid")
    low, high = (1, max_grid * max_grid) if thumbnail else (2, 12)
    nodes_raw = raw.get("nodes")
    if not isinstance(nodes_raw, list) or not low <= len(nodes_raw) <= high:
        col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, f"nodes は{low}〜{high}件の配列である必要があります", path)
    nodes_raw = nodes_raw if isinstance(nodes_raw, list) else []
    known_ids = {item.get("id") for item in nodes_raw
                 if isinstance(item, dict) and _nonblank_str(item.get("id"))}
    nodes: list[GridNode] = []
    for i, item in enumerate(nodes_raw):
        p = f"{path}.nodes[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "node はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _GRID_NODE_KEYS, p, col)
        node_id, label, tone = item.get("id"), item.get("label"), item.get("tone", "base")
        cell, span = _grid_pair(item.get("cell")), _grid_pair(item.get("span", [1, 1]))
        if not _nonblank_str(node_id):
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "node.id は空にできません", p)
        if not _nonblank_str(label) or len(label) > _MAX_GRID_NODE_LABEL:
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "node.label は1〜14字です", p)
        if cell is None:
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "node.cell は [列, 行] の1以上の整数2個です", p)
        if span is None:
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "node.span は [幅, 高さ] の1以上の整数2個です", p)
        if tone not in _GRID_TONES:
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, f"未知の tone '{tone}'", p)
        if _nonblank_str(node_id) and _nonblank_str(label) and cell and span and tone in _GRID_TONES:
            nodes.append(GridNode(id=node_id, label=label, col=cell[0], row=cell[1],
                                  span_cols=span[0], span_rows=span[1], tone=tone))
    regions_raw = raw.get("regions", [])
    if not isinstance(regions_raw, list) or len(regions_raw) > _MAX_GRID_REGIONS:
        col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "regions は0〜4件の配列である必要があります", path)
        regions_raw = regions_raw if isinstance(regions_raw, list) else []
    regions: list[GridRegion] = []
    for i, item in enumerate(regions_raw):
        p = f"{path}.regions[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "region はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _GRID_REGION_KEYS, p, col)
        region_id, label = item.get("id"), item.get("label")
        start, end = _grid_pair(item.get("from")), _grid_pair(item.get("to"))
        if not _nonblank_str(region_id):
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "region.id は空にできません", p)
        if not _nonblank_str(label) or len(label) > _MAX_GRID_REGION_LABEL:
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "region.label は1〜8字です", p)
        if start is None or end is None:
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "region.from と region.to は [列, 行] の1以上の整数2個です", p)
        elif start[0] > end[0] or start[1] > end[1]:
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "region.from は region.to の左上にある必要があります", p)
        elif _nonblank_str(region_id) and _nonblank_str(label):
            regions.append(GridRegion(id=region_id, label=label, from_col=start[0], from_row=start[1],
                                      to_col=end[0], to_row=end[1]))
    edges_raw = raw.get("edges", [])
    if not isinstance(edges_raw, list) or len(edges_raw) > _MAX_GRID_EDGES:
        col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "edges は0〜16件の配列である必要があります", path)
        edges_raw = edges_raw if isinstance(edges_raw, list) else []
    edges: list[GridEdge] = []
    pairs: set[tuple[str, str]] = set()
    for i, item in enumerate(edges_raw):
        p = f"{path}.edges[{i}]"
        if not isinstance(item, dict):
            col.add(INVALID_COMPONENT_PAYLOAD, "edge はオブジェクトである必要があります", p)
            continue
        _check_keys(item, _GRID_EDGE_KEYS, p, col)
        edge_id, source, target, label = item.get("id"), item.get("from"), item.get("to"), item.get("label", "")
        if not _nonblank_str(edge_id):
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "edge.id は空にできません", p)
        if source not in known_ids:
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, f"edge.from '{source}' がノードにありません", p)
        if target not in known_ids:
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, f"edge.to '{target}' がノードにありません", p)
        if source == target:
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "edge.from と edge.to は別のノードである必要があります", p)
        elif (source, target) in pairs:
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, f"辺 '{source}' → '{target}' が重複しています", p)
        elif (target, source) in pairs:
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, f"辺 '{source}' → '{target}' は逆向きの辺と重なります", p)
        if not isinstance(label, str) or len(label) > _MAX_GRID_EDGE_LABEL:
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "edge.label は10字以内です", p)
        if isinstance(source, str) and isinstance(target, str):
            pairs.add((source, target))
            if _nonblank_str(edge_id) and isinstance(label, str):
                edges.append(GridEdge(id=edge_id, source=source, target=target, label=label))
    markers: list[GridMarker] = []
    if "markers" in raw and not thumbnail:
        markers_raw = raw.get("markers")
        if not isinstance(markers_raw, list) or not 1 <= len(markers_raw) <= _MAX_GRID_MARKERS:
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "markers は1〜5件の配列である必要があります", path)
            markers_raw = []
        seen_n: set[int] = set()
        marked: set[str] = set()
        for i, item in enumerate(markers_raw):
            p = f"{path}.markers[{i}]"
            if not isinstance(item, dict):
                col.add(INVALID_COMPONENT_PAYLOAD, "marker はオブジェクトである必要があります", p)
                continue
            _check_keys(item, _GRID_MARKER_KEYS, p, col)
            n, target, ask = item.get("n"), item.get("target"), item.get("ask")
            if not _is_int(n) or not 1 <= n <= _MAX_GRID_MARKERS:
                col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "marker.n は1〜5の整数です", p)
            elif n in seen_n:
                col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, f"marker.n {n} が重複しています", p)
            if target not in known_ids:
                col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, f"marker.target '{target}' がノードにありません", p)
            elif target in marked:
                col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, f"ノード '{target}' に番号が2つあります", p)
            if ask is not None and not _nonblank_str(ask):
                col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, "marker.ask は空にできません", p)
            if _is_int(n):
                seen_n.add(n)
            if isinstance(target, str):
                marked.add(target)
                if _is_int(n) and (ask is None or _nonblank_str(ask)):
                    markers.append(GridMarker(n=n, target=target, ask=ask))
    if thumbnail:
        seen_ids: set[str] = set()
        for item_id in [n.id for n in nodes] + [r.id for r in regions] + [e.id for e in edges]:
            if item_id in seen_ids:
                col.add(DUPLICATE_SEMANTIC_ID, f"図の id '{item_id}' が重複しています", path)
            seen_ids.add(item_id)
    if len(col.diagnostics) > before:
        return None
    payload = GridDiagramPayload(cols=cols, rows=rows, nodes=tuple(nodes), regions=tuple(regions),
                                 edges=tuple(edges), markers=tuple(markers))
    for message in check_layout(payload):
        col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION, message, path)
    return None if len(col.diagnostics) > before else payload


def validate_grid_diagram(raw: object, *, thumbnail: bool = False) -> GridDiagramPayload:
    """Validate one grid-diagram payload on its own (tests, option thumbnails)."""
    col = DiagnosticCollector()
    payload = _validate_grid_diagram(raw, "grid-diagram", col, thumbnail=thumbnail)
    col.raise_if_any()
    assert payload is not None
    return payload


# ---------------------------------------------------------------------------
# Payload dispatch (S1 generalization)
````

- [ ] **Step 6: テストが通ることを確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_grid_diagram_validation.py -q`
Expected: `16 passed`

- [ ] **Step 7: 全体を確認してコミットする**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest`
Expected: `1400 passed, 166 subtests passed` / `selftest: 36 passed, 0 failed`

```bash
git add skills/visual-explain/scripts/ve_components/diagnostics.py skills/visual-explain/scripts/ve_components/validation.py skills/visual-explain/scripts/tests/test_grid_diagram_validation.py
git commit -m "$(cat <<'EOF'
feat(ve): validate grid diagram payloads and fail closed on bad placement

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NgfQq9eGiPhoY46Nmdb2Xv
EOF
)"
```

---

### Task 3: `grid-diagram` を 13 番目の canonical 形式として登録する（拡張ゲートを 1 コミットで）

**Files:**
- Create: `skills/visual-explain/scripts/ve_components/renderers/grid_diagram.py`, `skills/visual-explain/assets/components/grid-diagram.css`, `skills/visual-explain/scripts/tests/component-valid-grid-diagram.json`, `skills/visual-explain/scripts/tests/test_grid_diagram_renderer.py`, `skills/visual-explain/scripts/tests/grid-diagram-doc.html`（ビルド生成）, `skills/visual-explain/scripts/tests/component-bad-grid-viewbox.html`（生成）
- Modify: `skills/visual-explain/scripts/ve_components/model.py`, `validation.py`, `renderers/__init__.py`, `registry.py`, `checker.py`, `metrics.py`, `skills/visual-explain/references/component-vocabulary.json`, `component-ir.schema.json`, `skills/visual-explain/assets/components/registry.json`, `skills/visual-explain/scripts/check.sh`
- Test: `tests/test_grid_diagram_renderer.py`, `tests/test_metrics.py`, `tests/test_renderer_svg_gate.py`, `tests/test_stage_deck_registry_contract.py`, `tests/test_selftest_cases.py`

**Interfaces:**
- Consumes: Task 1 の `grid_layout` 全関数と型、Task 2 の `_validate_grid_diagram` と `GRID_DIAGRAM_STRUCTURE_VIOLATION`。既存の `renderers.common.claim_before_body` / `select_style_assets`、`model.CERTAINTY_LABEL` / `RenderManifest` / `RenderResult`、`checker._SvgSubtreeParser` / `_validate_svg_subtree` / `validate_renderer_svg` / `COMPONENT_ARTIFACT_CHECKS`。
- Produces:
  - `CanonicalIR.grid_diagram: GridDiagramPayload | None`、`payload_kind == "grid-diagram"`、`semantic_ids()` はノード → 囲み → 線の順に id を足す。
  - `renderers.grid_diagram.render_grid_svg(payload, *, svg_id, label, described_by, semantic=True) -> str`、`relation_items(payload) -> list[str]`、`render_grid_diagram(section, definition) -> RenderResult`（Task 5 が前の 2 つを使う）。DOM: `figure[data-ve-component="grid-diagram"][data-ve-grid="CxR"].ve-gd` > `figcaption.ve-gd-caption` / `p.ve-gd-summary` / `div.ve-gd-canvas > svg.ve-gd-svg.ve-gd-cols-C` / `ul.ve-gd-relations.visually-hidden` / `ul.ve-grid-diagram-notes`。SVG の中は `g.ve-gd-region` → `g.ve-gd-edge` → `g.ve-gd-node.ve-gd-tone-*` → `g.ve-gd-marker` の順。
  - `checker._grid_viewbox_from(markup, limit) -> str | None`（Task 5 も使う）、`_SvgSubtreeParser(component_key, expected_viewbox=None)`、`_validate_svg_subtree(fragment, component_key, expected_viewbox=None)`。
  - registry エントリ `grid-diagram@2`（資産 `grid-diagram.css` digest `1522386ec816d31b03e305af2ef250e4502aae5a7d205e61e7b63610c4386893` と `visual-stage`）、checker rule 名 `grid-diagram-structure`。
  - `metrics` は `.visually-hidden` の中を数えない。

- [ ] **Step 1: fixture と失敗するテストを書く**

`tests/component-valid-grid-diagram.json` を作る:

````json
{
  "schemaVersion": 2,
  "document": {
    "id": "grid-diagram-demo",
    "title": "承認の配置図",
    "summary": "根拠と顧客影響が共同承認で合流する位置を格子で示す。",
    "type": "system",
    "profile": "strict"
  },
  "sections": [
    {
      "kind": "first-screen",
      "id": "sec-first",
      "conclusion": "この資料の判断を進めます。"
    },
    {
      "kind": "canonical",
      "ir": {
        "id": "sec-grid",
        "relationship": {"kind": "spatial-layout", "capabilities": ["spatial-placement"]},
        "selection": {"component": "grid-diagram", "version": 2, "matchedCapabilities": ["spatial-placement"]},
        "caption": "何を見るか: 二つの根拠が共同承認で合流する位置",
        "certainty": [{"id": "cert-grid", "level": "inferred", "statement": "説明用の配置。"}],
        "sources": [{"id": "src-grid", "label": "承認手順メモ"}],
        "accessibility": {"label": "承認の配置図", "summary": "左に根拠、中央に共同承認、右に公開と撤回条件を置く。"},
        "grid-diagram": {
          "grid": {"cols": 4, "rows": 3},
          "nodes": [
            {"id": "exception", "label": "契約例外", "cell": [1, 1]},
            {"id": "price", "label": "料金改定案", "cell": [1, 3]},
            {"id": "approval", "label": "共同承認", "cell": [3, 2], "tone": "primary"},
            {"id": "rollback", "label": "撤回条件", "cell": [4, 3], "tone": "warning"}
          ],
          "regions": [{"id": "legal", "label": "根拠", "from": [1, 1], "to": [1, 3]}],
          "edges": [
            {"id": "e-exception", "from": "exception", "to": "approval", "label": "照合"},
            {"id": "e-price", "from": "price", "to": "approval"},
            {"id": "e-rollback", "from": "approval", "to": "rollback", "label": "見張る"}
          ]
        }
      }
    },
    {
      "kind": "closing",
      "id": "sec-closing",
      "blocks": [{"heading": "限界・確度", "items": ["説明用の配置で、実データではない。"]}]
    }
  ]
}
````

`tests/test_grid_diagram_renderer.py` を作る:

````python
"""Phase 4: grid-diagram registration, renderer DOM contract, and the final checker."""
from __future__ import annotations

import copy
import json
import unittest
from decimal import Decimal
from pathlib import Path

from build_explainer import build_document
from fixture_util import canonical_ir
from ve_components.checker import check_final_document
from ve_components.diagnostics import ContractError
from ve_components.model import CanonicalSection
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.renderers.grid_diagram import render_grid_diagram
from ve_components.validation import validate_assembly, validate_canonical_section

SKILL = Path(__file__).resolve().parents[2]
TESTS = SKILL / "scripts" / "tests"
COMPONENTS = SKILL / "assets" / "components"
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
REGISTRY = load_registry(COMPONENTS / "registry.json")
FIXTURE = "component-valid-grid-diagram.json"


def raw_fixture() -> dict:
    return json.loads((TESTS / FIXTURE).read_text("utf-8"), parse_float=Decimal)


def build(raw: dict) -> str:
    return build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS,
                          document_path="grid-diagram-doc.html")


def check(html: str) -> list[str]:
    return [d.message for d in check_final_document(html, SKELETON, REGISTRY, components_dir=COMPONENTS)]


class RegistrationTest(unittest.TestCase):
    def test_registry_and_renderer_allowlist_know_grid_diagram(self) -> None:
        definition = REGISTRY.find("grid-diagram", 2)
        self.assertIsNotNone(definition)
        self.assertEqual(definition.relationship_kind, "spatial-layout")
        self.assertEqual(definition.capabilities, ("spatial-placement",))
        self.assertEqual(definition.renderer, "grid-diagram@2")
        self.assertIn("grid-diagram@2", TRUSTED_RENDERERS)
        self.assertEqual([a.id for a in definition.assets], ["grid-diagram.css", "visual-stage"])

    def test_fixture_validates_as_a_canonical_section(self) -> None:
        ir = validate_canonical_section(canonical_ir(raw_fixture()))
        self.assertEqual(ir.payload_kind, "grid-diagram")
        self.assertEqual(ir.semantic_ids(), (
            "sec-grid", "cert-grid", "src-grid", "exception", "price", "approval", "rollback",
            "legal", "e-exception", "e-price", "e-rollback"))

    def test_annotations_are_not_offered_for_grid_diagram(self) -> None:
        ir = canonical_ir(raw_fixture())
        ir["takeawayTargetIds"] = ["approval"]
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(ir)
        self.assertIn("注釈対象が未登録のペイロード 'grid-diagram'", [d.message for d in ctx.exception.diagnostics])

    def test_semantic_ids_collide_with_certainty_ids(self) -> None:
        ir = canonical_ir(raw_fixture())
        ir["grid-diagram"]["nodes"][0]["id"] = "cert-grid"
        ir["grid-diagram"]["edges"][0]["from"] = "cert-grid"
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(ir)
        self.assertIn("意味 ID 'cert-grid' が重複しています", [d.message for d in ctx.exception.diagnostics])


class RendererTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ir = validate_canonical_section(canonical_ir(raw_fixture()))
        cls.result = render_grid_diagram(CanonicalSection(ir=ir), REGISTRY.find("grid-diagram", 2))
        cls.markup = cls.result.markup

    def test_figure_declares_its_grid_and_svg_viewbox_follows(self) -> None:
        self.assertIn('<figure data-ve-component="grid-diagram" class="ve-gd" data-ve-grid="4x3"', self.markup)
        self.assertIn('<svg id="sec-grid-svg" class="ve-gd-svg ve-gd-cols-4" viewBox="0 0 600 288"'
                      ' preserveAspectRatio="xMidYMid meet" role="img" aria-label="承認の配置図"'
                      ' aria-describedby="sec-grid-relations">', self.markup)

    def test_node_is_a_rect_and_centred_text_at_fixed_coordinates(self) -> None:
        self.assertIn(
            '<g class="ve-gd-node ve-gd-tone-primary" data-ve-semantic-id="approval">'
            '<rect class="ve-gd-node-box" x="316" y="118" width="118" height="52"></rect>'
            '<text class="ve-gd-node-label" x="375" y="149" text-anchor="middle">共同承認</text></g>',
            self.markup)

    def test_edge_is_line_pairs_with_one_bend_and_a_two_stroke_arrowhead(self) -> None:
        self.assertIn(
            '<g class="ve-gd-edge" data-ve-semantic-id="e-exception">'
            '<line class="ve-gd-edge-line" x1="134" y1="48" x2="375" y2="48"></line>'
            '<line class="ve-gd-edge-line" x1="375" y1="48" x2="375" y2="118"></line>'
            '<line class="ve-gd-edge-arrow" x1="371" y1="112" x2="375" y2="118"></line>'
            '<line class="ve-gd-edge-arrow" x1="379" y1="112" x2="375" y2="118"></line>'
            '<text class="ve-gd-edge-label" x="254" y="41" text-anchor="middle">照合</text></g>',
            self.markup)

    def test_region_is_a_frame_with_a_label(self) -> None:
        self.assertIn(
            '<g class="ve-gd-region" data-ve-semantic-id="legal">'
            '<rect class="ve-gd-region-frame" x="4" y="4" width="142" height="280"></rect>'
            '<text class="ve-gd-region-label" x="12" y="18" text-anchor="start">根拠</text></g>',
            self.markup)

    def test_reading_list_follows_the_picture(self) -> None:
        self.assertIn('<li class="ve-gd-rel-node">契約例外（根拠）</li>', self.markup)
        self.assertIn('<li class="ve-gd-rel-edge">契約例外 → 共同承認（照合）</li>', self.markup)
        self.assertIn('<li class="ve-gd-rel-edge">料金改定案 → 共同承認</li>', self.markup)

    def test_manifest_declares_the_svg_root_and_landmarks(self) -> None:
        manifest = self.result.manifest
        self.assertEqual(manifest.svg_root_ids, ("sec-grid-svg",))
        self.assertEqual(manifest.generated_landmark_ids,
                         ("sec-grid-caption", "sec-grid-summary", "sec-grid-relations", "sec-grid-svg"))
        self.assertEqual(self.result.style_asset_ids, ("grid-diagram.css",))


class FinalCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = build(raw_fixture())

    def test_built_fixture_passes_every_layer(self) -> None:
        self.assertEqual(check(self.html), [])

    def test_viewbox_must_match_the_declared_grid(self) -> None:
        forged = self.html.replace('viewBox="0 0 600 288"', 'viewBox="0 0 600 300"', 1)
        self.assertIn("viewBox は '0 0 600 288' の完全一致である必要があります", check(forged))

    def test_changing_the_grid_attribute_moves_the_expected_viewbox(self) -> None:
        forged = self.html.replace('data-ve-grid="4x3"', 'data-ve-grid="4x4"', 1)
        self.assertIn("viewBox は '0 0 600 384' の完全一致である必要があります", check(forged))

    def test_missing_grid_attribute_is_rejected(self) -> None:
        forged = self.html.replace(' data-ve-grid="4x3"', "", 1)
        self.assertIn("grid-diagram の figure に1〜6の data-ve-grid がありません", check(forged))

    def test_path_element_is_still_outside_the_allowlist(self) -> None:
        forged = self.html.replace('<g class="ve-gd-region"', '<path></path><g class="ve-gd-region"', 1)
        self.assertIn("許可されていない SVG 要素 <path>", check(forged))

    def test_reading_list_must_match_the_picture(self) -> None:
        forged = self.html.replace('<li class="ve-gd-rel-edge">料金改定案 → 共同承認</li>', "", 1)
        self.assertIn("grid-diagram の読み上げ一覧が図と一致しません", check(forged))

    def test_author_text_is_escaped_everywhere(self) -> None:
        raw = raw_fixture()
        raw["sections"][1]["ir"]["grid-diagram"]["nodes"][0]["label"] = "A&B <x>"
        html = build(raw)
        self.assertEqual(check(html), [])
        self.assertIn('text-anchor="middle">A&amp;B &lt;x&gt;</text>', html)
        self.assertIn('<li class="ve-gd-rel-node">A&amp;B &lt;x&gt;（根拠）</li>', html)

    def test_node_needs_its_box(self) -> None:
        forged = self.html.replace('class="ve-gd-node-box" x="316"', 'class="ve-gd-box" x="316"', 1)
        self.assertIn("grid-diagram ノードは rect.ve-gd-node-box を1つだけ持つ必要があります", check(forged))


if __name__ == "__main__":
    unittest.main()
````

既存テストの期待値を先に変える:

`skills/visual-explain/scripts/tests/test_metrics.py` — old:

````python
    def test_format(self) -> None:
````

new:

````python
    def test_screen_reader_only_text_is_not_counted(self) -> None:
        markup = '<p>見える</p><ul class="ve-gd-relations visually-hidden"><li>読み上げ</li></ul>'
        self.assertEqual(visible_chars(markup), 3)

    def test_format(self) -> None:
````

`skills/visual-explain/scripts/tests/test_renderer_svg_gate.py` — old:

````python
    def test_allowlist_contains_slope_and_waterfall(self) -> None:
        self.assertEqual(RENDERER_SVG_ALLOWLIST, frozenset({"slope@2", "waterfall@2"}))
````

new:

````python
    def test_allowlist_contains_slope_waterfall_and_grid_diagram(self) -> None:
        self.assertEqual(RENDERER_SVG_ALLOWLIST, frozenset({"slope@2", "waterfall@2", "grid-diagram@2"}))
````

`skills/visual-explain/scripts/tests/test_stage_deck_registry_contract.py` — old:

````python
    "kpi": ("kpi.css", "5953282c293f6788a73d77faa0cab1453330e46e86eddc62c897b4766c8c2b78"),
}
````

new:

````python
    "kpi": ("kpi.css", "5953282c293f6788a73d77faa0cab1453330e46e86eddc62c897b4766c8c2b78"),
    "grid-diagram": ("grid-diagram.css", "1522386ec816d31b03e305af2ef250e4502aae5a7d205e61e7b63610c4386893"),
}
````

`skills/visual-explain/scripts/tests/test_stage_deck_registry_contract.py` — old:

````python
    assert len(registry.components) == 12
````

new:

````python
    assert len(registry.components) == 13
````

`skills/visual-explain/scripts/tests/test_selftest_cases.py` — old:

````python
selftest: 36 passed, 0 failed
````

new:

````python
selftest: 38 passed, 0 failed
````

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_grid_diagram_renderer.py tests/test_metrics.py tests/test_renderer_svg_gate.py tests/test_stage_deck_registry_contract.py tests/test_selftest_cases.py -q`
Expected: `test_grid_diagram_renderer.py` が collection error（`No module named 've_components.renderers.grid_diagram'`）、ほかは `test_screen_reader_only_text_is_not_counted` / `test_allowlist_contains_slope_waterfall_and_grid_diagram` / registry の 2 件 / selftest の件数が FAIL

- [ ] **Step 3: canonical IR へ配線する**（`model.py`）

`skills/visual-explain/scripts/ve_components/model.py` — old:

````python
    evidence_map: Optional[EvidenceMapPayload] = None
    takeaway_target_ids
````

new:

````python
    evidence_map: Optional[EvidenceMapPayload] = None
    grid_diagram: Optional[GridDiagramPayload] = None
    takeaway_target_ids
````

`skills/visual-explain/scripts/ve_components/model.py` — old:

````python
        if self.evidence_map is not None:
            return "evidence-map"
        raise
````

new:

````python
        if self.evidence_map is not None:
            return "evidence-map"
        if self.grid_diagram is not None:
            return "grid-diagram"
        raise
````

`skills/visual-explain/scripts/ve_components/model.py` — old:

````python
            ids.extend(item.id for item in self.evidence_map.evidence)
        return tuple(ids)
````

new:

````python
            ids.extend(item.id for item in self.evidence_map.evidence)
        if self.grid_diagram is not None:
            ids.extend(node.id for node in self.grid_diagram.nodes)
            ids.extend(region.id for region in self.grid_diagram.regions)
            ids.extend(edge.id for edge in self.grid_diagram.edges)
        return tuple(ids)
````

- [ ] **Step 4: validation へ配線する**（`validation.py`）

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
    "slope", "bars", "kpi", "evidence-map",
    "takeawayTargetIds",
````

new:

````python
    "slope", "bars", "kpi", "evidence-map", "grid-diagram",
    "takeawayTargetIds",
````

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
    if payload_kind == "evidence-map":
        return {payload.conclusion.id, *(item.id for item in payload.evidence)}
    return set()


def _sequence_target_ids
````

new:

````python
    if payload_kind == "evidence-map":
        return {payload.conclusion.id, *(item.id for item in payload.evidence)}
    if payload_kind == "grid-diagram":
        return {*(n.id for n in payload.nodes), *(r.id for r in payload.regions), *(e.id for e in payload.edges)}
    return set()


def _sequence_target_ids
````

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
    evidence_map = None
    validated_payload = None
````

new:

````python
    evidence_map = None
    grid_diagram = None
    validated_payload = None
````

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
            elif payload_kind == "kpi":
                kpi = validated_payload
````

new:

````python
            elif payload_kind == "kpi":
                kpi = validated_payload
            elif payload_kind == "grid-diagram":
                grid_diagram = validated_payload
````

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
        evidence_map=evidence_map,
        takeaway_target_ids=takeaway_target_ids,
````

new:

````python
        evidence_map=evidence_map,
        grid_diagram=grid_diagram,
        takeaway_target_ids=takeaway_target_ids,
````

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
        collect(evidence_map.get("evidence"))
    seen: set[str] = set()
````

new:

````python
        collect(evidence_map.get("evidence"))
    grid_diagram = raw.get("grid-diagram")
    if isinstance(grid_diagram, dict):
        collect(grid_diagram.get("nodes"))
        collect(grid_diagram.get("regions"))
        collect(grid_diagram.get("edges"))
    seen: set[str] = set()
````

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
    "kpi": _validate_kpi,
}
````

new:

````python
    "kpi": _validate_kpi,
    "grid-diagram": _validate_grid_diagram,
}
````

- [ ] **Step 5: 語彙と schema に足す**

`references/component-vocabulary.json`:

`skills/visual-explain/references/component-vocabulary.json` — old:

````json
      "capabilities": ["metric-highlight"]
    }
  },
````

new:

````json
      "capabilities": ["metric-highlight"]
    },
    "grid-diagram": {
      "contractVersion": 2,
      "relationshipKind": "spatial-layout",
      "capabilities": ["spatial-placement"]
    }
  },
````

`references/component-ir.schema.json`（4 箇所の置換）:

`skills/visual-explain/references/component-ir.schema.json` — old:

````json
    "evidence-map": {"$ref": "#/$defs/evidenceMapPayload"},
````

new:

````json
    "evidence-map": {"$ref": "#/$defs/evidenceMapPayload"},
    "grid-diagram": {"$ref": "#/$defs/gridDiagramPayload"},
````

`skills/visual-explain/references/component-ir.schema.json` — old:

````json
"slope", "bars", "kpi", "evidence-map"]},
````

new:

````json
"slope", "bars", "kpi", "evidence-map", "grid-diagram"]},
````

`skills/visual-explain/references/component-ir.schema.json` — old:

````json
"headline-metrics", "claim-support"]},
````

new:

````json
"headline-metrics", "claim-support", "spatial-layout"]},
````

`skills/visual-explain/references/component-ir.schema.json` — old:

````json
        "claim-support-mapping",
        "typed-sequence"
````

new:

````json
        "claim-support-mapping",
        "spatial-placement",
        "typed-sequence"
````

`skills/visual-explain/references/component-ir.schema.json` — old:

````json
        "sourceRef": {"type": "string", "minLength": 1}
      }
    }
  }
}
````

new:

````json
        "sourceRef": {"type": "string", "minLength": 1}
      }
    },
    "gridDiagramPayload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["grid", "nodes"],
      "properties": {
        "grid": {"$ref": "#/$defs/gridSize"},
        "nodes": {"type": "array", "minItems": 2, "maxItems": 12, "items": {"$ref": "#/$defs/gridNode"}},
        "regions": {"type": "array", "maxItems": 4, "items": {"$ref": "#/$defs/gridRegion"}},
        "edges": {"type": "array", "maxItems": 16, "items": {"$ref": "#/$defs/gridEdge"}},
        "markers": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"$ref": "#/$defs/gridMarker"}}
      }
    },
    "gridSize": {
      "type": "object",
      "additionalProperties": false,
      "required": ["cols", "rows"],
      "properties": {
        "cols": {"type": "integer", "minimum": 1, "maximum": 6},
        "rows": {"type": "integer", "minimum": 1, "maximum": 6}
      }
    },
    "gridCell": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "integer", "minimum": 1}},
    "gridNode": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "label", "cell"],
      "properties": {
        "id": {"type": "string", "minLength": 1},
        "label": {"type": "string", "minLength": 1, "maxLength": 14},
        "cell": {"$ref": "#/$defs/gridCell"},
        "span": {"$ref": "#/$defs/gridCell"},
        "tone": {"enum": ["base", "primary", "warning"]}
      }
    },
    "gridRegion": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "label", "from", "to"],
      "properties": {
        "id": {"type": "string", "minLength": 1},
        "label": {"type": "string", "minLength": 1, "maxLength": 8},
        "from": {"$ref": "#/$defs/gridCell"},
        "to": {"$ref": "#/$defs/gridCell"}
      }
    },
    "gridEdge": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "from", "to"],
      "properties": {
        "id": {"type": "string", "minLength": 1},
        "from": {"type": "string", "minLength": 1},
        "to": {"type": "string", "minLength": 1},
        "label": {"type": "string", "maxLength": 10}
      }
    },
    "gridMarker": {
      "type": "object",
      "additionalProperties": false,
      "required": ["n", "target"],
      "properties": {
        "n": {"type": "integer", "minimum": 1, "maximum": 5},
        "target": {"type": "string", "minLength": 1},
        "ask": {"type": "string", "minLength": 1}
      }
    }
  }
}
````

`oneOf` の 12 本の枝すべてに `grid-diagram` の除外を足し、13 本目の枝を足す（1 行ずつ手で直すと漏れるので、スクリプトで行う。リポジトリルートで実行）:

```bash
python3 - <<'EOF'
import json
from pathlib import Path

path = Path("skills/visual-explain/references/component-ir.schema.json")
lines = path.read_text("utf-8").split("\n")
start = lines.index('  "oneOf": [')
end = lines.index("  ],", start)
branches = lines[start + 1:end]
assert len(branches) == 12 and not branches[-1].endswith(","), branches[-1]
updated = [line.rstrip(",")[:-3] + ', {"required": ["grid-diagram"]}]}},' for line in branches]
others = ", ".join('{"required": ["%s"]}' % name for name in (
    "matrix", "flow", "enumeration", "chevron", "pyramid", "stairs", "waterfall",
    "logic-tree", "slope", "bars", "kpi", "evidence-map"))
updated.append('    {"required": ["grid-diagram"], "not": {"anyOf": [%s]}}' % others)
lines[start + 1:end] = updated
path.write_text("\n".join(lines), "utf-8")
json.loads(path.read_text("utf-8"))
print("oneOf branches:", len(updated))
EOF
```

Expected: `oneOf branches: 13`

- [ ] **Step 6: レンダラを作り、信頼リストと rule 名に足す**

`ve_components/renderers/grid_diagram.py` を作る:

````python
"""Static, accessible renderer for the semantic ``grid-diagram`` component.

The author places nodes, regions and markers on grid cells; every coordinate,
route and colour comes from ``grid_layout`` and the component CSS. The SVG
uses only the renderer-svg allowlist (svg / g / rect / line / circle / text /
title), and a visually hidden list repeats the picture as text.
"""
from __future__ import annotations

import html

from ..grid_layout import (
    COL_W,
    MARKER_R,
    ROW_H,
    arrow_lines,
    marker_position,
    node_cells,
    node_label_lines,
    node_label_positions,
    node_rect,
    region_cells,
    region_label_position,
    region_rect,
    route_edge,
    viewbox,
)
from ..model import CERTAINTY_LABEL, CanonicalSection, GridDiagramPayload, RenderManifest, RenderResult
from .common import claim_before_body, select_style_assets

_MARKER_DIGITS = "①②③④⑤"


def _esc(value: object) -> str:
    return html.escape(str(value))


def render_grid_svg(payload: GridDiagramPayload, *, svg_id: str, label: str,
                    described_by: str, semantic: bool = True) -> str:
    """Draw one validated payload. ``semantic`` adds data-ve-semantic-id to each part."""

    def sid(item_id: str) -> str:
        return f' data-ve-semantic-id="{_esc(item_id)}"' if semantic else ""

    rects = {node.id: node_rect(node) for node in payload.nodes}
    width, height = payload.cols * COL_W, payload.rows * ROW_H
    parts: list[str] = []
    for region in payload.regions:
        rect = region_rect(region)
        lx, ly = region_label_position(region)
        parts.append(
            f'<g class="ve-gd-region"{sid(region.id)}>'
            f'<rect class="ve-gd-region-frame" x="{rect.x0}" y="{rect.y0}"'
            f' width="{rect.width}" height="{rect.height}"></rect>'
            f'<text class="ve-gd-region-label" x="{lx}" y="{ly}" text-anchor="start">{_esc(region.label)}</text>'
            f'</g>'
        )
    for edge in payload.edges:
        route = route_edge(edge, rects, width, height)
        assert not isinstance(route, str), route  # validation already ran check_layout
        lines = [
            f'<line class="ve-gd-edge-line" x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}"></line>'
            for a, b in zip(route.points, route.points[1:])
        ]
        lines.extend(
            f'<line class="ve-gd-edge-arrow" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"></line>'
            for x1, y1, x2, y2 in arrow_lines(route.points)
        )
        if route.label_at is not None:
            tx, ty, anchor = route.label_at
            lines.append(
                f'<text class="ve-gd-edge-label" x="{tx}" y="{ty}" text-anchor="{anchor}">{_esc(edge.label)}</text>'
            )
        parts.append(f'<g class="ve-gd-edge"{sid(edge.id)}>{"".join(lines)}</g>')
    for node in payload.nodes:
        rect = rects[node.id]
        label_lines = node_label_lines(node)
        assert label_lines is not None
        texts = "".join(
            f'<text class="ve-gd-node-label" x="{x}" y="{y}" text-anchor="middle">{_esc(line)}</text>'
            for line, (x, y) in zip(label_lines, node_label_positions(node, label_lines))
        )
        parts.append(
            f'<g class="ve-gd-node ve-gd-tone-{node.tone}"{sid(node.id)}>'
            f'<rect class="ve-gd-node-box" x="{rect.x0}" y="{rect.y0}"'
            f' width="{rect.width}" height="{rect.height}"></rect>{texts}</g>'
        )
    by_id = {node.id: node for node in payload.nodes}
    for marker in sorted(payload.markers, key=lambda m: m.n):
        cx, cy = marker_position(by_id[marker.target])
        parts.append(
            f'<g class="ve-gd-marker">'
            f'<circle class="ve-gd-marker-dot" cx="{cx}" cy="{cy}" r="{MARKER_R}"></circle>'
            f'<text class="ve-gd-marker-n" x="{cx}" y="{cy + 4}" text-anchor="middle">{marker.n}</text>'
            f'</g>'
        )
    return (
        f'<svg id="{_esc(svg_id)}" class="ve-gd-svg ve-gd-cols-{payload.cols}"'
        f' viewBox="{viewbox(payload.cols, payload.rows)}" preserveAspectRatio="xMidYMid meet"'
        f' role="img" aria-label="{_esc(label)}" aria-describedby="{_esc(described_by)}">'
        f'<title>{_esc(label)}</title>{"".join(parts)}</svg>'
    )


def relation_items(payload: GridDiagramPayload) -> list[str]:
    """Text twin of the picture: one item per node, edge and marker, in that order."""
    names = {node.id: node.label for node in payload.nodes}
    items: list[str] = []
    for node in payload.nodes:
        inside = [r.label for r in payload.regions if node_cells(node) <= region_cells(r)]
        where = f"（{'・'.join(inside)}）" if inside else ""
        items.append(f'<li class="ve-gd-rel-node">{_esc(node.label)}{_esc(where)}</li>')
    for edge in payload.edges:
        tail = f"（{edge.label}）" if edge.label else ""
        items.append(
            f'<li class="ve-gd-rel-edge">{_esc(names[edge.source])} → {_esc(names[edge.target])}{_esc(tail)}</li>'
        )
    for marker in sorted(payload.markers, key=lambda m: m.n):
        items.append(
            f'<li class="ve-gd-rel-marker">番号 {_MARKER_DIGITS[marker.n - 1]}: {_esc(names[marker.target])}</li>'
        )
    return items


def render_grid_diagram(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    payload = ir.grid_diagram
    assert payload is not None
    caption_id = f"{ir.id}-caption"
    summary_id = f"{ir.id}-summary"
    relations_id = f"{ir.id}-relations"
    svg_id = f"{ir.id}-svg"
    svg_markup = render_grid_svg(payload, svg_id=svg_id, label=ir.accessibility.label,
                                 described_by=relations_id)
    notes = []
    for cert in ir.certainty:
        notes.append(
            f'<li data-ve-semantic-id="{_esc(cert.id)}">'
            f'<strong>{_esc(CERTAINTY_LABEL.get(cert.level, cert.level))}:</strong> {_esc(cert.statement)}</li>'
        )
    for src in ir.sources:
        detail = f"（{_esc(src.detail)}）" if src.detail else ""
        notes.append(
            f'<li data-ve-semantic-id="{_esc(src.id)}"><strong>出典 {_esc(src.label)}</strong>{detail}</li>'
        )
    body_markup = (
        f'<figure data-ve-component="grid-diagram" class="ve-gd"'
        f' data-ve-grid="{payload.cols}x{payload.rows}" role="group"'
        f' aria-label="{_esc(ir.accessibility.label)}" aria-describedby="{_esc(summary_id)}">'
        f'<figcaption id="{_esc(caption_id)}" class="ve-gd-caption">{_esc(ir.caption)}</figcaption>'
        f'<p id="{_esc(summary_id)}" class="ve-gd-summary">{_esc(ir.accessibility.summary)}</p>'
        f'<div class="ve-gd-canvas">{svg_markup}</div>'
        f'<ul id="{_esc(relations_id)}" class="ve-gd-relations visually-hidden">'
        f'{"".join(relation_items(payload))}</ul>'
        f'<ul class="ve-grid-diagram-notes">{"".join(notes)}</ul>'
        f'</figure>'
    )
    markup = claim_before_body(ir, body_markup)
    style_assets = select_style_assets(ir, definition.assets)
    manifest = RenderManifest(
        component_id=definition.id,
        component_version=definition.version,
        instance_id=ir.id,
        consumed_semantic_ids=ir.semantic_ids(),
        generated_relationship_ids=(),
        generated_landmark_ids=(caption_id, summary_id, relations_id, svg_id),
        asset_ids=tuple(a.id for a in style_assets),
        asset_digests=tuple(a.digest for a in style_assets),
        declared_dependencies=tuple(definition.dependencies),
        fallback_mode=definition.fallback,
        svg_root_ids=(svg_id,),
    )
    return RenderResult(
        markup=markup,
        style_asset_ids=tuple(a.id for a in style_assets),
        script_asset_ids=(),
        manifest=manifest,
    )
````

`skills/visual-explain/scripts/ve_components/renderers/__init__.py` — old:

````python
from .kpi import render_kpi
````

new:

````python
from .kpi import render_kpi
from .grid_diagram import render_grid_diagram
````

`skills/visual-explain/scripts/ve_components/renderers/__init__.py` — old:

````python
    "kpi@2": render_kpi,
}
````

new:

````python
    "kpi@2": render_kpi,
    "grid-diagram@2": render_grid_diagram,
}
````

`skills/visual-explain/scripts/ve_components/registry.py` — old:

````python
    "kpi-structure",
})
````

new:

````python
    "kpi-structure",
    "grid-diagram-structure",
})
````

- [ ] **Step 7: component CSS を作り、registry にエントリを足す**

`assets/components/grid-diagram.css` を作る（末尾は改行 1 つ。digest はこのバイト列に対して固定）:

````css
[data-ve-component="grid-diagram"] { display: block; min-width: 0; margin: var(--space-3) 0; }
figure[data-ve-component="grid-diagram"] .ve-gd-caption { margin: 0 0 var(--space-1); font-weight: 700; font-size: var(--fs-h2); max-width: var(--w-narrative); }
figure[data-ve-component="grid-diagram"] .ve-gd-summary { margin: 0 0 var(--space-2); color: var(--text-dim); font-size: var(--fs-small); max-width: var(--w-narrative); }
[data-ve-component="grid-diagram"] .ve-gd-canvas { overflow-x: auto; }
[data-ve-component="grid-diagram"] .ve-gd-svg { display: block; width: 100%; margin: 0 auto; }
[data-ve-component="grid-diagram"] .ve-gd-svg.ve-gd-cols-1 { min-width: 7.5rem; max-width: 9.375rem; }
[data-ve-component="grid-diagram"] .ve-gd-svg.ve-gd-cols-2 { min-width: 15rem; max-width: 18.75rem; }
[data-ve-component="grid-diagram"] .ve-gd-svg.ve-gd-cols-3 { min-width: 22.5rem; max-width: 28.125rem; }
[data-ve-component="grid-diagram"] .ve-gd-svg.ve-gd-cols-4 { min-width: 30rem; max-width: 37.5rem; }
[data-ve-component="grid-diagram"] .ve-gd-svg.ve-gd-cols-5 { min-width: 37.5rem; max-width: 46.875rem; }
[data-ve-component="grid-diagram"] .ve-gd-svg.ve-gd-cols-6 { min-width: 45rem; max-width: 56.25rem; }
[data-ve-component="grid-diagram"] .ve-gd-region-frame { fill: none; stroke: var(--dg-line); stroke-width: 1.5; stroke-dasharray: 5 4; rx: 10px; }
[data-ve-component="grid-diagram"] .ve-gd-region-label { fill: var(--text-dim); font-size: 11px; font-weight: 700; }
[data-ve-component="grid-diagram"] .ve-gd-edge-line, [data-ve-component="grid-diagram"] .ve-gd-edge-arrow { stroke: var(--dg-line); stroke-width: 1.5; stroke-linecap: round; }
[data-ve-component="grid-diagram"] .ve-gd-edge-label { fill: var(--text-dim); font-size: 11px; }
[data-ve-component="grid-diagram"] .ve-gd-node-box { rx: 6px; }
[data-ve-component="grid-diagram"] .ve-gd-node-label { font-size: 13px; }
[data-ve-component="grid-diagram"] .ve-gd-tone-base .ve-gd-node-box { fill: var(--dg-primary-light); }
[data-ve-component="grid-diagram"] .ve-gd-tone-base .ve-gd-node-label { fill: var(--text); }
[data-ve-component="grid-diagram"] .ve-gd-tone-primary .ve-gd-node-box { fill: var(--dg-primary); }
[data-ve-component="grid-diagram"] .ve-gd-tone-primary .ve-gd-node-label { fill: var(--dg-on-primary); font-weight: 700; }
[data-ve-component="grid-diagram"] .ve-gd-tone-warning .ve-gd-node-box { fill: var(--bg); stroke: var(--dg-negative); stroke-width: 2; }
[data-ve-component="grid-diagram"] .ve-gd-tone-warning .ve-gd-node-label { fill: var(--text); }
[data-ve-component="grid-diagram"] .ve-gd-marker-dot { fill: var(--accent); }
[data-ve-component="grid-diagram"] .ve-gd-marker-n { fill: var(--bg); font-size: 12px; font-weight: 700; }
[data-ve-component="grid-diagram"] .ve-grid-diagram-notes { margin: var(--space-2) 0 0; padding-left: var(--space-2); color: var(--text-dim); font-size: var(--fs-small); }
[data-ve-component="grid-diagram"] .ve-grid-diagram-notes li { margin: 0; }
figure[data-ve-component="grid-diagram"].ve-gd-thumb { margin: var(--space-1) 0 0; }
figure[data-ve-component="grid-diagram"].ve-gd-thumb .ve-gd-svg { min-width: 0; margin: 0; }
figure[data-ve-component="grid-diagram"].ve-gd-thumb .ve-gd-svg.ve-gd-cols-1 { max-width: 8rem; }
figure[data-ve-component="grid-diagram"].ve-gd-thumb .ve-gd-svg.ve-gd-cols-2 { max-width: 16rem; }
figure[data-ve-component="grid-diagram"].ve-gd-thumb .ve-gd-svg.ve-gd-cols-3 { max-width: 24rem; }
````

registry に新エントリを足す（既存エントリは触らない。リポジトリルートで実行）:

```bash
python3 - <<'EOF'
import hashlib
import json
from pathlib import Path

components = Path("skills/visual-explain/assets/components")
registry = components / "registry.json"
data = json.loads(registry.read_text("utf-8"))
assert all(c["id"] != "grid-diagram" for c in data["components"])
digest = hashlib.sha256((components / "grid-diagram.css").read_bytes()).hexdigest()
data["components"].append({
    "id": "grid-diagram",
    "version": 2,
    "relationshipKind": "spatial-layout",
    "capabilities": ["spatial-placement"],
    "semanticResponsibility": "格子上の配置そのものが意味を持つ関係（近さ・上下・囲み）のみを担う。",
    "requiredInputs": ["caption", "accessibility", "grid", "nodes"],
    "optionalInputs": ["certainty", "sources", "regions", "edges", "markers"],
    "behavior": "宣言された格子のマスにノードと囲みを置き、直交1回折れの線で結んだ決定的 SVG を描画する。",
    "slots": ["caption", "certainty", "source", "accessibility"],
    "accessibility": "caption/summary を持つラベル付き figure、SVG 代替テキスト、ノード・関係・番号の読み上げ一覧。",
    "responsive": True,
    "dependencies": [],
    "fallback": "static-content",
    "checkerRules": ["static-content", "semantic-ids", "escaping", "no-external-reference",
                     "responsive-order", "grid-diagram-structure", "renderer-svg"],
    "renderer": "grid-diagram@2",
    "assets": [
        {"id": "grid-diagram.css", "slot": "styles", "path": "grid-diagram.css", "digest": digest},
        {"id": "visual-stage", "slot": "styles", "path": "visual-stage.css",
         "digest": "991e15a7616d1b411a843881de666e9d24846ba6d23fd2f58a98b38089faede8"},
    ],
})
registry.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
print(digest)
EOF
```

Expected: `1522386ec816d31b03e305af2ef250e4502aae5a7d205e61e7b63610c4386893`（違う場合は CSS のバイト列が本計画と違う。止めて報告する）

- [ ] **Step 8: checker を足す**（`checker.py`）

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
    FORBIDDEN_CONTENT_MARKUP,
    INVALID_CONTROLLED_ASSET,
````

new:

````python
    FORBIDDEN_CONTENT_MARKUP,
    GRID_DIAGRAM_STRUCTURE_VIOLATION,
    INVALID_CONTROLLED_ASSET,
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
from .validation import VOCABULARY, scan_author_markup_bans
````

new:

````python
from .grid_layout import MAX_GRID, viewbox as grid_viewbox
from .validation import VOCABULARY, scan_author_markup_bans
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
RENDERER_SVG_ALLOWLIST = frozenset({"slope@2", "waterfall@2"})
````

new:

````python
RENDERER_SVG_ALLOWLIST = frozenset({"slope@2", "waterfall@2", "grid-diagram@2"})
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
_SVG_OPEN_RE = re.compile(r"<svg\b([^>]*)>", re.IGNORECASE)
_WRAPPER_SECTION_RE
````

new:

````python
_SVG_OPEN_RE = re.compile(r"<svg\b([^>]*)>", re.IGNORECASE)
# grid-diagram declares its grid on the figure; the checker derives the viewBox from it.
_GRID_ATTR_RE = re.compile(r'\bdata-ve-grid="([1-9][0-9]*)x([1-9][0-9]*)"')
_WRAPPER_SECTION_RE
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
    def __init__(self, component_key: str = "slope@2") -> None:
        super().__init__(convert_charrefs=True)
        self.diagnostics: list[Diagnostic] = []
        self._svg_depth = 0
        self._component_key = component_key
````

new:

````python
    def __init__(self, component_key: str = "slope@2", expected_viewbox: str | None = None) -> None:
        super().__init__(convert_charrefs=True)
        self.diagnostics: list[Diagnostic] = []
        self._svg_depth = 0
        self._component_key = component_key
        self._expected_viewbox = expected_viewbox
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
            expected = _RENDERER_SVG_VIEWBOX.get(self._component_key, _RENDERER_SVG_VIEWBOX["slope@2"])
````

new:

````python
            expected = self._expected_viewbox or _RENDERER_SVG_VIEWBOX.get(
                self._component_key, _RENDERER_SVG_VIEWBOX["slope@2"])
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
def _validate_svg_subtree(fragment: str, component_key: str = "slope@2") -> list[Diagnostic]:
    parser = _SvgSubtreeParser(component_key=component_key)
````

new:

````python
def _validate_svg_subtree(fragment: str, component_key: str = "slope@2",
                          expected_viewbox: str | None = None) -> list[Diagnostic]:
    parser = _SvgSubtreeParser(component_key=component_key, expected_viewbox=expected_viewbox)
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
    diagnostics.extend(_validate_svg_subtree(fragment, component_key))
    return diagnostics


def validate_renderer_svg
````

new:

````python
    diagnostics.extend(_validate_svg_subtree(fragment, component_key))
    return diagnostics


def _grid_viewbox_from(markup: str, limit: int) -> str | None:
    """Expected viewBox from the first data-ve-grid in ``markup``; None if absent or too large."""
    match = _GRID_ATTR_RE.search(markup)
    if match is None:
        return None
    cols, rows = int(match.group(1)), int(match.group(2))
    if cols > limit or rows > limit:
        return None
    return grid_viewbox(cols, rows)


def validate_renderer_svg
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
        unit_diagnostics: list[Diagnostic] = []
        svg_matches = list(_SVG_OPEN_RE.finditer(body))
````

new:

````python
        unit_diagnostics: list[Diagnostic] = []
        expected_viewbox = None
        if component == "grid-diagram":
            expected_viewbox = _grid_viewbox_from(body, MAX_GRID)
            if expected_viewbox is None:
                unit_diagnostics.append(Diagnostic(
                    RENDERER_SVG_VIOLATION,
                    "grid-diagram の figure に1〜6の data-ve-grid がありません",
                ))
        svg_matches = list(_SVG_OPEN_RE.finditer(body))
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
            subtree = body[start:end + len("</svg>")]
            unit_diagnostics.extend(_validate_svg_subtree(subtree, component_key))
````

new:

````python
            subtree = body[start:end + len("</svg>")]
            unit_diagnostics.extend(_validate_svg_subtree(subtree, component_key, expected_viewbox))
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
def _check_bars_artifact(body: str, parser: _DomSemanticParser) -> list[Diagnostic]:
````

new:

````python
def _check_grid_diagram_artifact(body: str, parser: _DomSemanticParser) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    def fail(message: str) -> None:
        diagnostics.append(Diagnostic(GRID_DIAGRAM_STRUCTURE_VIOLATION, message))

    if len(_SVG_OPEN_RE.findall(body)) != 1:
        fail("grid-diagram には <svg> がちょうど1つ必要です")
    nodes = re.findall(r"<g\s+([^>]*\bve-gd-node\b[^>]*)>(.*?)</g>", body, re.DOTALL)
    if not 2 <= len(nodes) <= 12:
        fail(f"grid-diagram のノードは2〜12個である必要があります (found {len(nodes)})")
    for attrs, inner in nodes:
        if 'data-ve-semantic-id="' not in attrs:
            fail("grid-diagram ノードに data-ve-semantic-id がありません")
        if len(re.findall(r"<rect\s+[^>]*\bve-gd-node-box\b", inner)) != 1:
            fail("grid-diagram ノードは rect.ve-gd-node-box を1つだけ持つ必要があります")
    edges = re.findall(r"<g\s+[^>]*\bve-gd-edge\b", body)
    markers = re.findall(r"<g\s+[^>]*\bve-gd-marker\b[^>]*>(.*?)</g>", body, re.DOTALL)
    for kind, count in (("node", len(nodes)), ("edge", len(edges)), ("marker", len(markers))):
        if len(re.findall(rf'<li class="ve-gd-rel-{kind}"', body)) != count:
            fail("grid-diagram の読み上げ一覧が図と一致しません")
            break
    numbers = [re.sub(r"<[^>]+>", "", inner).strip() for inner in markers]
    if any(re.fullmatch(r"[1-5]", n) is None for n in numbers) or len(set(numbers)) != len(numbers):
        fail("grid-diagram の番号は1〜5の重複しない数字である必要があります")
    return diagnostics


def _check_bars_artifact(body: str, parser: _DomSemanticParser) -> list[Diagnostic]:
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
    "evidence-map": _check_evidence_map_artifact,
}
````

new:

````python
    "evidence-map": _check_evidence_map_artifact,
    "grid-diagram": _check_grid_diagram_artifact,
}
````

- [ ] **Step 9: 読み上げ一覧を字数から外す**（`metrics.py`）

`skills/visual-explain/scripts/ve_components/metrics.py` — old:

````python
_CHROME_CLASSES = frozenset({"ask-kind", "ask-badge", "ask-withdrawn-note", "ask-memo", "ask-prefix"})
````

new:

````python
_CHROME_CLASSES = frozenset({"ask-kind", "ask-badge", "ask-withdrawn-note", "ask-memo", "ask-prefix"})
# Screen-reader twins of a picture (relation lists) are not read by the eye.
_HIDDEN_CLASSES = frozenset({"visually-hidden"})
````

`skills/visual-explain/scripts/ve_components/metrics.py` — old:

````python
                           parent_skip or bool(classes & _CHROME_CLASSES)))
````

new:

````python
                           parent_skip or bool(classes & (_CHROME_CLASSES | _HIDDEN_CLASSES))))
````

- [ ] **Step 10: selftest の文書を作る**

`skills/visual-explain/scripts/check.sh` — old:

````bash
        ("v3-proposal-doc.html", ()),
````

new:

````bash
        ("v3-proposal-doc.html", ()),
        ("grid-diagram-doc.html", ()),
        ("component-bad-grid-viewbox.html", ("viewBox は '0 0 600 288' の完全一致である必要があります",)),
````

```bash
cd skills/visual-explain/scripts && python3 build_explainer.py --assembly tests/component-valid-grid-diagram.json --output tests/grid-diagram-doc.html && cd ../../..
```
Expected: `OK: tests/grid-diagram-doc.html` / `本文 141 字 / 図より前 0 字 / 図 1 点`

リポジトリルートで:

```bash
python3 - <<'EOF'
from pathlib import Path

tests = Path("skills/visual-explain/scripts/tests")
good = (tests / "grid-diagram-doc.html").read_text("utf-8")
assert good.count('viewBox="0 0 600 288"') == 1
(tests / "component-bad-grid-viewbox.html").write_text(
    good.replace('viewBox="0 0 600 288"', 'viewBox="0 0 600 300"'), "utf-8")
print("wrote component-bad-grid-viewbox.html")
EOF
```

- [ ] **Step 11: テストが通ることを確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_grid_diagram_renderer.py -q && bash check.sh tests/grid-diagram-doc.html && bash check.sh --selftest`
Expected: `18 passed` / `PASS` / `selftest: 38 passed, 0 failed`

- [ ] **Step 12: 全体を確認してコミットする**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q`
Expected: `1419 passed, 166 subtests passed`

```bash
git add skills/visual-explain/scripts/ve_components skills/visual-explain/assets/components/grid-diagram.css skills/visual-explain/assets/components/registry.json skills/visual-explain/references/component-vocabulary.json skills/visual-explain/references/component-ir.schema.json skills/visual-explain/scripts/check.sh skills/visual-explain/scripts/tests/component-valid-grid-diagram.json skills/visual-explain/scripts/tests/grid-diagram-doc.html skills/visual-explain/scripts/tests/component-bad-grid-viewbox.html skills/visual-explain/scripts/tests/test_grid_diagram_renderer.py skills/visual-explain/scripts/tests/test_metrics.py skills/visual-explain/scripts/tests/test_renderer_svg_gate.py skills/visual-explain/scripts/tests/test_stage_deck_registry_contract.py skills/visual-explain/scripts/tests/test_selftest_cases.py
git commit -m "$(cat <<'EOF'
feat(ve): register grid-diagram as the thirteenth canonical format

The SVG gate admits grid-diagram@2 with the same closed element and
attribute lists; only its viewBox is computed from the figure's grid.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NgfQq9eGiPhoY46Nmdb2Xv
EOF
)"
```

---

### Task 4: 全体図の番号をノードに描く（文書横断の検査）

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/validation.py`
- Test: `skills/visual-explain/scripts/tests/test_grid_diagram_overview.py`

**Interfaces:**
- Consumes: Task 3 の `CanonicalIR.grid_diagram` と、レンダラが `markers` を `g.ve-gd-marker`（丸と数字）と `li.ve-gd-rel-marker` に描くこと（Task 3 で実装済み）。既存の `FirstScreenSection.overview`。
- Produces: `validation._validate_grid_markers(sections, col)`（`validate_assembly` が `_validate_overview_links` の直後に呼ぶ）。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_grid_diagram_overview.py` を作る

````python
"""Phase 4: the overview figure as a grid-diagram draws the overview numbers on its nodes."""
from __future__ import annotations

import json
import unittest
from decimal import Decimal
from pathlib import Path

from build_explainer import build_document
from ve_components.checker import check_final_document
from ve_components.diagnostics import ContractError
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.validation import validate_assembly

SKILL = Path(__file__).resolve().parents[2]
TESTS = SKILL / "scripts" / "tests"
COMPONENTS = SKILL / "assets" / "components"
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
REGISTRY = load_registry(COMPONENTS / "registry.json")


def overview_assembly() -> dict:
    """The grid fixture promoted to the overview figure, with three marked targets."""
    raw = json.loads((TESTS / "component-valid-grid-diagram.json").read_text("utf-8"), parse_float=Decimal)
    first, grid, closing = raw["sections"]
    first["overview"] = {"section": "sec-grid", "markers": [
        {"n": 1, "label": "例外の扱い", "target": "sec-exception"},
        {"n": 2, "label": "共同承認の役割", "target": "sec-approval"},
        {"n": 3, "label": "撤回の条件", "target": "sec-closing"},
    ]}
    grid["ir"]["grid-diagram"]["markers"] = [
        {"n": 1, "target": "exception"},
        {"n": 2, "target": "approval"},
        {"n": 3, "target": "rollback", "ask": "sec-closing"},
    ]
    narratives = [
        {"kind": "narrative", "id": "sec-exception",
         "markup": "<section><h2>契約例外は法務が先に分類する</h2><p>分類が済むまで公開しない。</p></section>"},
        {"kind": "narrative", "id": "sec-approval",
         "markup": "<section><h2>共同承認で三部門がそろう</h2><p>一つの場で照合する。</p></section>"},
    ]
    raw["sections"] = [first, grid, *narratives, closing]
    return raw


def build(raw: dict) -> str:
    return build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS,
                          document_path="grid-overview.html")


def errors(raw: dict) -> list[str]:
    with unittest.TestCase().assertRaises(ContractError) as ctx:
        validate_assembly(raw)
    return [d.message for d in ctx.exception.diagnostics]


class OverviewMarkersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = build(overview_assembly())

    def test_document_passes_every_layer(self) -> None:
        self.assertEqual(check_final_document(self.html, SKELETON, REGISTRY, components_dir=COMPONENTS), [])

    def test_marker_is_a_blue_circle_on_the_node_top_right(self) -> None:
        self.assertIn(
            '<g class="ve-gd-marker"><circle class="ve-gd-marker-dot" cx="434" cy="118" r="10"></circle>'
            '<text class="ve-gd-marker-n" x="434" y="122" text-anchor="middle">2</text></g>',
            self.html)

    def test_numbers_are_also_listed_in_text(self) -> None:
        self.assertIn('<li class="ve-gd-rel-marker">番号 ②: 共同承認</li>', self.html)
        self.assertIn('<nav class="overview-markers" aria-label="この資料の論点">', self.html)

    def test_forged_marker_number_is_rejected_by_the_checker(self) -> None:
        forged = self.html.replace('text-anchor="middle">2</text></g>', 'text-anchor="middle">9</text></g>', 1)
        messages = [d.message for d in check_final_document(forged, SKELETON, REGISTRY, components_dir=COMPONENTS)]
        self.assertIn("grid-diagram の番号は1〜5の重複しない数字である必要があります", messages)


class OverviewMarkerRulesTest(unittest.TestCase):
    def test_overview_grid_must_carry_every_overview_number(self) -> None:
        raw = overview_assembly()
        raw["sections"][1]["ir"]["grid-diagram"]["markers"].pop()
        self.assertIn("全体図の grid-diagram の markers は first-screen.overview.markers と同じ番号を持つ必要があります",
                      errors(raw))
        del raw["sections"][1]["ir"]["grid-diagram"]["markers"]
        self.assertIn("全体図の grid-diagram の markers は first-screen.overview.markers と同じ番号を持つ必要があります",
                      errors(raw))

    def test_marker_ask_must_agree_with_the_overview_target(self) -> None:
        raw = overview_assembly()
        raw["sections"][1]["ir"]["grid-diagram"]["markers"][2]["ask"] = "sec-approval"
        self.assertIn("grid-diagram の marker 3 の ask 'sec-approval' は first-screen.overview.markers"
                      " の同じ番号の target と一致する必要があります", errors(raw))

    def test_markers_outside_the_overview_figure_are_rejected(self) -> None:
        raw = json.loads((TESTS / "component-valid-grid-diagram.json").read_text("utf-8"), parse_float=Decimal)
        raw["sections"][1]["ir"]["grid-diagram"]["markers"] = [{"n": 1, "target": "approval"}]
        self.assertIn("grid-diagram の markers は first-screen.overview の図にだけ付けられます", errors(raw))


if __name__ == "__main__":
    unittest.main()
````

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_grid_diagram_overview.py -q`
Expected: `OverviewMarkerRulesTest` の 3 件が FAIL（`AssertionError: ContractError not raised`）。描画の 4 件は Task 3 の実装で通る。

- [ ] **Step 3: 検査を足す**（`validation.py`）

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
    _validate_overview_links(sections_raw, sections, col)
````

new:

````python
    _validate_overview_links(sections_raw, sections, col)
    _validate_grid_markers(sections, col)
````

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
def _validate_ask_section(raw: dict, path: str, col: DiagnosticCollector, seen_ids: set[str]):
````

new:

````python
def _validate_grid_markers(sections: list[object], col: DiagnosticCollector) -> None:
    """Numbers on a grid-diagram are the overview's numbers: only on the overview figure, all of them."""
    first = sections[0] if sections and isinstance(sections[0], FirstScreenSection) else None
    overview = first.overview if first is not None else None
    overview_id = overview.section if overview is not None else None
    for section in sections:
        if not isinstance(section, CanonicalSection) or section.ir.grid_diagram is None:
            continue
        grid = section.ir.grid_diagram
        where = f"assembly.sections[{sections.index(section)}]"
        if section.ir.id != overview_id:
            if grid.markers:
                col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION,
                        "grid-diagram の markers は first-screen.overview の図にだけ付けられます", where)
            continue
        targets = {m.n: m.target for m in overview.markers}
        if {m.n for m in grid.markers} != set(targets):
            col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION,
                    "全体図の grid-diagram の markers は first-screen.overview.markers と同じ番号を持つ必要があります",
                    where)
        for marker in grid.markers:
            if marker.ask is not None and targets.get(marker.n) != marker.ask:
                col.add(GRID_DIAGRAM_STRUCTURE_VIOLATION,
                        f"grid-diagram の marker {marker.n} の ask '{marker.ask}' は"
                        f" first-screen.overview.markers の同じ番号の target と一致する必要があります",
                        where)


def _validate_ask_section(raw: dict, path: str, col: DiagnosticCollector, seen_ids: set[str]):
````

- [ ] **Step 4: テストが通ることを確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_grid_diagram_overview.py -q`
Expected: `7 passed`

- [ ] **Step 5: 全体を確認してコミットする**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest`
Expected: `1426 passed, 166 subtests passed` / `selftest: 38 passed, 0 failed`

```bash
git add skills/visual-explain/scripts/ve_components/validation.py skills/visual-explain/scripts/tests/test_grid_diagram_overview.py
git commit -m "$(cat <<'EOF'
feat(ve): put the overview numbers on the nodes of a grid overview figure

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NgfQq9eGiPhoY46Nmdb2Xv
EOF
)"
```

---

### Task 5: 選択肢の小図（案 A と案 B を絵で比べる）

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/model.py`, `validation.py`, `renderers/grid_diagram.py`, `document_sections.py`, `assembly.py`, `checker.py`, `skills/visual-explain/scripts/build_explainer.py`, `skills/visual-explain/references/assembly.schema.json`
- Test: `skills/visual-explain/scripts/tests/test_grid_diagram_thumbnails.py`

**Interfaces:**
- Consumes: Task 2 の `_validate_grid_diagram(..., thumbnail=True)`、Task 3 の `render_grid_svg` / `relation_items` / `_grid_viewbox_from` / registry の `grid-diagram.css`。既存の `render_ask` → `_render_decision_body`、`compose_document`、`AssetRef`、`validate_renderer_svg`。
- Produces: `AskOption.figure: GridDiagramPayload | None`、`renderers.grid_diagram.render_option_figure(payload, *, id_base, label) -> str`、`assembly.add_option_figure_assets(composition, asks, registry) -> CompositionResult`、`checker._validate_ask_thumbnails(attrs, body) -> list[Diagnostic]`、`_validate_closed_svg(..., expected_viewbox=None)`。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_grid_diagram_thumbnails.py` を作る

````python
"""Phase 4: a decision option may carry a small grid-diagram picture of what it looks like."""
from __future__ import annotations

import copy
import re
import unittest
from pathlib import Path

from build_explainer import build_document
from ve_components.checker import check_final_document
from ve_components.diagnostics import ContractError
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.validation import validate_assembly

SKILL = Path(__file__).resolve().parents[2]
COMPONENTS = SKILL / "assets" / "components"
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
REGISTRY = load_registry(COMPONENTS / "registry.json")

LIMITED = {
    "grid": {"cols": 3, "rows": 1},
    "nodes": [
        {"id": "limited", "label": "限定対象で公開", "cell": [1, 1], "tone": "primary"},
        {"id": "check", "label": "影響を確認", "cell": [2, 1]},
        {"id": "expand", "label": "全顧客へ拡大", "cell": [3, 1]},
    ],
    "edges": [{"id": "e1", "from": "limited", "to": "check"}, {"id": "e2", "from": "check", "to": "expand"}],
}
ALL = {
    "grid": {"cols": 3, "rows": 1},
    "nodes": [
        {"id": "all", "label": "全顧客へ一斉公開", "cell": [1, 1], "span": [2, 1], "tone": "primary"},
        {"id": "risk", "label": "誤りも全体へ", "cell": [3, 1], "tone": "warning"},
    ],
    "edges": [{"id": "e1", "from": "all", "to": "risk"}],
}


def assembly() -> dict:
    return {
        "schemaVersion": 2,
        "document": {"id": "thumbs", "title": "公開範囲の判断", "summary": "選択肢ごとの公開の形を図で比べる。",
                     "type": "system", "profile": "strict"},
        "sections": [
            {"kind": "first-screen", "id": "sec-first", "conclusion": "限定対象から公開を始める。"},
            {"kind": "ask", "id": "sec-ask", "askType": "decision",
             "question": "どの範囲から公開しますか？",
             "evidence": "照合シートの試算「契約例外 12 件のうち 9 件が同じ顧客群に集中」",
             "defaultId": "limited",
             "options": [
                 {"id": "limited", "label": "限定対象で段階公開する", "benefit": "影響を限定できる",
                  "tradeoff": "運用が増える", "figure": copy.deepcopy(LIMITED)},
                 {"id": "all", "label": "全顧客へ一斉公開する", "benefit": "切替が一度で済む",
                  "tradeoff": "誤りが全体に及ぶ", "figure": copy.deepcopy(ALL)},
             ]},
            {"kind": "closing", "id": "sec-closing",
             "blocks": [{"heading": "限界・確度", "items": ["説明用の想定です。"]}]},
        ],
    }


def build(raw: dict) -> str:
    return build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS, document_path="thumbs.html")


def check(html: str) -> list[str]:
    return [d.message for d in check_final_document(html, SKELETON, REGISTRY, components_dir=COMPONENTS)]


def errors(raw: dict) -> list[str]:
    with unittest.TestCase().assertRaises(ContractError) as ctx:
        validate_assembly(raw)
    return [d.message for d in ctx.exception.diagnostics]


class ThumbnailValidationTest(unittest.TestCase):
    def test_option_figure_is_parsed(self) -> None:
        request = validate_assembly(assembly())
        ask = request.sections[1]
        self.assertEqual([o.figure.cols for o in ask.options], [3, 3])

    def test_option_figure_is_three_by_three_at_most(self) -> None:
        raw = assembly()
        raw["sections"][1]["options"][0]["figure"]["grid"] = {"cols": 4, "rows": 1}
        self.assertIn("grid.cols と grid.rows は1〜3の整数です", errors(raw))

    def test_pictures_go_on_every_live_option_or_none(self) -> None:
        raw = assembly()
        del raw["sections"][1]["options"][1]["figure"]
        self.assertIn("選択肢の図は、取り下げていない選択肢すべてに付ける必要があります", errors(raw))
        raw["sections"][1]["options"].append({"id": "hold", "label": "保留", "benefit": "影響なし",
                                              "tradeoff": "目的未達", "withdrawn": True})
        raw["sections"][1]["options"][1]["figure"] = copy.deepcopy(ALL)
        validate_assembly(raw)  # a withdrawn option needs no picture


class ThumbnailRenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = build(assembly())

    def test_document_passes_every_layer(self) -> None:
        self.assertEqual(check(self.html), [])

    def test_picture_sits_inside_its_option(self) -> None:
        self.assertRegex(self.html, re.compile(
            r'<li data-ask-option data-ask-option-id="limited" data-ask-default>.*?'
            r'<figure data-ve-component="grid-diagram" class="ve-gd ve-gd-thumb" data-ve-thumb'
            r' data-ve-grid="3x1" aria-label="限定対象で段階公開する の図">'
            r'<svg id="sec-ask-opt-1-svg" class="ve-gd-svg ve-gd-cols-3" viewBox="0 0 450 96"', re.S))
        self.assertIn('<svg id="sec-ask-opt-2-svg"', self.html)

    def test_picture_has_no_semantic_ids_or_review_numbers(self) -> None:
        figures = re.findall(r'<figure data-ve-component="grid-diagram" class="ve-gd ve-gd-thumb".*?</figure>',
                             self.html, re.S)
        self.assertEqual(len(figures), 2)
        for figure in figures:
            self.assertNotIn("data-ve-semantic-id", figure)
            self.assertNotIn("data-ve-blk", figure)

    def test_stylesheet_is_shipped_without_a_canonical_grid_diagram(self) -> None:
        self.assertIn('data-ve-component="grid-diagram" data-ve-contract-version="2" data-ve-asset="grid-diagram.css"',
                      self.html)
        self.assertEqual(self.html.count('data-ve-asset="grid-diagram.css"'), 1)

    def test_ask_id_with_quotes_and_spaces_still_passes(self) -> None:
        raw = assembly()
        raw["sections"][1]["id"] = '判断 "範囲"'
        html = build(raw)
        self.assertEqual(check(html), [])
        self.assertIn('<svg id="判断 &quot;範囲&quot;-opt-1-svg"', html)

    def test_svg_outside_a_picture_is_rejected(self) -> None:
        forged = self.html.replace('<p class="ask-question"', '<svg id="x"></svg><p class="ask-question"', 1)
        self.assertIn("選択肢の図の外に <svg> があります", check(forged))

    def test_picture_larger_than_three_by_three_is_rejected(self) -> None:
        forged = self.html.replace('data-ve-grid="3x1"', 'data-ve-grid="4x1"', 1)
        self.assertIn("選択肢の図は3×3以内の grid-diagram である必要があります", check(forged))

    def test_picture_svg_keeps_the_viewbox_rule(self) -> None:
        forged = self.html.replace('viewBox="0 0 450 96"', 'viewBox="0 0 450 90"', 1)
        self.assertIn("viewBox は '0 0 450 96' の完全一致である必要があります", check(forged))

    def test_picture_svg_id_follows_the_option(self) -> None:
        forged = self.html.replace('id="sec-ask-opt-1-svg"', 'id="other-svg"', 1)
        self.assertIn("選択肢の図の <svg> id は 'sec-ask-opt-<番号>-svg' の形である必要があります", check(forged))

    def test_picture_in_a_non_decision_ask_is_rejected(self) -> None:
        forged = self.html.replace('data-ve-ask-type="decision"', 'data-ve-ask-type="request"', 1)
        self.assertIn("選択肢の図は decision ask にだけ置けます", check(forged))


if __name__ == "__main__":
    unittest.main()
````

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_grid_diagram_thumbnails.py -q`
Expected: `3 failed, 10 errors`（検証は `未知のフィールド 'figure'` で落ち、ビルドを使う `ThumbnailRenderTest` は setUpClass で ERROR になる）

- [ ] **Step 3: 型と検査を足す**

`skills/visual-explain/scripts/ve_components/model.py` — old:

````python
    benefit: str = ""
    withdrawn: bool = False
````

new:

````python
    benefit: str = ""
    withdrawn: bool = False
    figure: Optional[GridDiagramPayload] = None  # option picture: grid-diagram, 3x3 or smaller
````

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
_ASK_OPTION_KEYS = {"id", "label", "benefit", "tradeoff", "withdrawn"}
````

new:

````python
_ASK_OPTION_KEYS = {"id", "label", "benefit", "tradeoff", "withdrawn", "figure"}
````

`skills/visual-explain/scripts/ve_components/validation.py` — old:

````python
                withdrawn = False
            if accepted_id and _nonblank_str(label) and _nonblank_str(tradeoff) and _nonblank_str(benefit):
                options.append(AskOption(id=oid, label=label, tradeoff=tradeoff,
                                         benefit=benefit, withdrawn=withdrawn))
        if len(options) == len(options_raw) and sum(1 for o in options if not o.withdrawn) < 2:
            col.add(INVALID_COMPONENT_PAYLOAD, "decision の取り下げていない選択肢は2件以上必要です", path)
````

new:

````python
                withdrawn = False
            figure = None
            if "figure" in item:
                figure = _validate_grid_diagram(item["figure"], f"{op}.figure", col, thumbnail=True)
            if accepted_id and _nonblank_str(label) and _nonblank_str(tradeoff) and _nonblank_str(benefit):
                options.append(AskOption(id=oid, label=label, tradeoff=tradeoff,
                                         benefit=benefit, withdrawn=withdrawn, figure=figure))
        if len(options) == len(options_raw) and sum(1 for o in options if not o.withdrawn) < 2:
            col.add(INVALID_COMPONENT_PAYLOAD, "decision の取り下げていない選択肢は2件以上必要です", path)
        pictured = [isinstance(item, dict) and "figure" in item
                    for item in options_raw if not (isinstance(item, dict) and item.get("withdrawn") is True)]
        if any(pictured) and not all(pictured):
            col.add(INVALID_COMPONENT_PAYLOAD,
                    "選択肢の図は、取り下げていない選択肢すべてに付ける必要があります", path)
````

- [ ] **Step 4: 描画と資産を足す**

`skills/visual-explain/scripts/ve_components/renderers/grid_diagram.py` — old:

````python
def render_grid_diagram(section: CanonicalSection, definition) -> RenderResult:
````

new:

````python
def render_option_figure(payload: GridDiagramPayload, *, id_base: str, label: str) -> str:
    """Small picture inside a decision option; no semantic ids (it is not a canonical figure)."""
    relations_id = f"{id_base}-relations"
    svg = render_grid_svg(payload, svg_id=f"{id_base}-svg", label=label,
                          described_by=relations_id, semantic=False)
    return (
        f'<figure data-ve-component="grid-diagram" class="ve-gd ve-gd-thumb" data-ve-thumb'
        f' data-ve-grid="{payload.cols}x{payload.rows}" aria-label="{_esc(label)}">{svg}'
        f'<ul id="{_esc(relations_id)}" class="ve-gd-relations visually-hidden">'
        f'{"".join(relation_items(payload))}</ul></figure>'
    )


def render_grid_diagram(section: CanonicalSection, definition) -> RenderResult:
````

`skills/visual-explain/scripts/ve_components/document_sections.py` — old:

````python
def _render_decision_body(section: AskSection, kind_label: str, marker_attr: str = "") -> str:
    options_html: list[str] = []
    for opt in section.options:
````

new:

````python
def _render_decision_body(section: AskSection, kind_label: str, marker_attr: str = "") -> str:
    from .renderers.grid_diagram import render_option_figure

    options_html: list[str] = []
    for index, opt in enumerate(section.options, start=1):
        figure = ""
        if opt.figure is not None:
            figure = render_option_figure(opt.figure, id_base=f"{section.id}-opt-{index}",
                                          label=f"{opt.label} の図")
````

`skills/visual-explain/scripts/ve_components/document_sections.py` — old:

````python
            f'<span class="ask-tradeoff"><span class="ask-prefix">代償:</span> {_esc(opt.tradeoff)}</span>'
            "</li>"
````

new:

````python
            f'<span class="ask-tradeoff"><span class="ask-prefix">代償:</span> {_esc(opt.tradeoff)}</span>'
            f"{figure}</li>"
````

`skills/visual-explain/scripts/ve_components/assembly.py` — old:

````python
from dataclasses import dataclass
````

new:

````python
from dataclasses import dataclass, replace
````

`skills/visual-explain/scripts/ve_components/assembly.py` — old:

````python
def compose_sections(items) -> CompositionResult:
````

new:

````python
def add_option_figure_assets(composition: CompositionResult, asks, registry: Registry) -> CompositionResult:
    """Option pictures reuse the grid-diagram stylesheet, even with no canonical grid-diagram."""
    if not any(option.figure is not None for ask in asks for option in ask.options):
        return composition
    component = registry.find("grid-diagram", 2)
    asset = component.asset_by_id("grid-diagram.css") if component is not None else None
    if asset is None:
        raise ContractError([Diagnostic(RENDERER_FAILURE, "選択肢の図には grid-diagram の資産が必要です")])
    if any(ref.asset.id == asset.id for ref in composition.style_assets):
        return composition
    return replace(composition, style_assets=composition.style_assets + (AssetRef("grid-diagram", 2, asset),))


def compose_sections(items) -> CompositionResult:
````

`skills/visual-explain/scripts/build_explainer.py` — old:

````python
from ve_components.assembly import (  # noqa: E402
    CompositionResult,
````

new:

````python
from ve_components.assembly import (  # noqa: E402
    CompositionResult,
    add_option_figure_assets,
````

`skills/visual-explain/scripts/build_explainer.py` — old:

````python
    composition = compose_sections(items)
    return replace(composition, sections_markup=stamp_review_sections(composition.sections_markup))
````

new:

````python
    composition = add_option_figure_assets(
        compose_sections(items),
        tuple(s for s in request.sections if isinstance(s, AskSection)), registry)
    return replace(composition, sections_markup=stamp_review_sections(composition.sections_markup))
````

- [ ] **Step 5: checker の ask 内ゲートを足す**（`checker.py`）

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
from .grid_layout import MAX_GRID, viewbox as grid_viewbox
````

new:

````python
from .grid_layout import MAX_GRID, MAX_THUMB_GRID, viewbox as grid_viewbox
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
_GRID_ATTR_RE = re.compile(r'\bdata-ve-grid="([1-9][0-9]*)x([1-9][0-9]*)"')
````

new:

````python
_GRID_ATTR_RE = re.compile(r'\bdata-ve-grid="([1-9][0-9]*)x([1-9][0-9]*)"')
_THUMB_FIGURE_RE = re.compile(r"<figure\b([^>]*\bdata-ve-thumb\b[^>]*)>(.*?)</figure>", re.DOTALL)
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
    component_key: str,
    expected_id: str | None,
) -> list[Diagnostic]:
````

new:

````python
    component_key: str,
    expected_id: str | None,
    expected_viewbox: str | None = None,
) -> list[Diagnostic]:
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
    diagnostics.extend(_validate_svg_subtree(fragment, component_key))
    return diagnostics


def _grid_viewbox_from
````

new:

````python
    diagnostics.extend(_validate_svg_subtree(fragment, component_key, expected_viewbox))
    return diagnostics


def _grid_viewbox_from
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
    return grid_viewbox(cols, rows)


def validate_renderer_svg
````

new:

````python
    return grid_viewbox(cols, rows)


def _validate_ask_thumbnails(attrs: str, body: str) -> list[Diagnostic]:
    """Option pictures: one grid-diagram SVG per thumbnail figure, in decision asks only."""
    if _section_attr(attrs, "data-ve-ask-type") != "decision":
        return [Diagnostic(RENDERER_SVG_VIOLATION, "選択肢の図は decision ask にだけ置けます")]
    diagnostics: list[Diagnostic] = []
    section_id = _section_attr(attrs, "id") or ""
    figures = list(_THUMB_FIGURE_RE.finditer(body))
    inside = sum(len(_SVG_OPEN_RE.findall(match.group(2))) for match in figures)
    if inside != len(_SVG_OPEN_RE.findall(body)):
        diagnostics.append(Diagnostic(RENDERER_SVG_VIOLATION, "選択肢の図の外に <svg> があります"))
    id_re = re.compile(re.escape(section_id) + r"-opt-[1-9][0-9]*-svg")
    for match in figures:
        figure_attrs, figure_body = match.group(1), match.group(2)
        expected = _grid_viewbox_from(figure_attrs, MAX_THUMB_GRID)
        if _section_attr(figure_attrs, "data-ve-component") != "grid-diagram" or expected is None:
            diagnostics.append(Diagnostic(RENDERER_SVG_VIOLATION,
                                          "選択肢の図は3×3以内の grid-diagram である必要があります"))
            continue
        svgs = list(_SVG_OPEN_RE.finditer(figure_body))
        end = figure_body.find("</svg>", svgs[0].end()) if len(svgs) == 1 else -1
        if end == -1:
            diagnostics.append(Diagnostic(RENDERER_SVG_VIOLATION, "選択肢の図には閉じた <svg> がちょうど1つ必要です"))
            continue
        if not id_re.fullmatch(_section_attr(svgs[0].group(1), "id") or ""):
            diagnostics.append(Diagnostic(
                RENDERER_SVG_VIOLATION,
                f"選択肢の図の <svg> id は '{section_id}-opt-<番号>-svg' の形である必要があります"))
        diagnostics.extend(_validate_closed_svg(
            figure_body[svgs[0].start():end + len("</svg>")],
            component_key="grid-diagram@2", expected_id=None, expected_viewbox=expected,
        ))
    return diagnostics


def validate_renderer_svg
````

`skills/visual-explain/scripts/ve_components/checker.py` — old:

````python
        component_key = f"{component}@{version}" if component and version else ""
        allowed = (
````

new:

````python
        component_key = f"{component}@{version}" if component and version else ""
        if kind == "ask" and _SVG_OPEN_RE.search(body):
            diagnostics.extend(_validate_ask_thumbnails(attrs, body))
            continue
        allowed = (
````

- [ ] **Step 6: schema に足す**（`references/assembly.schema.json`）

`skills/visual-explain/references/assembly.schema.json` — old:

````json
        "tradeoff": {"type": "string", "minLength": 1},
        "withdrawn": {"type": "boolean"}
      }
````

new:

````json
        "tradeoff": {"type": "string", "minLength": 1},
        "withdrawn": {"type": "boolean"},
        "figure": {
          "description": "選択肢の小図。grid-diagram と同じ形で、grid は 3×3 以内、markers は書けない（validation が検査する）。",
          "$ref": "component-ir.schema.json#/$defs/gridDiagramPayload"
        }
      }
````

- [ ] **Step 7: テストが通ることを確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_grid_diagram_thumbnails.py -q`
Expected: `13 passed`

- [ ] **Step 8: 全体を確認してコミットする**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest`
Expected: `1439 passed, 166 subtests passed` / `selftest: 38 passed, 0 failed`

```bash
git add skills/visual-explain/scripts/ve_components skills/visual-explain/scripts/build_explainer.py skills/visual-explain/references/assembly.schema.json skills/visual-explain/scripts/tests/test_grid_diagram_thumbnails.py
git commit -m "$(cat <<'EOF'
feat(ve): let decision options carry a small grid picture of each choice

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NgfQq9eGiPhoY46Nmdb2Xv
EOF
)"
```

---

### Task 6: 同梱見本の主図を grid-diagram の全体図に作り直す

**Files:**
- Modify: `skills/visual-explain/examples/example-proposal.assembly.json`, `skills/visual-explain/examples/example-proposal.html`（再ビルド）
- Test: `skills/visual-explain/scripts/tests/test_example_proposal.py`

**Interfaces:**
- Consumes: Task 3〜5 のすべて（全体図の番号、選択肢の小図、metrics の読み上げ一覧除外）。
- Produces: 見本の section 順は `sec-first-screen` → `sec-approval-map`（grid-diagram の全体図）→ `sec-current-problem` → `sec-approval-map-intro` → `sec-before-after-compare` → `sec-ask-hypothesis` → `sec-ask-decision`（2 案とも小図付き）→ `sec-closing`。`sec-alternatives`（matrix）と legacy `.layers` 節は無くなる。

- [ ] **Step 1: 失敗するテストを書く**（`tests/test_example_proposal.py`）

`skills/visual-explain/scripts/tests/test_example_proposal.py` — old:

````python
    def test_checked_in_html_matches_fresh_build(self) -> None:
````

new:

````python
    def test_overview_figure_is_a_grid_diagram_with_the_numbers_on_nodes(self) -> None:
        html = _build()
        self.assertIn('data-ve-component="grid-diagram" data-ve-contract-version="2"'
                      ' data-ve-instance="sec-approval-map"', html)
        self.assertEqual(html.count('<g class="ve-gd-marker">'), 3)
        self.assertNotIn('data-ve-compat-reason="unmigrated-format" data-ve-instance="sec-approval-map"', html)

    def test_every_node_of_the_approval_map_is_connected(self) -> None:
        raw = json.loads((EXAMPLES / "example-proposal.assembly.json").read_text("utf-8"))
        grid = raw["sections"][1]["ir"]["grid-diagram"]
        touched = {e["from"] for e in grid["edges"]} | {e["to"] for e in grid["edges"]}
        self.assertEqual(touched, {n["id"] for n in grid["nodes"]})

    def test_both_decision_options_are_pictured(self) -> None:
        self.assertEqual(_build().count('class="ve-gd ve-gd-thumb"'), 2)

    def test_checked_in_html_matches_fresh_build(self) -> None:
````

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_example_proposal.py -q`
Expected: 新しい 3 件が FAIL（全体図が matrix のまま／`sections[1]` に `grid-diagram` が無い／小図が 0 個）

- [ ] **Step 3: assembly を書き換える**（リポジトリルートで実行。スクリプトはリポジトリに足さない）

```bash
python3 - <<'EOF'
"""Rebuild the example's overview as a grid-diagram (Phase 4 Task 6). Run from the repo root."""
import json
from pathlib import Path

path = Path("skills/visual-explain/examples/example-proposal.assembly.json")
raw = json.loads(path.read_text("utf-8"))
by_id = {s.get("id") or s["ir"]["id"]: s for s in raw["sections"]}
assert set(by_id) == {
    "sec-first-screen", "sec-alternatives", "sec-current-problem", "sec-approval-map-intro",
    "sec-approval-map", "sec-before-after-compare", "sec-ask-hypothesis", "sec-ask-decision", "sec-closing",
}, sorted(by_id)

by_id["sec-first-screen"]["overview"]["section"] = "sec-approval-map"
approval_map = {
    "kind": "canonical",
    "ir": {
        "id": "sec-approval-map",
        "relationship": {"kind": "spatial-layout", "capabilities": ["spatial-placement"]},
        "selection": {"component": "grid-diagram", "version": 2, "matchedCapabilities": ["spatial-placement"]},
        "caption": "見るところ: 根拠と顧客影響は共同承認で合流する。",
        "certainty": [{"id": "cert-approval-map", "level": "inferred",
                       "statement": "説明用の承認経路で、各部門の実際の手順とは照合していません。"}],
        "sources": [{"id": "src-approval-map", "label": "料金改定の承認手順メモ"}],
        "accessibility": {"label": "承認地図",
                          "summary": "左から根拠、顧客影響、共同承認、公開と保護の順に並ぶ。"},
        "grid-diagram": {
            "grid": {"cols": 4, "rows": 3},
            "nodes": [
                {"id": "contract-exception", "label": "契約例外", "cell": [1, 1]},
                {"id": "price-change", "label": "料金改定案", "cell": [1, 2]},
                {"id": "billing-calculation", "label": "請求計算と 対象顧客", "cell": [2, 1]},
                {"id": "notification-audience", "label": "告知対象と文面", "cell": [2, 3]},
                {"id": "joint-approval", "label": "三部門の 共同承認", "cell": [3, 2], "tone": "primary"},
                {"id": "limited-release", "label": "限定対象で公開", "cell": [4, 2], "tone": "primary"},
                {"id": "rollback-condition", "label": "撤回条件", "cell": [4, 3], "tone": "warning"},
            ],
            "regions": [
                {"id": "region-basis", "label": "根拠", "from": [1, 1], "to": [1, 2]},
                {"id": "region-impact", "label": "顧客影響", "from": [2, 1], "to": [2, 3]},
            ],
            "edges": [
                {"id": "e-exception-billing", "from": "contract-exception", "to": "billing-calculation"},
                {"id": "e-price-billing", "from": "price-change", "to": "billing-calculation"},
                {"id": "e-price-notice", "from": "price-change", "to": "notification-audience"},
                {"id": "e-billing-approval", "from": "billing-calculation", "to": "joint-approval"},
                {"id": "e-notice-approval", "from": "notification-audience", "to": "joint-approval"},
                {"id": "e-approval-release", "from": "joint-approval", "to": "limited-release"},
                {"id": "e-rollback-release", "from": "rollback-condition", "to": "limited-release", "label": "見張る"},
            ],
            "markers": [
                {"n": 1, "target": "contract-exception"},
                {"n": 2, "target": "joint-approval"},
                {"n": 3, "target": "limited-release"},
            ],
        },
    },
}
limited, everyone = by_id["sec-ask-decision"]["options"]
assert (limited["id"], everyone["id"]) == ("limited", "all")
limited["figure"] = {
    "grid": {"cols": 3, "rows": 1},
    "nodes": [
        {"id": "limited", "label": "限定対象で公開", "cell": [1, 1], "tone": "primary"},
        {"id": "check", "label": "影響を確認", "cell": [2, 1]},
        {"id": "expand", "label": "全顧客へ拡大", "cell": [3, 1]},
    ],
    "edges": [{"id": "e1", "from": "limited", "to": "check"}, {"id": "e2", "from": "check", "to": "expand"}],
}
everyone["figure"] = {
    "grid": {"cols": 3, "rows": 1},
    "nodes": [
        {"id": "all", "label": "全顧客へ一斉公開", "cell": [1, 1], "span": [2, 1], "tone": "primary"},
        {"id": "risk", "label": "誤りも全体へ", "cell": [3, 1], "tone": "warning"},
    ],
    "edges": [{"id": "e1", "from": "all", "to": "risk"}],
}
order = ["sec-first-screen", "sec-approval-map", "sec-current-problem", "sec-approval-map-intro",
         "sec-before-after-compare", "sec-ask-hypothesis", "sec-ask-decision", "sec-closing"]
by_id["sec-approval-map"] = approval_map
raw["sections"] = [by_id[key] for key in order]
path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", "utf-8")
print("rewrote", path)
EOF
```

Expected: `rewrote skills/visual-explain/examples/example-proposal.assembly.json`（先頭の 2 つの `assert` は、見本が `6e0e534` から変わっていたら止めるためのもの。止まったら報告する）

- [ ] **Step 4: 再ビルドして検査する**

```bash
python3 skills/visual-explain/scripts/build_explainer.py --assembly skills/visual-explain/examples/example-proposal.assembly.json --output skills/visual-explain/examples/example-proposal.html
bash skills/visual-explain/scripts/check.sh "$PWD/skills/visual-explain/examples/example-proposal.html"
```
Expected: `本文 1138 字 / 図より前 0 字 / 図 2 点` / `PASS`

- [ ] **Step 5: テストが通ることを確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_example_proposal.py tests/test_section_markers.py tests/test_document_checks.py -q`
Expected: すべて PASS（`test_example_proposal.py` は 6 件。`test_section_markers.py` が使う `<p class="claim" data-ve-blk="7"` は作り直し後も同じ番号で残る）

- [ ] **Step 6: 第一画面の収まりを目視する**（スクショは作業用ディレクトリへ。リポジトリに足さない）

```bash
SCRATCH=<作業用ディレクトリの絶対パス>; mkdir -p "$SCRATCH"
perl -e 'alarm 40; exec @ARGV' "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-first-run --user-data-dir="$(mktemp -d "$SCRATCH/chrome.XXXX")" --window-size=1280,900 --screenshot="$SCRATCH/example-1280.png" "file://$PWD/skills/visual-explain/examples/example-proposal.html"
ls -l "$SCRATCH/example-1280.png"
```
Expected: 終了コードが 142 でも PNG が今の時刻で書かれている。画像で、題名・結論・承認地図（左に「根拠」「顧客影響」の破線の囲み、中央に紺の「三部門の共同承認」、右に紺の「限定対象で公開」と橙枠の「撤回条件」、①は契約例外・②は共同承認・③は限定対象で公開の右上）・その下の番号一覧 ①②③ が、すべて 900px の内側に見える（試作では番号一覧が約 868px）。

- [ ] **Step 7: 全体を確認してコミットする**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest`
Expected: `1442 passed, 166 subtests passed` / `selftest: 38 passed, 0 failed`

```bash
git add skills/visual-explain/examples/example-proposal.assembly.json skills/visual-explain/examples/example-proposal.html skills/visual-explain/scripts/tests/test_example_proposal.py
git commit -m "$(cat <<'EOF'
feat(ve): redraw the example's approval map as a grid overview figure

Every node is now connected, the overview numbers sit on the nodes they
point to, and both decision options carry a small picture.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NgfQq9eGiPhoY46Nmdb2Xv
EOF
)"
```

---

### Task 7: スキル文書（12 → 13 形式、自由 SVG の記述を grid-diagram へ）

**Files:**
- Modify: `skills/visual-explain/SKILL.md`, `skills/visual-explain/references/patterns.md`, `skills/visual-explain/references/design-system.md`, `CLAUDE.md`
- Test: `skills/visual-explain/scripts/tests/test_component_contract.py`

**Interfaces:**
- Consumes: Task 3 の fixture `component-valid-grid-diagram.json`（patterns.md の組み立て例と同じ内容）。`test_component_contract.py` の `_assembly_blocks` は patterns.md の `"schemaVersion"` を含む ```json ブロックをすべて `validate_assembly` に通す。
- Produces: 文書のみ（コードの挙動は変えない）。

- [ ] **Step 1: 失敗するテストを書く**（`tests/test_component_contract.py`）

`skills/visual-explain/scripts/tests/test_component_contract.py` — old:

````python
    def test_docs_have_canonical_examples_for_all_twelve_components(self) -> None:
````

new:

````python
    def test_docs_have_canonical_examples_for_all_canonical_components(self) -> None:
````

`skills/visual-explain/scripts/tests/test_component_contract.py` — old:

````python
            "bars",
            "kpi",
        ]:
            self.assertIn(f'"component": "{comp}"', text, comp)
````

new:

````python
            "bars",
            "kpi",
            "grid-diagram",
        ]:
            self.assertIn(f'"component": "{comp}"', text, comp)
````

`skills/visual-explain/scripts/tests/test_component_contract.py` — old:

````python
    _TWELVE_COMPONENTS = (
        "matrix",
        "flow",
        "enumeration",
        "chevron",
        "pyramid",
        "stairs",
        "logic-tree",
        "waterfall",
        "slope",
        "evidence-map",
        "bars",
        "kpi",
    )
````

new:

````python
    _CANONICAL_COMPONENTS = (
        "matrix",
        "flow",
        "enumeration",
        "chevron",
        "pyramid",
        "stairs",
        "logic-tree",
        "waterfall",
        "slope",
        "evidence-map",
        "bars",
        "kpi",
        "grid-diagram",
    )
````

`skills/visual-explain/scripts/tests/test_component_contract.py` — old:

````python
        self.assertEqual(seen, set(self._TWELVE_COMPONENTS))
````

new:

````python
        self.assertEqual(seen, set(self._CANONICAL_COMPONENTS))
````

`skills/visual-explain/scripts/tests/test_component_contract.py` — old:

````python
            "### kpi（主要指標・リング型）@2",
        ):
````

new:

````python
            "### kpi（主要指標・リング型）@2",
            "### grid-diagram（格子上の配置）@2",
        ):
````

- [ ] **Step 2: 失敗を確認する**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_component_contract.py -q`
Expected: 3 件 FAIL（`grid-diagram` の組み立て例・`@2` 見出し・canonical 集合が patterns.md に無い）

- [ ] **Step 3: patterns.md を直す**

`skills/visual-explain/references/patterns.md` — old:

````markdown
ライブラリで表せない場合だけ自由なインライン SVG を使う。その直前に SVG を使う理由を HTML コメントで残し、座標直書きではなくデザイン規則に従う。同じ需要が繰り返すなら、新しい図フォーマットへの昇格を検討する。
````

new:

````markdown
これで表せない「配置そのものが意味を持つ図」は、自由なインライン SVG ではなく canonical の `grid-diagram`（後述）で描く。自由な SVG は checker が拒否する。
````

`skills/visual-explain/references/patterns.md` — old:

````markdown
## カノニカルな matrix / flow / enumeration / chevron / pyramid / stairs / logic-tree / waterfall / slope / evidence-map / bars / kpi / mixed の組み立て例
````

new:

````markdown
## カノニカルな matrix / flow / enumeration / chevron / pyramid / stairs / logic-tree / waterfall / slope / evidence-map / bars / kpi / grid-diagram / mixed の組み立て例
````

`skills/visual-explain/references/patterns.md` — old:

````markdown
昇格済みの `matrix`、`flow`、`enumeration`、`chevron`、`pyramid`、`stairs`、`logic-tree`、`waterfall`、`slope`、`evidence-map`、`bars`、`kpi` は canonical IR
````

new:

````markdown
昇格済みの `matrix`、`flow`、`enumeration`、`chevron`、`pyramid`、`stairs`、`logic-tree`、`waterfall`、`slope`、`evidence-map`、`bars`、`kpi`、`grid-diagram` は canonical IR
````

`skills/visual-explain/references/patterns.md` — old:

````markdown
- **主要指標の強調（リング型）** → `kpi`（`headline-metrics` / `metric-highlight`）。**複数系列の時系列比較は slope へ** — 最大5個（1行3個まで）。
````

new:

````markdown
- **主要指標の強調（リング型）** → `kpi`（`headline-metrics` / `metric-highlight`）。**複数系列の時系列比較は slope へ** — 最大5個（1行3個まで）。
- **配置そのものが意味を持つ（近さ＝関係、上下＝優先、囲み＝責任範囲）** → `grid-diagram`（`spatial-layout` / `spatial-placement`）。**順序だけなら chevron / flow、2軸の比較なら matrix** — 12 形式で表せるならそちらを使う。格子は列・行とも 1〜6、ノード 2〜12。
````

`skills/visual-explain/references/patterns.md` — old:

````markdown
再往復で捨てた案は `"withdrawn": true` で残す（取り消し線付きで表示され、選べない）。decision ask は1資料4問まで。
````

new:

````markdown
再往復で捨てた案は `"withdrawn": true` で残す（取り消し線付きで表示され、選べない）。decision ask は1資料4問まで。案ごとに見た目（範囲・順序・配置）が違うなら、取り下げていない選択肢すべてに `figure`（3×3 以内の `grid-diagram`。書き方は「grid-diagram（格子上の配置）@2」）を付ける。
````

`### mixed（matrix ＋ 互換 ＋ flow）` の直前に grid-diagram の節を足す:

`skills/visual-explain/references/patterns.md` — old:

````markdown
### mixed（matrix ＋ 互換 ＋ flow）
````

new:

````markdown
### grid-diagram（格子上の配置）@2

配置そのものが意味を持つとき（近さ＝関係、上下＝優先、囲み＝責任範囲）だけ使う。12 形式で表せるならそちらを使う。`grid` は列・行とも 1〜6。ノードは 2〜12 件で、`cell` は 1 始まりの `[列, 行]`、`span`（`[幅, 高さ]`）は任意、`label` は 14 字以内（1 行に収まらなければ半角か全角の空白 1 つの位置、無ければ中央で 2 行に折る）。`tone` は `base`（既定）/ `primary`（主役）/ `warning`（注意の枠）。`regions` は 0〜4 件の囲み（`label` 8 字以内、囲み同士は重ねない）、`edges` は 0〜16 件で `id` / `from` / `to` と任意の `label`（10 字以内）を持つ。座標・経路・色は書かない（ビルドが決める）。

ビルドは線を直交 1 回折れ（水平→垂直、ふさがっていれば垂直→水平）で引き、次のどれかに当たると**配置を直さずに**診断を返す: 2 つのノードが同じマスを占める / ノードが囲みの境界をまたぐ / 線が端点以外のノードを横切る / ラベルがノードや囲みに収まらない・線のラベルを置く場所がない / 参照先が無い・格子の外を指す。診断を読んでマスを置き直す（ラベル付きの線は、端点のあいだに空きマスを 1 つ置くと通りやすい）。

`markers`（`n` / `target` / 任意の `ask`）は first-screen の全体図（`overview.section`）にした grid-diagram にだけ書き、`overview.markers` と同じ番号をすべて置く。番号はノードの右上に青い丸で描かれ、直後の番号一覧にも並ぶ。`ask` を書くなら、同じ番号の `overview.markers[].target` と同じ id にする。takeaway 注釈（`takeawayTargetIds` / `emphasis`）は使えない（強調は `tone` で宣言する）。

```json
{
  "schemaVersion": 2,
  "document": {
    "id": "grid-diagram-demo",
    "title": "承認の配置図",
    "summary": "根拠と顧客影響が共同承認で合流する位置を格子で示す。",
    "type": "system",
    "profile": "strict"
  },
  "sections": [
    {
      "kind": "first-screen",
      "id": "sec-first",
      "conclusion": "この資料の判断を進めます。"
    },
    {
      "kind": "canonical",
      "ir": {
        "id": "sec-grid",
        "relationship": {
          "kind": "spatial-layout",
          "capabilities": [
            "spatial-placement"
          ]
        },
        "selection": {
          "component": "grid-diagram",
          "version": 2,
          "matchedCapabilities": [
            "spatial-placement"
          ]
        },
        "caption": "何を見るか: 二つの根拠が共同承認で合流する位置",
        "certainty": [
          {
            "id": "cert-grid",
            "level": "inferred",
            "statement": "説明用の配置。"
          }
        ],
        "sources": [
          {
            "id": "src-grid",
            "label": "承認手順メモ"
          }
        ],
        "accessibility": {
          "label": "承認の配置図",
          "summary": "左に根拠、中央に共同承認、右に公開と撤回条件を置く。"
        },
        "grid-diagram": {
          "grid": {
            "cols": 4,
            "rows": 3
          },
          "nodes": [
            {
              "id": "exception",
              "label": "契約例外",
              "cell": [
                1,
                1
              ]
            },
            {
              "id": "price",
              "label": "料金改定案",
              "cell": [
                1,
                3
              ]
            },
            {
              "id": "approval",
              "label": "共同承認",
              "cell": [
                3,
                2
              ],
              "tone": "primary"
            },
            {
              "id": "rollback",
              "label": "撤回条件",
              "cell": [
                4,
                3
              ],
              "tone": "warning"
            }
          ],
          "regions": [
            {
              "id": "legal",
              "label": "根拠",
              "from": [
                1,
                1
              ],
              "to": [
                1,
                3
              ]
            }
          ],
          "edges": [
            {
              "id": "e-exception",
              "from": "exception",
              "to": "approval",
              "label": "照合"
            },
            {
              "id": "e-price",
              "from": "price",
              "to": "approval"
            },
            {
              "id": "e-rollback",
              "from": "approval",
              "to": "rollback",
              "label": "見張る"
            }
          ]
        }
      }
    },
    {
      "kind": "closing",
      "id": "sec-closing",
      "blocks": [
        {
          "heading": "限界・確度",
          "items": [
            "説明用の配置で、実データではない。"
          ]
        }
      ]
    }
  ]
}
```

decision ask の選択肢には、同じ形の小図を `figure` に付けられる（`grid` は 3×3 以内、`markers` は書けない）。見た目が違う案を比べるときに使い、取り下げていない選択肢**すべて**に付ける。

```json
{
  "id": "limited",
  "label": "限定対象で段階公開する",
  "benefit": "誤りの影響を限定対象に閉じたまま照合の効果を確かめられる",
  "tradeoff": "対象選定と承認・顧客対応の運用を追加で用意する必要がある",
  "figure": {
    "grid": {"cols": 3, "rows": 1},
    "nodes": [
      {"id": "limited", "label": "限定対象で公開", "cell": [1, 1], "tone": "primary"},
      {"id": "check", "label": "影響を確認", "cell": [2, 1]},
      {"id": "expand", "label": "全顧客へ拡大", "cell": [3, 1]}
    ],
    "edges": [{"id": "e1", "from": "limited", "to": "check"}, {"id": "e2", "from": "check", "to": "expand"}]
  }
}
```

### mixed（matrix ＋ 互換 ＋ flow）
````

- [ ] **Step 4: SKILL.md を直す**

`skills/visual-explain/SKILL.md` — old:

````markdown
canonical 12 形式（`matrix` / `flow` / `enumeration` / `chevron` / `pyramid` / `stairs` / `logic-tree` / `waterfall` / `slope` / `evidence-map` / `bars` / `kpi`）を既定にする。
````

new:

````markdown
canonical 13 形式（`matrix` / `flow` / `enumeration` / `chevron` / `pyramid` / `stairs` / `logic-tree` / `waterfall` / `slope` / `evidence-map` / `bars` / `kpi` / `grid-diagram`）を既定にする。
````

`skills/visual-explain/SKILL.md` — old:

````markdown
ライブラリで表せない場合だけ、自由なインライン SVG を使える。使う直前に SVG を使う理由を HTML コメントで残し、描画規則に従うこと。弱いモデルはこの例外を使わず固定ライブラリ内で完結させる。同じ需要が繰り返されるなら、図フォーマットへの昇格を検討する。
````

new:

````markdown
配置そのものが意味を持つとき（近さ＝関係、上下＝優先、囲み＝責任範囲）だけ `grid-diagram` を使う。12 形式で表せるならそちらを使う。`grid-diagram` では格子（列×行）と、ノードを置くマス・囲み・線・番号だけを IR に書き、座標・線の経路・色はビルドに任せる。重なり・囲みの境界またぎ・線の横切り・ラベルのはみ出し・参照切れはビルドが診断を返すので、マスを置き直して再ビルドする。自由なインライン SVG は書かない（checker が拒否する）。
````

`skills/visual-explain/SKILL.md` — old:

````markdown
番号一覧が目次を兼ねるので、目次は生成しない。
````

new:

````markdown
番号一覧が目次を兼ねるので、目次は生成しない。全体図を `grid-diagram` にしたときは、その `markers` に overview と同じ番号をすべて書き、各番号を置くノードを `target` で指す（番号はノードの右上に描かれ、番号一覧も併記される）。全体図以外の `grid-diagram` には `markers` を書かない。
````

`skills/visual-explain/SKILL.md` — old:

````markdown
判断の中身は `kind: "ask"`（`askType: "decision"`）が担う。
````

new:

````markdown
判断の中身は `kind: "ask"`（`askType: "decision"`）が担う。案ごとに見た目（範囲・順序・配置）が違うなら、取り下げていない選択肢すべてに `figure`（3×3 以内の `grid-diagram`）を付け、案を絵で比べられるようにする。
````

`skills/visual-explain/SKILL.md` — old:

````markdown
- [ ] 回収パネルが closing の後に1つだけあり、推奨（`defaultId`）が選択済み扱いされていない。問いカードの各選択肢に利点・代償があり、推奨でない選択肢を選ぶ理由が読める。
````

new:

````markdown
- [ ] 回収パネルが closing の後に1つだけあり、推奨（`defaultId`）が選択済み扱いされていない。問いカードの各選択肢に利点・代償があり、推奨でない選択肢を選ぶ理由が読める。
- [ ] `grid-diagram` の図は、線がノードを横切らず、全体図なら番号がノードの右上と番号一覧の両方にある。選択肢の小図を使うなら、取り下げていない選択肢すべてに付いている。
````

`skills/visual-explain/SKILL.md` — old:

````markdown
## カノニカルなコンポーネント（canonical 12 形式）
````

new:

````markdown
## カノニカルなコンポーネント（canonical 13 形式）
````

`skills/visual-explain/SKILL.md` — old:

````markdown
主要指標の強調（リング型）は `kpi` を、次の1つの意思決定列で使う。
````

new:

````markdown
主要指標の強調（リング型）は `kpi`、配置そのものが意味を持つ図（近さ＝関係、上下＝優先、囲み＝責任範囲）は `grid-diagram` を、次の1つの意思決定列で使う。`grid-diagram` は 12 形式で表せないときだけ使う。
````

`skills/visual-explain/SKILL.md` — old:

````markdown
`hierarchical-decomposition`、`additive-bridge` など）
````

new:

````markdown
`hierarchical-decomposition`、`additive-bridge`、`spatial-layout` など）
````

`skills/visual-explain/SKILL.md` — old:

````markdown
matrix/flow/enumeration/chevron/pyramid/stairs/logic-tree/waterfall/slope/evidence-map/bars/kpi の canonical 生成が失敗した場合は、診断を返して**報告**する。
````

new:

````markdown
matrix/flow/enumeration/chevron/pyramid/stairs/logic-tree/waterfall/slope/evidence-map/bars/kpi/grid-diagram の canonical 生成が失敗した場合は、診断を返して**報告**する。
````

- [ ] **Step 5: design-system.md と CLAUDE.md を直す**

`skills/visual-explain/references/design-system.md` — old:

````markdown
## コンポーネント資産の所有権（canonical 12 形式）

昇格済みの `matrix`、`flow`、`enumeration`、`chevron`、`pyramid`、`stairs`、`logic-tree`、`waterfall`、`slope`、`evidence-map`、`bars`、`kpi` は骨格とコンポーネントで所有権を分ける。
````

new:

````markdown
## コンポーネント資産の所有権（canonical 13 形式）

昇格済みの `matrix`、`flow`、`enumeration`、`chevron`、`pyramid`、`stairs`、`logic-tree`、`waterfall`、`slope`、`evidence-map`、`bars`、`kpi`、`grid-diagram` は骨格とコンポーネントで所有権を分ける。
````

`skills/visual-explain/references/design-system.md` — old:

````markdown
kpi は `[data-ve-component="kpi"]` を根に持つ規則だけを書き
````

new:

````markdown
kpi は `[data-ve-component="kpi"]`、grid-diagram は `[data-ve-component="grid-diagram"]` を根に持つ規則だけを書き
````

`skills/visual-explain/references/design-system.md` — old:

````markdown
matrix/flow/enumeration/chevron/pyramid/stairs/logic-tree/waterfall/slope/evidence-map/bars/kpi は script を出さない。
````

new:

````markdown
matrix/flow/enumeration/chevron/pyramid/stairs/logic-tree/waterfall/slope/evidence-map/bars/kpi/grid-diagram は script を出さない。
````

`skills/visual-explain/references/design-system.md` — old:

````markdown
kpi は最大5個（1行3個まで）。超過は分割か縮退。
````

new:

````markdown
kpi は最大5個（1行3個まで）、grid-diagram は格子 6×6・ノード 12・線 16・囲み 4・番号 5（選択肢の小図は 3×3）。超過は分割か縮退。
````

`skills/visual-explain/references/design-system.md` — old:

````markdown
- **renderer-svg ゲート（slope / waterfall）**: SVG は `RENDERER_SVG_ALLOWLIST = {"slope@2", "waterfall@2"}` の canonical セクション内だけ許可。`RenderManifest.svg_root_ids` でルート id を宣言し、`assembly.render_canonical` と `checker.validate_renderer_svg` の二重ゲートで照合する。要素/属性は閉じた許可リストのみ（slope: `viewBox` 完全一致 `0 0 600 220`、waterfall: `0 0 640 360`）。互換節経由の SVG 持込も拒否する。
````

new:

````markdown
- **renderer-svg ゲート（slope / waterfall / grid-diagram）**: SVG は `RENDERER_SVG_ALLOWLIST = {"slope@2", "waterfall@2", "grid-diagram@2"}` の canonical セクション内と、decision ask の選択肢の小図（`figure[data-ve-thumb]`、grid-diagram 3×3 以内）の中だけ許可。`RenderManifest.svg_root_ids` でルート id を宣言し、`assembly.render_canonical` と `checker.validate_renderer_svg` の二重ゲートで照合する。要素/属性は閉じた許可リストのみ（`svg` / `g` / `rect` / `line` / `circle` / `text` / `title` / `desc`。`path` は無い）。viewBox は slope が `0 0 600 220`、waterfall が `0 0 640 360` の完全一致、grid-diagram は figure の `data-ve-grid="列x行"` から `grid_layout.viewbox`（1 マス 150×96）で計算した値の完全一致。互換節経由の SVG 持込も拒否する。
- **grid-diagram の幾何と色**: 幾何は `grid_layout.py` だけが決め、validation・レンダラ・checker が同じ関数を使う（ノードはマスから左右 16・上下 22 内側、線は直交 1 回折れ、矢じりは短い `line` 2 本、番号はノード右上の `circle`＋`text`）。SVG 内の文字は 13px / 11px（viewBox 単位。rem にすると収まり検査と一致しない）。色は `base`＝`--dg-primary-light` に `--text`、`primary`＝`--dg-primary` に `--dg-on-primary`、`warning`＝`--bg` に `--dg-negative` の枠、線と囲みの破線は `--dg-line`、番号は `--accent` の丸に `--bg` の数字。狭い画面では最小幅（列数×7.5rem）を保ち、図の枠の中で横にスクロールする。ノード・線・番号を読み上げ用の一覧（`.visually-hidden`）に重ねて出し、本文字数には数えない。
````

`CLAUDE.md` — old:

````markdown
# 全テスト（1289件前後）— 必ず scripts/ から python3 -m pytest のモジュール形式で実行する。
````

new:

````markdown
# 全テスト（1440件前後）— 必ず scripts/ から python3 -m pytest のモジュール形式で実行する。
````

`CLAUDE.md` — old:

````markdown
- canonical 12 形式: `matrix` / `flow` / `enumeration` / `chevron` / `pyramid` / `stairs` / `logic-tree` / `waterfall` / `slope` / `evidence-map` / `bars` / `kpi`。定義は `assets/components/registry.json`、CSS は `assets/components/*.css`。
````

new:

````markdown
- canonical 13 形式: `matrix` / `flow` / `enumeration` / `chevron` / `pyramid` / `stairs` / `logic-tree` / `waterfall` / `slope` / `evidence-map` / `bars` / `kpi` / `grid-diagram`。定義は `assets/components/registry.json`、CSS は `assets/components/*.css`。
- grid-diagram: 幾何は `grid_layout.py`（validation / renderer / checker が共有）。重なり・囲みの境界またぎ・線の横切り・文字の収まり・参照切れは fail-closed の診断で、自動再配置はしない。`markers` は first-screen の全体図にだけ書け、overview の番号と一致必須。decision の選択肢は `figure`（3×3 以内の小図）を持てる。
````

`CLAUDE.md` — old:

````markdown
- レンダラ発 SVG は二重ゲート（allowlist は `slope@1` のみ・要素/属性完全一致・viewBox 固定・整数座標。`test_renderer_svg_gate.py`）。
````

new:

````markdown
- レンダラ発 SVG は二重ゲート（allowlist は `slope@2` / `waterfall@2` / `grid-diagram@2`・要素/属性完全一致・整数座標。viewBox は slope / waterfall が固定値、grid-diagram は figure の `data-ve-grid` から計算した値。decision の選択肢の小図だけ ask 内の SVG を許す。`test_renderer_svg_gate.py`）。
````

- [ ] **Step 6: 残りの「12 形式」と固有名を確認する**

Run: `grep -rn "canonical 12\|slope@1\|自由なインライン SVG を使\|1289件" CLAUDE.md skills/visual-explain/SKILL.md skills/visual-explain/references/`
Expected: 出力なし

- [ ] **Step 7: 全体を確認してコミットする**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest`
Expected: `1442 passed, 166 subtests passed` / `selftest: 38 passed, 0 failed`

```bash
git add skills/visual-explain/SKILL.md skills/visual-explain/references/patterns.md skills/visual-explain/references/design-system.md CLAUDE.md skills/visual-explain/scripts/tests/test_component_contract.py
git commit -m "$(cat <<'EOF'
docs(ve): describe grid-diagram and retire the free inline SVG escape hatch

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NgfQq9eGiPhoY46Nmdb2Xv
EOF
)"
```

---

### Task 8: 全体の目視確認（1280 / 390 / ダーク）と仕上げ

**Files:**
- 変更なし（直す必要が見つかったときだけ、下の「直し方」に従う）

**Interfaces:**
- Consumes: Task 1〜7 の成果物。
- Produces: 目視の記録（タスク報告に書く。リポジトリには足さない）。

- [ ] **Step 1: 3 種類のスクショを撮る**（すべて作業用ディレクトリ。リポジトリに足さない）

```bash
SCRATCH=<作業用ディレクトリの絶対パス>; DOC="$PWD/skills/visual-explain/examples/example-proposal.html"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
shot() { perl -e 'alarm 40; exec @ARGV' "$CHROME" --headless=new --disable-gpu --no-first-run --user-data-dir="$(mktemp -d "$SCRATCH/chrome.XXXX")" --window-size="$1" --screenshot="$2" "$3" 2>/dev/null; ls -l "$2"; }
shot 1280,3400 "$SCRATCH/full-1280.png" "file://$DOC"
sed 's/<html lang="ja"/<html lang="ja" data-theme="dark"/' "$DOC" > "$SCRATCH/example-dark.html"
shot 1280,900 "$SCRATCH/dark-1280.png" "file://$SCRATCH/example-dark.html"
printf '<!doctype html><html><body style="margin:0;background:#888"><iframe src="file://%s" style="width:390px;height:1600px;border:0;background:#fff"></iframe></body></html>\n' "$DOC" > "$SCRATCH/phone.html"
shot 600,1600 "$SCRATCH/phone-390.png" "file://$SCRATCH/phone.html"
```
Expected: 3 枚とも今の時刻で書かれている（終了コード 142 は無視してよい）。

- [ ] **Step 2: 見る観点**

1. `full-1280.png`: 問いカードの 2 案それぞれの代償の行の下に小図がある（限定案は紺「限定対象で公開」→「影響を確認」→「全顧客へ拡大」、一斉案は 2 マス幅の紺「全顧客へ一斉公開」→ 橙枠「誤りも全体へ」）。案を選ぶと枠が青くなり、小図の上を押しても選べる。
2. `dark-1280.png`: 全体図のノードの文字（淡い面の `--text`、紺の面の `--dg-on-primary`）、破線、線、番号の丸が読める。
3. `phone-390.png`: 全体図は枠の中で横にスクロールする形で、左端の ① が見え、図の直後の番号一覧に ①②③ が文字で並ぶ。本文が横にはみ出していない。

- [ ] **Step 3: 直し方（必要なときだけ）**

- 色・太さ・余白など CSS だけの直しは `grid-diagram.css` を編集し、`shasum -a 256 skills/visual-explain/assets/components/grid-diagram.css` の値で registry の `grid-diagram.css` の `digest` と `tests/test_stage_deck_registry_contract.py` の `EXISTING_ASSETS["grid-diagram"]` を更新し、`tests/grid-diagram-doc.html` を Task 3 Step 10 のコマンドで作り直し（`component-bad-grid-viewbox.html` も同じスクリプトで作り直す）、見本を再ビルドする。新しい色・トークン外の値は足さない。
- 座標や文字サイズを変える直しは `grid_layout.py` の定数と CSS の px を必ず一緒に変え、Task 1・3 のテストの期待座標を計算し直す（片方だけ変えると収まり検査と描画がずれる）。
- どちらも、直したら全テストと selftest を通してから `fix(ve): …` でコミットする。

- [ ] **Step 4: 最終確認**

Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q && bash check.sh --selftest && bash check.sh "$PWD/../examples/example-proposal.html" && git -C ../../.. status --short`
Expected: `1442 passed, 166 subtests passed`（Step 3 で直したならその分を足した件数）/ `selftest: 38 passed, 0 failed` / `PASS` / 作業ツリーに未コミットの変更なし
