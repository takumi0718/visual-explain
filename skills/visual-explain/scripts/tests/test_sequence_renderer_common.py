"""Focused contracts for the shared static sequence expansion core."""
from __future__ import annotations

from dataclasses import replace

import pytest

from ve_components.diagnostics import ContractError, RENDERER_FAILURE
from ve_components.model import RenderManifest, RenderResult, SequenceDeclaration, SequenceStep
from ve_components.renderers import common


def _sequence(mode: str) -> SequenceDeclaration:
    return SequenceDeclaration(
        mode=mode,
        steps=(
            SequenceStep(id="step-a", label="Review", target_ids=("node-a", "node-b")),
            SequenceStep(id="step-b", label="Approve", target_ids=("node-c",)),
        ),
    )


def _result(markup: str = '<figure id="figure"><p id="body">Body</p></figure>') -> RenderResult:
    return RenderResult(
        markup=markup,
        style_asset_ids=("visual-stage",),
        script_asset_ids=(),
        manifest=RenderManifest(
            component_id="flow",
            component_version=2,
            instance_id="example",
            consumed_semantic_ids=("example", "node-a", "node-b", "node-c"),
            generated_relationship_ids=(),
            generated_landmark_ids=("figure", "body"),
            asset_ids=("visual-stage",),
            asset_digests=("0" * 64,),
            declared_dependencies=(),
            fallback_mode="semantic-list",
        ),
    )


def test_state_lens_highlights_only_the_current_step_after_an_unhighlighted_overview() -> None:
    panels = common.sequence_panels(_sequence("state-lens"))

    assert [panel.highlight_ids for panel in panels] == [
        frozenset(),
        frozenset({"node-a", "node-b"}),
        frozenset({"node-c"}),
    ]


def test_delta_accumulate_highlights_the_prefix_union() -> None:
    panels = common.sequence_panels(_sequence("delta-accumulate"))

    assert [panel.highlight_ids for panel in panels] == [
        frozenset(),
        frozenset({"node-a", "node-b"}),
        frozenset({"node-a", "node-b", "node-c"}),
    ]


def test_path_spotlight_adds_deterministically_derived_edges_to_current_nodes() -> None:
    sequence = _sequence("path-spotlight")

    def path_edges(declaration: SequenceDeclaration, step_index: int) -> tuple[str, ...]:
        assert declaration is sequence
        return (("edge-ab",), ("edge-bc",))[step_index]

    panels = common.sequence_panels(sequence, path_edges=path_edges)

    assert [panel.highlight_ids for panel in panels] == [
        frozenset(),
        frozenset({"node-a", "node-b", "edge-ab"}),
        frozenset({"node-c", "edge-bc"}),
    ]


