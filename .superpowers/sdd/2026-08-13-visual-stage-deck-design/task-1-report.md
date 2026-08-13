# Task 1 report: schema 3件の拡張

## Implementation summary

- Added `visual-stage` to the assembly `documentProfile` enum.
- Added optional canonical IR `claim`, `sequence`, and `assertions` properties.
- Added bounded sequence/assertion definitions with the specified required fields, limits, ID pattern, uniqueness, and closed objects.
- Added the authoritative sequence modes and `typed-sequence` capability to the component vocabulary; the capability is declared for matrix, flow, stairs, waterfall, and bars.
- Kept component IR `required` and existing payload `oneOf` unchanged.

## Exact commands and results

- `python3 -c "import json; [json.load(open(p)) for p in ['skills/visual-explain/references/assembly.schema.json','skills/visual-explain/references/component-ir.schema.json','skills/visual-explain/references/component-vocabulary.json']]"` — PASS (exit 0).
- `bash skills/visual-explain/scripts/check.sh --selftest` — `selftest: 31 passed, 0 failed`.
- Schema/vocabulary consistency assertion (sequence modes and capabilities) — `PASS`.
- Required/oneOf and assembly non-profile-definition comparison against `HEAD` — `PASS`.
- `git diff --check` — PASS.

## Files changed

- `skills/visual-explain/references/assembly.schema.json`
- `skills/visual-explain/references/component-ir.schema.json`
- `skills/visual-explain/references/component-vocabulary.json`

## Self-review

The diff is limited to the three requested declarative contract assets. `schemaVersion`, existing assembly definitions, component IR required fields, and existing payload exclusivity branches are unchanged. Sequence mode values are copied verbatim between vocabulary and schema, and `typed-sequence` is included in the schema capability enum and the five intended component declarations.

## Concerns

None.
