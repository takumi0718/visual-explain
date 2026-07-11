# Visual-Explain Diagram Component Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a canonical semantic component pipeline for `matrix` and `flow` that can assemble mixed canonical and compatibility sections into one safe, dependency-free, single self-contained HTML document.

**Architecture:** A Python-standard-library generation layer validates a limited JSON IR, deterministically narrows component candidates, verifies an explicit selection and reason, resolves a trusted registry entry, renders semantic markup, composes it with labelled compatibility markup, and flattens everything into controlled skeleton slots. Existing HTML insertion remains only a temporary source of compatibility markup; the existing checker remains the public safety gate and gains IR/manifest/controlled-slot checks without weakening fixed-region validation.

**Tech Stack:** Python 3 standard library (`dataclasses`, `json`, `html`, `hashlib`, `importlib`, `unittest`), POSIX shell, HTML5, CSS, and the repository's existing `check.sh`; no new package or external UI/diagram framework.

## Overview

Implement the approved specification at `docs/superpowers/specs/2026-07-10-visual-explain-component-foundation.md` as five rollback-safe milestones:

1. Freeze the legacy checker/skeleton baseline, then add the limited authoring and registry contracts without activating a component.
2. Introduce three controlled skeleton slots and their fail-closed safety checks while leaving them empty for legacy documents.
3. Add one opt-in composition/flattening pipeline that can mix canonical sections and compatibility sections.
4. Add `matrix` and `flow` as the only production registry entries and pass both through the same pipeline.
5. Promote the canonical route for normal `matrix`/`flow` generation in documentation while retaining explicitly labelled weak-model compatibility markup.

Each milestone is independently testable and committed separately. Do not switch documented default behavior until both components and the mixed-document checker suite pass. A rollback reverts the most recent milestone commit; it never requires changing an already-produced HTML document or weakening a checker rule.

The generation input is an assembly request, not a universal diagram language. It has document metadata and an ordered `sections` list. A canonical section contains the limited component IR. A compatibility section contains existing-rule markup plus explicit provenance and does not become canonical IR.

The public generation entry point will be:

```text
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly path/to/assembly.json \
  --output path/to/explainer.html
```

It must return exit 0 only after pre-render validation, rendering/assembly, flattening, and final checking all pass. It must return exit 1 with one or more bounded diagnostic codes when any stage fails. It must never silently replace a failed canonical section with compatibility markup.

## Global Constraints

- The final artifact is exactly one self-contained HTML file.
- The final artifact contains no external CSS, JavaScript, CDN reference, web font, network call, runtime loader, module import, or build dependency.
- Use only Python 3 standard-library code and existing repository tooling; install no dependency.
- Preserve the current CSP, safety boundary, document-structure checks, required-content checks, and fixed-region validation.
- Ordinary generated content cannot edit fixed regions, populate controlled style/script slots, or inject CSS or JavaScript.
- Only registry-allowlisted, hash-verified renderer assets may populate controlled style/script slots.
- Every core relationship, label, direction, caption, certainty assertion, source, and interaction meaning is present in static HTML/CSS. JavaScript is never required for core understanding.
- The first vertical slice contains exactly `matrix` and `flow`. Do not migrate `layers`, `compare`, `timeline`, `kpi`, `bars`, `terms`, `details`, or `stepper`.
- Do not add heuristic auto-selection, ranking, model-chosen aesthetics, free-coordinate drawing, decorative animation, rich interaction, or an external UI/diagram framework.
- Multiple matching candidates are valid; explicit selection is required. Invalid/under-specified declarations, zero candidates, out-of-set selections, and reason mismatches fail with distinct bounded diagnostics.
- A single component instance cannot combine matrix intersections and directed flow transitions unless a registered component explicitly declares that combined responsibility. No such component exists in this slice.
- A document may mix canonical `matrix`/`flow` instances and explicitly labelled compatibility sections in one ordered sequence.
- All sections use one composition/flattening final-assembly route. Compatibility sections bypass canonical validation/selection, registry resolution, and trusted renderer execution, then enter only the controlled content slot.
- Compatibility markup obeys existing content rules, fixed-region restrictions, provenance requirements, and final checker validation. It cannot contain arbitrary CSS or JavaScript.
- The old standalone HTML-insertion behavior is only the temporary source of compatibility markup, not a parallel final-assembly path.
- Preserve weak-model degradation as an explicit author choice with provenance; never silently fall back after canonical failure.
- Do not change or block on the known causal-reversal fixture issue. Add only general directed-edge validation.
- Preserve commit `6265e42` as separate prior work; do not squash or mix it into foundation commits.
- The implementation phase may run command-line tests but does not require a browser smoke test. Visual polish remains deferred.

## Repository Baseline

The implementer starts from these existing files:

- `skills/visual-explain/assets/skeleton.html` — fixed document shell and current centralized CSS/JavaScript/rendering behavior.
- `skills/visual-explain/SKILL.md` — author workflow and output rules.
- `skills/visual-explain/references/patterns.md` — existing format guidance.
- `skills/visual-explain/references/design-system.md` — current tokens and visual rules.
- `skills/visual-explain/scripts/check.sh` — public checker entry point and current fixed-region/safety checks.
- `skills/visual-explain/scripts/tests/` — catalog plus valid and invalid HTML fixtures.
- `skills/visual-explain/examples/example-proposal.html` — existing output retained as a legacy regression example.
- `docs/superpowers/specs/2026-07-10-visual-explain-component-foundation.md` — approved architecture and source of truth.

Create this focused file structure:

```text
skills/visual-explain/
├── assets/
│   ├── skeleton.html                         # modify: controlled slots only; preserve other regions
│   └── components/
│       ├── registry.json                     # create: production matrix/flow contract index
│       ├── matrix.css                        # create: minimal static semantic layout
│       └── flow.css                          # create: minimal static semantic layout
├── references/
│   ├── component-vocabulary.json             # create: authoritative IDs/capabilities/provenance strings
│   ├── assembly.schema.json                  # create: mixed-document assembly contract
│   ├── component-ir.schema.json              # create: canonical section contract
│   ├── patterns.md                           # modify: canonical matrix/flow authoring and fallback
│   └── design-system.md                      # modify: ownership and controlled asset rules
├── scripts/
│   ├── build_explainer.py                    # create: only generation CLI
│   ├── check.sh                              # modify: retain public checker, call component checker
│   ├── check_component_html.py               # create: final controlled-slot/semantic checker CLI
│   ├── ve_components/
│   │   ├── __init__.py                       # create: narrow public exports
│   │   ├── diagnostics.py                    # create: bounded error codes
│   │   ├── model.py                          # create: immutable IR/registry/render/assembly types
│   │   ├── validation.py                     # create: schema-equivalent validation
│   │   ├── registry.py                       # create: registry loading, hashes, trusted renderer map
│   │   ├── selection.py                      # create: deterministic candidate narrowing
│   │   ├── assembly.py                       # create: one canonical/compatibility composition route
│   │   ├── flatten.py                        # create: controlled-slot inlining and fixed-region preservation
│   │   ├── checker.py                        # create: reusable component/final-document checks
│   │   └── renderers/
│   │       ├── __init__.py                   # create empty in Task 2; populate in Tasks 5–6
│   │       ├── matrix.py                     # create: semantic table renderer
│   │       └── flow.py                       # create: semantic directed-list renderer
│   └── tests/
│       ├── test_component_contract.py        # create
│       ├── test_component_selection.py       # create
│       ├── test_controlled_slots.py           # create
│       ├── test_mixed_assembly.py             # create
│       ├── test_matrix_renderer.py            # create
│       ├── test_flow_renderer.py              # create
│       ├── test_component_checker.py          # create
│       ├── component-valid-matrix.json        # create
│       ├── component-valid-flow.json          # create
│       ├── component-valid-mixed.json         # create
│       ├── component-valid-weak-model.json    # create
│       ├── compatibility-valid-fragment.html  # create
│       ├── component-bad-fixed-region.html
│       ├── component-bad-content-style.html
│       ├── component-bad-content-script.html
│       ├── component-bad-asset-hash.html
│       ├── component-bad-selection.json
│       ├── component-bad-selection-reason.json
│       ├── component-bad-combined-relationship.json
│       ├── component-bad-flow-edge.json
│       ├── component-bad-matrix-cell.json
│       ├── component-bad-compatibility-provenance.html
│       ├── component-bad-weak-model-style.json
│       ├── component-bad-weak-model-script.json
│       └── catalog.html                       # modify only after both renderers pass
└── examples/
    └── example-proposal.html                 # do not modify; keep as regression input
```

