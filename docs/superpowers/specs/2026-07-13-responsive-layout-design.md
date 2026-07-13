# Responsive Layout Design (Fluid Type Scale + Two-Tier Figure Width)

**Date:** 2026-07-13
**Status:** Approved design revised after three-perspective subagent review (CSS correctness, repo consistency, over-engineering audit) and one external AI review round; not yet implemented
**Scope:** Skeleton fixed CSS (`assets/skeleton.html`), `references/design-system.md`, test fixtures, and one allowlist amendment in `scripts/tests/test_skeleton_audit.py`. No checker-logic, component-CSS, or generator changes.

## Goal

Optimize the self-contained HTML output for both desktop and mobile:

- On desktop, the document scales up optically (larger type, wider column) instead of floating as a small 720px column in whitespace.
- Dense, horizontally scrollable figures gain extra width on desktop.
- On mobile, nothing changes structurally, and known cramped layouts are fixed.

## Problem

`--w-narrative: 45rem` (≈720px at the 16px default) is the single max-width column for every element on every device. Mobile already stacks correctly via the `42rem` (skeleton) and `40rem` (component) breakpoints, but on desktop the document renders at the same 720px regardless of screen size. Widening the column directly would break Japanese body-text readability: 45rem is already ≈45 full-width characters per line, the upper bound of a comfortable measure.

Two observations make a low-risk fix possible:

1. Every skeleton token (5-step type scale, 7-step spacing, width) is rem-based, so the whole document scales similarly from a single root font-size.
2. `rem` inside media-query conditions always resolves against the initial font size (16px under default browser settings), independent of any `html { font-size }` declaration, so scaling the root cannot shift any existing breakpoint.

## Chosen Approach

Two composed mechanisms, both living entirely in the skeleton's fixed CSS.

Alternatives considered and rejected:

- **Widening `--w-narrative` (45→60rem):** stretches body lines to ≈60 characters, degrading readability, and reintroduces a second per-element max-width to compensate.
- **Type scale only (no breakout):** even at the scaled 900px column, a dense matrix still overflows into horizontal scroll; matrix is the one shape that genuinely benefits from extra width. (Component flow does not — see eligibility below.)
- **Breakout only (no type scale):** figures widen but body text stays optically small on desktop.
- **Container queries:** a rewrite of all ten component CSS files with no width gain by itself.
- **Opt-in breakout attribute (`data-wide`):** requires generator and checker changes plus a fail-closed eligibility rule; deferred unless QA rejects the automatic variant.

### Mechanism 1 — fluid type scale

Add one rule to the skeleton:

```css
html { font-size: clamp(1rem, 0.7rem + 0.5vw, 1.25rem); }
```

- At viewport ≤ 960px the root stays exactly 16px: phones and portrait tablets are pixel-identical to today.
- Above 960px the root grows linearly, reaching the 20px cap at 1760px viewport and staying constant beyond. At 1920px the narrative column is 45rem × 20px = 900px, with all type, spacing, and figures scaled by the same factor. (Derivation: the preferred term `0.7rem + 0.5vw` passes through (960px, 16px) and (1760px, 20px).)
- No token values change. Measure (characters per line) is invariant because the column and the type scale together.
- Existing media queries (`42rem`, `40rem`, and the `60rem` gate below) are unaffected because media-query `rem` uses the initial font size, not the declared root size.

### Mechanism 2 — two-tier figure width (symmetric breakout)

Eligibility is a **closed enumeration**, not a structural inference:

- **Legacy route:** `.figure` cards that contain a `.flow` or `.matrix`. Bare legacy `.flow`/`.matrix` markup (the canonical un-captioned form in `patterns.md`) is *not* eligible and keeps narrative width; wrapping in `.figure` is what opts a legacy diagram in.
- **Component route:** `matrix` only. Component `flow` is excluded because its canvas stacks stations vertically — widening it would only stretch node text toward a 65rem measure, contradicting the readability rationale above. `waterfall` (columns) also owns a horizontal-scroll container but is explicitly excluded as a follow-up candidate (see Non-Goals).

Two **separate** rules (they must not share one selector list: an unsupported `:has()` would invalidate the entire list in older browsers), gated behind `@media (min-width: 60rem)`:

```css
@media (min-width: 60rem) {
  .figure:has(.flow, .matrix) {
    margin-inline: calc(-1 * min(10rem, (100vw - 60rem) / 2));
  }
  figure[data-ve-component="matrix"] .ve-matrix-scroll {
    margin-inline: calc(-1 * min(10rem, (100vw - 60rem) / 2));
    max-width: none;
  }
  .figure .matrix table, figure[data-ve-component="matrix"] table { width: auto; margin-inline: auto; }
}
```

