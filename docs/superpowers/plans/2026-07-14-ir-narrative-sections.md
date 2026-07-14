# IR narrative セクション導入と IR ファースト移行 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** assembly IR に散文用 `kind: "narrative"` を追加して単一 IR JSON から完全な資料をビルド可能にし、SKILL.md / patterns.md を IR ファーストに書き換え、example-proposal を IR ビルドで再生成する。

**Architecture:** 既存の canonical/compatibility 二種の section に、第三の `narrative`（id + 限定 HTML markup のみ）を追加する。narrative は canonical の選択・レジストリ・レンダラを一切通らず、compatibility と同じ content-safety 検証を経て `<section data-ve-section-kind="narrative" data-ve-instance="...">` にラップされ、同一の composer/flattener/四層検証に入る。provenance は不要（compatibility の legacy 意味論を汚さない）。

**Tech Stack:** Python 3 標準ライブラリのみ（既存方針）。pytest。JSON Schema draft-07。

## Global Constraints

- `assets/skeleton.html`・`assets/components/*.css`・registry の digest は不可侵。1 バイトも変更しない。
- `diagnostics.py` の ALL_CODES 閉集合への追加は `INVALID_NARRATIVE_SECTION = "invalid_narrative_section"` の 1 件のみ。他の診断は既存コード（`DUPLICATE_SEMANTIC_ID`、`DUPLICATE_SECTION_ID`、`FORBIDDEN_CONTENT_MARKUP`、`MISSING_PROVENANCE`）を再利用する。
- `schemaVersion` は 1 のまま（後方互換の追加変更。既存 assembly はすべてそのまま通る）。
- 既存テストは全緑を維持する。テスト実行: `python3 -m pytest skills/visual-explain/scripts/tests -q`（リポジトリルートから）。
- テストの import・fixture 流儀は既存テスト（`test_mixed_assembly.py`、`test_v2_core.py`）を先に読んで踏襲する。`make_*_ir` や `ValidationError` は存在しない。契約違反は `ContractError` + `exc.value.codes` で検証する。
- ドキュメントは日本語。コミットは Conventional Commits（`feat(ve):` / `test(ve):` / `docs(ve):`）。
- 作業ブランチ `feat/ir-narrative-sections`。PR は draft。merge はユーザー判断。
- 各タスクの実装前に対象ファイルの現状を必ず読む（行番号は 2026-07-14 時点の main `f387a45` 基準でずれ得る）。

---

### Task 1: narrative kind の schema / model / validation（TDD）

**Files:**
- Modify: `skills/visual-explain/references/assembly.schema.json`
- Modify: `skills/visual-explain/scripts/ve_components/diagnostics.py`
- Modify: `skills/visual-explain/scripts/ve_components/model.py`（`CompatibilitySection` 定義の直後）
- Modify: `skills/visual-explain/scripts/ve_components/validation.py`（`_validate_section` 分岐と `_COMPAT_SECTION_KEYS` 付近）
- Create: `skills/visual-explain/scripts/tests/test_narrative_sections.py`

**Interfaces:**
- Consumes: `validate_assembly(raw) -> AssemblyRequest`（validation.py:1939）、`DiagnosticCollector`、`_nonblank_str`、`_check_keys`（validation.py 既存ヘルパ）
- Produces: `NarrativeSection(id: str, markup: str)`（frozen dataclass、model.py）。`validate_assembly` が `kind: "narrative"` を受理して `NarrativeSection` を返す。診断コード `invalid_narrative_section`。Task 2 以降はこの型名・フィールド名に依存する。

- [ ] **Step 1: ブランチ作成**

```bash
git switch -c feat/ir-narrative-sections
```

- [ ] **Step 2: 失敗するテストを書く**

`skills/visual-explain/scripts/tests/test_narrative_sections.py` を新規作成。import 方法（conftest / sys.path）は `test_mixed_assembly.py` の冒頭を読んで同じ流儀にする。