Do not create a generic `components/utils.py`, a client-side component runtime, format-specific build scripts, or a second compatibility flattener. Shared behavior belongs in the named modules above.

## Architecture-to-Task Mapping

| Approved boundary | Concrete owner | Implemented in | Proved by |
|---|---|---|---|
| Canonical vocabulary and limited IR | authoritative vocabulary JSON, JSON schemas, and immutable Python types | Tasks 1–2 | vocabulary/schema/fixture consistency tests |
| Deterministic narrowing and explicit selection | pure selection functions; no ranking fields | Task 2 | one/many/zero candidate tests |
| Registry as discovery/contract index | static JSON plus strict loader and trusted renderer map | Tasks 2, 5, 6 | unknown version/renderer/asset tests |
| Semantic renderer modules | `matrix.py` and `flow.py` only | Tasks 5–6 | semantic ID and static markup tests |
| One mixed composition route | discriminated canonical/compatibility section types | Task 4 | order and bypass spy tests |
| One flattening route | skeleton-slot substitution and asset deduplication | Tasks 3–4 | fixed-region hash and mixed-output tests |
| Controlled style/script slots | skeleton markers, allowlist, manifest, digest validation | Tasks 3, 7 | tamper/injection tests |
| Four checker layers | existing `check.sh` plus reusable Python checks | Tasks 1–3, 7 | legacy, IR, contract, and final DOM suites |
| Compatibility provenance | compatibility section wrapper and final checker | Tasks 4, 7 | missing/false provenance tests |
| Weak-model degradation | explicit compatibility assembly input and SKILL guidance | Tasks 4, 8 | no-silent-fallback and docs tests |
| Static-first/accessibility | semantic HTML, empty script lists, responsive CSS | Tasks 5–7 | no-script, landmarks, labels, reading-order tests |
| Gradual promotion | documentation switch only after both components pass | Task 8 | full acceptance command set |

The core interfaces are fixed before task execution:

- `validate_assembly(raw: dict[str, object]) -> AssemblyRequest`
- `validate_canonical_section(raw: dict[str, object]) -> CanonicalSection`
- `load_registry(path: Path) -> Registry`
- `narrow_candidates(declaration: RelationshipDeclaration, registry: Registry) -> Sequence[CandidateMatch]`
- `validate_explicit_selection(section: CanonicalSection, candidates: Sequence[CandidateMatch]) -> None`
- `resolve_component(registry: Registry, component_id: str, version: int) -> ComponentDefinition`
- `render_canonical(section: CanonicalSection, definition: ComponentDefinition) -> RenderResult`
- `compose_sections(sections: Sequence[RenderedCanonical | CompatibilitySection]) -> CompositionResult`
- `flatten_document(skeleton: str, composition: CompositionResult, registry: Registry) -> str`
- `check_final_document(document: str, skeleton: str, registry: Registry, expected: CompositionResult | None) -> Sequence[Diagnostic]`
- `build_document(request: AssemblyRequest, paths: BuildPaths) -> BuildResult`

`build_document` is the sole orchestration function. For a canonical section it calls validation → narrowing → explicit-selection validation → registry resolution → trusted renderer. For a compatibility section it skips all five operations and creates a provenance-labelled content section. Both results then call the same `compose_sections` and `flatten_document` functions. During a build, `expected` is the in-memory `CompositionResult`, so the checker compares IR-derived manifests with the flattened DOM before publishing output. The standalone `check.sh` call passes `expected=None`; it revalidates fixed regions, controlled assets, provenance, final semantic attributes, static content, and document safety without pretending to reconstruct the discarded source IR.

## Implementation Tasks

### Task 0: Freeze the legacy baseline and establish rollback evidence

**Files:**

- Inspect: every file listed under Repository Baseline.
- Modify: none.

**Deliverable:** A recorded green baseline and fixed-region digest before the first implementation commit.

- [ ] Confirm the working tree contains no unrelated edits and that prior fix commit `6265e42` is already in history:

  ```bash
  git status --short
  git log --oneline --all | rg '^6265e42 '
  ```

  Expected: `git status --short` is empty; the log contains exactly the prior fix commit. If unrelated edits exist, stop and isolate them before continuing.

- [ ] Record the starting commit and skeleton digest in the task notes:

  ```bash
  git rev-parse HEAD
  shasum -a 256 skills/visual-explain/assets/skeleton.html \
    skills/visual-explain/examples/example-proposal.html
  ```

  Expected: one 40-character commit ID and two SHA-256 digests, one for each named file.

- [ ] Run the current checker on the existing catalog and example without modifying them:

  ```bash
  bash skills/visual-explain/scripts/check.sh skills/visual-explain/scripts/tests/catalog.html
  bash skills/visual-explain/scripts/check.sh skills/visual-explain/examples/example-proposal.html
  ```

  Expected: both commands exit 0. Preserve the exact output as baseline evidence.

### Task 1: Add the limited assembly/IR contracts and bounded diagnostics

**Files:**

- Create: `skills/visual-explain/references/assembly.schema.json`
- Create: `skills/visual-explain/references/component-ir.schema.json`
- Create: `skills/visual-explain/references/component-vocabulary.json`
- Create: `skills/visual-explain/scripts/ve_components/__init__.py`
- Create: `skills/visual-explain/scripts/ve_components/diagnostics.py`
- Create: `skills/visual-explain/scripts/ve_components/model.py`
- Create: `skills/visual-explain/scripts/ve_components/validation.py`
- Create: `skills/visual-explain/scripts/tests/test_component_contract.py`
- Create: `skills/visual-explain/scripts/tests/component-valid-matrix.json`
- Create: `skills/visual-explain/scripts/tests/component-valid-flow.json`

**Interfaces:**

- Produces: immutable `AssemblyRequest`, `DocumentMetadata`, `CanonicalSection`, `CompatibilitySection`, `RelationshipDeclaration`, `ExplicitSelection`, `AccessibilityInfo`, `Source`, `CertaintyAssertion`, `MatrixPayload`, `FlowPayload`, `FlowNode`, `FlowEdge`, `RenderManifest`, `RenderResult`, `RendererFn`, `Diagnostic`, and `ContractError` types.
- Produces: `validate_assembly(raw)`, `validate_canonical_section(raw)`, and exact diagnostic codes used by all later tasks.
- Owns the vocabulary consumed by every later task. Tasks 2, 4, 5, 6, and 8 may not invent or rename component IDs, contract versions, relationship kinds, capability strings, compatibility sources, or compatibility reasons.

- [ ] Create `component-vocabulary.json` before writing schemas or fixtures. It is the authoritative MVP vocabulary:

  ```json
  {
    "vocabularyVersion": 1,
    "components": {
      "matrix": {
        "contractVersion": 1,
        "relationshipKind": "two-axis",
        "capabilities": ["two-axis-classification", "intersection-comparison"]
      },
      "flow": {
        "contractVersion": 1,
        "relationshipKind": "directed-graph",
        "capabilities": ["ordered-transition", "directed-transition", "branching"]
      }
    },
    "compatibility": {
      "sources": ["legacy-html-insertion"],
      "reasons": ["unmigrated-format", "weak-model-degradation"]
    }
  }
  ```

  This file defines semantic contract strings, not production registry entries or ranking metadata. The production registry remains empty until complete component units land in Tasks 5–6.

