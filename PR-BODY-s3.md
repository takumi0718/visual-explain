# PR: canonical-v2-s3-pyramid-stairs → canonical-v2

## Ten-step extension gate checklist

- [x] 1. `component-vocabulary.json` — `pyramid`/`layered-priority`/`priority-layering`, `stairs`/`staged-maturity`/`maturity-staging`
- [x] 2. `component-ir.schema.json` enums + `pyramidPayload`/`stairsPayload` + oneOf×6
- [x] 3. No new common IR fields — payload dispatch addition only
- [x] 4. `renderers/pyramid.py` + `renderers/stairs.py` + manifests consume all semantic IDs
- [x] 5. `assets/components/pyramid.css` + `stairs.css` (tokens only, count×index layout classes)
- [x] 6. digests `8a45af59cbe466a0902044aa0e91744186a8ba1766cd28e427f2819774ff227e` (pyramid), `8d872ab77019b2d857985135879ed039a823fc2b8a82bcf656949775e533dcbe` (stairs)
- [x] 7. `TRUSTED_RENDERERS["pyramid@1"]` + `["stairs@1"]`
- [x] 8. registry entries + `pyramid-structure` + `stairs-structure` checker rules
- [x] 9. four-layer checks + bad fixtures (JSON + bad structure HTML ×10)
- [x] 10. build + full pytest + `check.sh --selftest` + docs sync

## S3 pyramid + stairs specifics

- **Pyramid:** 3–4 tiers top-first; apex `ve-pyramid-face-strong`, others `ve-pyramid-face-dim`; widths via `ve-pyramid-count-{3,4}` + `ve-pyramid-index-{n}`; no inline `style=`
- **Stairs:** 3–5 stages low→high; `current:true` max 1 and requires `note`; only current tread gets `ve-stairs-tread-accent`; no last-stage emphasis; heights via `ve-stairs-count-{3..5}` + `ve-stairs-index-{n}`
- Both: `generated_relationship_ids=()`, `ve-*-notes` DOM contract

## Test evidence

```text
$ cd skills/visual-explain/scripts && python3 -m pytest tests -q
371 passed, 97 subtests passed in ~3.6s

$ python3 build_explainer.py --assembly tests/component-valid-pyramid.json --output tests/pyramid-doc.html
OK: tests/pyramid-doc.html

$ python3 build_explainer.py --assembly tests/component-valid-stairs.json --output tests/stairs-doc.html
OK: tests/stairs-doc.html

$ bash check.sh tests/pyramid-doc.html
PASS

$ bash check.sh tests/stairs-doc.html
PASS

$ bash check.sh --selftest
selftest: 25 passed, 0 failed

$ git diff HEAD -- '**/skeleton.html'
(empty — skeleton byte-identical)
```

## Light/dark inspection artifacts

- `skills/visual-explain/scripts/tests/pyramid-doc.html` (4-tier priority pyramid)
- `skills/visual-explain/scripts/tests/stairs-doc.html` (5-stage maturity with current+note)

## Docs touched

- `references/patterns.md` — selection guide (enumeration vs pyramid, stairs vs chevron) + two IR examples
- `references/design-system.md` — pyramid 4 tiers / stairs 5 stages caps + centering exception
- `SKILL.md` — canonical components list includes pyramid/stairs
- `scripts/tests/fixtures.md` — S3 fixture registry

## STOP

Local verification complete. Awaiting human approval before `git push` and draft PR creation.
