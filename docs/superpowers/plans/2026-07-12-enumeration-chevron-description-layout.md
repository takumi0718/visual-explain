# Enumeration / Chevron Description Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render enumeration and chevron concepts separately from optional explanations, placing vertical explanations on the right and horizontal explanations below while requiring a real concept title in number mode.

**Architecture:** Keep the canonical IR schema, dataclasses, component IDs, and component versions unchanged. Tighten contextual validation, split each renderer's semantic item into a concept child plus optional sibling explanation, move shape styling to the concept child, and strengthen artifact checking with a DOM-structure parser.

**Tech Stack:** Python 3 standard library, `html.parser.HTMLParser`, token-only CSS, JSON fixtures, pytest, `build_explainer.py`, and `check.sh`.

## Global Constraints

- Approved spec: `docs/superpowers/specs/2026-07-12-enumeration-chevron-description-layout-design.md`.
- Do not modify `skills/visual-explain/assets/skeleton.html` or any skeleton token.
- Do not add IR fields, author-controlled placement, a component ID, or a component version.
- List/vertical places description on the right; columns/horizontal places it below.
- `blockContent: "number"` requires non-blank `title` on every item/step; description never substitutes for title.
- `blockContent: "label"` keeps required `label` and forbidden `title`.
- Description remains all-present or all-absent; existing count and length limits remain unchanged.
- Semantic ID stays on the outer item; takeaway outline moves to the concept child.
- Vertical chevron loop rail owns only the concept column.
- Output stays static: no script, inline style, external reference, author HTML, or coordinates.
- CSS uses existing tokens only. Recompute strict SHA-256 digests after CSS edits.
- Every task follows red → green → focused regression → commit. During execution, request explicit approval before every commit; push and PR require separate approval.

## File Responsibilities

- `skills/visual-explain/scripts/ve_components/validation.py`: contextual authoring rules.
- `skills/visual-explain/scripts/ve_components/renderers/enumeration.py`: enumeration semantic markup.
- `skills/visual-explain/scripts/ve_components/renderers/chevron.py`: chevron markup and loop behavior.
- `skills/visual-explain/assets/components/enumeration.css`: enumeration layout and appearance.
- `skills/visual-explain/assets/components/chevron.css`: chevron layout, shapes, and loop rail.
- `skills/visual-explain/scripts/ve_components/checker.py`: artifact-only DOM checks.
- `skills/visual-explain/assets/components/registry.json`: exact CSS digests.
- `skills/visual-explain/scripts/tests/`: validation, renderer, checker, build, and visual fixtures.
- `skills/visual-explain/SKILL.md`, `skills/visual-explain/references/patterns.md`, `skills/visual-explain/references/design-system.md`, and canonical specs: author-facing contract.

---

### Task 1: Tighten the Concept Validation Contract

**Files:**
- Modify: `skills/visual-explain/scripts/tests/test_enumeration_renderer.py`
- Modify: `skills/visual-explain/scripts/tests/test_chevron_renderer.py`
- Modify: `skills/visual-explain/scripts/ve_components/validation.py`
- Modify: `skills/visual-explain/scripts/tests/component-valid-chevron-horizontal.json`
- Delete: `skills/visual-explain/scripts/tests/component-bad-chevron-title-in-horizontal.json`
- Create: `skills/visual-explain/scripts/tests/component-bad-chevron-missing-title-horizontal.json`
- Modify: `skills/visual-explain/scripts/tests/test_component_checker.py`
- Modify: `skills/visual-explain/scripts/tests/fixtures.md`

**Interfaces:**
- Consumes: `_validate_enumeration(...) -> EnumerationPayload | None` and `_validate_chevron(...) -> ChevronPayload | None`.
- Produces: invariant `blockContent == "number"` implies non-blank `title` with length at most 30 for every orientation.

- [ ] **Step 1: Write the failing enumeration validation test**

Add imports for `ContractError` and `validate_canonical_section`, then add:

