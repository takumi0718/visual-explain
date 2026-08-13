"""Task 11: legacy checker contracts for statically expanded sequence panels."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from fixture_util import canonical_ir
from test_flow_sequence_renderer import _sequence_section as _flow_sequence_section
from test_matrix_stairs_sequence_renderer import _state_lens_section
from test_waterfall_bars_sequence_renderer import _delta_section
from build_explainer import build_document
from ve_components.assembly import render_canonical
from ve_components.checker import (
    _has_external_asset_reference,
    extract_flow_dom,
    validate_artifact_semantics,
    validate_renderer_svg,
)
from ve_components.diagnostics import ARTIFACT_SEMANTIC_MISMATCH, RENDERER_SVG_VIOLATION
from ve_components.model import Assertion, CanonicalSection, SequenceDeclaration, SequenceStep
from ve_components.registry import load_registry, resolve_component
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.validation import validate_canonical_section


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
TESTS = SKILL / "scripts" / "tests"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
COMPONENTS = SKILL / "assets" / "components"
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")


def _waterfall_sequence_section() -> CanonicalSection:
    raw = json.loads((TESTS / "component-valid-waterfall.json").read_text("utf-8"))
    ir = validate_canonical_section(canonical_ir(raw))
    sequence = SequenceDeclaration(
        mode="delta-accumulate",
        steps=(
            SequenceStep(id="delta-1", label="前半", target_ids=("wf-start", "wf-step-1")),
            SequenceStep(id="delta-2", label="後半", target_ids=("wf-step-3", "wf-end")),
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
        claim="増減を段階的に確認する。",
        sequence=sequence,
        assertions=(Assertion(
            id="delta-meaning",
            text="増減を段階的に確認する。",
            cover_ids=("wf-start", "wf-step-1", "wf-step-3", "wf-end"),
        ),),
    ))


def _rendered(section: CanonicalSection) -> str:
    return render_canonical(
        section,
        resolve_component(section.ir.selection, REGISTRY),
    ).markup


def _panel_bounds(markup: str, number: int) -> tuple[int, int, int]:
    opening = f'<div data-step="{number}">'
    start = markup.index(opening)
    inner_start = start + len(opening)
    next_panel = f'<div data-step="{number + 1}">'
    if next_panel in markup[inner_start:]:
        end = markup.index(next_panel, inner_start)
    else:
        end = markup.index('<div class="ve-stepper-controls">', inner_start)
    # The panel closing tag is the final </div> before the next panel/controls.
    close = markup.rfind("</div>", inner_start, end)
    assert close != -1
    return start, inner_start, close


def _replace_panel_inner(markup: str, number: int, inner: str) -> str:
    _start, inner_start, close = _panel_bounds(markup, number)
    return markup[:inner_start] + inner + markup[close:]


def _panel(markup: str, number: int) -> str:
    start, _inner_start, close = _panel_bounds(markup, number)
    return markup[start:close + len("</div>")]


def _messages(diagnostics, code: str) -> str:
    return "\n".join(diagnostic.message for diagnostic in diagnostics if diagnostic.code == code)


def test_panel_aware_checker_accepts_complete_waterfall_sequence() -> None:
    markup = _rendered(_waterfall_sequence_section())

    assert validate_artifact_semantics(markup) == []
    assert validate_renderer_svg(markup) == []


def test_panel_aware_semantic_checker_accepts_other_sequence_components() -> None:
    sections = (
        _state_lens_section(
            "component-valid-matrix.json",
            (("cell-admin-read",), ("cell-viewer-write",)),
        ),
        _state_lens_section(
            "component-valid-stairs.json",
            (("stage-1",), ("stage-4",)),
        ),
        _delta_section("component-valid-bars.json", (("b1",), ("b2",))),
    )

    for section in sections:
        assert validate_artifact_semantics(_rendered(section)) == []


def test_flow_path_sequence_build_accepts_local_svg_namespace_and_js_comments() -> None:
    raw = json.loads(
        (TESTS / "component-valid-flow-sequence-branch.json").read_text("utf-8")
    )

    document = build_document(
        raw,
        REGISTRY,
        TRUSTED_RENDERERS,
        SKELETON,
        COMPONENTS,
        document_path="flow-sequence.html",
    )

    assert 'data-ve-sequence-mode="path-spotlight"' in document
    assert 'data-ve-asset="visual-stage-flow"' in document


def test_controlled_asset_url_scan_distinguishes_comments_and_svg_namespace_from_network_urls() -> None:
    assert _has_external_asset_reference(
        "// fetch('https://comment.invalid/x')\nconst ready = true;",
        "scripts",
    ) is False
    assert _has_external_asset_reference(
        "/* fetch('wss://comment.invalid/x') */ const ready = true;",
        "scripts",
    ) is False
    assert _has_external_asset_reference(
        "const SVG_NS = 'http:' + '//www.w3.org/2000/svg';"
        "document.createElementNS(SVG_NS, 'svg');",
        "scripts",
    ) is False
    assert _has_external_asset_reference(
        "document.createElementNS('http:' + '//www.w3.org/2000/svg', 'svg');",
        "scripts",
    ) is False
    assert _has_external_asset_reference(
        "fetch('https://example.invalid/data.json')",
        "scripts",
    ) is True
    assert _has_external_asset_reference(
        ".card { background: url(//example.invalid/image.png); }",
        "styles",
    ) is True


def test_controlled_script_scan_rejects_static_network_url_concatenation() -> None:
    blocked = (
        "fetch('http:' + '//example.invalid/data.json')",
        "fetch('//' + 'example.invalid/data.json')",
        "fetch('ht' + 'tp://example.invalid/data.json')",
        "new WebSocket('wss:' + '//example.invalid/socket')",
        "fetch('ftp:' + '//example.invalid/archive')",
        "fetch('http:' + '//www.w3.org/2000/svg')",
        "const SVG_NS = 'http:' + '//www.w3.org/2000/svg'; fetch(SVG_NS)",
    )

    for source in blocked:
        assert _has_external_asset_reference(source, "scripts") is True


def test_svg_namespace_allowance_requires_the_closed_document_call_shape() -> None:
    blocked = (
        "evil.createElementNS('http:' + '//www.w3.org/2000/svg', 'svg')",
        "evil.document.createElementNS('http:' + '//www.w3.org/2000/svg', 'svg')",
        "const document = evil; document.createElementNS('http:' + '//www.w3.org/2000/svg', 'svg')",
        "function build(document) { return document.createElementNS('http:' + '//www.w3.org/2000/svg', 'svg'); }",
        "const createElementNS = fetch; createElementNS('http:' + '//www.w3.org/2000/svg')",
        "createElementNS('http:' + '//www.w3.org/2000/svg', 'svg')",
    )

    for source in blocked:
        assert _has_external_asset_reference(source, "scripts") is True


def test_controlled_script_scan_fails_closed_on_dynamic_or_aliased_network_arguments() -> None:
    blocked = (
        "fetch(`ht${'tp'}${'s:'}${'/'}${'/host/x'}`)",
        r"fetch('\u{68}ttps:\u{2f}\u{2f}host/x')",
        "const a='ht'; const b='tps:'; const c='/'; const d='/host/x'; fetch(a+b+c+d)",
        "fetch(('ht' + 'tps:' + '/' + '/host/x'))",
    )

    for source in blocked:
        assert _has_external_asset_reference(source, "scripts") is True


def test_controlled_script_scan_rejects_network_api_identifiers_in_every_code_shape() -> None:
    blocked = (
        "const request = fetch; request('/local')",
        "fetch.call(window, '/local')",
        "function local(fetch) { return fetch('/local'); }",
        "fetch = localOnly",
        "new XMLHttpRequest()",
        "window.WebSocket",
        "navigator.sendBeacon",
        "importScripts.apply(null, files)",
        r"f\u0065tch('/local')",
    )

    for source in blocked:
        assert _has_external_asset_reference(source, "scripts") is True


def test_controlled_script_scan_rejects_computed_api_names_without_rejecting_ui_strings() -> None:
    assert _has_external_asset_reference("window['fetch']('/local')", "scripts") is True
    assert _has_external_asset_reference('const label = "fetch";', "scripts") is False


def test_controlled_script_scan_rejects_all_known_global_computed_member_access() -> None:
    blocked = (
        "globalThis['fe' + 'tch']('/local')",
        "globalThis[('fetch')]('/local')",
        "const name = 'fetch'; globalThis[name]('/local')",
        "globalThis?.['fetch']('/local')",
        "window['safeLocalProperty']",
    )

    for source in blocked:
        assert _has_external_asset_reference(source, "scripts") is True


def test_controlled_script_scan_keeps_strings_and_regex_literals_opaque() -> None:
    allowed = (
        "const labels = ['fetch', 'WebSocket'];",
        "const pattern = /fetch|WebSocket/g;",
        r"const pattern = /[/]fetch\/WebSocket[abc]/gi;",
    )

    for source in allowed:
        assert _has_external_asset_reference(source, "scripts") is False


def test_controlled_script_scan_distinguishes_division_from_regex_literal() -> None:
    assert _has_external_asset_reference("const ratio = total / count / 2;", "scripts") is False
    assert _has_external_asset_reference("const ratio = total / fetch / 2;", "scripts") is True


def test_controlled_script_reserves_network_names_in_object_and_class_code() -> None:
    assert _has_external_asset_reference("const handlers = {fetch: localOnly};", "scripts") is True
    assert _has_external_asset_reference("class Local { fetch() {} }", "scripts") is True


def test_controlled_style_scan_ignores_comment_urls_but_rejects_live_ones() -> None:
    assert _has_external_asset_reference(
        "/* background: url(https://comment.invalid/image.png) */ .card { color: red; }",
        "styles",
    ) is False
    assert _has_external_asset_reference(
        '@import "ftp://example.invalid/theme.css";',
        "styles",
    ) is True
    assert _has_external_asset_reference(
        '.card::before { content: "/*"; background: url(https://example.invalid/x);'
        ' content: "*/"; }',
        "styles",
    ) is True
    assert _has_external_asset_reference(
        r".card { background: url(https:\2f\2f bad.invalid/x); }",
        "styles",
    ) is True
    assert _has_external_asset_reference(
        r'.card::before { content: "url(foo\\bar)"; }',
        "styles",
    ) is False
    assert _has_external_asset_reference(
        r".card { background: \75rl(https:\2f\2f bad.invalid/x); }",
        "styles",
    ) is True
    for safe_url in ("data:image/svg+xml;base64,AA==", "#marker", "images/card.png"):
        assert _has_external_asset_reference(
            f".card {{ background: url({safe_url}); }}",
            "styles",
        ) is False


def test_semantic_checker_rejects_a_panel_missing_its_component_instance() -> None:
    markup = _rendered(_flow_sequence_section("path-spotlight"))
    tampered = _replace_panel_inner(markup, 2, '<p class="ve-seq-next">次へ</p>')

    messages = _messages(validate_artifact_semantics(tampered), ARTIFACT_SEMANTIC_MISMATCH)
    assert "panel 2" in messages


def test_semantic_checker_rejects_duplicate_component_instances_in_one_panel() -> None:
    markup = _rendered(_flow_sequence_section("path-spotlight"))
    panel_two = _panel(markup, 2)
    figure_start = panel_two.index('<figure data-ve-component="flow"')
    figure_end = panel_two.index("</figure>", figure_start) + len("</figure>")
    figure = panel_two[figure_start:figure_end]
    tampered = markup.replace(panel_two, panel_two[:figure_end] + figure + panel_two[figure_end:], 1)

    messages = _messages(validate_artifact_semantics(tampered), ARTIFACT_SEMANTIC_MISMATCH)
    assert "panel 2" in messages


def test_flow_checker_rejects_cross_panel_endpoint_reference() -> None:
    markup = _rendered(_flow_sequence_section("path-spotlight"))
    panel_two = _panel(markup, 2)
    tampered_panel = panel_two.replace(
        'data-ve-from="node-draft--p2"',
        'data-ve-from="node-draft--p3"',
        1,
    )
    tampered = markup.replace(panel_two, tampered_panel, 1)

    messages = _messages(validate_artifact_semantics(tampered), ARTIFACT_SEMANTIC_MISMATCH)
    assert "panel 2" in messages


def test_flow_checker_rejects_node_with_wrong_panel_suffix() -> None:
    markup = _rendered(_flow_sequence_section("path-spotlight"))
    panel_two = _panel(markup, 2)
    tampered_panel = panel_two.replace(
        'data-ve-node-id="node-draft--p2"',
        'data-ve-node-id="node-draft--p20"',
        1,
    )
    tampered = markup.replace(panel_two, tampered_panel, 1)

    messages = _messages(validate_artifact_semantics(tampered), ARTIFACT_SEMANTIC_MISMATCH)
    assert "panel 2" in messages


def test_flow_suffix_normalization_is_panel_scoped_and_preserves_suffix_shaped_base_ids() -> None:
    markup = (
        '<div data-stepper><div data-step="2">'
        '<ol class="ve-flow-canvas"><li class="ve-flow-station">'
        '<span class="ve-flow-node" data-ve-semantic-id="node-a--p2"'
        ' data-ve-node-id="node-a--p2--p2">A</span></li></ol>'
        '<i data-ve-semantic-id="edge-a" data-ve-from="node-a--p2--p2"'
        ' data-ve-to="node-a--p2--p2" data-ve-relation="ordered-transition"></i>'
        '</div></div>'
    )

    nodes, edges, incomplete = extract_flow_dom(markup)

    assert nodes == {"node-a--p2"}
    assert edges == {("node-a--p2", "node-a--p2", "ordered-transition")}
    assert incomplete is False

    outside_nodes, _outside_edges, _outside_incomplete = extract_flow_dom(
        '<div data-step="2"><ol class="ve-flow-canvas"><li class="ve-flow-station">'
        '<span class="ve-flow-node" data-ve-semantic-id="node-a--p2"'
        ' data-ve-node-id="node-a--p2--p2">A</span></li></ol></div>'
    )
    assert outside_nodes == set()


def test_svg_checker_rejects_one_panel_missing_its_svg() -> None:
    markup = _rendered(_waterfall_sequence_section())
    panel_two = _panel(markup, 2)
    svg_start = panel_two.index("<svg")
    svg_end = panel_two.index("</svg>", svg_start) + len("</svg>")
    tampered = markup.replace(panel_two, panel_two[:svg_start] + panel_two[svg_end:], 1)

    messages = _messages(validate_renderer_svg(tampered), RENDERER_SVG_VIOLATION)
    assert "panel 2" in messages


def test_svg_checker_rejects_duplicate_svg_inside_one_panel() -> None:
    markup = _rendered(_waterfall_sequence_section())
    panel_two = _panel(markup, 2)
    svg_start = panel_two.index("<svg")
    svg_end = panel_two.index("</svg>", svg_start) + len("</svg>")
    svg = panel_two[svg_start:svg_end]
    tampered = markup.replace(panel_two, panel_two[:svg_end] + svg + panel_two[svg_end:], 1)

    messages = _messages(validate_renderer_svg(tampered), RENDERER_SVG_VIOLATION)
    assert "panel 2" in messages


def test_svg_checker_requires_root_id_suffix_matching_its_panel() -> None:
    markup = _rendered(_waterfall_sequence_section())
    panel_two = _panel(markup, 2)
    tampered_panel = panel_two.replace(
        'id="sec-waterfall-svg--p2"',
        'id="sec-waterfall-svg--p3"',
        1,
    )
    tampered = markup.replace(panel_two, tampered_panel, 1)

    messages = _messages(validate_renderer_svg(tampered), RENDERER_SVG_VIOLATION)
    assert "panel 2" in messages


def test_svg_checker_rejects_svg_inserted_between_panels_and_controls() -> None:
    markup = _rendered(_waterfall_sequence_section())
    controls = '<div class="ve-stepper-controls">'
    rogue = (
        '<svg id="rogue-svg" viewBox="0 0 640 360"'
        ' preserveAspectRatio="xMidYMid meet"><rect x="0" y="0" width="1" height="1">'
        '</rect></svg>'
    )
    tampered = markup.replace(controls, rogue + controls, 1)

    messages = _messages(validate_renderer_svg(tampered), RENDERER_SVG_VIOLATION)
    assert "panel 外" in messages


def test_svg_checker_rejects_forbidden_svg_markup_outside_every_panel() -> None:
    markup = _rendered(_waterfall_sequence_section())
    controls = '<div class="ve-stepper-controls">'
    rogue = (
        '<svg id="rogue-svg" viewBox="0 0 640 360"'
        ' preserveAspectRatio="xMidYMid meet">'
        '<foreignObject><p>unsafe</p></foreignObject></svg>'
    )
    tampered = markup.replace(controls, rogue + controls, 1)

    messages = _messages(validate_renderer_svg(tampered), RENDERER_SVG_VIOLATION)
    assert "panel 外" in messages
    assert "foreignobject" in messages.lower()


def test_svg_panel_ownership_ignores_svg_text_inside_html_comments() -> None:
    markup = _rendered(_waterfall_sequence_section())
    controls = '<div class="ve-stepper-controls">'
    comment = '<!-- <svg id="not-an-element"><foreignObject></foreignObject></svg> -->'
    tampered = markup.replace(controls, comment + controls, 1)

    assert validate_renderer_svg(tampered) == []