- [ ] Write failing contract tests that load the vocabulary first, then both valid JSON fixtures. Require the matrix fixture to use `matrix`, version `1`, relationship kind `two-axis`, and matched capabilities drawn from `two-axis-classification`/`intersection-comparison`. Require the flow fixture to use `flow`, version `1`, relationship kind `directed-graph`, and matched capabilities drawn from `ordered-transition`/`directed-transition`/`branching`. Then reject unknown vocabulary strings; unknown fields; missing caption, certainty, source, or accessibility summary; HTML/CSS/JavaScript/coordinate keys in canonical payload; duplicate semantic IDs; bad matrix row/column references; and flow edges with missing `from`, `to`, or relationship type.

  Use these exact diagnostic strings: `invalid_relationship_declaration`, `invalid_component_payload`, `duplicate_semantic_id`, `invalid_matrix_reference`, `invalid_flow_edge`, `missing_required_slot`, `forbidden_authoring_field`, and `invalid_compatibility_provenance`.

- [ ] Define the assembly discriminator precisely in `assembly.schema.json`:

  ```json
  {
    "schemaVersion": 1,
    "document": {
      "id": "example-id",
      "title": "Example title",
      "summary": "One-sentence purpose"
    },
    "sections": [
      {"kind": "canonical", "ir": {}},
      {
        "kind": "compatibility",
        "id": "legacy-section",
        "markup": "<section>Existing-rule content</section>",
        "provenance": {
          "source": "legacy-html-insertion",
          "reason": "unmigrated-format",
          "format": "layers"
        }
      }
    ]
  }
  ```

  `kind=canonical` delegates to `component-ir.schema.json`. `kind=compatibility` accepts only `id`, `markup`, and the three provenance fields; it contains no relationship declaration, selection, renderer, style, or script fields. Its `source` and `reason` values must be members of `component-vocabulary.json`.

- [ ] Define the canonical common envelope with `additionalProperties: false`: IDs; relationship `kind` and `capabilities`; explicit component ID/version and `matchedCapabilities`; caption; certainty records/references; sources/references; accessibility label/summary; and exactly one `matrix` or `flow` payload. Copy the exact enums from `component-vocabulary.json` into the schema and add a consistency test so vocabulary, schema, and fixtures cannot drift. Define matrix rows/columns/cells and flow nodes/edges/groups/start or reading-order hint without markup or coordinates.

- [ ] Run the focused tests and observe failure because the validation modules do not yet exist:

  ```bash
  PYTHONPATH=skills/visual-explain/scripts \
    python3 -m unittest discover \
      -s skills/visual-explain/scripts/tests \
      -p 'test_component_contract.py' -v
  ```

  Expected: import failure or missing validator failure.

- [ ] Implement the immutable models and standard-library validation. `RenderResult` has `markup`, `style_asset_ids`, `script_asset_ids`, `manifest`, and `diagnostics`; `RenderManifest` has component ID/version, instance ID, consumed semantic IDs, generated relationship/landmark IDs, asset IDs/digests, declared dependencies, and fallback mode. Parse JSON only into typed values after rejecting booleans-as-integers, unknown fields, blank IDs, duplicate IDs, bad references, absent common slots, and renderer-shaped authoring fields. Do not infer relationship direction or component choice from prose.

- [ ] Run the focused tests:

  ```bash
  PYTHONPATH=skills/visual-explain/scripts \
    python3 -m unittest discover \
      -s skills/visual-explain/scripts/tests \
      -p 'test_component_contract.py' -v
  ```

  Expected: all Task 1 tests pass.

- [ ] Commit the contract milestone:

  ```bash
  git add skills/visual-explain/references/assembly.schema.json \
    skills/visual-explain/references/component-ir.schema.json \
    skills/visual-explain/references/component-vocabulary.json \
    skills/visual-explain/scripts/ve_components \
    skills/visual-explain/scripts/tests/test_component_contract.py \
    skills/visual-explain/scripts/tests/component-valid-matrix.json \
    skills/visual-explain/scripts/tests/component-valid-flow.json
  git commit -m "feat(visual-explain): define component authoring contracts"
  ```

  Rollback: revert this commit; no skeleton, checker, or legacy generation behavior has changed.

### Task 2: Add registry validation and deterministic explicit selection

**Files:**

- Create: `skills/visual-explain/assets/components/registry.json`
- Create: `skills/visual-explain/scripts/ve_components/registry.py`
- Create: `skills/visual-explain/scripts/ve_components/selection.py`
- Create: `skills/visual-explain/scripts/ve_components/renderers/__init__.py`
- Create: `skills/visual-explain/scripts/tests/test_component_selection.py`

**Interfaces:**

- Consumes: Task 1 models, diagnostic codes, and authoritative component/provenance vocabulary.
- Produces: `ComponentDefinition`, `AssetDefinition`, `Registry`, `CandidateMatch`, `load_registry`, `narrow_candidates`, `validate_explicit_selection`, `resolve_component`, and an initially empty `TRUSTED_RENDERERS: dict[str, RendererFn]` mapping.
- Production registry at this milestone: `{"registryVersion": 1, "components": []}`. Test-only definitions exercise matching until Tasks 5–6 add complete entries atomically with their renderers/assets/checks.

- [ ] Write failing tests for registry required metadata: ID/version, semantic responsibility, capabilities, required/optional inputs, behavior, certainty/source/caption slots, accessibility, responsive requirement, dependencies, fallback, checker rules, renderer reference, and asset identity/hash. Reject IDs, versions, relationship kinds, or capabilities that are not exact members of `component-vocabulary.json`; also reject ranking, heuristic, theme, animation, and advanced-interaction metadata.

- [ ] Write failing selection tests for these exact outcomes:

  - one matrix match returns one `CandidateMatch` with recorded matched capabilities;
  - two test-only components with the same capability return two candidates and do not fail;
  - explicit selection of either returned candidate succeeds;
  - a combined matrix/flow declaration returns zero candidates and raises `no_matching_component`;
  - an under-specified declaration raises `invalid_relationship_declaration` before matching;
  - a component outside a non-empty set raises `selection_outside_candidate_set`;
  - a reason that names capabilities not present in both declaration and registry raises `selection_reason_mismatch`;
  - unknown component/version, renderer reference, dependency, or checker rule fails closed.

- [ ] Run the tests and observe missing registry/selection failures:

  ```bash
  PYTHONPATH=skills/visual-explain/scripts \
    python3 -m unittest discover \
      -s skills/visual-explain/scripts/tests \
      -p 'test_component_selection.py' -v
  ```

  Expected: import or missing-function failure.

- [ ] Implement registry parsing with an explicit field allowlist and SHA-256 format checks. Implement candidate matching as set containment over declared relationship kind and required capabilities. Preserve registry order only for stable diagnostics; do not rank candidates.

- [ ] Implement `validate_explicit_selection` so it checks membership and exact matched-capability evidence. Use the four bounded categories from the spec: `invalid_relationship_declaration`, `no_matching_component`, `selection_outside_candidate_set`, and `selection_reason_mismatch`.

- [ ] Run Task 1–2 tests:

  ```bash
  PYTHONPATH=skills/visual-explain/scripts \
    python3 -m unittest discover \
      -s skills/visual-explain/scripts/tests \
      -p 'test_component_*.py' -v
  ```

  Expected: all discovered contract and selection tests pass.

- [ ] Commit:

  ```bash
  git add skills/visual-explain/assets/components/registry.json \
    skills/visual-explain/scripts/ve_components/registry.py \
    skills/visual-explain/scripts/ve_components/selection.py \
    skills/visual-explain/scripts/ve_components/renderers/__init__.py \
    skills/visual-explain/scripts/tests/test_component_selection.py
  git commit -m "feat(visual-explain): add deterministic component selection"
  ```

  Rollback: revert this commit; canonical component discovery becomes unavailable while legacy behavior remains untouched.

