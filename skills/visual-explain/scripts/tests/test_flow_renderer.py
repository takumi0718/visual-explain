"""Task 6 tests: the flow component through the same route as matrix."""
from __future__ import annotations

import copy
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from ve_components.diagnostics import ContractError
from ve_components.model import CanonicalSection, RenderResult
from ve_components.registry import ResolvedComponent, load_registry, resolve_component
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.renderers.flow import render_flow
from ve_components.validation import validate_canonical_section

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"
FLOW_DEF = REGISTRY.find("flow", 1)


def flow_ir(mutate=None) -> dict:
    raw = json.loads((TESTS / "component-valid-flow.json").read_text("utf-8"))
    ir = raw["sections"][0]["ir"]
    if mutate:
        mutate(ir)
    return ir


def render_fixture():
    ir = validate_canonical_section(flow_ir())
    return ir, render_flow(CanonicalSection(ir=ir), FLOW_DEF)


def _load(name: str) -> dict:
    return json.loads((TESTS / name).read_text("utf-8"))


def _render(raw: dict) -> RenderResult:
    ir = validate_canonical_section(raw["sections"][0]["ir"])
    return render_flow(CanonicalSection(ir=ir), FLOW_DEF)


def _render_flow_fixture(name: str) -> RenderResult:
    return _render(_load(name))


def codes(err: ContractError) -> set[str]:
    return err.codes


class SharedRouteTest(unittest.TestCase):
    def test_flow_uses_same_loader_and_resolver_as_matrix(self) -> None:
        self.assertIsNotNone(FLOW_DEF)
        self.assertIn("flow@1", TRUSTED_RENDERERS)
        self.assertIn("matrix@1", TRUSTED_RENDERERS)
        ir = validate_canonical_section(flow_ir())
        resolved = resolve_component(ir.selection, REGISTRY)
        self.assertIsInstance(resolved, ResolvedComponent)
        result = resolved.renderer(CanonicalSection(ir=ir), resolved.component)
        self.assertIsInstance(result, RenderResult)


class FlowPayloadRejectionTest(unittest.TestCase):
    def reject(self, mutate) -> set[str]:
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(flow_ir(mutate))
        return codes(ctx.exception)

    def test_duplicate_nodes(self) -> None:
        self.assertIn("duplicate_semantic_id", self.reject(lambda ir: ir["flow"]["nodes"][1].__setitem__("id", "node-draft")))

    def test_dangling_edge(self) -> None:
        self.assertIn("invalid_flow_edge", self.reject(lambda ir: ir["flow"]["edges"][0].__setitem__("to", "ghost")))

    def test_missing_relation(self) -> None:
        self.assertIn("invalid_flow_edge", self.reject(lambda ir: ir["flow"]["edges"][0].pop("relation")))

    def test_self_edge(self) -> None:
        self.assertIn("invalid_flow_edge", self.reject(lambda ir: ir["flow"]["edges"][0].__setitem__("to", ir["flow"]["edges"][0]["from"])))

    def test_ambiguous_start(self) -> None:
        def mutate(ir):
            ir["flow"].pop("startId")
            ir["flow"]["edges"] = [ir["flow"]["edges"][1]]  # only review->approve; draft & review both roots
        self.assertIn("invalid_component_payload", self.reject(mutate))

    def test_unreachable_node(self) -> None:
        def mutate(ir):
            ir["flow"]["edges"] = [ir["flow"]["edges"][1]]  # review->approve; draft is start but reaches nothing
        self.assertIn("invalid_component_payload", self.reject(mutate))

    def test_cycle_when_acyclic(self) -> None:
        def mutate(ir):
            ir["flow"]["edges"].append({"id": "edge-loop", "from": "node-approve", "to": "node-draft", "relation": "directed-transition"})
        self.assertIn("invalid_flow_edge", self.reject(mutate))


class FlowMarkupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ir, self.result = render_fixture()
        self.markup = self.result.markup

    def test_figure_with_caption_and_summary(self) -> None:
        self.assertIn('<figure data-ve-component="flow"', self.markup)
        self.assertIn(self.ir.caption, self.markup)
        self.assertIn(self.ir.accessibility.summary, self.markup)

    def test_nodes_in_reading_order(self) -> None:
        self.assertLess(self.markup.index("node-draft"), self.markup.index("node-review"))
        self.assertLess(self.markup.index("node-review"), self.markup.index("node-approve"))

    def test_edges_expose_from_to_relation_and_direction(self) -> None:
        for edge in self.ir.flow.edges:
            self.assertIn(f'data-ve-semantic-id="{edge.id}"', self.markup)
            self.assertIn(f'data-ve-from="{edge.source}"', self.markup)
            self.assertIn(f'data-ve-to="{edge.target}"', self.markup)
            self.assertIn(f'data-ve-relation="{edge.relation}"', self.markup)
        # Adjacent transitions render as inline spine links with a downward arrow.
        self.assertIn("↓", self.markup)

    def test_visible_certainty_and_source(self) -> None:
        self.assertIn("レビュー運用手順", self.markup)
        self.assertIn("確認済み", self.markup)

    def test_manifest_consumes_all_semantic_ids(self) -> None:
        self.assertEqual(set(self.result.manifest.consumed_semantic_ids), set(self.ir.semantic_ids()))
        self.assertEqual(self.result.script_asset_ids, ())
        self.assertEqual(self.result.style_asset_ids, ("flow.css",))

    def test_static_no_scripts_or_handlers_or_external(self) -> None:
        self.assertNotIn("<script", self.markup)
        self.assertFalse(re.search(r"\son[a-z]+=", self.markup))
        self.assertNotIn("style=", self.markup)
        self.assertNotIn("http://", self.markup)
        self.assertNotIn("https://", self.markup)

    def test_escaping(self) -> None:
        ir = validate_canonical_section(flow_ir(lambda ir: ir["flow"]["nodes"][0].__setitem__("label", "<x>&")))
        markup = render_flow(CanonicalSection(ir=ir), FLOW_DEF).markup
        self.assertNotIn("<x>", markup)
        self.assertIn("&lt;x&gt;", markup)

    def test_accessibility_label_preserved_in_dom(self) -> None:
        self.assertIn(f'aria-label="{self.ir.accessibility.label}"', self.markup)

    def test_css_namespaced_and_responsive(self) -> None:
        css = (SKILL / "assets" / "components" / "flow.css").read_text("utf-8")
        for line in css.splitlines():
            s = line.strip()
            if not s or s.startswith("/*") or s.startswith("@media") or s == "}":
                continue
            self.assertTrue(s.startswith('[data-ve-component="flow"]'), f"non-namespaced: {s}")
        # The spine+rails grid stays laid out on every viewport and scrolls
        # horizontally rather than reflowing: a scroll container plus a canvas
        # min-width is the responsive mechanism.
        self.assertIn("overflow-x: auto", css)
        self.assertIn("min-width: 24rem", css)


