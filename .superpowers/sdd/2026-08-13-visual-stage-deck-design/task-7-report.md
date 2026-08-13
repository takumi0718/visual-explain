# Task 7 Report — Shared Static Sequence Panel Expansion Core

## Status

Implemented the shared callback-oriented sequence expansion core without integrating any renderer. Existing renderer behavior remains unchanged until Tasks 8–10 call the new API.

## API contract

- `validation.SEQUENCE_MODES`: public immutable accepted-mode vocabulary reused by validation and the renderer core.
- `validation.SEQUENCE_REFERENCE_ATTRIBUTES`: public `MappingProxyType` closed allowlist from attribute name to accepted reference grammar (`dom-id`, fragment, single/list IDREF, URL reference, inline URL reference). This is the single rewrite/normalization source for later checker work.
- `common.SequencePanel(number, step, highlight_ids)`: panel 1 has `step=None` and an empty highlight set; panel k+1 carries step k and the centrally computed highlight set.
- `common.sequence_panels(sequence, path_edges=None)`: implements non-cumulative `state-lens`, prefix-union `delta-accumulate`, and `path-spotlight` current nodes plus a required deterministic `path_edges(sequence, zero_based_step_index)` callback.
- `common.expand_sequence(sequence, render_panel, path_edges=None)`: calls `render_panel(SequencePanel) -> RenderResult` once per complete panel body, namespaces all DOM IDs/references, wraps panels and controls, emits forecasts, and expands manifest landmarks/SVG roots in panel order. With `sequence=None`, it calls the callback once and returns that exact `RenderResult` object unchanged.
- `consumed_semantic_ids` and `generated_relationship_ids` remain base semantic IDs. Only `generated_landmark_ids` and `svg_root_ids` gain `--p<p>` suffixes.

## Behavior-cluster RED/GREEN evidence

All commands ran from `skills/visual-explain/scripts`.

1. Highlight semantics
   - RED: `python3 -m pytest tests/test_sequence_renderer_common.py -q` → 3 failed; `sequence_panels` missing.
   - GREEN: same command → 3 passed.
2. Closed ID/reference rewriting
   - RED: same command → 1 failed, 3 passed; panel namespace transformer missing.
   - GREEN: same command → 4 passed.
3. Wrapper, controls, and forecasts
   - RED: same command → 1 failed, 4 passed; `expand_sequence` missing.
   - GREEN: same command → 5 passed.
4. Manifest expansion and legacy no-op
   - RED: same command → 2 failed, 5 passed; manifest IDs stayed unsuffixed and `None` was unsupported.
   - GREEN: same command → 7 passed.

## Focused tests

`tests/test_sequence_renderer_common.py` contains seven behavior tests:

- overview plus current-only state-lens highlights;
- delta prefix union;
- path node targets plus callback-derived edges;
- all closed allowlist reference grammars, same-panel resolution, escaped deterministic output, unknown-form preservation, and base `data-ve-semantic-id` preservation;
- wrapper mode/total/steps, complete body count, previous/next/all controls, generic next label, escaped IR forecasts, exact final text, and no `.stepper-status`;
- panel-ordered landmark/SVG manifest expansion while semantic/relationship IDs remain base IDs;
- byte/object-identity legacy no-op.

## Files

- `skills/visual-explain/scripts/ve_components/renderers/common.py`
- `skills/visual-explain/scripts/ve_components/validation.py`
- `skills/visual-explain/scripts/tests/test_sequence_renderer_common.py`
- `.superpowers/sdd/2026-08-13-visual-stage-deck-design/task-7-report.md`

## Verification

- Focused: `python3 -m pytest tests/test_sequence_renderer_common.py -q` → 7 passed.
- Full canonical suite: `python3 -m pytest tests/ -x -q` → 856 passed, 153 subtests passed.
- Selftest: `./check.sh --selftest` → 31 passed, 0 failed.
- `git diff --check` → clean.

## Self-review / concerns

- The transformer uses a two-pass stdlib `HTMLParser` implementation: first collect panel-local DOM IDs, then rewrite only allowlisted references that resolve to those IDs. Unknown attributes, unknown reference forms, unresolved references, external href fragments, and semantic payload IDs are not rewritten.
- SVG attribute case that HTML parsing normalizes (`viewBox`, `preserveAspectRatio`) is restored explicitly; text entities remain escaped and deterministic.
- Expected follow-up boundary: Tasks 8–10 must render `ve-seq-spot`/`ve-seq-dim` from `SequencePanel.highlight_ids`; Task 8 must supply path edges and its station-only path canvas. No renderer was integrated here, as required, so end-to-end sequence canonical fixtures remain follow-up coverage.
