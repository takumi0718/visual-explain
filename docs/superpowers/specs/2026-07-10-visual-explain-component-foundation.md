## Overview

This specification defines a reusable semantic diagram-component foundation for visual-explain. The foundation changes the canonical authoring surface from format-specific HTML generation to a limited declarative intermediate representation (IR), while preserving the current single-file delivery model and the old standalone HTML-insertion generation behavior as a temporary source of compatibility markup. Canonical component instances and compatibility sections converge through one final-assembly path.

The architectural baseline is a minimal staged combination of a registry, generation-time component modules, a declarative IR, and final flattening. In the first vertical slice, exactly `matrix` and `flow` use one common contract, registry, composition path, module-resolution path, flattening path, and checker route. The other existing formats remain unchanged until later migrations.

The canonical pipeline is:

`Explanation IR → IR validation → deterministic candidate narrowing → explicit component selection → registry resolution → component rendering → composition → flatten/inlining → final HTML checker`

The produced explainer remains one dependency-free, self-contained HTML document. Component modules and the registry exist only at generation time. The final document has no imports, external CSS or JavaScript, CDN assets, web fonts, network dependency, runtime package dependency, or build dependency.

A component is a semantic-responsibility unit: it owns a bounded kind of relationship and the rules for rendering that relationship legibly. It is not an arbitrary HTML partial, a CSS-class family, or a convenient split of `skeleton.html`. This boundary allows renderers and a future visual language to evolve without forcing authors to generate DOM, CSS, or free coordinates.

## Goals

- Make semantic diagram programs reusable through stable component contracts rather than copied HTML fragments.
- Let an author declare explanation content and relationship structure, deterministically narrow the valid component set, and explicitly select a component with a checker-verifiable reason.
- Establish a limited canonical IR that weak models can produce reliably without authoring HTML, CSS, JavaScript, DOM operations, or coordinates.
- Give `matrix` and `flow` one shared end-to-end route while preserving their distinct semantic responsibilities.
- Separate selection, registry/discovery, rendering, composition, skeleton ownership, flattening, and checking into independently understandable boundaries.
- Preserve current CSP, safety, fixed-region validation, required-content validation, certainty, source attribution, accessibility, responsive meaning, and static-first behavior.
- Allow trusted component-local styles and optional enhancement scripts without allowing ordinary generated content to modify fixed regions or inject arbitrary CSS or JavaScript.
- Preserve a provenance-labelled compatibility and weak-model degradation path during gradual migration.
- Keep the final artifact a single self-contained HTML file.
- Leave room for a later coherent, beautiful, and intuitive visual language without prematurely choosing diagram styling or interaction patterns.
- Make incorrect relationship direction, order, or membership harder to render by requiring explicit semantic data and validating it before and after rendering.

## Non-Goals

- Implementing modules, schemas, renderers, checker changes, migrations, fixtures, dependency installation, or browser smoke tests in this phase.
- Completing the visual design of `matrix`, `flow`, or any other component.
- Migrating `layers`, `compare`, `timeline`, `kpi`, `bars`, `terms`, `details`, or `stepper` in the first vertical slice.
- Introducing an external UI framework, diagram library, runtime registry, or client-side component loader.
- Building heuristic component auto-selection, ranking, override logic, or model-driven visual styling in the MVP.
- Supporting interaction-required diagrams, decorative animation, arbitrary coordinates, or free-form connector drawing.
- Reworking the entire current skeleton or weakening its safety and fixed-region guarantees for convenience.
- Fixing, re-proposing, or making an immediate blocker of the known causal-reversal fixture issue. This specification addresses only general validation that makes direction and order errors harder.
- Defining a general-purpose diagram language for relationships not exercised by the first `matrix` and `flow` slice.
- Deciding the cadence or aesthetic direction of the later visual-language exploration.

## Current State and Constraints

The MVP produces one self-contained HTML document by inserting generated content into a fixed `skeleton.html`. CSS, JavaScript, diagram rendering behavior, CSP boundaries, and fixed-region safety assumptions are centralized in the skeleton. Existing fixed formats are `flow`, `layers`, `compare`, `matrix`, `timeline`, `kpi`, `bars`, `terms`, `details`, and `stepper`. The checker validates safety, fixed regions, document structure, and required content.

