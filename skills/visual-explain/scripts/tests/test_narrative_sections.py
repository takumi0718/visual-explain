import json
from pathlib import Path
from unittest import mock

import pytest

import build_explainer
from build_explainer import build_document
from ve_components.assembly import (
    compose_sections,
    process_canonical_section,
    process_narrative_section,
)
from ve_components.diagnostics import ContractError
from ve_components.model import NarrativeSection
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.validation import validate_assembly

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / "skills" / "visual-explain"
SKELETON = (SKILL_DIR / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS_DIR = SKILL_DIR / "assets" / "components"
REGISTRY = load_registry(COMPONENTS_DIR / "registry.json")
TESTS_DIR = SKILL_DIR / "scripts" / "tests"

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


def test_process_narrative_wraps_with_instance():
    sec = NarrativeSection(id="sec-intro", markup="<h1>結論</h1>")
    wrapped = process_narrative_section(sec)
    assert 'data-ve-section-kind="narrative"' in wrapped.markup
    assert 'data-ve-instance="sec-intro"' in wrapped.markup


def test_process_narrative_rejects_forbidden_markup():
    sec = NarrativeSection(id="sec-bad", markup='<script>alert(1)</script>')
    with pytest.raises(ContractError) as exc:
        process_narrative_section(sec)
    assert "forbidden_content_markup" in exc.value.codes


def _mixed_narrative_assembly():
    # Reuse the canonical ir from the enumeration fixture verbatim, sandwiched
    # between a first-screen and a closing narrative section.
    canonical = json.loads((TESTS_DIR / "component-valid-enumeration.json").read_text("utf-8"))
    first_screen = {"kind": "narrative", "id": "sec-first-screen",
                     "markup": '<section class="first-screen"><h1>結論を先に示す</h1></section>'}
    closing = {"kind": "narrative", "id": "sec-closing",
               "markup": '<section class="closing"><p>まとめ</p></section>'}
    canonical["sections"] = [first_screen, canonical["sections"][0], closing]
    return canonical


def test_build_document_orders_narrative_and_canonical_sections():
    raw = _mixed_narrative_assembly()
    # The final checker (Task 3) does not yet recognize the narrative
    # section-kind at the provenance layer; bypass just that gate here so this
    # test isolates build_document's own composition/dispatch route (this
    # task's scope) rather than Task 3's not-yet-built work.
    with mock.patch.object(build_explainer, "check_final_document", return_value=[]):
        doc = build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS_DIR)
    i_first = doc.index('data-ve-instance="sec-first-screen"')
    i_canonical = doc.index('data-ve-instance="sec-enum-list"')
    i_closing = doc.index('data-ve-instance="sec-closing"')
    assert i_first < i_canonical < i_closing
    assert doc.count('data-ve-section-kind="narrative"') == 2
    assert doc.count('data-ve-section-kind="canonical"') == 1


def test_compose_sections_rejects_duplicate_id_across_narrative_and_canonical():
    canonical_request = validate_assembly(
        json.loads((TESTS_DIR / "component-valid-enumeration.json").read_text("utf-8")))
    canonical_section = canonical_request.sections[0]
    rendered = process_canonical_section(canonical_section, REGISTRY, TRUSTED_RENDERERS)
    narrative = process_narrative_section(NarrativeSection(id=rendered.instance_id, markup="<p>まとめ</p>"))
    with pytest.raises(ContractError) as exc:
        compose_sections([rendered, narrative])
    assert "duplicate_section_id" in exc.value.codes