```python
def test_number_mode_requires_title_even_with_description(self) -> None:
    raw = json.loads((TESTS / "component-valid-enumeration.json").read_text("utf-8"))
    item = raw["sections"][0]["ir"]["enumeration"]["items"][0]
    item.pop("title")
    item["description"] = ["説明だけではコンセプトにならない"]
    with self.assertRaises(ContractError) as ctx:
        validate_canonical_section(raw["sections"][0]["ir"])
    self.assertIn(
        "enumeration_structure_violation",
        {d.code for d in ctx.exception.diagnostics},
    )
```

Run:

```bash
cd skills/visual-explain/scripts
python3 -m pytest tests/test_enumeration_renderer.py -q
```

Expected: FAIL because description currently substitutes for title.

- [ ] **Step 2: Replace obsolete chevron tests**

Replace `test_rejects_title_in_horizontal_orientation` and `test_rejects_horizontal_number_mode_without_descriptions` with:

```python
def test_horizontal_number_accepts_titles_with_descriptions(self) -> None:
    ir = _base_ir(orientation="horizontal", steps=[
        {"id": "s1", "title": "計画", "description": ["要件を確定する"]},
        {"id": "s2", "title": "準備", "description": ["実施条件を整える"]},
        {"id": "s3", "title": "実施", "description": ["計画を実行する"]},
    ])
    result = validate_raw(ir)
    self.assertEqual([s.title for s in result.chevron.steps], ["計画", "準備", "実施"])

def test_horizontal_number_accepts_titles_without_descriptions(self) -> None:
    validate_raw(_base_ir(orientation="horizontal", steps=[
        {"id": "s1", "title": "計画"},
        {"id": "s2", "title": "準備"},
        {"id": "s3", "title": "実施"},
    ]))

def test_horizontal_number_rejects_description_without_title(self) -> None:
    expect_violation(_base_ir(orientation="horizontal", steps=[
        {"id": "s1", "description": ["説明1"]},
        {"id": "s2", "description": ["説明2"]},
        {"id": "s3", "description": ["説明3"]},
    ]))

def test_vertical_number_rejects_description_without_title(self) -> None:
    expect_violation(_base_ir(steps=[
        {"id": "s1", "description": ["説明1"]},
        {"id": "s2", "description": ["説明2"]},
    ]))
```

Delete `test_number_mode_loop_falls_back_to_ordinal_when_no_label_or_title`; that IR becomes invalid. Keep the renderer's ordinal fallback as defensive behavior.

Run `python3 -m pytest tests/test_chevron_renderer.py -q`.

Expected: FAIL because horizontal title is prohibited and description still substitutes for title.

- [ ] **Step 3: Implement the minimum validator change**

Use this number-mode branch in `_validate_enumeration`:

```python
if label is not None:
    col.add(ENUMERATION_STRUCTURE_VIOLATION, "blockContent:number では label は禁止です", p)
if not _nonblank_str(title):
    col.add(ENUMERATION_STRUCTURE_VIOLATION, "blockContent:number では title が必須です", p)
elif len(str(title)) > 30:
    col.add(ENUMERATION_STRUCTURE_VIOLATION, "title は30字以内です", p)
```

Remove the horizontal-title prohibition from `_validate_chevron` and use:

```python
if label is not None:
    col.add(CHEVRON_STRUCTURE_VIOLATION, "blockContent:number では label は禁止です", p)
if not _nonblank_str(title):
    col.add(CHEVRON_STRUCTURE_VIOLATION, "blockContent:number では title が必須です", p)
elif len(str(title)) > 30:
    col.add(CHEVRON_STRUCTURE_VIOLATION, "title は30字以内です", p)
```

Do not alter description all-or-none, line, character, count, loop, or capability checks.

- [ ] **Step 4: Migrate fixtures and rejection registration**

Change `component-valid-chevron-horizontal.json` to:

```json
[
  {"id": "h1", "title": "要件確定", "description": ["要件を確定する"]},
  {"id": "h2", "title": "設計確認", "description": ["設計をレビューする"]},
  {"id": "h3", "title": "実装", "description": ["実装を完了する"]},
  {"id": "h4", "title": "検証", "description": ["検証を通過する"]}
]
```