This centralization is useful for a small MVP but combines four kinds of change: semantic format behavior, visual styling, document-shell behavior, and security boundaries. Merely splitting the skeleton into HTML fragments or CSS files would move code without establishing semantic ownership. The foundation therefore treats the current skeleton as the compatibility baseline, not as the desired component boundary.

The following constraints are invariant:

- The final artifact is one self-contained HTML file.
- It has no external CSS, JavaScript, CDN, web fonts, network calls, runtime loader, or required build tool.
- Generation-time resolution and flattening may use local modules, but no module mechanism remains in the artifact.
- CSP, safety checks, fixed-region checks, document structure checks, and required-content checks are preserved unless a separately documented need justifies a change.
- All core relationships, labels, certainty, sources, captions, and the meaning of optional interactions are legible in static HTML and CSS when JavaScript is absent, fails, or is blocked.
- There is always an unoperated core path. JavaScript may enhance navigation or disclosure but may not create, fetch, or make initially intelligible the core explanation.
- Certainty, source attribution, accessibility semantics, and meaningful responsive behavior are required, not renderer-specific decoration.
- Migration is incremental. Existing formats do not move until their semantic contract and checker coverage are ready.
- Ordinary generated content cannot edit fixed regions or inject CSS or JavaScript.
- Weak-model degradation is explicit and provenance-labelled rather than silently treated as a canonical component render.

## Options and Recommendation

Four approaches were considered.

| Criterion | 1. Skeleton-embedded parts plus registry | 2. Component modules imported and inlined at generation time | 3. Declarative IR/schema selects renderers | 4. Minimal staged combination |
|---|---|---|---|---|
| AI generation stability | Moderate: authors still generate skeleton-shaped HTML | Moderate: module APIs reduce duplication but add import decisions | High: authors produce bounded semantic data | Highest: limited IR is canonical, compatibility remains available |
| Visual expressiveness | Low to moderate; constrained by the centralized skeleton | High; renderer modules can evolve independently | Moderate to high; depends on renderer maturity | High; semantic stability and renderer evolution coexist |
| Responsibility clarity | Low; registry risks becoming only an index over tangled parts | High at module boundaries | High between authoring and rendering | Highest when IR, registry, renderer, skeleton, checker, and flattening are explicit |
| Checker-verifiability | Moderate; mostly post-hoc HTML checks | Moderate to high; module contracts add evidence | High; IR and output can both be checked | High; dual checks are established on a small shared route |
| Convergence to one HTML | Native | Achieved by inlining | Requires rendering and flattening | Explicitly guaranteed by generation-time flattening |
| Weak-model usability | Moderate; HTML generation burden remains | Moderate; module/API choice remains | High; constrained schema is easier to produce | High; IR is normal, labelled HTML insertion is degradation |
| Extension cost | High; the skeleton continues to grow | Moderate | Moderate; schema, renderer, and checker must move together | Moderate initially, then controlled through one extension gate |
| Migration cost | Lowest, but preserves centralization | Moderate | High if introduced as a replacement | Bounded; only `matrix` and `flow` move first |
| Over-engineering risk | Low structural investment, high debt-retention risk | Moderate | High if a universal IR is designed prematurely | Moderate and controllable by limiting IR and component count |
| Future visual language | Weak | Strong | Strong | Strongest: semantic contracts survive renderer replacement |

The decision is approach 4, the minimal staged combination:

- Use a limited declarative IR as the initial canonical authoring surface.
- Narrow component candidates deterministically from declared relationship structure.
- Require the author or generator to select a component explicitly and record a semantic reason.
- Use the registry only for discovery and contract resolution, not heuristic routing.
- Resolve trusted component modules at generation time and flatten their outputs into controlled skeleton slots.
- Route only `matrix` and `flow` through the new path initially.
- Preserve current HTML insertion as a temporary, labelled compatibility and weak-model fallback path.

This combination avoids both extremes: leaving semantic rendering embedded in the skeleton and designing a universal diagram IR before there is evidence for it. Heuristic auto-selection remains a later option after registry metadata and component coverage are mature; it is not part of the MVP contract.

## Architecture and Responsibility Boundaries

### Explanation IR and validation

