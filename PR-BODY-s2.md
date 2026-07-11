# PR: canonical-v2-s2-chevron → canonical-v2

## Ten-step extension gate checklist

- [x] 1. `component-vocabulary.json` — `chevron` / `ordered-sequence` / `linear-sequence`, `closed-loop`
- [x] 2. `component-ir.schema.json` enums + `chevronPayload` + oneOf×4
- [x] 3. No new common IR fields — payload dispatch addition only
- [x] 4. `renderers/chevron.py` + manifest consumes all semantic IDs
- [x] 5. `assets/components/chevron.css` (tokens only, clip-path chevron shapes)
- [x] 6. digest `61b562e8f7c7fdc990c4c44002ddb858a761f4f6212ed64ea7211c3ef407bd68`
- [x] 7. `TRUSTED_RENDERERS["chevron@1"]`
- [x] 8. registry entry + `chevron-structure` checker rule
- [x] 9. four-layer checks + bad fixtures (JSON + `component-bad-chevron-structure.html`)
- [x] 10. build + full pytest + `check.sh --selftest` + docs sync

## S2 chevron specifics

- Vertical centered layout + optional loop rail (renderer-owned, no `data-ve-from/to`)
- Visually-hidden sentence for last→first step labels when `loop: true`
- Horizontal arrow chevrons; narrow screens stack vertically
- `loop:true` ⇔ `closed-loop` capability; `linear-sequence` always required

## Test evidence

```text
$ cd skills/visual-explain/scripts && python3 -m pytest tests -q
305 passed, 88 subtests passed in ~3.0s

$ python3 build_explainer.py --assembly tests/component-valid-chevron-loop.json --output tests/chevron-doc.html
OK: tests/chevron-doc.html

$ python3 build_explainer.py --assembly tests/component-valid-chevron-horizontal.json --output tests/chevron-horizontal-doc.html
OK: tests/chevron-horizontal-doc.html

$ bash check.sh tests/chevron-doc.html
PASS

$ bash check.sh tests/chevron-horizontal-doc.html
PASS

$ bash check.sh --selftest
selftest: 25 passed, 0 failed

$ git diff HEAD -- '**/skeleton.html'
(empty — skeleton byte-identical)
```

## Light/dark inspection artifacts

- `skills/visual-explain/scripts/tests/chevron-doc.html` (vertical + loop rail)
- `skills/visual-explain/scripts/tests/chevron-horizontal-doc.html` (horizontal arrows)

## Docs touched

- `references/patterns.md` — chevron IR example + flow/chevron kind routing rule
- `references/design-system.md` — chevron 6-step cap + centering exception
- `SKILL.md` — canonical components list includes chevron
- `scripts/tests/fixtures.md` — S2 fixture registry

## STOP

Local verification complete. Awaiting human approval before `git push` and draft PR creation.
