"""Task 15 integration coverage for every allowed visual-stage sequence pairing."""
from __future__ import annotations

from copy import deepcopy
from html.parser import HTMLParser
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from build_explainer import build_document
from fixture_util import canonical_ir
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
TESTS = SKILL / "scripts" / "tests"
FIXTURES = TESTS / "fixtures"
COMPONENTS = SKILL / "assets" / "components"
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
REGISTRY = load_registry(COMPONENTS / "registry.json")
BUILD = SKILL / "scripts" / "build_explainer.py"
CHECK = SKILL / "scripts" / "check.sh"


@dataclass
class _Element:
    tag: str
    attrs: dict[str, str]
    parent: "_Element | None" = None
    children: list["_Element"] = field(default_factory=list)

    @property
    def classes(self) -> frozenset[str]:
        return frozenset(self.attrs.get("class", "").split())

    def descendants(self) -> list["_Element"]:
        found: list[_Element] = []
        for child in self.children:
            found.append(child)
            found.extend(child.descendants())
        return found


class _TreeParser(HTMLParser):
    _VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Element("document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = _Element(tag, {key: value or "" for key, value in attrs}, self.stack[-1])
        self.stack[-1].children.append(element)
        if tag not in self._VOID:
            self.stack.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self._VOID:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return


SEQUENCE_CASES = {
    "vs-flow-path-spotlight.assembly.json": {
        "component": "flow",
        "mode": "path-spotlight",
        "eligible": {
            "node-draft", "node-review", "node-approve", "node-publish",
            "edge-draft-review", "edge-review-approve", "edge-approve-publish",
            "edge-draft-approve",
        },
        "spots": (
            {"node-draft", "node-review", "edge-draft-review"},
            {"node-approve", "node-publish", "edge-review-approve", "edge-approve-publish"},
        ),
    },
    "vs-flow-state-lens.assembly.json": {
        "component": "flow",
        "mode": "state-lens",
        "eligible": {
            "node-draft", "node-review", "node-approve", "node-publish",
            "edge-draft-review", "edge-review-approve", "edge-approve-publish",
        },
        "spots": (
            {"node-draft", "node-review"},
            {"node-publish"},
        ),
    },
    "vs-matrix-state-lens.assembly.json": {
        "component": "matrix",
        "mode": "state-lens",
        "eligible": {"cell-admin-read", "cell-admin-write", "cell-viewer-read", "cell-viewer-write"},
        "spots": (
            {"cell-admin-read", "cell-admin-write"},
            {"cell-viewer-write"},
        ),
    },
    "vs-stairs-state-lens.assembly.json": {
        "component": "stairs",
        "mode": "state-lens",
        "eligible": {"stage-1", "stage-2", "stage-3", "stage-4", "stage-5"},
        "spots": (
            {"stage-1", "stage-2"},
            {"stage-4"},
        ),
    },
    "vs-waterfall-delta-accumulate.assembly.json": {
        "component": "waterfall",
        "mode": "delta-accumulate",
        "eligible": {"wf-start", "wf-step-1", "wf-step-2", "wf-step-3", "wf-step-4", "wf-end"},
        "spots": (
            {"wf-start", "wf-step-1"},
            {"wf-start", "wf-step-1", "wf-step-3", "wf-end"},
        ),
    },
    "vs-bars-delta-accumulate.assembly.json": {
        "component": "bars",
        "mode": "delta-accumulate",
        "eligible": {"b1", "b2"},
        "spots": (
            {"b1"},
            {"b1", "b2"},
        ),
    },
}


CLAIM_ONLY_SOURCES = {
    "matrix": "component-valid-matrix.json",
    "flow": "component-valid-flow.json",
    "enumeration": "component-valid-enumeration.json",
    "chevron": "component-valid-chevron.json",
    "pyramid": "component-valid-pyramid.json",
    "stairs": "component-valid-stairs.json",
    "logic-tree": "component-valid-logic-tree.json",
    "waterfall": "component-valid-waterfall.json",
    "slope": "component-valid-slope.json",
    "evidence-map": "component-valid-evidence-map.json",
    "bars": "component-valid-bars.json",
    "kpi": "component-valid-kpi.json",
}

PAYLOAD_KEYS = {
    "matrix": "matrix",
    "flow": "flow",
    "enumeration": "enumeration",
    "chevron": "chevron",
    "pyramid": "pyramid",
    "stairs": "stairs",
    "logic-tree": "logic-tree",
    "waterfall": "waterfall",
    "slope": "slope",
    "evidence-map": "evidence-map",
    "bars": "bars",
    "kpi": "kpi",
}


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text("utf-8"))


