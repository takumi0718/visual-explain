# visual-explain canonical v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The approved design spec is `spec.md` next to this plan (identical to the repository's committed canonical-v2 spec); every numeric limit, enum name, diagnostic code, and geometry constant referenced below is normative there. Do not write implementation code from memory of this plan alone — open the spec section named in each task first.

**Goal:** Extend visual-explain's canonical IR pipeline from 2 components (matrix, flow) to 10 (adding enumeration, chevron, pyramid, stairs, logic-tree, waterfall, slope, evidence-map = 8 new / 10 diagram formats), in six atomic slices, without weakening any existing safety contract.

**Architecture:** Each slice completes the design-system.md ten-step extension gate atomically: vocabulary → IR schema → typed model → strict validation → trusted renderer + manifest → namespaced token-only CSS + strict SHA-256 digest → `TRUSTED_RENDERERS` → registry entry → four-layer checker rules + bad fixtures → build + full test + docs sync. Slice 1 additionally generalizes the matrix/flow-hardcoded core (payload dispatch, semantic-ID collection, annotation targets, notes-class check, manifest cross-checks, closed code/rule sets) so slices 2–6 are additive.

**Tech Stack:** Python 3 standard library only (no dependency installs), JSON Schema draft-07 (documentation-grade; Python validators are authoritative), pytest for tests, `check.sh` (bash + embedded Python) for document checking. Repository: `~/workspace/visual-explain`, branch `canonical-v2`, all paths below relative to repo root. Skill root: `skills/visual-explain/`.

## Global Constraints

Copied from `spec.md`; every task's requirements implicitly include all of these.

- **Skeleton bytes are inviolable:** `skills/visual-explain/assets/skeleton.html` tokens, fixed regions, and fixed JavaScript are byte-identical before and after every slice. No token additions, overrides, or edits. `git diff` for a slice must never touch `skeleton.html`.
- **IR is semantics only:** canonical IR carries numbers, text, and declarations — never HTML/CSS/JS/DOM operations/coordinates. All layout math (waterfall offsets, slope coordinates, stair heights, pyramid widths) lives in renderers. New payload field names must not collide with `validation.FORBIDDEN_AUTHORING_KEYS` (spec confirms none do).
- **Fail closed:** every rejection is a bounded `Diagnostic` whose code is registered in `diagnostics.ALL_CODES`; unknown codes raise at construction. No silent fallback to compatibility markup; build failures print diagnostics and produce no output file (atomic temp-file write already guarantees this).
- **Static first:** production registry script assets stay empty for all 10 components. Renderers return `script_asset_ids=()`. The content slot bans inline `style` attributes, `on*` attributes, and external references (`checker._ContentSafetyParser` — do not weaken). All new layout output is pre-generated CSS classes or (slope only) SVG geometry attributes.
- **Atomic ten-step gate per component:** each slice lands vocabulary, schema, model, validation, renderer+manifest, CSS+strict digest, `TRUSTED_RENDERERS`, registry entry, checker rules+bad fixtures, and passing build+tests+docs in ONE branch/PR. No partial production entries; rollback removes the whole set together.
- **Strict digests:** every CSS asset digest in `assets/components/registry.json` is the exact `shasum -a 256` of the committed file. Recompute after any CSS edit; never wildcard or trust-on-first-use.
- **Trusted renderers:** only `renderers/__init__.py:TRUSTED_RENDERERS` entries (`"<id>@1"`) may render; registry `renderer` field must equal `"<id>@<version>"` (enforced by `registry._validate_entry`).
- **Checker closed sets:** new checker rule names must be added to `registry.KNOWN_CHECKER_RULES`; new diagnostic codes to `diagnostics.py` constants + `ALL_CODES`. Every new component-specific checker rule gets ≥1 bad fixture fixing its failure.
- **Fixture rules:** naming follows existing conventions — IR: `component-valid-<x>.json` / `component-bad-<x>-<case>.json`; final-document: `component-bad-<x>-<case>.html`; built docs: `<component>-doc.html`. Register every new fixture in `scripts/tests/fixtures.md`.
- **Documentation sync per slice:** `references/patterns.md` (selection guide + canonical IR JSON example), `references/design-system.md` (density caps; slice-specific notes), `SKILL.md` (canonical component list), `scripts/tests/fixtures.md` — updated in the same commit series as the code.
- **Tests:** full `python3 -m pytest tests -q` (run from `skills/visual-explain/scripts/`) green, plus `bash check.sh --selftest` green (legacy path unchanged), plus `bash check.sh <built-doc>` PASS, before any slice is declared done.
- **Light/dark inspection:** each slice commits its built document fixture(s) (`scripts/tests/<component>-doc.html`; components with two presentation variants — chevron, waterfall — commit one built document per variant) — self-contained HTML whose skeleton handles both themes — and the PR body names them as the human visual-inspection artifacts (open and toggle OS/browser light & dark).
- **Human gates:** no `git push`, no remote PR creation, no merge, and no destructive cleanup without the specific human approval for that action. Each slice ends with **local** verification and locally generated PR-body/draft material only, then STOPS; pushing the branch and creating the remote draft PR happen only after an explicit approval, and merging is a second, separate human gate. Task N+1 starts only from the then-current `canonical-v2` after Task N's human-approved merge.
- **Numeric rules (waterfall/slope):** JSON parsed with `parse_float=decimal.Decimal` (Task 5; `parse_int` untouched). Numeric fields accept `int | Decimal` only — `bool` and binary `float` rejected. Waterfall requires `displayPrecision > 0` and accepts only `abs(start.value + Σdelta − end.value) <= displayPrecision/2` in exact Decimal arithmetic. Geometry quantized via `Decimal.quantize(Decimal("1"), rounding=ROUND_HALF_UP)`. No clamping — out-of-domain computed geometry is `renderer_failure`.
- **renderer-svg:** SVG appears in the content slot only inside canonical sections of `RENDERER_SVG_ALLOWLIST = frozenset({"slope@1"})`, declared via `RenderManifest.svg_root_ids`, one `<svg>` per section with `id="<instance>-svg"`, exact per-element attribute allowlist, namespace-anything rejected, `viewBox` exact-match `0 0 600 220`, `preserveAspectRatio` only `xMidYMid meet`, `text-anchor` only `start|middle|end`, scalar coordinates `^-?[0-9]+$` (radius `r`: `^[0-9]+$`).
- **Lengths:** all character caps counted in Unicode code points (Python `len()`).
- **Existing matrix/flow contracts unchanged**, with one sanctioned strictness-preserving exception: flow `edge.relation` becomes scoped to flow's own capabilities (Task 1) so the v2 enum growth cannot widen it.

## Adopted execution policy — aggregate one PR (2026-07-12)

