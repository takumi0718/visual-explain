from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from ve_components.diagnostics import ContractError
from ve_components.validation import validate_assembly


def _flow_ir() -> dict:
    return {
        "id": "sec-flow",
        "relationship": {
            "kind": "directed-graph",
            "capabilities": ["ordered-transition", "typed-sequence"],
        },
        "selection": {
            "component": "flow",
            "version": 2,
            "matchedCapabilities": ["ordered-transition", "typed-sequence"],
        },
        "caption": "承認経路",
        "certainty": [
            {"id": "certainty-1", "level": "confirmed", "statement": "経路は確認済み。"}
        ],
        "sources": [{"id": "source-1", "label": "運用手順"}],
        "accessibility": {"label": "承認経路", "summary": "起案から公開までの経路。"},
        "flow": {
            "nodes": [
                {"id": "node-a", "label": "起案"},
                {"id": "node-b", "label": "確認"},
                {"id": "node-c", "label": "承認"},
                {"id": "node-d", "label": "公開"},
            ],
            "edges": [
                {"id": "edge-ab", "from": "node-a", "to": "node-b", "relation": "ordered-transition"},
                {"id": "edge-bc", "from": "node-b", "to": "node-c", "relation": "ordered-transition"},
                {"id": "edge-cd", "from": "node-c", "to": "node-d", "relation": "ordered-transition"},
            ],
            "startId": "node-a",
        },
        "claim": "承認経路は一本につながる。",
        "sequence": {
            "mode": "path-spotlight",
            "steps": [
                {"id": "step-a", "label": "確認まで", "targetIds": ["node-a", "node-b"]},
                {"id": "step-b", "label": "公開まで", "targetIds": ["node-c", "node-d"]},
            ],
        },
        "assertions": [
            {"id": "assertion-a", "text": "承認経路は一本につながる。", "coverIds": ["node-a"]}
        ],
    }


def _assembly(profile: str = "visual-stage", ir: dict | None = None) -> dict:
    return {
        "schemaVersion": 1,
        "document": {
            "id": "doc-1",
            "title": "承認資料",
            "summary": "承認経路を示す資料。",
            "type": "system",
            "profile": profile,
        },
        "sections": [
            {"kind": "first-screen", "id": "sec-first", "decision": "承認経路を採用します。"},
            {"kind": "canonical", "ir": deepcopy(ir if ir is not None else _flow_ir())},
            {
                "kind": "closing",
                "id": "sec-closing",
                "blocks": [{"heading": "限界・確度", "items": ["運用変更は未反映"]}],
            },
        ],
    }


def _messages(error: ContractError) -> str:
    return " ".join(str(d) for d in error.diagnostics)


def test_visual_stage_profile_parses_stage_fields_into_canonical_ir() -> None:
    request = validate_assembly(_assembly())

    ir = request.sections[1].ir
    assert request.document.profile == "visual-stage"
    assert ir.claim == "承認経路は一本につながる。"
    assert ir.sequence is not None
    assert ir.sequence.mode == "path-spotlight"
    assert ir.sequence.steps[1].target_ids == ("node-c", "node-d")
    assert ir.assertions is not None
    assert ir.assertions[0].cover_ids == ("node-a",)


@pytest.mark.parametrize("field", ["claim", "sequence", "assertions"])
@pytest.mark.parametrize("profile", ["strict", "extended"])
def test_existing_profiles_reject_each_stage_field(field: str, profile: str) -> None:
    ir = _flow_ir()
    for candidate in ("claim", "sequence", "assertions"):
        if candidate != field:
            del ir[candidate]

    with pytest.raises(ContractError) as exc:
        validate_assembly(_assembly(profile=profile, ir=ir))

    assert f"{field} は visual-stage profile でのみ使用できます" in _messages(exc.value)


@pytest.mark.parametrize("field,value", [
    ("takeawayTargetIds", ["node-a"]),
    ("emphasis", [{"targetId": "node-a", "label": "注目"}]),
])
def test_visual_stage_rejects_legacy_emphasis_fields(field: str, value: object) -> None:
    ir = _flow_ir()
    ir[field] = value

    with pytest.raises(ContractError) as exc:
        validate_assembly(_assembly(ir=ir))

    assert f"visual-stage では {field} を使用できません" in _messages(exc.value)


