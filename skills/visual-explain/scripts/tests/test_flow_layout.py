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

    def test_parallel_edges_fail(self):
        # v1 は同一 (source, target) 対の並行辺を禁止する（隣接辺の上書き・レール重複を構造的に排除）
        diags = check_topology(_nodes("a", "b"), [_edge("e1", "a", "b"), _edge("e2", "a", "b")], [])
        self.assertTrue(any(d.code == "flow_topology_violation" for d in diags))

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