The Explanation IR is the canonical authoring boundary. It contains explanation-level metadata, declared relationship structure, component instances, explicit selections and reasons, content payloads, certainty and source references, captions, and accessibility descriptions. It contains no HTML, CSS, JavaScript, DOM operations, renderer class names, pixel coordinates, or connector geometry.

Initial validation checks the IR before any renderer runs. It establishes that relationship declarations, semantic identifiers, content, certainty/source references, captions, and accessibility data are structurally valid. It does not repair or infer missing causal direction from prose.

### Selection and routing

The selection layer maps one component instance's declared relationship structure to an ordered-neutral set of allowed component IDs using registry capabilities. In the MVP this process is deterministic and non-heuristic. A set containing more than one component is a valid result: it means multiple registered components declare the required capability, not that the declaration is invalid. The author or generator must then choose one allowed component explicitly.

The IR records both the selected component and a reason expressed as matched declared capabilities. The reason is semantic, such as a need to show directed transitions or two-axis intersections; visual preference is not a valid reason. A component outside the narrowed candidate set, a missing reason, or a reason that does not match the declared structure fails canonical validation.

### Registry and discovery

The registry is the generation-time index of component contracts. It answers which components exist, what relationships they can express, what inputs they require, which trusted renderer resolves them, what dependencies and fallbacks they declare, and which checker rules apply.

The registry does not rank components, inspect prose, choose aesthetics, execute renderers, compose sections, or appear in the final HTML. It does not become a heuristic router in the MVP.

### Semantic components and renderers

A component owns one bounded semantic responsibility and its representation rules. `matrix` owns two-axis classification and intersection comparison. `flow` owns explicit sequence, directed transitions, and branching relationships.

A component owns:

- validation rules specific to its semantic payload;
- transformation of that payload into statically legible semantic markup;
- component-local trusted styling needed to expose the relationship;
- accessibility semantics and reading order inside the component;
- responsive preservation of meaning inside the component;
- an optional enhancement that does not replace the static core;
- a fallback and checker rules for its rendered relationship;
- a render manifest that traces semantic input IDs to output IDs and trusted assets.

A component does not own:

- the explainer's overall narrative or component choice;
- section ordering or cross-component page composition;
- the document shell, CSP, global typography, or fixed regions;
- global source aggregation or explanation-level certainty policy;
- arbitrary styling supplied by generated content;
- relationships not declared in its contract;
- free-coordinate positioning across components;
- network or external runtime behavior.

The renderer is a trusted generation-time module implementing the component contract. It receives validated semantic input and returns a typed render result. It is not invoked in the final document.

### Composition

Composition arranges component instances into explainer sections. It owns section order, instance scoping, narrative adjacency, caption placement, shared certainty/source references, common tokens, and final reading order between components. It does not mutate a component's internal graph, invent relationships, connect arbitrary coordinates across components, or select a renderer.

### Skeleton

The skeleton owns the document shell, fixed regions, CSP, global tokens, baseline typography, common non-component UI, and explicit insertion points. During migration it gains narrowly controlled component markup/style/script slots. It does not retain new component-specific rendering logic.

### Flattening and final checking

The flattener resolves registry entries and trusted modules, composes render results, deduplicates approved assets, and inlines them into the correct skeleton slots. It leaves no imports, registry references, module loaders, or dependencies in the final artifact.

The checker validates both canonical input and the flattened result. Passing final HTML checks alone does not make an invalid canonical IR valid, and passing IR checks does not excuse an unsafe or incomplete final document.

### Compatibility route

A final explainer may contain any ordered mix of canonical `matrix`/`flow` component instances and explicitly labelled compatibility sections. Both kinds of section enter the same composition and flattening final-assembly route and become one document.

A compatibility section bypasses canonical IR relationship selection, candidate narrowing, registry resolution, and trusted component renderer execution. The old standalone HTML-insertion generation behavior is only the temporary source of that section's HTML markup; it is not a second final-assembly path. The resulting markup enters only the controlled content slot, under the existing content rules and explicit compatibility provenance. It cannot claim the canonical component route, edit fixed regions, contribute to controlled style or script slots, or inject arbitrary CSS or JavaScript. It remains subject to existing fixed-region restrictions and final HTML checker validation. A fallback is deliberate and observable; canonical validation failure must not silently switch paths.