def _render(raw: dict, document_path: str = "visual-stage.html") -> str:
    return build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS, document_path=document_path)


def _tree(html: str) -> _Element:
    parser = _TreeParser()
    parser.feed(html)
    parser.close()
    return parser.root


def _canonical(root: _Element, instance_id: str) -> _Element:
    matches = [
        node for node in root.descendants()
        if node.attrs.get("data-ve-section-kind") == "canonical"
        and node.attrs.get("data-ve-instance") == instance_id
    ]
    assert len(matches) == 1
    return matches[0]


def _semantic_state(panel: _Element, state_class: str) -> set[str]:
    return {
        node.attrs["data-ve-semantic-id"]
        for node in panel.descendants()
        if "data-ve-semantic-id" in node.attrs and state_class in node.classes
    }


def _assert_panel_semantics(
    panel: _Element,
    eligible: set[str],
    expected_spot: set[str],
) -> None:
    actual_spot = _semantic_state(panel, "ve-seq-spot")
    actual_dim = _semantic_state(panel, "ve-seq-dim")
    assert actual_spot == expected_spot
    assert actual_dim == eligible - expected_spot
    assert not actual_spot & actual_dim
    for node in panel.descendants():
        semantic_id = node.attrs.get("data-ve-semantic-id")
        if semantic_id is not None and semantic_id not in eligible:
            assert not ({"ve-seq-spot", "ve-seq-dim"} & node.classes)


def test_flow_state_lens_uses_panel_local_refs_without_changing_semantic_ids() -> None:
    raw = _load_fixture("vs-flow-state-lens.assembly.json")
    html = _render(raw, "vs-flow-state-lens.html")
    section = _canonical(_tree(html), canonical_ir(raw)["id"])
    stepper = next(node for node in section.children if "data-stepper" in node.attrs)
    panels = [node for node in stepper.children if "data-step" in node.attrs]

    for number, panel in enumerate(panels, start=1):
        nodes = [
            node for node in panel.descendants()
            if node.attrs.get("data-ve-semantic-id", "").startswith("node-")
        ]
        assert {node.attrs["data-ve-semantic-id"] for node in nodes} == {
            "node-draft", "node-review", "node-approve", "node-publish",
        }
        stations = [node.parent for node in nodes]
        assert all(station is not None for station in stations)
        assert {station.attrs.get("id") for station in stations if station is not None} == {
            f"node-draft--p{number}", f"node-review--p{number}",
            f"node-approve--p{number}", f"node-publish--p{number}",
        }
        edges = [
            node for node in panel.descendants()
            if node.attrs.get("data-ve-semantic-id", "").startswith("edge-")
        ]
        assert {(edge.attrs["data-ve-from"], edge.attrs["data-ve-to"]) for edge in edges} == {
            (f"node-draft--p{number}", f"node-review--p{number}"),
            (f"node-review--p{number}", f"node-approve--p{number}"),
            (f"node-approve--p{number}", f"node-publish--p{number}"),
        }


def test_sequence_semantics_reject_highlight_classes_on_noneligible_notes() -> None:
    raw = _load_fixture("vs-flow-state-lens.assembly.json")
    html = _render(raw, "vs-flow-state-lens.html")
    section = _canonical(_tree(html), canonical_ir(raw)["id"])
    stepper = next(node for node in section.children if "data-stepper" in node.attrs)
    panels = [node for node in stepper.children if "data-step" in node.attrs]
    case = SEQUENCE_CASES["vs-flow-state-lens.assembly.json"]

    for panel, expected_spot in zip(panels[1:], case["spots"]):
        certainty = next(
            node for node in panel.descendants()
            if node.attrs.get("data-ve-semantic-id") == "flow-state-cert"
        )
        certainty.attrs["class"] = f'{certainty.attrs.get("class", "")} ve-seq-spot'.strip()
        with pytest.raises(AssertionError):
            _assert_panel_semantics(panel, case["eligible"], expected_spot)