def test_panel_namespacing_suffixes_dom_ids_and_only_allowed_same_panel_references() -> None:
    markup = (
        '<svg id="diagram" viewBox="0 0 10 10" aria-labelledby="title desc absent"'
        ' style="filter: url(#fx); mask: url(#absent)" data-unknown-ref="node-a">'
        '<title id="title">A &amp; B</title><desc id="desc">Diagram</desc>'
        '<filter id="fx"></filter><marker id="arrow"></marker><path id="node-a"'
        ' data-ve-semantic-id="node-a" data-ve-node-id="node-a"'
        ' data-ve-from="node-a" data-ve-to="node-b" clip-path="url(#fx)"'
        ' mask="url(#fx)" filter="url(#fx)" marker-start="url(#arrow)"'
        ' marker-mid="url(#arrow)" marker-end="url(#arrow)"'
        ' fill="url(#fx)" stroke="url(#fx)"></path>'
        '<g id="node-b"></g>'
        '<use href="#title" xlink:href="#desc"></use>'
        '<label for="node-a" aria-describedby="desc absent"'
        ' aria-owns="node-a node-b">Node</label>'
        '<a href="https://example.com/#title">external</a></svg>'
    )

    rewritten = common.expand_sequence(
        _sequence("state-lens"), lambda panel: _result(markup),
    ).markup

    for base_id in ("diagram", "title", "desc", "fx", "arrow", "node-a", "node-b"):
        assert f'id="{base_id}--p3"' in rewritten
    assert 'data-ve-semantic-id="node-a"' in rewritten
    assert 'data-ve-node-id="node-a--p3"' in rewritten
    assert 'data-ve-from="node-a--p3" data-ve-to="node-b--p3"' in rewritten
    assert 'aria-labelledby="title--p3 desc--p3 absent"' in rewritten
    for attr in ("clip-path", "mask", "filter", "fill", "stroke"):
        assert f'{attr}="url(#fx--p3)"' in rewritten
    for attr in ("marker-start", "marker-mid", "marker-end"):
        assert f'{attr}="url(#arrow--p3)"' in rewritten
    assert 'style="filter: url(#fx--p3); mask: url(#absent)"' in rewritten
    assert 'href="#title--p3" xlink:href="#desc--p3"' in rewritten
    assert 'for="node-a--p3" aria-describedby="desc--p3 absent"' in rewritten
    assert 'aria-owns="node-a--p3 node-b--p3"' in rewritten
    assert 'data-unknown-ref="node-a"' in rewritten
    assert 'href="https://example.com/#title"' in rewritten
    assert '<title id="title--p3">A &amp; B</title>' in rewritten


def test_panel_namespacing_rewrites_each_data_connect_endpoint_in_the_same_panel() -> None:
    markup = (
        '<figure id="figure"><span id="node-a"></span><span id="node-b"></span>'
        '<div data-connect="node-a->node-b, node-b -> absent"></div></figure>'
    )

    rewritten = common.expand_sequence(
        _sequence("state-lens"), lambda panel: _result(markup),
    ).markup

    assert (
        'data-connect="node-a--p3-&gt;node-b--p3, node-b--p3 -&gt; absent"'
        in rewritten
    )


def test_exact_url_reference_attributes_do_not_scan_embedded_tokens() -> None:
    markup = (
        '<figure id="figure" style="filter: url(#fx)"><span id="fx"></span>'
        '<div id="bad-url" filter="junk url(#fx) junk"></div></figure>'
    )

    rewritten = common.expand_sequence(
        _sequence("state-lens"), lambda panel: _result(markup),
    ).markup

    assert 'id="figure--p3" style="filter: url(#fx--p3)"' in rewritten
    assert 'id="bad-url--p3" filter="junk url(#fx) junk"' in rewritten


def test_expand_sequence_emits_stepper_controls_and_escaped_panel_forecasts() -> None:
    sequence = SequenceDeclaration(
        mode="state-lens",
        steps=(
            SequenceStep(id="step-a", label="Review <risk>", target_ids=("node-a",)),
            SequenceStep(id="step-b", label="Approve & ship", target_ids=("node-b",)),
        ),
    )

    expanded = common.expand_sequence(sequence, lambda panel: _result())
    markup = expanded.markup

    assert markup.startswith(
        '<div data-stepper data-ve-sequence-mode="state-lens" data-total-steps="3">'
    )
    assert [markup.count(f'data-step="{number}"') for number in (1, 2, 3)] == [1, 1, 1]
    assert markup.count("<figure ") == 3
    assert markup.count('data-step-action="previous"') == 1
    assert markup.count('data-step-action="next"') == 1
    assert markup.count('data-step-action="all"') == 1
    assert 'data-next-label="次へ: 次の段階を強調表示"' in markup
    assert '<p class="ve-seq-next">次の段階: Review &lt;risk&gt;</p>' in markup
    assert '<p class="ve-seq-next">次の段階: Approve &amp; ship</p>' in markup
    assert markup.count('<p class="ve-seq-next">これで全段階です</p>') == 1
    assert "stepper-status" not in markup


