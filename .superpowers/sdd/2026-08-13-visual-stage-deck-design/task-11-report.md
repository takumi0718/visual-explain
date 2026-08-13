# Task 11 Report — Panel-aware legacy component checker

## Status

Implemented and verified. `checker.py` now treats every sequence `[data-step]`
subtree as an independent complete component instance for artifact semantics and
SVG validation, while retaining legacy non-stepper behavior.

## Behavior and trust boundaries

- `extract_flow_dom()` normalizes `data-ve-node-id` and flow endpoint references
  from an exact enclosing-panel `--pN` suffix back to base semantic IDs. The
  normalization is enabled only below `[data-stepper] [data-step="N"]`, or when
  the panel-aware artifact checker supplies that already-validated panel context.
- Suffix-shaped base IDs remain unambiguous: base `node-a--p2` in panel 2 is
  emitted as `node-a--p2--p2` and normalized once. A bare `data-step` outside a
  stepper does not enable normalization.
- `validate_artifact_semantics()` slices sequence panels without reserializing
  markup, requires exactly one matching component instance in each panel, and
  runs the incumbent component checker on each panel separately. Missing or
  duplicate instances and cross-panel/wrong-suffix flow references fail with
  panel-numbered diagnostics.
- `validate_renderer_svg()` requires exactly one SVG in every panel of an
  allowlisted SVG component and enforces `id="<instance>-svg--pN"` plus the
  incumbent element/attribute grammar per subtree. Legacy SVG IDs remain
  `<instance>-svg`.
- Document-wide real DOM ID uniqueness remains owned by the unchanged legacy
  `check.sh` layer; sequence output passes that layer using suffixed actual IDs.
  Base semantic IDs remain unchanged on `data-ve-semantic-id`, so panel 1 can
  remain the canonical payload inventory for the later expected-record checks.
- The T8 exact xfail was removed: flow path sequences now pass
  `render_canonical()`'s real trust boundary.

## TDD evidence

1. Flow trust boundary:
   - RED: the former xfail, made a normal assertion, failed with the exact
     `flow node` and `flow endpoint/relation` IR mismatch diagnostics.
   - GREEN: panel-scoped suffix normalization made the test pass.
2. Panel semantic/SVG contracts:
   - RED: seven new focused cases failed: a complete waterfall sequence was
     falsely aggregated, missing/duplicate panel instances were missed,
     cross-panel/wrong suffixes were not panel-scoped, and SVG missing/
     duplicate/wrong-root cases lacked panel validation.
   - GREEN: panel subtree extraction plus per-panel semantic/SVG application.
3. Stepper-context security:
   - RED: a bare `data-step="2"` outside a stepper incorrectly enabled suffix
     normalization.
   - GREEN: normalization now requires the stepper ancestor/context.
4. Real build integration:
   - RED: the branch flow sequence build failed because the incumbent asset
     scanner treated JavaScript `//` comments and the standard SVG namespace
     passed to `createElementNS` as network references.
   - GREEN: the checker now scans URL literals rather than every `//`, preserves
     network URL rejection, and admits the closed non-fetching SVG namespace.

## Focused coverage

`tests/test_checker_sequence_panels.py` covers:

- flow/matrix/stairs/waterfall/bars complete sequence acceptance;
- missing and duplicate component instances in one panel;
- cross-panel endpoint references and wrong suffixes;
- suffix-shaped base IDs and bare-`data-step` isolation;
- missing, duplicate, and wrong-ID SVG roots per panel;
- real flow path sequence `build_document()` with the controlled runtime;
- comments/SVG namespace versus actual network URL asset scanning.

The one pre-existing T8 dependency test was minimally changed from exact xfail
to successful trust-boundary execution. No fixture was modified.

## Verification

- Focused checker/sequence/legacy SVG suites: `166 passed, 56 subtests passed`.
- Full canonical suite: `924 passed, 153 subtests passed`.
- Checker selftest: `31 passed, 0 failed`.
- Real branch sequence CLI build: `OK`; generated document `check.sh`: `PASS`.
- Legacy flow/matrix/stairs/waterfall/bars exact-byte tests: `5 passed`.
- `python3 -m py_compile` on production and focused test: passed.
- `git diff --check`: clean.

## Self-review / concerns

- Production changes are confined to `checker.py`; tests add one focused file
  and update only the explicitly ruled T8 xfail.
- Panel slicing uses `HTMLParser` positions solely to retain original substrings;
  it does not repair or reserialize trusted renderer markup.
- Sequence cardinality/order, all-panel DOM normalization, and expected-record
  payload equality remain Tasks 12–14 as planned. This task supplies the
  component/SVG panel boundary they consume.
