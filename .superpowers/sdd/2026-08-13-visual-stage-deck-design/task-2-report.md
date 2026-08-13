# Task 2 report: model.py IR dataclass extension

## Implementation summary

- Added frozen `SequenceStep`, `SequenceDeclaration`, and `Assertion` dataclasses with Python field names `target_ids` and `cover_ids` mapped from the schema JSON names.
- Added optional `claim`, `sequence`, and `assertions` fields to `CanonicalIR`, preserving existing constructor compatibility through defaults.
- Confirmed `semantic_ids()` remains payload-only: sequence step IDs and assertion IDs are not added.
- Added focused behavior coverage in `test_model_stage_deck.py`.

## RED

Command:

```text
PYTHONPATH=skills/visual-explain/scripts python3 -m pytest skills/visual-explain/scripts/tests/test_model_stage_deck.py -q
```

Output:

```text
ImportError: cannot import name 'Assertion' from 've_components.model'
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

This was the expected RED: the focused test imported the required new model surface before it existed.

## GREEN and full suite

Focused GREEN:

```text
PYTHONPATH=skills/visual-explain/scripts python3 -m pytest skills/visual-explain/scripts/tests/test_model_stage_deck.py -q
1 passed in 0.04s
```

Full suite (from `skills/visual-explain/scripts`, so existing relative fixture paths resolve):

```text
python3 -m pytest tests/ -x -q
763 passed, 153 subtests passed in 8.18s
```

The brief's root-directory path command with `PYTHONPATH` reached 246 tests but failed an existing cwd-sensitive documentation test (`../references/design-system.md` not found); the scripts-directory invocation above is the passing full verification.

## Files changed

- `skills/visual-explain/scripts/ve_components/model.py`
- `skills/visual-explain/scripts/tests/test_model_stage_deck.py`

## Self-review

- Scope is limited to the requested model surface and focused test.
- Dataclasses are frozen and use immutable tuple collections.
- Existing `CanonicalIR` positional construction remains compatible because new fields are optional and appended after existing required fields.
- Semantic ID behavior is explicitly asserted.

## Concerns

- Full-suite tests depend on being launched from `skills/visual-explain/scripts`; the brief's root-relative command has a pre-existing path-sensitive failure.