## Component Contract

### Inputs

Every component instance receives a common envelope plus a component-specific payload.

The common envelope contains:

- a stable explanation, section, and instance identity;
- the declared relationship structure;
- the explicit component ID and contract version;
- the semantic selection reason and matched capabilities;
- caption data;
- certainty assertions and references;
- source records and references;
- an accessibility label and concise relationship summary;
- the component-specific semantic payload.

The `matrix` payload contains row and column axes, axis labels, cells, stable semantic IDs, cell content or references, and an optional declared comparison direction. It does not contain grid CSS, DOM markup, or coordinates.

The `flow` payload contains stable nodes, explicit directed edges, edge relationship types, optional semantic branches or groups, and an explicit start or reading-order hint when the graph does not yield one unambiguously. Each edge specifies direction structurally. The renderer never derives `from` and `to` from prose or array position.

### Outputs

A renderer returns a typed render result containing:

- a namespaced semantic markup fragment;
- references to trusted, component-local style assets;
- references to optional trusted enhancement-script assets;
- a render manifest;
- validation diagnostics.

The render manifest records component ID and version, instance ID, consumed semantic IDs, generated relationship and landmark IDs, trusted asset identities and hashes, declared dependencies, and active fallback mode. It creates traceability between the IR, controlled slots, and final DOM.

The contract does not accept arbitrary renderer-authored strings from an ordinary generation response as trusted style or script assets. Only assets resolved from allowlisted registry entries and controlled renderer modules may enter controlled slots.

### MVP-minimum registry metadata

| Metadata | MVP requirement |
|---|---|
| Identity and version | Stable component ID and contract version for resolution and compatibility checks |
| Semantic responsibility | Short, reviewable definition of the relationship the component owns |
| Relationship capabilities | Declared relationship types accepted by deterministic narrowing |
| Required and optional inputs | Types, cardinality, stable-ID requirements, constraints, and component payload schema |
| Static/interactive behavior | `static` or `static-with-optional-enhancement`; interaction-required is forbidden |
| Caption, certainty, and source slots | Accepted placement/reference rules; common-envelope preservation is mandatory |
| Accessibility | Required semantics, label/summary, internal reading order, and enhancement focus behavior when applicable |
| Responsive requirement | Narrow layouts preserve meaning and reading order; specific aesthetic breakpoints remain renderer-owned |
| Dependencies | Explicit foundation-provided token/helper dependencies only; no external or component-to-component runtime dependency |
| Fallback/degradation | Static behavior for absent enhancements, constrained space, or unsupported optional features; core semantics cannot be dropped |
| Checker rules | Identifiers for IR, manifest, controlled-asset, accessibility, and final DOM checks |
| Renderer reference | Generation-time trusted module identity; removed during flattening |

### Later metadata, not MVP placeholders

The following are deferred until there is evidence for them: heuristic ranking hints, auto-selection confidence, visual-language family, theme variants, density preferences, animation semantics, advanced interaction capability, cross-component linking, deeper localization metadata, component performance budgets, and a full registry deprecation lifecycle.

These fields are not empty required placeholders in the MVP schema. Omitting them prevents the initial registry from pretending to support decisions it cannot yet validate.

### Static-first, CSS, JavaScript, accessibility, and responsive ownership

Static-first is an invariant, not a fallback quality target. The markup and CSS present every core relationship, node or cell label, relationship direction, certainty, source, caption, and the meaning of any enhancement without JavaScript. A script may improve navigation, filtering, focus, or disclosure only when the initial document already exposes the complete core explanation.

Component-local CSS is namespaced and uses skeleton-owned tokens where available. It owns the minimum layout needed to expose the component's relationship. It may not reset global styles or target fixed regions. Ordinary generated content cannot supply CSS.

Optional JavaScript is a trusted, allowlisted renderer asset. It is enhancement-only, instance-scoped, CSP-compliant, and unnecessary for initial meaning. Ordinary generated content cannot supply scripts, event-handler attributes, or executable URLs.

The component owns semantic structure, internal reading order, labels, descriptions, and enhancement focus behavior inside its rendered boundary. Composition owns reading order between instances. The skeleton owns document-level landmarks and global navigation. Responsive behavior may change layout, wrapping, or static presentation, but may not hide semantic content, reverse order, or require interaction to recover core meaning.

