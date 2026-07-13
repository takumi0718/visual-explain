# Responsive Layout (Fluid Type Scale + Two-Tier Figure Width) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make generated explainer HTML scale up optically on desktop (fluid 16→20px root, symmetric breakout for flow/matrix figures) while leaving mobile pixel-identical except one ask-options fix.

**Architecture:** All CSS changes live in the skeleton's fixed `<style>` block (`assets/skeleton.html`). Because the checker byte-compares fixed regions against that file, every skeleton-embedding fixture is re-spliced; six of the seven `KEEP_AS_IS` fixtures (all except the skeleton-less `compatibility-valid-fragment.html`) get the same three CSS edits applied textually. The design spec is `docs/superpowers/specs/2026-07-13-responsive-layout-design.md`.

**Tech Stack:** Plain CSS in a fixed HTML skeleton, Python stdlib checker/tests (pytest + unittest), `check.sh --selftest`.

## Global Constraints

- No skeleton token is added, removed, or changed (`--fs-*`, `--space-*`, `--w-narrative` stay byte-identical).
- No changes to `assets/components/*.css`, `registry.json`, `build_explainer.py`, `ve_components/` or `check.sh`/`check_component_html.py` logic.
- The fluid scale rule is exactly `font-size: clamp(1rem, 0.7rem + 0.5vw, 1.25rem)` on `html`.
- The breakout margin value is exactly `calc(-1 * min(10rem, (100vw - 60rem) / 2))`, gated behind `@media (min-width: 60rem)`, applied to exactly two selectors: `.figure:has(.flow, .matrix)` and `figure[data-ve-component="matrix"] .ve-matrix-scroll` (the latter also gets `max-width: none;`). Component `flow` is NOT eligible.
- The two breakout selectors are separate rules (never share one selector list with `:has()`).
- Baseline before this plan: `check.sh --selftest` = 25 passed, `python3 -m pytest tests/ -q` = 515 passed. Every task ends green and committed.
- All commands below run from `skills/visual-explain/scripts/` unless stated otherwise. Repo root is `/Users/yoshidatakumi/workspace/visual-explain`.
- Commit messages end with:
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: Skeleton responsive CSS + audit tests + fixture re-splice

**Files:**
- Modify: `skills/visual-explain/assets/skeleton.html` (3 edits inside `<style>`)
- Modify: `skills/visual-explain/scripts/tests/test_skeleton_audit.py` (new test class + spacing-audit exception)
- Modify: `skills/visual-explain/scripts/tests/tools/resplice.py` (docstring note only)
- Regenerate: `skills/visual-explain/scripts/tests/*.html` (80 via resplice + 6 KEEP_AS_IS via textual edits; `compatibility-valid-fragment.html` untouched), `skills/visual-explain/examples/example-proposal.html`

**Interfaces:**
- Consumes: current skeleton fixed CSS (anchors quoted verbatim below; verified present once each).
- Produces: the three CSS rules quoted in Global Constraints, embedded identically in the skeleton and all fixtures. Task 2's doc text and Task 3's QA refer to them.

- [ ] **Step 1: Create the feature branch**

```bash
cd /Users/yoshidatakumi/workspace/visual-explain
git checkout -b feat/responsive-layout
cd skills/visual-explain/scripts
```

- [ ] **Step 2: Write the failing tests**

Append to `skills/visual-explain/scripts/tests/test_skeleton_audit.py` (before the final `if __name__ == "__main__":` block):

```python
class ResponsiveLayoutTest(unittest.TestCase):
    """design spec 2026-07-13: 流体ルートスケールと二層幅の骨格規則を固定する。"""

    def test_fluid_root_type_scale(self):
        self.assertIn(
            "html { background: var(--bg); color: var(--text); "
            "font-size: clamp(1rem, 0.7rem + 0.5vw, 1.25rem); }",
            SKELETON)

    def test_two_tier_breakout_rules(self):
        gate = SKELETON.split("@media (min-width: 60rem) {", 1)
        self.assertEqual(len(gate), 2, "60rem の media gate がありません")
        block = gate[1].split("}\n\n", 1)[0]
        self.assertIn(
            ".figure:has(.flow, .matrix) { margin-inline: "
            "calc(-1 * min(10rem, (100vw - 60rem) / 2)); }",
            block)
        self.assertIn(
            'figure[data-ve-component="matrix"] .ve-matrix-scroll { margin-inline: '
            "calc(-1 * min(10rem, (100vw - 60rem) / 2)); max-width: none; }",
            block)

    def test_ask_options_stack_on_mobile(self):
        mobile = SKELETON.split("@media (max-width: 42rem) {", 1)[1]
        self.assertIn(
            ".ask-options [data-ask-option] { grid-template-columns: 1fr; "
            "gap: var(--space-1); }",
            mobile)
```

