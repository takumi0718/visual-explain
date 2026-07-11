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

# Row upper bound shared with the renderer's pre-generated ve-rail-{s}-{e}
# classes (bounds 1<=s<e<=28). Kept here so validation can fail closed with
# flow_topology_too_complex *before* the renderer ever has to fail closed
# with renderer_failure.
MAX_SPINE_ROWS = 28


def order_index(nodes: Sequence, reading_order: Sequence[str]) -> dict[str, int]:
    order = list(reading_order) if reading_order else [n.id for n in nodes]
    return {nid: i for i, nid in enumerate(order)}


def check_topology(nodes: Sequence, edges: Sequence, reading_order: Sequence[str]) -> list[Diagnostic]:
    index = order_index(nodes, reading_order)
    diags: list[Diagnostic] = []
    fan_out: dict[str, int] = {}
    fan_in: dict[str, int] = {}
    seen_pairs: set[tuple[str, str]] = set()
    for edge in edges:
        pair = (edge.source, edge.target)
        if pair in seen_pairs:
            diags.append(Diagnostic(FLOW_TOPOLOGY_VIOLATION,
                                    f"辺 '{edge.id}' は同一ノード対の並行辺です (v1 では禁止)"))
        seen_pairs.add(pair)
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


def _spine_walk(nodes: Sequence, edges: Sequence, reading_order: Sequence[str]) -> tuple[int, dict[str, int]]:
    """Mirrors renderers/flow.py's row-counting walk exactly: one row per
    contiguous group-label run, one row per station, one row per adjacent
    link (edges whose span == 1, which the renderer inlines into the spine
    rather than routing onto a rail). Returns the final row number reached
    and each station's row (both 1-indexed, matching the renderer)."""
    node_by_id = {n.id: n for n in nodes}
    index = order_index(nodes, reading_order)
    ordered = sorted((nid for nid in index if nid in node_by_id), key=index.__getitem__)

    adjacent: dict[int, object] = {}
    for edge in edges:
        s, t = index.get(edge.source), index.get(edge.target)
        if s is not None and t == s + 1:
            adjacent[s] = edge

    station_row: dict[str, int] = {}
    row = 0
    current_group: object = object()  # 先頭比較用の番兵
    for nid in ordered:
        group = node_by_id[nid].group
        if group != current_group:
            current_group = group
            if group is not None:
                row += 1
        row += 1
        station_row[nid] = row
        if adjacent.get(index[nid]) is not None:
            row += 1
    return row, station_row


def projected_spine_rows(nodes: Sequence, edges: Sequence, reading_order: Sequence[str]) -> int:
    """Renderer's row count for the spine: group-label rows + stations + adjacent links."""
    last_row, _ = _spine_walk(nodes, edges, reading_order)
    return last_row


def check_row_budget(nodes: Sequence, edges: Sequence, reading_order: Sequence[str]) -> list[Diagnostic]:
    """Fails closed, at validation time, exactly when the renderer would later
    fail closed: either the spine itself grows past MAX_SPINE_ROWS, or some
    rail's end row (station_row[target] + 1, the same quantity
    renderers/flow.py checks before emitting a ve-rail-{s}-{e} class) does.
    """
    last_row, station_row = _spine_walk(nodes, edges, reading_order)
    if last_row > MAX_SPINE_ROWS:
        return [Diagnostic(
            FLOW_TOPOLOGY_TOO_COMPLEX,
            f"flow が行予算 {MAX_SPINE_ROWS} を超えます (ノード/リンク/グループ行の合計)")]

    index = order_index(nodes, reading_order)
    for edge in edges:
        src, dst = index.get(edge.source), index.get(edge.target)
        if src is None or dst is None or dst <= src or dst - src == 1:
            continue  # 未知ID・後方辺は他検査が担当、隣接辺はレールではなくspineに載る
        rail_end_row = station_row.get(edge.target)
        if rail_end_row is not None and rail_end_row + 1 > MAX_SPINE_ROWS:
            return [Diagnostic(
                FLOW_TOPOLOGY_TOO_COMPLEX,
                f"flow が行予算 {MAX_SPINE_ROWS} を超えます (ノード/リンク/グループ行の合計)")]
    return []
