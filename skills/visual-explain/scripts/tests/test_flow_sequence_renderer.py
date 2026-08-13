"""Focused Task 8 contracts for flow sequence rendering."""
from __future__ import annotations

from hashlib import sha256
import html
import json
import re
import subprocess
from pathlib import Path

import pytest

from fixture_util import canonical_ir
from ve_components.assembly import render_canonical
from ve_components.diagnostics import ContractError
from ve_components.model import CanonicalSection
from ve_components.registry import load_registry, resolve_component
from ve_components.renderers.flow import _path_edge_ids, render_flow
from ve_components.validation import validate_assembly, validate_canonical_section


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
TESTS = SKILL / "scripts" / "tests"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
FLOW_DEF = REGISTRY.find("flow", 2)


def _legacy_section() -> CanonicalSection:
    raw = json.loads((TESTS / "component-valid-flow.json").read_text("utf-8"))
    return CanonicalSection(ir=validate_canonical_section(canonical_ir(raw)))


def _sequence_section(mode: str) -> CanonicalSection:
    raw = json.loads((TESTS / "component-valid-flow.json").read_text("utf-8"))
    raw["document"]["profile"] = "visual-stage"
    ir = canonical_ir(raw)
    ir["relationship"]["capabilities"].append("typed-sequence")
    ir["selection"]["matchedCapabilities"].append("typed-sequence")
    ir["flow"]["nodes"].append({"id": "node-publish", "label": "公開"})
    ir["flow"]["edges"].append({
        "id": "edge-approve-publish",
        "from": "node-approve",
        "to": "node-publish",
        "relation": "ordered-transition",
        "label": "公開",
    })
    ir["claim"] = "起案から公開までの経路を段階的に示す。"
    ir["sequence"] = {
        "mode": mode,
        "steps": [
            {
                "id": "step-draft-review",
                "label": "レビューまで",
                "targetIds": ["node-draft", "node-review"],
            },
            {
                "id": "step-approve-publish",
                "label": "公開まで",
                "targetIds": ["node-approve", "node-publish"],
            },
        ],
    }
    ir["assertions"] = [{
        "id": "assertion-flow-path",
        "text": "起案から公開までの経路を段階的に示す。",
        "coverIds": ["node-draft"],
    }]
    request = validate_assembly(raw)
    section = request.sections[1]
    assert isinstance(section, CanonicalSection)
    return section


def _branched_sequence_section() -> CanonicalSection:
    raw = json.loads(
        (TESTS / "component-valid-flow-sequence-branch.json").read_text("utf-8")
    )
    request = validate_assembly(raw)
    section = request.sections[1]
    assert isinstance(section, CanonicalSection)
    return section


def _panel(markup: str, number: int) -> str:
    start = markup.index(f'<div data-step="{number}">')
    if f'<div data-step="{number + 1}">' in markup:
        end = markup.index(f'<div data-step="{number + 1}">', start)
    else:
        end = markup.index('<div class="ve-stepper-controls">', start)
    return markup[start:end]


def _semantic_classes(panel: str, semantic_id: str) -> frozenset[str]:
    tag = re.search(
        rf'<[^>]+data-ve-semantic-id="{re.escape(semantic_id)}"[^>]*>', panel,
    )
    assert tag is not None, semantic_id
    classes = re.search(r'class="([^"]+)"', tag.group(0))
    return frozenset(classes.group(1).split()) if classes else frozenset()


def _connector_pairs(panel: str) -> tuple[tuple[str, str], ...]:
    pairs = []
    for declaration in re.findall(r'data-connect="([^"]+)"', panel):
        source, target = html.unescape(declaration).split("->")
        pairs.append((source, target))
    return tuple(pairs)


def test_path_edge_derivation_returns_within_step_edges_then_previous_tail_bridge() -> None:
    section = _sequence_section("path-spotlight")
    flow = section.ir.flow
    sequence = section.ir.sequence
    assert flow is not None and sequence is not None

    assert _path_edge_ids(flow, sequence, 0) == ("edge-draft-review",)
    assert _path_edge_ids(flow, sequence, 1) == (
        "edge-approve-publish",
        "edge-review-approve",
    )


