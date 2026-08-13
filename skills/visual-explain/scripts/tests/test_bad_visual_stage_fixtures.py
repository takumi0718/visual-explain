"""Task 16: one visual-stage contract violation per committed bad fixture."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import pytest

from build_explainer import build_document
from ve_components.diagnostics import ContractError
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.validation import validate_assembly


SCRIPTS = Path(__file__).resolve().parents[1]
SKILL = SCRIPTS.parent
FIXTURES = Path(__file__).with_name("fixtures")
REFERENCES = SKILL / "references"
COMPONENTS = SKILL / "assets" / "components"
REGISTRY = load_registry(COMPONENTS / "registry.json")
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
IR_SCHEMA = json.loads((REFERENCES / "component-ir.schema.json").read_text("utf-8"))


@dataclass(frozen=True)
class BadCase:
    filename: str
    owner: str
    code: str
    message: str
    path: str
    extra_messages: tuple[str, ...] = ()


def _case(
    stem: str,
    owner: str,
    code: str,
    message: str,
    path: str,
    *extra_messages: str,
) -> BadCase:
    return BadCase(
        filename=f"bad-vs-{stem}.assembly.json",
        owner=owner,
        code=code,
        message=message,
        path=path,
        extra_messages=extra_messages,
    )


BAD_CASES = (
    _case("sequence-steps-9", "schema", "invalid_component_payload", "sequence.steps は2〜8件", "assembly.sections[1].ir.sequence"),
    _case("sequence-steps-1", "schema", "invalid_component_payload", "sequence.steps は2〜8件", "assembly.sections[1].ir.sequence"),
    _case("bars-path-spotlight", "validation", "invalid_component_payload", "path-spotlight は component 'bars'", "assembly.sections[1].ir"),
    _case("dangling-target-id", "validation", "invalid_component_payload", "targetId 'missing-node' は payload semantic id", "assembly.sections[1].ir"),
    _case("target-id-is-step-id", "validation", "invalid_component_payload", "targetId 'path-review' は payload semantic id", "assembly.sections[1].ir"),
    _case("duplicate-step-id", "validation", "duplicate_semantic_id", "step.id 'path-review' が重複", "assembly.sections[1].ir.sequence.steps[1]"),
    _case("invalid-step-id", "schema", "invalid_component_payload", "step.id の形式が不正", "assembly.sections[1].ir.sequence.steps[0]"),
    _case("unknown-step-field", "schema", "invalid_component_payload", "未知のフィールド 'extra'", "assembly.sections[1].ir.sequence.steps[0]"),
    _case("empty-step-label", "schema", "invalid_component_payload", "step.label は1〜40字", "assembly.sections[1].ir.sequence.steps[0]"),
    _case("long-step-label", "schema", "invalid_component_payload", "step.label は1〜40字", "assembly.sections[1].ir.sequence.steps[0]"),
    _case("empty-target-ids", "schema", "invalid_component_payload", "step.targetIds は非空", "assembly.sections[1].ir.sequence.steps[0]"),
    _case("duplicate-target-ids", "schema", "invalid_component_payload", "step.targetIds 'node-draft' が重複", "assembly.sections[1].ir.sequence.steps[0]"),
    _case("state-lens-source-target", "validation", "invalid_component_payload", "targetId 'flow-source' は payload semantic id", "assembly.sections[1].ir"),
    _case("compatibility-section", "validation", "invalid_component_payload", "visual-stage では compatibility section", "assembly.sections[2]"),
    _case("missing-claim", "validation", "missing_required_slot", "visual-stage canonical には claim が必須", "assembly.sections[1].ir"),
    _case("missing-assertions", "validation", "missing_required_slot", "visual-stage canonical には assertions が必須", "assembly.sections[1].ir"),
    _case("empty-assertions", "schema", "invalid_component_payload", "assertions は非空の配列", "assembly.sections[1].ir.assertions", "claim は assertions のいずれかの text と一致"),
    _case("invalid-assertion-id", "schema", "invalid_component_payload", "assertion.id の形式が不正", "assembly.sections[1].ir.assertions[0]"),
    _case("duplicate-document-assertion-id", "validation", "duplicate_semantic_id", "assertion.id 'flow-path-claim' は文書内で重複", "assembly.sections"),
    _case("empty-assertion-text", "schema", "invalid_component_payload", "assertion.text は1〜80字", "assembly.sections[1].ir.assertions[1]"),
    _case("long-assertion-text", "schema", "invalid_component_payload", "assertion.text は1〜80字", "assembly.sections[1].ir.assertions[1]"),
    _case("empty-cover-ids", "schema", "invalid_component_payload", "assertion.coverIds は非空", "assembly.sections[1].ir.assertions[1]"),
    _case("duplicate-cover-ids", "schema", "invalid_component_payload", "assertion.coverIds 'node-draft' が重複", "assembly.sections[1].ir.assertions[0]"),
    _case("dangling-cover-id", "validation", "invalid_component_payload", "coverId 'missing-node' は payload semantic id", "assembly.sections[1].ir"),
    _case("claim-not-in-assertions", "validation", "invalid_component_payload", "claim は assertions のいずれかの text と一致", "assembly.sections[1].ir"),
    _case("incomplete-assertion-coverage", "document-check", "document_structure_violation", "payload semantic id が assertions で未カバー", "content.canonical[flow-path]"),
    _case("delta-reused-target", "validation", "invalid_component_payload", "delta-accumulate の targetId 'b1' は先行 step と重複", "assembly.sections[1].ir"),
    _case("path-disconnected", "validation", "invalid_component_payload", "path-spotlight step 間の node 'node-review' から 'node-publish'", "assembly.sections[1].ir"),
    _case("path-overlapping-targets", "validation", "invalid_component_payload", "path-spotlight の targetId 'node-review' は step 間で重複", "assembly.sections[1].ir", "path-spotlight step 間の node 'node-review' から 'node-review'"),
    _case("three-narratives", "validation", "invalid_narrative_section", "visual-stage の narrative section は最大2件", "assembly.sections"),
    _case("narrative-201", "validation", "invalid_narrative_section", "visual-stage の narrative plain text は200字以内", "assembly.sections[2]"),
    _case("claim-narrative-overlap", "document-check", "document_structure_violation", "assertion 'flow-path-claim' と narrative 'context'", "content.narrative[context]"),
    _case("nonclaim-narrative-overlap", "document-check", "document_structure_violation", "assertion 'flow-path-detail' と narrative 'context'", "content.narrative[context]"),
    _case("strict-with-claim", "validation", "invalid_component_payload", "claim は visual-stage profile でのみ", "assembly.sections[1].ir"),
    _case("strict-with-sequence", "validation", "invalid_component_payload", "sequence は visual-stage profile でのみ", "assembly.sections[1].ir"),
    _case("strict-with-assertions", "validation", "invalid_component_payload", "assertions は visual-stage profile でのみ", "assembly.sections[1].ir"),
    _case("visual-stage-takeaway-targets", "validation", "invalid_component_payload", "visual-stage では takeawayTargetIds", "assembly.sections[1].ir"),
    _case("visual-stage-emphasis", "validation", "invalid_component_payload", "visual-stage では emphasis", "assembly.sections[1].ir"),
    _case("missing-sequence-mode", "schema", "missing_required_slot", "sequence.mode は必須", "assembly.sections[1].ir.sequence"),
    _case("missing-sequence-steps", "schema", "missing_required_slot", "sequence.steps は必須", "assembly.sections[1].ir.sequence"),
    _case("missing-step-id", "schema", "missing_required_slot", "step.id は必須", "assembly.sections[1].ir.sequence.steps[0]"),
    _case("missing-step-label", "schema", "missing_required_slot", "step.label は必須", "assembly.sections[1].ir.sequence.steps[0]"),
    _case("missing-step-target-ids", "schema", "missing_required_slot", "step.targetIds は必須", "assembly.sections[1].ir.sequence.steps[0]"),
    _case("missing-assertion-id", "schema", "missing_required_slot", "assertion.id は必須", "assembly.sections[1].ir.assertions[1]"),
    _case("missing-assertion-text", "schema", "missing_required_slot", "assertion.text は必須", "assembly.sections[1].ir.assertions[1]"),
    _case("missing-assertion-cover-ids", "schema", "missing_required_slot", "assertion.coverIds は必須", "assembly.sections[1].ir.assertions[1]"),
)


# filename -> (schema JSON pointer, keyword, literal expected value)
SCHEMA_CONTRACTS = {
    "bad-vs-sequence-steps-9.assembly.json": ("#/$defs/sequenceDeclaration/properties/steps", "maxItems", 8),
    "bad-vs-sequence-steps-1.assembly.json": ("#/$defs/sequenceDeclaration/properties/steps", "minItems", 2),
    "bad-vs-invalid-step-id.assembly.json": ("#/$defs/sequenceStep/properties/id", "pattern", "^[a-z0-9][a-z0-9-]{0,31}$"),
    "bad-vs-unknown-step-field.assembly.json": ("#/$defs/sequenceStep", "additionalProperties", False),
    "bad-vs-empty-step-label.assembly.json": ("#/$defs/sequenceStep/properties/label", "minLength", 1),
    "bad-vs-long-step-label.assembly.json": ("#/$defs/sequenceStep/properties/label", "maxLength", 40),
    "bad-vs-empty-target-ids.assembly.json": ("#/$defs/sequenceStep/properties/targetIds", "minItems", 1),
    "bad-vs-duplicate-target-ids.assembly.json": ("#/$defs/sequenceStep/properties/targetIds", "uniqueItems", True),
    "bad-vs-empty-assertions.assembly.json": ("#/properties/assertions", "minItems", 1),
    "bad-vs-invalid-assertion-id.assembly.json": ("#/$defs/assertion/properties/id", "pattern", "^[a-z0-9][a-z0-9-]{0,31}$"),
    "bad-vs-empty-assertion-text.assembly.json": ("#/$defs/assertion/properties/text", "minLength", 1),
    "bad-vs-long-assertion-text.assembly.json": ("#/$defs/assertion/properties/text", "maxLength", 80),
    "bad-vs-empty-cover-ids.assembly.json": ("#/$defs/assertion/properties/coverIds", "minItems", 1),
    "bad-vs-duplicate-cover-ids.assembly.json": ("#/$defs/assertion/properties/coverIds", "uniqueItems", True),
    "bad-vs-missing-sequence-mode.assembly.json": ("#/$defs/sequenceDeclaration", "required", "mode"),
    "bad-vs-missing-sequence-steps.assembly.json": ("#/$defs/sequenceDeclaration", "required", "steps"),
    "bad-vs-missing-step-id.assembly.json": ("#/$defs/sequenceStep", "required", "id"),
    "bad-vs-missing-step-label.assembly.json": ("#/$defs/sequenceStep", "required", "label"),
    "bad-vs-missing-step-target-ids.assembly.json": ("#/$defs/sequenceStep", "required", "targetIds"),
    "bad-vs-missing-assertion-id.assembly.json": ("#/$defs/assertion", "required", "id"),
    "bad-vs-missing-assertion-text.assembly.json": ("#/$defs/assertion", "required", "text"),
    "bad-vs-missing-assertion-cover-ids.assembly.json": ("#/$defs/assertion", "required", "coverIds"),
}

REQUIRED_OMISSION_CASES = {
    "bad-vs-missing-sequence-mode.assembly.json",
    "bad-vs-missing-sequence-steps.assembly.json",
    "bad-vs-missing-step-id.assembly.json",
    "bad-vs-missing-step-label.assembly.json",
    "bad-vs-missing-step-target-ids.assembly.json",
    "bad-vs-missing-assertion-id.assembly.json",
    "bad-vs-missing-assertion-text.assembly.json",
    "bad-vs-missing-assertion-cover-ids.assembly.json",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def _schema_node(pointer: str) -> object:
    node: object = IR_SCHEMA
    for token in pointer.removeprefix("#/").split("/"):
        assert isinstance(node, dict)
        node = node[token.replace("~1", "/").replace("~0", "~")]
    return node


def _full_build(raw: dict) -> str:
    return build_document(
        raw,
        REGISTRY,
        TRUSTED_RENDERERS,
        SKELETON,
        COMPONENTS,
        document_path="bad-visual-stage-fixture.html",
    )


def test_bad_visual_stage_inventory_is_exactly_46_unique_committed_fixtures() -> None:
    names = [case.filename for case in BAD_CASES]
    assert len(names) == 46
    assert len(set(names)) == 46
    assert {case.owner for case in BAD_CASES} == {"schema", "validation", "document-check"}
    assert [case.owner for case in BAD_CASES].count("schema") == 22
    assert [case.owner for case in BAD_CASES].count("validation") == 21
    assert [case.owner for case in BAD_CASES].count("document-check") == 3
    assert set(SCHEMA_CONTRACTS) == {case.filename for case in BAD_CASES if case.owner == "schema"}
    assert len(REQUIRED_OMISSION_CASES) == 8
    assert REQUIRED_OMISSION_CASES <= set(names)
    assert set(names) == {path.name for path in FIXTURES.glob("bad-vs-*.assembly.json")}


@pytest.mark.parametrize("case", BAD_CASES, ids=lambda case: case.filename)
def test_each_bad_visual_stage_fixture_fails_at_its_owned_boundary(case: BadCase) -> None:
    raw = _load(FIXTURES / case.filename)

    if case.owner == "document-check":
        # A document-check fixture must survive the earlier raw-IR boundary;
        # otherwise its intended rendered-document diagnostic could be masked.
        validate_assembly(raw)
    else:
        # validation.py is the executable, diagnostic-bearing mirror of
        # component-ir.schema.json used by the build pipeline.
        with pytest.raises(ContractError) as validation_caught:
            validate_assembly(raw)

    with pytest.raises(ContractError) as caught:
        _full_build(raw)

    if case.owner != "document-check":
        assert validation_caught.value.diagnostics == caught.value.diagnostics

    diagnostics = caught.value.diagnostics
    assert diagnostics[0].code == case.code
    assert case.message in diagnostics[0].message
    assert diagnostics[0].path == case.path
    assert len(diagnostics) == 1 + len(case.extra_messages)
    assert tuple(message in diagnostic.message for message, diagnostic in zip(case.extra_messages, diagnostics[1:])) == tuple(True for _ in case.extra_messages)


def test_schema_owned_bad_fixtures_are_backed_by_the_authoritative_keywords() -> None:
    for filename, (pointer, keyword, expected) in SCHEMA_CONTRACTS.items():
        node = _schema_node(pointer)
        assert isinstance(node, dict), filename
        actual = node[keyword]
        if keyword == "required":
            assert expected in actual, filename
        else:
            assert actual == expected, filename


def test_each_bad_fixture_has_a_valid_positive_counterpart() -> None:
    for path in sorted(FIXTURES.glob("vs-*.assembly.json")):
        assert isinstance(_full_build(_load(path)), str), path.name


def test_bad_fixture_numeric_boundaries_have_immediate_valid_neighbors() -> None:
    steps_9 = _load(FIXTURES / "bad-vs-sequence-steps-9.assembly.json")
    del steps_9["sections"][1]["ir"]["sequence"]["steps"][8]
    assert isinstance(_full_build(steps_9), str)

    steps_1 = _load(FIXTURES / "bad-vs-sequence-steps-1.assembly.json")
    steps_1["sections"][1]["ir"]["sequence"]["steps"].append(
        {"id": "state-boundary", "label": "段階2", "targetIds": ["node-publish"]}
    )
    assert isinstance(_full_build(steps_1), str)

    narrative_201 = _load(FIXTURES / "bad-vs-narrative-201.assembly.json")
    narrative_201["sections"][2]["markup"] = f"<p>{'あ' * 200}</p>"
    assert isinstance(_full_build(narrative_201), str)

    for filename, value in (
        ("bad-vs-empty-step-label.assembly.json", "x"),
        ("bad-vs-long-step-label.assembly.json", "x" * 40),
    ):
        raw = _load(FIXTURES / filename)
        raw["sections"][1]["ir"]["sequence"]["steps"][0]["label"] = value
        assert isinstance(_full_build(raw), str)

    for filename, value in (
        ("bad-vs-empty-assertion-text.assembly.json", "x"),
        ("bad-vs-long-assertion-text.assembly.json", "x" * 80),
    ):
        raw = _load(FIXTURES / filename)
        raw["sections"][1]["ir"]["assertions"][1]["text"] = value
        assert isinstance(_full_build(raw), str)


def test_cascading_diagnostics_have_one_edit_valid_counterparts() -> None:
    empty_assertions = _load(FIXTURES / "bad-vs-empty-assertions.assembly.json")
    empty_assertions["sections"][1]["ir"]["assertions"] = [
        {
            "id": "flow-path-claim",
            "text": "主要な承認経路を段階ごとに追跡できる。",
            "coverIds": [
                "node-draft",
                "node-review",
                "node-approve",
                "node-publish",
                "edge-draft-review",
                "edge-review-approve",
                "edge-approve-publish",
                "edge-draft-approve",
            ],
        }
    ]
    assert isinstance(_full_build(empty_assertions), str)

    overlapping_path = _load(FIXTURES / "bad-vs-path-overlapping-targets.assembly.json")
    overlapping_path["sections"][1]["ir"]["sequence"]["steps"][1]["targetIds"] = [
        "node-approve",
        "node-publish",
    ]
    assert isinstance(_full_build(overlapping_path), str)
