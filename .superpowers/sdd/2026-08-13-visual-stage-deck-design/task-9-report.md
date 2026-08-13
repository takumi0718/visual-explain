# Task 9 Report — Matrix/Stairs State-Lens Sequence Rendering

## Status

Implemented renderer-local sequence branches for `matrix@2` and `stairs@2` using the shared Task 7 `SequencePanel` / `expand_sequence()` contract. Sequence panels apply current-step-only state-lens classes to eligible payload items, while legacy rendering remains byte-identical.

## Behavior and structure

- Panel 1 is a complete figure with no `ve-seq-spot` or `ve-seq-dim` class.
- Each later panel is a complete component instance.
- Matrix dense cells and concept cells receive `ve-seq-spot` only when their cell ID is in that panel's `highlight_ids`; all other real cells receive `ve-seq-dim`. Axis headers and non-cell markup are not sequence-painted.
- Stairs stages receive the same current-step-only spot/dim treatment. Prior-step targets return to `ve-seq-dim`, proving the state lens is non-cumulative.
- `expand_sequence()` owns panel ID/reference suffixing and manifest landmark expansion. Renderer callbacks return invariant asset/manifest contracts for every panel.
- The shared claim is applied after expansion, so it appears once immediately before the stepper rather than once per panel.
- No flow-specific runtime or script asset is selected.

## RED/GREEN evidence

Commands ran from `skills/visual-explain/scripts`.

1. Dense matrix + stairs sequence branch and complete-panel contract
   - RED: `python3 -m pytest tests/test_matrix_stairs_sequence_renderer.py -q` → 4 failed, 2 passed. Both renderers ignored `sequence` and returned a single figure, so panel 2 was absent and the stepper/claim contract failed.
   - GREEN: same command → 6 passed.
2. Concept matrix branch
   - RED: after isolating the concept-grid behavior, same command → 1 failed, 6 passed. Concept cells lacked `ve-seq-spot` / `ve-seq-dim`.
   - GREEN: same command → 7 passed.

The focused tests use literal expected target sets and inspect rendered semantic elements rather than mocks or renderer internals. Mutating either renderer to accumulate previous targets, omit dim classes, paint axis IDs, duplicate the claim, or skip panel expansion makes at least one focused assertion fail.

## Files

- `skills/visual-explain/scripts/ve_components/renderers/matrix.py`
- `skills/visual-explain/scripts/ve_components/renderers/stairs.py`
- `skills/visual-explain/scripts/tests/test_matrix_stairs_sequence_renderer.py`
- `.superpowers/sdd/2026-08-13-visual-stage-deck-design/task-9-report.md`

## Verification

- Task + existing renderer tests: `python3 -m pytest tests/test_matrix_renderer.py tests/test_stairs_renderer.py tests/test_matrix_stairs_sequence_renderer.py -q` → 49 passed, 3 subtests passed.
- Full canonical suite: `python3 -m pytest tests/ -x -q` → 903 passed, 1 expected T11 xfail, 153 subtests passed.
- Selftest: `./check.sh --selftest` → 31 passed, 0 failed.
- Legacy matrix markup SHA-256: `dd263127f89af1b365ea1d190e5dd50c43ddae2ef653a533f3543d14c229224c` (unchanged).
- Legacy stairs markup SHA-256: `dfae19ac36f2decc2ec5214346f3da9a5923194893e068930e4919cc369d5b89` (unchanged).
- `git diff --check` → clean.

## Self-review / concerns

- Renderer entry points rely on validation's mode×component and target-kind gates, as planned. If an invalid non-state-lens declaration bypasses validation, the shared expansion core may reject it or apply that mode's shared highlight semantics; this is outside the validated renderer boundary.
- Final assembly/checker acceptance of repeated panel semantic IDs still depends on Task 11's panel-aware normalization. Direct `RenderResult` markup and manifests follow Task 7's suffix contract now.
- No existing tests or fixtures were changed.