def test_path_panels_keep_station_only_canvas_and_panel_local_connectors() -> None:
    result = render_flow(_sequence_section("path-spotlight"), FLOW_DEF)

    assert 'data-ve-sequence-mode="path-spotlight"' in result.markup
    for number in (1, 2, 3):
        panel = _panel(result.markup, number)
        assert panel.count("data-connect-scope") == 1
        canvas_match = re.search(
            r'<ol class="ve-flow-canvas ve-flow-path-canvas">(.*?)</ol>',
            panel,
            re.DOTALL,
        )
        assert canvas_match is not None
        canvas = canvas_match.group(1)
        assert len(re.findall(r'<li class="ve-flow-station"(?=[ >])', canvas)) == 4
        assert "ve-flow-link" not in canvas
        assert "ve-flow-rail" not in canvas
        assert "ve-flow-group-label" not in canvas
        assert "data-connect=" not in canvas

        dom_ids = set(re.findall(r'\bid="([^"]+)"', panel))
        pairs = _connector_pairs(panel)
        assert pairs == (
            (f"node-draft--p{number}", f"node-review--p{number}"),
            (f"node-review--p{number}", f"node-approve--p{number}"),
            (f"node-approve--p{number}", f"node-publish--p{number}"),
        )
        assert {endpoint for pair in pairs for endpoint in pair} <= dom_ids
        assert panel.count('data-ve-semantic-id="edge-') == 3
        assert f'data-ve-from="node-review--p{number}"' in panel
        assert f'data-ve-to="node-approve--p{number}"' in panel


def test_path_emits_runtime_asset_only_for_path_spotlight_with_verified_digest() -> None:
    runtime_path = SKILL / "assets" / "components" / "visual-stage-flow.js"
    result = render_flow(_sequence_section("path-spotlight"), FLOW_DEF)
    runtime = FLOW_DEF.asset_by_id("visual-stage-flow")

    assert runtime is not None
    assert (runtime.slot, runtime.path) == ("scripts", "visual-stage-flow.js")
    assert sha256(runtime_path.read_bytes()).hexdigest() == runtime.digest
    assert result.script_asset_ids == ("visual-stage-flow",)
    assert result.manifest.asset_ids == (
        "flow.css", "visual-stage", "visual-stage-flow",
    )
    assert result.manifest.asset_digests[-1] == runtime.digest


def test_flow_runtime_is_path_only_and_replaces_fixed_output_after_each_trigger() -> None:
    source = (
        SKILL / "assets" / "components" / "visual-stage-flow.js"
    ).read_text("utf-8")

    assert '[data-stepper][data-ve-sequence-mode="path-spotlight"] [data-connect-scope]' in source
    assert "requestAnimationFrame" in source
    assert "window.addEventListener('load'" in source
    assert "document.addEventListener('visual-explain:stepchange'" in source
    assert "document.addEventListener('toggle'" in source
    assert "new ResizeObserver" in source
    assert "closest('[data-step][hidden]')" in source
    assert "querySelectorAll('.connector-layer, .connector-warning')" in source
    assert "connection-text visually-hidden" in source


def test_flow_runtime_suspends_opted_in_scopes_before_fixed_handlers_can_see_them() -> None:
    source = (
        SKILL / "assets" / "components" / "visual-stage-flow.js"
    ).read_text("utf-8")

    initial_suspend = source.rindex("\n  suspendScopes();")
    assert initial_suspend < source.index("window.addEventListener('load'")
    assert initial_suspend < source.index("schedule();", initial_suspend)
    assert "scope.removeAttribute('data-connect-scope')" in source
    assert "declaration.removeAttribute('data-connect')" in source
    assert "scope.setAttribute('data-ve-flow-connect-scope', '')" in source
    assert "declaration.setAttribute('data-ve-flow-connect', value)" in source
    assert "const suspendAndSchedule" in source
    assert "new ResizeObserver(suspendAndSchedule)" in source
    assert "window.addEventListener('load', suspendAndSchedule)" in source
    assert "document.addEventListener('visual-explain:stepchange', suspendAndSchedule)" in source
    toggle = source.split("document.addEventListener('toggle'", 1)[1]
    assert "suspendAndSchedule();" in toggle
    assert "finally" in source
    assert "suspendScope(scope)" in source.split("finally", 1)[1]