Delete the obsolete title-prohibited bad fixture. Create `component-bad-chevron-missing-title-horizontal.json` with three described steps where one lacks title. Replace the filename in `LayerTwoBuildRejectionTest.BAD` and in `fixtures.md`.

Run:

```bash
python3 -m pytest tests/test_enumeration_renderer.py tests/test_chevron_renderer.py tests/test_v2_core.py tests/test_component_checker.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit after approval**

Stage only Task 1 files and commit with:

```bash
git commit -m "fix(visual-explain): require concepts in numbered blocks"
```

---

### Task 2: Separate Enumeration Concept and Description

**Files:**
- Modify: `skills/visual-explain/scripts/tests/test_enumeration_renderer.py`
- Modify: `skills/visual-explain/scripts/ve_components/renderers/enumeration.py`
- Modify: `skills/visual-explain/assets/components/enumeration.css`
- Modify: `skills/visual-explain/assets/components/registry.json`
- Modify: `skills/visual-explain/scripts/tests/component-valid-enumeration.json`
- Modify: `skills/visual-explain/scripts/tests/component-valid-enumeration-columns.json`
- Modify: `skills/visual-explain/scripts/tests/enumeration-doc.html`

**Interfaces:**
- Produces outer `.ve-enum-block[data-ve-semantic-id]`, direct child `.ve-enum-concept`, and optional direct sibling `.ve-enum-description`.
- `ve-takeaway-target` moves to the concept child; `data-ve-takeaway` remains on the outer item.

- [ ] **Step 1: Add described valid fixtures**

Add a description to every item in both valid fixtures. Keep titles in list/number and labels in columns/label. Use one line per item so the fixture isolates placement rather than density limits.

- [ ] **Step 2: Write failing DOM-separation tests**

```python
def test_description_is_outside_vertical_concept(self) -> None:
    _, result = render_fixture("component-valid-enumeration.json")
    concepts = re.findall(r'<div class="[^"]*ve-enum-concept[^"]*">(.*?)</div>', result.markup, re.DOTALL)
    self.assertEqual(len(concepts), 3)
    self.assertEqual(result.markup.count('class="ve-enum-description"'), 3)
    self.assertTrue(all("ve-enum-description" not in concept for concept in concepts))

def test_columns_emit_concept_then_description(self) -> None:
    _, result = render_fixture("component-valid-enumeration-columns.json")
    self.assertRegex(result.markup, r've-enum-concept[^>]*>.*?</div><ul class="ve-enum-description">')

def test_concept_only_emits_no_description_region(self) -> None:
    raw = json.loads((TESTS / "component-valid-enumeration.json").read_text("utf-8"))
    for item in raw["sections"][0]["ir"]["enumeration"]["items"]:
        item.pop("description")
    ir = validate_canonical_section(raw["sections"][0]["ir"])
    result = render_enumeration(CanonicalSection(ir=ir), ENUM_DEF)
    self.assertNotIn("ve-enum-description", result.markup)
    self.assertNotIn("ve-enum-has-description", result.markup)
```

Add a takeaway test asserting `data-ve-takeaway` on the outer item and `ve-takeaway-target` on `.ve-enum-concept` only.

Run `python3 -m pytest tests/test_enumeration_renderer.py -q`.

Expected: FAIL because there is no concept child and description remains inside the shaped element.

- [ ] **Step 3: Split enumeration markup**

Use this renderer structure:

```python
concept_classes = ["ve-enum-concept"]
if item.id in takeaway:
    concept_classes.append("ve-takeaway-target")
concept_html = f'<div class="{" ".join(concept_classes)}">{heading}</div>'

description_html = ""
if item.description:
    lines = "".join(f"<li>{_esc(line)}</li>" for line in item.description)
    description_html = f'<ul class="ve-enum-description">{lines}</ul>'

