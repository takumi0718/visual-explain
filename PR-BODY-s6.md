# PR: canonical-v2-s6-slope-evidence-map → canonical-v2

## Ten-step extension gate checklist

- [x] 1. `component-vocabulary.json` — `slope`/`two-point-change`/`["two-point-comparison"]`, `evidence-map`/`claim-support`/`["claim-support-mapping"]`
- [x] 2. `component-ir.schema.json` enums + `slopePayload` + `evidenceMapPayload` + oneOf×10
- [x] 3. No new common IR fields — payload dispatch + `RenderManifest.svg_root_ids` only
- [x] 4. `renderers/slope.py` + `renderers/evidence_map.py` + manifest consumes all semantic IDs
- [x] 5. `assets/components/slope.css`, `evidence-map.css` (SHA256 digests registered)
- [x] 6. digests `21d450d28ece001f4483e90f75c4fd4a6881737e459a94bcf35f434a7e3c08f2`, `f988fe3d3d93658d4ff42790cd26d5b2101c91706d246d3cf463f9d8676b0547`
- [x] 7. `TRUSTED_RENDERERS["slope@1"]`, `["evidence-map@1"]`
- [x] 8. registry entries + `slope-structure` / `renderer-svg` / `evidence-map-references` checker rules
- [x] 9. four-layer checks + bad fixtures (JSON + HTML + SVG gate categories)
- [x] 10. build + full pytest + `check.sh --selftest` + docs sync

## S6 specifics

- **renderer-svg gate (atomic):** `RENDERER_SVG_ALLOWLIST = frozenset({"slope@1"})`, `RenderManifest.svg_root_ids`, `assembly.render_canonical` cross-check, `checker.validate_renderer_svg` per-element allowlist
- **slope geometry:** from X=120 / to X=480; Y band 20–200; `y(v)=200−round((v−min)/range×180)`; range 0 → Y=110; required `unit`
- **evidence-map:** certaintyRef/sourceRef strict resolution; link classes `ve-em-link-{confirmed|inferred|unverified}`; monochrome `ve-cert` badge per card; conclusion `ve-em-border-strong`

## Test evidence

```text
# RED (tests written before implementation)
35 tests collected → 5 failed, 29 passed, 1 xfailed (missing fixtures / unimplemented gate)

# GREEN (after implementation)
$ cd skills/visual-explain/scripts && python3 -m pytest tests -q
484 passed, 119 subtests passed in 3.98s

$ python3 -m pytest tests/test_slope_renderer.py tests/test_evidence_map_renderer.py tests/test_renderer_svg_gate.py -q
35 passed, 8 subtests passed in 0.10s

$ python3 build_explainer.py --assembly tests/component-valid-slope.json --output tests/slope-doc.html
OK: tests/slope-doc.html

$ python3 build_explainer.py --assembly tests/component-valid-evidence-map.json --output tests/evidence-map-doc.html
OK: tests/evidence-map-doc.html

$ bash check.sh tests/slope-doc.html
PASS

$ bash check.sh tests/evidence-map-doc.html
PASS

$ bash check.sh --selftest
selftest: 25 passed, 0 failed

$ git diff HEAD -- '**/skeleton.html'
(empty — skeleton byte-identical)
```

## Light/dark inspection artifacts

- `skills/visual-explain/scripts/tests/slope-doc.html` (increase/decrease/flat + SVG)
- `skills/visual-explain/scripts/tests/evidence-map-doc.html` (confirmed/inferred links + badges)

## Docs touched

- `references/patterns.md` — slope/evidence-map selection guide + IR examples
- `references/design-system.md` — caps slope 5 / evidence 4 + renderer-svg gate summary
- `SKILL.md` — final 10-component list
- `scripts/tests/fixtures.md` — S6 fixture registry (all SVG bad categories + boundary valid)

## STOP

Local verification complete. Awaiting human approval before `git push` and draft PR `canonical-v2-s6-slope-evidence-map`.