def test_expand_sequence_suffixes_panel_landmarks_and_svg_roots_only() -> None:
    base = _result(
        '<figure id="figure" aria-describedby="body">'
        '<p id="body">Body</p><svg id="diagram"></svg></figure>'
    )
    base = RenderResult(
        markup=base.markup,
        style_asset_ids=base.style_asset_ids,
        script_asset_ids=base.script_asset_ids,
        manifest=RenderManifest(
            component_id=base.manifest.component_id,
            component_version=base.manifest.component_version,
            instance_id=base.manifest.instance_id,
            consumed_semantic_ids=base.manifest.consumed_semantic_ids,
            generated_relationship_ids=("edge-ab",),
            generated_landmark_ids=("figure", "body", "diagram"),
            asset_ids=base.manifest.asset_ids,
            asset_digests=base.manifest.asset_digests,
            declared_dependencies=base.manifest.declared_dependencies,
            fallback_mode=base.manifest.fallback_mode,
            svg_root_ids=("diagram",),
        ),
    )

    expanded = common.expand_sequence(_sequence("state-lens"), lambda panel: base)

    assert expanded.manifest.generated_landmark_ids == (
        "figure--p1", "body--p1", "diagram--p1",
        "figure--p2", "body--p2", "diagram--p2",
        "figure--p3", "body--p3", "diagram--p3",
    )
    assert expanded.manifest.svg_root_ids == (
        "diagram--p1", "diagram--p2", "diagram--p3",
    )
    assert expanded.manifest.consumed_semantic_ids == (
        "example", "node-a", "node-b", "node-c",
    )
    assert expanded.manifest.generated_relationship_ids == ("edge-ab",)
    assert expanded.markup.count('<svg id="diagram--p') == 3


_DIVERGENT_PANEL_FIELDS = (
    "style_asset_ids",
    "script_asset_ids",
    "component_id",
    "component_version",
    "instance_id",
    "consumed_semantic_ids",
    "generated_relationship_ids",
    "generated_landmark_ids",
    "asset_ids",
    "asset_digests",
    "declared_dependencies",
    "fallback_mode",
    "svg_root_ids",
)


def _diverge(result: RenderResult, field: str) -> RenderResult:
    values = {
        "style_asset_ids": ("other-style",),
        "script_asset_ids": ("other-script",),
        "component_id": "bars",
        "component_version": 3,
        "instance_id": "other-instance",
        "consumed_semantic_ids": ("different-semantic",),
        "generated_relationship_ids": ("different-edge",),
        "generated_landmark_ids": ("different-landmark",),
        "asset_ids": ("other-asset",),
        "asset_digests": ("1" * 64,),
        "declared_dependencies": ("other-dependency",),
        "fallback_mode": "different-fallback",
        "svg_root_ids": ("different-svg",),
    }
    if field in {"style_asset_ids", "script_asset_ids"}:
        return replace(result, **{field: values[field]})
    return replace(result, manifest=replace(result.manifest, **{field: values[field]}))


@pytest.mark.parametrize("field", _DIVERGENT_PANEL_FIELDS)
def test_expand_sequence_rejects_divergent_callback_contract_fields(field: str) -> None:
    base = _result()

    def render(panel: common.SequencePanel) -> RenderResult:
        return _diverge(base, field) if panel.number == 3 else base

    with pytest.raises(ContractError) as exc:
        common.expand_sequence(_sequence("state-lens"), render)

    assert {diagnostic.code for diagnostic in exc.value.diagnostics} == {RENDERER_FAILURE}
    assert any(field in diagnostic.message for diagnostic in exc.value.diagnostics)


def test_expand_sequence_is_an_exact_legacy_noop_without_a_sequence() -> None:
    legacy = _result('<figure id="legacy">unchanged &amp; exact</figure>')

    expanded = common.expand_sequence(None, lambda panel: legacy)

    assert expanded is legacy