## Selection, Registry, and Composition

### Canonical selection policy

The initial selection policy is deterministic narrowing followed by explicit author selection:

1. The author declares the relationship structure independently of a component name.
2. The selection layer matches that declaration against registry relationship capabilities.
3. It returns the valid candidate set, with the capabilities matched for each candidate, without ranking or aesthetic preference. A candidate set may contain one or several components.
4. The author or generator explicitly selects one candidate.
5. The IR records the selected component and matched-capability reason.
6. The checker verifies that the component was in the candidate set and that the reason matches both the declaration and registry contract.

For the first slice, the relevant distinction is intentionally narrow: a component instance declaring two-axis classification/intersection comparison routes to `matrix` candidates; an instance declaring explicit ordered or directed transitions/branches routes to `flow` candidates. An explanation that needs both relationship families declares two component instances and lets composition order them.

Multiple candidates for one valid declaration are normal and require explicit selection. Canonical authoring fails only when the declaration itself is structurally invalid, when no registered component matches all capabilities required by that one instance, or when the explicit selection or reason is invalid. In particular, one component instance that combines matrix-style intersections and flow-style directed transitions requires a registered component whose contract explicitly supports that combined responsibility. Because the first slice has no such component, that declaration yields no candidate; it is not treated as an ambiguous multi-candidate result. Under-specified declarations that omit the relationship fields needed for deterministic matching are structurally invalid rather than guessed from prose.

The selection layer and checker use bounded diagnostic categories: invalid relationship declaration, no matching component, selection outside candidate set, and selection-reason mismatch. A compatibility render may be requested explicitly, with provenance, but is not an automatic success path.

Heuristic registry-metadata auto-selection and override are deferred. The contract leaves room to add them later without changing the requirement that a resolved selection and its basis be recorded and checkable.

### Registry resolution and module discovery

Registry lookup occurs after selection validation. A lookup resolves the exact component contract version, trusted renderer module, trusted asset identities and hashes, allowed dependencies, fallback, and checker rule set. Resolution fails closed when the component or version is unknown, the renderer is not allowlisted, a dependency is undeclared, or a required checker rule is unavailable.

Discovery is available to generation tooling so an author can learn the valid component contracts. Discovery output is descriptive and schema-bound; it does not expose renderer internals as authoring instructions.

### Composition rules

Composition accepts validated canonical component instances and explicitly labelled compatibility sections in the same explainer. It establishes one mixed section sequence, unique scopes, cross-section reading order, caption placement, and shared source/certainty references, then sends that sequence through one flattening route. It preserves each canonical component's semantic identifiers and graph. A compatibility section carries markup plus assembly metadata and provenance, not a canonical component selection or registry contract.

Composition may reuse foundation tokens and deduplicate identical trusted assets. It may not merge two component payloads into an unregistered hybrid, draw cross-component free-coordinate connectors, infer missing edges, or resolve a component choice. A future cross-component relationship requires an explicit semantic contract rather than a composition shortcut.

## Final HTML Flattening and Ownership

Flattening is a small generation-time convergence step, not a runtime framework. Its only target is the dependency-free final HTML.

There is exactly one composition/flattening final-assembly route, including for documents that mix canonical and compatibility sections. The flattener:

- verifies every canonical instance against the selected registry contract;
- invokes only the resolved trusted renderer version for canonical instances; it performs no registry lookup or component-renderer execution for compatibility sections;
- accepts compatibility markup only from the temporary standalone HTML-insertion generation behavior, with required provenance and existing-rule content validation;
- verifies each canonical renderer's returned manifest and trusted asset identities;
- scopes instance IDs and component-local markup;
- orders component markup according to composition;
- deduplicates identical allowlisted style/script assets;
- places markup, styles, and optional scripts only in their designated controlled slots;
- preserves all other skeleton fixed regions byte-for-byte or according to their existing canonical hash rules;
- emits provenance sufficient for checker traceability without retaining executable registry or module machinery;
- confirms that no import, external reference, or generation dependency remains.

Controlled slots are explicit security boundaries introduced by migration:

