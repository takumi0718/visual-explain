# PR: canonical-v2-s1-enumeration → canonical-v2

## Ten-step extension gate checklist

- [x] 1. `component-vocabulary.json` — `enumeration` / `parallel-enumeration` / `parallel-itemization`
- [x] 2. `component-ir.schema.json` enums + `enumerationPayload` + `flowRelation` + oneOf×3
- [x] 3. No new common IR fields — payload dispatch generalization only
- [x] 4. `renderers/enumeration.py` + manifest consumes all semantic IDs
- [x] 5. `assets/components/enumeration.css` (tokens only, list centering exception)
- [x] 6. digest `f681c590d2795e964905e711c9d335cb28b763a64a521dcf95fcd7294818a2cb`
- [x] 7. `TRUSTED_RENDERERS["enumeration@1"]`
- [x] 8. registry entry + `enumeration-structure` checker rule
- [x] 9. four-layer checks + bad fixtures (JSON + `component-bad-enumeration-structure.html`)
- [x] 10. build + full pytest + `check.sh --selftest` + docs sync

## Cross-cutting generalization (S1)

- `_PAYLOAD_VALIDATORS` / `ANNOTATION_TARGETS` dispatch tables
- `CanonicalIR.semantic_ids()` includes enumeration item IDs
- flow `edge.relation` scoped to `flowRelation` only
- checker: `ve-<component>-notes`, non-flow/matrix attribute prohibition, `COMPONENT_ARTIFACT_CHECKS`

## Test evidence

```text
$ cd skills/visual-explain/scripts && python3 -m pytest tests -q
281 passed, 73 subtests passed in ~2.4s

$ python3 build_explainer.py --assembly tests/component-valid-enumeration.json --output tests/enumeration-doc.html
OK: tests/enumeration-doc.html

$ bash check.sh tests/enumeration-doc.html
PASS

$ bash check.sh --selftest
selftest: 25 passed, 0 failed

$ git diff HEAD -- '**/skeleton.html'
(empty — skeleton byte-identical)
```

## Light/dark inspection artifact

- `skills/visual-explain/scripts/tests/enumeration-doc.html` (list/number variant)
- columns/label variant: build `component-valid-enumeration-columns.json` locally if needed for visual review

## Docs touched

- `references/patterns.md` — selection guide + enumeration IR example
- `references/design-system.md` — density caps, centering exception, gate step 3 wording
- `SKILL.md` — canonical components list includes enumeration
- `scripts/tests/fixtures.md` — new fixture registry

## STOP

Local verification complete. Awaiting human approval before `git push` and draft PR creation.
