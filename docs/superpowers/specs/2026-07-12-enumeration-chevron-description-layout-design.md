# Enumeration / Chevron Description Layout Design

**Date:** 2026-07-12
**Status:** Implemented on `feat/enumeration-chevron-description-layout`; automated verification complete, browser visual QA pending environment availability
**Scope:** Canonical `enumeration@1` and `chevron@1`

## Goal

Separate each item's concept from its explanatory bullets. The concept remains inside the enumeration block or chevron shape; optional explanation is rendered beside or below that shape according to the authored orientation.

## Problem

The current renderers place `description` inside the same dark or clipped element as the number, label, and title. This conflates two roles:

- the concept that identifies an item or step;
- supporting explanation that expands that concept.

The desired visual grammar is:

- vertical layouts: concept on the left, explanation on the right;
- horizontal layouts: concept above, explanation below;
- no explanation: render the concept alone without an empty explanation region.

This applies equally to `enumeration` and `chevron`.

## Chosen Approach

Keep the existing IR fields and component identifiers. Change the validation and rendered DOM/CSS contracts so that `description` is always external to the concept shape.

This approach is chosen because placement is fully determined by `presentation` or `orientation`. Adding an author-controlled placement field would introduce redundant states and invalid combinations. Creating new component versions would add migration and maintenance cost without changing the semantic relationship represented by either component.

## Semantic Contract

### Concept content

Every item or step must have a textual concept independent of its explanation.

- `blockContent: "label"`: `label` remains required and is the concept; `title` remains forbidden.
- `blockContent: "number"`: `title` becomes required and is the concept; the renderer-generated number is a structural identifier, not a substitute for the concept.
- `description` remains optional supporting detail and never satisfies the minimum concept requirement.

Consequences:

- Number-only items are rejected.
- Number-plus-description items without a `title` are rejected.
- Horizontal number-mode chevrons now accept and require `title`.
- Existing description-only horizontal chevron fixtures must be migrated to include titles.

### Description consistency

The existing all-or-none rule remains:

- either every item or step supplies a non-empty `description`;
- or none of them supplies `description`.

Partial explanation sets remain invalid because they create unbalanced rows or columns and make omission indistinguishable from missing content.

Existing line-count and character-count limits remain unchanged:

- enumeration list: 1–3 lines, 60 characters per line;
- enumeration columns: 1–4 lines, 40 characters per line;
- chevron vertical: 1–3 lines, 40 characters per line;
- chevron horizontal: 1–2 lines, 30 characters per line.

## Layout Contract

| Component | Authored layout | Concept placement | Description placement |
| --- | --- | --- | --- |
| enumeration | `presentation: "list"` | left | right |
| enumeration | `presentation: "columns"` | top | below |
| chevron | `orientation: "vertical"` | left | right |
| chevron | `orientation: "horizontal"` | top | below |

The authored layout controls description placement even when responsive CSS stacks a horizontal layout on a narrow viewport. A horizontal item that stacks responsively still keeps its explanation below its concept.

### Description absent

When all descriptions are absent:

- no description wrapper is emitted;
- no empty grid column or row is reserved;
- the existing concept-only centering behavior is preserved;
- no modifier class implying descriptions is emitted.

## Rendered Structure

Each semantic item remains one list item so assistive technology reads the concept and explanation as one unit. The visual shape moves to a dedicated concept child.

Conceptual structure for enumeration:

```html
<li class="ve-enum-block" data-ve-semantic-id="item-id">
  <div class="ve-enum-concept">number/label + title</div>
  <ul class="ve-enum-description"><li>supporting explanation</li></ul>
</li>
```

Conceptual structure for chevron:

```html
<li class="ve-chevron-step" data-ve-semantic-id="step-id">
  <div class="ve-chevron-concept">number/label + title</div>
  <ul class="ve-chevron-description"><li>supporting explanation</li></ul>
</li>
```