blocks.append(
    f'<li class="ve-enum-block" data-ve-semantic-id="{_esc(item.id)}"{takeaway_attr}>'
    f'{concept_html}{description_html}{emphasis_html}</li>'
)
```

Append `ve-enum-has-description` to the list classes only when descriptions exist.

- [ ] **Step 4: Move shape CSS to `.ve-enum-concept`**

Implement:

```css
[data-ve-component="enumeration"] .ve-enum-block { min-width: 0; font-size: var(--fs-figure); }
[data-ve-component="enumeration"] .ve-enum-concept {
  background: var(--text-dim); color: var(--bg); padding: var(--space-2);
  border-radius: var(--radius); text-align: center;
}
[data-ve-component="enumeration"] .ve-enum-list-centered.ve-enum-has-description .ve-enum-block {
  display: grid; grid-template-columns: minmax(8rem, 14rem) minmax(12rem, 1fr);
  align-items: center; gap: var(--space-2); margin-bottom: var(--space-2);
}
[data-ve-component="enumeration"] .ve-enum-columns .ve-enum-block {
  display: flex; flex: 1 1 10rem; min-width: 8rem; max-width: 14rem;
  flex-direction: column; margin: 0;
}
[data-ve-component="enumeration"] .ve-enum-description {
  margin: var(--space-1) 0 0; padding-left: var(--space-3);
  color: var(--text); font-size: var(--fs-small); text-align: left;
}
```

Keep concept-only list centering. At `40rem`, retain the right-side explanation for authored list layout and stack columns units while keeping explanation below.

- [ ] **Step 5: Update digest, build, and verify**

```bash
cd skills/visual-explain/scripts
shasum -a 256 ../assets/components/enumeration.css
python3 -m pytest tests/test_enumeration_renderer.py tests/test_component_contract.py -q
python3 build_explainer.py --assembly tests/component-valid-enumeration.json --output tests/enumeration-doc.html
bash check.sh tests/enumeration-doc.html
```

Copy the exact digest into the enumeration asset entry in `registry.json`. Expected: tests PASS, build `OK:`, checker `PASS`.

- [ ] **Step 6: Commit after approval**

Stage only Task 2 files and commit with:

```bash
git commit -m "feat(visual-explain): separate enumeration explanations"
```

---

### Task 3: Separate Chevron Concept and Description

**Files:**
- Modify: `skills/visual-explain/scripts/tests/test_chevron_renderer.py`
- Modify: `skills/visual-explain/scripts/ve_components/renderers/chevron.py`
- Modify: `skills/visual-explain/assets/components/chevron.css`
- Modify: `skills/visual-explain/assets/components/registry.json`
- Modify: `skills/visual-explain/scripts/tests/component-valid-chevron.json`
- Modify: `skills/visual-explain/scripts/tests/component-valid-chevron-horizontal.json`
- Modify: `skills/visual-explain/scripts/tests/component-valid-chevron-loop.json`
- Modify: `skills/visual-explain/scripts/tests/chevron-doc.html`
- Modify: `skills/visual-explain/scripts/tests/chevron-horizontal-doc.html`

**Interfaces:**
- Produces outer `.ve-chevron-step[data-ve-semantic-id]`, direct child `.ve-chevron-concept`, and optional direct sibling `.ve-chevron-description`.
- Loop rail remains a sibling of the ordered list inside `.ve-chevron-centered-column` and is positioned against the concept column.

- [ ] **Step 1: Write failing DOM and loop-layout tests**

```python
def test_horizontal_title_is_in_concept_and_description_is_outside(self) -> None:
    ir, result = render_fixture("component-valid-chevron-horizontal.json")
    concepts = re.findall(r'<div class="[^"]*ve-chevron-concept[^"]*">(.*?)</div>', result.markup, re.DOTALL)
    self.assertEqual(len(concepts), len(ir.chevron.steps))
    self.assertEqual(result.markup.count('class="ve-chevron-description"'), len(ir.chevron.steps))
    for step, concept in zip(ir.chevron.steps, concepts):
        self.assertIn(step.title, concept)
        self.assertNotIn("ve-chevron-description", concept)

