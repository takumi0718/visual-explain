"""Focused Task 9 contracts for matrix/stairs state-lens rendering."""
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
from ve_components.renderers.matrix import render_matrix
from ve_components.renderers.stairs import render_stairs
from ve_components.validation import validate_canonical_section


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
TESTS = SKILL / "scripts" / "tests"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
MATRIX_DEF = REGISTRY.find("matrix", 2)
STAIRS_DEF = REGISTRY.find("stairs", 2)


def _legacy_section(fixture_name: str) -> CanonicalSection:
    raw = json.loads((TESTS / fixture_name).read_text("utf-8"))
    return CanonicalSection(ir=validate_canonical_section(canonical_ir(raw)))


def _state_lens_section(
    fixture_name: str,
    step_targets: tuple[tuple[str, ...], ...],
) -> CanonicalSection:
    section = _legacy_section(fixture_name)
    ir = section.ir
    sequence = SequenceDeclaration(
        mode="state-lens",
        steps=tuple(
            SequenceStep(
                id=f"lens-{index}",
                label=f"状態 {index}",
                target_ids=targets,
            )
            for index, targets in enumerate(step_targets, start=1)
        ),
    )
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
        claim="現在の対象だけを同一図上で確認する。",
        sequence=sequence,
        assertions=(Assertion(
            id="state-lens-meaning",
            text="現在の対象だけを同一図上で確認する。",
            cover_ids=tuple(target for targets in step_targets for target in targets),
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


def test_matrix_state_lens_spots_only_current_cells_without_accumulating() -> None:
    section = _state_lens_section(
        "component-valid-matrix.json",
        (("cell-admin-read", "cell-admin-write"), ("cell-viewer-write",)),
    )
    result = render_matrix(section, MATRIX_DEF)
    panel_two = _panel(result.markup, 2)
    panel_three = _panel(result.markup, 3)

    for cell_id in ("cell-admin-read", "cell-admin-write"):
        assert "ve-seq-spot" in _semantic_classes(panel_two, cell_id)
        assert "ve-seq-dim" in _semantic_classes(panel_three, cell_id)
    assert "ve-seq-dim" in _semantic_classes(panel_two, "cell-viewer-write")
    assert "ve-seq-spot" in _semantic_classes(panel_three, "cell-viewer-write")
    assert "ve-seq-dim" in _semantic_classes(panel_two, "cell-viewer-read")
    assert "ve-seq-dim" in _semantic_classes(panel_three, "cell-viewer-read")

    for axis_id in ("row-admin", "row-viewer", "col-read", "col-write"):
        assert not ({"ve-seq-spot", "ve-seq-dim"} & _semantic_classes(panel_two, axis_id))


def test_concept_matrix_state_lens_uses_the_same_cell_only_semantics() -> None:
    section = _state_lens_section(
        "component-valid-matrix-concept.json",
        (("cell-admin-read",), ("cell-viewer-write",)),
    )
    result = render_matrix(section, MATRIX_DEF)
    panel_two = _panel(result.markup, 2)
    panel_three = _panel(result.markup, 3)

    assert {"ve-mx-cell", "ve-seq-spot"} <= _semantic_classes(
        panel_two, "cell-admin-read",
    )
    assert {"ve-mx-cell", "ve-seq-dim"} <= _semantic_classes(
        panel_three, "cell-admin-read",
    )
    assert {"ve-mx-cell", "ve-seq-dim"} <= _semantic_classes(
        panel_two, "cell-viewer-write",
    )
    assert {"ve-mx-cell", "ve-seq-spot"} <= _semantic_classes(
        panel_three, "cell-viewer-write",
    )


def test_stairs_state_lens_spots_only_current_stages_without_accumulating() -> None:
    section = _state_lens_section(
        "component-valid-stairs.json",
        (("stage-1", "stage-2"), ("stage-4",)),
    )
    result = render_stairs(section, STAIRS_DEF)
    panel_two = _panel(result.markup, 2)
    panel_three = _panel(result.markup, 3)

    for stage_id in ("stage-1", "stage-2"):
        assert "ve-seq-spot" in _semantic_classes(panel_two, stage_id)
        assert "ve-seq-dim" in _semantic_classes(panel_three, stage_id)
    assert "ve-seq-dim" in _semantic_classes(panel_two, "stage-4")
    assert "ve-seq-spot" in _semantic_classes(panel_three, "stage-4")
    for stage_id in ("stage-3", "stage-5"):
        assert "ve-seq-dim" in _semantic_classes(panel_two, stage_id)
        assert "ve-seq-dim" in _semantic_classes(panel_three, stage_id)


@pytest.mark.parametrize(
    ("fixture_name", "component_id", "renderer", "definition", "item_ids"),
    [
        (
            "component-valid-matrix.json",
            "matrix",
            render_matrix,
            MATRIX_DEF,
            ("cell-admin-read", "cell-admin-write", "cell-viewer-read", "cell-viewer-write"),
        ),
        (
            "component-valid-stairs.json",
            "stairs",
            render_stairs,
            STAIRS_DEF,
            ("stage-1", "stage-2", "stage-3", "stage-4", "stage-5"),
        ),
    ],
)
def test_state_lens_panels_are_complete_instances_with_one_shared_claim(
    fixture_name: str,
    component_id: str,
    renderer,
    definition,
    item_ids: tuple[str, ...],
) -> None:
    section = _state_lens_section(fixture_name, ((item_ids[0],), (item_ids[-1],)))
    result = renderer(section, definition)

    assert result.markup.startswith(
        '<p class="ve-claim">現在の対象だけを同一図上で確認する。</p>'
        '<div data-stepper data-ve-sequence-mode="state-lens" data-total-steps="3">'
    )
    assert result.markup.count('class="ve-claim"') == 1
    for number in (1, 2, 3):
        panel = _panel(result.markup, number)
        assert panel.count(f'<figure data-ve-component="{component_id}"') == 1
        assert "ve-claim" not in panel
        for item_id in item_ids:
            assert f'data-ve-semantic-id="{item_id}"' in panel

    overview = _panel(result.markup, 1)
    assert "ve-seq-spot" not in overview
    assert "ve-seq-dim" not in overview
    assert result.style_asset_ids == (f"{component_id}.css", "visual-stage")
    assert result.script_asset_ids == ()
    assert result.manifest.consumed_semantic_ids == section.ir.semantic_ids()
    assert result.manifest.generated_landmark_ids == tuple(
        f"{section.ir.id}-{kind}--p{number}"
        for number in (1, 2, 3)
        for kind in ("caption", "summary")
    )


@pytest.mark.parametrize(
    ("fixture_name", "renderer", "definition", "expected_sha256"),
    [
        (
            "component-valid-matrix.json",
            render_matrix,
            MATRIX_DEF,
            "8a7a5aad2b2127dd0cbeabc6812323c61cf0de4178324c9e156de59614ea12ef",
        ),
        (
            "component-valid-stairs.json",
            render_stairs,
            STAIRS_DEF,
            "dfae19ac36f2decc2ec5214346f3da9a5923194893e068930e4919cc369d5b89",
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