These snippets define ownership, not authorable HTML. Canonical authors continue to provide IR only.

### Visual ownership

The following styles move from the semantic list item to the concept child:

- background and foreground colors;
- padding and text alignment;
- enumeration border radius;
- chevron `clip-path`;
- takeaway outline.

The description uses normal surface text and must not inherit the concept's dark background, inverse foreground, or clip path.

### Semantic ID and annotations

- `data-ve-semantic-id` remains on the outer list item because the ID denotes the complete semantic item: concept plus explanation.
- `data-ve-takeaway="true"` remains associated with that semantic item.
- The visible takeaway outline is drawn only around the concept child.
- `emphasis` remains attached to the semantic item. When a description exists, it is placed in the explanation region after the description; otherwise it appears immediately after the concept without creating an empty description list.

## Enumeration Behavior

### Vertical list

- Each item is a two-column row.
- Concept blocks form the left column; explanations form the right column.
- Concept widths are consistent within the figure so explanations begin on a common visual axis.
- The complete group, not each concept independently, is centered within the figure.

### Horizontal columns

- Each item is a vertical unit containing a concept and its explanation.
- Units remain equal participants in the horizontal layout.
- On narrow viewports, units stack vertically while retaining concept-above-description order.

## Chevron Behavior

### Vertical

- Each step is a two-column row with the chevron concept on the left and explanation on the right.
- The downward chevron shape applies only to the concept child.
- The optional loop rail aligns to and encloses only the concept column; it must not wrap the explanation column.
- The visually hidden loop sentence remains unchanged.

### Horizontal

- Each step is a vertical unit with the chevron concept above and explanation below.
- Adjacent concept shapes retain their right-tip/left-notch sequence and overlap behavior.
- Explanations do not overlap and remain aligned with their corresponding concept.
- Horizontal number mode renders renderer number plus required `title` inside the concept shape.
- On narrow viewports, each complete unit stacks vertically. Its explanation remains below its own concept.

## Accessibility

- The outer ordered or unordered list semantics remain unchanged.
- Each outer list item contains its concept followed by its explanation in DOM reading order.
- Renderer-generated enumeration numbers remain `aria-hidden` because they do not declare order.
- Renderer-generated chevron numbers remain visible but `aria-hidden`; ordered-list semantics continue to convey sequence to assistive technology.
- Caption, summary, certainty/source notes, semantic IDs, and the accessible loop sentence remain intact.
- Layout must not depend on color, clipping, or spatial position alone to associate explanation with concept; DOM containment provides the association.

## Validation and Failure Behavior

Validation remains fail-closed.

For both components:

- reject number mode when any item or step lacks a non-blank `title`;
- retain label-mode label requirements and title prohibition;
- retain description all-or-none validation;
- retain existing count and text-length limits.

For chevron specifically:

- remove the horizontal-orientation prohibition on `title`;
- keep horizontal steps at 3–6;
- keep horizontal loop prohibition and `loop`/`closed-loop` capability agreement;
- reject a horizontal number-mode step without `title`, even when it has description.

No new diagnostic code is introduced. Violations continue to use `enumeration_structure_violation` or `chevron_structure_violation` as appropriate.

## Artifact Checker Contract

The artifact checker must verify the new separation rather than merely count outer blocks:

- exactly one concept child exists per enumeration item or chevron step;
- a description list, when present, is a sibling of the concept child and not its descendant;
- description presence is all-or-none across one component instance;
- each semantic outer item still owns exactly one `data-ve-semantic-id`;
- horizontal chevrons still contain no loop rail;
- vertical chevrons contain at most one loop rail.

Malformed handcrafted artifacts fail with `artifact_semantic_mismatch`.

## Registry and Asset Integrity

Component IDs, component versions, relationship kinds, capabilities, required inputs, and renderer IDs remain unchanged.