def test_vertical_description_is_sibling_of_concept(self) -> None:
    _, result = render_fixture("component-valid-chevron.json")
    self.assertRegex(result.markup, r've-chevron-concept[^>]*>.*?</div><ul class="ve-chevron-description">')

def test_loop_wrapper_keeps_rail_outside_description(self) -> None:
    _, result = render_fixture("component-valid-chevron-loop.json")
    self.assertRegex(
        result.markup,
        r'<div class="ve-chevron-centered-column"><div class="ve-chevron-loop-rail".*?</div><ol',
    )
```

Also add tests for concept-only output and takeaway ownership matching Task 2.

Run `python3 -m pytest tests/test_chevron_renderer.py -q`.

Expected: FAIL because no concept child exists and description is inside the shaped step.

- [ ] **Step 2: Split chevron markup**

Use:

```python
concept_classes = ["ve-chevron-concept"]
if step.id in takeaway:
    concept_classes.append("ve-takeaway-target")
concept_html = f'<div class="{" ".join(concept_classes)}">{heading}</div>'

description_html = ""
if step.description:
    lines = "".join(f"<li>{_esc(line)}</li>" for line in step.description)
    description_html = f'<ul class="ve-chevron-description">{lines}</ul>'

blocks.append(
    f'<li class="ve-chevron-step" data-ve-semantic-id="{_esc(step.id)}"{takeaway_attr}>'
    f'{concept_html}{description_html}{emphasis_html}</li>'
)
```

Append `ve-chevron-has-description` to the ordered-list classes only when descriptions exist. Preserve caption, summary, notes, loop sentence, manifest, and no-script behavior.

- [ ] **Step 3: Move chevron geometry to the concept child**

Implement these selectors and retain existing token values:

```css
[data-ve-component="chevron"] .ve-chevron-step { min-width: 0; font-size: var(--fs-figure); }
[data-ve-component="chevron"] .ve-chevron-concept {
  background: var(--text-dim); color: var(--bg); padding: var(--space-2);
  text-align: center;
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 1rem), 50% 100%, 0 calc(100% - 1rem));
}
[data-ve-component="chevron"] .ve-chevron-centered.ve-chevron-has-description .ve-chevron-step {
  display: grid; grid-template-columns: minmax(8rem, 14rem) minmax(12rem, 1fr);
  align-items: center; gap: var(--space-2); margin-bottom: var(--space-2);
}
[data-ve-component="chevron"] .ve-chevron-horizontal .ve-chevron-step {
  display: flex; flex: 1 1 8rem; min-width: 6rem; max-width: 12rem;
  flex-direction: column; margin: 0;
}
[data-ve-component="chevron"] .ve-chevron-horizontal .ve-chevron-concept {
  clip-path: polygon(0.75rem 0, calc(100% - 0.75rem) 0, 100% 50%, calc(100% - 0.75rem) 100%, 0.75rem 100%, 0 50%);
}
[data-ve-component="chevron"] .ve-chevron-description {
  margin: var(--space-1) 0 0; padding-left: var(--space-3);
  color: var(--text); font-size: var(--fs-small); text-align: left;
}
```

Move both vertical and horizontal clip paths from the outer step to `.ve-chevron-concept`. Keep adjacent concept continuity without overlapping description text. At `40rem`, stack each complete horizontal unit and keep its description below. Position the vertical loop rail against the concept column, not the explanation width.

- [ ] **Step 4: Update digest, build, and verify**

```bash
cd skills/visual-explain/scripts
shasum -a 256 ../assets/components/chevron.css
python3 -m pytest tests/test_chevron_renderer.py tests/test_component_contract.py -q
python3 build_explainer.py --assembly tests/component-valid-chevron.json --output tests/chevron-doc.html
python3 build_explainer.py --assembly tests/component-valid-chevron-horizontal.json --output tests/chevron-horizontal-doc.html
bash check.sh tests/chevron-doc.html
bash check.sh tests/chevron-horizontal-doc.html
```

Copy the exact digest into the chevron asset entry. Expected: tests PASS, both builds `OK:`, both checks `PASS`.

- [ ] **Step 5: Visually verify the component states**

Inspect described vertical/horizontal enumeration, described vertical/horizontal chevron, concept-only enumeration, concept-only chevron, and described vertical loop chevron at desktop and below `40rem`. Verify association, wrapping, chevron continuity, no description overlap, concept-only collapse, loop ownership, and no page-level horizontal overflow. Add a focused regression before any corrective CSS change.

- [ ] **Step 6: Commit after approval**

Stage only Task 3 files and commit with:

```bash
git commit -m "feat(visual-explain): separate chevron explanations"
```

---

### Task 4: Enforce Separation in the Artifact Checker

**Files:**
- Modify: `skills/visual-explain/scripts/tests/test_component_checker.py`
- Modify: `skills/visual-explain/scripts/ve_components/checker.py`

**Interfaces:**
- Produces `_ItemLayoutParser(outer_class, concept_class, description_class)` and one structural record per semantic outer item.
- Consumed by `_check_enumeration_artifact` and `_check_chevron_artifact`.

- [ ] **Step 1: Write failing artifact tamper tests**

Add tests that build a valid document and mutate exactly one condition:

```python
def test_enumeration_description_nested_in_concept_fails(self) -> None:
    doc = build("component-valid-enumeration.json")
    tampered = doc.replace(
        '</div><ul class="ve-enum-description">',
        '<ul class="ve-enum-description">',
        1,
    ).replace('</ul></li>', '</ul></div></li>', 1)
    self.assertIn("artifact_semantic_mismatch", self.diags(tampered))