```python
import pytest

from ve_components.diagnostics import ContractError
from ve_components.model import NarrativeSection
from ve_components.validation import validate_assembly

BASE = {"schemaVersion": 1,
        "document": {"id": "doc", "title": "検証資料", "summary": "narrative 検証。"}}

NARR = {"kind": "narrative", "id": "sec-intro",
        "markup": '<section class="first-screen"><h1>結論を先に示す</h1></section>'}


def _assembly(*sections):
    return {**BASE, "sections": list(sections)}


def test_narrative_section_parses():
    req = validate_assembly(_assembly(NARR))
    sec = req.sections[0]
    assert isinstance(sec, NarrativeSection)
    assert sec.id == "sec-intro"
    assert "first-screen" in sec.markup


def test_narrative_rejects_extra_field():
    bad = {**NARR, "provenance": {"source": "legacy-html-insertion"}}
    with pytest.raises(ContractError) as exc:
        validate_assembly(_assembly(bad))
    assert "invalid_narrative_section" in exc.value.codes


def test_narrative_rejects_blank_id_and_markup():
    with pytest.raises(ContractError) as exc:
        validate_assembly(_assembly({"kind": "narrative", "id": " ", "markup": " "}))
    assert "invalid_narrative_section" in exc.value.codes


def test_narrative_duplicate_id_rejected():
    with pytest.raises(ContractError) as exc:
        validate_assembly(_assembly(NARR, dict(NARR)))
    assert "duplicate_semantic_id" in exc.value.codes
```

- [ ] **Step 3: 失敗を確認**

Run: `python3 -m pytest skills/visual-explain/scripts/tests/test_narrative_sections.py -v`
Expected: FAIL（`ImportError: cannot import name 'NarrativeSection'`）

- [ ] **Step 4: 最小実装**

`diagnostics.py` — 既存グループの並びに追加し、ALL_CODES にも同名を追加:

```python
# Narrative section codes.
INVALID_NARRATIVE_SECTION = "invalid_narrative_section"
```

`model.py` — `CompatibilitySection` の直後:

```python
@dataclass(frozen=True)
class NarrativeSection:
    id: str
    markup: str
```

`AssemblyRequest.sections` のコメントを `CanonicalSection | NarrativeSection | CompatibilitySection` に更新。

`validation.py` — 定数と分岐と検証関数（`_validate_compatibility_section` の直前後に置き、その制御フローを踏襲する）:

```python
_NARRATIVE_SECTION_KEYS = {"kind", "id", "markup"}
```

`_validate_section` の `if kind == "compatibility":` の直前に:

```python
    if kind == "narrative":
        return _validate_narrative_section(raw, path, col, seen_ids)
```

```python
def _validate_narrative_section(raw: dict, path: str, col: DiagnosticCollector, seen_ids: set[str]):
    # Narrative accepts only id and markup. Provenance, relationship, selection,
    # or asset fields are authoring violations.
    before = len(col.diagnostics)
    for key in raw:
        if key not in _NARRATIVE_SECTION_KEYS:
            col.add(INVALID_NARRATIVE_SECTION, f"narrative に不正なフィールド '{key}'", path)
    sid = raw.get("id")
    if not _nonblank_str(sid):
        col.add(INVALID_NARRATIVE_SECTION, "narrative.id は空にできません", path)
    if not _nonblank_str(raw.get("markup")):
        col.add(INVALID_NARRATIVE_SECTION, "narrative.markup は空にできません", path)
    if len(col.diagnostics) > before:
        return None
    if sid in seen_ids:
        col.add(DUPLICATE_SEMANTIC_ID, f"section id '{sid}' が重複しています", path)
        return None
    seen_ids.add(sid)
    return NarrativeSection(id=sid, markup=raw["markup"])
```

`assembly.schema.json` — `$defs` に追加し、`section.oneOf` に `{"$ref": "#/$defs/narrativeSection"}` を追加。トップレベル `description` の section 説明に narrative を追記:

```json
"narrativeSection": {
  "type": "object",
  "additionalProperties": false,
  "required": ["kind", "id", "markup"],
  "properties": {
    "kind": {"const": "narrative"},
    "id": {"type": "string", "minLength": 1},
    "markup": {"type": "string", "minLength": 1}
  }
}
```

- [ ] **Step 5: テスト成功と回帰なしを確認**

Run: `python3 -m pytest skills/visual-explain/scripts/tests -q`
Expected: 新規 4 件 PASS、既存全緑（`test_component_contract.py` の schema ドリフト検査を含む。FAIL したらその検査の期待値を narrative 込みに更新する — 検査の意図を壊さないこと）。

- [ ] **Step 6: Commit**

```bash
git add -A skills/visual-explain
git commit -m "feat(ve): add narrative section kind to assembly schema and validation"
```

---

