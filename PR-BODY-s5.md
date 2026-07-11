# PR: canonical-v2-s5-waterfall → canonical-v2

## Ten-step extension gate checklist

- [x] 1. `component-vocabulary.json` — `waterfall`/`additive-bridge`/`["additive-bridging"]`
- [x] 2. `component-ir.schema.json` enums + `waterfallPayload` + oneOf×8
- [x] 3. No new common IR fields — payload dispatch addition only (`waterfall` JSON key)
- [x] 4. `renderers/waterfall.py` + manifest consumes all semantic IDs (start ∪ steps ∪ end)
- [x] 5. `assets/components/waterfall.css` (pre-generated `ve-wf-start-0…100` / `ve-wf-len-0…100`, orientation containers `ve-wf-bars`/`ve-wf-columns`)
- [x] 6. digest `cbcad059f545814022cd3363ffa09963c8b17a80bb46be4d8a1d08a3684b9d5d`
- [x] 7. `TRUSTED_RENDERERS["waterfall@1"]`
- [x] 8. registry entry + `waterfall-consistency` checker rule
- [x] 9. four-layer checks + bad fixtures (JSON ×6 + bad structure HTML)
- [x] 10. build + full pytest + `check.sh --selftest` + docs sync

## S5 waterfall specifics

- **Numeric domain:** `scripts/ve_components/numeric.py` — `quantize_percent`, `is_numeric`, `waterfall_scale_values` (baseline 0 included)
- **Build entry:** `build_explainer.py` uses `json.loads(..., parse_float=Decimal)`; `parse_int` untouched
- **Validation:** `displayPrecision` required; arithmetic `<= displayPrecision/2` (Decimal); float/bool rejected; range 0 rejected; bars 1–4 / columns 1–7 steps
- **Layout:** class-driven `ve-wf-start-*` / `ve-wf-len-*` only — no inline `style=`; out-of-range → `renderer_failure` (no clamp)
- **valueText:** opaque display text, never cross-checked against numeric `value`/`delta`

## Test evidence

```text
$ cd skills/visual-explain/scripts && python3 -m pytest tests -q
442 passed, 111 subtests passed in ~4.2s

$ python3 build_explainer.py --assembly tests/component-valid-waterfall.json --output tests/waterfall-doc.html
OK: tests/waterfall-doc.html

$ python3 build_explainer.py --assembly tests/component-valid-waterfall-columns.json --output tests/waterfall-columns-doc.html
OK: tests/waterfall-columns-doc.html

$ bash check.sh tests/waterfall-doc.html
PASS

$ bash check.sh tests/waterfall-columns-doc.html
PASS

$ bash check.sh --selftest
selftest: 25 passed, 0 failed

$ git diff HEAD -- '**/skeleton.html'
(empty — skeleton byte-identical)
```

## Light/dark inspection artifacts

- `skills/visual-explain/scripts/tests/waterfall-doc.html` (bars; negative cumulative + zero-cross)
- `skills/visual-explain/scripts/tests/waterfall-columns-doc.html` (columns; 5 steps horizontal scroll)

## Docs touched

- `references/patterns.md` — waterfall selection guide (columns 狭い画面 → bars 推奨) + IR example
- `references/design-system.md` — waterfall caps 行型6行/横並び9列 + geometry-is-auxiliary/valueText-is-primary
- `SKILL.md` — canonical components list includes waterfall
- `scripts/tests/fixtures.md` — S5 fixture registry

## STOP

Local verification complete. Awaiting human approval before `git push` and draft PR `canonical-v2-s5-waterfall`.