def test_chevron_missing_concept_child_fails(self) -> None:
    doc = build("component-valid-chevron.json")
    tampered = doc.replace('class="ve-chevron-concept"', 'class="ve-chevron-concept-missing"', 1)
    self.assertIn("artifact_semantic_mismatch", self.diags(tampered))

def test_enumeration_duplicate_concept_child_fails(self) -> None:
    doc = build("component-valid-enumeration.json")
    marker = '<div class="ve-enum-concept">'
    tampered = doc.replace(marker, marker + '<div class="ve-enum-concept">duplicate</div>', 1)
    self.assertIn("artifact_semantic_mismatch", self.diags(tampered))

def test_chevron_partial_descriptions_fail(self) -> None:
    doc = build("component-valid-chevron.json")
    tampered = doc.replace('<ul class="ve-chevron-description">', '<ul class="ve-chevron-description-missing">', 1)
    self.assertIn("artifact_semantic_mismatch", self.diags(tampered))
```

Add one test moving `data-ve-semantic-id` from the outer item to its concept child. Run `python3 -m pytest tests/test_component_checker.py -q`.

Expected: nested, duplicate, or partial layouts pass incorrectly under the count-only checker.

- [ ] **Step 2: Add the structural parser**

Add `from dataclasses import dataclass`, then define:

```python
@dataclass
class _ItemLayoutRecord:
    has_semantic_id: bool = False
    concept_count: int = 0
    concept_not_direct: bool = False
    description_count: int = 0
    description_nested_in_concept: bool = False