def test_flow_runtime_draws_every_declaration_with_edge_identity_and_state() -> None:
    source = (
        SKILL / "assets" / "components" / "visual-stage-flow.js"
    ).read_text("utf-8")

    assert "querySelectorAll('[data-connect]')" in source
    assert "non-adjacent" not in source
    assert "adjacent(" not in source
    assert "path.setAttribute('data-ve-semantic-id', semanticId)" in source
    assert "path.classList.add(stateClass)" in source
    assert "ve-seq-spot" in source
    assert "ve-seq-dim" in source
    assert "markerId" in source
    assert "url(#${markerId})" in source


def _production_geometry_cases() -> dict[str, object]:
    source = (
        SKILL / "assets" / "components" / "visual-stage-flow.js"
    ).read_text("utf-8")
    start = source.index("  const pointPair")
    end = source.index("  const warning", start)
    geometry = source[start:end]
    program = geometry + """
const box = (left, top) => ({left, top, right: left + 100, bottom: top + 60, width: 100, height: 60});
const stationBoxes = [
  box(0, 0), box(120, 0), box(240, 0), box(360, 0),
  box(0, 100), box(120, 100), box(240, 100), box(360, 100)
];
const stations = stationBoxes.map((bounds, index) => ({
  id: `node-${index + 1}`,
  getBoundingClientRect: () => bounds
}));
const scope = {
  getBoundingClientRect: () => ({left: 0, top: 0, right: 460, bottom: 160, width: 460, height: 160}),
  querySelectorAll: () => stations
};
const definitions = {
  'same-row-adjacent': [0, 1, 0],
  'same-row-skip': [0, 2, 1],
  'wrap-boundary-adjacent': [3, 4, 3],
  'same-column-cross-row': [0, 4, 4]
};

const samples = (d) => {
  const tokens = d.match(/[MLC]|-?\\d+(?:\\.\\d+)?/g);
  const points = [];
  let index = 0;
  let current;
  while (index < tokens.length) {
    const command = tokens[index++];
    if (command === 'M') {
      current = {x: Number(tokens[index++]), y: Number(tokens[index++])};
      points.push(current);
    } else if (command === 'L') {
      const end = {x: Number(tokens[index++]), y: Number(tokens[index++])};
      for (let step = 1; step <= 40; step += 1) {
        const t = step / 40;
        points.push({x: current.x + (end.x - current.x) * t, y: current.y + (end.y - current.y) * t});
      }
      current = end;
    } else if (command === 'C') {
      const p0 = current;
      const p1 = {x: Number(tokens[index++]), y: Number(tokens[index++])};
      const p2 = {x: Number(tokens[index++]), y: Number(tokens[index++])};
      const p3 = {x: Number(tokens[index++]), y: Number(tokens[index++])};
      for (let step = 1; step <= 100; step += 1) {
        const t = step / 100;
        const u = 1 - t;
        points.push({
          x: u ** 3 * p0.x + 3 * u ** 2 * t * p1.x + 3 * u * t ** 2 * p2.x + t ** 3 * p3.x,
          y: u ** 3 * p0.y + 3 * u ** 2 * t * p1.y + 3 * u * t ** 2 * p2.y + t ** 3 * p3.y
        });
      }
      current = p3;
    }
  }
  return points;
};
const strictlyInside = (point, bounds) => (
  point.x > bounds.left + .01 && point.x < bounds.right - .01
  && point.y > bounds.top + .01 && point.y < bounds.bottom - .01
);

const results = {};
Object.entries(definitions).forEach(([name, [fromIndex, toIndex, declarationIndex]]) => {
  const d = pathFor(stations[fromIndex], stations[toIndex], scope, declarationIndex);
  const points = samples(d);
  results[name] = {
    d,
    hits: stationBoxes.flatMap((bounds, index) => (
      points.some((point) => strictlyInside(point, bounds)) ? [`node-${index + 1}`] : []
    )),
    minX: Math.min(...points.map((point) => point.x)),
    maxX: Math.max(...points.map((point) => point.x)),
    minY: Math.min(...points.map((point) => point.y)),
    maxY: Math.max(...points.map((point) => point.y))
  };
});
process.stdout.write(JSON.stringify(results));
"""

    completed = subprocess.run(
        ["node", "-e", program], capture_output=True, text=True, check=True,
    )
    return json.loads(completed.stdout)