- The extension is symmetric (equal negative margins), so the widened element stays centered on the narrative column's axis; both edges move out by the same amount, up to 10rem per side (total ≤ 65rem). The 10rem/65rem cap is a provisional aesthetic bound (≈44% width gain), to be tuned during visual QA.
- The `60rem` gate reuses Mechanism 1's knee so the design has a single desktop threshold (960px initial-rem). The extension **ramps continuously from 0** at that knee: inside the declaration `60rem` scales with the fluid root, so the ramp is exactly 0 at a 960px viewport, grows at 0.35px per viewport px per side, and meets the 10rem cap near a 1490px viewport. There is no discontinuous width jump at the gate.
- Total widened width is `45rem + min(20rem, 100vw − 60rem)` ≤ `100vw − 15rem`, so no page-level horizontal overflow can occur even with classic (always-visible) scrollbars.
- **Legacy route:** the whole `.figure` surface card widens, because its own `overflow: auto` would clip a widened child. The figcaption sits inside the card and moves with it; the card boundary provides its own alignment context. Browsers without `:has()` keep the figure at narrative width — a fail-safe degradation.
- **Component route:** only the `.ve-matrix-scroll` container widens. `max-width: none` is required because the component sheet declares `max-width: 100%`, which would otherwise re-clamp the width and turn the negative margins into a leftward shift instead of a symmetric widening. The skeleton selector (specificity 0,2,1) deliberately overrides the component's declaration (0,2,0); this cross-boundary override is documented in the ownership amendment below. Captions, summaries, and notes keep `max-width: var(--w-narrative)` and stay flush with the body-text edge.
- **Matrix tables are content-width inside the breakout** (user decision after QA review of the sparse 2×2 case): within the 60rem gate, `.figure .matrix table` and `figure[data-ve-component="matrix"] table` get `width: auto; margin-inline: auto`, so a sparse table sizes to its content (respecting the component `min-width` floors) and centers on the column axis instead of stretching to ≈1300px. A dense table wider than the container still overflows into its scroll container. Known cosmetic consequence: for sparse tables the width snaps from full-column to content-width when crossing the 960px gate; judged in QA item 4.
Effective figure widths with both mechanisms active: ≈1160px on a 1440px screen, ≈1300px on a 1920px screen.

### Mechanism 3 — mobile hardening

- Known defect: `.ask-options [data-ask-option]` keeps its two-column grid (`minmax(8rem, .35fr) 1fr`) at all widths and is cramped at 320px. Add to the existing `@media (max-width: 42rem)` block:

  ```css
  .ask-options [data-ask-option] { grid-template-columns: 1fr; gap: var(--space-1); }
  ```

- Audit at 320 / 375 / 430px: all ten components, legacy figures (flow, layers, compare, matrix, timeline, kpi, bars, terms), ask blocks, first-screen, stepper, theme control. A newly found breakage is bundled into this change only if it is the same shape as the known defect — one rule using existing tokens and existing breakpoints. Anything larger becomes a separate change.

## Spec Amendments (design-system.md)

The single-width principle is amended honestly rather than silently diverging:

- **幅（1）— 単一幅** becomes a two-tier width rule: `--w-narrative` (45rem) remains the only column for headings, body, and all non-eligible figures; eligible figures (the closed enumeration above) may extend symmetrically up to 65rem total on wide viewports. Edge sharing is preserved as symmetry around the shared center axis. Caption placement follows the route: component-route captions/summaries/notes keep `--w-narrative` and stay flush with the body-text edge; a widened legacy card carries its in-card figcaption with it, the card boundary being its alignment context. The amendment states this two-route caption contract explicitly.
- The sentence 「中央寄せは使わない」 in the same section is rewritten to scope it to content alignment inside the column (e.g. 「カラム内で内容を中央寄せしない。二層幅の張り出しは本文カラムの中心軸に対する対称拡張であり、この規則の例外ではない」), since the page column itself has always been centered by the skeleton.
- The 表層「単一幅」 bullet and the レイアウト不変条件 section reference the same closed exception.
- **コンポーネント資産の所有権** gains a closed exception: the skeleton may target component-namespaced selectors (`figure[data-ve-component="matrix"] .ve-matrix-scroll`) for two-tier width layout only, including overriding the component's `max-width`; components still own all other namespaced rules. The note 「骨格全体の中央揃え規則は変えない」 is reconciled with the breakout's center-axis symmetry.
- A new surface-layer bullet documents the fluid root type scale (16→20px across 960→1760px) and states that token values and measure are unchanged.
- `patterns.md` gains one note: wrapping a legacy `.flow`/`.matrix` in a `.figure` is what opts it into the two-tier width; the canonical bare markup stays at narrative width.
- The Pi/Katsura conservative-degradation section is unaffected.