> This user-approved policy supersedes the per-slice remote-PR/merge waits in **PR Boundaries and Sequential Integration**, every task's `Slice Gate` stop wording, each task's `Baseline: … after Task N merge` wording, and the Post-S6 prerequisite that S6 be remotely merged.

- Keep the six slices serial and atomic, but integrate each locally into the single `canonical-v2` integration branch after its local gate and review have converged. A slice must still complete its ten-step gate, full tests, skeleton-byte check, generated inspection artifacts, docs sync, and different-runtime review before its changes become the baseline for the following slice.
- Do **not** push or open a remote PR for S1–S5, and do not wait for an individual-slice human PR/merge gate. Record each slice's local `PR-BODY-s<N>.md` as cumulative evidence and proceed directly to the next slice from the current integration head.
- The normal three-round maximum, fail-closed gate behavior, reviewer independence, and non-convergence reporting remain in force. A non-converged slice requires an explicit human disposition before it may be locally integrated; accepted audit notes must be recorded alongside the run evidence.
- After S6, regenerate every inspection artifact, run the full integrated test/check evidence, and perform the cumulative cross-component review plus its bounded remediation loop on the integrated `canonical-v2` branch.
- Only after that cumulative review is clean (or its residual risk has an explicit human disposition) prepare **one** combined PR body and decision material for `canonical-v2` into its parent branch. `git push`, remote draft-PR creation, remote merge, and destructive cleanup remain separate, explicit human gates.

## File Structure (whole project)

New files by the end of Task 6 (all under `skills/visual-explain/`):

- `scripts/ve_components/renderers/{enumeration,chevron,pyramid,stairs,logic_tree,waterfall,slope,evidence_map}.py` — one trusted renderer per component (module name uses underscore; component ID uses hyphen).
- `assets/components/{enumeration,chevron,pyramid,stairs,logic-tree,waterfall,slope,evidence-map}.css` — namespaced (`[data-ve-component="<id>"]` root), tokens only.
- `scripts/tests/test_<component>_renderer.py` (8 files) and `scripts/tests/test_v2_core.py` (Task 1 generalization tests).
- Fixtures per component (valid JSON, bad JSON per rejection rule, bad HTML per checker rule, built `<component>-doc.html`).

Repeatedly modified files (every slice): `references/component-vocabulary.json`, `references/component-ir.schema.json`, `scripts/ve_components/{model,validation,diagnostics,registry,checker}.py`, `scripts/ve_components/renderers/__init__.py`, `assets/components/registry.json`, `references/patterns.md`, `references/design-system.md`, `SKILL.md`, `scripts/tests/fixtures.md`. Task 5 additionally modifies `scripts/build_explainer.py`; Task 6 additionally modifies `scripts/ve_components/{model,assembly}.py` (manifest SVG fields/checks). `references/assembly.schema.json` is **never** modified (spec audit finding 4).

Naming conventions produced by Task 1 and consumed by every later task:

- payload dataclass `<Component>Payload` + item dataclasses in `model.py`; `CanonicalIR` optional field named exactly like the payload JSON key (Python attribute uses underscore: `logic_tree`, `evidence_map`).
- validator `_validate_<component>(raw, path, col) -> <Component>Payload | None` registered in `validation._PAYLOAD_VALIDATORS: dict[str, ...]` keyed by component ID.
- renderer `render_<component>(section, definition) -> RenderResult`; DOM contract: `figure[data-ve-component="<id>"][role="group"][aria-label][aria-describedby]` root, `figcaption.ve-<id>-caption` (`id="<instance>-caption"`), `p.ve-<id>-summary` (`id="<instance>-summary"`), `ul.ve-<id>-notes` (all certainty/sources as `li[data-ve-semantic-id]`), every payload item carries `data-ve-semantic-id`; `generated_relationship_ids=()`; never emits `data-ve-from/to/relation` or `data-ve-row-id/column-id`; all text through `html.escape`.
- diagnostic code `<component_snake>_structure_violation`; checker rule `<id>-structure` (Task 5 adds `waterfall-consistency` + `waterfall_arithmetic_mismatch`; Task 6 adds `renderer-svg`/`renderer_svg_violation` and `evidence-map-references`).

## Test Commands (identical every slice)

```bash
cd ~/workspace/visual-explain/skills/visual-explain/scripts
python3 -m pytest tests -q                        # expect: all passed
bash check.sh --selftest                          # expect: "selftest: N passed, 0 failed" — 0 failed, and N unchanged by your slice (v2 adds no legacy selftest cases)
python3 build_explainer.py --assembly tests/component-valid-<x>.json --output tests/<x>-doc.html   # expect: "OK: …"
bash check.sh tests/<x>-doc.html                  # expect: PASS
shasum -a 256 ../assets/components/<x>.css        # paste into registry.json digest
```

## PR Boundaries and Sequential Integration