### Task 2: composition と build の narrative 経路（TDD）

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/assembly.py`
- Modify: `skills/visual-explain/scripts/build_explainer.py:58-74`（`build_document` の dispatch）
- Modify: `skills/visual-explain/scripts/tests/test_narrative_sections.py`（追記）

**Interfaces:**
- Consumes: Task 1 の `NarrativeSection`。`validate_content_markup(markup) -> list[Diagnostic]`（checker.py、compat と同一の content-safety）。`_attr`（assembly.py 既存）。
- Produces: `WrappedNarrative(instance_id: str, markup: str)`、`process_narrative_section(section: NarrativeSection) -> WrappedNarrative`、`CompositionResult.narrative: tuple[WrappedNarrative, ...]`。ラッパは `<section data-ve-section-kind="narrative" data-ve-instance="<id>">…</section>`。Task 3 は `expected.narrative` に依存する。

- [ ] **Step 1: 失敗するテストを追記**

```python
from ve_components.assembly import process_narrative_section


def test_process_narrative_wraps_with_instance():
    sec = NarrativeSection(id="sec-intro", markup="<h1>結論</h1>")
    wrapped = process_narrative_section(sec)
    assert 'data-ve-section-kind="narrative"' in wrapped.markup
    assert 'data-ve-instance="sec-intro"' in wrapped.markup


def test_process_narrative_rejects_forbidden_markup():
    sec = NarrativeSection(id="sec-bad", markup='<script>alert(1)</script>')
    with pytest.raises(ContractError) as exc:
        process_narrative_section(sec)
    assert "forbidden_content_markup" in exc.value.codes
```

さらに end-to-end（`test_mixed_assembly.py` の build 系テストの流儀を読み、同じ方法で）: `component-valid-enumeration.json` の canonical ir を再利用し、narrative（first-screen）+ canonical + narrative（closing）の 3 section assembly を `build_document`（または `build_to_path`）でビルドして、出力に 3 つの section ラッパが元の順序で並ぶことを assert する。narrative と canonical で同じ id を使った場合に `duplicate_section_id` になることも 1 件 assert する。

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m pytest skills/visual-explain/scripts/tests/test_narrative_sections.py -v`
Expected: FAIL（`ImportError: cannot import name 'process_narrative_section'`）

- [ ] **Step 3: 実装**

`assembly.py` — `WrappedCompatibility` の直後:

```python
@dataclass(frozen=True)
class WrappedNarrative:
    instance_id: str
    markup: str
```

`process_compatibility_section` の直後:

```python
def process_narrative_section(section: NarrativeSection) -> WrappedNarrative:
    diagnostics = validate_content_markup(section.markup)
    if diagnostics:
        raise ContractError(diagnostics)
    wrapper = (
        f'<section data-ve-section-kind="narrative"'
        f' data-ve-instance="{_attr(section.id)}">\n{section.markup}\n</section>'
    )
    return WrappedNarrative(instance_id=section.id, markup=wrapper)
```

`CompositionResult` に `narrative: tuple[WrappedNarrative, ...]` フィールドを追加。`compose_sections` のループを isinstance 明示分岐に書き換え（`RenderedCanonical` → manifests/assets、`WrappedCompatibility` → compatibility、`WrappedNarrative` → narrative）。既存の `else: compatibility.append(item)` を暗黙のまま残さない。model import に `NarrativeSection` を追加。

`build_explainer.py` — import に `process_narrative_section` と `NarrativeSection` を追加し、dispatch を:

```python
        if isinstance(section, CanonicalSection):
            items.append(process_canonical_section(section, registry, renderers))
        elif isinstance(section, NarrativeSection):
            items.append(process_narrative_section(section))
        else:
            items.append(process_compatibility_section(section))
```

- [ ] **Step 4: テスト成功と回帰なしを確認**

Run: `python3 -m pytest skills/visual-explain/scripts/tests -q`
Expected: 全緑（`CompositionResult` の位置引数で構築している既存テストがあれば narrative フィールド追加で壊れる — キーワード引数化で追随する）。

- [ ] **Step 5: Commit**

```bash
git add -A skills/visual-explain
git commit -m "feat(ve): compose and build narrative sections through the single composer"
```

---

### Task 3: 最終検証ゲートと fixture（TDD）

**Files:**
- Modify: `skills/visual-explain/scripts/ve_components/checker.py`（`validate_final_provenance`、checker.py:456-475 付近）
- Modify: `skills/visual-explain/scripts/ve_components/final_checks.py`（`check_manifest_to_dom` 末尾）
- Create: `skills/visual-explain/scripts/tests/component-valid-narrative-mixed.json`
- Modify: `skills/visual-explain/scripts/tests/test_narrative_sections.py`（追記）