@pytest.mark.parametrize("fixture_name", SEQUENCE_CASES)
def test_sequence_fixtures_build_and_pass_the_real_checker_cli(
    fixture_name: str, tmp_path: Path,
) -> None:
    output = tmp_path / f"{Path(fixture_name).stem}.html"
    built = subprocess.run(
        ["python3", str(BUILD), "--assembly", str(FIXTURES / fixture_name), "--output", str(output)],
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stderr
    assert output.is_file()

    checked = subprocess.run(["bash", str(CHECK), str(output)], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert "PASS" in checked.stdout


@pytest.mark.parametrize(("fixture_name", "case"), SEQUENCE_CASES.items())
def test_sequence_fixture_panels_have_exact_mode_semantics(
    fixture_name: str, case: dict,
) -> None:
    raw = _load_fixture(fixture_name)
    ir = canonical_ir(raw)
    html = _render(raw, fixture_name.removesuffix(".assembly.json") + ".html")
    section = _canonical(_tree(html), ir["id"])
    direct = section.children

    claims = [node for node in direct if "ve-claim" in node.classes]
    steppers = [node for node in direct if "data-stepper" in node.attrs]
    assert len(claims) == 1
    assert len(steppers) == 1
    assert direct.index(claims[0]) + 1 == direct.index(steppers[0])
    assert not [node for node in steppers[0].descendants() if "ve-claim" in node.classes]
    assert steppers[0].attrs["data-ve-sequence-mode"] == case["mode"]
    assert steppers[0].attrs["data-total-steps"] == "3"
    controls = {
        node.attrs.get("data-step-action")
        for node in steppers[0].descendants()
        if "data-step-action" in node.attrs
    }
    assert controls == {"previous", "next", "all"}

    panels = [node for node in steppers[0].children if "data-step" in node.attrs]
    assert [panel.attrs["data-step"] for panel in panels] == ["1", "2", "3"]
    overview_ids = {
        node.attrs["data-ve-semantic-id"]
        for node in panels[0].descendants()
        if "data-ve-semantic-id" in node.attrs
    }
    expected_payload_ids = {
        value
        for obj in _walk_dicts(ir)
        if isinstance((value := obj.get("id")), str)
    } - {ir["id"]} - {step["id"] for step in ir["sequence"]["steps"]} - {
        assertion["id"] for assertion in ir["assertions"]
    }
    assert expected_payload_ids <= overview_ids
    assert not _semantic_state(panels[0], "ve-seq-spot")
    assert not _semantic_state(panels[0], "ve-seq-dim")

    for panel_number, panel in enumerate(panels, start=1):
        figures = [
            node for node in panel.descendants()
            if node.attrs.get("data-ve-component") == case["component"]
        ]
        assert len(figures) == 1
        ids = [node.attrs["id"] for node in panel.descendants() if "id" in node.attrs]
        assert ids
        assert all(dom_id.endswith(f"--p{panel_number}") for dom_id in ids)

    for panel_number, (panel, expected_spot) in enumerate(zip(panels[1:], case["spots"]), start=2):
        _assert_panel_semantics(panel, case["eligible"], expected_spot)

    assert html.count('data-ve-asset="visual-stage"') == 1
    assert html.count(f'data-ve-asset="{case["component"]}.css"') == 1
    expected_runtime_count = int(case["mode"] == "path-spotlight")
    assert html.count('data-ve-asset="visual-stage-flow"') == expected_runtime_count


def _walk_dicts(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _claim_only(component: str, fixture_name: str) -> tuple[dict, str]:
    raw = deepcopy(json.loads((TESTS / fixture_name).read_text("utf-8")))
    raw["document"]["profile"] = "visual-stage"
    ir = canonical_ir(raw)
    assert ir["selection"]["component"] == component
    ir.pop("takeawayTargetIds", None)
    ir.pop("takeawayScope", None)
    ir.pop("emphasis", None)
    claim = f"{component} の全情報を一つの図で確認する。"
    cover_ids = sorted(
        value
        for obj in _walk_dicts(ir[PAYLOAD_KEYS[component]])
        if isinstance((value := obj.get("id")), str)
    )
    ir["claim"] = claim
    ir["assertions"] = [{"id": f"claim-{component}", "text": claim, "coverIds": cover_ids}]
    return raw, ir["id"]


@pytest.mark.parametrize(("component", "fixture_name"), CLAIM_ONLY_SOURCES.items())
def test_claim_only_visual_stage_uses_one_leading_claim_for_all_renderers(
    component: str, fixture_name: str,
) -> None:
    raw, instance_id = _claim_only(component, fixture_name)
    html = _render(raw, f"claim-only-{component}.html")
    section = _canonical(_tree(html), instance_id)
    direct = section.children

    assert len([node for node in section.descendants() if "ve-claim" in node.classes]) == 1
    assert direct[0].tag == "p"
    assert "ve-claim" in direct[0].classes
    assert direct[1].tag == "figure"
    assert direct[1].attrs.get("data-ve-component") == component
    assert not [node for node in section.descendants() if "data-stepper" in node.attrs]
    assert html.count('data-ve-asset="visual-stage"') == 1
    assert html.count(f'data-ve-asset="{component}.css"') == 1
    assert 'data-ve-asset="visual-stage-flow"' not in html
