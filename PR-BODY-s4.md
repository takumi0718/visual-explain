# PR: canonical-v2-s4-logic-tree → canonical-v2

## Ten-step extension gate checklist

- [x] 1. `component-vocabulary.json` — `logic-tree`/`hierarchical-decomposition`/`mece-decomposition`
- [x] 2. `component-ir.schema.json` enums + `logicTreePayload` + oneOf×7
- [x] 3. No new common IR fields — payload dispatch addition only (`logic-tree` JSON key → `logic_tree` Python attribute)
- [x] 4. `renderers/logic_tree.py` + manifest consumes all semantic IDs (root ∪ branches ∪ leaves)
- [x] 5. `assets/components/logic-tree.css` (tokens only, grid+border connectors, responsive stack)
- [x] 6. digest `392189a53a978812139170109f88a1846863b141a338e6240719a9bea8309dd2`
- [x] 7. `TRUSTED_RENDERERS["logic-tree@1"]`
- [x] 8. registry entry + `logic-tree-structure` checker rule
- [x] 9. four-layer checks + bad fixtures (JSON ×5 + bad structure HTML)
- [x] 10. build + full pytest + `check.sh --selftest` + docs sync

## S4 logic-tree specifics

- **Structure:** root + 2–4 branches; each branch 0–2 leaves; depth fixed root→branch→leaf
- **Labels:** root ≤20 / branch ≤16 / leaf text ≤40
- **Layout:** `ve-logic-tree-layout-horizontal` (root left, shared `ve-logic-tree-spine`, per-branch `ve-logic-tree-connector`); root stem `ve-logic-tree-root-stem` joins root to spine
- **Connectors:** renderer-owned spine + branch connectors (grid+border, `aria-hidden`, no `data-ve-from/to` / `data-connect`); connector count == branch count
- **Notes:** `ve-logic-tree-notes` DOM contract; `generated_relationship_ids=()`

## Test evidence

```text
$ cd skills/visual-explain/scripts && python3 -m pytest tests -q
407 passed, 100 subtests passed in ~3.8s

$ python3 build_explainer.py --assembly tests/component-valid-logic-tree.json --output tests/logic-tree-doc.html
OK: tests/logic-tree-doc.html

$ bash check.sh tests/logic-tree-doc.html
PASS

$ bash check.sh --selftest
selftest: 25 passed, 0 failed

$ git diff HEAD -- '**/skeleton.html'
(empty — skeleton byte-identical)
```

## Light/dark inspection artifacts

- `skills/visual-explain/scripts/tests/logic-tree-doc.html` (root + 3 branches, mixed 0–2 leaves)

## Docs touched

- `references/patterns.md` — selection guide (logic-tree vs decision-tree, MECE-not-machine-checkable) + IR example
- `references/design-system.md` — logic-tree 枝4・leaf各2 cap
- `SKILL.md` — canonical components list includes logic-tree
- `scripts/tests/fixtures.md` — S4 fixture registry

## STOP

Local verification complete. Awaiting human approval before `git push` and draft PR creation.
