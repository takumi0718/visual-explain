"""Task 12 visual-stage information-completeness checks."""
from __future__ import annotations

from dataclasses import replace

from ve_components.assembly import ExpectedCanonicalRecord
from ve_components.document_checks import check_document_structure
from ve_components.model import Assertion, SequenceDeclaration, SequenceStep


def _record(
    *,
    instance_id: str = "sec-map",
    payload_ids: frozenset[str] = frozenset({"node-a", "node-b"}),
    claim: str | None = "A & B are covered",
    assertions: tuple[Assertion, ...] | None = (
        Assertion("coverage", "A & B are covered", ("node-a", "node-b")),
    ),
    sequence: SequenceDeclaration | None = None,
) -> ExpectedCanonicalRecord:
    return ExpectedCanonicalRecord(
        component_id="flow",
        instance_id=instance_id,
        payload_semantic_ids=payload_ids,
        claim=claim,
        assertions=assertions,
        sequence=sequence,
    )


def _content(
    *,
    profile: str = "visual-stage",
    claim_markup: str = "A &amp; B are covered",
    narratives: tuple[str, ...] = (),
    canonical_instance: str = "sec-map",
) -> str:
    narrative_markup = "".join(
        f'<section data-ve-section-kind="narrative" data-ve-instance="n-{index}">{text}</section>'
        for index, text in enumerate(narratives, 1)
    )
    return (
        f'<section data-ve-section-kind="first-screen" data-ve-document-type="proposal" '
        f'data-ve-profile="{profile}"><h1>Title</h1><p class="subtitle">Summary</p></section>'
        f'<section data-ve-section-kind="canonical" data-ve-component="flow" '
        f'data-ve-instance="{canonical_instance}">'
        f'<p class="ve-claim">{claim_markup}</p><figure data-ve-component="flow"></figure></section>'
        f'{narrative_markup}'
        '<section data-ve-section-kind="closing"><h2>リスクと弱い前提</h2>'
        '<h2>不確かな点</h2></section>'
    )


def _visual_messages(content: str, expected) -> list[str]:
    return [
        diagnostic.message
        for diagnostic in check_document_structure(content, title="Title", expected=expected)
        if "visual-stage" in diagnostic.message
    ]


def test_valid_expected_record_accepts_entity_decoded_exact_claim() -> None:
    assert _visual_messages(_content(narratives=("x" * 200,)), (_record(),)) == []


def test_non_visual_stage_returns_before_expected_completeness_checks() -> None:
    broken = replace(_record(), claim=None, assertions=None)
    assert _visual_messages(_content(profile="strict", claim_markup="tampered"), (broken,)) == []


def test_expected_record_is_fail_closed_when_build_path_supplies_no_records() -> None:
    messages = _visual_messages(_content(), ())
    assert any("expected record" in message for message in messages)


def test_claim_and_assertions_are_required_and_claim_must_be_in_inventory() -> None:
    missing = replace(_record(), claim=None, assertions=None)
    messages = _visual_messages(_content(), (missing,))
    assert any("claim" in message and "必須" in message for message in messages)
    assert any("assertions" in message and "必須" in message for message in messages)

    mismatched = replace(
        _record(),
        assertions=(Assertion("other", "A different assertion", ("node-a", "node-b")),),
    )
    messages = _visual_messages(_content(), (mismatched,))
    assert any("assertion.text" in message and "一致" in message for message in messages)


def test_claim_text_must_match_the_claim_in_its_canonical_section_exactly() -> None:
    messages = _visual_messages(_content(claim_markup="A  &amp; B are covered"), (_record(),))
    assert any(".ve-claim" in message and "一致" in message for message in messages)


def test_cover_ids_must_exist_and_union_must_cover_payload_in_stable_order() -> None:
    record = replace(
        _record(),
        payload_semantic_ids=frozenset({"z-last", "a-first"}),
        assertions=(Assertion("coverage", "A & B are covered", ("missing", "z-last")),),
    )
    messages = _visual_messages(_content(), (record,))
    assert any("coverIds" in message and "missing" in message for message in messages)
    assert any("未カバー" in message and "a-first" in message for message in messages)


def test_sequence_targets_must_exist_and_step_ids_are_document_unique() -> None:
    sequence = SequenceDeclaration("state-lens", (
        SequenceStep("same-step", "one", ("node-a",)),
        SequenceStep("same-step", "two", ("missing",)),
    ))
    messages = _visual_messages(_content(), (replace(_record(), sequence=sequence),))
    assert any("targetIds" in message and "missing" in message for message in messages)
    assert any("step id" in message and "same-step" in message and "重複" in message for message in messages)


def test_visual_stage_narrative_limits_are_rechecked_from_rendered_dom() -> None:
    too_many = _visual_messages(_content(narratives=("a", "b", "c")), (_record(),))
    assert any("narrative" in message and "最大2" in message for message in too_many)

    too_long = _visual_messages(_content(narratives=("x" * 201,)), (_record(),))
    assert any("narrative" in message and "200" in message for message in too_long)


def test_expected_records_are_matched_to_canonical_instance_not_global_claim_text() -> None:
    messages = _visual_messages(
        _content(canonical_instance="another-instance"),
        (_record(),),
    )
    assert any("sec-map" in message and "canonical" in message for message in messages)


def test_completeness_diagnostics_are_stable_and_bounded() -> None:
    records = tuple(
        replace(
            _record(),
            instance_id=f"missing-{index:02d}",
            payload_semantic_ids=frozenset({f"z-{index:02d}", f"a-{index:02d}"}),
        )
        for index in range(40)
    )
    first = _visual_messages(_content(), records)
    second = _visual_messages(_content(), records)

    assert first == second
    assert len(first) == 32
