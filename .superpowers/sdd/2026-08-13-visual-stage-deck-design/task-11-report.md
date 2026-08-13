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

## Fix Round 1

Two review findings were reproduced with exact RED tests and fixed.

1. Sequence SVG ownership
   - RED: a valid SVG, or a forbidden `<foreignObject>` SVG, inserted between
     the final panel and controls escaped both the panel-only SVG validator and
     the post-section outside scan. A follow-up adversarial case showed that a
     raw regex ownership count would also treat `<svg>` text in an HTML comment
     as a real element.
   - GREEN: `_SequencePanelParser` now records source offsets for actual panel
     and SVG elements. Every SVG open element in a sequence canonical must lie
     inside exactly one recorded panel interval. Panel-external SVG is rejected
     and its real subtree still passes through the incumbent closed SVG grammar,
     so forbidden elements cannot hide outside panels. Comments are ignored by
     construction rather than stripped by regex.
2. Controlled asset network scanning
   - RED: static concatenations such as `fetch('http:' + '//host')`, split
     `http`, protocol-relative strings, `wss://`, and `ftp://` were missed;
     conversely URL text in JS/CSS comments was rejected. The former SVG
     namespace string exception also allowed that same string in `fetch()`.
   - GREEN: scripts use a small comment-aware tokenizer with escape decoding and
     adjacent string-expression folding. Statically recoverable network URLs
     (`http`, `https`, `ws`, `wss`, `ftp`, and `//`) fail. The SVG namespace is
     allowed only as a direct or single-purpose binding for namespace-only DOM
     APIs; any fetch/WebSocket/general use fails. Styles use quote-aware comment
     removal before their live URL scan, including strings that contain comment
     delimiter text.

Fix-round verification:

- Focused adversarial file: `17 passed`.
- Related checker/SVG/asset/flow suites: `192 passed, 56 subtests passed`.
- Full canonical suite: `929 passed, 153 subtests passed`.
- Checker selftest: `31 passed, 0 failed`.
- Real branch flow sequence CLI build and generated-document check: `OK`, `PASS`.
- Legacy flow/matrix/stairs/waterfall/bars exact-byte tests: `5 passed`.
- `python3 -m py_compile` and `git diff --check`: clean.

## Fix Round 2

Two fix-derived review findings were reproduced and closed with additional RED
tests.

1. SVG namespace call spoofing
   - RED: member spoofing (`evil.createElementNS` and
     `evil.document.createElementNS`), a locally rebound `document`, and an
     aliased bare `createElementNS` could all reuse the namespace exception.
   - GREEN: the exception now requires the exact unshadowed global receiver
     shape `document.createElementNS(namespace, ...)`. A namespace binding is
     allowed only when every later occurrence is that exact call argument. The
     committed runtime satisfies this closed shape; arbitrary receivers,
     rebinding, and acquisition contexts fail.
2. Static URL obfuscation
   - RED: interpolated templates, `\u{...}` code-point escapes, const aliases,
     parenthesized concatenation, and CSS escaped slashes bypassed the scan.
   - GREEN: the tokenizer decodes code-point escapes; a bounded static string
     evaluator folds parentheses, `+`, and simple const/let bindings. Known
     acquisition calls (`fetch`, `WebSocket`, `EventSource`, `sendBeacon`, and
     `importScripts`) fail closed when their first argument cannot be evaluated,
     and reject evaluated external URLs. Dynamic templates therefore cannot
     hide a network target. Any backslash inside a live CSS `url(...)` is
     rejected fail-closed, while comment-only URLs and the existing assets
     remain accepted.

Fix-round verification:

- Focused adversarial file: `19 passed`.
- Related checker/SVG/asset/flow suites: `194 passed, 56 subtests passed`.
- Full canonical suite: `931 passed, 153 subtests passed`.
- Checker selftest: `31 passed, 0 failed`.
- Real branch flow sequence CLI build and generated-document check: `OK`, `PASS`.
- Legacy flow/matrix/stairs/waterfall/bars exact-byte tests: `5 passed`.
- `python3 -m py_compile` and `git diff --check`: clean.

## Fix Round 3

The controlled-asset policy was intentionally simplified after review: these
assets do not need network acquisition APIs, so their presence is prohibited
instead of attempting to prove each call argument safe.

1. JavaScript closed acquisition vocabulary
   - RED: direct aliases, `.call`, shadowed parameters, reassignment, bare
     property references, computed `window['fetch']`, and escaped identifiers
     could evade a call-shape/argument analyzer.
   - GREEN: after comment/string tokenization, any code identifier in the closed
     acquisition set (`fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource`,
     `sendBeacon`, `importScripts`) is rejected regardless of use shape.
     Computed-property string tokens are rejected only inside `[...]`, so an
     ordinary UI string such as `"fetch"` remains valid. A backslash in JS code
     outside comments/strings is fail-closed, preventing escaped identifiers.
     The const environment and acquisition call evaluator from Round 2 were
     deleted. Existing SVG namespace validation remains receiver/context closed.
2. CSS code-aware escape handling
   - RED: escaped `url` identifiers and escaped scheme slashes bypassed the scan,
     while text content containing `"url(foo\\bar)"` was falsely rejected.
   - GREEN: a bounded CSS tokenizer now excludes comments and ordinary strings
     from code, decodes CSS escapes in code identifiers and `url(...)` values,
     and rejects external network URLs only in live `url`/`@import` contexts.
     `data:`, fragment, and relative URLs remain allowed.

Fix-round verification:

- Focused adversarial file: `21 passed`.
- Related checker/SVG/asset/flow suites: `196 passed, 56 subtests passed`.
- Full canonical suite: `933 passed, 153 subtests passed`.
- Checker selftest: `31 passed, 0 failed`.
- Real branch flow sequence CLI build and generated-document check: `OK`, `PASS`.
- Legacy flow/matrix/stairs/waterfall/bars exact-byte tests: `5 passed`.
- `python3 -m py_compile` and `git diff --check`: clean.

## Fix Round 4

Two remaining scanner findings were reproduced with exact RED cases and fixed
without restoring string-expression evaluation.

1. Known-global computed members
   - RED: split, parenthesized, aliased, and optional computed access on
     `globalThis` bypassed the computed-property string check.
   - GREEN: any direct computed member access on the known global receivers
     `window` or `globalThis` is rejected before inspecting its property
     expression. This covers `[...]` and `?.[...]`, including unknown aliases,
     while ordinary array literals remain unrelated tokenizer structure.
2. Regex/string opacity
   - RED: forbidden API words inside regular-expression bodies were emitted as
     code identifiers and falsely rejected. The existing bracket/string rule
     also conflated ordinary string arrays with computed properties.
   - GREEN: the small JS lexer now recognizes regex literals in expression
     context, consuming escapes, character classes, and flags as one opaque
     token. Division remains punctuation in value context. Comments, strings,
     and regex bodies therefore do not reserve ordinary UI vocabulary. Code
     identifiers are intentionally still closed: object keys such as `fetch`
     and class methods named `fetch` are rejected by the controlled-asset
     policy.

Fix-round verification:

- Focused adversarial file: `25 passed`.
- Related checker/SVG/asset/flow suites: `200 passed, 56 subtests passed`.
- Full canonical suite: `937 passed, 153 subtests passed`.
- Checker selftest: `31 passed, 0 failed`.
- Real branch flow sequence CLI build and generated-document check: `OK`, `PASS`.
- Legacy flow/matrix/stairs/waterfall/bars exact-byte tests: `5 passed`.
- `python3 -m py_compile` and `git diff --check`: clean.