### Task 3: Introduce controlled skeleton slots without weakening fixed regions

**Files:**

- Modify: `skills/visual-explain/assets/skeleton.html`
- Modify: `skills/visual-explain/scripts/check.sh`
- Create: `skills/visual-explain/scripts/check_component_html.py`
- Create: `skills/visual-explain/scripts/ve_components/checker.py`
- Create: `skills/visual-explain/scripts/tests/test_controlled_slots.py`
- Create: `skills/visual-explain/scripts/tests/component-bad-fixed-region.html`
- Create: `skills/visual-explain/scripts/tests/component-bad-content-style.html`
- Create: `skills/visual-explain/scripts/tests/component-bad-content-script.html`
- Create: `skills/visual-explain/scripts/tests/component-bad-asset-hash.html`

**Interfaces:**

- Consumes: registry asset definitions and Task 1 diagnostics.
- Produces: `extract_controlled_slots`, `normalized_fixed_regions`, `validate_content_markup`, `validate_controlled_assets`, and the `check_final_document` skeleton/safety layer. At this milestone the `expected` argument may be `None`; Task 7 completes manifest-to-DOM comparisons when it is provided.

- [ ] Add failing tests for three exact marker pairs in the skeleton:

  ```html
  <!-- VE-CONTROLLED:COMPONENT-STYLES:BEGIN -->
  <!-- VE-CONTROLLED:COMPONENT-STYLES:END -->
  <!-- VE-CONTROLLED:CONTENT:BEGIN -->
  <!-- VE-CONTROLLED:CONTENT:END -->
  <!-- VE-CONTROLLED:COMPONENT-SCRIPTS:BEGIN -->
  <!-- VE-CONTROLLED:COMPONENT-SCRIPTS:END -->
  ```

  Require each pair exactly once, in document order, with style markers in `<head>`, content markers in the existing generated-content region, and script markers at the current trusted-script boundary.

- [ ] Add failing fixed-region tests. Replace each controlled-slot body with a constant sentinel, hash the remaining document, and compare it with the similarly normalized skeleton. A byte change outside the three bodies must fail `fixed_region_mismatch`; a content change inside a slot proceeds to slot-specific validation.

- [ ] Add failing content tests that reject `<style>`, `<script>`, `<link>`, `<base>`, `<iframe>`, `<object>`, `<embed>`, inline `style`, `on*` attributes, executable URLs, external URLs, and nested controlled-slot markers in compatibility markup. Preserve every stricter existing `check.sh` rule.

- [ ] Add failing controlled-asset tests. Each style/script block must have component ID, contract version, asset ID, and SHA-256 provenance; the registry must declare the asset, slot type, digest, and dependency. Reject unknown, tampered, external, duplicate-conflicting, or wrong-slot assets. With no production script asset registered, any non-empty script slot must fail.

- [ ] Run the focused tests and observe marker/checker failures:

  ```bash
  PYTHONPATH=skills/visual-explain/scripts \
    python3 -m unittest discover \
      -s skills/visual-explain/scripts/tests \
      -p 'test_controlled_slots.py' -v
  ```

  Expected: failures for missing controlled markers and checker functions.

- [ ] Insert only the six markers into `skeleton.html`. Move no existing fixed CSS/JavaScript during this task. Keep all slot bodies empty.

- [ ] Implement controlled-slot extraction with deterministic string boundaries, normalized fixed-region comparison, existing-rule compatibility content validation, and registry/manifest/hash asset checks. Do not use an HTML-repair parser that could normalize unsafe input before validation.

- [ ] Extend `check.sh` to run all existing checks first and then invoke `check_component_html.py`. Resolve the script directory from `${BASH_SOURCE[0]}` so the call works from any current directory; pass absolute paths for the document, sibling script, skeleton, and registry. Preserve the existing CLI and exit behavior.

- [ ] Run the focused tests, then legacy regressions:

  ```bash
  PYTHONPATH=skills/visual-explain/scripts \
    python3 -m unittest discover \
      -s skills/visual-explain/scripts/tests \
      -p 'test_controlled_slots.py' -v
  bash skills/visual-explain/scripts/check.sh skills/visual-explain/scripts/tests/catalog.html
  bash skills/visual-explain/scripts/check.sh skills/visual-explain/examples/example-proposal.html
  ```

  Expected: unit tests pass; both legacy documents exit 0. A marker-free document is recognized as pre-migration legacy only when it also contains no `data-ve-section-kind`, `data-ve-component`, or controlled-slot marker. Any component/provenance-bearing document with a missing marker fails. Newly flattened documents must contain all markers.

- [ ] Commit:

  ```bash
  git add skills/visual-explain/assets/skeleton.html \
    skills/visual-explain/scripts/check.sh \
    skills/visual-explain/scripts/check_component_html.py \
    skills/visual-explain/scripts/ve_components/checker.py \
    skills/visual-explain/scripts/tests/test_controlled_slots.py \
    skills/visual-explain/scripts/tests/component-bad-fixed-region.html \
    skills/visual-explain/scripts/tests/component-bad-content-style.html \
    skills/visual-explain/scripts/tests/component-bad-content-script.html \
    skills/visual-explain/scripts/tests/component-bad-asset-hash.html
  git commit -m "feat(visual-explain): protect controlled component slots"
  ```

  Rollback: revert this commit to restore the exact baseline skeleton/checker. Tasks 1–2 remain dark generation-time code and do not affect legacy output.

### Task 4: Build one mixed-document composition and flattening route

**Files:**

- Create: `skills/visual-explain/scripts/ve_components/assembly.py`
- Create: `skills/visual-explain/scripts/ve_components/flatten.py`
- Create: `skills/visual-explain/scripts/build_explainer.py`
- Create: `skills/visual-explain/scripts/tests/test_mixed_assembly.py`
- Create: `skills/visual-explain/scripts/tests/compatibility-valid-fragment.html`
- Create: `skills/visual-explain/scripts/tests/component-valid-mixed.json`
- Create: `skills/visual-explain/scripts/tests/component-valid-weak-model.json`
- Create: `skills/visual-explain/scripts/tests/component-bad-weak-model-style.json`
- Create: `skills/visual-explain/scripts/tests/component-bad-weak-model-script.json`

**Interfaces:**

- Consumes: validation, selection, registry, checker, skeleton markers, and injected trusted renderer resolver.
- Produces: `RenderedCanonical`, `CompositionResult`, `BuildPaths`, `BuildResult`, `render_canonical`, `compose_sections`, `flatten_document`, and `build_document`. `CompositionResult` contains ordered rendered/compatibility sections plus deduplicated style/script asset references and canonical manifests. `BuildResult` contains final HTML, diagnostics, and the published output path.

- [ ] Write a failing mixed assembly test with three ordered sections: canonical matrix test double, compatibility `layers` fragment, canonical flow test double. Assert final content order, one set of controlled markers, compatibility provenance, canonical instance provenance, and deduplicated trusted styles.

- [ ] Add spy assertions proving the compatibility section never calls `validate_canonical_section`, `narrow_candidates`, `resolve_component`, or the renderer resolver. It must call `validate_content_markup`, receive the wrapper `data-ve-section-kind="compatibility"`, `data-ve-compat-source="legacy-html-insertion"`, and enter the same `compose_sections`/`flatten_document` calls as canonical output.

- [ ] Add failure tests for absent/false provenance, compatibility CSS/JavaScript injection, canonical failure with no silent fallback, duplicate section/instance IDs, registry lookup failure, renderer diagnostic failure, and final checker failure.

- [ ] Add `component-valid-weak-model.json` with one compatibility-only matrix or flow section using `source="legacy-html-insertion"` and `reason="weak-model-degradation"`. Assert `validate_assembly` accepts the vocabulary values, canonical validation/selection/registry/renderer spies remain uncalled, the output wrapper retains the exact reason, markup enters only the content slot, and final checking passes.

