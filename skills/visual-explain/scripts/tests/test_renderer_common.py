"""Focused contracts for renderer claim markup and stage asset selection."""
from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest

from ve_components.registry import AssetDefinition


def _common():
    return importlib.import_module("ve_components.renderers.common")


def _ir(**overrides):
    values = {"claim": None, "sequence": None, "assertions": None}
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.parametrize("body", [
    '<figure data-ve-component="matrix"></figure>',
    '<div class="ve-stepper"></div>',
])
def test_claim_before_body_escapes_once_and_stays_outside_body(body: str) -> None:
    claim = 'Choose <p class="ve-claim">A & B</p> "now"'

    markup = _common().claim_before_body(_ir(claim=claim), body)

    expected_claim = (
        '<p class="ve-claim">Choose &lt;p class=&quot;ve-claim&quot;&gt;'
        'A &amp; B&lt;/p&gt; &quot;now&quot;</p>'
    )
    assert markup == expected_claim + body
    assert markup.count('<p class="ve-claim">') == 1


def test_claim_before_body_preserves_legacy_body_byte_for_byte() -> None:
    body = '<figure data-ve-component="flow">\n  legacy bytes\n</figure>'

    assert _common().claim_before_body(_ir(), body) == body


def _asset(asset_id: str, slot: str = "styles") -> AssetDefinition:
    return AssetDefinition(asset_id, slot, f"{asset_id}.css", "0" * 64)


@pytest.mark.parametrize("field", ["claim", "sequence", "assertions"])
def test_select_style_assets_includes_visual_stage_when_any_stage_field_is_present(field: str) -> None:
    incumbent = _asset("incumbnt")
    shared = _asset("visual-stage")
    extension = _asset("extensio")
    assets = (incumbent, shared, extension)

    selected = _common().select_style_assets(_ir(**{field: object()}), assets)

    assert selected == assets
    assert all(actual is original for actual, original in zip(selected, assets))


def test_select_style_assets_omits_only_visual_stage_without_stage_fields() -> None:
    incumbent = _asset("incumbnt")
    shared = _asset("visual-stage")
    extension = _asset("extensio")
    script = _asset("scripted", "scripts")

    selected = _common().select_style_assets(
        _ir(), (incumbent, shared, extension, script),
    )

    assert selected == (incumbent, extension)
    assert selected[0] is incumbent
    assert selected[1] is extension