The CSS asset contents change, so both asset SHA-256 digests in `assets/components/registry.json` and the corresponding trusted registry expectations must be regenerated or updated through the existing integrity workflow. The rendered manifest must continue to declare exactly the component's updated CSS asset and no script.

## Documentation Changes

Update the canonical v2 component specification and user-facing pattern/design references to state:

- concept and explanation are separate visual regions;
- vertical means explanation right;
- horizontal means explanation below;
- number mode requires a title;
- horizontal chevron permits and requires title in number mode;
- description remains optional but all-or-none.

Examples must show at least one described vertical form, one described horizontal form, and one concept-only form.

## Test Strategy

### Validation tests

- Accept label mode with and without descriptions.
- Accept number mode only when every item or step has a title.
- Accept horizontal number-mode chevrons with title and description.
- Reject number-only content.
- Reject number-plus-description without title.
- Retain rejection of partial description sets.
- Retain all count, length, loop, and capability boundary tests.

### Renderer DOM tests

For all four layout variants:

- one outer semantic item per IR item or step;
- one concept child per outer item;
- descriptions are siblings of concept children;
- concept text appears inside the concept child;
- description text appears outside the concept child;
- no description wrapper is emitted for concept-only fixtures;
- takeaway outline class targets the concept child;
- manifests consume all semantic IDs.

### Artifact checker tests

Add invalid artifacts for:

- description nested inside a concept child;
- missing concept child;
- duplicate concept child;
- descriptions present for only some items;
- semantic ID moved off the outer item.

### Generated-document and visual checks

Build and run `check.sh` for:

- enumeration vertical with descriptions;
- enumeration horizontal with descriptions;
- chevron vertical with descriptions;
- chevron horizontal with number, title, and descriptions;
- concept-only enumeration;
- concept-only chevron;
- vertical loop chevron with descriptions.

Inspect desktop and narrow-width rendering for alignment, concept/description association, chevron continuity, loop-rail ownership, wrapping, and absence of horizontal page overflow.

## Expected File Impact

The implementation plan will cover changes to:

- `skills/visual-explain/scripts/ve_components/validation.py`
- `skills/visual-explain/scripts/ve_components/renderers/enumeration.py`
- `skills/visual-explain/scripts/ve_components/renderers/chevron.py`
- `skills/visual-explain/scripts/ve_components/checker.py`
- `skills/visual-explain/assets/components/enumeration.css`
- `skills/visual-explain/assets/components/chevron.css`
- `skills/visual-explain/assets/components/registry.json`
- enumeration and chevron unit tests, valid fixtures, invalid fixtures, and generated checked documents
- `skills/visual-explain/SKILL.md`
- `skills/visual-explain/references/patterns.md`
- `skills/visual-explain/references/design-system.md`
- `docs/superpowers/specs/2026-07-11-visual-explain-canonical-v2-components.md`

The schema and model retain their existing fields. They require no structural change because `title` and `description` already exist; contextual requirements remain enforced by validation.

## Non-Goals

- No author-controlled description placement option.
- No new component or component version.
- No change to enumeration versus chevron semantic selection.
- No partial per-item description support.
- No arbitrary HTML, CSS, coordinates, or author-controlled layout.
- No restyling of skeleton tokens or unrelated canonical components.
- No change to loop topology, flow routing, or animation behavior.

## Acceptance Criteria

The design is complete when all of the following are true:

1. Every rendered enumeration item and chevron step has a distinct concept region.
2. Any description is outside that concept region.
3. Vertical descriptions appear to the right; horizontal descriptions appear below.
4. Number mode always includes a title as the concept.
5. Horizontal number-mode chevrons show number plus title inside the shape.
6. Description-free inputs render no empty explanation region.
7. Responsive stacking preserves the concept-to-description association.
8. Vertical loop rails align only with the concept column.
9. Canonical validation, artifact checks, manifest integrity, accessibility, and existing unrelated component tests remain green.