def _invalid_sequence(mutator) -> str:
    ir = _flow_ir()
    mutator(ir)
    with pytest.raises(ContractError) as exc:
        validate_assembly(_assembly(ir=ir))
    return _messages(exc.value)


@pytest.mark.parametrize("mutator,expected", [
    (lambda ir: ir["sequence"].pop("mode"), "sequence.mode は必須です"),
    (lambda ir: ir["sequence"].pop("steps"), "sequence.steps は必須です"),
    (lambda ir: ir["sequence"].update(mode="zoom"), "未知の sequence.mode 'zoom'"),
    (lambda ir: ir["sequence"].update(steps=ir["sequence"]["steps"][:1]), "sequence.steps は2〜8件"),
    (
        lambda ir: ir["sequence"].update(steps=ir["sequence"]["steps"] * 5),
        "sequence.steps は2〜8件",
    ),
    (lambda ir: ir["sequence"]["steps"][0].update(extra=True), "未知のフィールド 'extra'"),
    (lambda ir: ir["sequence"]["steps"][0].pop("id"), "step.id は必須です"),
    (lambda ir: ir["sequence"]["steps"][0].pop("label"), "step.label は必須です"),
    (lambda ir: ir["sequence"]["steps"][0].pop("targetIds"), "step.targetIds は必須です"),
    (lambda ir: ir["sequence"]["steps"][0].update(id="Bad_ID"), "step.id の形式が不正"),
    (
        lambda ir: ir["sequence"]["steps"][1].update(id="step-a"),
        "step.id 'step-a' が重複",
    ),
    (lambda ir: ir["sequence"]["steps"][0].update(label=""), "step.label は1〜40字"),
    (lambda ir: ir["sequence"]["steps"][0].update(label="x" * 41), "step.label は1〜40字"),
    (lambda ir: ir["sequence"]["steps"][0].update(targetIds=[]), "step.targetIds は非空"),
    (
        lambda ir: ir["sequence"]["steps"][0].update(targetIds=["node-a", "node-a"]),
        "step.targetIds 'node-a' が重複",
    ),
    (
        lambda ir: ir["sequence"]["steps"][0].update(targetIds=["missing-node"]),
        "targetId 'missing-node' は payload semantic id ではありません",
    ),
    (
        lambda ir: ir["sequence"]["steps"][0].update(targetIds=["step-a"]),
        "targetId 'step-a' は payload semantic id ではありません",
    ),
    (
        lambda ir: ir["sequence"]["steps"][0].update(targetIds=["edge-ab"]),
        "path-spotlight の対象は flow node id のみ",
    ),
])
def test_sequence_shape_and_payload_namespace_are_validated(mutator, expected: str) -> None:
    assert expected in _invalid_sequence(mutator)


@pytest.mark.parametrize("caps_key", ["relationship", "selection"])
def test_sequence_requires_typed_sequence_in_both_capability_declarations(caps_key: str) -> None:
    def mutate(ir: dict) -> None:
        key = "capabilities" if caps_key == "relationship" else "matchedCapabilities"
        ir[caps_key][key].remove("typed-sequence")

    messages = _invalid_sequence(mutate)
    assert f"{caps_key} に typed-sequence が必要です" in messages


def test_state_lens_rejects_non_state_payload_ids() -> None:
    def mutate(ir: dict) -> None:
        ir["sequence"] = {
            "mode": "state-lens",
            "steps": [
                {"id": "state-a", "label": "辺", "targetIds": ["edge-ab"]},
                {"id": "state-b", "label": "注記", "targetIds": ["source-1"]},
            ],
        }

    messages = _invalid_sequence(mutate)
    assert "state-lens の対象は状態を持つ payload 要素 id のみ" in messages
    assert "targetId 'source-1' は payload semantic id ではありません" in messages


