import dataclasses

from ve_components.model import (
    AccessibilityInfo,
    Assertion,
    CanonicalIR,
    ExplicitSelection,
    RelationshipDeclaration,
    SequenceDeclaration,
    SequenceStep,
)


def _ir_with_stage_fields() -> CanonicalIR:
    return CanonicalIR(
        id="section-1",
        relationship=RelationshipDeclaration("two-axis", ("two-axis-classification",)),
        selection=ExplicitSelection("matrix", 2, ("two-axis-classification",)),
        caption="Caption",
        certainty=(),
        sources=(),
        accessibility=AccessibilityInfo("Label", "Summary"),
        claim="A concise claim",
        sequence=SequenceDeclaration(
            mode="path-spotlight",
            steps=(SequenceStep("step-1", "First", ("payload-1",)),),
        ),
        assertions=(Assertion("assertion-1", "A claim", ("payload-1",)),),
    )


def test_stage_deck_fields_are_frozen_and_step_assertion_ids_are_not_semantic_ids() -> None:
    ir = _ir_with_stage_fields()

    assert ir.claim == "A concise claim"
    assert ir.sequence is not None
    assert ir.sequence.steps[0].target_ids == ("payload-1",)
    assert ir.assertions is not None
    assert ir.assertions[0].cover_ids == ("payload-1",)
    assert "step-1" not in ir.semantic_ids()
    assert "assertion-1" not in ir.semantic_ids()
    assert dataclasses.is_dataclass(SequenceDeclaration)
    assert dataclasses.is_dataclass(SequenceStep)
    assert dataclasses.is_dataclass(Assertion)
    assert getattr(SequenceDeclaration, "__dataclass_params__").frozen
    assert getattr(SequenceStep, "__dataclass_params__").frozen
    assert getattr(Assertion, "__dataclass_params__").frozen