- [ ] Add `component-bad-weak-model-style.json` and `component-bad-weak-model-script.json` with valid weak-model provenance but compatibility markup containing arbitrary CSS and JavaScript respectively. Assert both fail existing-rule content validation, publish no output, and do not switch routes. Keep a separate canonical-failure assertion proving there is no automatic weak-model fallback.

- [ ] Run the focused tests and observe missing assembly/flatten failures:

  ```bash
  PYTHONPATH=skills/visual-explain/scripts \
    python3 -m unittest discover \
      -s skills/visual-explain/scripts/tests \
      -p 'test_mixed_assembly.py' -v
  ```

  Expected: import or missing-function failure.

- [ ] Implement `compose_sections` as an order-preserving function over the two discriminated section types. It may scope IDs and deduplicate identical asset IDs/digests; it may not infer relationships, choose components, merge graphs, or create cross-component connectors.

- [ ] Implement `flatten_document` with exact controlled-marker replacement. Emit one `<style>` per trusted deduplicated asset with asset provenance, ordered section markup in the content slot, and zero scripts unless a registry entry supplies an allowlisted script. Reject any change outside controlled bodies by comparing normalized fixed regions before returning.

- [ ] Implement `build_document` and `build_explainer.py`. The CLI loads the assembly request and registry, processes canonical and compatibility branches as specified, calls the single composer/flattener, passes the resulting `CompositionResult` as `expected` to final checking, writes the output only after all checks pass, and prints diagnostics without a traceback for contract failures. Use a temporary file plus atomic rename so a failed build does not leave a partial HTML document.

- [ ] Run mixed and prior tests:

  ```bash
  PYTHONPATH=skills/visual-explain/scripts \
    python3 -m unittest discover \
      -s skills/visual-explain/scripts/tests \
      -p 'test_*.py' -v
  ```

  Expected: all tests pass with the test-double renderers; production registry still has no active component entries.

- [ ] Commit:

  ```bash
  git add skills/visual-explain/scripts/ve_components/assembly.py \
    skills/visual-explain/scripts/ve_components/flatten.py \
    skills/visual-explain/scripts/build_explainer.py \
    skills/visual-explain/scripts/tests/test_mixed_assembly.py \
    skills/visual-explain/scripts/tests/compatibility-valid-fragment.html \
    skills/visual-explain/scripts/tests/component-valid-mixed.json \
    skills/visual-explain/scripts/tests/component-valid-weak-model.json \
    skills/visual-explain/scripts/tests/component-bad-weak-model-style.json \
    skills/visual-explain/scripts/tests/component-bad-weak-model-script.json
  git commit -m "feat(visual-explain): assemble mixed component documents"
  ```

  Rollback: revert this commit; controlled empty slots and their checks remain, while no production component is exposed.

### Task 5: Add the semantic `matrix` component as a complete registry unit

**Files:**

- Modify: `skills/visual-explain/scripts/ve_components/renderers/__init__.py`
- Create: `skills/visual-explain/scripts/ve_components/renderers/matrix.py`
- Create: `skills/visual-explain/assets/components/matrix.css`
- Modify: `skills/visual-explain/assets/components/registry.json`
- Create: `skills/visual-explain/scripts/tests/test_matrix_renderer.py`

**Interfaces:**

- Consumes: `CanonicalSection`, `MatrixPayload`, `ComponentDefinition`, and shared escaping/manifest types.
- Produces: `render_matrix(section, definition) -> RenderResult` and trusted key `matrix@1` in the renderer allowlist.
- Registry responsibility: two-axis classification and intersection comparison only.

- [ ] Write failing tests for a complete registry entry and renderer result. The result must consume every row, column, cell, caption, certainty, source, and accessibility semantic ID; declare `matrix.css`; declare no script; and return no undeclared relationship.

- [ ] Write failing markup assertions for a semantic `<figure>` containing a visible caption and summary, a `<table>`, row/column headers with stable `data-ve-semantic-id`, cells with `data-ve-row-id` and `data-ve-column-id`, visible certainty/source references, and a deterministic DOM order matching the declared rows/columns. Escape all authored text.

- [ ] Write failing responsive/static assertions: no hidden core cell content, no event handlers, no interaction requirement, no external references, and a CSS namespace rooted at `[data-ve-component="matrix"]`. The minimal narrow layout may scroll the table horizontally only if headers, caption, and cell associations remain present and readable.

- [ ] Run the focused tests and observe missing renderer/asset failures:

  ```bash
  PYTHONPATH=skills/visual-explain/scripts \
    python3 -m unittest discover \
      -s skills/visual-explain/scripts/tests \
      -p 'test_matrix_renderer.py' -v
  ```

  Expected: renderer or registry-entry failure.

- [ ] Implement the minimal static renderer and CSS. Use existing skeleton tokens; do not choose a new color system, decorative grid treatment, animation, or density variants.

- [ ] Compute the final asset digest and add the entire `matrix@1` registry entry only after renderer, CSS, fallback, accessibility, responsive, dependency, and checker-rule fields are complete:

  ```bash
  shasum -a 256 skills/visual-explain/assets/components/matrix.css
  ```

  Record the exact digest in `registry.json`; do not use a wildcard or runtime trust-on-first-use value. The entry must copy component ID `matrix`, contract version `1`, relationship kind `two-axis`, and capabilities exactly from `component-vocabulary.json`. Task 1 fixtures are immutable inputs here; a mismatch fails Task 5 rather than authorizing a fixture rename.

- [ ] Run the focused test and build the canonical matrix fixture into a temporary output:

  ```bash
  PYTHONPATH=skills/visual-explain/scripts \
    python3 -m unittest discover \
      -s skills/visual-explain/scripts/tests \
      -p 'test_matrix_renderer.py' -v
  tmp="$(mktemp -t visual-explain-matrix).html"
  python3 skills/visual-explain/scripts/build_explainer.py \
    --assembly skills/visual-explain/scripts/tests/component-valid-matrix.json \
    --output "$tmp"
  bash skills/visual-explain/scripts/check.sh "$tmp"
  rm "$tmp"
  ```

  Expected: tests pass; build and checker exit 0.

- [ ] Commit:

  ```bash
  git add skills/visual-explain/scripts/ve_components/renderers \
    skills/visual-explain/assets/components/matrix.css \
    skills/visual-explain/assets/components/registry.json \
    skills/visual-explain/scripts/tests/test_matrix_renderer.py
  git commit -m "feat(visual-explain): add semantic matrix component"
  ```

  Rollback: revert this commit; the shared dark pipeline and compatibility behavior remain intact.

### Task 6: Add the semantic `flow` component through the same route

**Files:**

- Create: `skills/visual-explain/scripts/ve_components/renderers/flow.py`
- Create: `skills/visual-explain/assets/components/flow.css`
- Modify: `skills/visual-explain/scripts/ve_components/renderers/__init__.py`
- Modify: `skills/visual-explain/assets/components/registry.json`
- Create: `skills/visual-explain/scripts/tests/test_flow_renderer.py`

**Interfaces:**

- Consumes: the exact Task 5 renderer interface; do not add a flow-only orchestration or flattening API.
- Produces: `render_flow(section, definition) -> RenderResult` and trusted key `flow@1`.
- Registry responsibility: explicit order, directed transition, and branch relationships only.

- [ ] Write failing tests proving `flow@1` uses the same registry loader, resolver, `RenderResult`, composer, controlled slots, and checker rules as `matrix@1`.

- [ ] Write failing payload tests for duplicate nodes, dangling edges, missing `from`/`to`/relationship type, accidental self-edge, ambiguous start without a reading-order hint, unreachable nodes, and a cycle when the relationship declares acyclic order. Do not infer or reverse an edge from prose or input array order.

- [ ] Write failing markup assertions for a semantic `<figure>` with visible caption/summary and an ordered or grouped list of nodes plus a visible edge list. Every edge must expose `data-ve-from`, `data-ve-to`, `data-ve-relation`, a visible direction indicator, and its semantic ID. Include visible certainty/source references and deterministic reading order.