**Interfaces:**
- Consumes: Task 2 の `CompositionResult.narrative`。`_ATTR_RE`、`_SECTION_TAG_RE`（checker.py 既存）。
- Produces: `validate_final_provenance` が `kind="narrative"` を受理（`data-ve-instance` 必須）。`check_manifest_to_dom` が `expected.narrative` の DOM 存在を検査。新 fixture は narrative + canonical + compatibility の三種混在で、`check.sh` 単体（--type なし）で PASS する。

- [ ] **Step 1: 失敗するテストを追記**

```python
from ve_components.checker import validate_final_provenance


def test_final_provenance_accepts_narrative_with_instance():
    content = ('<section data-ve-section-kind="narrative"'
               ' data-ve-instance="sec-intro"><h1>結論</h1></section>')
    assert validate_final_provenance(content) == []


def test_final_provenance_rejects_narrative_without_instance():
    content = '<section data-ve-section-kind="narrative"><h1>結論</h1></section>'
    diags = validate_final_provenance(content)
    assert any(d.code == "missing_provenance" for d in diags)
```

manifest-to-DOM 側: 三種混在 assembly をビルド後、出力 HTML から narrative section を 1 つ手で削った文字列を `check_final_document(..., expected=composition)` に渡し、`missing_provenance` が出ることを assert（`final_checks.py` のテスト流儀は `test_component_checker.py` を読んで踏襲）。

fixture `component-valid-narrative-mixed.json`: document（id `narrative-mixed-demo`）+ sections = narrative first-screen（`<section class="first-screen"><h1>…</h1><p class="subtitle decision">…</p></section>`）→ `component-valid-enumeration.json` から流用した canonical enumeration → compatibility layers（`component-valid-mixed.json` の compat section を流用）→ narrative closing（`<section class="closing-section"><h2>リスクと弱い前提</h2><p>…</p></section>`）。`test_visual_explain_fixtures.py` が `component-valid-*.json` を自動走査するか読んで確認し、走査対象なら期待に合わせ、対象外なら本テストからビルド + `check.sh` subprocess で PASS を assert する。

- [ ] **Step 2: 失敗を確認**

Run: `python3 -m pytest skills/visual-explain/scripts/tests/test_narrative_sections.py -v`
Expected: FAIL（narrative kind が「未知の section-kind」で missing_provenance になる／expected.narrative 未検査）

- [ ] **Step 3: 実装**

`checker.py` `validate_final_provenance` — `elif kind == "compatibility":` ブロックの後に:

```python
        elif kind == "narrative":
            if not _ATTR_RE("data-ve-instance").search(attrs):
                diagnostics.append(Diagnostic(MISSING_PROVENANCE, "narrative セクションに instance がありません"))
```

`final_checks.py` `check_manifest_to_dom` — compatibility ループの後に:

```python
    for record in expected.narrative:
        if f'data-ve-instance="{record.instance_id}"' not in content:
            diagnostics.append(Diagnostic(MISSING_PROVENANCE,
                                          f"narrative '{record.instance_id}' が最終DOMにありません"))
    return diagnostics
```

- [ ] **Step 4: 全テストと check.sh selftest**

Run: `python3 -m pytest skills/visual-explain/scripts/tests -q && bash skills/visual-explain/scripts/check.sh --selftest`
Expected: 全緑 / PASS

- [ ] **Step 5: Commit**

```bash
git add -A skills/visual-explain
git commit -m "test(ve): gate narrative sections in final provenance and manifest-to-DOM checks"
```

---

### Task 4: SKILL.md / patterns.md の IR ファースト書き換え

**Files:**
- Modify: `skills/visual-explain/SKILL.md`（ワークフロー手順 5-6 = 現 46-47 行、canonical 節 = 現 146-158 行、互換節 = 現 160-169 行）
- Modify: `skills/visual-explain/references/patterns.md`（冒頭段落と JSON 例の節）

**Interfaces:**
- Consumes: Task 1-3 で実装した narrative kind（文書はこの実装と一致していなければならない）。
- Produces: 生成経路の記述が「IR ビルドが唯一の正規経路。skeleton 直編集は最終手段」で一貫した SKILL.md / patterns.md。

