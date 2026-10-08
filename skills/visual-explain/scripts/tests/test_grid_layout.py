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