- [ ] Write failing static/accessibility assertions: all nodes/edges remain present without scripts; no element requires clicking to reveal core relationships; no external references or inline handlers; CSS is rooted at `[data-ve-component="flow"]`; responsive CSS may stack but cannot reverse semantic order.

- [ ] Run the focused tests and observe missing renderer/asset failures:

  ```bash
  PYTHONPATH=skills/visual-explain/scripts \
    python3 -m unittest discover \
      -s skills/visual-explain/scripts/tests \
      -p 'test_flow_renderer.py' -v
  ```

  Expected: renderer or registry-entry failure.

- [ ] Implement the minimal static renderer and CSS using existing tokens. Do not implement free-coordinate nodes, SVG connector routing, animation, pan/zoom, filtering, or decorative transitions.

- [ ] Compute and record the exact CSS digest only when the complete `flow@1` contract is ready:

  ```bash
  shasum -a 256 skills/visual-explain/assets/components/flow.css
  ```

  The entry must copy component ID `flow`, contract version `1`, relationship kind `directed-graph`, and capabilities exactly from `component-vocabulary.json`. Task 1 fixtures are immutable inputs here; a mismatch fails Task 6.

- [ ] Run the focused test and build/check the canonical flow fixture:

  ```bash
  PYTHONPATH=skills/visual-explain/scripts \
    python3 -m unittest discover \
      -s skills/visual-explain/scripts/tests \
      -p 'test_flow_renderer.py' -v
  tmp="$(mktemp -t visual-explain-flow).html"
  python3 skills/visual-explain/scripts/build_explainer.py \
    --assembly skills/visual-explain/scripts/tests/component-valid-flow.json \
    --output "$tmp"
  bash skills/visual-explain/scripts/check.sh "$tmp"
  rm "$tmp"
  ```

  Expected: tests pass; build and checker exit 0.

- [ ] Commit:

  ```bash
  git add skills/visual-explain/scripts/ve_components/renderers/flow.py \
    skills/visual-explain/scripts/ve_components/renderers/__init__.py \
    skills/visual-explain/assets/components/flow.css \
    skills/visual-explain/assets/components/registry.json \
    skills/visual-explain/scripts/tests/test_flow_renderer.py
  git commit -m "feat(visual-explain): add semantic flow component"
  ```

  Rollback: revert this commit to remove `flow@1`; do not promote the vertical slice while only `matrix@1` remains.

### Task 7: Complete four-layer checker coverage and vertical-slice fixtures

**Files:**

- Modify: `skills/visual-explain/scripts/ve_components/checker.py`
- Modify: `skills/visual-explain/scripts/check_component_html.py`
- Modify: `skills/visual-explain/scripts/check.sh`
- Create: `skills/visual-explain/scripts/tests/test_component_checker.py`
- Create: `skills/visual-explain/scripts/tests/component-bad-selection.json`
- Create: `skills/visual-explain/scripts/tests/component-bad-selection-reason.json`
- Create: `skills/visual-explain/scripts/tests/component-bad-combined-relationship.json`
- Create: `skills/visual-explain/scripts/tests/component-bad-flow-edge.json`
- Create: `skills/visual-explain/scripts/tests/component-bad-matrix-cell.json`
- Create: `skills/visual-explain/scripts/tests/component-bad-compatibility-provenance.html`
- Modify: `skills/visual-explain/scripts/tests/catalog.html`

**Interfaces:**

- Consumes: canonical IR, registry rules, render manifests, final provenance attributes, and existing checker outcomes.
- Produces: complete four-layer diagnostics from the unchanged `check.sh <document>` public command and from `build_document` before output publication.

- [ ] Write a table-driven failing test covering all four layers:

  - safety/fixed regions: external reference, changed fixed byte, content CSS/script, wrong slot, unknown asset, digest tamper, undeclared dependency;
  - IR/selection: malformed declaration, no candidate, multiple candidates accepted, out-of-set selection, reason mismatch;
  - component/manifest: missing semantic ID, introduced relationship, component/version mismatch, missing caption/certainty/source/accessibility, undeclared fallback;
  - flattened document: duplicate DOM ID, matrix row/column mismatch, reversed or missing flow edge attributes, bad reading order, hidden core content, missing provenance, compatibility markup outside content slot.

- [ ] Add a static-first test that removes the entire component-script slot body from valid matrix, flow, and mixed outputs and requires all semantic IDs, visible relationship labels/directions, captions, certainty, and sources still to pass. The production registry must have empty script asset arrays for both MVP components.

- [ ] Add a trusted-asset test that changes one byte of `matrix.css` or `flow.css` after loading the registry and requires build/check failure before final output replacement. Restore the byte within the test fixture or use an isolated temporary copy; never mutate the working-tree asset in-place during the test.

- [ ] Add a mixed-document test that validates canonical matrix → compatibility layers → canonical flow in one HTML, one skeleton, one content slot, one final checker invocation, with no registry/renderer provenance on the compatibility wrapper and no compatibility content in style/script slots.

- [ ] Build `component-valid-weak-model.json`, pass the result through the same final checker, and assert the artifact retains `data-ve-compat-source="legacy-html-insertion"` and `data-ve-compat-reason="weak-model-degradation"`. Run both bad weak-model JSON fixtures through `build_explainer.py` and assert non-zero exit, no output publication, and explicit content-safety diagnostics. This supplements rather than replaces the generic compatibility and no-silent-fallback tests.

- [ ] Run the focused checker tests and observe missing semantic/final checks:

  ```bash
  PYTHONPATH=skills/visual-explain/scripts \
    python3 -m unittest discover \
      -s skills/visual-explain/scripts/tests \
      -p 'test_component_checker.py' -v
  ```

  Expected: at least one assertion fails in each not-yet-complete checker layer.

- [ ] Implement the missing reusable checker rules. When `expected` is present, compare every canonical renderer manifest and compatibility section record to final DOM data attributes without executing scripts; this is the IR/manifest-to-DOM gate used by `build_document`. When `expected=None`, validate the artifact's final provenance, semantic relationship attributes, static content, controlled assets, and fixed regions, and do not claim source-IR completeness. Keep `check.sh` fail-closed and retain every pre-existing check before the new checker call.

- [ ] Generate valid matrix, flow, and mixed outputs in temporary files, check them, then add concise links/examples to `catalog.html`. Do not replace or visually redesign unrelated catalog entries.

- [ ] Run the complete suite and explicit bad fixtures:

  ```bash
  PYTHONPATH=skills/visual-explain/scripts \
    python3 -m unittest discover \
      -s skills/visual-explain/scripts/tests \
      -p 'test_*.py' -v
  for fixture in \
    skills/visual-explain/scripts/tests/component-bad-fixed-region.html \
    skills/visual-explain/scripts/tests/component-bad-content-style.html \
    skills/visual-explain/scripts/tests/component-bad-content-script.html \
    skills/visual-explain/scripts/tests/component-bad-asset-hash.html \
    skills/visual-explain/scripts/tests/component-bad-compatibility-provenance.html; do
    if bash skills/visual-explain/scripts/check.sh "$fixture"; then
      echo "unexpected pass: $fixture" >&2
      exit 1
    fi
  done
  bash skills/visual-explain/scripts/check.sh skills/visual-explain/scripts/tests/catalog.html
  bash skills/visual-explain/scripts/check.sh skills/visual-explain/examples/example-proposal.html
  ```

  Expected: unit suite passes; every bad HTML fixture exits non-zero; catalog and legacy example exit 0. Do not alter the known causal-reversal fixture or use its result as the foundation gate.

