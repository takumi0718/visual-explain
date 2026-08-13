"""Task 14 rendered-sequence and visual-stage CSS contracts."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ve_components.assembly import ExpectedCanonicalRecord
from ve_components.document_checks import (
    check_document_structure,
    check_visual_stage_css,
    check_visual_stage_document_css,
)
from ve_components.model import Assertion, SequenceDeclaration, SequenceStep


ROOT = Path(__file__).resolve().parents[2]
SKELETON = (ROOT / "assets" / "skeleton.html").read_text("utf-8")
VISUAL_STAGE_CSS = (ROOT / "assets" / "components" / "visual-stage.css").read_text("utf-8")


def _record(*, component: str = "flow", mode: str = "state-lens") -> ExpectedCanonicalRecord:
    return ExpectedCanonicalRecord(
        component_id=component,
        instance_id="diagram",
        payload_semantic_ids=frozenset({"node--p9", "desc"}),
        claim="Claim",
        assertions=(Assertion("claim", "Claim", ("node--p9", "desc")),),
        sequence=SequenceDeclaration(mode, (
            SequenceStep("one", "First", ("node--p9",)),
            SequenceStep("two", "Second", ("desc",)),
        )),
    )


def _panel(number: int, *, classes: str = "", text: str = "Body", ref_panel: int | None = None) -> str:
    target_panel = number if ref_panel is None else ref_panel
    class_attr = f' class="node {classes}"' if classes else ' class="node"'
    return (
        f'<div data-step="{number}" aria-current="step">'
        f'<figure id="figure--p{number}">'
        f'<div id="node--p9--p{number}"{class_attr} '
        f'aria-describedby="desc--p{target_panel}">{text}</div>'
        f'<span id="desc--p{number}" tabindex="-1"></span>'
        f'</figure><p class="ve-seq-next">Forecast {number}</p></div>'
    )


def _stepper(
    *,
    panels: tuple[str, ...] | None = None,
    total: str = "3",
    mode: str = "state-lens",
) -> str:
    if panels is None:
        panels = (
            _panel(1),
            _panel(2, classes="ve-seq-spot"),
            _panel(3, classes="ve-seq-dim"),
        )
    return (
        f'<div data-stepper data-ve-sequence-mode="{mode}" data-total-steps="{total}">'
        f'{"".join(panels)}'
        '<div class="ve-stepper-controls">'
        '<button type="button" data-step-action="previous">Prev</button>'
        '<button type="button" data-step-action="next" data-next-label="Next">Next</button>'
        '<button type="button" data-step-action="all">All</button>'
        '</div></div>'
    )


def _content(*, body: str | None = None, claim: str = '<p class="ve-claim">Claim</p>') -> str:
    return (
        '<section data-ve-section-kind="first-screen" data-ve-document-type="proposal" '
        'data-ve-profile="visual-stage"><h1>Title</h1><p class="subtitle">Summary</p></section>'
        '<section data-ve-section-kind="canonical" data-ve-component="flow" '
        f'data-ve-instance="diagram">{claim}{body or _stepper()}</section>'
        '<section data-ve-section-kind="closing"><h2>リスクと弱い前提</h2>'
        '<h2>不確かな点</h2></section>'
    )


def _messages(content: str, expected: tuple[ExpectedCanonicalRecord, ...] = (_record(),)) -> list[str]:
    return [
        item.message
        for item in check_document_structure(content, title="Title", expected=expected)
        if "visual-stage sequence" in item.message
    ]


def test_valid_sequence_accepts_suffix_shaped_base_ids_and_state_only_differences() -> None:
    assert _messages(_content()) == []


@pytest.mark.parametrize(
    ("panels", "needle"),
    (
        ((_panel(1), _panel(2, classes="ve-seq-spot")), "panel 数"),
        ((_panel(1), _panel(3, classes="ve-seq-dim"), _panel(2, classes="ve-seq-spot")), "連番"),
        ((_panel(1), _panel(2, classes="ve-seq-spot"), _panel(3), _panel(4)), "panel 数"),
    ),
)
def test_missing_reordered_and_extra_panels_fail_closed(panels: tuple[str, ...], needle: str) -> None:
    assert any(needle in message for message in _messages(_content(body=_stepper(panels=panels))))


def test_total_steps_and_expected_step_limit_are_rechecked() -> None:
    assert any("data-total-steps" in message for message in _messages(_content(body=_stepper(total="4"))))
    too_many = replace(
        _record(),
        sequence=SequenceDeclaration("state-lens", tuple(
            SequenceStep(f"s-{index}", str(index), ("desc",)) for index in range(9)
        )),
    )
    assert any("8" in message for message in _messages(_content(), (too_many,)))


def test_mode_component_allowtable_and_expected_mode_are_rechecked() -> None:
    invalid = replace(_record(component="bars", mode="path-spotlight"), instance_id="diagram")
    messages = _messages(_content(body=_stepper(mode="path-spotlight")), (invalid,))
    assert any("使用できません" in message for message in messages)


def test_panel_one_must_be_unhighlighted_and_references_must_close_in_same_panel() -> None:
    highlighted = (_panel(1, classes="ve-seq-spot"), _panel(2), _panel(3))
    assert any("panel 1" in message and "強調" in message for message in _messages(
        _content(body=_stepper(panels=highlighted)),
    ))

    cross_ref = (_panel(1), _panel(2, ref_panel=1), _panel(3))
    assert any("同一 panel" in message for message in _messages(
        _content(body=_stepper(panels=cross_ref)),
    ))


def test_unsuffixed_ids_and_dom_drift_are_rejected_after_normalization() -> None:
    unsuffixed = _panel(2).replace('id="desc--p2"', 'id="desc"')
    assert any("--p2" in message for message in _messages(_content(body=_stepper(
        panels=(_panel(1), unsuffixed, _panel(3)),
    ))))

    drifted = _panel(3).replace(">Body</div>", ">Changed</div>")
    assert any("DOM" in message for message in _messages(_content(body=_stepper(
        panels=(_panel(1), _panel(2), drifted),
    ))))


def test_stepper_controls_and_claim_outside_panels_are_exact_contracts() -> None:
    missing_all = _stepper().replace(
        '<button type="button" data-step-action="all">All</button>', "",
    )
    assert any("all" in message for message in _messages(_content(body=missing_all)))

    inside_claim = _stepper().replace(
        '<figure id="figure--p1">', '<p class="ve-claim">Claim</p><figure id="figure--p1">', 1,
    )
    assert any("claim" in message and "panel 外" in message for message in _messages(
        _content(body=inside_claim, claim=""),
    ))

    nested_claim = '<div><p class="ve-claim">Claim</p></div>'
    assert any("直前" in message for message in _messages(
        _content(claim=nested_claim),
    ))

    all_inside_panel = _stepper().replace(
        '<p class="ve-seq-next">Forecast 1</p></div>',
        '<button type="button" data-step-action="all">Nested all</button>'
        '<p class="ve-seq-next">Forecast 1</p></div>',
    ).replace('<button type="button" data-step-action="all">All</button>', "")
    assert any("panel 外" in message and "all" in message for message in _messages(
        _content(body=all_inside_panel),
    ))


def test_real_visual_stage_css_obeys_paint_only_and_width_contract() -> None:
    assert check_visual_stage_css(VISUAL_STAGE_CSS, SKELETON) == []


@pytest.mark.parametrize(
    "declaration",
    (
        "width: 1px",
        "w\\69 dth: 1px",
        "font-size: 2rem",
        "border: 0",
        "transform: none",
    ),
)
def test_css_scanner_rejects_layout_properties_in_compound_nested_highlight_rules(
    declaration: str,
) -> None:
    css = VISUAL_STAGE_CSS + (
        '\n@media (min-width: 1px) { .card:is(.ve-seq-\\73 pot, .other) { '
        f'color: red; {declaration}; content: "width: 3px"; }} }}'
    )
    assert any("paint-only" in item.message for item in check_visual_stage_css(css, SKELETON))


def test_css_scanner_ignores_layout_in_claim_and_path_layout_blocks_and_comments_strings() -> None:
    css = VISUAL_STAGE_CSS + (
        '\n.ve-claim, .ve-flow-path-canvas { width: 100%; display: flex; '
        'content: ".ve-seq-spot { transform: scale(2) }"; '
        '/* .ve-seq-dim { margin: 2rem; } */ }'
    )
    assert check_visual_stage_css(css, SKELETON) == []


def test_width_equation_uses_actual_css_constants_and_skeleton_linked_content_token() -> None:
    too_wide = VISUAL_STAGE_CSS.replace(
        "--ve-path-spotlight-node-width: 10.5rem",
        "--ve-path-spotlight-node-width: 10.5001rem",
    )
    assert any("4W" in item.message for item in check_visual_stage_css(too_wide, SKELETON))

    unlinked = VISUAL_STAGE_CSS.replace(
        "--ve-path-spotlight-content-width: var(--w-narrative)",
        "--ve-path-spotlight-content-width: 45rem",
    )
    assert any("skeleton" in item.message for item in check_visual_stage_css(unlinked, SKELETON))


def test_bad_css_is_not_scanned_for_non_visual_stage_profile() -> None:
    strict = _content().replace('data-ve-profile="visual-stage"', 'data-ve-profile="strict"')
    style = '<style data-ve-asset="visual-stage">.ve-seq-spot { width: 1px; }</style>'
    messages = check_visual_stage_document_css(strict, style, SKELETON)
    assert not any("visual-stage CSS" in item.message for item in messages)
