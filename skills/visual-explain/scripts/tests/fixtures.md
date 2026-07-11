# Task 8 fixed fixture matrix

These are known facts to reproduce exactly. Do not invent facts. Each output must state certainty next to claims and must pass `../check.sh`.

## A. Proposal approval — ctx self-healing wrapper

Source: `agent-stack` commit `b799a3f` (`fix: ctx ラッパーを自己修復型にし stale/欠落 shim を自動再生成`).

Required facts:
- A missing or stale `ctx` console-script shim can make direct execution fail after a fresh clone, git pull, or a `project.scripts` change.
- When a venv already exists, the fast path runs `uv pip install --python "$venv/bin/python" -e "$proj" --force-reinstall --no-deps --quiet` to regenerate console scripts without dependency churn.
- When no venv exists, it creates one with `uv venv` and performs a full editable install.
- Decision: approve the self-healing wrapper versus retaining a direct shim invocation.

## B. System explanation — agent-stack Nix wiring

Required facts:
- The public dotfiles flake imports the private overlay only when `DOTFILES_PRIVATE_ROOT` points to it.
- `mkOutOfStoreSymlink` links mutable sources edit-in-place rather than copying them through the Nix store.
- `crossRuntimeSkill` declares four runtime links: `.agents`, `.codex`, `.claude`, and `.hermes`.
- Antigravity settings are seed-on-missing through a Home Manager activation step because its runtime rewrites the live settings file.

## C. Research report — visual-explain design findings

Required facts:
- Congruence principle: use movement only when the change itself is the content; otherwise prefer static explanation.
- A premortem works by asking readers to generate causal reasons for a hypothetical failure, rather than merely listing risks.
- `~/.agents/skills` is a de facto skill discovery convention; Claude Code has its own discovery-path exception.

## 検証 fixture マトリクス（spec 対応）

spec の「検証 fixture マトリクス」を満たす4文書。いずれも現行 skeleton から生成し、`../check.sh` を通す。

- `matrix-doc-long-titles.html`: 45〜50字の日本語アクションタイトル見出しを2節に持ち、長い見出しでも折り返し・整列が破綻しないことを固定する（構造層・表層）。
- `matrix-doc-mixed-density.html`: 疎な第一画面（提案1文＋判断1文＋条件2件）と8行×4列の高密度 matrix（選択案に `data-tone="accent"`）を同居させ、密度差の表示を固定する（構造層・表層）。
- `matrix-doc-all-notations.html`: `data-tone="accent|positive|warning"` の option-card、確度3値バッジ、`decision`/`request`/`hypothesis` の ask 3種、takeaway キャプションと出所注釈を1文書に同時収載し、記法層を網羅する。
- `assembly-branching-flow.json`: 6ノード・group 2つ・隣接エッジ4・スキップ（`branching`）1・`takeawayTargetIds`1件・`emphasis`1件の canonical flow。前向き・fan≤3・レール≤3・行予算≤28を満たし、`build_explainer.py` でビルドして `ve-flow-rail`／`ve-flow-group-label`／注釈が出ることを固定する（flow 契約とトポロジー）。

## Design-gate mock

`mock-design-gate.html` はデザインゲート専用（checker 対象外・目視レビュー用）。

## Title fixture contract

Every ordinary fixture has one `TITLE:BEGIN`/`TITLE:END` slot containing one non-empty plain-text `<title>` element. The negative title fixtures isolate empty, markup, unresolved-placeholder, and missing-marker diagnostics.

## Evaluation contract

For every generated document, evaluate: required-fact reproduction, zero unsupported claims or arrows, correct certainty labels, and readability. The first screen alone must answer what the material concerns and what decision is requested.

### Pi/Katsura Qwen guard

For Pi/Katsura Qwen only, required cause→effect wording must be preserved verbatim or quoted. Do not draw arrows or sequences unless their order is an explicit required fact; mark any allowed inference as **推論**. When uncertain, use a matrix, terms, or prose instead of a flow diagram. This is an additive model-specific guard, not a relaxation of the general contract.

## S1 enumeration fixtures（canonical-v2）

S1 スライスで追加した列挙型コンポーネントの検証用フィクスチャ。

| ファイル | 意図 |
|---|---|
| `component-valid-enumeration.json` | list / number モードの有効 IR |
| `component-valid-enumeration-columns.json` | columns / label モードの有効 IR |
| `component-bad-enumeration-gap-description.json` | description 歯抜け → `enumeration_structure_violation` |
| `component-bad-enumeration-label-missing.json` | label モードで label 欠落 |
| `component-bad-enumeration-too-many.json` | 7項目（上限超過） |
| `component-bad-enumeration-empty-block.json` | number モードで title/description 両欠 |
| `component-bad-enumeration-structure.html` | ビルド済み文書で1項目のみ → `artifact_semantic_mismatch` |
| `component-bad-enumeration-missing-semantic-id.html` | ブロック1件の `data-ve-semantic-id` 欠落 → enumeration 構造診断 |
| `enumeration-doc.html` | light/dark 目視用のビルド成果物 |

## S2 chevron fixtures（canonical-v2）

S2 スライスで追加したチェブロン型コンポーネントの検証用フィクスチャ。

