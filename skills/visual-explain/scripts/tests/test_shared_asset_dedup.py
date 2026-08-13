"""Task 4 shared-asset assembly and controlled-slot contracts."""
from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path

from ve_components.assembly import (
    AssetRef,
    ExpectedCanonicalRecord,
    RenderedCanonical,
    compose_sections,
)
from ve_components.checker import validate_controlled_assets
from ve_components.model import RenderManifest
from ve_components.registry import AssetDefinition, Registry, load_registry


CSS = ".shared{color:inherit}\n"
DIGEST = hashlib.sha256(CSS.encode("utf-8")).hexdigest()


def _manifest(component_id: str, instance_id: str, digest: str) -> RenderManifest:
    return RenderManifest(
        component_id=component_id,
        component_version=2,
        instance_id=instance_id,
        consumed_semantic_ids=(instance_id,),
        generated_relationship_ids=(),
        generated_landmark_ids=(),
        asset_ids=("visual-stage",),
        asset_digests=(digest,),
        declared_dependencies=(),
        fallback_mode="static-content",
    )


def _rendered(component_id: str, instance_id: str, asset: AssetDefinition) -> RenderedCanonical:
    ref = AssetRef(component_id=component_id, version=2, asset=asset)
    return RenderedCanonical(
        instance_id=instance_id,
        markup=f'<section data-ve-instance="{instance_id}"></section>',
        style_assets=(ref,),
        script_assets=(),
        manifest=_manifest(component_id, instance_id, asset.digest),
        expected_record=ExpectedCanonicalRecord(
            component_id=component_id,
            instance_id=instance_id,
            payload_semantic_ids=frozenset(),
            claim=None,
            assertions=None,
            sequence=None,
        ),
    )


def _registry_with_shared_assets(second_digest: str) -> Registry:
    production = load_registry(
        Path(__file__).resolve().parents[2] / "assets" / "components" / "registry.json"
    )
    matrix = production.find("matrix", 2)
    flow = production.find("flow", 2)
    assert matrix is not None and flow is not None
    first = AssetDefinition("visual-stage", "styles", "visual-stage.css", DIGEST)
    second = AssetDefinition("visual-stage", "styles", "visual-stage.css", second_digest)
    return Registry(
        registry_version=production.registry_version,
        components=(dataclasses.replace(matrix, assets=(first,)), dataclasses.replace(flow, assets=(second,))),
    )


def _style_slot() -> dict[str, str]:
    return {
        "styles": (
            '<style data-ve-component="matrix" data-ve-contract-version="2" '
            f'data-ve-asset="visual-stage" data-ve-digest="{DIGEST}">{CSS}</style>'
        ),
        "scripts": "",
    }


def test_compose_deduplicates_same_asset_id_and_digest_across_components() -> None:
    asset = AssetDefinition("visual-stage", "styles", "visual-stage.css", DIGEST)

    result = compose_sections((
        _rendered("matrix", "matrix-one", asset),
        _rendered("flow", "flow-one", asset),
    ))

    assert len(result.style_assets) == 1
    assert result.style_assets[0].asset.id == "visual-stage"


def test_controlled_asset_accepts_one_emission_when_all_declarations_share_digest() -> None:
    assert validate_controlled_assets(_style_slot(), _registry_with_shared_assets(DIGEST), None) == []


def test_controlled_asset_rejects_one_emission_when_registry_declarations_conflict() -> None:
    conflicting = "f" * 64

    diagnostics = validate_controlled_assets(
        _style_slot(), _registry_with_shared_assets(conflicting), None,
    )

    assert "invalid_controlled_asset" in {diagnostic.code for diagnostic in diagnostics}
