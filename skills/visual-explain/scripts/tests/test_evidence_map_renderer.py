"""S6 tests: evidence-map validation and renderer DOM contract."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

from ve_components.checker import check_final_document
from ve_components.diagnostics import ContractError
from ve_components.model import CanonicalSection
from ve_components.registry import load_registry
from ve_components.validation import validate_canonical_section

EVIDENCE_MAP_STRUCTURE_VIOLATION = "evidence_map_structure_violation"

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS = SKILL / "assets" / "components"
EM_DEF = REGISTRY.find("evidence-map", 2)


def _base_ir(**em_overrides) -> dict:
    em = {
        "conclusion": {"id": "conc", "label": "主張"},
        "evidence": [
            {"id": "ev-1", "label": "根拠1", "certaintyRef": "cert-1"},
            {"id": "ev-2", "label": "根拠2", "certaintyRef": "cert-2", "sourceRef": "src-1"},
        ],
    }
    em.update(em_overrides)
    return {
        "id": "sec-em",
        "relationship": {"kind": "claim-support", "capabilities": ["claim-support-mapping"]},
        "selection": {
            "component": "evidence-map",
            "version": 2,
            "matchedCapabilities": ["claim-support-mapping"],
        },
        "caption": "論拠",
        "certainty": [
            {"id": "cert-1", "level": "confirmed", "statement": "確定。"},
            {"id": "cert-2", "level": "inferred", "statement": "推定。"},
        ],
        "sources": [{"id": "src-1", "label": "出典"}],
        "accessibility": {"label": "論拠地図", "summary": "結論と根拠。"},
        "evidence-map": em,
    }


def validate_raw(ir: dict):
    return validate_canonical_section(ir)


def expect_violation(ir: dict, code: str = EVIDENCE_MAP_STRUCTURE_VIOLATION) -> None:
    with unittest.TestCase().assertRaises(ContractError) as ctx:
        validate_raw(ir)
    codes = {d.code for d in ctx.exception.diagnostics}
    unittest.TestCase().assertIn(code, codes)


def render_fixture(name: str):
    from ve_components.renderers.evidence_map import render_evidence_map

    path = TESTS / name if name.endswith(".json") else TESTS / f"{name}.json"
    raw = json.loads(path.read_text("utf-8"))
    ir = validate_canonical_section(raw["sections"][0]["ir"])
    result = render_evidence_map(CanonicalSection(ir=ir), EM_DEF)
    return SimpleNamespace(ir=ir, result=result, markup=result.markup)


class EvidenceMapValidationTest(unittest.TestCase):
    def test_rejects_unresolved_certainty_ref(self) -> None:
        raw = json.loads((TESTS / "component-bad-evidence-map-unresolved-certainty.json").read_text("utf-8"))
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(raw["sections"][0]["ir"])
        self.assertIn(EVIDENCE_MAP_STRUCTURE_VIOLATION, {d.code for d in ctx.exception.diagnostics})

    def test_rejects_unresolved_source_ref(self) -> None:
        raw = json.loads((TESTS / "component-bad-evidence-map-unresolved-source.json").read_text("utf-8"))
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(raw["sections"][0]["ir"])
        self.assertIn(EVIDENCE_MAP_STRUCTURE_VIOLATION, {d.code for d in ctx.exception.diagnostics})

    def test_rejects_too_many_evidence(self) -> None:
        raw = json.loads((TESTS / "component-bad-evidence-map-too-many-evidence.json").read_text("utf-8"))
        with self.assertRaises(ContractError) as ctx:
            validate_canonical_section(raw["sections"][0]["ir"])
        self.assertIn(EVIDENCE_MAP_STRUCTURE_VIOLATION, {d.code for d in ctx.exception.diagnostics})

    def test_rejects_one_evidence(self) -> None:
        ir = _base_ir(evidence=[{"id": "ev-1", "label": "のみ", "certaintyRef": "cert-1"}])
        expect_violation(ir)


class EvidenceMapMarkupTest(unittest.TestCase):
    def setUp(self) -> None:
        fixture = render_fixture("component-valid-evidence-map.json")
        self.ir = fixture.ir
        self.result = fixture.result
        self.markup = fixture.markup

    def test_conclusion_uses_navy_fill(self) -> None:
        self.assertIn('class="ve-em-conclusion"', self.markup)
        self.assertNotIn("ve-em-border-strong", self.markup)

    def test_evidence_cards_have_certainty_ref(self) -> None:
        for item in self.ir.evidence_map.evidence:
            self.assertIn(f'data-ve-certainty-ref="{item.certainty_ref}"', self.markup)

    def test_optional_source_ref_on_card(self) -> None:
        item = next(i for i in self.ir.evidence_map.evidence if i.source_ref)
        self.assertIn(f'data-ve-source-ref="{item.source_ref}"', self.markup)

    def test_branch_classes_from_certainty(self) -> None:
        self.assertIn("ve-em-solid", self.markup)
        self.assertIn("ve-em-dashed", self.markup)

    def test_monochrome_certainty_badge_on_each_card(self) -> None:
        for item in self.ir.evidence_map.evidence:
            block = re.search(
                rf'<div[^>]*data-ve-semantic-id="{re.escape(item.id)}"[^>]*>.*?</div>',
                self.markup,
                re.DOTALL,
            )
            self.assertIsNotNone(block)
            self.assertIn("ve-cert", block.group(0))

    def test_no_data_ve_from_or_to(self) -> None:
        self.assertNotIn("data-ve-from", self.markup)
        self.assertNotIn("data-ve-to", self.markup)

    def test_evidence_map_v2_uses_spine_children(self) -> None:
        markup = render_fixture("component-valid-evidence-map").markup
        self.assertIn('class="ve-em-body"', markup)
        self.assertIn("ve-em-solid", markup)   # 確認済み=実線の枝


class EvidenceMapReferencesFixtureTest(unittest.TestCase):
    def test_evidence_map_references_bad_fixture(self) -> None:
        raw = (TESTS / "component-bad-evidence-map-references.html").read_text("utf-8")
        codes = [d.code for d in check_final_document(raw, SKELETON, REGISTRY, components_dir=COMPONENTS)]
        violations = [c for c in codes if c == EVIDENCE_MAP_STRUCTURE_VIOLATION]
        self.assertGreaterEqual(len(violations), 2)

    def test_empty_ve_cert_bad_fixture(self) -> None:
        raw = (TESTS / "component-bad-evidence-map-empty-cert.html").read_text("utf-8")
        codes = [d.code for d in check_final_document(raw, SKELETON, REGISTRY, components_dir=COMPONENTS)]
        self.assertIn(EVIDENCE_MAP_STRUCTURE_VIOLATION, codes)
        self.assertIn("ve-cert", " ".join(d.message for d in check_final_document(
            raw, SKELETON, REGISTRY, components_dir=COMPONENTS
        ) if d.code == EVIDENCE_MAP_STRUCTURE_VIOLATION))


if __name__ == "__main__":
    unittest.main()
