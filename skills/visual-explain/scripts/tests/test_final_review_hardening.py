"""Regression contracts from the final whole-branch review."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from build_explainer import build_document
from ve_components.checker import check_final_document
from ve_components.diagnostics import ContractError
from ve_components.document_checks import _parse_dom_tree, check_visual_stage_css
from ve_components.model import CanonicalSection
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.renderers.flow import _path_edge_ids
from ve_components.validation import validate_assembly


ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = ROOT / "assets" / "components"
SKELETON = (ROOT / "assets" / "skeleton.html").read_text("utf-8")
VISUAL_STAGE_CSS = (COMPONENTS / "visual-stage.css").read_text("utf-8")
REGISTRY = load_registry(COMPONENTS / "registry.json")


def _flow_document() -> str:
    raw = json.loads(
        (Path(__file__).parent / "fixtures" / "vs-flow-path-spotlight.assembly.json")
        .read_text("utf-8")
    )
    return build_document(
        raw,
        REGISTRY,
        TRUSTED_RENDERERS,
        SKELETON,
        COMPONENTS,
        document_path="final-review-hardening.html",
    )


@pytest.mark.parametrize(
    "mutate",
    (
        lambda document: document.replace(
            'data-step="1"', 'data-step="99" DATA-STEP="1"', 1,
        ),
        lambda document: document.replace(
            '<div data-stepper data-ve-sequence-mode="path-spotlight"',
            '<div data-stepper data-ve-sequence-mode="invalid" '
            'DATA-VE-SEQUENCE-MODE="path-spotlight"',
            1,
        ),
        lambda document: document.replace(
            'class="ve-flow-node"',
            'class="ve-flow-node ve-seq-spot" CLASS="ve-flow-node"',
            1,
        ),
        lambda document: document.replace(
            'data-total-steps="3"',
            'data-total-steps="99" DATA-TOTAL-STEPS="3"',
            1,
        ),
        lambda document: document.replace(
            '<div data-step="1">',
            '<input id="browser-first" ID="checker-last"/><div data-step="1">',
            1,
        ),
    ),
)
def test_full_checker_rejects_case_insensitive_duplicate_html_attributes(mutate) -> None:
    document = mutate(_flow_document())

    diagnostics = check_final_document(
        document, SKELETON, REGISTRY, components_dir=COMPONENTS,
    )

    assert any("重複属性" in item.message for item in diagnostics)


def test_both_document_parsers_record_duplicates_before_attribute_mapping() -> None:
    root = _parse_dom_tree(
        '<div data-step="99" DATA-STEP="1" class="ve-seq-spot" CLASS="plain"></div>'
    )
    assert root.duplicate_attributes == [("div", "data-step"), ("div", "class")]

    self_closed = _parse_dom_tree('<input id="browser-first" ID="checker-last"/>')
    assert self_closed.duplicate_attributes == [("input", "id")]

    clean = _parse_dom_tree('<div data-step="1" class="ve-seq-spot plain"></div>')
    assert clean.duplicate_attributes == []


def test_css_parser_rejects_modern_nested_qualified_rules() -> None:
    css = VISUAL_STAGE_CSS + (
        '\n[data-stepper] { & .ve-seq-spot { width: 1px; } }'
    )

    assert any("nested" in item.message.lower() for item in check_visual_stage_css(css, SKELETON))


def test_css_nested_rule_guard_ignores_comments_strings_and_custom_property_blocks() -> None:
    css = VISUAL_STAGE_CSS + r'''
      @media (min-width: 1px) { .ordinary { color: red; } }
      .ordinary {
        content: "& .ve-seq-spot { width: 1px; }";
        --structured-value: { color: red; nested: { width: 1px; }; };
        /* & .ve-seq-spot { width: 1px; } */
      }
    '''

    assert check_visual_stage_css(css, SKELETON) == []


@pytest.mark.parametrize(
    "mutation",
    (
        lambda css: css.replace("overflow-wrap: anywhere", "overflow-wrap: normal", 1),
        lambda css: css + (
            '\n[data-stepper][data-ve-sequence-mode="path-spotlight"] '
            '[data-ve-component="flow"] .ve-flow-node { white-space: nowrap; }'
        ),
        lambda css: css + '\n.ve-flow-path-canvas .ve-flow-node { word-break: keep-all; }',
        lambda css: css + '\n.ve-flow-node { overflow-wrap: break-word !important; }',
    ),
)
def test_path_node_wrapping_contract_rejects_missing_or_competing_sources(mutation) -> None:
    assert any(
        "wrapping" in item.message.lower()
        for item in check_visual_stage_css(mutation(VISUAL_STAGE_CSS), SKELETON)
    )


def test_path_node_wrapping_contract_does_not_reject_unrelated_white_space_rules() -> None:
    css = VISUAL_STAGE_CSS + (
        "\n.certainty { white-space: nowrap; }"
        "\nbody .certainty { white-space: nowrap; }"
        "\n[data-stepper] .ve-seq-next { white-space: nowrap; }"
    )
    assert check_visual_stage_css(css, SKELETON) == []


def test_path_node_wrapping_contract_rejects_inherited_skeleton_nowrap() -> None:
    skeleton = SKELETON.replace(
        "section { min-width: 0;",
        "section { white-space: nowrap; min-width: 0;",
        1,
    )
    assert any(
        "wrapping" in item.message.lower()
        for item in check_visual_stage_css(VISUAL_STAGE_CSS, skeleton)
    )


def _invalid_assertion_error() -> ContractError:
    raw = json.loads(
        (Path(__file__).parent / "fixtures" / "vs-flow-state-lens.assembly.json")
        .read_text("utf-8")
    )
    canonical = raw["sections"][1]["ir"]
    canonical["assertions"] = [
        {
            "id": f"INVALID-{index}-" + "x" * 5000,
            "text": "",
            "coverIds": [f"missing-{index}-" + "y" * 5000],
        }
        for index in range(100)
    ]
    with pytest.raises(ContractError) as caught:
        validate_assembly(raw)
    return caught.value


def test_validation_diagnostics_and_exception_text_are_globally_bounded() -> None:
    first = _invalid_assertion_error()
    second = _invalid_assertion_error()

    assert first.diagnostics == second.diagnostics
    assert len(first.diagnostics) <= 32
    assert any("省略" in item.message for item in first.diagnostics)
    assert max(len(item.message) for item in first.diagnostics) <= 384
    assert max(len(item.path) for item in first.diagnostics) <= 384
    assert len(str(first)) <= 16384


def test_path_edge_derivation_fails_closed_when_a_required_pair_is_absent() -> None:
    raw = json.loads(
        (Path(__file__).parent / "fixtures" / "vs-flow-path-spotlight.assembly.json")
        .read_text("utf-8")
    )
    request = validate_assembly(raw)
    section = request.sections[1]
    assert isinstance(section, CanonicalSection)
    flow = section.ir.flow
    sequence = section.ir.sequence
    assert flow is not None and sequence is not None
    missing = replace(
        flow,
        edges=tuple(edge for edge in flow.edges if edge.id != "edge-draft-review"),
    )

    with pytest.raises(ContractError) as caught:
        _path_edge_ids(missing, sequence, 0)

    assert "edge-draft-review" not in str(caught.value)
    assert "node-draft" in str(caught.value)
    assert "node-review" in str(caught.value)
