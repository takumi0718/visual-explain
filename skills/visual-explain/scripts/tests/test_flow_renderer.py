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
        self.assertIn("→", self.markup)

    def test_visible_certainty_and_source(self) -> None:
        self.assertIn("レビュー運用手順", self.markup)
        self.assertIn("確定", self.markup)

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

    def test_css_namespaced_and_responsive(self) -> None:
        css = (SKILL / "assets" / "components" / "flow.css").read_text("utf-8")
        for line in css.splitlines():
            s = line.strip()
            if not s or s.startswith("/*") or s.startswith("@media") or s == "}":
                continue
            self.assertTrue(s.startswith('[data-ve-component="flow"]'), f"non-namespaced: {s}")
        self.assertIn("@media", css)


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


if __name__ == "__main__":
    unittest.main()
