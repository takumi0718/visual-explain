"""Focused Task 8 contracts for flow sequence rendering."""
from __future__ import annotations

from hashlib import sha256
import html
import json
import re
from pathlib import Path

import pytest

from fixture_util import canonical_ir
from ve_components.assembly import render_canonical
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


@pytest.mark.xfail(
    strict=True,
    reason="T11 will normalize panel suffixes in render_canonical's flow trust check",
)
def test_path_sequence_render_canonical_waits_for_panel_aware_t11() -> None:
    section = _sequence_section("path-spotlight")
    resolved = resolve_component(section.ir.selection, REGISTRY)

    render_canonical(section, resolved)
