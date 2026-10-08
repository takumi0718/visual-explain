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


def label_box(points: Sequence[tuple[int, int]], label: str) -> tuple[Rect, tuple[int, int, str]]:
    """Box and anchor of an edge label, placed on the longest segment of the path."""
    segments = list(zip(points, points[1:]))
    longest = max(segments, key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
    return _label_box(longest[0], longest[1], label)


def region_label_box(region) -> Rect:
    """Estimated text box of a region label, from the same width estimate as the fit check."""
    x, y = region_label_position(region)
    return Rect(x, y - REGION_FONT, x + len(region.label) * REGION_FONT, y + 3)


def route_edge(edge, rects: dict[str, Rect], width: int, height: int,
               taken: Sequence[Rect] = ()) -> EdgeRoute | str:
    """Route one edge; return the route or the diagnostic message explaining why it cannot.

    ``taken`` holds label boxes already placed by earlier edges; a label may not overlap them.
    """
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
        box, anchor = label_box(points, edge.label)
        inside = bounds.x0 <= box.x0 and box.x1 <= bounds.x1 and bounds.y0 <= box.y0 and box.y1 <= bounds.y1
        if (inside and not any(box.overlaps(rect) for rect in rects.values())
                and not any(box.overlaps(other) for other in taken)):
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
    taken: list[Rect] = []
    segments: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for edge in payload.edges:
        route = route_edge(edge, rects, width, height, taken)
        if isinstance(route, str):
            messages.append(route)
            continue
        segments.extend(zip(route.points, route.points[1:]))
        if edge.label:
            taken.append(label_box(route.points, edge.label)[0])
    for region in payload.regions:
        box = region_label_box(region)
        if any(_segment_hits(a, b, box) for a, b in segments):
            messages.append(f"囲み '{region.id}' のラベルに線が重なります")
    return messages
