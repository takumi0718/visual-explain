# visual-explain ビジュアル基準 v1 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** spec `docs/superpowers/specs/2026-07-11-visual-explain-visual-standard-v1.md` の3層ビジュアル基準（構造/記法/表層）を skeleton・matrix/flow renderer・validation・checker・規範文書へ実装する。

**Architecture:** 純関数の `flow_layout.py`（トポロジー検査＋レール割当）を validation と flow renderer が共有する。skeleton はトークン全面改訂（モノクロ階調＋判断状態3色・4段タイプスケール・8px グリッド・二段階幅・ask ブロック CSS）。注釈は CanonicalIR の追加フィールドとして model→schema→validation→renderer→checker を同期拡張する。すべて fail-closed の bounded diagnostics で失敗する。

**Tech Stack:** Python 3 標準ライブラリ（unittest / html.parser / dataclasses / json / hashlib / re）、POSIX shell、HTML5、CSS（`color-mix()`・CSS Grid。外部依存なし）。

## Global Constraints

- 最終成果物は自己完結 HTML 1ファイル。外部 CSS/JS/CDN/フォント/画像/ネットワークを含まない。
- CSP・固定領域ハッシュ検証・信頼レジストリ（SHA-256）・fail-closed 診断・renderer 信頼境界の DOM 照合は弱めない。受理範囲の縮小（強化）のみ許す。
- 色は判断状態専用: 選択＝青（`--accent`）／推奨＝緑（`--positive`）／警告＝橙（`--warning`）。装飾色ゼロ。確度バッジはモノクロ＋線種差。
- タイプスケール4段固定: 30px/700・20px/700・16px/400・13px/400（rem 実装）。本文行長は日本語約40字。
- スペーシングは 8px グリッド（8/16/24/32/48/64/88px）。監査対象は margin・padding・gap のみ。
- 幅は二段階: narrative 45rem（720px）／evidence 最大 65rem（1040px）。左端整列線を共有。
- コントラスト: 通常文字 4.5:1・大文字（20px/700以上）3:1・意味非文字 3:1。light/dark 全トークン組合せ。
- flow v1 トポロジー: 全エッジ前向き（reading order 基準）・自己ループ/循環禁止・fan-out/fan-in 各3以下・レール3本以下。違反は bounded diagnostic。
- 注釈: `takeawayTargetIds` 原則1〜3件（0件は `takeawayScope: "whole"` 必須）・`emphasis` 最大3件・label 40字以内・型別 ID 制約・重複禁止。
- 各タスクは独立コミット。直近マイルストーン revert で戻せること。commit 前にテスト緑を確認。
- テストは `cd skills/visual-explain/scripts && python3 -m unittest <target> -v` で実行する。

## File Structure

- Create: `skills/visual-explain/scripts/ve_components/flow_layout.py` — 前向き検査・fan 上限・スパン計算・レール割当の純関数
- Create: `skills/visual-explain/scripts/tests/test_flow_layout.py`
- Create: `skills/visual-explain/scripts/tests/test_annotation.py`
- Create: `skills/visual-explain/scripts/tests/test_skeleton_audit.py` — コントラスト＋8px グリッド監査
- Create: `skills/visual-explain/scripts/tests/test_ask_blocks.py`
- Create: `skills/visual-explain/references/sources.md` — 出典台帳
- Modify: `skills/visual-explain/scripts/ve_components/diagnostics.py` — 新診断コード3つ
- Modify: `skills/visual-explain/scripts/ve_components/model.py` — EmphasisAnnotation / CanonicalIR 拡張
- Modify: `skills/visual-explain/scripts/ve_components/validation.py` — トポロジー制約＋注釈検証
- Modify: `skills/visual-explain/scripts/ve_components/renderers/matrix.py` / `flow.py`
- Modify: `skills/visual-explain/scripts/ve_components/checker.py` — ask 検証＋flow DOM 抽出の維持
- Modify: `skills/visual-explain/assets/skeleton.html` / `assets/components/matrix.css` / `flow.css` / `registry.json`
- Modify: `skills/visual-explain/references/component-ir.schema.json` / `design-system.md` / `patterns.md`
- Modify: `skills/visual-explain/scripts/tests/`（既存 fixture の resplice と追加 fixture）
- Modify: `skills/visual-explain/examples/example-proposal.html`

---

### Task 0: ベースライン凍結

**Files:**
- なし（記録のみ）

- [ ] **Step 1: 開始状態を記録**

```bash
cd /Users/yoshidatakumi/workspace/visual-explain
git rev-parse HEAD          # 期待: 9a42810 以降の visual-standard-v1 ブランチ先頭
git status --porcelain      # 期待: 空
shasum -a 256 skills/visual-explain/assets/skeleton.html
```

- [ ] **Step 2: 全テストが緑であることを確認**

```bash
cd skills/visual-explain/scripts && python3 -m unittest discover -s tests -v 2>&1 | tail -3
```
Expected: `Ran 196 tests` / `OK`

```bash
./check.sh ../examples/example-proposal.html
```
Expected: `PASS`

---

### Task 1: flow_layout.py — トポロジー純関数

**Files:**
- Create: `skills/visual-explain/scripts/ve_components/flow_layout.py`
- Test: `skills/visual-explain/scripts/tests/test_flow_layout.py`
- Modify: `skills/visual-explain/scripts/ve_components/diagnostics.py`

**Interfaces:**
- Produces:
  - `order_index(nodes: Sequence[FlowNode], reading_order: Sequence[str]) -> dict[str, int]` — reading_order 優先、なければ宣言順
  - `check_topology(nodes, edges, reading_order) -> list[Diagnostic]` — 前向き・自己ループ・fan 上限を検査
  - `edge_spans(edges, index) -> list[tuple[str, int, int]]` — (edge_id, start_idx, end_idx)（常に start < end）
  - `assign_rails(spans: list[tuple[str, int, int]], max_rails: int = 3) -> tuple[dict[str, int], list[Diagnostic]]` — 隣接エッジ（end == start+1）はレール対象外で `{}` に含めない。スキップエッジへ greedy interval coloring でレーン 0..2 を割当。超過は診断
  - 診断コード `FLOW_TOPOLOGY_VIOLATION = "flow_topology_violation"`、`FLOW_TOPOLOGY_TOO_COMPLEX = "flow_topology_too_complex"`（diagnostics.py に追加）

- [ ] **Step 1: 失敗するテストを書く**

`skills/visual-explain/scripts/tests/test_flow_layout.py`:

```python
import unittest

from ve_components.model import FlowEdge, FlowNode
from ve_components.flow_layout import assign_rails, check_topology, edge_spans, order_index


def _nodes(*ids):
    return [FlowNode(id=i, label=i) for i in ids]


def _edge(eid, s, t):
    return FlowEdge(id=eid, source=s, target=t, relation="directed-transition")


class OrderIndexTest(unittest.TestCase):
    def test_reading_order_wins(self):
        idx = order_index(_nodes("a", "b"), ["b", "a"])
        self.assertEqual(idx, {"b": 0, "a": 1})

    def test_declaration_order_fallback(self):
        idx = order_index(_nodes("a", "b"), [])
        self.assertEqual(idx, {"a": 0, "b": 1})


class TopologyTest(unittest.TestCase):
    def test_forward_edges_pass(self):
        diags = check_topology(_nodes("a", "b", "c"), [_edge("e1", "a", "b"), _edge("e2", "a", "c")], [])
        self.assertEqual(diags, [])

    def test_backward_edge_fails(self):
        diags = check_topology(_nodes("a", "b"), [_edge("e1", "b", "a")], [])
        self.assertEqual([d.code for d in diags], ["flow_topology_violation"])

    def test_self_loop_fails(self):
        diags = check_topology(_nodes("a"), [_edge("e1", "a", "a")], [])
        self.assertEqual([d.code for d in diags], ["flow_topology_violation"])

    def test_fan_out_over_three_fails(self):
        nodes = _nodes("a", "b", "c", "d", "e")
        edges = [_edge(f"e{i}", "a", t) for i, t in enumerate(["b", "c", "d", "e"])]
        diags = check_topology(nodes, edges, [])
        self.assertTrue(any(d.code == "flow_topology_violation" for d in diags))

    def test_fan_in_over_three_fails(self):
        nodes = _nodes("a", "b", "c", "d", "e")
        edges = [_edge(f"e{i}", s, "e") for i, s in enumerate(["a", "b", "c", "d"])]
        diags = check_topology(nodes, edges, [])
        self.assertTrue(any(d.code == "flow_topology_violation" for d in diags))


class RailTest(unittest.TestCase):
    def test_adjacent_edges_are_spine_not_rail(self):
        idx = {"a": 0, "b": 1, "c": 2}
        spans = edge_spans([_edge("e1", "a", "b"), _edge("e2", "b", "c")], idx)
        rails, diags = assign_rails(spans)
        self.assertEqual(rails, {})
        self.assertEqual(diags, [])

    def test_skip_edges_get_disjoint_lanes(self):
        idx = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4}
        spans = edge_spans([_edge("s1", "a", "c"), _edge("s2", "c", "e")], idx)
        rails, diags = assign_rails(spans)
        self.assertEqual(diags, [])
        self.assertEqual(rails["s1"], 0)
        self.assertEqual(rails["s2"], 0)  # 区間が重ならないので同一レーン再利用

    def test_overlapping_skips_use_new_lanes(self):
        idx = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4}
        spans = edge_spans([_edge("s1", "a", "c"), _edge("s2", "a", "d"), _edge("s3", "a", "e")], idx)
        rails, diags = assign_rails(spans)
        self.assertEqual(diags, [])
        self.assertEqual(sorted(rails.values()), [0, 1, 2])

    def test_fourth_concurrent_rail_fails(self):
        idx = {n: i for i, n in enumerate("abcdef")}
        edges = [_edge("s1", "a", "c"), _edge("s2", "a", "d"), _edge("s3", "a", "e"),
                 _edge("s4", "b", "f")]
        rails, diags = assign_rails(edge_spans(edges, idx))
        self.assertEqual([d.code for d in diags], ["flow_topology_too_complex"])


if __name__ == "__main__":
    unittest.main()
```

（注: `s1/s2/s3` は fan-out 3 なので check_topology は通る。`s4` が同時レーン4本目を要求する。）

- [ ] **Step 2: 失敗を確認**

```bash
cd skills/visual-explain/scripts && python3 -m unittest tests.test_flow_layout -v
```
Expected: FAIL（`No module named 've_components.flow_layout'`）

- [ ] **Step 3: diagnostics.py にコードを追加**

`diagnostics.py` の既存コード定義群の末尾に追加:

```python
FLOW_TOPOLOGY_VIOLATION = "flow_topology_violation"
FLOW_TOPOLOGY_TOO_COMPLEX = "flow_topology_too_complex"
```

（既存の bounded コード一覧に登録する集合/検査があれば同時に追記する。`grep -n "INVALID_COMPONENT_PAYLOAD" ve_components/diagnostics.py` で定義形式を確認し、同じ形式に従うこと。）

- [ ] **Step 4: flow_layout.py を実装**

