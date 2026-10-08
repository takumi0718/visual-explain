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


class UniquenessTest(unittest.TestCase):
    """Duplicate ids must be reported before check_layout sees the payload."""

    def test_duplicate_node_id_is_reported_without_running_layout(self) -> None:
        raw = changed()
        raw["nodes"][2]["id"] = "approval"
        self.assertEqual(messages(raw), ["図の id 'approval' が重複しています"])

    def test_edge_id_clashing_with_a_node_id_is_reported(self) -> None:
        raw = changed()
        raw["edges"][0]["id"] = "rollback"
        self.assertEqual(messages(raw), ["図の id 'rollback' が重複しています"])

    def test_unknown_edge_endpoint_never_reaches_layout(self) -> None:
        raw = changed(edges=[{"id": "e1", "from": "ghost", "to": "approval"}])
        self.assertEqual(messages(raw), ["edge.from 'ghost' がノードにありません"])


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