@pytest.mark.parametrize(
    ("case", "axis"),
    [
        ("same-row-adjacent", "horizontal"),
        ("same-row-skip", "outer-horizontal"),
        ("wrap-boundary-adjacent", "outer-wrap"),
        ("same-column-cross-row", "vertical"),
    ],
)
def test_production_path_geometry_avoids_every_station_rectangle(
    case: str, axis: str,
) -> None:
    result = _production_geometry_cases()[case]

    assert result["hits"] == [], f'{case}: {result["d"]}'
    assert result["d"].count(" L ") >= 3, "route must expose endpoint stubs"
    if axis == "horizontal":
        assert (result["minY"], result["maxY"]) == (30, 30)
    elif axis == "outer-horizontal":
        assert result["minY"] < 0 or result["maxY"] > 60
    elif axis == "outer-wrap":
        coordinates = [
            (float(x), float(y))
            for x, y in re.findall(r'[ML] (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)', result["d"])
        ]
        assert any(
            first[1] == second[1] and 60 < first[1] < 100
            for first, second in zip(coordinates, coordinates[1:])
        ), "route must use a horizontal segment in the empty inter-row lane"
    else:
        assert (result["minX"], result["maxX"]) == (50, 50)


def test_flow_runtime_marker_uses_the_actual_edge_path_stroke() -> None:
    source = (
        SKILL / "assets" / "components" / "visual-stage-flow.js"
    ).read_text("utf-8")

    assert "shape.setAttribute('fill', 'context-stroke')" in source


def test_path_scope_and_actual_connector_paths_have_scoped_paint_rules() -> None:
    css = (SKILL / "assets" / "components" / "visual-stage.css").read_text("utf-8")

    assert re.search(
        r'\[data-ve-sequence-mode="path-spotlight"\].*?\.ve-flow-scroll\[data-connect-scope\]\s*\{[^}]*position:\s*relative;',
        css,
        re.DOTALL,
    )
    assert re.search(
        r'\[data-ve-sequence-mode="path-spotlight"\].*?\.ve-flow-scroll\[data-ve-flow-connect-scope\]\s*\{[^}]*position:\s*relative;',
        css,
        re.DOTALL,
    )
    assert re.search(r'\.ve-flow-connector-layer path\.ve-seq-dim\s*\{[^}]*opacity:', css, re.DOTALL)
    spot = re.search(r'\.ve-flow-connector-layer path\.ve-seq-spot\s*\{([^}]*)\}', css, re.DOTALL)
    assert spot is not None
    assert "stroke:" in spot.group(1)
    assert set(re.findall(r'([a-z-]+)\s*:', spot.group(1))) <= {"stroke", "stroke-width", "opacity"}


def test_branched_path_keeps_non_adjacent_skip_edge_for_opt_in_runtime() -> None:
    result = render_flow(_branched_sequence_section(), FLOW_DEF)

    for number in (1, 2, 3):
        panel = _panel(result.markup, number)
        pairs = _connector_pairs(panel)
        assert (f"node-draft--p{number}", f"node-approve--p{number}") in pairs
        assert panel.count('data-ve-semantic-id="edge-') == 4
        assert f'data-connect="node-draft--p{number}-&gt;node-approve--p{number}"' in panel
        if number == 1:
            assert "ve-seq-dim" not in _semantic_classes(panel, "edge-draft-approve")
        else:
            assert "ve-seq-dim" in _semantic_classes(panel, "edge-draft-approve")


