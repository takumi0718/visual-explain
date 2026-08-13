"""Task 16: one visual-stage contract violation per committed bad fixture."""
from __future__ import annotations

from copy import deepcopy
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
    extra_diagnostics: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True)
class Correction:
    operation: str
    path: str
    value: object | None = None


def _case(
    stem: str,
    owner: str,
    code: str,
    message: str,
    path: str,
    *extra_diagnostics: tuple[str, str, str],
) -> BadCase:
    return BadCase(
        filename=f"bad-vs-{stem}.assembly.json",
        owner=owner,
        code=code,
        message=message,
        path=path,
        extra_diagnostics=extra_diagnostics,
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
    _case("empty-assertions", "schema", "invalid_component_payload", "assertions は非空の配列", "assembly.sections[1].ir.assertions", ("invalid_component_payload", "claim は assertions のいずれかの text と一致", "assembly.sections[1].ir")),
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
    _case("path-overlapping-targets", "validation", "invalid_component_payload", "path-spotlight の targetId 'node-review' は step 間で重複", "assembly.sections[1].ir", ("invalid_component_payload", "path-spotlight step 間の node 'node-review' から 'node-review'", "assembly.sections[1].ir")),
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

# One literal JSON operation repairs each fixture. Values are test-owned
# contract examples; none are derived from production schemas or validators.
_FLOW_ASSERTIONS = [{
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
}]
_FLOW_STEPS = [
    {"id": "path-review", "label": "確認まで", "targetIds": ["node-draft", "node-review"]},
    {"id": "path-publish", "label": "公開まで", "targetIds": ["node-approve", "node-publish"]},
]
CORRECTIONS = {
    "bad-vs-sequence-steps-9.assembly.json": Correction("remove", "/sections/1/ir/sequence/steps/8"),
    "bad-vs-sequence-steps-1.assembly.json": Correction("add", "/sections/1/ir/sequence/steps/-", {"id": "state-boundary", "label": "段階2", "targetIds": ["node-publish"]}),
    "bad-vs-bars-path-spotlight.assembly.json": Correction("replace", "/sections/1/ir/sequence/mode", "delta-accumulate"),
    "bad-vs-dangling-target-id.assembly.json": Correction("replace", "/sections/1/ir/sequence/steps/0/targetIds/0", "node-draft"),
    "bad-vs-target-id-is-step-id.assembly.json": Correction("replace", "/sections/1/ir/sequence/steps/0/targetIds/0", "node-draft"),
    "bad-vs-duplicate-step-id.assembly.json": Correction("replace", "/sections/1/ir/sequence/steps/1/id", "path-publish"),
    "bad-vs-invalid-step-id.assembly.json": Correction("replace", "/sections/1/ir/sequence/steps/0/id", "path-review"),
    "bad-vs-unknown-step-field.assembly.json": Correction("remove", "/sections/1/ir/sequence/steps/0/extra"),
    "bad-vs-empty-step-label.assembly.json": Correction("replace", "/sections/1/ir/sequence/steps/0/label", "確認まで"),
    "bad-vs-long-step-label.assembly.json": Correction("replace", "/sections/1/ir/sequence/steps/0/label", "x" * 40),
    "bad-vs-empty-target-ids.assembly.json": Correction("replace", "/sections/1/ir/sequence/steps/0/targetIds", ["node-draft", "node-review"]),
    "bad-vs-duplicate-target-ids.assembly.json": Correction("replace", "/sections/1/ir/sequence/steps/0/targetIds", ["node-draft", "node-review"]),
    "bad-vs-state-lens-source-target.assembly.json": Correction("replace", "/sections/1/ir/sequence/steps/0/targetIds/0", "node-draft"),
    "bad-vs-compatibility-section.assembly.json": Correction("remove", "/sections/2"),
    "bad-vs-missing-claim.assembly.json": Correction("add", "/sections/1/ir/claim", "主要な承認経路を段階ごとに追跡できる。"),
    "bad-vs-missing-assertions.assembly.json": Correction("add", "/sections/1/ir/assertions", _FLOW_ASSERTIONS),
    "bad-vs-empty-assertions.assembly.json": Correction("replace", "/sections/1/ir/assertions", _FLOW_ASSERTIONS),
    "bad-vs-invalid-assertion-id.assembly.json": Correction("replace", "/sections/1/ir/assertions/0/id", "flow-path-claim"),
    "bad-vs-duplicate-document-assertion-id.assembly.json": Correction("replace", "/sections/2/ir/assertions/0/id", "flow-path-claim-second"),
    "bad-vs-empty-assertion-text.assembly.json": Correction("replace", "/sections/1/ir/assertions/1/text", "補足主張。"),
    "bad-vs-long-assertion-text.assembly.json": Correction("replace", "/sections/1/ir/assertions/1/text", "x" * 80),
    "bad-vs-empty-cover-ids.assembly.json": Correction("replace", "/sections/1/ir/assertions/1/coverIds", ["node-draft"]),
    "bad-vs-duplicate-cover-ids.assembly.json": Correction("remove", "/sections/1/ir/assertions/0/coverIds/8"),
    "bad-vs-dangling-cover-id.assembly.json": Correction("remove", "/sections/1/ir/assertions/0/coverIds/8"),
    "bad-vs-claim-not-in-assertions.assembly.json": Correction("replace", "/sections/1/ir/claim", "主要な承認経路を段階ごとに追跡できる。"),
    "bad-vs-incomplete-assertion-coverage.assembly.json": Correction("replace", "/sections/1/ir/assertions/0/coverIds", _FLOW_ASSERTIONS[0]["coverIds"]),
    "bad-vs-delta-reused-target.assembly.json": Correction("replace", "/sections/1/ir/sequence/steps/1/targetIds/0", "b2"),
    "bad-vs-path-disconnected.assembly.json": Correction("replace", "/sections/1/ir/sequence/steps/1/targetIds", ["node-approve", "node-publish"]),
    "bad-vs-path-overlapping-targets.assembly.json": Correction("replace", "/sections/1/ir/sequence/steps/1/targetIds", ["node-approve", "node-publish"]),
    "bad-vs-three-narratives.assembly.json": Correction("remove", "/sections/4"),
    "bad-vs-narrative-201.assembly.json": Correction("replace", "/sections/2/markup", f"<p>{'あ' * 200}</p>"),
    "bad-vs-claim-narrative-overlap.assembly.json": Correction("replace", "/sections/2/markup", "<p>図外の背景条件。</p>"),
    "bad-vs-nonclaim-narrative-overlap.assembly.json": Correction("replace", "/sections/2/markup", "<p>図外の背景条件。</p>"),
    "bad-vs-strict-with-claim.assembly.json": Correction("remove", "/sections/1/ir/claim"),
    "bad-vs-strict-with-sequence.assembly.json": Correction("remove", "/sections/1/ir/sequence"),
    "bad-vs-strict-with-assertions.assembly.json": Correction("remove", "/sections/1/ir/assertions"),
    "bad-vs-visual-stage-takeaway-targets.assembly.json": Correction("remove", "/sections/1/ir/takeawayTargetIds"),
    "bad-vs-visual-stage-emphasis.assembly.json": Correction("remove", "/sections/1/ir/emphasis"),
    "bad-vs-missing-sequence-mode.assembly.json": Correction("add", "/sections/1/ir/sequence/mode", "path-spotlight"),
    "bad-vs-missing-sequence-steps.assembly.json": Correction("add", "/sections/1/ir/sequence/steps", _FLOW_STEPS),
    "bad-vs-missing-step-id.assembly.json": Correction("add", "/sections/1/ir/sequence/steps/0/id", "path-review"),
    "bad-vs-missing-step-label.assembly.json": Correction("add", "/sections/1/ir/sequence/steps/0/label", "確認まで"),
    "bad-vs-missing-step-target-ids.assembly.json": Correction("add", "/sections/1/ir/sequence/steps/0/targetIds", ["node-draft", "node-review"]),
    "bad-vs-missing-assertion-id.assembly.json": Correction("add", "/sections/1/ir/assertions/1/id", "flow-path-detail"),
    "bad-vs-missing-assertion-text.assembly.json": Correction("add", "/sections/1/ir/assertions/1/text", "補足主張。"),
    "bad-vs-missing-assertion-cover-ids.assembly.json": Correction("add", "/sections/1/ir/assertions/1/coverIds", ["node-draft"]),
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


def _pointer_parent(document: object, pointer: str) -> tuple[object, str]:
    tokens = [
        token.replace("~1", "/").replace("~0", "~")
        for token in pointer.removeprefix("/").split("/")
    ]
    parent = document
    for token in tokens[:-1]:
        parent = parent[int(token)] if isinstance(parent, list) else parent[token]
    return parent, tokens[-1]


def _apply_correction(raw: dict, correction: Correction) -> dict:
    repaired = deepcopy(raw)
    parent, token = _pointer_parent(repaired, correction.path)
    if correction.operation == "replace":
        key = int(token) if isinstance(parent, list) else token
        assert parent[key] != correction.value
        parent[key] = deepcopy(correction.value)
    elif correction.operation == "add":
        if isinstance(parent, list):
            assert token == "-"
            parent.append(deepcopy(correction.value))
        else:
            assert token not in parent
            parent[token] = deepcopy(correction.value)
    elif correction.operation == "remove":
        key = int(token) if isinstance(parent, list) else token
        del parent[key]
    else:
        raise AssertionError(f"unknown correction operation: {correction.operation}")
    return repaired


def _assert_only_declared_structural_edit(
    before: dict,
    after: dict,
    correction: Correction,
) -> None:
    restored = deepcopy(after)
    before_parent, before_token = _pointer_parent(before, correction.path)
    after_parent, after_token = _pointer_parent(restored, correction.path)

    if correction.operation == "replace":
        before_key = int(before_token) if isinstance(before_parent, list) else before_token
        after_key = int(after_token) if isinstance(after_parent, list) else after_token
        assert before_parent[before_key] != after_parent[after_key]
        after_parent[after_key] = deepcopy(before_parent[before_key])
    elif correction.operation == "add":
        if isinstance(after_parent, list):
            assert after_token == "-"
            assert after_parent[-1] == correction.value
            after_parent.pop()
        else:
            assert before_token not in before_parent
            assert after_parent[after_token] == correction.value
            del after_parent[after_token]
    else:
        before_key = int(before_token) if isinstance(before_parent, list) else before_token
        removed = deepcopy(before_parent[before_key])
        if isinstance(after_parent, list):
            after_parent.insert(int(after_token), removed)
        else:
            assert after_token not in after_parent
            after_parent[after_token] = removed

    assert restored == before


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


def test_cover_reference_fixtures_append_one_bad_id_to_complete_coverage() -> None:
    valid = _load(FIXTURES / "vs-flow-path-spotlight.assembly.json")
    complete = valid["sections"][1]["ir"]["assertions"][0]["coverIds"]

    duplicate = _load(FIXTURES / "bad-vs-duplicate-cover-ids.assembly.json")
    dangling = _load(FIXTURES / "bad-vs-dangling-cover-id.assembly.json")

    assert duplicate["sections"][1]["ir"]["assertions"][0]["coverIds"] == [
        *complete,
        "node-draft",
    ]
    assert dangling["sections"][1]["ir"]["assertions"][0]["coverIds"] == [
        *complete,
        "missing-node",
    ]


def test_every_bad_case_declares_one_explicit_correction() -> None:
    assert set(CORRECTIONS) == {case.filename for case in BAD_CASES}


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
    expected = (
        (case.code, case.message, case.path),
        *case.extra_diagnostics,
    )
    assert len(diagnostics) == len(expected)
    for diagnostic, (code, message, path) in zip(diagnostics, expected, strict=True):
        assert diagnostic.code == code
        assert message in diagnostic.message
        assert diagnostic.path == path


def test_schema_owned_bad_fixtures_are_backed_by_the_authoritative_keywords() -> None:
    for filename, (pointer, keyword, expected) in SCHEMA_CONTRACTS.items():
        node = _schema_node(pointer)
        assert isinstance(node, dict), filename
        actual = node[keyword]
        if keyword == "required":
            assert expected in actual, filename
        else:
            assert actual == expected, filename


@pytest.mark.parametrize("case", BAD_CASES, ids=lambda case: case.filename)
def test_each_bad_fixture_has_one_explicit_validating_correction(case: BadCase) -> None:
    raw = _load(FIXTURES / case.filename)
    correction = CORRECTIONS[case.filename]
    repaired = _apply_correction(raw, correction)

    _assert_only_declared_structural_edit(raw, repaired, correction)
    validate_assembly(repaired)
    assert isinstance(_full_build(repaired), str)