class _ItemLayoutParser(HTMLParser):
    def __init__(self, outer_class: str, concept_class: str, description_class: str) -> None:
        super().__init__(convert_charrefs=True)
        self.outer_class = outer_class
        self.concept_class = concept_class
        self.description_class = description_class
        self.records: list[_ItemLayoutRecord] = []
        self._stack: list[tuple[str, frozenset[str]]] = []
        self._active: list[tuple[int, _ItemLayoutRecord]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        classes = _class_tokens(attrs)
        values = {k.lower(): (v or "") for k, v in attrs}
        if tag == "li" and self.outer_class in classes:
            record = _ItemLayoutRecord(bool(values.get("data-ve-semantic-id")))
            self.records.append(record)
            self._active.append((len(self._stack), record))
        elif self._active:
            outer_depth, record = self._active[-1]
            direct_child = len(self._stack) == outer_depth + 1
            if self.concept_class in classes:
                record.concept_count += 1
                record.concept_not_direct = record.concept_not_direct or not direct_child
            if self.description_class in classes:
                record.description_count += 1
                inside_concept = any(
                    self.concept_class in ancestor_classes
                    for _tag, ancestor_classes in self._stack[outer_depth + 1:]
                )
                record.description_nested_in_concept = inside_concept or not direct_child
        if tag not in _VOID_TAGS:
            self._stack.append((tag, classes))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                break
        while self._active and len(self._stack) <= self._active[-1][0]:
            self._active.pop()
```

Add `handle_startendtag` only if a red test demonstrates a relevant self-closing tag; current component contract emits none for these three classes.

- [ ] **Step 3: Apply one shared layout check**

```python
def _check_item_layout(body: str, *, component: str, outer: str, concept: str, description: str) -> list[Diagnostic]:
    parser = _ItemLayoutParser(outer, concept, description)
    parser.feed(body)
    parser.close()
    diagnostics: list[Diagnostic] = []
    counts = [record.description_count for record in parser.records]
    for index, record in enumerate(parser.records, start=1):
        if not record.has_semantic_id:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          f"{component} 項目 {index} の外側に意味 ID がありません"))
        if record.concept_count != 1 or record.concept_not_direct:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          f"{component} 項目 {index} の concept は1個必要です"))
        if record.description_count > 1 or record.description_nested_in_concept:
            diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                          f"{component} 項目 {index} の description は concept の兄弟である必要があります"))
    if any(counts) and not all(count == 1 for count in counts):
        diagnostics.append(Diagnostic(ARTIFACT_SEMANTIC_MISMATCH,
                                      f"{component} の description は全有または全無である必要があります"))
    return diagnostics