class FlowGroupsTest(unittest.TestCase):
    def setUp(self) -> None:
        raw = json.loads((TESTS / "component-valid-flow-groups.json").read_text("utf-8"))
        self.ir = validate_canonical_section(raw["sections"][0]["ir"])
        self.result = render_flow(CanonicalSection(ir=self.ir), FLOW_DEF)
        self.markup = self.result.markup

    def test_group_ids_and_labels_in_dom(self) -> None:
        for group in self.ir.flow.groups:
            self.assertIn(f'data-ve-semantic-id="{group.id}"', self.markup)
            self.assertIn(group.label, self.markup)

    def test_all_non_section_consumed_ids_in_dom(self) -> None:
        for sid in self.result.manifest.consumed_semantic_ids:
            if sid == self.ir.id:
                continue
            self.assertIn(f'data-ve-semantic-id="{sid}"', self.markup)

    def test_grouped_reading_order_preserved(self) -> None:
        self.assertLess(self.markup.index("gn-draft"), self.markup.index("gn-review"))
        self.assertLess(self.markup.index("gn-review"), self.markup.index("gn-approve"))

    def test_build_and_check_grouped_flow(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as handle:
            out = Path(handle.name)
        try:
            build = subprocess.run(
                ["python3", str(SKILL / "scripts" / "build_explainer.py"),
                 "--assembly", str(TESTS / "component-valid-flow-groups.json"), "--output", str(out)],
                capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            check = subprocess.run(["bash", str(SKILL / "scripts" / "check.sh"), str(out)],
                                   capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        finally:
            out.unlink(missing_ok=True)


def _grouped_ir(reading_order):
    return {
        "id": "sec-grp-order",
        "relationship": {"kind": "directed-graph", "capabilities": ["ordered-transition", "directed-transition", "branching"]},
        "selection": {"component": "flow", "version": 1, "matchedCapabilities": ["ordered-transition", "directed-transition"]},
        "caption": "順序保持のグループ",
        "certainty": [{"id": "oc", "level": "confirmed", "statement": "s"}],
        "sources": [{"id": "os", "label": "L"}],
        "accessibility": {"label": "lab", "summary": "sum"},
        "flow": {
            "groups": [{"id": "grp-a", "label": "Aグループ"}, {"id": "grp-b", "label": "Bグループ"}],
            "nodes": [
                {"id": "a1", "label": "A1", "group": "grp-a"},
                {"id": "b1", "label": "B1", "group": "grp-b"},
                {"id": "b2", "label": "B2", "group": "grp-b"}
            ],
            "edges": [
                {"id": "eo1", "from": "b1", "to": "b2", "relation": "ordered-transition"},
                {"id": "eo2", "from": "b2", "to": "a1", "relation": "directed-transition"}
            ],
            "startId": "b1",
            "readingOrder": reading_order
        }
    }


class FlowGroupReadingOrderTest(unittest.TestCase):
    def test_reading_order_wins_over_group_declaration_order(self) -> None:
        # groups declared [A, B] but reading order presents the B group first.
        ir = validate_canonical_section(_grouped_ir(["b1", "b2", "a1"]))
        markup = render_flow(CanonicalSection(ir=ir), FLOW_DEF).markup
        self.assertLess(markup.index("b1"), markup.index("b2"))
        self.assertLess(markup.index("b2"), markup.index("a1"))
        self.assertLess(markup.index("grp-b"), markup.index("grp-a"))

    def test_non_contiguous_group_reading_order_rejected(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(_grouped_ir(["b1", "a1", "b2"]))
        self.assertIn("invalid_component_payload", ctx.exception.codes)


class FlowReadingOrderPermutationTest(unittest.TestCase):
    """readingOrder, when present, must be a unique permutation of exactly the
    declared flow node IDs — for grouped and ungrouped flows alike."""

    def reject_ungrouped(self, reading_order) -> set[str]:
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(
                flow_ir(lambda ir: ir["flow"].__setitem__("readingOrder", reading_order)))
        return codes(ctx.exception)

    def test_ungrouped_valid_permutation_accepted(self) -> None:
        # component-valid-flow.json's two edges form a linear chain
        # (draft -> review -> approve), which forces a single forward order
        # for those three nodes under v1 topology. To exercise genuine
        # permutation freedom (an order that differs from declaration order)
        # without tripping the forward-edge constraint, add a node reachable
        # only from node-draft with no other ordering constraint, and move it
        # ahead of node-review/node-approve in the reading order.
        def mutate(ir):
            ir["flow"]["nodes"].append({"id": "node-extra", "label": "参考資料"})
            ir["flow"]["edges"].append({
                "id": "edge-draft-extra", "from": "node-draft", "to": "node-extra",
                "relation": "directed-transition", "label": "参照",
            })
            ir["flow"]["readingOrder"] = ["node-draft", "node-extra", "node-review", "node-approve"]

        ir = validate_canonical_section(flow_ir(mutate))
        self.assertEqual(
            list(ir.flow.reading_order),
            ["node-draft", "node-extra", "node-review", "node-approve"])

    def test_ungrouped_duplicate_id_rejected(self) -> None:
        # All nodes present, but node-draft is repeated.
        self.assertIn("invalid_component_payload",
                      self.reject_ungrouped(["node-draft", "node-review", "node-approve", "node-draft"]))

    def test_ungrouped_missing_id_rejected(self) -> None:
        # node-approve is omitted, so the order is not a full permutation.
        self.assertIn("invalid_component_payload",
                      self.reject_ungrouped(["node-draft", "node-review"]))

    def test_grouped_duplicate_id_rejected(self) -> None:
        # b1 repeated but kept contiguous within its group, so the duplicate must
        # be caught by permutation validation, not the group-contiguity path.
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(_grouped_ir(["b1", "b1", "b2", "a1"]))
        self.assertIn("invalid_component_payload", ctx.exception.codes)

    def test_grouped_missing_id_rejected(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(_grouped_ir(["b1", "b2"]))
        self.assertIn("invalid_component_payload", ctx.exception.codes)

    def test_present_empty_reading_order_rejected_ungrouped(self) -> None:
        # An explicitly present but empty readingOrder for a non-empty flow is
        # not a permutation of the node IDs and must be rejected — it is not the
        # same as an absent order.
        self.assertIn("invalid_component_payload", self.reject_ungrouped([]))

    def test_present_empty_reading_order_rejected_grouped(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(_grouped_ir([]))
        self.assertIn("invalid_component_payload", ctx.exception.codes)

    def test_absent_reading_order_allowed(self) -> None:
        # No readingOrder key at all: the renderer's node-order fallback is
        # intended, so validation must accept it.
        ir = validate_canonical_section(flow_ir(lambda ir: ir["flow"].pop("readingOrder", None)))
        self.assertEqual(ir.flow.reading_order, ())


class FlowBuildTest(unittest.TestCase):
    def test_build_and_check_flow_fixture(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as handle:
            out = Path(handle.name)
        try:
            build = subprocess.run(
                ["python3", str(SKILL / "scripts" / "build_explainer.py"),
                 "--assembly", str(TESTS / "component-valid-flow.json"), "--output", str(out)],
                capture_output=True, text=True,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            check = subprocess.run(["bash", str(SKILL / "scripts" / "check.sh"), str(out)],
                                   capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        finally:
            out.unlink(missing_ok=True)


class SpineLayoutTest(unittest.TestCase):
    def test_adjacent_edge_becomes_inline_link(self) -> None:
        result = _render_flow_fixture("component-valid-flow.json")
        self.assertIn('class="ve-flow-link"', result.markup)
        self.assertNotIn('class="ve-flow-rail"', result.markup)

    def test_skip_edge_becomes_rail_with_lane(self) -> None:
        raw = _load("component-valid-flow.json")
        ir = raw["sections"][0]["ir"]
        ir["flow"]["edges"].append(
            {"id": "edge-skip", "from": "node-draft", "to": "node-approve",
             "relation": "branching", "label": "即時承認"})
        result = _render(raw)
        self.assertIn('data-ve-semantic-id="edge-skip"', result.markup)
        self.assertIn("ve-rail-lane-0", result.markup)
        self.assertRegex(result.markup, r"ve-rail-\d+-\d+")  # 行スパンクラスが付与されている

    def test_visible_edges_match_ir_exactly(self) -> None:
        # 信頼境界の extract_flow_dom が新構造でも from/to/relation を全件回収できる
        from ve_components.checker import extract_flow_dom
        raw = _load("component-valid-flow.json")
        result = _render(raw)
        nodes, edges, incomplete = extract_flow_dom(result.markup)
        self.assertFalse(incomplete)
        declared = {(e["from"], e["to"], e["relation"]) for e in raw["sections"][0]["ir"]["flow"]["edges"]}
        self.assertEqual(edges, declared)

    def test_hidden_edge_list_has_no_data_attrs(self) -> None:
        result = _render_flow_fixture("component-valid-flow.json")
        hidden = result.markup.split('class="ve-flow-edges visually-hidden"', 1)[1]
        hidden = hidden.split("</ul>", 1)[0]
        self.assertNotIn("data-ve-from", hidden)

    def test_annotated_node_marked(self) -> None:
        result = _render_flow_fixture("component-valid-flow-annotated.json")
        self.assertIn("ve-takeaway-target", result.markup)
        self.assertIn('<span class="ve-emphasis">ここで滞留が発生</span>', result.markup)


if __name__ == "__main__":
    unittest.main()