- [ ] **Step 1: ワークフロー手順 5 を置換**

現行（`assets/skeleton.html` を新しい資料へコピーし…）を次で置換:

> 5. **構成する:** assembly IR（JSON）を書く。`document`（id / title / summary）と `sections[]` に、散文（第一画面、主張と根拠、末尾節）は `kind: "narrative"`、図は `kind: "canonical"` を読み順で置き、`python3 scripts/build_explainer.py --assembly <IR.json> --output <絶対パス>` で生成する。skeleton をコピー・直編集しない。生成 HTML を手で直さない。narrative の markup は限定 HTML（見出し・段落・リスト・`details`・`.ask` など。`style` / `script` / `meta` / `iframe` / `form` は禁止）で、結論先行、必要時の用語表、型ごとの本文、必須の末尾節を入れる。schema は [references/assembly.schema.json](references/assembly.schema.json)、完全な JSON 例は [references/patterns.md](references/patterns.md)、描画規則はレンダラが保証する（[references/design-system.md](references/design-system.md) は目視確認の規範として読む）。

- [ ] **Step 2: ワークフロー手順 6 を置換**

> 6. **機械チェックする:** `bash scripts/check.sh <絶対パス>` を実行する（経路自動検出・四層検証）。FAIL は IR を修正して**再ビルド**し、成功するまで次へ進まない。

- [ ] **Step 3: canonical 節（現 146-158 行）の手順 5 前後を narrative 込みに更新**

「ビルドして検証する」の記述に、散文が `kind: "narrative"` として同じ assembly に入ること、`check.sh <html>`（--type 不要）で検証することを明記。段落末尾の「完全な JSON 例は references/patterns.md を参照する」は維持。

- [ ] **Step 4: 互換節（現 160-169 行）に skeleton 直編集の降格を明記**

節末に追加:

> skeleton 直編集（`assets/skeleton.html` をコピーして CONTENT を手書きする方式）は正規経路ではない。`build_explainer.py` を実行できない環境での最終手段としてだけ許され、その場合も `scripts/check.sh <絶対パス> --type <proposal|system|research>` を通し、資料が canonical 成功ではないことを利用者に報告する。同梱の `examples/example-proposal.html` は `examples/example-proposal.assembly.json` からの IR ビルド生成物であり、直編集の見本ではない。

- [ ] **Step 5: patterns.md 冒頭段落を置換**

現行冒頭（「固定骨格の TITLE:BEGIN と…間だけを編集する。…図はここにある HTML 契約どおりに埋め」）を次で置換。以降の共通契約・資料型テンプレート・図契約の本文は変更しない:

> この資料は assembly IR（JSON）の書き方と、レンダラが生成する図の契約を定める。作成者は IR に意味（関係・データ・散文・確度・出典）だけを宣言し、HTML は `scripts/build_explainer.py` が生成する。散文は `kind: "narrative"`、図は `kind: "canonical"`、未移行 legacy 図は `kind: "compatibility"`（provenance 必須）の section として一つの assembly に読み順で並べる。以下の HTML 契約はレンダラ出力と互換節検証の規範であり、手書きで埋める指示ではない。各セクションは **1つの問い**だけに答え、目安を**主張1行・根拠2〜3行**にする。図・表・短文のうち最短で明確に伝わる1つを主にし、図が短文より明確になる理由がないなら図を使わない。根拠は主張または図の近傍に置く。核心、制約、反証を折りたたみに隠してはならない。

- [ ] **Step 6: patterns.md の JSON 例の節に narrative + 三種混在の完全な assembly 例を 1 つ追加**

Task 3 の fixture `component-valid-narrative-mixed.json` と同構成の例を掲載（コピペで動く完全 JSON）。

- [ ] **Step 7: 残存する旧手順の検索と検証**

Run: `grep -rn "新しい資料へコピー\|間だけを編集" skills/visual-explain/SKILL.md skills/visual-explain/references/patterns.md && echo NG || echo OK`
Expected: OK（skeleton コピー・CONTENT 手編集の指示文の残存なし。互換節の降格文言は「コピーして…手書きする方式は正規経路ではない」という否定文なので該当しない）
Run: `python3 -m pytest skills/visual-explain/scripts/tests -q`
Expected: 全緑

- [ ] **Step 8: Commit**

```bash
git add skills/visual-explain/SKILL.md skills/visual-explain/references/patterns.md
git commit -m "docs(ve): make IR build the sole primary authoring route; demote skeleton direct-edit"
```