```python
"""Pure v1 topology functions shared by validation and the flow renderer.

The v1 drawable topology: every edge goes forward in reading order, no
self-loops (hence no cycles), fan-out/fan-in <= 3 per node, and skip edges
must fit in at most 3 concurrent right-hand rails. All functions are pure and
deterministic; diagnostics are returned, never printed.
"""
from __future__ import annotations

from typing import Sequence

from .diagnostics import (
    FLOW_TOPOLOGY_TOO_COMPLEX,
    FLOW_TOPOLOGY_VIOLATION,
    Diagnostic,
)

_MAX_FAN = 3
_MAX_RAILS = 3


def order_index(nodes: Sequence, reading_order: Sequence[str]) -> dict[str, int]:
    order = list(reading_order) if reading_order else [n.id for n in nodes]
    return {nid: i for i, nid in enumerate(order)}


def check_topology(nodes: Sequence, edges: Sequence, reading_order: Sequence[str]) -> list[Diagnostic]:
    index = order_index(nodes, reading_order)
    diags: list[Diagnostic] = []
    fan_out: dict[str, int] = {}
    fan_in: dict[str, int] = {}
    for edge in edges:
        src, dst = index.get(edge.source), index.get(edge.target)
        if src is None or dst is None:
            continue  # 未知 ID は既存の整合検査が別コードで報告する
        if dst <= src:
            diags.append(Diagnostic(
                FLOW_TOPOLOGY_VIOLATION,
                f"辺 '{edge.id}' が前向き制約に違反します (reading order 上で {edge.source} → {edge.target})"))
        fan_out[edge.source] = fan_out.get(edge.source, 0) + 1
        fan_in[edge.target] = fan_in.get(edge.target, 0) + 1
    for nid, count in sorted(fan_out.items()):
        if count > _MAX_FAN:
            diags.append(Diagnostic(FLOW_TOPOLOGY_VIOLATION, f"ノード '{nid}' の分岐が上限3を超えます ({count})"))
    for nid, count in sorted(fan_in.items()):
        if count > _MAX_FAN:
            diags.append(Diagnostic(FLOW_TOPOLOGY_VIOLATION, f"ノード '{nid}' の合流が上限3を超えます ({count})"))
    return diags


def edge_spans(edges: Sequence, index: dict[str, int]) -> list[tuple[str, int, int]]:
    spans = []
    for edge in edges:
        src, dst = index.get(edge.source), index.get(edge.target)
        if src is None or dst is None or dst <= src:
            continue
        spans.append((edge.id, src, dst))
    return spans


def assign_rails(spans: list[tuple[str, int, int]], max_rails: int = _MAX_RAILS) -> tuple[dict[str, int], list[Diagnostic]]:
    """Greedy interval coloring over skip edges (span length >= 2)."""
    skip = sorted((s for s in spans if s[2] - s[1] >= 2), key=lambda s: (s[1], s[2], s[0]))
    lanes: list[int] = []  # occupied-until (end index) per lane
    out: dict[str, int] = {}
    diags: list[Diagnostic] = []
    for eid, start, end in skip:
        for lane_no, until in enumerate(lanes):
            if start >= until:
                lanes[lane_no] = end
                out[eid] = lane_no
                break
        else:
            if len(lanes) >= max_rails:
                diags.append(Diagnostic(
                    FLOW_TOPOLOGY_TOO_COMPLEX,
                    f"辺 '{eid}' に割り当てるレールがありません (同時レール上限 {max_rails})"))
                continue
            lanes.append(end)
            out[eid] = len(lanes) - 1
    return out, diags
```

- [ ] **Step 5: テストが緑になることを確認**

```bash
python3 -m unittest tests.test_flow_layout -v
```
Expected: PASS（10 tests）

- [ ] **Step 6: 回帰確認とコミット**

```bash
python3 -m unittest discover -s tests 2>&1 | tail -3   # 期待: 全緑
git add ve_components/flow_layout.py ve_components/diagnostics.py tests/test_flow_layout.py
git commit -m "feat(visual-explain): add v1 flow topology pure functions"
```

---

### Task 2: validation へのトポロジー制約組み込み

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/validation.py`（`_validate_flow` 呼び出し後にトポロジー検査を追加。validation.py:159 の `acyclic` 分岐は残すが、v1 検査が常に循環を含めて拒否する）
- Test: `skills/visual-explain/scripts/tests/test_component_contract.py`（追記）
- Create: `skills/visual-explain/scripts/tests/component-bad-flow-backward.json`

**Interfaces:**
- Consumes: `flow_layout.check_topology` / `edge_spans` / `assign_rails` / `order_index`
- Produces: `validate_assembly` が後退エッジ・fan 超過・レール超過の flow を `flow_topology_violation` / `flow_topology_too_complex` で拒否する

- [ ] **Step 1: 失敗するテストを書く**

`tests/component-bad-flow-backward.json` を `tests/component-valid-flow.json` のコピーとして作成し、`flow.edges` を次に差し替える（node-approve → node-draft の後退エッジ）:

```json
"edges": [
  {"id": "edge-draft-review", "from": "node-draft", "to": "node-review", "relation": "ordered-transition", "label": "提出"},
  {"id": "edge-back", "from": "node-approve", "to": "node-draft", "relation": "directed-transition", "label": "差戻し"}
]
```

`tests/test_component_contract.py` に追記（既存の fixture 読込ヘルパの形式に合わせる。既存テストの `_load` 相当を流用する）:

```python
class FlowTopologyContractTest(unittest.TestCase):
    def test_backward_edge_rejected(self):
        raw = _load_fixture("component-bad-flow-backward.json")
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        self.assertIn("flow_topology_violation", [d.code for d in ctx.exception.diagnostics])

    def test_valid_flow_still_accepted(self):
        raw = _load_fixture("component-valid-flow.json")
        request = validate_assembly(raw)
        self.assertEqual(len(request.sections), 1)
```

- [ ] **Step 2: 失敗を確認**

```bash
python3 -m unittest tests.test_component_contract -v 2>&1 | tail -5
```
Expected: `test_backward_edge_rejected` FAIL（後退エッジが現状は受理される）

- [ ] **Step 3: validation.py に組み込む**

`validation.py` の flow 検証部（`_validate_flow` が FlowPayload を構築して返した直後、validation.py:159 付近の呼び出し側）に追加:

```python
from .flow_layout import assign_rails, check_topology, edge_spans, order_index
```

`_validate_flow` の末尾（`_check_flow_integrity` 呼び出しの後、FlowPayload return の前）に:

```python
    topo = check_topology(nodes, edges, list(reading_order))
    for diag in topo:
        col.add(diag.code, diag.message, path)
    if not topo:
        index = order_index(nodes, list(reading_order))
        _, rail_diags = assign_rails(edge_spans(edges, index))
        for diag in rail_diags:
            col.add(diag.code, diag.message, path)
```

（`col.add` のシグネチャは既存呼び出しに合わせる。トポロジー違反時はレール検査をスキップして診断の重複を避ける。）

- [ ] **Step 4: テスト緑と回帰を確認、コミット**

```bash
python3 -m unittest tests.test_component_contract tests.test_flow_layout -v 2>&1 | tail -3
python3 -m unittest discover -s tests 2>&1 | tail -3
```
Expected: 全緑（既存 valid fixture は直線 flow なので影響なし）

```bash
git add ve_components/validation.py tests/test_component_contract.py tests/component-bad-flow-backward.json
git commit -m "feat(visual-explain): enforce v1 flow topology in validation"
```

---

### Task 3: 注釈 IR（model・schema・validation）

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/model.py`
- Modify: `skills/visual-explain/scripts/ve_components/validation.py`
- Modify: `skills/visual-explain/references/component-ir.schema.json`
- Create: `skills/visual-explain/scripts/tests/test_annotation.py`
- Create: `skills/visual-explain/scripts/tests/component-valid-flow-annotated.json`

**Interfaces:**
- Produces:
  - `EmphasisAnnotation(target_id: str, label: str)`（frozen dataclass、model.py）
  - `CanonicalIR` に追加: `takeaway_target_ids: tuple[str, ...] = ()`、`takeaway_scope: str = "targets"`、`emphasis: tuple[EmphasisAnnotation, ...] = ()`
  - JSON 側フィールド名: `takeawayTargetIds` / `takeawayScope`（`"targets"` か `"whole"`）/ `emphasis: [{"targetId", "label"}]`
  - 検証規則: targets 1〜3件（0件時は `takeawayScope: "whole"` の明示必須）、matrix はセル ID のみ・flow はノード/エッジ ID のみ、重複禁止、label 40字以内、label==caption 禁止、emphasis 最大3件。違反は既存 `INVALID_COMPONENT_PAYLOAD` を使う

- [ ] **Step 1: 失敗するテストを書く**

`tests/component-valid-flow-annotated.json` を `component-valid-flow.json` のコピーとして作成し、IR に追加:

```json
"takeawayTargetIds": ["edge-review-approve"],
"emphasis": [{"targetId": "node-review", "label": "ここで滞留が発生"}]
```

`tests/test_annotation.py`:

```python
import copy
import json
import unittest
from pathlib import Path

from ve_components.diagnostics import ContractError
from ve_components.validation import validate_assembly

FIXTURES = Path(__file__).resolve().parent


def _load(name):
    return json.loads((FIXTURES / name).read_text("utf-8"))


def _ir(raw):
    return raw["sections"][0]["ir"]


class AnnotationValidationTest(unittest.TestCase):
    def setUp(self):
        self.raw = _load("component-valid-flow-annotated.json")

    def _codes(self, raw):
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        return [d.code for d in ctx.exception.diagnostics]

    def test_valid_annotation_accepted(self):
        request = validate_assembly(self.raw)
        ir = request.sections[0].ir
        self.assertEqual(ir.takeaway_target_ids, ("edge-review-approve",))
        self.assertEqual(ir.emphasis[0].target_id, "node-review")

    def test_unknown_target_rejected(self):
        raw = copy.deepcopy(self.raw)
        _ir(raw)["takeawayTargetIds"] = ["no-such-id"]
        self.assertIn("invalid_component_payload", self._codes(raw))

    def test_zero_targets_require_whole_scope(self):
        raw = copy.deepcopy(self.raw)
        _ir(raw)["takeawayTargetIds"] = []
        del _ir(raw)["emphasis"]
        self.assertIn("invalid_component_payload", self._codes(raw))
        raw2 = copy.deepcopy(raw)
        _ir(raw2)["takeawayScope"] = "whole"
        validate_assembly(raw2)  # 明示すれば通る

    def test_over_three_targets_rejected(self):
        raw = copy.deepcopy(self.raw)
        _ir(raw)["takeawayTargetIds"] = ["node-draft", "node-review", "node-approve", "edge-draft-review"]
        self.assertIn("invalid_component_payload", self._codes(raw))

    def test_duplicate_targets_rejected(self):
        raw = copy.deepcopy(self.raw)
        _ir(raw)["takeawayTargetIds"] = ["node-draft", "node-draft"]
        self.assertIn("invalid_component_payload", self._codes(raw))

    def test_emphasis_label_over_40_chars_rejected(self):
        raw = copy.deepcopy(self.raw)
        _ir(raw)["emphasis"] = [{"targetId": "node-review", "label": "あ" * 41}]
        self.assertIn("invalid_component_payload", self._codes(raw))

    def test_emphasis_label_equal_to_caption_rejected(self):
        raw = copy.deepcopy(self.raw)
        _ir(raw)["emphasis"] = [{"targetId": "node-review", "label": _ir(raw)["caption"]}]
        self.assertIn("invalid_component_payload", self._codes(raw))

    def test_matrix_targets_must_be_cells(self):
        raw = _load("component-valid-mixed.json")
        for section in raw["sections"]:
            if section.get("kind") == "canonical" and "matrix" in section["ir"]:
                # 行 ID（セルではない）を指すと拒否される
                row_id = section["ir"]["matrix"]["rows"][0]["id"]
                section["ir"]["takeawayTargetIds"] = [row_id]
                break
        self.assertIn("invalid_component_payload", self._codes(raw))


if __name__ == "__main__":
    unittest.main()
```