def test_path_highlights_current_nodes_with_within_and_bridge_edges_only() -> None:
    markup = render_flow(_sequence_section("path-spotlight"), FLOW_DEF).markup
    panel_two = _panel(markup, 2)
    panel_three = _panel(markup, 3)

    for semantic_id in ("node-draft", "node-review", "edge-draft-review"):
        assert "ve-seq-spot" in _semantic_classes(panel_two, semantic_id)
    for semantic_id in (
        "node-approve", "node-publish", "edge-review-approve", "edge-approve-publish",
    ):
        assert "ve-seq-dim" in _semantic_classes(panel_two, semantic_id)

    for semantic_id in (
        "node-approve", "node-publish", "edge-review-approve", "edge-approve-publish",
    ):
        assert "ve-seq-spot" in _semantic_classes(panel_three, semantic_id)
    for semantic_id in ("node-draft", "node-review", "edge-draft-review"):
        assert "ve-seq-dim" in _semantic_classes(panel_three, semantic_id)


def test_state_lens_reuses_complete_flow_and_spots_current_nodes_only() -> None:
    result = render_flow(_sequence_section("state-lens"), FLOW_DEF)

    assert 'data-ve-sequence-mode="state-lens"' in result.markup
    assert result.script_asset_ids == ()
    panel_two = _panel(result.markup, 2)
    panel_three = _panel(result.markup, 3)
    for panel in (panel_two, panel_three):
        assert panel.count('class="ve-flow-canvas"') == 1
        assert "ve-flow-path-canvas" not in panel
        assert panel.count('data-ve-semantic-id="node-') == 4
        assert panel.count('data-ve-semantic-id="edge-') == 3

    for semantic_id in ("node-draft", "node-review"):
        assert "ve-seq-spot" in _semantic_classes(panel_two, semantic_id)
        assert "ve-seq-dim" in _semantic_classes(panel_three, semantic_id)
    for semantic_id in ("node-approve", "node-publish"):
        assert "ve-seq-dim" in _semantic_classes(panel_two, semantic_id)
        assert "ve-seq-spot" in _semantic_classes(panel_three, semantic_id)
    for edge_id in ("edge-draft-review", "edge-review-approve", "edge-approve-publish"):
        assert "ve-seq-dim" in _semantic_classes(panel_two, edge_id)
        assert "ve-seq-dim" in _semantic_classes(panel_three, edge_id)


@pytest.mark.parametrize("mode", ["path-spotlight", "state-lens"])
def test_overview_panel_is_complete_and_has_no_sequence_highlight(mode: str) -> None:
    section = _sequence_section(mode)
    result = render_flow(section, FLOW_DEF)
    panel = _panel(result.markup, 1)

    assert panel.count('<figure data-ve-component="flow"') == 1
    assert section.ir.caption in panel
    assert section.ir.accessibility.summary in panel
    assert 'class="ve-flow-notes"' in panel
    for semantic_id in section.ir.semantic_ids():
        if semantic_id == section.ir.id:
            continue
        assert f'data-ve-semantic-id="{semantic_id}"' in panel
    assert "ve-seq-spot" not in panel
    assert "ve-seq-dim" not in panel


def test_legacy_flow_remains_byte_exact_and_passes_the_trust_boundary() -> None:
    section = _legacy_section()
    result = render_flow(section, FLOW_DEF)

    assert sha256(result.markup.encode()).hexdigest() == (
        "8991075bc5c9b8d20d8ee6abe86c4b88c47c1e556df55b10e34158db9c976420"
    )
    assert result.style_asset_ids == ("flow.css",)
    assert result.script_asset_ids == ()
    assert result.diagnostics == ()
    resolved = resolve_component(section.ir.selection, REGISTRY)
    rendered = render_canonical(section, resolved)
    assert result.markup in rendered.markup


def test_path_sequence_render_canonical_waits_for_panel_aware_t11() -> None:
    section = _sequence_section("path-spotlight")
    resolved = resolve_component(section.ir.selection, REGISTRY)

    try:
        render_canonical(section, resolved)
    except ContractError as exc:
        assert [diagnostic.message for diagnostic in exc.diagnostics] == [
            "renderer 'flow@2' の flow ノードが IR と不一致です",
            "renderer 'flow@2' の flow 端点/関係が IR と不一致です",
        ]
        pytest.xfail("T11 will normalize panel suffixes in the flow trust check")