- The content slot accepts canonical component markup produced from validated IR and explicitly labelled compatibility markup produced by the old standalone HTML-insertion generation behavior under existing content rules. Both may coexist in document order.
- The component-style slot accepts only allowlisted, hash-verified assets declared by the resolved registry entry and render manifest.
- The optional enhancement-script slot accepts only allowlisted, hash-verified, CSP-compliant assets declared by the resolved registry entry and manifest.
- No slot accepts arbitrary CSS or JavaScript from ordinary generated content.

All regions outside these slots continue to use existing fixed-region hashing and validation. Controlled slots are not exempt from checking; they are validated under stricter registry/manifest/namespace/dependency rules appropriate to their variable contents.

Ownership after flattening remains observable: component markup carries instance and semantic identities, controlled assets carry component/version/hash provenance, compatibility sections carry compatibility provenance, and skeleton-owned regions remain fixed. The final document needs no registry or build tool to render.

## Checker and Safety Contracts

Checking has four layers.

### 1. Safety and fixed-region checks

The checker preserves existing CSP, prohibited external reference, unsafe markup/script, fixed-region integrity, document structure, and required-content checks. All non-controlled fixed regions remain hashed or structurally validated as today. Ordinary generated content cannot modify them.

Controlled style and script slots are validated by allowlisted component ID/version/asset hash, render manifest declaration, slot type, namespace constraints, prohibited constructs, CSP compatibility, absence of external references, and complete declared dependency closure. A controlled slot is not a general escape hatch.

### 2. IR and selection checks

For canonical component instances, the checker validates the limited IR schema, stable semantic IDs, declared relationship structure, explicit component selection, selection reason, candidate-set membership, required caption/certainty/source/accessibility data, and component contract version. It accepts a deterministic candidate set with multiple members, then requires the explicit selection and reason to identify one valid member. It rejects structurally invalid or under-specified declarations, an empty candidate set, a selection outside a non-empty candidate set, and a reason not supported by the recorded matched capabilities, using the bounded diagnostic categories defined by the selection policy. Canonical input cannot omit a field and expect the renderer to infer it from prose. Compatibility sections do not pretend to pass this layer; their provenance identifies them as bypassing canonical IR selection and registry resolution.

### 3. Component-contract and manifest checks

The checker validates required and optional payload rules, behavior classification, fallback declaration, responsive and accessibility requirements, trusted dependency declarations, renderer/manifest identity, and semantic ID coverage. Every required input semantic ID must be accounted for in the manifest, and the manifest may not introduce undeclared core relationships.

### 4. Flattened-document checks

The checker traces IR semantic IDs and relationships into the final DOM; verifies uniqueness, reading order, labels, captions, certainty, sources, fallback content, and controlled assets; and confirms static-first behavior. Final HTML must remain meaningful with enhancement scripts absent. Compatibility sections must retain compatibility provenance and pass the existing final checks.

Canonical failures are explicit. A failure does not silently weaken a rule, alter a fixed region, discard semantic content, or switch to compatibility mode. Compatibility fallback must be deliberately selected and labelled.

General relationship validation makes incorrect causal or order rendering harder:

- `flow` edges require stable `from`, `to`, and relationship type fields.
- Direction is not inferred from node prose, source order, array position, or screen geometry.
- Duplicate IDs, dangling edges, invalid endpoints, accidental self-edges, and undeclared relationship types are errors.
- Unreachable nodes, ambiguous starts, cycles that conflict with a declared acyclic relation, and display-order contradictions are errors or explicit warnings only where the contract defines an allowed exception.
- The manifest records the directed relationships rendered, and final DOM semantics must preserve them.
- `matrix` cells must reference valid row and column identities; duplicate or orphan intersections are errors.

These are general input and output safeguards. The known causal-reversal fixture issue is neither fixed nor treated as a blocker in this design phase.

## Migration and First Vertical Slice

Migration proceeds component by component.

### Stage 1: Foundation preparation without format migration

Treat the current skeleton and checker behavior as the compatibility baseline. Define the limited common IR envelope, registry contract, typed render result, manifest, controlled slots, flattening boundary, compatibility provenance, and four checker layers. Introducing a controlled slot must preserve hashing/validation for every other fixed region and must not authorize generated CSS or JavaScript.

