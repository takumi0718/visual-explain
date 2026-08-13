"""Task 14 rendered-sequence and visual-stage CSS contracts."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from build_explainer import build_document
from ve_components.assembly import ExpectedCanonicalRecord
from ve_components.checker import check_final_document
from ve_components.document_checks import (
    check_document_structure,
    check_visual_stage_css,
    check_visual_stage_document_css,
)
from ve_components.model import Assertion, SequenceDeclaration, SequenceStep
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS


ROOT = Path(__file__).resolve().parents[2]
SKELETON = (ROOT / "assets" / "skeleton.html").read_text("utf-8")
VISUAL_STAGE_CSS = (ROOT / "assets" / "components" / "visual-stage.css").read_text("utf-8")
COMPONENTS = ROOT / "assets" / "components"
REGISTRY = load_registry(COMPONENTS / "registry.json")


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


def test_css_scanner_ignores_claim_and_non_sizing_path_blocks_comments_and_strings() -> None:
    css = VISUAL_STAGE_CSS + (
        '\n.ve-claim { width: 100%; display: flex; '
        'content: ".ve-seq-spot { transform: scale(2) }"; } '
        '.ordinary .ve-flow-path-canvas { overflow-wrap: anywhere; '
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


@pytest.mark.parametrize(
    "mutation",
    (
        lambda css: css.replace(
            ":root {", ".evil:not(:root) {", 1,
        ),
        lambda css: css.replace(
            "gap: var(--ve-path-spotlight-gap)", "gap: 8rem",
        ),
        lambda css: css.replace(
            "flex: 0 0 var(--ve-path-spotlight-node-width)", "flex: 0 0 20rem",
        ),
        lambda css: css + "\n:root { --ve-path-spotlight-gap: 1rem; }",
        lambda css: css + "\n.evil .ve-flow-path-canvas { gap: 8rem; }",
    ),
)
def test_width_contract_is_tied_to_unique_effective_path_layout_declarations(mutation) -> None:
    assert check_visual_stage_css(mutation(VISUAL_STAGE_CSS), SKELETON)


@pytest.mark.parametrize(
    "skeleton",
    (
        SKELETON.replace(
            "width: min(100% - var(--space-4), var(--w-narrative))",
            "width: 30rem",
        ),
        SKELETON.replace(
            "padding: var(--space-4) 0 var(--space-6)",
            "padding: var(--space-4) 5rem var(--space-6)",
        ),
        SKELETON.replace(
            "section { min-width: 0;",
            ".evil main { width: 30rem; } section { min-width: 0;",
        ),
    ),
)
def test_width_contract_rechecks_skeleton_main_content_width_and_inline_padding(skeleton: str) -> None:
    assert any("skeleton main" in item.message for item in check_visual_stage_css(
        VISUAL_STAGE_CSS, skeleton,
    ))


@pytest.mark.parametrize(
    "selector",
    (
        '[class~="ve-seq-spot"]',
        '[class~="VE-SEQ-SPOT" i]',
        '[cl\\61ss~="ve-seq-spot" s]',
        '[class~="ve-seq-\\73 pot"]',
    ),
)
def test_css_scanner_recognizes_class_attribute_highlight_selectors(selector: str) -> None:
    css = VISUAL_STAGE_CSS + f"\n.card{selector} {{ width: 1px; }}"
    assert any("paint-only" in item.message for item in check_visual_stage_css(css, SKELETON))


@pytest.mark.parametrize(
    "selector",
    (
        '[class="ve-seq-spot"]',
        '[class^="ve-seq-spot"]',
        '[class$="ve-seq-spot"]',
        '[class*="ve-seq-spot"]',
        '[class|="ve-seq-spot"]',
        '[class="VE-SEQ-SPOT" \\69]',
        '[class*="prefix-ve-seq-spot-suffix"]',
        '[class^="ve-seq"]',
    ),
)
def test_css_scanner_conservatively_recognizes_every_matching_class_operator(
    selector: str,
) -> None:
    css = VISUAL_STAGE_CSS + f"\n.card{selector} {{ width: 1px; }}"
    assert any("paint-only" in item.message for item in check_visual_stage_css(css, SKELETON))


def test_css_scanner_decodes_hex_escape_whitespace_terminators_before_selector_parsing() -> None:
    css = VISUAL_STAGE_CSS + '\n[cl\\61 ss^="ve-seq-\\73 pot" s] { width: 1px; }'
    assert any("paint-only" in item.message for item in check_visual_stage_css(css, SKELETON))


@pytest.mark.parametrize(
    "css",
    (
        VISUAL_STAGE_CSS + "\n.ve-flow-station { flex-basis: 30rem !important; }",
        VISUAL_STAGE_CSS + "\n.ve-flow-station { max-width: 30rem !important; }",
        VISUAL_STAGE_CSS + '\n[class~="ve-flow-path-canvas"] { gap: 8rem !important; }',
        VISUAL_STAGE_CSS + "\n.ve-flow-path-canvas { grid-gap: 8rem; }",
    ),
)
def test_width_contract_rejects_closed_set_interfering_visual_stage_sources(css: str) -> None:
    assert any("1212" in item.message for item in check_visual_stage_css(css, SKELETON))


@pytest.mark.parametrize(
    "css",
    (
        VISUAL_STAGE_CSS + "\n.ve-flow-station { inline-size: 30rem; }",
        VISUAL_STAGE_CSS + "\n.ve-flow-station { border-inline-width: 1rem; }",
        VISUAL_STAGE_CSS + "\n[data-stepper] * { flex-basis: 30rem; }",
        VISUAL_STAGE_CSS + "\n[data-stepper] .ve-flow-node { padding-inline-start: 2rem; }",
        VISUAL_STAGE_CSS + "\n.ve-flow-station { margin-inline: 1rem; }",
        VISUAL_STAGE_CSS + "\n.ve-flow-path-canvas { display: grid; }",
        VISUAL_STAGE_CSS + '\n[class^="ve-flow"] { inline-size: 30rem; }',
    ),
)
def test_width_contract_rejects_logical_and_ancestor_sizing_sources(css: str) -> None:
    assert any("1212" in item.message for item in check_visual_stage_css(css, SKELETON))


@pytest.mark.parametrize(
    "css",
    (
        VISUAL_STAGE_CSS + "\n.ve-flow-node { writing-mode: vertical-rl; }",
        VISUAL_STAGE_CSS + "\n.ve-flow-station { all: initial; }",
    ),
)
def test_width_contract_rejects_axis_and_reset_overrides_in_path_sources(css: str) -> None:
    assert any("1212" in item.message for item in check_visual_stage_css(css, SKELETON))


@pytest.mark.parametrize(
    "skeleton",
    (
        SKELETON.replace(
            "section { min-width: 0;",
            "main { border-inline: 1rem solid red; } section { min-width: 0;",
        ),
        SKELETON.replace(
            "section { min-width: 0;",
            "* { padding-inline: 5rem !important; } section { min-width: 0;",
        ),
        SKELETON.replace(
            "main { width: min(100% - var(--space-4), var(--w-narrative));",
            "main { box-sizing: content-box; width: min(100% - var(--space-4), var(--w-narrative));",
        ),
        SKELETON.replace(
            "main { width: min(100% - var(--space-4), var(--w-narrative));",
            "main { padding-inline-start: 5rem; width: min(100% - var(--space-4), var(--w-narrative));",
        ),
        SKELETON.replace("body { margin: 0;", "body { margin: 5rem;"),
    ),
)
def test_content_width_contract_includes_padding_border_and_box_sizing(skeleton: str) -> None:
    assert any("1212" in item.message for item in check_visual_stage_css(
        VISUAL_STAGE_CSS, skeleton,
    ))


@pytest.mark.parametrize(
    "skeleton",
    (
        SKELETON.replace(
            "main { width: min(100% - var(--space-4), var(--w-narrative));",
            "main { all: initial; width: min(100% - var(--space-4), var(--w-narrative));",
        ),
        SKELETON.replace(
            "section { min-width: 0;",
            "* { writing-mode: vertical-rl; } section { min-width: 0;",
        ),
    ),
)
def test_content_width_contract_rejects_axis_and_reset_overrides(skeleton: str) -> None:
    assert any("1212" in item.message for item in check_visual_stage_css(
        VISUAL_STAGE_CSS, skeleton,
    ))


@pytest.mark.parametrize(
    "bad_attribute",
    (
        'data-connect=""',
        'data-connect="node--p9--p2-&gt;desc--p2,"',
        'data-connect="node--p9--p2 desc--p2"',
        'filter="url(#desc--p2) trailing"',
        'filter="url(#)"',
    ),
)
def test_closed_reference_attributes_reject_malformed_or_trailing_grammar(
    bad_attribute: str,
) -> None:
    panel_two = _panel(2).replace(
        'aria-describedby="desc--p2"',
        f'aria-describedby="desc--p2" {bad_attribute}',
    )
    messages = _messages(_content(body=_stepper(
        panels=(_panel(1), panel_two, _panel(3)),
    )))
    assert any("参照属性" in message and "形式" in message for message in messages)


@pytest.mark.parametrize(
    "bad_attribute",
    (
        'href=""',
        'href="https://example.invalid/#desc--p2"',
        'href="desc--p2"',
        'xlink:href="none"',
        'filter="none"',
        'mask="garbage"',
        'fill="currentColor"',
        'stroke="https://example.invalid/paint"',
    ),
)
def test_every_designated_reference_attribute_has_closed_local_grammar(
    bad_attribute: str,
) -> None:
    panel_two = _panel(2).replace(
        'aria-describedby="desc--p2"',
        f'aria-describedby="desc--p2" {bad_attribute}',
    )
    messages = _messages(_content(body=_stepper(
        panels=(_panel(1), panel_two, _panel(3)),
    )))
    assert any("参照属性" in message and "形式" in message for message in messages)


@pytest.mark.parametrize(
    "bad_attribute",
    (
        'href=" #desc--p1 "',
        'filter="u\\72l(#desc--p2) trailing"',
        'style="filter: u\\72l(#desc--p2) trailing"',
        'style="filter: u\\72l(#desc--p1)"',
    ),
)
def test_reference_grammar_decodes_css_escapes_and_trims_fragment_values(
    bad_attribute: str,
) -> None:
    panel_two = _panel(2).replace(
        'aria-describedby="desc--p2"',
        f'aria-describedby="desc--p2" {bad_attribute}',
    )
    messages = _messages(_content(body=_stepper(
        panels=(_panel(1), panel_two, _panel(3)),
    )))
    assert any(
        "参照属性" in message and "形式" in message or "同一 panel" in message
        for message in messages
    )


def test_visual_stage_diagnostics_share_one_document_wide_stable_cap() -> None:
    style = "<style data-ve-asset=\"visual-stage\">" + VISUAL_STAGE_CSS + "\n" + "\n".join(
        f'.bad-{index}[class*="ve-seq-spot"] {{ width: {index + 1}px; }}'
        for index in range(40)
    ) + "</style>"

    first = check_visual_stage_document_css(_content(), style, SKELETON)
    second = check_visual_stage_document_css(_content(), style, SKELETON)
    assert first == second
    assert len(first) == 32


def test_css_only_public_checker_has_the_same_stable_cap() -> None:
    css = VISUAL_STAGE_CSS + "\n" + "\n".join(
        f'.bad-{index}[class*="ve-seq-spot"] {{ width: {index + 1}px; }}'
        for index in range(40)
    )
    first = check_visual_stage_css(css, SKELETON)
    second = check_visual_stage_css(css, SKELETON)
    assert first == second
    assert len(first) == 32


def test_final_checker_shares_cap_between_structure_and_css_diagnostics() -> None:
    raw = json.loads(
        (ROOT / "scripts" / "tests" / "component-valid-flow-sequence-branch.json")
        .read_text("utf-8")
    )
    document = build_document(
        raw,
        REGISTRY,
        TRUSTED_RENDERERS,
        SKELETON,
        COMPONENTS,
        document_path="bounded.html",
    )
    document = document.replace('data-step="1"', 'data-step="9"', 1)
    style_start = document.index('data-ve-asset="visual-stage"')
    style_end = document.index("</style>", style_start)
    invalid_rules = "\n".join(
        f'.bad-{index}[class*="ve-seq-spot"] {{ width: {index + 1}px; }}'
        for index in range(40)
    )
    document = document[:style_end] + invalid_rules + document[style_end:]

    first = check_final_document(document, SKELETON, REGISTRY, components_dir=COMPONENTS)
    second = check_final_document(document, SKELETON, REGISTRY, components_dir=COMPONENTS)
    first_visual = [item for item in first if item.message.startswith("visual-stage ")]
    second_visual = [item for item in second if item.message.startswith("visual-stage ")]
    assert first_visual == second_visual
    assert len(first_visual) == 32


def test_user_controlled_identifiers_are_bounded_in_diagnostics() -> None:
    huge_identifier = "x" * 5000
    css = VISUAL_STAGE_CSS + (
        f"\n.ve-flow-station#{huge_identifier} "
        "{ flex-basis: 30rem !important; }"
    )
    css_messages = [item.message for item in check_visual_stage_css(css, SKELETON)]
    assert css_messages
    assert max(map(len, css_messages)) <= 512

    record = replace(
        _record(),
        assertions=(Assertion("claim", "Claim", (huge_identifier,)),),
    )
    structure_messages = [
        item.message
        for item in check_document_structure(_content(), title="Title", expected=(record,))
        if item.message.startswith("visual-stage ")
    ]
    assert structure_messages
    assert max(map(len, structure_messages)) <= 512


def test_every_user_controlled_diagnostic_field_uses_the_common_length_bound() -> None:
    huge = "z" * 5000
    css = VISUAL_STAGE_CSS + f'\n[class*="ve-seq-spot"] {{ {huge}: 1; }}'
    css_messages = [item.message for item in check_visual_stage_css(css, SKELETON)]
    assert css_messages
    assert max(map(len, css_messages)) <= 512

    expected = replace(_record(component=huge), instance_id="diagram")
    content = _content(body=_stepper(mode=huge))
    structure_messages = [
        item.message
        for item in check_document_structure(content, title="Title", expected=(expected,))
        if item.message.startswith("visual-stage ")
    ]
    assert structure_messages
    assert max(map(len, structure_messages)) <= 512


def test_suffix_shaped_semantic_base_requires_exact_base_plus_panel_suffix() -> None:
    record = replace(
        _record(),
        payload_semantic_ids=frozenset({"node--p1", "desc"}),
        assertions=(Assertion("claim", "Claim", ("node--p1", "desc")),),
        sequence=SequenceDeclaration("state-lens", (
            SequenceStep("one", "First", ("node--p1",)),
            SequenceStep("two", "Second", ("desc",)),
        )),
    )
    panels = tuple(
        _panel(number).replace(
            f'id="node--p9--p{number}"',
            (
                'id="node--p1"'
                if number == 1
                else f'id="node--p1--p{number}"'
            ),
        )
        for number in (1, 2, 3)
    )
    messages = _messages(_content(body=_stepper(panels=panels)), (record,))
    assert any("node--p1--p1" in message for message in messages)


def test_bad_css_is_not_scanned_for_non_visual_stage_profile() -> None:
    strict = _content().replace('data-ve-profile="visual-stage"', 'data-ve-profile="strict"')
    style = '<style data-ve-asset="visual-stage">.ve-seq-spot { width: 1px; }</style>'
    messages = check_visual_stage_document_css(strict, style, SKELETON)
    assert not any("visual-stage CSS" in item.message for item in messages)