（`invalid_component_payload` の実コード文字列は `grep -n 'INVALID_COMPONENT_PAYLOAD' ve_components/diagnostics.py` で確認し、テスト側をそれに合わせる。）

- [ ] **Step 2: 失敗を確認**

```bash
python3 -m unittest tests.test_annotation -v 2>&1 | tail -5
```
Expected: FAIL（未知フィールド `takeawayTargetIds` が unknown-field 検査で拒否される、等）

- [ ] **Step 3: model.py を拡張**

`MatrixPayload` の後に追加し、`CanonicalIR` にフィールドを足す:

```python
@dataclass(frozen=True)
class EmphasisAnnotation:
    target_id: str
    label: str
```

`CanonicalIR` に追加（`flow: Optional[FlowPayload] = None` の後）:

```python
    takeaway_target_ids: tuple[str, ...] = ()
    takeaway_scope: str = "targets"
    emphasis: tuple["EmphasisAnnotation", ...] = ()
```

- [ ] **Step 4: validation.py を拡張**

canonical IR の許可フィールド集合（unknown-field 検査のallowlist）に `takeawayTargetIds` / `takeawayScope` / `emphasis` を追加。matrix/flow ペイロード検証後（対象 ID 集合が確定した位置）に注釈検証を追加:

```python
def _validate_annotations(raw, path, col, caption, payload_kind, cell_ids, node_ids, edge_ids):
    scope = raw.get("takeawayScope", "targets")
    if scope not in ("targets", "whole"):
        col.add(INVALID_COMPONENT_PAYLOAD, f"takeawayScope '{scope}' は targets か whole のみ有効です", path)
    targets = raw.get("takeawayTargetIds", None)
    target_list = targets if isinstance(targets, list) else []
    if targets is not None and not isinstance(targets, list):
        col.add(INVALID_COMPONENT_PAYLOAD, "takeawayTargetIds は配列が必要です", path)
    allowed = cell_ids if payload_kind == "matrix" else (node_ids | edge_ids)
    kind_label = "セル" if payload_kind == "matrix" else "ノード/エッジ"
    if scope == "targets" and len(target_list) == 0:
        col.add(INVALID_COMPONENT_PAYLOAD,
                "takeawayTargetIds が0件です (図全体が対象なら takeawayScope: \"whole\" を明示してください)", path)
    if scope == "whole" and target_list:
        col.add(INVALID_COMPONENT_PAYLOAD, "takeawayScope: whole と takeawayTargetIds は併用できません", path)
    if len(target_list) > 3:
        col.add(INVALID_COMPONENT_PAYLOAD, "takeawayTargetIds は最大3件です", path)
    seen: set[str] = set()
    for tid in target_list:
        if tid in seen:
            col.add(INVALID_COMPONENT_PAYLOAD, f"takeawayTargetIds '{tid}' が重複しています", path)
        seen.add(tid)
        if tid not in allowed:
            col.add(INVALID_COMPONENT_PAYLOAD, f"takeaway 対象 '{tid}' は {kind_label} ID ではありません", path)
    emphasis_raw = raw.get("emphasis", [])
    if not isinstance(emphasis_raw, list) or len(emphasis_raw) > 3:
        col.add(INVALID_COMPONENT_PAYLOAD, "emphasis は最大3件の配列が必要です", path)
        emphasis_raw = []
    result = []
    seen_emphasis: set[str] = set()
    for i, item in enumerate(emphasis_raw):
        if not isinstance(item, dict) or set(item) != {"targetId", "label"}:
            col.add(INVALID_COMPONENT_PAYLOAD, f"emphasis[{i}] は targetId と label のみを持つ必要があります", path)
            continue
        tid, label = item["targetId"], item["label"]
        if tid in seen_emphasis:
            col.add(INVALID_COMPONENT_PAYLOAD, f"emphasis 対象 '{tid}' が重複しています", path)
        seen_emphasis.add(tid)
        if tid not in allowed:
            col.add(INVALID_COMPONENT_PAYLOAD, f"emphasis 対象 '{tid}' は {kind_label} ID ではありません", path)
        if not isinstance(label, str) or not label.strip() or len(label) > 40:
            col.add(INVALID_COMPONENT_PAYLOAD, f"emphasis[{i}].label は1〜40字が必要です", path)
        elif label == caption:
            col.add(INVALID_COMPONENT_PAYLOAD, "emphasis.label と caption の同文重複は禁止です", path)
        else:
            result.append(EmphasisAnnotation(target_id=str(tid), label=label))
    return tuple(str(t) for t in target_list), scope, tuple(result)
```

呼び出し側（CanonicalIR 構築部）で戻り値を `CanonicalIR(..., takeaway_target_ids=..., takeaway_scope=..., emphasis=...)` に渡す。ID 集合は既に構築済みの rows/columns/cells/nodes/edges から作る。

- [ ] **Step 5: component-ir.schema.json に追記**

canonical envelope の `properties` に追加し、`additionalProperties: false` を維持:

```json
"takeawayTargetIds": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
"takeawayScope": {"enum": ["targets", "whole"]},
"emphasis": {
  "type": "array", "maxItems": 3,
  "items": {"type": "object", "additionalProperties": false,
            "required": ["targetId", "label"],
            "properties": {"targetId": {"type": "string"},
                            "label": {"type": "string", "minLength": 1, "maxLength": 40}}}
}
```

（schema と vocabulary と validation の一致テストが既存にあるため、`python3 -m unittest tests.test_component_contract` で drift を検出する。）

- [ ] **Step 6: テスト緑・回帰・コミット**

```bash
python3 -m unittest tests.test_annotation -v 2>&1 | tail -3
python3 -m unittest discover -s tests 2>&1 | tail -3
git add ve_components/model.py ve_components/validation.py ../references/component-ir.schema.json tests/test_annotation.py tests/component-valid-flow-annotated.json
git commit -m "feat(visual-explain): add minimal annotation IR for matrix/flow"
```

---

### Task 4: skeleton 全面改訂（トークン・タイプスケール・8px・二段階幅・ask CSS）＋監査テスト＋fixture resplice

**Files:**
- Modify: `skills/visual-explain/assets/skeleton.html`（`<style>` ブロックのみ。CSP・マーカー・FIXED JS は1バイトも変更しない）
- Create: `skills/visual-explain/scripts/tests/test_skeleton_audit.py`
- Modify: `skills/visual-explain/scripts/tests/*.html`（全 HTML fixture の固定領域 resplice）
- Modify: `skills/visual-explain/examples/example-proposal.html`（固定領域 resplice のみ。内容改訂は Task 9）

**Interfaces:**
- Produces: 新トークン語彙（design-system.md 改訂の前提）:
  - 階調: `--bg` `--surface` `--border` `--border-strong` `--text` `--text-dim` `--text-faint`
  - 判断状態: `--accent`（選択=青）`--accent-strong` `--positive`（推奨=緑）`--positive-strong` `--warning`（警告=橙）`--warning-strong`。`--accent-warm` は `--warning` の別名として残す（後方互換）
  - タイプ: `--fs-hero: 1.875rem` `--fs-h2: 1.25rem` `--fs-body: 1rem` `--fs-small: .8125rem`、`--lh-body: 1.75` `--lh-heading: 1.45`
  - 余白: `--space-1: .5rem` 〜 `--space-7: 5.5rem`（8/16/24/32/48/64/88px）
  - 幅: `--w-narrative: 45rem` `--w-evidence: 65rem`
  - ask ブロッククラス: `.ask[data-ask="decision|request|hypothesis"]` `.ask-kind` `.ask-question` `.ask-options` `[data-ask-option]` `[data-ask-default]` `.ask-tradeoff` `.ask-no-default-reason` `.ask-steps` `[data-ask-role]` `.ask-claim` `.ask-verify`
  - 確度バッジ: `.certainty` はモノクロ（`color: var(--text-dim)`）＋線種差 — confirmed=実線・inferred=破線・unverified=点線

- [ ] **Step 1: 監査テストを書く（旧 skeleton で FAIL することを確認する）**

`tests/test_skeleton_audit.py`:

```python
import re
import unittest
from pathlib import Path

SKELETON = (Path(__file__).resolve().parents[2] / "assets" / "skeleton.html").read_text("utf-8")
COMPONENT_CSS = [
    (Path(__file__).resolve().parents[2] / "assets" / "components" / name).read_text("utf-8")
    for name in ("matrix.css", "flow.css")
]

_HEX = re.compile(r"^#([0-9a-fA-F]{6})$")


def _luminance(hex_color):
    def channel(v):
        v = v / 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    m = _HEX.match(hex_color)
    r, g, b = (int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def tokens_of(block_text):
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", block_text))


def _blocks():
    light = SKELETON.split(":root {", 1)[1].split("}", 1)[0]
    dark = SKELETON.split(':root[data-theme="dark"]', 1)[1].split("}", 1)[0]
    return {"light": tokens_of(light), "dark": tokens_of(dark)}


# (前景トークン, 背景トークン, 最低比, 用途)
PAIRS = [
    ("text", "bg", 4.5, "本文/ページ背景"),
    ("text", "surface", 4.5, "本文/面"),
    ("text-dim", "bg", 4.5, "補助本文/ページ背景"),
    ("text-dim", "surface", 4.5, "補助本文/面"),
    ("accent", "bg", 4.5, "選択/背景"),
    ("accent-strong", "surface", 4.5, "選択強/面"),
    ("positive", "bg", 4.5, "推奨/背景"),
    ("warning", "bg", 4.5, "警告/背景"),
    ("border-strong", "bg", 3.0, "表見出し罫線(非文字)"),
]


class ContrastAuditTest(unittest.TestCase):
    def test_all_token_pairs_meet_wcag(self):
        for theme, tokens in _blocks().items():
            for fg, bg, minimum, purpose in PAIRS:
                with self.subTest(theme=theme, pair=f"{fg}/{bg}"):
                    self.assertIn(fg, tokens, f"{theme} に --{fg} がありません")
                    self.assertIn(bg, tokens, f"{theme} に --{bg} がありません")
                    ratio = contrast(tokens[fg], tokens[bg])
                    self.assertGreaterEqual(ratio, minimum, f"{theme} {purpose}: {ratio:.2f} < {minimum}")


_SPACING_PROP = re.compile(
    r"(?:^|[;{])\s*(margin|padding|gap|margin-[a-z]+|padding-[a-z]+|margin-block|margin-inline|padding-inline|padding-block|row-gap|column-gap)\s*:\s*([^;}]+)", re.M)
_ALLOWED_VALUE = re.compile(
    r"^(0|var\(--space-[1-7]\)|auto|inherit)$")


class SpacingGridAuditTest(unittest.TestCase):
    def _audit(self, css, label):
        violations = []
        for prop, value in _SPACING_PROP.findall(css):
            parts = value.strip().split()
            for part in parts:
                if not _ALLOWED_VALUE.match(part.strip()):
                    violations.append(f"{label}: {prop}: {value.strip()}")
                    break
        return violations

    def test_skeleton_spacing_on_grid(self):
        style = SKELETON.split("<style>", 1)[1].split("</style>", 1)[0]
        self.assertEqual(self._audit(style, "skeleton"), [])

    def test_component_css_spacing_on_grid(self):
        violations = []
        for css, label in zip(COMPONENT_CSS, ("matrix.css", "flow.css")):
            violations.extend(self._audit(css, label))
        self.assertEqual(violations, [])


class TypeScaleTest(unittest.TestCase):
    def test_four_step_scale_tokens_exist(self):
        for token in ("--fs-hero: 1.875rem", "--fs-h2: 1.25rem", "--fs-body: 1rem", "--fs-small: .8125rem"):
            self.assertIn(token, SKELETON)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 旧 skeleton で FAIL することを確認**

```bash
python3 -m unittest tests.test_skeleton_audit -v 2>&1 | tail -5
```
Expected: FAIL（`--border-strong` 不在、spacing がグリッド外、タイプトークン不在）

- [ ] **Step 3: skeleton.html の `<style>` を新基準へ全面改訂**

固定領域のうち `<style>...</style>` の内側だけを置き換える。トークンブロック（light / dark 両方）:

```css
:root {
  color-scheme: light;
  --bg: #ffffff;
  --surface: #f4f5f7;
  --border: #e2e5e9;
  --border-strong: #1a1d21;
  --text: #1a1d21;
  --text-dim: #555e6a;
  --text-faint: #79828e;
  --accent: #2456b3;
  --accent-strong: #1a4290;
  --positive: #1e6b46;
  --positive-strong: #14532f;
  --warning: #9a4e0e;
  --warning-strong: #7c3d08;
  --accent-warm: #9a4e0e;
  --focus: #005fcc;
  --fs-hero: 1.875rem; --fs-h2: 1.25rem; --fs-body: 1rem; --fs-small: .8125rem;
  --lh-body: 1.75; --lh-heading: 1.45;
  --space-1: .5rem; --space-2: 1rem; --space-3: 1.5rem; --space-4: 2rem;
  --space-5: 3rem; --space-6: 4rem; --space-7: 5.5rem;
  --w-narrative: 45rem; --w-evidence: 65rem;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Hiragino Sans", "Noto Sans JP", sans-serif;
}
```

dark ブロック（`@media (prefers-color-scheme: dark)` の `:root:not([data-theme])` と `:root[data-theme="dark"]` の両方に同値を書く。既存構造を踏襲）:

```css
  --bg: #15181c;
  --surface: #1e2226;
  --border: #33383f;
  --border-strong: #e9ebee;
  --text: #e9ebee;
  --text-dim: #aab1bb;
  --text-faint: #838b96;
  --accent: #85aef2;
  --accent-strong: #a8c4f6;
  --positive: #6cc496;
  --positive-strong: #92d6b2;
  --warning: #e0a05e;
  --warning-strong: #eab884;
  --accent-warm: #e0a05e;
  --focus: #8cc8ff;
```

主要レイアウト規則（既存セレクタは全て残し、値だけ新基準へ。抜粋 — 完全な置換は以下の規則で機械的に行う):

```css
main { width: min(100% - var(--space-4), var(--w-evidence)); margin: 0 auto; padding: var(--space-4) 0 var(--space-6); }
section { min-width: 0; margin-block: var(--space-7); }
p, ul, ol, .claim, .evidence { max-width: var(--w-narrative); }
body { margin: 0; font-size: var(--fs-body); line-height: var(--lh-body); overflow-wrap: anywhere; }
h1 { font-size: var(--fs-hero); font-weight: 700; line-height: var(--lh-heading); max-width: var(--w-narrative); }
h2 { font-size: var(--fs-h2); font-weight: 700; line-height: var(--lh-heading); max-width: var(--w-narrative); }
.first-screen { display: grid; gap: var(--space-4); padding: var(--space-6) 0; background: transparent; border-left: 0; min-height: 60vh; align-content: center; }
.figure { position: relative; min-width: 0; margin: var(--space-3) 0; padding: var(--space-3); background: var(--surface); border: 0; border-radius: .5rem; overflow: auto; }
.matrix-label, .matrix-cell { padding: var(--space-1) var(--space-2) var(--space-1) 0; border: 0; border-bottom: 1px solid var(--border); background: transparent; }
.matrix thead .matrix-label { border-bottom: 1px solid var(--border-strong); }
.certainty { display: inline-flex; align-items: center; margin-inline: var(--space-1); padding: 0 var(--space-1); border: 1px solid var(--text-dim); border-radius: 999px; color: var(--text-dim); font-size: .82em; font-weight: 700; white-space: nowrap; }
.certainty.confirmed { border-style: solid; }
.certainty.inferred { border-style: dashed; }
.certainty.unverified { border-style: dotted; }
```

置換の機械的規則:
1. すべての `margin`/`padding`/`gap` 値を最も近い `var(--space-N)` か `0` に置換（`.25rem` 等の微小値は `0` か `var(--space-1)` に寄せる。境界線の視覚調整に本当に必要な場合は border/inset 等 spacing 以外のプロパティで表現する）。
2. `font-size` は4トークン（または既存の `em` 相対値）のみ。`1.1rem` → `var(--fs-h2)` か `var(--fs-body)` に寄せる。
3. カード類（`.option-card` `.kpi-card` `.term` `.compare-frame` `details.deep-dive` `.stepper`）は `border: 0; background: var(--surface);` へ（枠線を面で代替）。
4. `.closing-section` の `border-top` は `var(--warning)`、`.first-screen` の accent 縦帯は削除（余白で区切る）。
5. `[data-tone]` 系・`.flow`/`.flow-node`・`.timeline`・`.bars`・`.lane` の構造は維持し、色参照だけ新トークンへ。

ask ブロック CSS を `<style>` 末尾（`footer` 規則の前）に追加:

```css
.ask { max-width: var(--w-narrative); margin: var(--space-3) 0; padding: var(--space-3); background: var(--surface); border-radius: .5rem; }
.ask-kind { display: inline-block; margin: 0 0 var(--space-1); padding: 0 var(--space-1); border-radius: .25rem; font-size: var(--fs-small); font-weight: 700; letter-spacing: .08em; }
.ask[data-ask="decision"] .ask-kind { color: var(--accent-strong); background: color-mix(in srgb, var(--accent) 12%, var(--surface)); }
.ask[data-ask="request"] .ask-kind { color: var(--warning-strong); background: color-mix(in srgb, var(--warning) 12%, var(--surface)); }
.ask[data-ask="hypothesis"] .ask-kind { color: var(--text-dim); background: var(--bg); }
.ask-question, .ask-claim { margin: 0 0 var(--space-2); font-weight: 700; }
.ask-options { display: grid; gap: var(--space-1); margin: 0; padding: 0; list-style: none; }
.ask-options [data-ask-option] { display: grid; grid-template-columns: minmax(8rem, .35fr) 1fr; gap: var(--space-2); padding: var(--space-1); border-radius: .3rem; }
.ask-options [data-ask-default] { background: color-mix(in srgb, var(--positive) 12%, var(--surface)); }
.ask-options [data-ask-default] > :first-child::after { content: "既定案"; margin-left: var(--space-1); color: var(--positive); font-size: var(--fs-small); font-weight: 700; }
.ask-tradeoff, .ask-no-default-reason { color: var(--text-dim); }
.ask-steps { display: grid; gap: var(--space-1); margin: 0; padding-left: var(--space-3); }
.ask-steps [data-ask-role]::before { content: attr(data-ask-role-label); margin-right: var(--space-1); font-size: var(--fs-small); font-weight: 700; letter-spacing: .04em; }
.ask-verify { margin: var(--space-2) 0 0; color: var(--text-dim); font-size: var(--fs-small); }
```

- [ ] **Step 4: 監査テストが緑になることを確認**

```bash
python3 -m unittest tests.test_skeleton_audit -v 2>&1 | tail -3
```
Expected: PASS。コントラスト不足のトークンがあれば該当色の明度だけを調整して再実行（色相は変えない）。

- [ ] **Step 5: 全 HTML fixture と example を新 skeleton へ resplice**

固定領域ハッシュ検査は skeleton とバイト一致を要求するため、追跡中の全 HTML fixture を機械的に再接合する。`skills/visual-explain/scripts/tests/tools/resplice.py` を作成:

```python
#!/usr/bin/env python3
"""Re-splice tracked HTML fixtures onto the current skeleton.

Extracts each fixture's TITLE, CONTENT, and controlled-slot bodies, then
re-inserts them between the same markers of the new skeleton. Fixtures whose
markers are intentionally broken (bad-closing 等、マーカー自体を検査する fixture)
are listed in KEEP_AS_IS and skipped.
"""
import sys
from pathlib import Path

MARKERS = [
    ("<!-- TITLE:BEGIN -->", "<!-- TITLE:END -->"),
    ("<!-- VE-CONTROLLED:COMPONENT-STYLES:BEGIN -->", "<!-- VE-CONTROLLED:COMPONENT-STYLES:END -->"),
    ("<!-- VE-CONTROLLED:CONTENT:BEGIN -->", "<!-- VE-CONTROLLED:CONTENT:END -->"),
    ("<!-- VE-CONTROLLED:COMPONENT-SCRIPTS:BEGIN -->", "<!-- VE-CONTROLLED:COMPONENT-SCRIPTS:END -->"),
    ("<!-- CONTENT:BEGIN -->", "<!-- CONTENT:END -->"),
]
KEEP_AS_IS = {"bad-closing.html", "bad-system-closing.html", "bad-fixed-region.html", "bad-nesting.html"}


def between(text, begin, end):
    if begin not in text or end not in text:
        return None
    return text.split(begin, 1)[1].split(end, 1)[0]


def splice(skeleton, fixture):
    out = skeleton
    for begin, end in MARKERS:
        body = between(fixture, begin, end)
        if body is None:
            continue
        head, rest = out.split(begin, 1)
        _, tail = rest.split(end, 1)
        out = head + begin + body + end + tail
    return out


def main():
    root = Path(__file__).resolve().parents[3]
    skeleton = (root / "assets" / "skeleton.html").read_text("utf-8")
    targets = sys.argv[1:] or [str(p) for p in (root / "scripts" / "tests").glob("*.html")]
    for path in targets:
        p = Path(path)
        if p.name in KEEP_AS_IS:
            print(f"skip {p.name}")
            continue
        p.write_text(splice(skeleton, p.read_text("utf-8")), "utf-8")
        print(f"resplice {p.name}")


if __name__ == "__main__":
    main()