| ファイル | 意図 |
|---|---|
| `component-valid-chevron.json` | vertical / number モードの有効 IR（4段） |
| `component-valid-chevron-loop.json` | vertical / label / loop:true の有効 IR |
| `component-valid-chevron-loop-number.json` | vertical / number / loop:true の有効 IR（タイトル endpoint） |
| `component-valid-chevron-horizontal.json` | horizontal / number モードの有効 IR |
| `component-bad-chevron-loop-horizontal.json` | loop+horizontal → `chevron_structure_violation` |
| `component-bad-chevron-loop-capability-mismatch.json` | loop/capability 不整合 |
| `component-bad-chevron-title-in-horizontal.json` | 横型で title 禁止違反 |
| `component-bad-chevron-no-visible-content.json` | 最小可視内容違反 |
| `component-bad-chevron-too-few-horizontal.json` | 横型2段（下限未満） |
| `component-bad-chevron-structure.html` | ビルド済み文書で1段のみ → `artifact_semantic_mismatch` |
| `chevron-doc.html` | light/dark 目視用（vertical+loop） |
| `chevron-horizontal-doc.html` | light/dark 目視用（horizontal） |

## S3 pyramid + stairs fixtures（canonical-v2）

S3 スライスで追加したピラミッド型・階段型コンポーネントの検証用フィクスチャ。

| ファイル | 意図 |
|---|---|
| `component-valid-pyramid.json` | 4層の有効 IR |
| `component-bad-pyramid-too-few.json` | 2層（下限未満） → `pyramid_structure_violation` |
| `component-bad-pyramid-too-many.json` | 5層（上限超過） |
| `component-bad-pyramid-label-long.json` | label 13字 |
| `component-bad-pyramid-structure.html` | ビルド済み文書で2層のみ → `artifact_semantic_mismatch` |
| `component-bad-pyramid-face-order.html` | 先頭/下位の face クラス入替 → `artifact_semantic_mismatch` |
| `component-bad-pyramid-count-mismatch.html` | コンテナ count 不一致 → `artifact_semantic_mismatch` |
| `component-bad-pyramid-index-mismatch.html` | index クラス欠落/重複 → `artifact_semantic_mismatch` |
| `component-bad-pyramid-face-near-match.html` | face クラスの near-match → `artifact_semantic_mismatch` |
| `pyramid-doc.html` | light/dark 目視用のビルド成果物 |
| `component-valid-stairs.json` | 5段・current+note の有効 IR |
| `component-bad-stairs-two-current.json` | current 2件 |
| `component-bad-stairs-current-without-note.json` | current without note → `stairs_structure_violation` |
| `component-bad-stairs-too-many.json` | 6段（上限超過） |
| `component-bad-stairs-structure.html` | accent 2件 → `artifact_semantic_mismatch` |
| `component-bad-stairs-note-on-sibling.html` | accent 段に note なし・兄弟段に note → `artifact_semantic_mismatch` |
| `component-bad-stairs-count-mismatch.html` | コンテナ count 不一致 → `artifact_semantic_mismatch` |
| `component-bad-stairs-index-mismatch.html` | index クラス不一致 → `artifact_semantic_mismatch` |
| `component-bad-stairs-empty-note.html` | 空の ve-stairs-note → `artifact_semantic_mismatch` |
| `component-bad-stairs-accent-near-match.html` | tread クラス near-match → `artifact_semantic_mismatch` |
| `component-bad-stairs-note-near-match.html` | note クラス near-match → `artifact_semantic_mismatch` |
| `stairs-doc.html` | light/dark 目視用のビルド成果物 |

## S4 logic-tree fixtures（canonical-v2）

S4 スライスで追加したロジックツリー型コンポーネントの検証用フィクスチャ。

| ファイル | 意図 |
|---|---|
| `component-valid-logic-tree.json` | root + 3枝（leaf 0〜2 混在）の有効 IR |
| `component-bad-logic-tree-too-few-branches.json` | 1枝（下限未満） → `logic_tree_structure_violation` |
| `component-bad-logic-tree-too-many-branches.json` | 5枝（上限超過） |
| `component-bad-logic-tree-three-leaves.json` | 1枝に葉3件 |
| `component-bad-logic-tree-label-long.json` | root ラベル21字 |
| `component-bad-logic-tree-depth.json` | 葉に `leaves` → `invalid_component_payload` |
| `component-bad-logic-tree-structure.html` | ビルド済み文書で1枝のみ → `artifact_semantic_mismatch` |
| `component-bad-logic-tree-missing-leaf-id.html` | leaf の `data-ve-semantic-id` 欠落 → `artifact_semantic_mismatch` |
| `component-bad-logic-tree-extra-connector.html` | connector 過多 → `artifact_semantic_mismatch` |
| `component-bad-logic-tree-data-connect.html` | connector の `data-connect` → `artifact_semantic_mismatch` |
| `component-bad-logic-tree-connector-near-match.html` | connector クラス near-match → `artifact_semantic_mismatch` |
| `component-bad-logic-tree-spine-near-match.html` | spine クラス near-match → `artifact_semantic_mismatch` |
| `component-bad-logic-tree-root-stem-near-match.html` | root-stem クラス near-match → `artifact_semantic_mismatch` |
| `logic-tree-doc.html` | light/dark 目視用のビルド成果物 |