- One slice = one local branch = (after approval) one **draft PR** into `canonical-v2`: branches `canonical-v2-s1-enumeration`, `-s2-chevron`, `-s3-pyramid-stairs`, `-s4-logic-tree`, `-s5-waterfall`, `-s6-slope-evidence-map`.
- Hard dependency chain: Task N+1 **must** branch from `canonical-v2` only after the human has reviewed and merged Task N's PR. Never stack branches; never start Task N+1 from Task N's branch.
- **Slice Gate (mandatory end-of-slice procedure — every task's final step references this):**
  1. **Local verification & draft material (no remote actions):** re-run the full Test Commands block locally; confirm `git diff canonical-v2 -- '**/skeleton.html'` is empty; write the PR body to a local file `PR-BODY-s<N>.md` on the branch (contents: ten-step gate checklist checked off, test output summary, built inspection HTML path(s), docs files touched). Do **not** push. → **STOP: report completion and present the PR body + evidence paths to the human; wait for approval.**
  2. **After the human's explicit approval of THIS slice:** `git push -u origin <branch>` and create the **draft** PR into `canonical-v2` using the prepared body. Remote PR creation is never automatic — it happens only inside this approved step.
  3. → **STOP again: merging is a separate human gate.** Do not merge, mark ready-for-review, or start Task N+1 until the human has merged the PR into `canonical-v2`.
- Each PR body lists: gate steps 1–10 checked off, test output summary, the built `<component>-doc.html` path(s) for light/dark inspection, and the docs files touched.
- Commit style: small TDD commits (`test: …` failing test → `feat: …` make green → `docs: …` sync), matching each task's steps.

---

### Task 1: S1 — Cross-cutting generalization + enumeration (G1/G2)

Spec sections: 「横断基盤の一般化」, 「コンポーネント別契約 1. enumeration」, 「レイアウト出力の制約」, 「四層検査への追加」.

**Files:**
- Inspect first (ground truth): `scripts/ve_components/validation.py` (`_validate_canonical_ir`, `_validate_annotations`, `_validate_flow` line ~513 relation check), `scripts/ve_components/model.py` (`CanonicalIR.semantic_ids`, `RenderManifest`), `scripts/ve_components/checker.py` (`validate_artifact_semantics`, `_ContentSafetyParser`), `scripts/ve_components/assembly.py` (`render_canonical`), `scripts/ve_components/registry.py` (`KNOWN_CHECKER_RULES`), `scripts/ve_components/renderers/{matrix,flow}.py` (DOM/manifest pattern to copy), `references/component-ir.schema.json`, `references/component-vocabulary.json`.
- Create: `scripts/ve_components/renderers/enumeration.py`, `assets/components/enumeration.css`, `scripts/tests/test_v2_core.py`, `scripts/tests/test_enumeration_renderer.py`, fixtures `scripts/tests/component-valid-enumeration.json` (list/number variant), `scripts/tests/component-valid-enumeration-columns.json` (columns/label variant), `scripts/tests/component-bad-enumeration-{gap-description,label-missing,too-many,empty-block}.json`, `scripts/tests/component-bad-enumeration-structure.html`, built `scripts/tests/enumeration-doc.html`.
- Modify: `references/component-vocabulary.json`, `references/component-ir.schema.json`, `scripts/ve_components/{model,validation,diagnostics,registry,checker}.py`, `scripts/ve_components/renderers/__init__.py`, `assets/components/registry.json`, `references/{patterns,design-system}.md`, `SKILL.md`, `scripts/tests/fixtures.md`.

**Interfaces:**
- Consumes: existing `RendererFn` signature `(CanonicalSection, ComponentDefinition) -> RenderResult`; existing `DiagnosticCollector`; existing matrix/flow renderer DOM pattern.
- Produces (relied on by Tasks 2–6): `validation._PAYLOAD_VALIDATORS` dispatch dict (component ID → validator); `validation.ANNOTATION_TARGETS` per-payload target-ID extractor (component ID → function returning the set of annotatable IDs); generalized `CanonicalIR.semantic_ids()`; checker `COMPONENT_ARTIFACT_CHECKS` dispatch (component ID → DOM-structure check over a canonical section body) and generalized `ve-<id>-notes` requirement; artifact rule "sections whose `data-ve-component` is neither `flow` nor `matrix` must not contain `data-ve-from/to/relation` or `data-ve-row-id/column-id`"; the naming conventions in File Structure above.

**Steps:**

- [ ] **Step 1 — failing core tests.** In `scripts/tests/test_v2_core.py` write tests (they fail against current code): (a) `test_flow_edge_relation_scoped` — a valid flow IR whose edge `relation` is `"two-axis-classification"` is rejected with `invalid_flow_edge`; (b) `test_payload_dispatch_rejects_multi_payload` — an IR containing both `matrix` and `enumeration` keys → `invalid_component_payload`; (c) `test_payload_selection_mismatch` — `enumeration` payload with `selection.component: "matrix"` → `invalid_component_payload`; (d) `test_semantic_ids_include_enumeration_items`; (e) `test_annotation_targets_enumeration` — `takeawayTargetIds` referencing an item ID accepted, unknown ID rejected. Run `python3 -m pytest tests/test_v2_core.py -q`; expected: FAIL/ERROR (vocabulary/validators absent).
- [ ] **Step 2 — vocabulary + schema.** Add to `component-vocabulary.json`: `"enumeration": {"contractVersion": 1, "relationshipKind": "parallel-enumeration", "capabilities": ["parallel-itemization"]}`. In `component-ir.schema.json`: extend `componentId`/`relationshipKind`/`capability` enums; add `$defs/enumerationPayload` (items 2–6 of `{id, label?, title?, description?[]}` plus `presentation`, `blockContent`); add top-level `enumeration` property; extend `oneOf` to 3 mutually-exclusive branches; add `$defs/flowRelation` = `["ordered-transition","directed-transition","branching"]` and point `flowEdge.relation` at it. Run existing drift tests: `python3 -m pytest tests/test_component_contract.py -q`; expected: PASS (they compare enums to vocabulary).
- [ ] **Step 3 — model + validation generalization.** In `model.py`: add `EnumerationItem`/`EnumerationPayload` frozen dataclasses; add `enumeration` field to `CanonicalIR`; generalize `payload_kind` and `semantic_ids()` (items' `id`s included). In `validation.py`: introduce `_PAYLOAD_VALIDATORS` and `ANNOTATION_TARGETS`; rewrite the payload-exclusivity/dispatch block of `_validate_canonical_ir` per spec (exactly one payload key; key must equal `selection.component`); scope flow `edge.relation` to `flowRelation`; implement `_validate_enumeration` enforcing spec limits: items 2–6 (columns 2–4); label ≤16 required + title forbidden in `blockContent:"label"`; title ≤30 optional in `"number"`; **minimum visible content** (number mode: each item has title or description); description all-or-none, list 1–3 lines ≤60 chars, columns 1–4 lines ≤40 chars; violations → new code `enumeration_structure_violation` (add constant + `ALL_CODES` entry in `diagnostics.py`). Run Step 1 tests; expected: PASS. Commit.
- [ ] **Step 4 — failing renderer tests.** In `test_enumeration_renderer.py`: assert figure root/caption/summary/notes DOM contract (`ve-enumeration-notes`), one block per item with `data-ve-semantic-id`, renderer numbering 1..n in number mode (numbers NOT in IR), centered-list class on `presentation:"list"`, columns wrapper on `"columns"`, `generated_relationship_ids == ()`, `script_asset_ids == ()`, manifest `consumed_semantic_ids == ir.semantic_ids()`, no `data-ve-from`/`data-ve-row-id` anywhere. Run; expected: FAIL (module missing).
- [ ] **Step 5 — renderer + CSS + trust chain.** Implement `renderers/enumeration.py` following `renderers/matrix.py` structure. Write `assets/components/enumeration.css` (root `[data-ve-component="enumeration"]`; tokens only: block face `--text-dim`, text `--bg`, list centered via `width: fit-content; margin-inline: auto`; columns stack on narrow screens preserving order; no new colors/fonts/animation). Compute `shasum -a 256 ../assets/components/enumeration.css`; add registry entry (id/version 1/kind/capabilities/requiredInputs `["caption","accessibility","items"]`/checkerRules `["static-content","semantic-ids","escaping","no-external-reference","responsive-order","enumeration-structure"]`/renderer `"enumeration@1"`/assets with exact digest); add `"enumeration@1": render_enumeration` to `TRUSTED_RENDERERS`; add `"enumeration-structure"` to `KNOWN_CHECKER_RULES`. Run Step 4 tests; expected: PASS. Commit.
- [ ] **Step 6 — checker generalization + bad fixtures.** In `checker.py`: generalize the notes check in `validate_artifact_semantics` to require `ve-<component>-notes` per section's `data-ve-component` (closed set from vocabulary); add the non-flow/matrix `data-ve-from/…` prohibition; add `COMPONENT_ARTIFACT_CHECKS` dispatch with the enumeration entry (item count 2–6, blocks carry semantic IDs, notes present). Write `component-bad-enumeration-structure.html` (an otherwise-valid final document whose enumeration section has 1 item) and bad-JSON fixtures listed in Files; add checker tests to `test_v2_core.py`/`test_component_checker.py` asserting each fixture's diagnostic code. Run `python3 -m pytest tests -q`; expected: PASS (including untouched matrix/flow suites — proves generalization is behavior-preserving except the sanctioned edge.relation scope).
- [ ] **Step 7 — build + four-layer verification.** `python3 build_explainer.py --assembly tests/component-valid-enumeration.json --output tests/enumeration-doc.html` → `OK:`; `bash check.sh tests/enumeration-doc.html` → PASS; `bash check.sh --selftest` → 0 failed. Commit `tests/enumeration-doc.html` as the light/dark inspection artifact.
- [ ] **Step 8 — docs sync.** patterns.md: add 「箇条書き種別 → 図」 selection-guide subsection (enumeration vs chevron order test; pyramid misuse warning stub) + full canonical enumeration IR JSON example. design-system.md: density caps line (enumeration 6 / columns 4), the figure-container-only centering exception, and generalize gate step 3 wording per spec (「既存コンポーネントが使わない共通 IR フィールドを追加しない…」). SKILL.md: rename the canonical section to cover the component list and add enumeration. fixtures.md: register all new fixtures. Commit.
- [ ] **Step 9 — gate audit + Slice Gate.** Walk the ten-step gate list against the diff (all ten satisfied in this one branch). Then execute the **Slice Gate** procedure (see PR Boundaries): local verification + `PR-BODY-s1.md` only, **STOP for approval**; push + create draft PR `canonical-v2-s1-enumeration` → `canonical-v2` only after explicit approval; **STOP again before merge.**

### Task 2: S2 — chevron (F1/F2)

Spec section: 「コンポーネント別契約 4. chevron」. Baseline: fresh `canonical-v2` after Task 1 merge; the dispatch/notes/annotation machinery from Task 1 exists — this slice only **adds entries**, it must not re-modify Task 1's generalized logic.

**Files:**
- Inspect: Task 1's enumeration renderer/validator/fixtures as the template; `renderers/flow.py` for the visually-hidden sentence pattern (`visually-hidden` list) to copy for the loop.
- Create: `scripts/ve_components/renderers/chevron.py`, `assets/components/chevron.css`, `scripts/tests/test_chevron_renderer.py`, fixtures (deterministic contents fixed here): `component-valid-chevron.json` — vertical / `blockContent:"number"` / `loop:false`, 4 steps with titles 「受付」「検証」「実行」「報告」 and 2-line descriptions each; `component-valid-chevron-loop.json` — vertical / `blockContent:"label"` / `loop:true`, capabilities `["linear-sequence","closed-loop"]`, 3 steps labeled 「計測」「評価」「改善」; `component-valid-chevron-horizontal.json` — horizontal / `blockContent:"number"`, 4 steps, no titles (forbidden), each with a 1-line ≤30-char description; `component-bad-chevron-{loop-horizontal,loop-capability-mismatch,title-in-horizontal,no-visible-content,too-few-horizontal}.json`, `component-bad-chevron-structure.html`, built `chevron-doc.html` (vertical+loop) and `chevron-horizontal-doc.html`.
- Modify: vocabulary (+`chevron`, kind `ordered-sequence`, capabilities `["linear-sequence","closed-loop"]`), IR schema (payload `$defs/chevronPayload`, oneOf → 4), `model.py` (+`ChevronStep`/`ChevronPayload`, `CanonicalIR.chevron`, `semantic_ids`), `validation.py` (register `_validate_chevron` + annotation targets = step IDs), `diagnostics.py` (+`chevron_structure_violation`), `registry.py` (`KNOWN_CHECKER_RULES` +`chevron-structure`), `checker.py` (`COMPONENT_ARTIFACT_CHECKS` chevron entry), `renderers/__init__.py` (+`"chevron@1"`), `assets/components/registry.json`, four docs files.

**Interfaces:**
- Consumes: `_PAYLOAD_VALIDATORS` / `ANNOTATION_TARGETS` / `COMPONENT_ARTIFACT_CHECKS` registration points; enumeration's blockContent rules (chevron reuses them verbatim).
- Produces: nothing new structurally; the loop-rail CSS technique (left rail + arrowhead, renderer-owned, no `data-ve-from/to`).

**Steps:**

- [ ] **Step 1 — failing validation tests** in `test_chevron_renderer.py`: steps 2–6 accepted; `loop:true` + `orientation:"horizontal"` rejected; `loop:true` without `closed-loop` capability (and inverse) → `chevron_structure_violation`; horizontal with `title` rejected; horizontal number-mode without descriptions rejected (minimum-visible-content: title forbidden ⇒ description required on all steps); vertical description 1–3 lines ≤40 chars, horizontal 1–2 lines ≤30 chars boundaries (40-char line accepted, 41 rejected). Run; expect FAIL.
- [ ] **Step 2 — vocabulary/schema/model/validation** per Files list, enforcing every rule from the spec's chevron contract (declaration order = execution order; all-or-none descriptions; `linear-sequence` always required). Run Step 1 tests; expect PASS. Commit.
- [ ] **Step 3 — failing renderer tests:** DOM contract (`ve-chevron-notes` etc.); vertical variant centered; `loop:true` renders exactly one renderer-owned return rail element with **no** `data-ve-from/to` and adds a visually-hidden sentence naming last→first step labels; horizontal variant has no loop rail; manifest invariants as Task 1. Run; expect FAIL.
- [ ] **Step 4 — renderer + CSS + trust chain** (clip-path chevron shapes owned by `chevron.css`; horizontal wraps to vertical stacking on narrow screens). `shasum -a 256`, registry entry, `TRUSTED_RENDERERS`, `KNOWN_CHECKER_RULES`. Run; expect PASS. Commit.
- [ ] **Step 5 — checker entry + bad fixtures + full suite.** chevron artifact check (2–6 steps; loop rail only in vertical sections). All fixtures asserted by code. `python3 -m pytest tests -q` and `bash check.sh --selftest` green.
- [ ] **Step 6 — build BOTH variants and commit both as light/dark evidence:**
  ```bash
  python3 build_explainer.py --assembly tests/component-valid-chevron-loop.json --output tests/chevron-doc.html            # expect: OK
  python3 build_explainer.py --assembly tests/component-valid-chevron-horizontal.json --output tests/chevron-horizontal-doc.html   # expect: OK
  bash check.sh tests/chevron-doc.html              # expect: PASS
  bash check.sh tests/chevron-horizontal-doc.html   # expect: PASS
  git add tests/chevron-doc.html tests/chevron-horizontal-doc.html && git commit -m "test: add chevron light/dark inspection documents (vertical+loop, horizontal)"
  ```
  Both HTMLs are named in the PR body as the light/dark inspection artifacts (vertical/loop rail and horizontal arrow variants must each be visually verified).
- [ ] **Step 7 — docs sync** (patterns.md: chevron IR example + the kind-based flow/chevron routing rule 「分岐・合流は directed-graph=flow、線形は ordered-sequence=chevron」; design-system.md: chevron 6-step cap; SKILL.md list; fixtures.md). Gate audit, then **Slice Gate** (see PR Boundaries): local verification + `PR-BODY-s2.md`, **STOP for approval**; push + draft PR `canonical-v2-s2-chevron` only after approval; **STOP again before merge.**

### Task 3: S3 — pyramid + stairs (G5/F3)

Spec sections: 「3. pyramid」「5. stairs」. Baseline: `canonical-v2` after Task 2 merge. Two components, one atomic slice: both must complete the full gate; do not land one without the other.

**Files:**
- Create: `renderers/pyramid.py`, `renderers/stairs.py`, `assets/components/pyramid.css`, `assets/components/stairs.css`, `scripts/tests/test_pyramid_renderer.py`, `scripts/tests/test_stairs_renderer.py`, fixtures `component-valid-pyramid.json`, `component-bad-pyramid-{too-few,too-many,label-long}.json`, `component-valid-stairs.json` (with one `current:true` stage carrying `note`), `component-bad-stairs-{two-current,current-without-note,too-many}.json`, `component-bad-pyramid-structure.html`, `component-bad-stairs-structure.html`, built `pyramid-doc.html`, `stairs-doc.html`.
- Modify: the standard nine files (vocabulary ×2 entries: `pyramid`/`layered-priority`/`["priority-layering"]`, `stairs`/`staged-maturity`/`["maturity-staging"]`; schema payloads `$defs/pyramidPayload`+`$defs/stairsPayload`, oneOf → 6; model `PyramidTier/PyramidPayload/Stage/StairsPayload`; validators; diagnostics +`pyramid_structure_violation`+`stairs_structure_violation`; `KNOWN_CHECKER_RULES` +`pyramid-structure`+`stairs-structure`; checker dispatch ×2; `TRUSTED_RENDERERS` +`"pyramid@1"`+`"stairs@1"`; registry ×2 entries with digests; docs).

**Interfaces:**
- Consumes: Task 1 registration points.
- Produces: the count×index CSS class technique (`ve-pyramid-count-{3,4}`, `ve-stairs-count-{3..5}` container classes + per-index item classes) — fully enumerated static layout, reused nowhere else but proving the pattern.

**Steps:**

- [ ] **Step 1 — failing validation tests:** pyramid tiers 3–4 top-first (first tier = apex), label ≤12 / sub ≤30; stairs stages 3–5 low→high, label ≤14 / note ≤20, `current:true` max 1 and **requires `note`** (fixture `current-without-note` → `stairs_structure_violation`). Run; expect FAIL.
- [ ] **Step 2 — vocabulary/schema/model/validation ×2.** Tests PASS. Commit.
- [ ] **Step 3 — failing renderer tests:** pyramid apex tier only uses `--border-strong` face, others `--text-dim` (assert class names, not colors); widths via count×index classes, **no inline style attributes anywhere** (`style=` absent from markup); stairs `current` tread only gets accent class and its note text rendered visibly; **no emphasis on the last stage**; both meet the common DOM contract (`ve-pyramid-notes` / `ve-stairs-notes`, `generated_relationship_ids=()`).
- [ ] **Step 4 — renderers + CSS ×2 + digests + registry + trust list + checker entries + bad HTML fixtures.** Full suite green.
- [ ] **Step 5 — build both docs + check.sh PASS**; commit both HTMLs as light/dark evidence.
- [ ] **Step 6 — docs sync** (patterns.md selection guide: 「単なる並列3項目は enumeration、優先構造だけ pyramid」「留まる状態は stairs、流れる工程は chevron」+ two IR examples; design-system.md caps: pyramid 4 tiers, stairs 5 stages; SKILL.md; fixtures.md). Gate audit (both components fully gated), then **Slice Gate** (see PR Boundaries): local verification + `PR-BODY-s3.md`, **STOP for approval**; push + draft PR `canonical-v2-s3-pyramid-stairs` only after approval; **STOP again before merge.**

### Task 4: S4 — logic-tree (G3)

Spec section: 「2. logic-tree」. Baseline: `canonical-v2` after Task 3 merge. First renderer-owned connector lines (grid + border-based, independent of flow's connector assets).

**Files:**
- Create: `renderers/logic_tree.py`, `assets/components/logic-tree.css`, `scripts/tests/test_logic_tree_renderer.py`, fixtures `component-valid-logic-tree.json` (root + 3 branches, mixed 0–2 leaves), `component-bad-logic-tree-{too-few-branches,too-many-branches,three-leaves,label-long,depth}.json`, `component-bad-logic-tree-structure.html`, built `logic-tree-doc.html`.
- Modify: standard nine files (vocabulary `logic-tree`/`hierarchical-decomposition`/`["mece-decomposition"]`; schema `$defs/logicTreePayload` with `root{id,label}` + `branches[]` 2–4 of `{id,label,leaves?[]}`, leaf `{id,text}` 0–2 per branch, oneOf → 7; model `LogicTreeLeaf/LogicTreeBranch/LogicTreePayload` — note Python attribute `logic_tree`, JSON key `"logic-tree"`; validator: depth fixed at root→branch→leaf, root ≤20 / branch ≤16 / leaf text ≤40; diagnostics +`logic_tree_structure_violation`; rule `logic-tree-structure`; renderer `"logic-tree@1"`; registry; docs).

**Interfaces:**
- Consumes: Task 1 registration points.
- Produces: renderer-owned connector technique (CSS borders on a grid — no SVG, no `data-connect`, no `data-ve-from/to`), cited by spec as flow-independent.

**Steps:**

- [ ] **Step 1 — failing validation tests** for every bad fixture above (schema depth violation = a leaf carrying its own `leaves` → unknown-field rejection; assert `logic_tree_structure_violation` or `invalid_component_payload` as designed in the validator). Run; expect FAIL.
- [ ] **Step 2 — vocabulary/schema/model/validation.** Semantic IDs/annotation targets = root ∪ branches ∪ leaves. Tests PASS. Commit.
- [ ] **Step 3 — failing renderer tests:** root left / branches right layout classes; connector elements are presentation-only (no data attributes); narrow-screen vertical stacking preserves reading order (root before branches in DOM); common DOM contract (`ve-logic-tree-notes`).
- [ ] **Step 4 — renderer + CSS + digest + registry + trust + checker entry + bad HTML fixture.** Full suite + selftest green.
- [ ] **Step 5 — build `logic-tree-doc.html` + check.sh PASS**; commit as light/dark evidence.
- [ ] **Step 6 — docs sync** (patterns.md: 「構成の分解は logic-tree、読者がたどる判断分岐は decision-tree（バックログ）— 誤用は選択ガイドで防ぐ」+ MECE-not-machine-checkable note + IR example; design-system.md: 枝 4・leaf 各 2 cap; SKILL.md; fixtures.md). Gate audit, then **Slice Gate** (see PR Boundaries): local verification + `PR-BODY-s4.md`, **STOP for approval**; push + draft PR `canonical-v2-s4-logic-tree` only after approval; **STOP again before merge.**

### Task 5: S5 — waterfall (B1) + Decimal parsing

Spec sections: 「6. waterfall」「数値の取り扱い」「レイアウト出力の制約」. Baseline: `canonical-v2` after Task 4 merge. New verification category: build-entry Decimal parsing + acceptance-time arithmetic consistency + quantized class layout.

**Files:**
- Inspect: `scripts/build_explainer.py:main` (the single `json.loads` call site), `renderers/flow.py` rail classes (`ve-rail-{s}-{e}`) as the pre-generated-class precedent.
- Create: `renderers/waterfall.py`, `assets/components/waterfall.css` (with pre-generated `ve-wf-start-0…100` / `ve-wf-len-0…100`, 202 rules, orientation container classes `ve-wf-bars`/`ve-wf-columns`), `scripts/tests/test_waterfall_renderer.py`, fixtures (deterministic contents fixed here): `component-valid-waterfall.json` — `orientation:"bars"`, `displayPrecision: 1`, start `{value: 30, valueText: "30件"}`, steps `[{delta: -50, tone: "warning", valueText: "−50件"}, {delta: 45, tone: "positive", valueText: "+45件"}]`, end `{value: 25, valueText: "25件"}` (exercises negative cumulative −20 and a zero crossing); `component-valid-waterfall-columns.json` — `orientation:"columns"`, `displayPrecision: 1`, start `{value: 100, valueText: "100件"}`, five steps `+10/−20/+5/−30/+15`（tones positive/warning/positive/warning/positive）, end `{value: 80, valueText: "80件"}`; `component-bad-waterfall-{arithmetic,no-precision,float-value,zero-range,too-many-bars,missing-tone}.json`, `component-bad-waterfall-structure.html`, built `waterfall-doc.html` (bars) and `waterfall-columns-doc.html`.
- Modify: standard nine files (vocabulary `waterfall`/`additive-bridge`/`["additive-bridging"]`; schema `$defs/waterfallPayload` — `displayPrecision` required, `start/steps/end` shapes, `tone` enum `positive|warning|neutral`, oneOf → 8; model `WaterfallStep/WaterfallPayload`; validator; diagnostics +`waterfall_structure_violation`+`waterfall_arithmetic_mismatch`; rules +`waterfall-consistency`; renderer `"waterfall@1"`; registry; docs) **plus** `scripts/build_explainer.py` (add `parse_float=decimal.Decimal` to `json.loads`; leave `parse_int` untouched so `_is_int` version checks keep passing).

**Interfaces:**
- Consumes: Task 1 registration points; flow's class-driven layout precedent.
- Produces: numeric-domain helpers reused by Task 6 — put `quantize_percent(value, lo, hi) -> int` (ROUND_HALF_UP; exact 0/100 at endpoints) and the `int|Decimal`-only type guard in a new module `scripts/ve_components/numeric.py` so slope imports the identical rounding.

**Steps:**

- [ ] **Step 1 — failing numeric/validation tests** in `test_waterfall_renderer.py`: acceptance at error exactly `displayPrecision/2` and rejection just above (`Decimal("0.5")` vs `Decimal("0.500001")` with precision 1); missing `displayPrecision` rejected; `float` value instance rejected (`waterfall_structure_violation`); `bool` rejected; zero-range (all cumulative values 0) rejected; `delta: 0` step accepted; bars 1–4 steps / columns 1–7 steps caps; per-step `tone` required; `valueText` required, non-empty, ≤16, never cross-checked against `value` (fixture where valueText contradicts value still ACCEPTED — opacity is contractual). Plus `test_build_parses_floats_as_decimal`: run `build_explainer.build_to_path`-level test or direct `json.loads(..., parse_float=Decimal)` assertion through the CLI path with a fixture containing `0.1`. Run; expect FAIL.
- [ ] **Step 2 — numeric.py + vocabulary/schema/model/validation + build_explainer change.** Domain per spec: cumulative series `c_0=start.value, c_i=c_{i-1}+delta_i`, `end.value`, **plus baseline 0 always**; `range = max−min`; percent = `(v−min)/range×100` quantized. Tests PASS. Commit.
- [ ] **Step 3 — failing renderer tests:** every bar carries exactly one `ve-wf-start-<p>` and one `ve-wf-len-<p>` class with `0 ≤ p ≤ 100`; endpoints map min→0/max→100 exactly; `style=` attribute absent from all markup; `valueText` visibly rendered for start/every step/end; tone classes only on steps (start/end monochrome); dashed connector elements present between consecutive bars; columns orientation renders inside a horizontal-scroll container and never auto-degrades to bars; out-of-range percent (forced via monkeypatched quantizer) → `renderer_failure` not clamping.
- [ ] **Step 4 — renderer + waterfall.css (202 pre-generated rules) + digest + registry + trust + checker entries** (`waterfall-consistency` final-document check: section shows valueTexts and bar classes within range) **+ bad HTML fixture.** Full suite + selftest green. Commit.
- [ ] **Step 5 — build BOTH orientation docs and commit both as light/dark evidence:**
  ```bash
  python3 build_explainer.py --assembly tests/component-valid-waterfall.json --output tests/waterfall-doc.html                    # expect: OK (bars; negative cumulative + zero-cross — the hardest visual)
  python3 build_explainer.py --assembly tests/component-valid-waterfall-columns.json --output tests/waterfall-columns-doc.html   # expect: OK (columns; 5 steps in a horizontal-scroll container)
  bash check.sh tests/waterfall-doc.html            # expect: PASS
  bash check.sh tests/waterfall-columns-doc.html    # expect: PASS
  git add tests/waterfall-doc.html tests/waterfall-columns-doc.html && git commit -m "test: add waterfall light/dark inspection documents (bars, columns)"
  ```
  Both HTMLs are named in the PR body as the light/dark inspection artifacts (bars row layout and columns bridge must each be visually verified).
- [ ] **Step 6 — docs sync** (patterns.md: waterfall IR example + 「columns は狭い画面で bars を推奨」 guidance; design-system.md: caps 行型6行/横並び9列 + geometry-is-auxiliary/valueText-is-primary note; SKILL.md; fixtures.md). Gate audit, then **Slice Gate** (see PR Boundaries): local verification + `PR-BODY-s5.md`, **STOP for approval**; push + draft PR `canonical-v2-s5-waterfall` only after approval; **STOP again before merge.**

### Task 6: S6 — slope (B3) + evidence-map (E1) + renderer-svg gate

Spec sections: 「7. slope」「8. evidence-map」「renderer-svg ゲート」「数値の取り扱い」. Baseline: `canonical-v2` after Task 5 merge. Largest checker change — keep the three SVG gate pieces (allowlist, manifest, feature rejection) in one atomic slice.

**Files:**
- Inspect: `model.py:RenderManifest`, `assembly.py:render_canonical` (where manifest cross-checks live), `checker.py:validate_artifact_semantics` + `_ContentSafetyParser`, `scripts/ve_components/numeric.py` (Task 5), `final_checks.py:check_manifest_to_dom`.
- Create: `renderers/slope.py`, `renderers/evidence_map.py`, `assets/components/slope.css`, `assets/components/evidence-map.css`, `scripts/tests/test_slope_renderer.py`, `scripts/tests/test_evidence_map_renderer.py`, `scripts/tests/test_renderer_svg_gate.py`, fixtures: `component-valid-slope.json` (increase+decrease+flat items), `component-bad-slope-{no-unit,three-points-shape,float-value,too-many-items}.json`, `component-valid-evidence-map.json`, `component-bad-evidence-map-{unresolved-certainty,unresolved-source,too-many-evidence,nested}.json`; bad SVG HTML fixtures (one per category, spec 「renderer-svg ゲート」 item 5): `component-bad-svg-{foreign-section,rect-element,transform-attr,xlink-attr,xmlns-decl,noninteger-coord,nested-svg,foreignobject}.html` + boundary-valid `component-valid-svg-boundary.html` (coordinates exactly 0/600/220); final-document structural fixtures `component-bad-slope-structure.html` (see Step 3a) and `component-bad-evidence-map-references.html` (see Step 3b) plus `component-bad-evidence-map-structure.html` (evidence count 5 > cap 4 → `evidence_map_structure_violation`); built `slope-doc.html`, `evidence-map-doc.html`.
- Modify: standard nine files ×2 components (vocabulary `slope`/`two-point-change`/`["two-point-comparison"]`, `evidence-map`/`claim-support`/`["claim-support-mapping"]`; schema `$defs/slopePayload` — `axes{fromLabel,toLabel}` ≤8 each, **required `unit`** non-empty ≤8, items 1–5 with tone; `$defs/evidenceMapPayload` — `conclusion{id,label≤30}` + `evidence[]` 2–4 of `{id,label≤40,certaintyRef,sourceRef?}`; oneOf → 10 final; model `SlopeItem/SlopePayload/EvidenceItem/EvidenceMapPayload` **+ `RenderManifest.svg_root_ids: tuple[str, ...] = ()`**; validators — evidence `certaintyRef` must resolve into `certainty[]` ids, `sourceRef` into `sources[]` ids, else `evidence_map_structure_violation`; diagnostics +`slope_structure_violation`+`evidence_map_structure_violation`+`renderer_svg_violation`; rules +`slope-structure`+`renderer-svg`+`evidence-map-references`; renderers `"slope@1"`/`"evidence-map@1"`; registry ×2; docs) **plus** `assembly.py` (`render_canonical`: SVG roots in markup must equal `manifest.svg_root_ids`; non-empty `svg_root_ids` requires `component.key in RENDERER_SVG_ALLOWLIST`; undeclared SVG output → `renderer_failure`) **plus** `checker.py` (`RENDERER_SVG_ALLOWLIST = frozenset({"slope@1"})`; artifact SVG gate: `<svg>` only inside allowlisted canonical sections — compatibility sections and non-allowlisted canonical sections reject; one svg per section with `id="<instance>-svg"`; no nested svg; element allowlist `{svg,g,line,circle,text,title,desc}`; per-element exact attribute allowlist and value grammars from the spec — `viewBox` exact `0 0 600 220`, `preserveAspectRatio` only `xMidYMid meet`, `text-anchor` only `start|middle|end`, coords `^-?[0-9]+$`, `r` `^[0-9]+$`, any namespaced/colon attribute rejected).

**Interfaces:**
- Consumes: `numeric.quantize_percent`/type guards (Task 5); Task 1 registration points; `_wrapper_attrs`-style section parsing in checker.
- Produces: terminal state — all 10 components registered; `RENDERER_SVG_ALLOWLIST` as the only sanctioned SVG door.

**Steps:**

- [ ] **Step 1 — failing slope geometry tests** (spec 「表現（決定的ジオメトリ）」+「必須テスト」): from-X=120 / to-X=480 fixed; value band Y=20..200; inverted mapping `y(v)=200−round((v−min)/range×180)` with ROUND_HALF_UP; min→Y=200, max→Y=20; increase item ⇒ `y2 < y1`, decrease ⇒ `y2 > y1`; range-0 ⇒ all Y=110; `unit` required and rendered in summary/notes; `valueText` opaque (contradictory text accepted); float instance rejected. Run; expect FAIL.
- [ ] **Step 2 — failing evidence-map tests:** unresolved `certaintyRef`/`sourceRef` rejected; conclusion 1 / evidence 2–4 / single level only; link line-style classes derived from referenced certainty level (`ve-em-link-confirmed|inferred|unverified`); every evidence card shows the monochrome certainty badge text; conclusion card `--border-strong` class; cards carry `data-ve-certainty-ref` (+optional `data-ve-source-ref`) and **no** `data-ve-from/to`. Run; expect FAIL.
- [ ] **Step 3 — failing SVG-gate tests** in `test_renderer_svg_gate.py`: each bad SVG fixture yields `renderer_svg_violation` via `check_final_document`; boundary-valid fixture passes; `render_canonical` rejects a stub renderer emitting `<svg>` without `svg_root_ids` (→ `renderer_failure`) and a stub non-slope component declaring `svg_root_ids` (allowlist). Run; expect FAIL.
- [ ] **Step 3a — failing slope-structure final-document test.** Author `component-bad-slope-structure.html`: an otherwise-valid final document whose slope canonical section **breaks the items 1–5 structural invariant by containing six item `line` elements** (six `line.ve-slope-item[data-ve-semantic-id]` in the SVG — one more than the density cap). Expected diagnostic: exactly one `slope_structure_violation` from the `slope-structure` entry in `COMPONENT_ARTIFACT_CHECKS` (the artifact-only path of `check_final_document`, no manifest). Fixed by checker test `test_renderer_svg_gate.py::test_slope_structure_bad_fixture`, which loads the fixture, runs `check_final_document`, and asserts the code appears. Run; expect FAIL (fixture rejected for the wrong reason or accepted).
- [ ] **Step 3b — failing evidence-map-references final-document test.** Author `component-bad-evidence-map-references.html`: an otherwise-valid final document whose evidence-map section has (i) one evidence card **missing its `data-ve-certainty-ref` attribute entirely** and (ii) another card whose `data-ve-source-ref` points to an id with **no matching `data-ve-semantic-id` note** in the section's `ve-evidence-map-notes`. Expected diagnostics: `evidence_map_structure_violation` (one per broken card) from the `evidence-map-references` artifact check. Fixed by checker test `test_evidence_map_renderer.py::test_evidence_map_references_bad_fixture`. This final-document fixture is **distinct from** the JSON validation fixture `component-bad-evidence-map-unresolved-certainty.json`, which exercises the IR layer (`_validate_evidence_map`), not the DOM layer. Run; expect FAIL.
- [ ] **Step 4 — implement:** model field, both validators, both renderers (slope emits exactly one `<svg id="<instance>-svg" viewBox="0 0 600 220" …>` using only allowlisted elements/attributes, values/labels as `text` at both ends, classes for `--fs-figure` sizing via `slope.css`; evidence-map is pure HTML/CSS), both CSS files + digests, registry ×2, `TRUSTED_RENDERERS` ×2, `KNOWN_CHECKER_RULES` +3, diagnostics +3, assembly + checker gates (including the `slope-structure` and `evidence-map-references` entries in `COMPONENT_ARTIFACT_CHECKS`). Run Steps 1–3b tests; expect PASS. Commit in TDD sequence (validators → renderers → gates).
- [ ] **Step 5 — full verification:** `python3 -m pytest tests -q` all green (including all five earlier components' suites); `bash check.sh --selftest` 0 failed; build `slope-doc.html` + `evidence-map-doc.html`; `bash check.sh` PASS on both; commit both as light/dark evidence.
- [ ] **Step 6 — docs sync:** patterns.md (slope + evidence-map IR examples; 「3点以上は timeline/文章」「根拠の根拠は図を分割」 guidance), design-system.md (caps slope 5 / evidence 4; renderer-svg gate summary — allowlist + manifest + feature-rejection 三点), SKILL.md (final 10-component list), fixtures.md (all SVG fixture categories). Gate audit ×2 components, then **Slice Gate** (see PR Boundaries): local verification + `PR-BODY-s6.md`, **STOP for approval**; push + draft PR `canonical-v2-s6-slope-evidence-map` only after approval; **STOP again before merge.**

---

## Post-S6 Cumulative Review & Remediation Workflow

Run only after Task 6's PR is human-approved and merged.

1. **Integrated diff:** `git diff 74ac58e...canonical-v2` (the full v2 expansion from the canonical-v2 baseline commit `74ac58e`). Also regenerate all `<component>-doc.html` fixtures and re-run the full Test Commands block as the review's evidence base.
2. **Claude fable review:** submit the integrated diff + spec.md for a cumulative cross-component review (drift between slices, contract asymmetries, checker gaps, docs consistency).
3. **If Critical/Important findings exist:** open ONE remediation branch `canonical-v2-remediation-r<N>` from `canonical-v2` — a **bounded, single-branch remediation task**: Cursor performs the implementation, Codex reviews the remediation diff. Scope is exactly the review findings; no new features.
4. **Re-review with Claude fable.** Repeat steps 3–4 until the review is clean **or** the three-round convergence limit is reached (rounds counted per remediation cycle). Never perform cross-branch auto-fix; every remediation lands via its own human-gated PR into `canonical-v2`.
5. **Done condition:** review clean → canonical-v2 expansion is complete; report final state (component list, test counts, fixture inventory) to the human.

## Self-Review Notes (plan vs spec)

- Every spec contract section (1–8), the generalization section, numeric rules, layout-class constraint, renderer-svg gate (incl. R1/R2 adopted refinements: per-element attribute allowlist, viewBox exact form, enumerated `preserveAspectRatio`/`text-anchor`, slope deterministic geometry + direction tests, slope `unit`, minimum-visible-content, vertical-chevron description limits), four-layer additions, docs-sync list, slice order S1–S6, and the post-S6 bounded remediation loop each map to a named task/step above.
- Deliberately excluded (spec backlog / non-goals): per-item slope units, state-machine, all backlog components, skeleton restyling, interactive renderer scripts.
- `assembly.schema.json` intentionally untouched in every task (spec audit finding 4).

---

ADOPTED: PR-C1 — Human gates restored explicitly: new **Slice Gate** procedure (PR Boundaries) — each slice ends with local verification + locally written `PR-BODY-s<N>.md` only, STOP for approval; push + remote **draft** PR creation only after that specific approval; second STOP before merge. All six task-final steps and the Global Constraints human-gate bullet now reference it; no wording implies automatic remote PR creation.
ADOPTED: PR-C2 — Added final-document fixture `component-bad-slope-structure.html` (Task 6 Step 3a): breaks the slope items 1–5 DOM invariant with six `line.ve-slope-item[data-ve-semantic-id]` elements; expected exactly one `slope_structure_violation` from the `slope-structure` artifact check; fixed by `test_renderer_svg_gate.py::test_slope_structure_bad_fixture`.
ADOPTED: PR-I1 — Both chevron variants and both waterfall variants now have deterministic fixture contents (exact steps/labels/values/tones/displayPrecision), separate generated HTML filenames (`chevron-doc.html`/`chevron-horizontal-doc.html`, `waterfall-doc.html`/`waterfall-columns-doc.html`), explicit build + check.sh command blocks with expected output, and git commit evidence steps; PR bodies must name both artifacts per slice. Single combined documents are not used.
ADOPTED: PR-I2 — Added final-document fixture `component-bad-evidence-map-references.html` (Task 6 Step 3b): one evidence card missing `data-ve-certainty-ref` and one card with a dangling `data-ve-source-ref`; expected `evidence_map_structure_violation` per broken card via the `evidence-map-references` artifact check; covered by `test_evidence_map_renderer.py::test_evidence_map_references_bad_fixture`; kept distinct from the IR-layer JSON fixture `component-bad-evidence-map-unresolved-certainty.json`.

STATUS: complete