- [ ] Commit:

  ```bash
  git add skills/visual-explain/scripts/ve_components/checker.py \
    skills/visual-explain/scripts/check_component_html.py \
    skills/visual-explain/scripts/check.sh \
    skills/visual-explain/scripts/tests/test_component_checker.py \
    skills/visual-explain/scripts/tests/component-bad-fixed-region.html \
    skills/visual-explain/scripts/tests/component-bad-content-style.html \
    skills/visual-explain/scripts/tests/component-bad-content-script.html \
    skills/visual-explain/scripts/tests/component-bad-asset-hash.html \
    skills/visual-explain/scripts/tests/component-bad-selection.json \
    skills/visual-explain/scripts/tests/component-bad-selection-reason.json \
    skills/visual-explain/scripts/tests/component-bad-combined-relationship.json \
    skills/visual-explain/scripts/tests/component-bad-flow-edge.json \
    skills/visual-explain/scripts/tests/component-bad-matrix-cell.json \
    skills/visual-explain/scripts/tests/component-bad-compatibility-provenance.html \
    skills/visual-explain/scripts/tests/catalog.html
  git commit -m "test(visual-explain): enforce component safety contracts"
  ```

  Rollback: revert this commit only if Tasks 5–6 have not been promoted. Never retain production component entries while removing their required checker rules.

### Task 8: Promote matrix/flow authoring and document safe extension

**Files:**

- Modify: `skills/visual-explain/SKILL.md`
- Modify: `skills/visual-explain/references/patterns.md`
- Modify: `skills/visual-explain/references/design-system.md`
- Verify unchanged: `skills/visual-explain/examples/example-proposal.html`
- Verify unchanged: `docs/superpowers/specs/2026-07-10-visual-explain-component-foundation.md`

**Deliverable:** Normal `matrix`/`flow` guidance uses the canonical IR/build route; all other formats and explicit weak-model cases produce labelled compatibility markup that enters the same final assembly.

- [ ] Update `SKILL.md` with one decision sequence: declare relationship → use registry discovery → choose explicitly from deterministic candidates → record matched-capability reason → build/check. State that matrix/flow canonical failure is reported, not silently converted.

- [ ] Document weak-model degradation as an explicit compatibility section with `source=legacy-html-insertion`, `reason=weak-model-degradation`, and a format. State that it bypasses canonical selection/registry/renderer, can coexist with canonical sections, enters only the content slot, and still passes `check.sh`.

- [ ] Update `patterns.md` with complete canonical JSON examples for one matrix, one flow, and one mixed document. Keep other formats on the legacy markup source and do not redesign them.

- [ ] Update `design-system.md` with ownership rules: skeleton global tokens/fixed regions; component namespaced minimal CSS; empty production script assets; static-first/accessibility; trusted asset digest updates; and the ten-step extension gate from the spec. Do not add new colors, typefaces, spacing systems, animations, or individual visual treatments.

- [ ] Add a documentation consistency test to `test_component_contract.py` that parses every JSON code block labelled as an assembly example and validates it with `validate_assembly`. Assert only `matrix` and `flow` appear in production registry entries.

- [ ] Extend that consistency test to assert every documented component ID/version, relationship kind, capability, compatibility source, and compatibility reason is present in `component-vocabulary.json`; documentation may not introduce aliases.

- [ ] Run the full acceptance commands in the next section. Compare the current `example-proposal.html` digest with the Task 0 digest or repository version to confirm it was not rewritten.

- [ ] Commit promotion documentation only after all commands pass:

  ```bash
  git add skills/visual-explain/SKILL.md \
    skills/visual-explain/references/patterns.md \
    skills/visual-explain/references/design-system.md \
    skills/visual-explain/scripts/tests/test_component_contract.py
  git commit -m "docs(visual-explain): promote matrix and flow component authoring"
  ```

  Rollback: revert this documentation commit to stop promotion while leaving the opt-in implementation available. If runtime rollback is also required, revert Tasks 7 → 6 → 5 → 4 → 3 in reverse order; Tasks 1–2 may safely remain dark.

## Testing Strategy

Use TDD for every task: add the smallest failing test, run it and confirm the intended failure, implement only the behavior needed, then rerun the focused and cumulative suites before committing.

### Test layers

| Layer | Test focus | Command/gate |
|---|---|---|
| Schema and model | required/optional fields, unknown-field rejection, semantic IDs, matrix/flow references, compatibility discriminator | `PYTHONPATH=skills/visual-explain/scripts python3 -m unittest discover -s skills/visual-explain/scripts/tests -p 'test_component_contract.py' -v` |
| Selection and registry | one/many/zero candidates, explicit reason, no heuristics, exact renderer/version/assets/checker rules | `PYTHONPATH=skills/visual-explain/scripts python3 -m unittest discover -s skills/visual-explain/scripts/tests -p 'test_component_selection.py' -v` |
| Fixed-region and slots | marker uniqueness/order, normalized fixed-region equality, content prohibitions, asset hashes | `PYTHONPATH=skills/visual-explain/scripts python3 -m unittest discover -s skills/visual-explain/scripts/tests -p 'test_controlled_slots.py' -v` |
| Assembly | mixed order, compatibility bypass spies, one composer/flattener, atomic output | `PYTHONPATH=skills/visual-explain/scripts python3 -m unittest discover -s skills/visual-explain/scripts/tests -p 'test_mixed_assembly.py' -v` |
| Weak-model degradation | allowed provenance vocabulary, canonical bypass, final provenance, CSS/JavaScript rejection, no silent fallback | `PYTHONPATH=skills/visual-explain/scripts python3 -m unittest discover -s skills/visual-explain/scripts/tests -p 'test_mixed_assembly.py' -v` followed by the `test_component_checker.py` command below |
| Renderer contract | semantic HTML, escaping, manifest coverage, no scripts, responsive/static invariants | matrix and flow focused suites |
| Final checker | IR-to-DOM traceability, provenance, asset tamper, no external dependency, static-first | `PYTHONPATH=skills/visual-explain/scripts python3 -m unittest discover -s skills/visual-explain/scripts/tests -p 'test_component_checker.py' -v` |
| Legacy regression | existing catalog and example remain valid; old bad fixtures remain bad | existing `check.sh` commands |

### Full acceptance command set

Run from repository root:

```bash
PYTHONPATH=skills/visual-explain/scripts \
  python3 -m unittest discover \
    -s skills/visual-explain/scripts/tests \
    -p 'test_*.py' -v

matrix_out="$(mktemp -t visual-explain-matrix).html"
flow_out="$(mktemp -t visual-explain-flow).html"
mixed_out="$(mktemp -t visual-explain-mixed).html"
weak_out="$(mktemp -t visual-explain-weak).html"

python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/scripts/tests/component-valid-matrix.json \
  --output "$matrix_out"
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/scripts/tests/component-valid-flow.json \
  --output "$flow_out"
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/scripts/tests/component-valid-mixed.json \
  --output "$mixed_out"
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/scripts/tests/component-valid-weak-model.json \
  --output "$weak_out"

bash skills/visual-explain/scripts/check.sh "$matrix_out"
bash skills/visual-explain/scripts/check.sh "$flow_out"
bash skills/visual-explain/scripts/check.sh "$mixed_out"
bash skills/visual-explain/scripts/check.sh "$weak_out"
bash skills/visual-explain/scripts/check.sh skills/visual-explain/scripts/tests/catalog.html
bash skills/visual-explain/scripts/check.sh skills/visual-explain/examples/example-proposal.html

if rg -n '<script[^>]+src=|<link[^>]+href=|@import|https?://|type="module"' \
  "$matrix_out" "$flow_out" "$mixed_out" "$weak_out"; then
  echo "external or module dependency found" >&2
  exit 1
fi

for bad_weak in \
  skills/visual-explain/scripts/tests/component-bad-weak-model-style.json \
  skills/visual-explain/scripts/tests/component-bad-weak-model-script.json; do
  if python3 skills/visual-explain/scripts/build_explainer.py \
    --assembly "$bad_weak" --output "$weak_out.rejected"; then
    echo "unexpected weak-model compatibility pass: $bad_weak" >&2
    exit 1
  fi
  test ! -e "$weak_out.rejected"
done

rm "$matrix_out" "$flow_out" "$mixed_out" "$weak_out"
```

