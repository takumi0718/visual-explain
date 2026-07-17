import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from build_explainer import build_document
from ve_components.assembly import (
    compose_sections,
    process_canonical_section,
    process_compatibility_section,
    process_narrative_section,
)
from ve_components.checker import check_final_document, validate_final_provenance
from ve_components.diagnostics import ContractError
from ve_components.flatten import flatten_document
from ve_components.model import CanonicalSection, NarrativeSection
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.validation import validate_assembly

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / "skills" / "visual-explain"
SKELETON = (SKILL_DIR / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS_DIR = SKILL_DIR / "assets" / "components"
REGISTRY = load_registry(COMPONENTS_DIR / "registry.json")
TESTS_DIR = SKILL_DIR / "scripts" / "tests"
CHECK = SKILL_DIR / "scripts" / "check.sh"

BASE = {"schemaVersion": 1,
        "document": {"id": "doc", "title": "検証資料", "summary": "narrative 検証。",
                     "type": "system", "profile": "strict"}}

FIRST = {"kind": "first-screen", "id": "sec-first", "decision": "決めます。"}
CLOSING = {
    "kind": "closing",
    "id": "sec-closing",
    "blocks": [{"heading": "限界・確度", "items": ["推論を含む"]}],
}
NARR = {"kind": "narrative", "id": "sec-intro", "markup": "<p>結論を先に示す</p>"}


def _assembly(*middle):
    return {**BASE, "sections": [FIRST, *middle, CLOSING]}


def test_narrative_section_parses():
    req = validate_assembly(_assembly(NARR))
    sec = req.sections[1]
    assert isinstance(sec, NarrativeSection)
    assert sec.id == "sec-intro"
    assert "結論を先に示す" in sec.markup


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
    sec = NarrativeSection(id="sec-intro", markup="<p>結論</p>")
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
    # between typed first-screen and closing with a body narrative.
    canonical = json.loads((TESTS_DIR / "component-valid-enumeration.json").read_text("utf-8"))
    body = {"kind": "narrative", "id": "sec-body", "markup": "<p>補足の本文です。</p>"}
    # Keep typed bookends from the fixture; insert body narrative before closing.
    sections = list(canonical["sections"])
    # fixture is [first-screen, canonical, closing]
    sections.insert(-1, body)
    canonical["sections"] = sections
    return canonical


def test_build_document_orders_narrative_and_canonical_sections():
    raw = _mixed_narrative_assembly()
    doc = build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS_DIR, document_path="doc.html")
    i_first = doc.index('data-ve-section-kind="first-screen"')
    i_canonical = doc.index('data-ve-instance="sec-enum-list"')
    i_body = doc.index('data-ve-instance="sec-body"')
    i_closing = doc.index('data-ve-section-kind="closing"')
    assert i_first < i_canonical < i_body < i_closing
    assert doc.count('data-ve-section-kind="narrative"') == 1
    assert doc.count('data-ve-section-kind="canonical"') == 1


def test_compose_sections_rejects_duplicate_id_across_narrative_and_canonical():
    canonical_request = validate_assembly(
        json.loads((TESTS_DIR / "component-valid-enumeration.json").read_text("utf-8")))
    canonical_section = next(s for s in canonical_request.sections if isinstance(s, CanonicalSection))
    rendered = process_canonical_section(canonical_section, REGISTRY, TRUSTED_RENDERERS)
    narrative = process_narrative_section(NarrativeSection(id=rendered.instance_id, markup="<p>まとめ</p>"))
    with pytest.raises(ContractError) as exc:
        compose_sections([rendered, narrative])
    assert "duplicate_section_id" in exc.value.codes


def test_final_provenance_accepts_narrative_with_instance():
    content = ('<section data-ve-section-kind="narrative"'
               ' data-ve-instance="sec-intro"><p>結論</p></section>')
    assert validate_final_provenance(content) == []


def test_final_provenance_rejects_narrative_without_instance():
    content = '<section data-ve-section-kind="narrative"><p>結論</p></section>'
    diags = validate_final_provenance(content)
    assert any(d.code == "missing_provenance" for d in diags)


def _build_composition_and_document(raw):
    # Mirrors build_document's own dispatch/compose/flatten steps, but keeps
    # the intermediate CompositionResult around so the test can pass it as
    # ``expected`` to check_final_document directly (build_document only
    # returns the final HTML string).
    from ve_components.document_sections import render_ask, render_closing, render_first_screen
    from ve_components.model import AskSection, ClosingSection, FirstScreenSection

    request = validate_assembly(raw)
    items = []
    for section in request.sections:
        if isinstance(section, CanonicalSection):
            items.append(process_canonical_section(section, REGISTRY, TRUSTED_RENDERERS))
        elif isinstance(section, NarrativeSection):
            items.append(process_narrative_section(section))
        elif isinstance(section, FirstScreenSection):
            items.append(render_first_screen(section, request.document))
        elif isinstance(section, ClosingSection):
            items.append(render_closing(section))
        elif isinstance(section, AskSection):
            items.append(render_ask(section))
        else:
            items.append(process_compatibility_section(section))
    composition = compose_sections(items)
    document = flatten_document(composition, SKELETON, COMPONENTS_DIR, request.document.title)
    return composition, document


def test_manifest_to_dom_flags_narrative_section_removed_from_final_dom():
    raw = json.loads((TESTS_DIR / "component-valid-narrative-mixed.json").read_text("utf-8"))
    composition, document = _build_composition_and_document(raw)
    # Sanity: the untouched build passes the full four-layer checker.
    assert check_final_document(document, SKELETON, REGISTRY, expected=composition,
                                 components_dir=COMPONENTS_DIR) == []
    removed = composition.narrative[-1]
    mutated = document.replace(removed.markup, "")
    assert mutated != document
    diags = check_final_document(mutated, SKELETON, REGISTRY, expected=composition,
                                  components_dir=COMPONENTS_DIR)
    assert any(d.code == "missing_provenance" for d in diags)


def test_narrative_mixed_fixture_passes_check_sh():
    raw = json.loads((TESTS_DIR / "component-valid-narrative-mixed.json").read_text("utf-8"))
    document = build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS_DIR, document_path="doc.html")
    out = Path(tempfile.gettempdir()) / "ve-narrative-mixed-doc.html"
    out.write_text(document, "utf-8")
    try:
        proc = subprocess.run(["bash", str(CHECK), str(out)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "PASS" in proc.stdout + proc.stderr
    finally:
        out.unlink(missing_ok=True)