### Stage 2: Shared `matrix` and `flow` vertical slice

Register only `matrix` and `flow`. Each uses its own semantic payload and renderer but shares the same:

- common IR envelope;
- deterministic narrowing and explicit selection/reason;
- registry discovery and exact contract resolution;
- composition interface and instance scoping;
- trusted generation-time module resolution;
- typed render result and manifest;
- controlled markup/style/script slot policy;
- flattening path;
- dual IR and final HTML checker route;
- static-first, certainty, source, caption, accessibility, and responsive invariants;
- single-file, dependency-free output requirement.

The slice succeeds only when both components traverse that common route. Demonstrating one component on the new path while special-casing the other does not satisfy the foundation objective.

The slice establishes semantic correctness and safety, not finished appearance. `matrix` must make axes and intersections statically understandable; `flow` must make nodes, direction, sequence, and branches statically understandable. Their detailed visual treatments are deferred.

### Stage 3: Compatibility coexistence and promotion

For `layers`, `compare`, `timeline`, `kpi`, `bars`, `terms`, `details`, and `stepper`, the old standalone HTML-insertion generation behavior remains the temporary source of compatibility markup. Weak-model generation may use the same source behavior when it cannot safely satisfy canonical IR. In both cases the markup becomes an explicitly labelled compatibility section and joins canonical sections, if any, through the one composition/flattening final-assembly route. It bypasses canonical selection, registry resolution, and trusted component renderer execution, but remains subject to existing content rules, fixed-region restrictions, and final HTML checks.

After `matrix` and `flow` meet their shared-route success criteria, their normal generation route becomes canonical IR. The old HTML-insertion generation behavior remains a bounded emergency source of compatibility markup for them and cannot be reported as canonical success.

### Stage 4: Later one-at-a-time migrations

Each remaining format migrates only after its semantic responsibility, capabilities, schema, trusted renderer assets, fallback, accessibility behavior, and checker rules pass the safe extension procedure. No big-bang conversion is required, and migrating all formats is not part of the first vertical slice.

The present standalone HTML-insertion generation behavior is temporary rather than permanent architecture. It is not a separate mixed-document assembly route. Because the system is not yet in operation, this compatibility-markup source may be replaced after component coverage and weak-model behavior justify removal; removal is a later explicit decision, not an MVP assumption.

## Safe Extension Procedure

A new component, or a semantic expansion of an existing one, follows this gate in order:

1. Define one semantic responsibility in relationship terms, not markup or visual-style terms.
2. Compare its capabilities with existing components. Resolve overlap by narrowing responsibilities or documenting why a distinct component is necessary.
3. Provide the MVP-minimum registry metadata, common-envelope use, component payload schema, stable-ID rules, and selection capabilities.
4. Define static representation, internal accessibility semantics, responsive preservation of meaning, and any optional enhancement without requiring interaction.
5. Define fallback/degradation behavior that retains all core semantics.
6. Identify trusted renderer and asset ownership. Review CSS namespace, script necessity, CSP behavior, external-reference absence, dependencies, and controlled-slot eligibility.
7. Define IR, manifest, asset, accessibility, relationship, and final DOM checker rules, including traceability from every required semantic input.
8. Demonstrate use through the existing common registry, composition, flattening, and checker route; do not add a parallel route.
9. Add the registry entry only after its contract, renderer identity, asset hashes, and checker rules are available together.
10. Admit the component to deterministic candidate narrowing only after the full gate passes.

Prohibited shortcuts include registry placeholders with no checker rules, HTML fragments presented as semantic components, arbitrary generated assets, renderer-specific fields in the common IR, silent compatibility fallback, and component-specific changes to unrelated fixed regions.

Version changes that alter accepted relationships, required inputs, rendered semantic traceability, or safety rules require a contract-version review. Pure visual changes remain renderer-owned but still require trusted asset hash updates and verification that static, accessibility, responsive, and checker invariants remain true.

## Deferred Visual Design

The foundation deliberately defers:

- the detailed grid, grouping, emphasis, and density treatment for `matrix`;
- connector geometry, node shapes, branch layout, and spatial treatment for `flow`;
- color, typography, shape, spacing, iconography, and emphasis as a shared visual language;
- aesthetic breakpoint tuning beyond preserving responsive meaning and reading order;
- animation and transition language;
- rich interaction, filtering, cross-highlighting, and cross-component transitions;
- free-coordinate layouts or decorative motion.