def _bars_ir() -> dict:
    ir = {
        "id": "sec-bars",
        "relationship": {
            "kind": "quantitative-comparison",
            "capabilities": ["single-axis-quantity", "typed-sequence"],
        },
        "selection": {
            "component": "bars",
            "version": 2,
            "matchedCapabilities": ["single-axis-quantity", "typed-sequence"],
        },
        "caption": "比較",
        "certainty": [{"id": "certainty-1", "level": "confirmed", "statement": "確認済み。"}],
        "sources": [{"id": "source-1", "label": "統計"}],
        "accessibility": {"label": "棒グラフ", "summary": "2項目の比較。"},
        "bars": {
            "title": "比較",
            "unitLabel": "%",
            "items": [
                {"id": "bar-a", "label": "A", "value": "10", "valueText": "10%"},
                {"id": "bar-b", "label": "B", "value": "20", "valueText": "20%"},
            ],
        },
        "claim": "BはAより大きい。",
        "sequence": {
            "mode": "delta-accumulate",
            "steps": [
                {"id": "delta-a", "label": "A", "targetIds": ["bar-a"]},
                {"id": "delta-b", "label": "B", "targetIds": ["bar-b"]},
            ],
        },
        "assertions": [{"id": "assertion-bars", "text": "BはAより大きい。", "coverIds": ["bar-b"]}],
    }
    return ir


def test_mode_component_allowlist_rejects_bars_path_spotlight() -> None:
    ir = _bars_ir()
    ir["sequence"]["mode"] = "path-spotlight"

    with pytest.raises(ContractError) as exc:
        validate_assembly(_assembly(ir=ir))

    assert "path-spotlight は component 'bars' では使用できません" in _messages(exc.value)


def test_delta_accumulate_rejects_target_reused_by_later_step() -> None:
    ir = _bars_ir()
    ir["sequence"]["steps"][1]["targetIds"] = ["bar-a"]

    with pytest.raises(ContractError) as exc:
        validate_assembly(_assembly(ir=ir))

    assert "delta-accumulate の targetId 'bar-a' は先行 step と重複" in _messages(exc.value)


@pytest.mark.parametrize("mutator,expected", [
    (
        lambda ir: ir["sequence"]["steps"][0].update(targetIds=["node-a", "node-c"]),
        "path-spotlight step 内の node 'node-a' から 'node-c' へ辺接続がありません",
    ),
    (
        lambda ir: ir["sequence"]["steps"][1].update(targetIds=["node-b", "node-c"]),
        "path-spotlight の targetId 'node-b' は step 間で重複",
    ),
    (
        lambda ir: (
            ir["sequence"]["steps"][0].update(targetIds=["node-a"]),
            ir["sequence"]["steps"][1].update(targetIds=["node-c", "node-d"]),
        ),
        "path-spotlight step 間の node 'node-a' から 'node-c' へ辺接続がありません",
    ),
])
def test_path_spotlight_requires_one_disjoint_connected_path(mutator, expected: str) -> None:
    assert expected in _invalid_sequence(mutator)


def test_path_spotlight_limits_each_step_to_four_nodes() -> None:
    def mutate(ir: dict) -> None:
        ir["flow"]["nodes"].extend([
            {"id": "node-e", "label": "通知"},
            {"id": "node-f", "label": "完了"},
        ])
        ir["flow"]["edges"].extend([
            {"id": "edge-de", "from": "node-d", "to": "node-e", "relation": "ordered-transition"},
            {"id": "edge-ef", "from": "node-e", "to": "node-f", "relation": "ordered-transition"},
        ])
        ir["sequence"]["steps"][0]["targetIds"] = ["node-a", "node-b", "node-c", "node-d", "node-e"]
        ir["sequence"]["steps"][1]["targetIds"] = ["node-f"]

    assert "path-spotlight の1 step は最大4ノード" in _invalid_sequence(mutate)


def _invalid_ir(mutator) -> str:
    ir = _flow_ir()
    mutator(ir)
    with pytest.raises(ContractError) as exc:
        validate_assembly(_assembly(ir=ir))
    return _messages(exc.value)