## Impact and Invariants

- **Skeleton tokens:** no token added, removed, or changed. The additions are the `html` font-size rule, the breakout block, and the ask-options stacking rule.
- **Component CSS / registry.json:** files untouched; asset hashes stay valid. The matrix scroll container's `max-width` is overridden from the skeleton (see ownership amendment) rather than edited in place.
- **Checker:** runtime logic (`check.sh` embedded Python, `check_component_html.py`, `ve_components.checker`) unchanged. One test-side amendment is required: `test_skeleton_audit.py` restricts skeleton margin values to an allowlist (`0 | var(--space-*) | auto | inherit`), which the breakout's `calc(-1 * min(…))` violates; the audit gains an explicit, narrowly scoped exception for the two breakout rules.
- **Test fixtures:** the checker byte-compares fixed regions against `assets/skeleton.html`, so skeleton-embedding fixtures must be re-spliced (measured: 86 of 87 `scripts/tests/*.html` embed the skeleton's fixed CSS; only `compatibility-valid-fragment.html` does not). `resplice.py`'s default glob would destroy the two marker-less fixtures (`bad-title-missing.html`, `compatibility-valid-fragment.html`) and `component-bad-fixed-region.html`, whose intentional divergence lives outside the splice markers (in the fixed footer region), so `KEEP_AS_IS` grows to seven entries; the tool re-splices 80 fixtures plus the example, and the six KEEP_AS_IS files that embed skeleton CSS receive the same three CSS edits textually, preserving their intentional marker damage and fixed-region divergence.
- **Generators (`build_explainer.py`, `ve_components`):** untouched.
- **Previously generated documents:** self-contained snapshots; they keep the old layout when viewed and are not migrated. Re-editing an old document and re-running `check.sh` will hard-fail the fixed-region comparison until it is re-spliced onto the new skeleton — an accepted consequence of the byte-compare design.

## Verification

1. `check.sh --selftest` and the full pytest suite pass after fixture regeneration and the skeleton-audit allowlist amendment.
2. Regenerate one representative document per route (legacy and component) and inspect at 375 / 768 / 1440 / 1920px in light and dark themes:
   - 375px is pixel-identical to the pre-change rendering (fluid scale inactive, breakout gated off), with one intended exception: `.ask-options` rows now stack in one column.
   - 1920px shows the 900px narrative column and ≈1300px eligible figures centered on the same axis.
   - Non-eligible content — body text, component flow, kpi, bars, terms, pyramid, stairs, waterfall, slope, enumeration, chevron, logic-tree, evidence-map, and bare legacy flow/matrix — remains at narrative width on all viewports.
3. Resize continuously from 900px to 1920px and confirm eligible figures widen smoothly from the 960px knee with no discontinuous jump.
4. With classic (always-visible) scrollbars forced, confirm no page-level horizontal scrollbar appears at any width ≥ 960px.
5. Confirm component-route matrix captions stay flush with the body-text edge while the scroll canvas widens.
6. Inspect a sparse component matrix (2×2) at 1920px: its table stays content-width (≥ the component's `min-width` floor) and centered on the column axis; it must NOT stretch to the widened container. Also resize across 960px and judge the sparse table's width snap acceptable.
7. Check browser zoom at 200% and 400% on a 1280px window: content reflows without page-level horizontal scrolling and text scales as expected.
8. This QA pass may be combined with the still-open browser visual QA for the enumeration/chevron description-layout change.

## Trade-offs and Risks

- **Sparse legacy flows widen too.** A figure-wrapped 2–3 node legacy flow stretches across the widened card (flow nodes flex-grow). Sparse matrix stretching was eliminated by the content-width table rule above; the flow case remains accepted pending visual QA, with the opt-in `data-wide` attribute as the fallback (explicitly out of scope for this change).
- **`:has()` dependency (legacy route only)** degrades to the current narrative width on old browsers; no content is lost. The component-route rule is kept in a separate selector list precisely so this degradation cannot spread to it.
- **Cross-boundary `max-width` override** slightly blurs skeleton/component ownership; accepted as a documented, closed exception in preference to editing component CSS and invalidating registry hashes.
- **Breakpoint inconsistency (skeleton 42rem vs components 40rem)** predates this change and is left as-is; unifying it would require touching all component assets and registry hashes for no user-visible gain.

## Non-Goals

- Waterfall `columns` (9-column) breakout — it owns a horizontal-scroll container and is the natural follow-up if QA shows it cramped, but it is excluded from this change's closed enumeration.
- Widening bare (non-`.figure`-wrapped) legacy flow/matrix markup.
- Container-query migration of components.
- Any change to information density rules, tokens, or the meaning skeleton.