```

実行:

```bash
python3 tests/tools/resplice.py
python3 tests/tools/resplice.py ../examples/example-proposal.html
```

- [ ] **Step 6: 全テストを実行し、破綻した fixture を手当てする**

```bash
python3 -m unittest discover -s tests 2>&1 | tail -15
./check.sh ../examples/example-proposal.html
```

想定される失敗と対処:
- **KEEP_AS_IS の fixture**: マーカー破壊やハッシュ不一致を意図する fixture は、旧 skeleton 断片を含むと fixed-region 検査の「期待する失敗」がズレる。各 fixture の意図（`tests/fixtures.md` 参照）を確認し、新 skeleton ベースで同じ違反を再現するよう更新する。
- **skeleton digest を記録しているテスト**: `grep -rn "$(shasum -a 256 <旧digest>)" tests/` 相当で digest 定数を検索し（`grep -rn 'sha256\|digest' tests/*.py | grep -v component`）、新値へ更新する。
- 全緑になるまで fixture を修正する。checker 本体のルールは変更しない。

- [ ] **Step 7: コミット**

```bash
git add ../assets/skeleton.html tests/ ../examples/example-proposal.html
git commit -m "feat(visual-explain): redesign skeleton to visual standard v1 tokens"
```

---

### Task 5: matrix renderer の注釈描画＋matrix.css 再スタイル

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/renderers/matrix.py`
- Modify: `skills/visual-explain/assets/components/matrix.css`
- Modify: `skills/visual-explain/assets/components/registry.json`（matrix.css digest）
- Test: `skills/visual-explain/scripts/tests/test_mixed_assembly.py`（追記）

**Interfaces:**
- Consumes: `CanonicalIR.takeaway_target_ids` / `.takeaway_scope` / `.emphasis`（Task 3）
- Produces: takeaway 対象セルに `class="ve-takeaway-target"`、emphasis は対象セル内に `<span class="ve-emphasis">ラベル</span>`、summary 末尾に注釈文を追記した markup

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_mixed_assembly.py` に追記（既存の build ヘルパを流用。matrix 注釈付き IR は `component-valid-mixed.json` の matrix セクションへ `takeawayTargetIds: ["<実在セルID>"]` と `emphasis` を加えた deepcopy で作る）:

```python
class MatrixAnnotationRenderTest(unittest.TestCase):
    def _build_with_annotation(self):
        raw = _load("component-valid-mixed.json")
        for section in raw["sections"]:
            if section.get("kind") == "canonical" and "matrix" in section["ir"]:
                cell_id = section["ir"]["matrix"]["cells"][0]["id"]
                section["ir"]["takeawayTargetIds"] = [cell_id]
                section["ir"]["emphasis"] = [{"targetId": cell_id, "label": "判断の分岐点"}]
                return _build(raw), cell_id
        raise AssertionError("matrix section not found")

    def test_takeaway_target_marked(self):
        html_doc, cell_id = self._build_with_annotation()
        self.assertIn(f'data-ve-semantic-id="{cell_id}" data-ve-takeaway="true"', html_doc.replace("' ", '" '))
        self.assertIn("ve-takeaway-target", html_doc)

    def test_emphasis_label_rendered_and_in_summary(self):
        html_doc, _ = self._build_with_annotation()
        self.assertIn('<span class="ve-emphasis">判断の分岐点</span>', html_doc)
        self.assertIn("注釈: 判断の分岐点", html_doc)
```

- [ ] **Step 2: 失敗を確認**

```bash
python3 -m unittest tests.test_mixed_assembly -v 2>&1 | tail -5
```
Expected: 新テスト2件 FAIL

- [ ] **Step 3: matrix.py を実装**

`render_matrix` 冒頭に:

```python
    takeaway = set(ir.takeaway_target_ids)
    emphasis_by_id = {e.target_id: e.label for e in ir.emphasis}
```

セル出力部（`cells.append(...)` の td 生成）を変更:

```python
            classes = ' class="ve-takeaway-target"' if cell.id in takeaway else ""
            takeaway_attr = ' data-ve-takeaway="true"' if cell.id in takeaway else ""
            emphasis_html = (f'<span class="ve-emphasis">{_esc(emphasis_by_id[cell.id])}</span>'
                             if cell.id in emphasis_by_id else "")
            cells.append(
                f'<td{classes} data-ve-semantic-id="{_esc(cell.id)}" data-ve-row-id="{_esc(row.id)}"'
                f' data-ve-column-id="{_esc(col.id)}"{takeaway_attr}>{_esc(cell.content)}{emphasis_html}{refs_html}</td>'
            )
```

summary 出力を変更（注釈の a11y 反映）:

```python
    annotation_note = ""
    if emphasis_by_id:
        joined = "、".join(f"注釈: {_esc(label)}" for label in emphasis_by_id.values())
        annotation_note = f" {joined}"
    # figcaption/summary の行:
    f'<p id="{_esc(summary_id)}" class="ve-matrix-summary">{_esc(ir.accessibility.summary)}{annotation_note}</p>'
```

- [ ] **Step 4: matrix.css を新基準へ全面書換**

```css
[data-ve-component="matrix"] { display: block; min-width: 0; margin: var(--space-3) 0; }
[data-ve-component="matrix"] .ve-matrix-caption { margin: 0 0 var(--space-1); font-weight: 700; font-size: var(--fs-h2); max-width: var(--w-narrative); }
[data-ve-component="matrix"] .ve-matrix-summary { margin: 0 0 var(--space-2); color: var(--text-dim); max-width: var(--w-narrative); }
[data-ve-component="matrix"] .ve-matrix-scroll { max-width: 100%; overflow-x: auto; }
[data-ve-component="matrix"] table { width: 100%; min-width: 32rem; border-collapse: collapse; }
[data-ve-component="matrix"] th,
[data-ve-component="matrix"] td { padding: var(--space-1) var(--space-2) var(--space-1) 0; text-align: left; vertical-align: top; border: 0; border-bottom: 1px solid var(--border); background: transparent; }
[data-ve-component="matrix"] thead th { border-bottom: 1px solid var(--border-strong); font-weight: 700; font-size: var(--fs-small); }
[data-ve-component="matrix"] tbody th { font-weight: 700; }
[data-ve-component="matrix"] .ve-matrix-corner { border: 0; }
[data-ve-component="matrix"] .ve-takeaway-target { font-weight: 700; background: color-mix(in srgb, var(--text) 6%, transparent); }
[data-ve-component="matrix"] .ve-emphasis { display: block; margin-top: var(--space-1); color: var(--text-dim); font-size: .85em; font-weight: 700; }
[data-ve-component="matrix"] .ve-matrix-refs { display: block; margin-top: var(--space-1); }
[data-ve-component="matrix"] .ve-cert { display: inline-block; margin-right: var(--space-1); font-size: .8em; font-weight: 700; color: var(--text-dim); border-bottom: 1px solid var(--text-dim); }
[data-ve-component="matrix"] .ve-cert-inferred { border-bottom-style: dashed; }
[data-ve-component="matrix"] .ve-cert-unverified { border-bottom-style: dotted; }
[data-ve-component="matrix"] .ve-src { display: inline-block; font-size: .8em; color: var(--text-faint); }
[data-ve-component="matrix"] .ve-matrix-notes { margin: var(--space-2) 0 0; padding-left: var(--space-3); color: var(--text-dim); font-size: var(--fs-small); }
[data-ve-component="matrix"] .ve-matrix-notes li { margin: 0 0 var(--space-1); }
```

- [ ] **Step 5: registry.json の digest を更新**

```bash
shasum -a 256 ../assets/components/matrix.css
```
出力値を `registry.json` の matrix アセット `digest` に貼り付ける。

- [ ] **Step 6: テスト緑・回帰・コミット**

```bash
python3 -m unittest tests.test_mixed_assembly tests.test_skeleton_audit -v 2>&1 | tail -3
python3 -m unittest discover -s tests 2>&1 | tail -3
git add ve_components/renderers/matrix.py ../assets/components/matrix.css ../assets/components/registry.json tests/test_mixed_assembly.py
git commit -m "feat(visual-explain): render matrix annotations and restyle to v1"
```

---

### Task 6: flow renderer の視覚構造刷新（spine＋レール）＋flow.css

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/renderers/flow.py`
- Modify: `skills/visual-explain/assets/components/flow.css`
- Modify: `skills/visual-explain/assets/components/registry.json`（flow.css digest、`behavior` 文言）
- Modify: `skills/visual-explain/scripts/ve_components/checker.py`（`_DomSemanticParser` が新構造のノード/エッジを抽出できることの確認・必要なら同期）
- Test: `skills/visual-explain/scripts/tests/test_flow_renderer.py`（改訂・追記）

**Interfaces:**
- Consumes: `flow_layout.order_index` / `edge_spans` / `assign_rails`、`CanonicalIR.takeaway_target_ids` / `.emphasis`
- Produces: 新 markup 構造 —

```html
<figure data-ve-component="flow" role="group" aria-label="…" aria-describedby="…">
  <figcaption class="ve-flow-caption">…takeaway…</figcaption>
  <p class="ve-flow-summary">…（注釈文を含む）</p>
  <div class="ve-flow-canvas" style-free>
    <ol class="ve-flow-spine">
      <li class="ve-flow-station">
        <span class="ve-flow-node" data-ve-semantic-id="n1" data-ve-node-id="n1">起案</span>
      </li>
      <li class="ve-flow-link" data-ve-semantic-id="e1" data-ve-from="n1" data-ve-to="n2" data-ve-relation="ordered-transition">
        <span class="ve-flow-arrow" aria-hidden="true">↓</span><span class="ve-flow-edge-label">提出</span><span class="ve-flow-rel">順序遷移</span>
      </li>
      <li class="ve-flow-station">…n2…</li>
    </ol>
    <div class="ve-flow-rails">
      <span class="ve-flow-rail" data-ve-semantic-id="e9" data-ve-from="n1" data-ve-to="n4"
            data-ve-relation="branching" data-ve-rail-lane="0" data-ve-rail-start="1" data-ve-rail-end="7">
        <span class="ve-flow-edge-label">例外時</span>
      </span>
    </div>
  </div>
  <ul class="ve-flow-edges visually-hidden">…（全エッジの文章、data 属性なし）…</ul>
  <ul class="ve-flow-notes">…確度・出典…</ul>
</figure>
```

  - spine の DOM 順は station（reading order）と隣接 link の交互。隣接エッジ（span==1）は link 要素、スキップエッジは rail 要素。
  - rail は `data-ve-rail-lane`（0..2）と `data-ve-rail-start/-end`（CSS Grid の行番号に対応する整数）を持つ。CSS Grid の `grid-row` で位置決めする（自由座標ではなく構造インデックス）。
  - group は station の連続区間を `<li class="ve-flow-group-block" data-ve-semantic-id="g1">` でラップし、`<span class="ve-flow-group-label">` を先頭に置く（現行の連続性検証をそのまま利用）。
  - 可視の data 属性付きエッジ要素は link と rail のみ。visually-hidden の文章一覧には data 属性を付けない（DOM 照合の二重計上を避ける。set 照合なので実害はないが、可視層が唯一の意味層であることを保つ）。

- [ ] **Step 1: 既存テストの期待を新構造へ書き換え、失敗するテストを追加**

`tests/test_flow_renderer.py` を開き、markup 構造を前提にしたアサーション（`ve-flow-nodes` 等）を新クラス名へ更新した上で、次を追加:

```python
class SpineLayoutTest(unittest.TestCase):
    def test_adjacent_edge_becomes_inline_link(self):
        result = _render_flow_fixture("component-valid-flow.json")
        self.assertIn('class="ve-flow-link"', result.markup)
        self.assertNotIn('class="ve-flow-rail"', result.markup)

    def test_skip_edge_becomes_rail_with_lane(self):
        raw = _load("component-valid-flow.json")
        ir = raw["sections"][0]["ir"]
        ir["flow"]["edges"].append(
            {"id": "edge-skip", "from": "node-draft", "to": "node-approve",
             "relation": "branching", "label": "即時承認"})
        result = _render(raw)
        self.assertIn('data-ve-semantic-id="edge-skip"', result.markup)
        self.assertIn('data-ve-rail-lane="0"', result.markup)

    def test_visible_edges_match_ir_exactly(self):
        # 信頼境界の extract_flow_dom が新構造でも from/to/relation を全件回収できる
        from ve_components.checker import extract_flow_dom
        raw = _load("component-valid-flow.json")
        result = _render(raw)
        nodes, edges, incomplete = extract_flow_dom(result.markup)
        self.assertFalse(incomplete)
        declared = {(e["from"], e["to"], e["relation"]) for e in raw["sections"][0]["ir"]["flow"]["edges"]}
        self.assertEqual(edges, declared)

    def test_hidden_edge_list_has_no_data_attrs(self):
        result = _render_flow_fixture("component-valid-flow.json")
        hidden = result.markup.split('class="ve-flow-edges visually-hidden"', 1)[1]
        hidden = hidden.split("</ul>", 1)[0]
        self.assertNotIn("data-ve-from", hidden)

    def test_annotated_node_marked(self):
        result = _render_flow_fixture("component-valid-flow-annotated.json")
        self.assertIn("ve-takeaway-target", result.markup)
        self.assertIn('<span class="ve-emphasis">ここで滞留が発生</span>', result.markup)
```

（`_render` / `_render_flow_fixture` / `_load` は既存 test_flow_renderer.py のヘルパ形式に合わせて定義・流用する。）

- [ ] **Step 2: 失敗を確認**

```bash
python3 -m unittest tests.test_flow_renderer -v 2>&1 | tail -8
```
Expected: 新規テスト FAIL（`ve-flow-link` 不在等）

- [ ] **Step 3: flow.py を刷新**

`render_flow` を次の構造で書き直す（`RenderManifest`/`RenderResult` 生成・notes 生成・グループ連続分割ロジックは既存を維持）:

```python
from ..flow_layout import assign_rails, edge_spans, order_index

def render_flow(section: CanonicalSection, definition) -> RenderResult:
    ir = section.ir
    flow = ir.flow
    assert flow is not None
    node_by_id = {n.id: n for n in flow.nodes}
    takeaway = set(ir.takeaway_target_ids)
    emphasis_by_id = {e.target_id: e.label for e in ir.emphasis}

    index = order_index(flow.nodes, list(flow.reading_order))
    ordered = sorted((nid for nid in index if nid in node_by_id), key=index.__getitem__)
    spans = edge_spans(flow.edges, index)
    rails, rail_diags = assign_rails(spans)
    diagnostics = list(rail_diags)  # validation 済みだが renderer でも防御的に fail

    adjacent = {}  # spine 位置 i と i+1 を結ぶ辺
    for edge in flow.edges:
        s, t = index.get(edge.source), index.get(edge.target)
        if s is not None and t == s + 1:
            adjacent[s] = edge

    def annotate(nid: str) -> str:
        cls = " ve-takeaway-target" if nid in takeaway else ""
        attr = ' data-ve-takeaway="true"' if nid in takeaway else ""
        emphasis = (f'<span class="ve-emphasis">{_esc(emphasis_by_id[nid])}</span>'
                    if nid in emphasis_by_id else "")
        return cls, attr, emphasis

    def station_li(nid: str, row: int) -> str:
        cls, attr, emphasis = annotate(nid)
        return (f'<li class="ve-flow-station" data-ve-row="{row}">'
                f'<span class="ve-flow-node{cls}" data-ve-semantic-id="{_esc(nid)}"'
                f' data-ve-node-id="{_esc(nid)}"{attr}>{_esc(node_by_id[nid].label)}{emphasis}</span></li>')

    def link_li(edge, row: int) -> str:
        cls, attr, emphasis = annotate(edge.id)
        relation = _RELATION_LABEL.get(edge.relation, edge.relation)
        label = f'<span class="ve-flow-edge-label">{_esc(edge.label)}</span>' if edge.label else ""
        return (f'<li class="ve-flow-link{cls}" data-ve-row="{row}" data-ve-semantic-id="{_esc(edge.id)}"'
                f' data-ve-from="{_esc(edge.source)}" data-ve-to="{_esc(edge.target)}"'
                f' data-ve-relation="{_esc(edge.relation)}"{attr}>'
                f'<span class="ve-flow-arrow" aria-hidden="true">↓</span>{label}'
                f'<span class="ve-flow-rel">{_esc(relation)}</span>{emphasis}</li>')
```

spine の組み立て: `ordered` を走査し、位置 i の station（grid 行 `2*i+1`）と、`adjacent.get(i)` があれば link（grid 行 `2*i+2`）を交互に emit。グループは既存の連続 run 分割を station 単位で適用し `ve-flow-group-block` でラップする。

rail の組み立て: rail のグリッド行は「エッジ (s, t) → 開始行 `2*s+1`・終了行 `2*t+2`」（station 行の先頭から対象 station 行の末尾まで）:

```python
    rail_items = []
    for edge in flow.edges:
        if edge.id not in rails:
            continue
        s, t = index[edge.source], index[edge.target]
        cls, attr, emphasis = annotate(edge.id)
        label = f'<span class="ve-flow-edge-label">{_esc(edge.label)}</span>' if edge.label else ""
        rail_items.append(
            f'<span class="ve-flow-rail{cls}" data-ve-semantic-id="{_esc(edge.id)}"'
            f' data-ve-from="{_esc(edge.source)}" data-ve-to="{_esc(edge.target)}"'
            f' data-ve-relation="{_esc(edge.relation)}" data-ve-rail-lane="{rails[edge.id]}"'
            f' data-ve-rail-start="{2 * s + 1}" data-ve-rail-end="{2 * t + 2}"{attr}>'
            f'{label}{emphasis}</span>')
```

visually-hidden の全エッジ文章一覧（data 属性なし）と notes は既存文言を流用。summary には matrix と同形式で注釈文を追記する。非隣接・非レール辺は存在しない（validation 済み）が、防御的に「span==1 でも rails でもない辺」が残った場合は `RENDERER_FAILURE` 相当の diagnostics に積んで fail する。

- [ ] **Step 4: flow.css を新構造用に全面書換**

```css
[data-ve-component="flow"] { display: block; min-width: 0; margin: var(--space-3) 0; }
[data-ve-component="flow"] .ve-flow-caption { margin: 0 0 var(--space-1); font-weight: 700; font-size: var(--fs-h2); max-width: var(--w-narrative); }
[data-ve-component="flow"] .ve-flow-summary { margin: 0 0 var(--space-2); color: var(--text-dim); max-width: var(--w-narrative); }
[data-ve-component="flow"] .ve-flow-canvas { display: grid; grid-template-columns: minmax(14rem, 28rem) repeat(3, var(--space-4)); }
[data-ve-component="flow"] .ve-flow-spine { display: grid; grid-column: 1; grid-row: 1; margin: 0; padding: 0; list-style: none; }
[data-ve-component="flow"] .ve-flow-station { grid-column: 1; }
[data-ve-component="flow"] .ve-flow-node { display: block; padding: var(--space-1) var(--space-2); background: var(--surface); border-radius: .4rem; font-weight: 700; }
[data-ve-component="flow"] .ve-flow-link { display: grid; grid-template-columns: auto 1fr auto; gap: var(--space-1); align-items: center; padding: var(--space-1) var(--space-2); color: var(--text-dim); }
[data-ve-component="flow"] .ve-flow-arrow { color: var(--accent); font-weight: 700; }
[data-ve-component="flow"] .ve-flow-rel { font-size: var(--fs-small); color: var(--text-faint); }
[data-ve-component="flow"] .ve-flow-rails { display: grid; grid-column: 2 / -1; grid-row: 1; grid-template-columns: subgrid; }
[data-ve-component="flow"] .ve-flow-rail { position: relative; border-right: 2px solid var(--accent); border-top: 2px solid var(--accent); border-bottom: 2px solid var(--accent); border-top-right-radius: .4rem; border-bottom-right-radius: .4rem; padding-right: var(--space-1); font-size: var(--fs-small); color: var(--text-dim); }
[data-ve-component="flow"] .ve-flow-rail::after { content: "◀"; position: absolute; left: -0.4rem; bottom: -0.55rem; color: var(--accent); font-size: .7rem; }
[data-ve-component="flow"] .ve-flow-rail[data-ve-rail-lane="0"] { grid-column: 1; }
[data-ve-component="flow"] .ve-flow-rail[data-ve-rail-lane="1"] { grid-column: 2; }
[data-ve-component="flow"] .ve-flow-rail[data-ve-rail-lane="2"] { grid-column: 3; }
[data-ve-component="flow"] .ve-flow-group-block { display: grid; grid-column: 1; padding: var(--space-1); background: var(--bg); border-radius: .4rem; }
[data-ve-component="flow"] .ve-flow-group-label { color: var(--text-faint); font-size: var(--fs-small); font-weight: 700; letter-spacing: .06em; }
[data-ve-component="flow"] .ve-flow-node.ve-takeaway-target { font-weight: 700; background: color-mix(in srgb, var(--text) 8%, var(--surface)); }
[data-ve-component="flow"] .ve-emphasis { display: block; margin-top: var(--space-1); color: var(--text-dim); font-size: .85em; font-weight: 700; }
[data-ve-component="flow"] .ve-flow-notes { margin: var(--space-2) 0 0; padding-left: var(--space-3); color: var(--text-dim); font-size: var(--fs-small); }
```

rail の縦スパンは inline の `grid-row` を許さない設計のため、`data-ve-rail-start/-end` を CSS では使えない。**代替**: renderer が station/link に `data-ve-row` を出力済みなので、rail 要素を `.ve-flow-rails` 内で**行位置に対応する空セルと共に順序配置**する方式を採る — rails コンテナを `grid-template-rows: subgrid` にし、rail 要素へ `style` を使わずに行を指定する手段が CSS だけでは無いため、**レーンごとに1列・行方向は rail 要素の前後に `<span class="ve-flow-rail-gap" data-ve-rows="N"></span>` を挿入して行を消費する**。renderer は各レーン列について（gap, rail, gap…）の順で子要素を emit し、`.ve-flow-rail-gap { grid-row: span var(--ve-rows); }` は使えないので gap 要素を N 個の空 `<span class="ve-flow-rail-gap"></span>` として展開する（N は行数。決定論的・非座標）。この詳細は実装時に `test_skip_edge_becomes_rail_with_lane` と目視 fixture で検証する。

- [ ] **Step 5: checker との同期を確認**

```bash
grep -n "_NODE_LIST_CLASSES\|ve-flow-nodes" ve_components/checker.py
```

`_DomSemanticParser` の `_NODE_LIST_CLASSES = {"ve-flow-nodes", "ve-flow-group-nodes"}` はノード認識の親リスト制約。新構造ではノードは `.ve-flow-spine` / `.ve-flow-group-block` 配下になるため、集合を `{"ve-flow-spine", "ve-flow-group-block"}` に更新し、`.ve-flow-node` が `<span>` になったことに合わせてタグ非依存の認識であることを確認する（checker のノード束縛は class ベース）。該当テスト（test_component_checker / test_controlled_slots の flow 系 fixture）を新構造の断片へ更新する。**弱めない**: 認識規則の対象クラス名の変更のみで、data 属性必須・完全性検査はそのまま。

- [ ] **Step 6: registry.json 更新（digest・文言）**

```bash
shasum -a 256 ../assets/components/flow.css
```
digest を更新し、`behavior` を「静的な spine とレールでノードと接続を同一視野に描画する。」へ変更。

- [ ] **Step 7: テスト緑・回帰・コミット**

```bash
python3 -m unittest tests.test_flow_renderer tests.test_mixed_assembly tests.test_component_checker -v 2>&1 | tail -3
python3 -m unittest discover -s tests 2>&1 | tail -3
git add ve_components/renderers/flow.py ve_components/checker.py ../assets/components/flow.css ../assets/components/registry.json tests/
git commit -m "feat(visual-explain): rebuild flow renderer as spine+rails topology view"
```

---

### Task 7: ask ブロックの checker 検証

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/checker.py`
- Modify: `skills/visual-explain/scripts/ve_components/diagnostics.py`（`ASK_CONTRACT_VIOLATION = "ask_contract_violation"`）
- Create: `skills/visual-explain/scripts/tests/test_ask_blocks.py`
- Create: `skills/visual-explain/scripts/tests/bad-ask-decision.html`（新 skeleton ベース。resplice ツールで生成し CONTENT に違反 ask を入れる）

**Interfaces:**
- Produces: `validate_ask_blocks(content_markup: str) -> list[Diagnostic]` — `data-ask` 属性を持つ要素を走査し、種別契約を検査。`validate_content_markup` の呼び出し側（compatibility 経路と最終文書検査の両方が通る `check_final_document` / 静的 checker）に組み込む

検査規則（DOM 構造。HTMLParser ベースで `data-ask` 要素のサブツリーを収集）:
- `data-ask` の値が `decision` / `request` / `hypothesis` のいずれでもない → 違反
- decision: `.ask-question` ちょうど1つ、`[data-ask-option]` 2つ以上、`[data-ask-default]` は0か1、0のとき `.ask-no-default-reason` 必須
- request: `[data-ask-role]` を持つ項目1つ以上、各値は `user` / `agent` / `third-party` のみ、`data-ask-role-label` 属性必須（表示ラベル）
- hypothesis: `.ask-claim` ちょうど1つ・その内部に `.certainty` 必須、`.ask-verify` ちょうど1つ

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_ask_blocks.py`:

```python
import unittest

from ve_components.checker import validate_ask_blocks

VALID_DECISION = """
<div class="ask" data-ask="decision">
  <p class="ask-kind">判断してください</p>
  <p class="ask-question">注釈を今回に含めますか？</p>
  <ul class="ask-options">
    <li data-ask-option data-ask-default><span>含める</span><span class="ask-tradeoff">変更量が増える</span></li>
    <li data-ask-option><span>次フェーズ</span><span class="ask-tradeoff">効果が遅れる</span></li>
  </ul>
</div>
"""

VALID_REQUEST = """
<div class="ask" data-ask="request">
  <p class="ask-kind">お願いする動作</p>
  <ol class="ask-steps">
    <li data-ask-role="user" data-ask-role-label="あなた">specをレビューする</li>
    <li data-ask-role="agent" data-ask-role-label="Claude">planを執筆する</li>
  </ol>
</div>
"""

VALID_HYPOTHESIS = """
<div class="ask" data-ask="hypothesis">
  <p class="ask-kind">検証待ちの仮説</p>
  <p class="ask-claim">見出しだけで判断できる <span class="certainty inferred">推論</span></p>
  <p class="ask-verify">検証方法: 見出し列のみで判断内容を言えるか確認する</p>
</div>
"""


class AskBlockTest(unittest.TestCase):
    def test_valid_blocks_pass(self):
        for markup in (VALID_DECISION, VALID_REQUEST, VALID_HYPOTHESIS):
            self.assertEqual(validate_ask_blocks(markup), [])

    def test_unknown_kind_fails(self):
        diags = validate_ask_blocks('<div class="ask" data-ask="poll"><p class="ask-question">?</p></div>')
        self.assertEqual([d.code for d in diags], ["ask_contract_violation"])

    def test_decision_needs_two_options(self):
        markup = VALID_DECISION.replace(
            '<li data-ask-option><span>次フェーズ</span><span class="ask-tradeoff">効果が遅れる</span></li>', "")
        self.assertTrue(validate_ask_blocks(markup))

    def test_decision_two_defaults_fail(self):
        markup = VALID_DECISION.replace("<li data-ask-option><span>次フェーズ", "<li data-ask-option data-ask-default><span>次フェーズ")
        self.assertTrue(validate_ask_blocks(markup))

    def test_decision_zero_default_requires_reason(self):
        markup = VALID_DECISION.replace(" data-ask-default", "")
        self.assertTrue(validate_ask_blocks(markup))
        with_reason = markup.replace("</ul>", '</ul><p class="ask-no-default-reason">判断材料が拮抗しているため</p>')
        self.assertEqual(validate_ask_blocks(with_reason), [])

    def test_request_role_must_be_semantic(self):
        markup = VALID_REQUEST.replace('data-ask-role="user"', 'data-ask-role="あなた"')
        self.assertTrue(validate_ask_blocks(markup))

    def test_hypothesis_needs_certainty_and_verify(self):
        markup = VALID_HYPOTHESIS.replace('<span class="certainty inferred">推論</span>', "")
        self.assertTrue(validate_ask_blocks(markup))
        markup2 = VALID_HYPOTHESIS.replace('class="ask-verify"', 'class="other"')
        self.assertTrue(validate_ask_blocks(markup2))

    def test_content_without_ask_is_ignored(self):
        self.assertEqual(validate_ask_blocks("<p>ふつうの本文</p>"), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 失敗を確認**

```bash
python3 -m unittest tests.test_ask_blocks -v 2>&1 | tail -3
```
Expected: FAIL（`validate_ask_blocks` 未定義）

- [ ] **Step 3: checker.py に実装**

`_ContentSafetyParser` の後に追加:

```python
_ASK_KINDS = frozenset({"decision", "request", "hypothesis"})
_ASK_ROLES = frozenset({"user", "agent", "third-party"})


class _AskParser(HTMLParser):
    """Collect structural facts for each data-ask subtree (nesting-depth scoped)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict] = []
        self._stack: list[tuple[dict, int]] = []
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        self._depth += 1
        attr = dict(attrs)
        classes = frozenset((attr.get("class") or "").split())
        if "data-ask" in attr:
            block = {"kind": attr.get("data-ask") or "", "questions": 0, "options": 0,
                     "defaults": 0, "no_default_reason": 0, "roles": [], "role_labels": 0,
                     "claims": 0, "claim_certainty": 0, "verifies": 0, "_claim_depth": None}
            self.blocks.append(block)
            self._stack.append((block, self._depth))
        for block, _depth in self._stack:
            if "ask-question" in classes:
                block["questions"] += 1
            if "data-ask-option" in attr:
                block["options"] += 1
            if "data-ask-default" in attr:
                block["defaults"] += 1
            if "ask-no-default-reason" in classes:
                block["no_default_reason"] += 1
            if "data-ask-role" in attr:
                block["roles"].append(attr.get("data-ask-role") or "")
                if attr.get("data-ask-role-label"):
                    block["role_labels"] += 1
            if "ask-claim" in classes:
                block["claims"] += 1
                block["_claim_depth"] = self._depth
            if "certainty" in classes and block["_claim_depth"] is not None and self._depth > block["_claim_depth"]:
                block["claim_certainty"] += 1
            if "ask-verify" in classes:
                block["verifies"] += 1

    def handle_endtag(self, tag):
        if self._stack and self._stack[-1][1] == self._depth:
            block, _ = self._stack[-1]
            if block["_claim_depth"] == self._depth:
                block["_claim_depth"] = None
            self._stack.pop()
        self._depth -= 1


def validate_ask_blocks(content_markup: str) -> list[Diagnostic]:
    parser = _AskParser()
    parser.feed(content_markup)
    parser.close()
    diags: list[Diagnostic] = []
    for block in parser.blocks:
        kind = block["kind"]
        if kind not in _ASK_KINDS:
            diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, f"未知の ask 種別 '{kind}'"))
            continue
        if kind == "decision":
            if block["questions"] != 1:
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "decision には ask-question がちょうど1つ必要です"))
            if block["options"] < 2:
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "decision には選択肢が2件以上必要です"))
            if block["defaults"] > 1:
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "decision の既定案は最大1件です"))
            if block["defaults"] == 0 and block["no_default_reason"] != 1:
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "既定案なしの decision には ask-no-default-reason が必要です"))
        elif kind == "request":
            if not block["roles"]:
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "request には data-ask-role 付きの手順が1件以上必要です"))
            if any(role not in _ASK_ROLES for role in block["roles"]):
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "data-ask-role は user/agent/third-party のみ有効です"))
            if block["role_labels"] != len(block["roles"]):
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "各手順に data-ask-role-label（表示ラベル）が必要です"))
        else:  # hypothesis
            if block["claims"] != 1 or block["claim_certainty"] < 1:
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "hypothesis には確度バッジ入りの ask-claim がちょうど1つ必要です"))
            if block["verifies"] != 1:
                diags.append(Diagnostic(ASK_CONTRACT_VIOLATION, "hypothesis には ask-verify がちょうど1つ必要です"))
    return diags
```

`validate_content_markup` の末尾に `diagnostics.extend(validate_ask_blocks(content_markup))` を追加し、`check_final_document` の最終検査経路（`validate_artifact_semantics` を呼ぶ側）にも content 全体への `validate_ask_blocks` 呼び出しを追加する。diagnostics.py に `ASK_CONTRACT_VIOLATION = "ask_contract_violation"` を追加。

- [ ] **Step 4: 静的 checker 経路の fixture を追加**

`bad-ask-decision.html` を `valid-research.html` のコピーから作成し、CONTENT 内に選択肢1件だけの decision ブロックを挿入。`test_component_checker.py`（静的 checker のテスト）に「bad-ask-decision.html が `ask_contract_violation` で fail する」テストを追記する（既存の bad-* fixture テストの形式に従う）。

- [ ] **Step 5: テスト緑・回帰・コミット**

```bash
python3 -m unittest tests.test_ask_blocks tests.test_component_checker -v 2>&1 | tail -3
python3 -m unittest discover -s tests 2>&1 | tail -3
git add ve_components/checker.py ve_components/diagnostics.py tests/test_ask_blocks.py tests/bad-ask-decision.html tests/test_component_checker.py
git commit -m "feat(visual-explain): validate ask block contracts in checker"
```

---

### Task 8: 規範文書の全面改訂（design-system / patterns / 出典台帳）

**Files:**
- Modify: `skills/visual-explain/references/design-system.md`
- Modify: `skills/visual-explain/references/patterns.md`
- Create: `skills/visual-explain/references/sources.md`

**Interfaces:**
- Consumes: Task 4 のトークン語彙・Task 7 の ask 記法・Task 3/5/6 の注釈記法
- Produces: 生成時規範（このスキルを実行するモデルへの指示文書）

- [ ] **Step 1: design-system.md を3層基準へ改訂**

既存の構成（固定骨格の説明・トークン・matrix/flow 色契約・Mayer 規則・確度と出典）を保ちながら、次を反映する:

1. **トークン節を新語彙に置換**: Task 4 の Produces に列挙した全トークン（階調7・判断状態6＋alias・タイプ4＋行間2・余白7・幅2）を、それぞれ1行の用途説明付きで列挙する。「`--accent`=選択、`--positive`=推奨、`--warning`=警告。**色は判断状態専用。装飾に使うな。確度はモノクロバッジ＋線種（confirmed=実線・inferred=破線・unverified=点線）で表し、意味色を使うな**」を明記。
2. **3層基準の章を追加**: 構造層（アクションタイトル契約 — 述語を持つ自己完結した主張・1洞察・40〜50字目安／1主張＝1主要証拠オブジェクト／horizontal logic 自己検査／3秒・30秒・3分パス）、記法層（統一記法・takeaway キャプション・注釈・ask）、表層（4段タイプスケール・8px グリッド・二段階幅 — narrative 45rem / evidence 65rem・左端整列線・枠線は面で代替）を、生成時の命令形で記述する。
3. **密度上限**: matrix は1画面あたり10行目安・flow は12ノード目安。超えるなら分割せよ、と明記。
4. **既存の Mayer 節・確度と出所節・「効果を約束しない」規律は保持**（文言はトークン変更に追随）。

- [ ] **Step 2: patterns.md を改訂**

1. 冒頭の共通契約に「**見出しはアクションタイトル**（述語を持つ自己完結した主張。トピック名禁止）」「**horizontal logic 自己検査**: 完成前に見出しだけを上から読み、承認/却下を判断できなければ見出しを書き直す」を追加。
2. 図のキャプション規約を「caption はその図から持ち帰る1文（takeaway）。図の説明文を書かない」に変更。
3. canonical matrix/flow の注釈の使い方を追加: 「takeaway が特定のセル/ノード/エッジで証明されるなら `takeawayTargetIds` で1〜3件指し、局所の補足は `emphasis` で対象の直近に書く。図全体の主張のみ `takeawayScope: "whole"`」。
4. **ask ブロック文法**を共通文法ブロック節へ追加（Task 7 の VALID_DECISION / VALID_REQUEST / VALID_HYPOTHESIS と同一のマークアップを掲載し、使い分け — 未決事項は decision・ユーザーへの依頼は request・検証待ち主張は hypothesis — を1行ずつ）。
5. flow の記述を新構造に更新: 「flow は縦の spine で描かれる。分岐・スキップは右側レールになる。前向き・fan 3以下・レール3以下を超える構造は受理されない。受理不能なら matrix か文章へ」。既存の Pi/Katsura 縮退節は保持。

- [ ] **Step 3: sources.md を作成**

```markdown
# visual-explain ビジュアル基準 v1 の出典台帳

参照日はすべて 2026-07-11。「支持する規則」は design-system.md の対応規範。

| 資料 | 種別 | URL/書誌 | 支持する規則 |
|---|---|---|---|
| IBCS Standards (ISO 24896) | 一次 | https://www.ibcs.com/ | 統一記法（同じ意味＝同じ見た目）、根拠部の高密度許容（CONDENSE） |
| Apple HIG: Typography | 一次 | https://developer.apple.com/design/human-interface-guidelines/typography | 単一フォント族・ウェイト階層 |
| Apple HIG: Layout | 一次 | https://developer.apple.com/design/human-interface-guidelines/layout | 整列・画面適応 |
| FT Visual Vocabulary | 一次 | https://github.com/Financial-Times/chart-doctor/tree/main/visual-vocabulary | 関係9カテゴリ（将来の拡充語彙） |
| McKinsey 流スライド設計解説 | 二次 | https://a1slides.com/mckinsey-presentation-framework/ ほか deckary.com | アクションタイトル・horizontal logic・ピラミッド原則 |
| Minto, *The Pyramid Principle* | 原典未参照（二次経由） | 書誌のみ | 同上 |
| Zelazny, *Say It With Charts* | 原典未参照（二次経由） | 書誌のみ | 比較5型（将来語彙） |
| Tufte data-ink 解説 | 二次 | https://infovis-wiki.net/wiki/Data-Ink_Ratio | 装飾色ゼロ・non-data-ink 削減 |
| Burn-Murdoch 注釈研究の紹介 | 二次 | https://gijn.org/stories/data-visualization-storytelling-tips-john-burn-murdoch/ | 図上注釈の第一級化 |
| 5秒ルール解説 | 二次 | https://customerscience.com.au/customer-experience-2/designing-actionable-dashboards-the-5-second-rule-for-executives/ | 3秒テスト・3段階読解パス |
| 8px グリッド | 実務慣行 | （HIG の明文規定ではない） | スペーシンググリッド |
| 3層責務分離・判断状態色・ask 記法・疎密2モード | 独自決定 | spec 2026-07-11 | 該当章全体 |

限界: 教育/報道文脈の実験知見は本用途での効果量を約束しない（design-system.md の規律を参照）。
```

- [ ] **Step 4: 整合確認とコミット**

```bash
grep -n "flow-node\|--accent-warm" ../references/design-system.md ../references/patterns.md
# 期待: 新記述と skeleton の実クラス/トークンが一致していること（目視）
python3 -m unittest discover -s tests 2>&1 | tail -3
git add ../references/design-system.md ../references/patterns.md ../references/sources.md
git commit -m "docs(visual-explain): rewrite generation norms for visual standard v1"
```

---

### Task 9: 検証 fixture マトリクスと canonical example の再生成

**Files:**
- Create: `skills/visual-explain/scripts/tests/matrix-doc-long-titles.html`（長い日本語見出し）
- Create: `skills/visual-explain/scripts/tests/matrix-doc-mixed-density.html`（疎な第一画面＋高密度 matrix）
- Create: `skills/visual-explain/scripts/tests/assembly-branching-flow.json`（分岐＋group＋スキップ＋注釈入り flow）
- Create: `skills/visual-explain/scripts/tests/matrix-doc-all-notations.html`（意味色3・確度3・ask 3種・注釈の同時出現）
- Modify: `skills/visual-explain/scripts/tests/test_component_checker.py`（4文書が checker PASS するテスト）
- Modify: `skills/visual-explain/examples/example-proposal.html`（新基準の内容へ改訂）
- Modify: `skills/visual-explain/scripts/tests/fixtures.md`（fixture 台帳の追記）

**Interfaces:**
- Consumes: これまでの全タスクの成果物
- Produces: spec の「検証 fixture マトリクス」を満たす4文書と、更新済み canonical example

- [ ] **Step 1: 検証テストを書く（失敗を確認）**

`test_component_checker.py` に追記:

```python
class VerificationMatrixTest(unittest.TestCase):
    DOCS = ["matrix-doc-long-titles.html", "matrix-doc-mixed-density.html",
            "matrix-doc-all-notations.html"]

    def test_verification_docs_pass_checker(self):
        for name in self.DOCS:
            with self.subTest(doc=name):
                diags = _check_document(FIXTURES / name)   # 既存の checker 実行ヘルパに合わせる
                self.assertEqual(diags, [])

    def test_branching_flow_assembly_builds(self):
        raw = _load("assembly-branching-flow.json")
        html_doc = _build(raw)   # 既存の build ヘルパに合わせる
        self.assertIn("ve-flow-rail", html_doc)
        self.assertIn("ve-flow-group-block", html_doc)
```

Expected（実装前）: fixture 不在で FAIL。

- [ ] **Step 2: 4つの検証文書を作成**

いずれも `resplice.py` で新 skeleton から生成し、CONTENT にのみ内容を書く。

1. **matrix-doc-long-titles.html**: 第一画面＋見出しが45〜50字の日本語アクションタイトルを持つセクション2つ（例:「承認フローの手戻りは3箇所に集中しており、いずれもレビュー担当の引き継ぎ境界で発生している」）。本文は各2〜3文。
2. **matrix-doc-mixed-density.html**: 第一画面（提案1文＋判断1文＋条件2件のみ）と、8行×4列の `.matrix` 表（選択案1行に `data-tone="accent"`）を持つ根拠セクション。
3. **assembly-branching-flow.json**: 6ノード・group 2つ・隣接エッジ4・スキップエッジ1（`branching`）・`takeawayTargetIds` 1件・`emphasis` 1件の canonical flow アセンブリ。`component-valid-flow-groups.json` を出発点に拡張する。
4. **matrix-doc-all-notations.html**: 1文書内に — `data-tone="accent|positive|warning"` の option-card、確度バッジ3種、decision（既定案あり）/request/hypothesis の ask 3種 — を同時に含むセクション群。

- [ ] **Step 3: canonical example を新基準の内容へ改訂**

`examples/example-proposal.html` の CONTENT を新基準で書き直す（resplice 済みの骨格に対して内容のみ）:
- 第一画面: 提案1文・あなたが決めること1文・条件2件（現行内容を保持しつつ密度を疎モードへ）
- 全見出しをアクションタイトル契約（述語・自己完結・40〜50字以内）へ書き直す
- 比較表の caption を takeaway 文へ変更
- 末尾の判断依頼を decision ブロック（既定案＋トレードオフ付き選択肢2件）に変換
- 「リスクと弱い前提」に hypothesis ブロックを1つ入れる

- [ ] **Step 4: 全検証を実行**

```bash
python3 -m unittest discover -s tests -v 2>&1 | tail -3
./check.sh ../examples/example-proposal.html
./check.sh tests/matrix-doc-all-notations.html
```
Expected: 全緑・全 PASS

- [ ] **Step 5: fixtures.md を更新しコミット**

fixture 台帳へ4文書の目的（spec の検証マトリクス対応）を1行ずつ追記。

```bash
git add tests/ ../examples/example-proposal.html
git commit -m "test(visual-explain): add verification fixture matrix and regenerate canonical example"
```

- [ ] **Step 6: ユーザー目視スモークの準備**

```bash
open ../examples/example-proposal.html
open tests/matrix-doc-all-notations.html
```

ユーザーへ依頼する確認項目（ライト/ダーク×広幅/狭幅）: 3秒テスト／見出しのみ判断テスト／色＝意味（装飾色ゼロ）／overflow・整列破綻なし。**この確認はユーザーが行う。完了主張の前に必ず依頼すること。**

---

## Self-Review 記録

- **Spec coverage**: 構造層（Task 8 patterns/design-system・Task 9 example）／記法層 — トークン・確度分離（Task 4）・注釈（Task 3/5/6）・ask（Task 4 CSS・Task 7 checker・Task 8 文法）・将来語彙（Task 8 sources/design-system）／表層（Task 4・監査 Task 4 Step 1）／flow 契約とトポロジー（Task 1/2/6）／実装スコープ表の全行（Task 3〜9）／成功基準（Task 4 監査・Task 9 マトリクス・目視）— 対応タスクあり。
- **Placeholder scan**: 「実装時に確認/調整」とした箇所は (a) コントラスト不足時の明度調整（監査テストが裁定者）、(b) rail の行消費の gap 展開詳細（テストと目視 fixture が裁定者）、(c) 既存ヘルパ関数名への追随 — いずれも裁定手続きを明記済み。
- **Type consistency**: `flow_layout` の関数名/シグネチャは Task 1 定義を Task 2/6 が消費。`EmphasisAnnotation.target_id` / `takeaway_target_ids` は Task 3 定義を Task 5/6 が消費。ask のクラス名/データ属性は Task 4（CSS）・Task 7（checker）・Task 8（文法）・Task 9（fixture）で同一。