---

### Task 5: example-proposal を IR ビルドで再生成

**Files:**
- Create: `skills/visual-explain/examples/example-proposal.assembly.json`
- Modify: `skills/visual-explain/examples/example-proposal.html`（`build_explainer.py` の出力で全置換）

**Interfaces:**
- Consumes: Task 1-3 の narrative 経路。現 `example-proposal.html` の CONTENT 領域（現 296-403 行）が原文。
- Produces: 「実証済みの確実な経路」の証拠が IR ビルドを指す example ペア（assembly JSON + 生成 HTML）。

- [ ] **Step 1: 現 example の CONTENT を読み、次の対応で assembly JSON を書く**

| 現セクション | 変換先 |
| --- | --- |
| `.first-screen`（結論 + あなたが決めること + 条件2件） | narrative（markup は原文どおり） |
| `current-problem`（散文 + certainty + source-note） | narrative（原文どおり） |
| `approval-map` の `.layers` 図 | compatibility（markup 原文どおり、provenance = `legacy-html-insertion` / `unmigrated-format` / `layers`）。**実行時決定（2026-07-14 ユーザー承認）**: 原図は `契約例外` と `料金改定案` の二起点 DAG で、単一起点制約の `flow@2` へは因果の捏造なしに変換できないため、原文完全保持を優先して compat 維持とする。当初計画の rollback-condition への辺追加も不要となり撤回 |
| `approval-map` の見出しと前後の散文 | narrative（図の前後で分割してよい。読み順維持） |
| `before-after` の `.compare` | compatibility（markup 原文どおり、provenance = `legacy-html-insertion` / `unmigrated-format` / `compare`）。見出しと散文は narrative |
| `alternatives` の `.matrix` テーブル | canonical `matrix@2`（rows / columns / cells へ原文の全セル文言を移す）。見出しと散文は narrative |
| `.closing-section`（リスクと弱い前提 / 不確かな点、`.ask` ブロック含む） | narrative（原文どおり） |

可視テキストは全て原文どおり保持する（例外なし）。canonical 化で機械が生成する枠（figcaption / notes）と原文の重複が出る場合は、narrative 側から重複文を落とす方を選ぶ。

- [ ] **Step 2: ビルドして example を置換**

```bash
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/examples/example-proposal.assembly.json \
  --output skills/visual-explain/examples/example-proposal.html
```

Expected: `OK: ...example-proposal.html`

- [ ] **Step 3: 検証**

```bash
bash skills/visual-explain/scripts/check.sh "$(pwd)/skills/visual-explain/examples/example-proposal.html"
python3 -m pytest skills/visual-explain/scripts/tests -q
```

Expected: PASS / 全緑。加えて生成 HTML をブラウザで開き、第一画面 3 要素・承認地図・比較表・末尾節が原 example と同等に読めることを目視確認し、結果をタスク報告に書く。

- [ ] **Step 4: Commit**

```bash
git add skills/visual-explain/examples/
git commit -m "feat(ve): regenerate example-proposal from assembly IR (approval-map stays compatibility per two-source DAG decision)"
```

---

### Task 6: 全体検証と draft PR

**Files:**
- なし（検証と PR 作成のみ）

**Interfaces:**
- Consumes: Task 1-5 の全成果。
- Produces: draft PR。merge はユーザー判断。

- [ ] **Step 1: フル検証**

```bash
python3 -m pytest skills/visual-explain/scripts/tests -q
bash skills/visual-explain/scripts/check.sh --selftest
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/scripts/tests/component-valid-narrative-mixed.json \
  --output /tmp/ve-narrative-smoke.html && \
  bash skills/visual-explain/scripts/check.sh /tmp/ve-narrative-smoke.html
```

Expected: 全緑 / PASS / OK+PASS

- [ ] **Step 2: 差分の最終レビュー**

`git log --oneline main..HEAD` と `git diff main --stat` を確認し、skeleton.html / assets/components/*.css / registry.json に差分がないことを確認する（Global Constraints）。

- [ ] **Step 3: push と draft PR**

```bash
git push -u origin feat/ir-narrative-sections
gh pr create --draft --title "feat(ve): narrative sections make IR build the sole primary route" \
  --body "<変更概要・検証結果・rollback-condition 辺追加の注記を含める>"
```

Expected: draft PR の URL。merge はユーザー判断。