Deferral does not mean the foundation is visually neutral in its consequences. The IR deliberately excludes DOM, CSS, and coordinates; semantic responsibilities are stable; renderers are replaceable; skeleton tokens are shareable; and static accessibility is mandatory. These decisions leave room for a later beautiful and intuitive language without coupling that language to authoring or safety contracts.

The first slice needs only a minimal static treatment that makes relationships unambiguous. The cadence of later exploration remains a non-blocking open question: it may proceed component by component, or begin with a common visual grammar spanning `matrix` and `flow`.

## Risks, Decisions, and Open Questions

### Decisions

- Adopt the minimal staged combination of limited IR, registry, trusted generation-time modules, and flattening.
- Make declarative IR the canonical initial authoring surface; retain old standalone HTML insertion only as a temporary source of labelled compatibility markup.
- Select components by deterministic narrowing followed by explicit author/generator selection with a recorded, checker-verifiable semantic reason.
- Keep the registry a discovery and contract index; defer heuristic routing and override.
- Limit the first vertical slice to `matrix` and `flow` through one common route.
- Keep component boundaries semantic, not file-, fragment-, or CSS-based.
- Allow component-local styles and optional scripts only as trusted, allowlisted, hash-verified assets placed in controlled skeleton slots.
- Preserve hashing and validation for all other fixed regions, and prohibit ordinary generated content from injecting CSS/JavaScript or editing fixed regions.
- Require static-first rendering, an unoperated core path, certainty, sources, captions, accessibility, and responsive preservation of meaning.
- Label compatibility and weak-model degradation explicitly and continue final HTML validation on those outputs.
- Permit canonical `matrix`/`flow` instances and compatibility sections to coexist in one explainer and converge through one composition/flattening final-assembly route; compatibility sections bypass canonical selection, registry resolution, and trusted component renderer execution.
- Defer all other formats, auto-routing, rich interaction, and detailed visual-language work.

### Risks and mitigations

- **Prematurely general IR:** Limit the schema to the common envelope and data exercised by `matrix` and `flow`; add later relationships through the extension gate.
- **Registry becomes an implicit router:** Exclude ranking and heuristic metadata from the MVP and require explicit selection.
- **Skeleton centralization reappears in another form:** Review every component by semantic responsibility and keep component rendering logic outside the document shell.
- **Controlled slots weaken the safety boundary:** Permit only registry/manifest-declared, allowlisted, hash-verified trusted assets; preserve all other fixed-region checks.
- **Render manifest drifts from DOM:** Require final traceability checks for semantic IDs, relationships, assets, and fallback state.
- **Compatibility becomes permanent or hides failures:** Require provenance, deliberate entry, and per-component promotion criteria; never silently fall back.
- **Weak models fail the IR:** Keep the IR small, make selection explicit and deterministic, return bounded diagnostics, and retain the labelled compatibility path.
- **Renderer visuals distort semantics:** Validate explicit edge direction, matrix membership, reading order, semantic ID coverage, and static fallback in the final document.
- **Optional JavaScript becomes required:** Treat absence of script as a standard checker condition and forbid enhancement code from owning core content.
- **Extension cost grows across schema, renderer, and checker:** Use one extension gate and require all contract pieces to land together instead of maintaining partial registry entries.

### Non-blocking open question

After the foundation is proven, should visual-language exploration proceed component by component or as one shared grammar across `matrix` and `flow`? This affects design cadence only. It does not block the foundation architecture, first vertical slice, checker contracts, or migration.

ADOPTED: I-1 — Defined multiple matching candidates as a normal selection result, distinguished them from invalid/under-specified/no-match declarations (including an unregistered matrix+flow combined responsibility), and aligned the selection return, checker behavior, and bounded diagnostics.
ADOPTED: I-R2-1 — Defined mixed canonical/compatibility explainers and one shared composition/flattening final-assembly route; compatibility markup comes from the old standalone HTML-insertion generator, bypasses canonical selection/registry/renderer execution, enters only the controlled content slot, and retains provenance and existing safety checks.
STATUS: complete
