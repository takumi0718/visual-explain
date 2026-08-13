"""Focused Task 10 contracts for waterfall/bars delta accumulation."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
import re
from pathlib import Path

import pytest

from fixture_util import canonical_ir
from ve_components.model import (
    Assertion,
    CanonicalSection,
    SequenceDeclaration,
    SequenceStep,
)
from ve_components.registry import load_registry
from ve_components.renderers.bars import render_bars
from ve_components.renderers.waterfall import render_waterfall
from ve_components.validation import validate_canonical_section


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
TESTS = SKILL / "scripts" / "tests"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
WATERFALL_DEF = REGISTRY.find("waterfall", 2)
BARS_DEF = REGISTRY.find("bars", 2)


def _legacy_section(fixture_name: str) -> CanonicalSection:
    raw = json.loads((TESTS / fixture_name).read_text("utf-8"))
    return CanonicalSection(ir=validate_canonical_section(canonical_ir(raw)))


def _delta_section(
    fixture_name: str,
    step_targets: tuple[tuple[str, ...], ...],
) -> CanonicalSection:
    section = _legacy_section(fixture_name)
    ir = section.ir
    sequence = SequenceDeclaration(
        mode="delta-accumulate",
        steps=tuple(
            SequenceStep(
                id=f"delta-{index}",
                label=f"差分 {index}",
                target_ids=targets,
            )
            for index, targets in enumerate(step_targets, start=1)
        ),
    )
    claim = "到達済みの定量項目を累積して確認する。"
    return CanonicalSection(ir=replace(
        ir,
        relationship=replace(
            ir.relationship,
            capabilities=ir.relationship.capabilities + ("typed-sequence",),
        ),
        selection=replace(
            ir.selection,
            matched_capabilities=ir.selection.matched_capabilities + ("typed-sequence",),
        ),
        claim=claim,
        sequence=sequence,
        assertions=(Assertion(
            id="delta-meaning",
            text=claim,
            cover_ids=ir.semantic_ids(),
        ),),
    ))


def _panel(markup: str, number: int) -> str:
    start = markup.index(f'<div data-step="{number}">')
    next_panel = f'<div data-step="{number + 1}">'
    if next_panel in markup:
        end = markup.index(next_panel, start)
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


def _semantic_inventory(panel: str) -> tuple[str, ...]:
    return tuple(re.findall(r'data-ve-semantic-id="([^"]+)"', panel))


def test_waterfall_delta_panels_accumulate_only_quantitative_items() -> None:
    section = _delta_section(
        "component-valid-waterfall.json",
        (("wf-start", "wf-step-1"), ("wf-step-3", "wf-end")),
    )
    result = render_waterfall(section, WATERFALL_DEF)
    panel_two = _panel(result.markup, 2)
    panel_three = _panel(result.markup, 3)

    for item_id in ("wf-start", "wf-step-1"):
        assert "ve-seq-spot" in _semantic_classes(panel_two, item_id)
        assert "ve-seq-spot" in _semantic_classes(panel_three, item_id)
    for item_id in ("wf-step-3", "wf-end"):
        assert "ve-seq-dim" in _semantic_classes(panel_two, item_id)
        assert "ve-seq-spot" in _semantic_classes(panel_three, item_id)
    for item_id in ("wf-step-2", "wf-step-4"):
        assert "ve-seq-dim" in _semantic_classes(panel_two, item_id)
        assert "ve-seq-dim" in _semantic_classes(panel_three, item_id)
    for note_id in ("cert-wf", "src-wf"):
        assert not ({"ve-seq-spot", "ve-seq-dim"} & _semantic_classes(panel_two, note_id))
        assert not ({"ve-seq-spot", "ve-seq-dim"} & _semantic_classes(panel_three, note_id))


def test_bars_delta_panels_accumulate_instead_of_replacing_prior_items() -> None:
    section = _delta_section(
        "component-valid-bars.json",
        (("b1",), ("b2",)),
    )
    result = render_bars(section, BARS_DEF)
    panel_two = _panel(result.markup, 2)
    panel_three = _panel(result.markup, 3)

    assert "ve-seq-spot" in _semantic_classes(panel_two, "b1")
    assert "ve-seq-dim" in _semantic_classes(panel_two, "b2")
    assert "ve-seq-spot" in _semantic_classes(panel_three, "b1")
    assert "ve-seq-spot" in _semantic_classes(panel_three, "b2")
    for note_id in ("cert-bars", "src-bars"):
        assert not ({"ve-seq-spot", "ve-seq-dim"} & _semantic_classes(panel_two, note_id))
        assert not ({"ve-seq-spot", "ve-seq-dim"} & _semantic_classes(panel_three, note_id))


@pytest.mark.parametrize(
    ("fixture_name", "component_id", "renderer", "definition", "targets", "inventory"),
    [
        (
            "component-valid-waterfall.json",
            "waterfall",
            render_waterfall,
            WATERFALL_DEF,
            (("wf-start", "wf-step-1"), ("wf-step-3", "wf-end")),
            (
                "wf-start", "wf-step-1", "wf-step-2", "wf-step-3", "wf-step-4", "wf-end",
                "cert-wf", "src-wf",
            ),
        ),
        (
            "component-valid-bars.json",
            "bars",
            render_bars,
            BARS_DEF,
            (("b1",), ("b2",)),
            ("b1", "b2", "cert-bars", "src-bars"),
        ),
    ],
)
def test_delta_panels_keep_complete_semantic_inventory_and_one_shared_claim(
    fixture_name: str,
    component_id: str,
    renderer,
    definition,
    targets: tuple[tuple[str, ...], ...],
    inventory: tuple[str, ...],
) -> None:
    section = _delta_section(fixture_name, targets)
    result = renderer(section, definition)

    assert result.markup.startswith(
        '<p class="ve-claim">到達済みの定量項目を累積して確認する。</p>'
        '<div data-stepper data-ve-sequence-mode="delta-accumulate" data-total-steps="3">'
    )
    assert result.markup.count('class="ve-claim"') == 1
    for number in (1, 2, 3):
        panel = _panel(result.markup, number)
        assert panel.count(f'<figure data-ve-component="{component_id}"') == 1
        assert _semantic_inventory(panel) == inventory
        assert "ve-claim" not in panel

    overview = _panel(result.markup, 1)
    assert "ve-seq-spot" not in overview
    assert "ve-seq-dim" not in overview
    assert result.style_asset_ids == (f"{component_id}.css", "visual-stage")
    assert result.script_asset_ids == ()
    assert result.manifest.consumed_semantic_ids == section.ir.semantic_ids()


def test_waterfall_delta_panels_preserve_svg_totals_connectors_and_manifest_suffixes() -> None:
    section = _delta_section(
        "component-valid-waterfall.json",
        (("wf-start", "wf-step-1"), ("wf-step-3", "wf-end")),
    )
    result = render_waterfall(section, WATERFALL_DEF)

    for number in (1, 2, 3):
        panel = _panel(result.markup, number)
        assert panel.count('class="ve-wf-bar ve-wf-total"') == 2
        assert panel.count('class="ve-wf-connector"') == 5
        assert 'class="ve-wf-bar ve-wf-minus"' in panel
        assert 'class="ve-wf-bar ve-wf-minus-soft"' in panel
    assert result.manifest.generated_landmark_ids == tuple(
        f"sec-waterfall-{kind}--p{number}"
        for number in (1, 2, 3)
        for kind in ("caption", "summary", "svg")
    )
    assert result.manifest.svg_root_ids == tuple(
        f"sec-waterfall-svg--p{number}" for number in (1, 2, 3)
    )


def test_bars_delta_panels_preserve_widths_highlight_and_manifest_suffixes() -> None:
    section = _delta_section("component-valid-bars.json", (("b1",), ("b2",)))
    result = render_bars(section, BARS_DEF)

    for number in (1, 2, 3):
        panel = _panel(result.markup, number)
        assert panel.count("ve-bars-w-100") == 1
        assert panel.count("ve-bars-w-17") == 1
        assert panel.count("ve-dg-highlight") == 1
    assert result.manifest.generated_landmark_ids == tuple(
        f"sec-bars-{kind}--p{number}"
        for number in (1, 2, 3)
        for kind in ("caption", "summary")
    )


@pytest.mark.parametrize(
    ("fixture_name", "renderer", "definition", "expected_sha256"),
    [
        (
            "component-valid-waterfall.json",
            render_waterfall,
            WATERFALL_DEF,
            "9a55aed897e794504bd76f4253eb57ef72046ad7338d2ec822f346d81df49ab9",
        ),
        (
            "component-valid-bars.json",
            render_bars,
            BARS_DEF,
            "9c8998f00bf3457b2b6a9a2331d211bdb21413cb85f99f01f46c84f729da2d3b",
        ),
    ],
)
def test_legacy_rendering_remains_byte_exact(
    fixture_name: str,
    renderer,
    definition,
    expected_sha256: str,
) -> None:
    result = renderer(_legacy_section(fixture_name), definition)

    assert sha256(result.markup.encode()).hexdigest() == expected_sha256
    assert "data-stepper" not in result.markup
    assert "ve-seq-spot" not in result.markup
    assert "ve-seq-dim" not in result.markup