@pytest.mark.parametrize("mutator,expected", [
    (lambda ir: ir.pop("claim"), "visual-stage canonical には claim が必須です"),
    (lambda ir: ir.update(claim=""), "claim は1〜80字である必要があります"),
    (lambda ir: ir.update(claim="x" * 81), "claim は1〜80字である必要があります"),
    (lambda ir: ir.pop("assertions"), "visual-stage canonical には assertions が必須です"),
    (lambda ir: ir.update(assertions=[]), "assertions は非空の配列である必要があります"),
    (lambda ir: ir["assertions"][0].update(extra=True), "未知のフィールド 'extra'"),
    (lambda ir: ir["assertions"][0].pop("id"), "assertion.id は必須です"),
    (lambda ir: ir["assertions"][0].pop("text"), "assertion.text は必須です"),
    (lambda ir: ir["assertions"][0].pop("coverIds"), "assertion.coverIds は必須です"),
    (lambda ir: ir["assertions"][0].update(id="Bad_ID"), "assertion.id の形式が不正"),
    (lambda ir: ir["assertions"][0].update(text=""), "assertion.text は1〜80字"),
    (lambda ir: ir["assertions"][0].update(text="x" * 81), "assertion.text は1〜80字"),
    (lambda ir: ir["assertions"][0].update(coverIds=[]), "assertion.coverIds は非空"),
    (
        lambda ir: ir["assertions"][0].update(coverIds=["node-a", "node-a"]),
        "assertion.coverIds 'node-a' が重複",
    ),
    (
        lambda ir: ir["assertions"][0].update(coverIds=["missing-node"]),
        "coverId 'missing-node' は payload semantic id ではありません",
    ),
    (
        lambda ir: ir["assertions"][0].update(coverIds=["step-a"]),
        "coverId 'step-a' は payload semantic id ではありません",
    ),
    (
        lambda ir: ir["assertions"][0].update(coverIds=["source-1"]),
        "coverId 'source-1' は payload semantic id ではありません",
    ),
    (lambda ir: ir.update(claim="inventory にない主張。"), "claim は assertions のいずれかの text と一致"),
])
def test_claim_and_assertion_contract(mutator, expected: str) -> None:
    assert expected in _invalid_ir(mutator)


def _assembly_with_second_canonical() -> dict:
    raw = _assembly()
    second_ir = _flow_ir()
    second_ir["id"] = "sec-flow-second"
    raw["sections"].insert(2, {"kind": "canonical", "ir": second_ir})
    return raw


@pytest.mark.parametrize("namespace,expected", [
    ("step", "step.id 'step-a' は文書内で重複しています"),
    ("assertion", "assertion.id 'assertion-a' は文書内で重複しています"),
])
def test_stage_ids_are_unique_across_canonical_sections(namespace: str, expected: str) -> None:
    raw = _assembly_with_second_canonical()
    if namespace == "step":
        raw["sections"][2]["ir"]["assertions"][0]["id"] = "assertion-b"
    else:
        raw["sections"][2]["ir"]["sequence"]["steps"][0]["id"] = "step-c"
        raw["sections"][2]["ir"]["sequence"]["steps"][1]["id"] = "step-d"

    with pytest.raises(ContractError) as exc:
        validate_assembly(raw)

    assert expected in _messages(exc.value)


def test_payload_step_and_assertion_ids_are_separate_namespaces() -> None:
    ir = _flow_ir()
    ir["sequence"]["steps"][0]["id"] = "node-a"
    ir["assertions"][0]["id"] = "node-a"

    request = validate_assembly(_assembly(ir=ir))

    assert request.sections[1].ir.sequence.steps[0].id == "node-a"
    assert request.sections[1].ir.assertions[0].id == "node-a"


def _narrative(section_id: str, text: str) -> dict:
    return {"kind": "narrative", "id": section_id, "markup": f"<p>{text}</p>"}


def _compatibility() -> dict:
    return {
        "kind": "compatibility",
        "id": "sec-compat",
        "markup": "<p>旧形式</p>",
        "provenance": {
            "source": "legacy-html-insertion",
            "reason": "unmigrated-format",
            "format": "freeform",
        },
    }


def test_visual_stage_requires_main_canonical_immediately_after_first_screen() -> None:
    raw = _assembly()
    raw["sections"].insert(1, _narrative("sec-context", "前提"))

    with pytest.raises(ContractError) as exc:
        validate_assembly(raw)

    assert "visual-stage は first-screen の直後に canonical 主図が必要です" in _messages(exc.value)


def test_visual_stage_rejects_compatibility_section() -> None:
    raw = _assembly()
    raw["sections"].insert(2, _compatibility())

    with pytest.raises(ContractError) as exc:
        validate_assembly(raw)

    assert "visual-stage では compatibility section を使用できません" in _messages(exc.value)