- [ ] **Step 3: Run the new tests to verify they fail**

Run: `python3 -m pytest tests/test_skeleton_audit.py -q`
Expected: 3 failed (the three `ResponsiveLayoutTest` tests), rest passed.

- [ ] **Step 4: Edit the skeleton — three exact edits**

In `skills/visual-explain/assets/skeleton.html`:

Edit A (line 83) — replace:
```css
    html { background: var(--bg); color: var(--text); }
```
with:
```css
    html { background: var(--bg); color: var(--text); font-size: clamp(1rem, 0.7rem + 0.5vw, 1.25rem); }
```

Edit B — insert the ask-options rule inside the existing 42rem block, directly after `      .compare { grid-template-columns: 1fr; }`:
```css
      .compare { grid-template-columns: 1fr; }
      .ask-options [data-ask-option] { grid-template-columns: 1fr; gap: var(--space-1); }
```

Edit C — insert the breakout block directly before `    @media (max-width: 42rem) {`:
```css
    /* 二層幅: 適格の図だけ本文カラムの中心軸から対称に張り出す（design-system.md 幅の節） */
    @media (min-width: 60rem) {
      .figure:has(.flow, .matrix) { margin-inline: calc(-1 * min(10rem, (100vw - 60rem) / 2)); }
      figure[data-ve-component="matrix"] .ve-matrix-scroll { margin-inline: calc(-1 * min(10rem, (100vw - 60rem) / 2)); max-width: none; }
    }

    @media (max-width: 42rem) {
```
(Do Edit B before Edit C so the `@media (max-width: 42rem) {` anchor is still unique when C runs — B's anchor is the `.compare` line, unaffected by C.)

- [ ] **Step 5: Run the audit tests — ResponsiveLayoutTest passes, SpacingGridAuditTest now fails**

Run: `python3 -m pytest tests/test_skeleton_audit.py -q`
Expected: `test_skeleton_spacing_on_grid` FAILS with a violation like `skeleton: margin-inline: calc(-1 * min(10rem, (100vw - 60rem) / 2))`; all three `ResponsiveLayoutTest` tests PASS.

- [ ] **Step 6: Add the narrow spacing-audit exception**

In `tests/test_skeleton_audit.py`, add one module-level constant after `_ALLOWED_VALUE`:

```python
# 二層幅の張り出し（design spec 2026-07-13）だけを 8px グリッド監査の明示的例外とする。
_BREAKOUT_MARGIN = "calc(-1 * min(10rem, (100vw - 60rem) / 2))"
```

and replace the `_audit` method of `SpacingGridAuditTest` with:

```python
    def _audit(self, css, label):
        violations = []
        for prop, value in _SPACING_PROP.findall(css):
            value = value.strip()
            if prop == "margin-inline" and value == _BREAKOUT_MARGIN:
                continue
            for part in value.split():
                if not _ALLOWED_VALUE.match(part.strip()):
                    violations.append(f"{label}: {prop}: {value}")
                    break
        return violations
```

- [ ] **Step 7: Run the audit tests to verify they all pass**

Run: `python3 -m pytest tests/test_skeleton_audit.py -q`
Expected: all passed.

- [ ] **Step 8: Extend KEEP_AS_IS before running resplice (data-loss guard)**

Three fixtures would be DESTROYED by the current default glob: `bad-title-missing.html` (no TITLE markers — resplice would re-insert the skeleton's default title, erasing the fixture's purpose), `compatibility-valid-fragment.html` (a 4-line fragment with no markers at all — resplice would replace it with the entire bare skeleton), and `component-bad-fixed-region.html` (its intentional divergence lives in fixed region 3 — the footer — outside the splice markers, so resplice would overwrite it with the skeleton's clean footer and erase the `fixed_region_mismatch` it exists to trigger). In `tests/tools/resplice.py` replace:

```python
KEEP_AS_IS = {"bad-closing.html", "bad-system-closing.html", "bad-fixed-region.html", "bad-nesting.html"}
```

with:

```python
KEEP_AS_IS = {
    "bad-closing.html", "bad-system-closing.html", "bad-fixed-region.html", "bad-nesting.html",
    # マーカー欠落を検査する fixture と骨格を持たない断片。resplice すると内容が壊れる。
    # component-bad-fixed-region.html は固定領域3（footer）に故意相違を持ち、resplice すると消える。
    "bad-title-missing.html", "compatibility-valid-fragment.html", "component-bad-fixed-region.html",
}
```

- [ ] **Step 9: Re-splice the skeleton-embedding fixtures and the example**

```bash
python3 tests/tools/resplice.py
python3 tests/tools/resplice.py ../examples/example-proposal.html
```
Expected output: `resplice <name>.html` for 80 test fixtures plus `example-proposal.html`, and `skip` lines for the seven KEEP_AS_IS names.

- [ ] **Step 10: Apply the same three edits textually to six KEEP_AS_IS fixtures**

The four marker-broken fixtures plus `bad-title-missing.html` and `component-bad-fixed-region.html` all embed the pre-change skeleton CSS byte-for-byte (verified: each anchor occurs exactly once per file). `compatibility-valid-fragment.html` carries no skeleton bytes and needs nothing. Run from `skills/visual-explain/scripts/`:

```bash
python3 - <<'PY'
from pathlib import Path
EDITS = [
    ("html { background: var(--bg); color: var(--text); }",
     "html { background: var(--bg); color: var(--text); font-size: clamp(1rem, 0.7rem + 0.5vw, 1.25rem); }"),
    ("      .compare { grid-template-columns: 1fr; }",
     "      .compare { grid-template-columns: 1fr; }\n"
     "      .ask-options [data-ask-option] { grid-template-columns: 1fr; gap: var(--space-1); }"),
    ("    @media (max-width: 42rem) {",
     "    /* 二層幅: 適格の図だけ本文カラムの中心軸から対称に張り出す（design-system.md 幅の節） */\n"
     "    @media (min-width: 60rem) {\n"
     "      .figure:has(.flow, .matrix) { margin-inline: calc(-1 * min(10rem, (100vw - 60rem) / 2)); }\n"
     '      figure[data-ve-component="matrix"] .ve-matrix-scroll { margin-inline: calc(-1 * min(10rem, (100vw - 60rem) / 2)); max-width: none; }\n'
     "    }\n\n"
     "    @media (max-width: 42rem) {"),
]
for name in ("bad-closing.html", "bad-system-closing.html",
             "bad-fixed-region.html", "bad-nesting.html",
             "bad-title-missing.html", "component-bad-fixed-region.html"):
    p = Path("tests") / name
    text = p.read_text("utf-8")
    for old, new in EDITS:
        assert text.count(old) == 1, (name, old[:50])
        text = text.replace(old, new)
    p.write_text(text, "utf-8")
    print("styled", name)
PY
```
Expected: `styled <name>` × 6, no AssertionError. (Edit order matters: the `.compare` edit runs before the 42rem-anchored edit, mirroring Step 4.)

- [ ] **Step 11: Document the manual-sync rule in resplice.py**

In `tests/tools/resplice.py`, extend the docstring's KEEP_AS_IS sentence to:

```python
"""Re-splice tracked HTML fixtures onto the current skeleton.

Extracts each fixture's TITLE, CONTENT, and controlled-slot bodies, then
re-inserts them between the same markers of the new skeleton. Fixtures whose
markers are intentionally broken (bad-closing 等、マーカー自体を検査する fixture)
are listed in KEEP_AS_IS and skipped. 骨格の固定 CSS を変更したときは、
KEEP_AS_IS のうち骨格 CSS を埋め込む6件（compatibility-valid-fragment.html 以外）にも
同じ編集をテキスト置換で適用すること（マーカー破壊や固定領域の故意相違は保存し、
固定 CSS だけを骨格と一致させる）。
"""
```

- [ ] **Step 12: Run the full suite and the selftest to verify green**

```bash
python3 -m pytest tests/ -q
./check.sh --selftest
```
Expected: `518 passed` (515 baseline + 3 new; subtest count may vary) and `selftest: 25 passed, 0 failed`.

- [ ] **Step 13: Verify no unintended byte drift, then commit**

```bash
cd /Users/yoshidatakumi/workspace/visual-explain
git diff --stat   # expect: skeleton.html, test_skeleton_audit.py, resplice.py, example-proposal.html, 86 tests/*.html (all except compatibility-valid-fragment.html)
git diff --stat -- skills/visual-explain/scripts/tests/compatibility-valid-fragment.html   # expect: empty
git add -A
git commit -m "feat(visual-explain): add fluid type scale and two-tier figure width

Fluid root font-size (16-20px across 960-1760px), symmetric breakout for
figure-wrapped legacy flow/matrix and component matrix (60rem gate,
continuous ramp, 65rem cap), ask-options mobile stacking. Fixtures
re-spliced; KEEP_AS_IS fixtures synced textually.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: design-system.md and patterns.md amendments

**Files:**
- Modify: `skills/visual-explain/references/design-system.md` (5 edits)
- Modify: `skills/visual-explain/references/patterns.md` (1 insertion)

**Interfaces:**
- Consumes: the CSS rules committed in Task 1 (quoted verbatim in the new doc text).
- Produces: the normative two-tier width wording that Task 3's QA judgments reference.

- [ ] **Step 1: Amend 幅（1）— replace the single-width section**

In `design-system.md`, replace:

```markdown
**幅（1）— 単一幅。左右のエッジを共有せよ。**

- `--w-narrative`（45rem）: コンテンツの唯一の最大幅カラム。見出し・本文・図・表・キャプションを含む全要素がこの幅に収まり、左右のエッジを共有する

密な表・flow は各自の横スクロールコンテナ内で溢れさせ、ページ全体を広げるな。中央寄せは使わない。
```

with:

```markdown
**幅（2階層）— 本文は単一幅。適格の密な図だけ対称に張り出す。**

- `--w-narrative`（45rem）: 見出し・本文・キャプション・非適格の図を収める唯一の本文カラム。左右のエッジを共有する
- 二層幅の適格は閉じた列挙とする: `figure` に包んだ legacy の `flow` / `matrix` と、コンポーネント `matrix` のスクロールコンテナだけが、広い画面（初期換算 960px 以上）で本文カラムの中心軸から左右対称に張り出せる（連続ランプ、片側最大 10rem、合計 65rem 以下）。裸の legacy `flow` / `matrix`、コンポーネント `flow`、その他の図は張り出さない
- ルート文字サイズは流体スケールする（`clamp(1rem, 0.7rem + 0.5vw, 1.25rem)`。960px 以下で 16px、1760px で 20px 到達）。トークン値と1行の字数は不変
- caption の位置は経路で決まる: コンポーネント経路の caption / summary / notes は `--w-narrative` を保ち本文エッジに揃える。張り出した legacy カードの figcaption はカードに追従し、カード境界を整列コンテキストとする

密な表・flow は各自の横スクロールコンテナ内で溢れさせ、ページ全体を広げるな。カラム内で内容を中央寄せしない。二層幅の張り出しは本文カラムの中心軸に対する対称拡張であり、この規則の例外ではない。
```

- [ ] **Step 2: Amend the 表層 bullet and add the fluid-scale bullet**

Replace:

```markdown
- **単一幅**: 全要素は `--w-narrative` 一本のカラムに収め、左右のエッジを共有する。密な表・flow は各自の横スクロールコンテナ内で溢れさせる。
```

with:

```markdown
- **二層幅**: 本文と非適格の図は `--w-narrative` 一本のカラムに収め、左右のエッジを共有する。適格の図（幅の節の閉じた列挙）だけが広い画面で中心軸から対称に張り出す。密な表・flow は各自の横スクロールコンテナ内で溢れさせる。
- **流体ルートスケール**: ルート文字サイズは 960→1760px で 16→20px に流体スケールする。タイプ・余白・幅のトークン値と1行の字数は不変。
```

- [ ] **Step 3: Add the layout-invariant bullet**

In the レイアウト不変条件 list, after the final bullet
`- 1セクション1問いを守り、主張を1行、根拠を2〜3行の目安に抑えよ。概ね1画面に収まるかを目視確認せよ。`
append:

```markdown
- 二層幅の張り出しは幅の節の閉じた列挙にだけ適用する。新しい図種を張り出させるには、幅の節・骨格 CSS・`test_skeleton_audit.py` の監査例外を同時に改訂せよ。
```

- [ ] **Step 4: Amend the ownership section**

In コンポーネント資産の所有権, after the bullet ending `新しい色・書体・余白系・アニメーション・装飾を足さない。` insert:

```markdown
- **二層幅のための閉じた例外**: 骨格は二層幅レイアウトに限り、コンポーネント名前空間セレクタ（`figure[data-ve-component="matrix"] .ve-matrix-scroll`）を対象にでき、その `max-width` を上書きできる。それ以外の名前空間規則は引き続きコンポーネントが所有する。
```

and replace the sentence `骨格全体の中央揃え規則は変えない。`（図コンテナ内の中央揃え例外 bullet の末尾）with:

```markdown
骨格全体の中央揃え規則は変えない。二層幅の対称張り出しは中央軸に対する拡張であり、この規則とは独立である。
```

- [ ] **Step 5: Add the patterns.md note**

In `patterns.md`, insert directly before the line `## コネクタ宣言`:

```markdown
## 広い画面での二層幅

`figure` に包んだ legacy の `flow` / `matrix` は、広い画面で本文カラムの中心軸から左右対称に張り出す（コンポーネント `matrix` も同様。詳細は `design-system.md` の幅の節）。裸の `flow` / `matrix` は本文幅のまま。張り出しを意図するなら `figure` に包め。

```

- [ ] **Step 6: Verify no stale wording and suite still green**

```bash
grep -rn "単一幅" /Users/yoshidatakumi/workspace/visual-explain/skills/
```
Expected: no hits (the term now only survives in docs/superpowers history).

```bash
python3 -m pytest tests/ -q
```
Expected: `518 passed`.

- [ ] **Step 7: Commit**

```bash
cd /Users/yoshidatakumi/workspace/visual-explain
git add skills/visual-explain/references/design-system.md skills/visual-explain/references/patterns.md
git commit -m "docs(visual-explain): document two-tier width and fluid root scale

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Visual QA (browser, user-gated)

**Files:**
- Create (scratchpad, not committed): a built component-matrix document
- Read: `skills/visual-explain/scripts/tests/catalog.html` (legacy figures, re-spliced in Task 1)
- Modify: `docs/superpowers/specs/2026-07-13-responsive-layout-design.md` (Status line after QA)

**Interfaces:**
- Consumes: Task 1's re-spliced fixtures and skeleton.
- Produces: QA verdicts for the spec's Verification items 2–8; a Status update on the spec.

- [ ] **Step 1: Build the component-route QA document**

```bash
cd /Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/scripts
python3 build_explainer.py --assembly tests/component-valid-matrix.json \
  --output "$SCRATCHPAD/qa-component-matrix.html"
```
(`$SCRATCHPAD` = the session scratchpad directory.) Expected: `OK: .../qa-component-matrix.html`. This also proves the unchanged builder+checker accept the new skeleton end-to-end.

- [ ] **Step 2: Open both QA documents in the browser**

```bash
open "$SCRATCHPAD/qa-component-matrix.html"
open /Users/yoshidatakumi/workspace/visual-explain/skills/visual-explain/scripts/tests/catalog.html
```

- [ ] **Step 3: Walk the spec's manual QA checklist with the user (human eyes required — pause here)**

From the spec's Verification section, confirm each item and record PASS/FAIL:

1. 375px: identical to pre-change except `.ask-options` rows stack in one column.
2. 1920px: 900px narrative column; eligible figures ≈1300px, centered on the same axis.
3. Non-eligible content (body text, component flow, kpi, bars, terms, pyramid, stairs, waterfall, slope, enumeration, chevron, logic-tree, evidence-map, bare legacy flow/matrix) stays at narrative width at all viewports.
4. Resize 900→1920px: eligible figures widen smoothly from the 960px knee, no jump.
5. Classic scrollbars forced: no page-level horizontal scrollbar at ≥ 960px.
6. Component matrix captions stay flush with the body-text edge while the canvas widens.
7. Sparse 2×2 component matrix at 1920px: judge the stretched table acceptable or not (if not: fallback is the opt-in `data-wide` route — separate change, do not improvise a density heuristic).
8. Browser zoom 200% / 400% at a 1280px window: reflow without horizontal scrolling.
9. Mobile audit at 320 / 375 / 430px (spec Mechanism 3): all ten components, legacy figures, ask blocks, first-screen, stepper, theme control — no cramped or overflowing layout. A new finding is bundled only if it is one rule using existing tokens and breakpoints; otherwise it becomes a separate change.
10. Both themes (light/dark) for items 1–2.

- [ ] **Step 4: Record the QA outcome in the spec and commit**

Update the spec's `**Status:**` line to `Implemented on feat/responsive-layout; automated verification green; browser visual QA <PASS or list of failures> (2026-07-13)`.

```bash
cd /Users/yoshidatakumi/workspace/visual-explain
git add docs/superpowers/specs/2026-07-13-responsive-layout-design.md
git commit -m "docs(visual-explain): record responsive layout QA outcome

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Integration decision (user-gated)**

Merge of `feat/responsive-layout` into `main` is the user's call (REQUIRED SUB-SKILL at that point: superpowers:finishing-a-development-branch).