```

Call it from both component artifact checks with their three exact classes. Retain existing count, semantic-ID, orientation, and loop checks.

Run:

```bash
python3 -m pytest tests/test_component_checker.py tests/test_controlled_slots.py tests/test_mixed_assembly.py -q
bash check.sh tests/enumeration-doc.html
bash check.sh tests/chevron-doc.html
bash check.sh tests/chevron-horizontal-doc.html
```

Expected: PASS without a new diagnostic code.

- [ ] **Step 4: Commit after approval**

Stage only checker and checker tests, then commit with:

```bash
git commit -m "test(visual-explain): enforce concept explanation separation"
```

---

### Task 5: Synchronize Documentation and Run the Full Gate

**Files:**
- Modify: `skills/visual-explain/SKILL.md`
- Modify: `skills/visual-explain/references/patterns.md`
- Modify: `skills/visual-explain/references/design-system.md`
- Modify: `docs/superpowers/specs/2026-07-11-visual-explain-canonical-v2-components.md`
- Modify: `skills/visual-explain/scripts/tests/fixtures.md`
- Modify: `skills/visual-explain/scripts/tests/enumeration-doc.html`
- Modify: `skills/visual-explain/scripts/tests/chevron-doc.html`
- Modify: `skills/visual-explain/scripts/tests/chevron-horizontal-doc.html`
- Track: `docs/superpowers/specs/2026-07-12-enumeration-chevron-description-layout-design.md`
- Track: `docs/superpowers/plans/2026-07-12-enumeration-chevron-description-layout.md`

**Interfaces:**
- Produces one consistent author-facing contract and generated artifacts matching final registry digests.

- [ ] **Step 1: Replace obsolete normative rules**

In the 2026-07-11 canonical v2 spec, `SKILL.md`, `patterns.md`, and `design-system.md`, replace:

- number mode may use title or description as minimum content;
- horizontal chevron forbids title;
- horizontal number chevron requires description because title is forbidden;
- description appears inside the concept block.

With:

```markdown
- `blockContent: "number"` requires `title` on every item/step; the generated number is an identifier, not the concept.
- `description` is optional supporting detail and remains all-present or all-absent.
- list/vertical places description to the right of the concept.
- columns/horizontal places description below the concept.
- horizontal number chevrons render number + title in the shape and optional description below.
```

Do not change component selection, density limits, loop topology, skeleton tokens, or unrelated component rules.

- [ ] **Step 2: Update fixture documentation and design status**

Remove every reference to `component-bad-chevron-title-in-horizontal.json` and document its missing-title replacement. Keep the approved 2026-07-12 spec requirements unchanged.

Run:

```bash
rg -n 'horizontal.*title.*禁止|title/description|title か description|component-bad-chevron-title-in-horizontal' skills/visual-explain docs/superpowers/specs --glob '*.md' --glob '*.json'
```

Expected: no active obsolete rule. Historical text may remain only when explicitly labeled superseded.

- [ ] **Step 3: Regenerate checked documents**

```bash
cd skills/visual-explain/scripts
python3 build_explainer.py --assembly tests/component-valid-enumeration.json --output tests/enumeration-doc.html
python3 build_explainer.py --assembly tests/component-valid-chevron.json --output tests/chevron-doc.html
python3 build_explainer.py --assembly tests/component-valid-chevron-horizontal.json --output tests/chevron-horizontal-doc.html
bash check.sh tests/enumeration-doc.html
bash check.sh tests/chevron-doc.html
bash check.sh tests/chevron-horizontal-doc.html
```

Expected: three `OK:` build lines and three `PASS` check results.

- [ ] **Step 4: Run the complete verification gate**

```bash
cd skills/visual-explain/scripts
python3 -m pytest tests -q
bash check.sh --selftest
cd ../../..
git diff --check
git diff -- skills/visual-explain/assets/skeleton.html
shasum -a 256 skills/visual-explain/assets/components/enumeration.css
shasum -a 256 skills/visual-explain/assets/components/chevron.css
```

Expected:

- pytest reports all tests passed;
- selftest reports zero failed;
- `git diff --check` prints nothing;
- skeleton diff prints nothing;
- both digests exactly match `registry.json`.

- [ ] **Step 5: Perform final visual QA**

Open the three generated documents and any concept-only/loop variants created during Tasks 2–3. Check light and dark themes at desktop and below `40rem`. Record pass/fail for:

- vertical explanation on the right;
- horizontal explanation below the matching concept;
- number plus title inside horizontal chevrons;
- no empty region in concept-only output;
- description text does not overlap;
- horizontal chevron continuity remains legible;
- loop rail follows only the concept column;
- no page-level horizontal overflow.

If a defect appears, return to its task, add a failing regression, make the smallest correction, recompute the CSS digest, regenerate all documents, and repeat the full gate.

- [ ] **Step 6: Commit documentation and generated artifacts after approval**

Stage only Task 5 documentation, plan/spec, fixture registry, and regenerated documents. Commit with:

```bash
git commit -m "docs(visual-explain): document external explanation layout"
```

## Completion Gate

Implementation is complete only when:

- all five tasks have independent green evidence;
- every acceptance criterion in the approved spec maps to a test or recorded visual check;
- no obsolete title/description rule remains active;
- CSS digests match the registry exactly;
- skeleton bytes are unchanged;
- full pytest and selftest pass;
- desktop, narrow-width, light, and dark checks pass;
- commit, push, PR, and merge remain separately user-authorized actions.

## Execution Evidence — 2026-07-12

- Branch: `feat/enumeration-chevron-description-layout`.
- Focused checker integration: `147 passed, 49 subtests passed`.
- Full suite: `515 passed, 125 subtests passed`.
- Legacy selftest: `25 passed, 0 failed`.
- `enumeration-doc.html`, `chevron-doc.html`, `chevron-horizontal-doc.html`, and a temporary loop build all passed `check.sh`.
- The Browser runtime reported no available browser backends, so desktop/narrow-width light/dark visual inspection remains pending. DOM ownership, concept-only collapse, responsive selectors, loop ordering, and overflow-sensitive structure are covered by automated tests and static artifact checks.