def test_visual_stage_accepts_two_narratives_of_exactly_200_plain_text_chars() -> None:
    raw = _assembly()
    raw["sections"].insert(2, _narrative("sec-context-a", "あ" * 200))
    raw["sections"].insert(3, _narrative("sec-context-b", "い" * 200))

    request = validate_assembly(raw)

    assert len(request.sections) == 5


@pytest.mark.parametrize("mutation,expected", [
    ("count", "visual-stage の narrative section は最大2件です"),
    ("length", "visual-stage の narrative plain text は200字以内です"),
])
def test_visual_stage_rejects_narrative_limits(mutation: str, expected: str) -> None:
    raw = _assembly()
    if mutation == "count":
        raw["sections"][2:2] = [
            _narrative("sec-context-a", "a"),
            _narrative("sec-context-b", "b"),
            _narrative("sec-context-c", "c"),
        ]
    else:
        raw["sections"].insert(2, _narrative("sec-context", "あ" * 201))

    with pytest.raises(ContractError) as exc:
        validate_assembly(raw)

    assert expected in _messages(exc.value)


@pytest.mark.parametrize("profile", ["strict", "extended"])
def test_existing_profiles_do_not_receive_visual_stage_document_limits(profile: str) -> None:
    raw = _assembly(profile=profile)
    ir = raw["sections"][1]["ir"]
    del ir["claim"]
    del ir["sequence"]
    del ir["assertions"]
    ir["relationship"]["capabilities"].remove("typed-sequence")
    ir["selection"]["matchedCapabilities"].remove("typed-sequence")
    raw["sections"][1:1] = [
        _narrative("sec-before-main", "前提"),
        _narrative("sec-long", "あ" * 201),
        _compatibility(),
    ]

    request = validate_assembly(raw)

    assert request.document.profile == profile
    assert len(request.sections) == 6


def _fixture_ir(filename: str, mode: str, target_ids: tuple[str, str]) -> dict:
    raw = json.loads(Path(__file__).with_name(filename).read_text("utf-8"))
    ir = deepcopy(raw["sections"][1]["ir"])
    ir["relationship"]["capabilities"].append("typed-sequence")
    ir["selection"]["matchedCapabilities"].append("typed-sequence")
    ir["claim"] = "対象を段階的に示す。"
    ir["sequence"] = {
        "mode": mode,
        "steps": [
            {"id": "step-one", "label": "第一段階", "targetIds": [target_ids[0]]},
            {"id": "step-two", "label": "第二段階", "targetIds": [target_ids[1]]},
        ],
    }
    ir["assertions"] = [
        {"id": "assertion-one", "text": "対象を段階的に示す。", "coverIds": [target_ids[0]]}
    ]
    return ir


@pytest.mark.parametrize("filename,mode,target_ids", [
    ("component-valid-flow.json", "state-lens", ("node-draft", "node-review")),
    ("component-valid-matrix.json", "state-lens", ("cell-admin-read", "cell-viewer-write")),
    ("component-valid-stairs.json", "state-lens", ("stage-1", "stage-2")),
    ("component-valid-waterfall.json", "delta-accumulate", ("wf-step-1", "wf-step-2")),
])
def test_all_remaining_allowed_mode_component_pairs_are_accepted(
    filename: str, mode: str, target_ids: tuple[str, str]
) -> None:
    request = validate_assembly(_assembly(ir=_fixture_ir(filename, mode, target_ids)))

    assert request.sections[1].ir.sequence.mode == mode


def test_state_lens_rejects_matrix_axis_id_even_though_it_is_a_payload_id() -> None:
    ir = _fixture_ir("component-valid-matrix.json", "state-lens", ("row-admin", "cell-admin-read"))

    with pytest.raises(ContractError) as exc:
        validate_assembly(_assembly(ir=ir))

    assert "state-lens の対象は状態を持つ payload 要素 id のみ" in _messages(exc.value)


def test_visual_stage_allows_claim_and_assertions_without_sequence() -> None:
    ir = _flow_ir()
    del ir["sequence"]
    ir["relationship"]["capabilities"].remove("typed-sequence")
    ir["selection"]["matchedCapabilities"].remove("typed-sequence")

    request = validate_assembly(_assembly(ir=ir))

    assert request.sections[1].ir.sequence is None