Expected: unit tests pass; all build/check commands exit 0; the dependency scan finds no matches and the shell block exits 0.

Do not substitute a browser screenshot for semantic/static assertions. Browser smoke and finished visual review are outside this foundation slice.

## Migration, Rollback, and Compatibility

### Activation order

1. Land contracts and selection as dark generation-time code.
2. Land empty controlled slots and checker support; prove legacy output remains accepted.
3. Land the opt-in mixed assembly builder with test renderers only.
4. Land `matrix@1`; do not promote while it is the sole production component.
5. Land `flow@1`; run the shared-route and four-layer checker gate for both.
6. Promote matrix/flow authoring in `SKILL.md` and references.

The production registry contains no partial component. A component entry, renderer allowlist entry, minimal CSS asset, exact digest, fallback, accessibility contract, and checker rules are added in the same task/commit.

### Rollback rules

- Before documentation promotion, the new builder is opt-in. Revert its latest milestone without changing legacy authoring.
- After promotion, first revert the documentation commit so authors stop choosing the canonical path.
- If one renderer must roll back, remove its registry entry, trusted renderer mapping, assets, and checker expectations together. Do not leave a selectable component with missing safety rules.
- The controlled slots may remain empty and checked even when no renderer is active. To restore the exact legacy skeleton, revert Task 3 after reverting Tasks 4–7.
- Never weaken final checking to preserve a broken component. Disable selection/promotion for that component instead.
- Already-produced self-contained HTML remains renderable because it contains no registry or runtime dependency. Checker behavior for new validations may reject unsafe old artifacts without changing their runtime rendering.

### Compatibility behavior

- `layers`, `compare`, `timeline`, `kpi`, `bars`, `terms`, `details`, and `stepper` continue to originate as old-rule HTML markup.
- A weak model may explicitly choose compatibility markup for matrix/flow, but provenance must say `reason=weak-model-degradation`; this is never canonical success.
- Allowed compatibility provenance is defined once in `component-vocabulary.json`: source `legacy-html-insertion` and reasons `unmigrated-format` or `weak-model-degradation`. Unknown aliases fail validation.
- Compatibility markup is wrapped as a compatibility section and is ordered with canonical sections by the one composer.
- It bypasses canonical IR selection, registry resolution, renderer execution, component manifests, and controlled component assets.
- It enters only the controlled content slot and cannot contain style/script/link injection, inline executable behavior, external dependencies, or fixed-region markers.
- Existing content and final checker rules remain mandatory.
- Canonical failure returns diagnostics and leaves the output untouched. It never silently switches to compatibility.

## Acceptance Criteria

The vertical slice is complete only when every item below is evidenced by automated tests and the full acceptance command set:

- `matrix` and `flow` are the only production component registry entries.
- Component IDs, contract versions, relationship kinds, capabilities, compatibility sources, and compatibility reasons exactly match the Task 1 authoritative vocabulary across schema, fixtures, registry, tests, and documentation.
- Both use the same common envelope, validation, deterministic selection, explicit reason check, registry resolver, `RenderResult`, composer, flattener, controlled slots, and final checker entry point.
- The canonical authoring format contains no HTML, CSS, JavaScript, DOM operation, renderer class, connector geometry, or free coordinate.
- Matrix payload validation enforces row/column/cell identity and rejects orphan or duplicate intersections.
- Flow payload validation enforces explicit `from`, `to`, and relationship type and rejects general direction/order integrity failures without modifying the known causal-reversal fixture.
- One valid declaration may return multiple candidates; explicit selection of a returned member works. Invalid, no-match, out-of-set, and reason-mismatch outcomes have distinct diagnostics.
- Registry resolution fails closed for unknown version, renderer, asset hash, dependency, or checker rule.
- A final explainer can order canonical matrix, compatibility markup, and canonical flow in one document.
- The mixed explainer uses exactly one composition/flattening route and one final checker invocation.
- Compatibility sections demonstrably bypass canonical selection, registry, and renderer calls and carry `legacy-html-insertion` provenance.
- The dedicated `component-valid-weak-model.json` fixture with `reason=weak-model-degradation` builds and passes final checking; dedicated CSS and JavaScript injection fixtures fail without output publication or fallback.
- Compatibility markup appears only in the content slot and cannot populate style/script slots or modify fixed regions.
- Style assets are namespaced, registry-allowlisted, manifest-declared, hash-verified, deduplicated, and inlined. The MVP registry declares no script assets.
- Every byte outside controlled-slot bodies matches the skeleton's fixed-region baseline under the established normalization; deliberate mutation fails.
- Matrix uses semantic table relationships; flow uses explicit semantic node/edge order. All authored text is escaped.
- Caption, certainty, sources, accessibility label/summary, semantic IDs, and relationship direction survive IR → manifest → final DOM.
- Removing optional-script-slot contents leaves every core relationship and label visible and checker-valid.
- Narrow-layout CSS preserves semantic reading order and content; it does not require interaction.
- Final outputs contain no external reference, module import, runtime loader, or dependency.
- Existing `catalog.html`, `example-proposal.html`, and current safety fixtures retain their prior expected outcomes.
- `SKILL.md` makes canonical matrix/flow the normal route only after both pass; other formats remain compatibility sources.
- No new UI framework, diagram library, heuristic router, visual-language system, rich interaction, animation, or other-format migration is present.

## Deferred Work and Risks

Deferred work is explicitly outside phase 1:

- finished matrix grid styling, density, emphasis, and visual variants;
- flow connector geometry, node shapes, branch layout, spatial optimization, and SVG/free-coordinate rendering;
- shared color, typography, shape, spacing, iconography, or motion language;
- animation, cross-highlighting, filtering, pan/zoom, and cross-component interaction;
- heuristic registry ranking, auto-selection, confidence, or override;
- migrations for `layers`, `compare`, `timeline`, `kpi`, `bars`, `terms`, `details`, and `stepper`;
- removal of compatibility markup generation;
- a full registry deprecation lifecycle, localization expansion, themes, performance budgets, and cross-component semantic links;
- resolution of the known causal-reversal fixture issue;
- browser-based aesthetic smoke testing.

Risks and their implementation controls:

- **IR expansion:** Reject fields not exercised by matrix/flow; add future fields only with a component extension review.
- **Registry becomes routing policy:** Keep selection as pure capability matching and reject ranking metadata.
- **Trusted asset escape hatch:** Treat registry ID/version/digest, renderer allowlist, manifest declaration, namespace, slot type, CSP, and no-external-reference checks as a single fail-closed gate.
- **Fixed-region regression:** Normalize only the three controlled bodies; hash/compare everything else and retain old checker tests.
- **Compatibility hides canonical defects:** Require explicit provenance and no-silent-fallback tests; promotion metrics distinguish canonical from compatibility output.
- **Weak-model authoring errors:** Keep schemas small, diagnostics bounded, examples complete, and compatibility deliberate.
- **Manifest/DOM drift:** Require semantic ID and relationship coverage in final checker tests.
- **JavaScript dependency creep:** Ship no script asset for matrix/flow and test the empty/removed script slot.
- **Partial vertical slice promotion:** Make Task 8 depend on both renderer tasks and the complete four-layer checker gate.
- **Visual work leaks into foundation:** Limit CSS to semantic legibility, existing tokens, namespace, static accessibility, and responsive order. Defer aesthetic review.

The later choice between component-by-component visual exploration and a shared matrix/flow visual grammar is non-blocking and does not alter this plan.

ADOPTED: I-1 — Added an authoritative Task 1 capability/provenance vocabulary with exact matrix/flow IDs, versions, relationship kinds, capability strings, schema/fixture consistency tests, and later registry/documentation conformance gates.
ADOPTED: I-2 — Added allowed compatibility-reason vocabulary plus dedicated valid and CSS/JavaScript-invalid weak-model-degradation fixtures, canonical-bypass assertions, final-check coverage, and no-output/no-silent-fallback acceptance gates.
STATUS: complete
