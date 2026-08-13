"""Task 4 immutable canonical expectations and checker argument transport."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ve_components.assembly import compose_sections, process_canonical_section
from ve_components.checker import check_final_document
from ve_components.diagnostics import ContractError
from ve_components.registry import Registry, load_registry
from ve_components.renderers.matrix import render_matrix
from ve_components.validation import validate_assembly


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
TESTS = SKILL / "scripts" / "tests"
COMPONENTS = SKILL / "assets" / "components"
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")


def _visual_stage_matrix_section():
    raw = json.loads((TESTS / "component-valid-matrix.json").read_text("utf-8"))
    raw["document"]["profile"] = "visual-stage"
    ir = raw["sections"][1]["ir"]
    ir["relationship"]["capabilities"].append("typed-sequence")
    ir["selection"]["matchedCapabilities"].append("typed-sequence")
    ir["claim"] = "権限差はセル単位で明確になる。"
    ir["sequence"] = {
        "mode": "state-lens",
        "steps": [
            {"id": "admin", "label": "管理者", "targetIds": ["cell-admin-read"]},
            {"id": "viewer", "label": "閲覧者", "targetIds": ["cell-viewer-write"]},
        ],
    }
    ir["assertions"] = [{
        "id": "permission-gap",
        "text": "権限差はセル単位で明確になる。",
        "coverIds": ["cell-admin-read", "cell-viewer-write"],
    }]
    return validate_assembly(raw).sections[1]


def test_compose_carries_immutable_validated_ir_facts_as_expected_records() -> None:
    section = _visual_stage_matrix_section()
    production = load_registry(COMPONENTS / "registry.json")
    matrix = production.find("matrix", 2)
    assert matrix is not None
    registry = Registry(
        registry_version=production.registry_version,
        components=(dataclasses.replace(
            matrix, capabilities=matrix.capabilities + ("typed-sequence",),
        ),),
    )

    rendered = process_canonical_section(section, registry, {"matrix@2": render_matrix})
    composition = compose_sections((rendered,))

    assert len(composition.expected_records) == 1
    record = composition.expected_records[0]
    assert record.component_id == "matrix"
    assert record.instance_id == "sec-access-matrix"
    assert record.payload_semantic_ids == frozenset({
        "row-admin", "row-viewer", "col-read", "col-write",
        "cell-admin-read", "cell-admin-write", "cell-viewer-read", "cell-viewer-write",
    })
    assert record.claim == "権限差はセル単位で明確になる。"
    assert record.assertions == section.ir.assertions
    assert record.sequence == section.ir.sequence
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.claim = "変更不可"


def test_compose_rejects_canonical_manifest_without_expected_record() -> None:
    section = _visual_stage_matrix_section()
    registry = load_registry(COMPONENTS / "registry.json")
    rendered = process_canonical_section(section, registry, {"matrix@2": render_matrix})
    missing_record = dataclasses.replace(rendered, expected_record=None)

    with pytest.raises(ContractError) as exc:
        compose_sections((missing_record,))

    assert {diagnostic.code for diagnostic in exc.value.diagnostics} == {"renderer_failure"}
    assert "expected record" in " ".join(
        diagnostic.message for diagnostic in exc.value.diagnostics
    )


def test_final_checker_passes_expected_records_to_document_structure(monkeypatch) -> None:
    import ve_components.document_checks as document_checks

    expected_records = (object(),)
    captured = []

    def recording_check(content_markup: str, *, title=None, expected=None):
        captured.append(expected)
        return []

    monkeypatch.setattr(document_checks, "check_document_structure", recording_check)

    expected = SimpleNamespace(
        manifests=(), compatibility=(), narrative=(), expected_records=expected_records,
    )
    check_final_document(
        SKELETON, SKELETON, load_registry(COMPONENTS / "registry.json"), expected=expected,
    )

    assert captured == [expected_records]
