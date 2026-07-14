import pytest

from ve_components.diagnostics import ContractError
from ve_components.model import NarrativeSection
from ve_components.validation import validate_assembly

BASE = {"schemaVersion": 1,
        "document": {"id": "doc", "title": "検証資料", "summary": "narrative 検証。"}}

NARR = {"kind": "narrative", "id": "sec-intro",
        "markup": '<section class="first-screen"><h1>結論を先に示す</h1></section>'}


def _assembly(*sections):
    return {**BASE, "sections": list(sections)}


def test_narrative_section_parses():
    req = validate_assembly(_assembly(NARR))
    sec = req.sections[0]
    assert isinstance(sec, NarrativeSection)
    assert sec.id == "sec-intro"
    assert "first-screen" in sec.markup


def test_narrative_rejects_extra_field():
    bad = {**NARR, "provenance": {"source": "legacy-html-insertion"}}
    with pytest.raises(ContractError) as exc:
        validate_assembly(_assembly(bad))
    assert "invalid_narrative_section" in exc.value.codes


def test_narrative_rejects_blank_id_and_markup():
    with pytest.raises(ContractError) as exc:
        validate_assembly(_assembly({"kind": "narrative", "id": " ", "markup": " "}))
    assert "invalid_narrative_section" in exc.value.codes


def test_narrative_duplicate_id_rejected():
    with pytest.raises(ContractError) as exc:
        validate_assembly(_assembly(NARR, dict(NARR)))
    assert "duplicate_semantic_id" in exc.value.codes
