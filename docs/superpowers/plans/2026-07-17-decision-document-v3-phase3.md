# 判断資料 v3 Phase 3（表現拡張）実装計画

> **For agentic workers:** この計画はタスク単位で実装する。各タスクは TDD（失敗するテスト→最小実装→パス→コミット）で進め、チェックボックス（`- [ ]`）で進捗を管理する。正本 spec: `docs/superpowers/specs/2026-07-16-decision-document-v3-design.md`。計画と spec が矛盾したら実装せず報告する。

## Goal

新 canonical 部品 `code`（両 profile）と `image`（extended 限定・data: URI 埋め込み）、レンダラ用 SVG 許可リストの拡張（`path` / `polyline` / `marker`）、extended 限定の freeform セクション（広いが閉じた許可リスト契約）、skeleton CSP の `img-src data:` 改定を実装し、強モデル向けの表現上限を解放する。

## Architecture

すべて既存の単一経路（validation → registry 絞り込み → 明示選択 → 信頼レンダラ → composer / flattener → 最終検査 → atomic write）への**語彙追加**として実装する。`code` / `image` は既存 12 形式と同じ canonical 部品の機構（`component-vocabulary.json` ＋ `registry.json` ＋ `renderers/` ＋ manifest ＋ `_check_*_artifact` 最終検査）に乗せ、新しい経路は作らない。image の入力契約（厳密 base64 decode・magic bytes 照合・寸法/バイト上限）は標準ライブラリのみの純関数モジュール `image_contract.py` に隔離し、IR 段階（validation）と生成物段階（component checker）の両方から同じ関数を呼ぶ。

freeform は「任意の HTML」ではなく**閉じた許可リスト契約**の新セクション種別として実装する。許可リスト検査は新モジュール `freeform_checks.py` が担い、IR 段階で全 markup を検査する。provenance はモデルの markup ではなく**レンダラが wrapper に付与**する（`data-ve-provenance-*` は予約 data 属性なので narrative / freeform 本文では書けず、偽装できない）。検査群④の緩和は最終文書層の safety parser に「freeform wrapper スコープ追跡」を追加して実現する — freeform 内ではインライン `style`（プロパティ許可リスト検証つき）と拡張タグを許し、検査群①（script・イベント属性・外部参照）②（自己完結）③（正直さ・確度語彙）は freeform 内にも全適用する。data: URI の `img src` は **image 部品 wrapper 内のみ**の scoped 許可とし、narrative / compatibility / freeform では引き続き拒否する（freeform の HTML 許可リストに `img` は入れない）。

skeleton の変更は **CSP 1 行のみ**（`img-src 'none'` → `img-src data:`）を Task 8 に隔離する。固定領域ハッシュが変わるため、Phase 2 と同じ手順で全 HTML fixture の resplice ＋ KEEP_AS_IS 6 件のテキスト同期を必ず行う。

**前提: Phase 2（判断回収）実装がマージ済みの main から着手する。** skeleton は Phase 2 で回収 JS 入りに改定済みで、Phase 3 の skeleton 差分は CSP 行だけになる。Phase 2 未マージの時点で着手した場合は Task 8 の resplice が二重差分になるため、着手前に必ず main の状態を確認して報告する。

## Tech Stack

Python 3 標準ライブラリのみ（実装・検査とも。画像ヘッダ解析も `base64` / `re` / バイト演算だけで行い、Pillow 等は導入しない）。テストは pytest（開発時専用）。Phase 3 は新規 JS を書かないため、Phase 2 の node ハーネスは変更しない。

## テスト戦略

- 決定的な検査（IR 契約・レンダラ出力・checker・CSP 文字列）はすべて pytest ＋ `check.sh --selftest` で固定する。
- 新部品は既存慣例を踏襲する: `component-valid-*.json` / `component-bad-*.json`（IR fixture）＋ renderer / checker ユニットテスト＋ `*-doc.html`（必要時）。
- ブラウザ確認は**目視 QA のみ**（Phase 2 で確立した「Playwright 等の外部テストツールを導入しない」方針を踏襲。Phase 3 は新規 JS がなく、確認対象は code / image / freeform の静的描画と CSP 下での画像表示だけ）。QA 記録は `.runs/decision-doc-v3-p3/qa/` に保存する。
- image の入力契約は純関数（`image_contract.py`）に隔離してユニットテストで網羅する（正常 3 MIME / SVG data URI 拒否 / magic 不一致 / 上限超過 / 壊れた base64）。

## Global Constraints

- **前提となる main**: Phase 2 実装マージ済み。Phase 1 の検証証拠（`.runs/decision-doc-v3-p1/`）・Phase 2 の検証証拠（`.runs/decision-doc-v3-p2/`）・既存 fixture は保持し変更しない（Task 8 の resplice による固定領域更新を除く）。Phase 3 の検証アーティファクトはすべて `.runs/decision-doc-v3-p3/`（QA 記録は `qa/`）に置く。
- `assets/skeleton.html` の変更は **Task 8 のみ**で行い、変更は CSP の `img-src` 1 箇所に限る。skeleton は固定領域を SHA-256 でバイト一致検証されるため、1 バイトの変更も checker・全テスト・既存生成物に波及する。変更後は `scripts/tests/tools/resplice.py` で全 HTML fixture を一括再生成し、KEEP_AS_IS の 6 fixture へ同一編集をテキスト置換で適用する（resplice.py docstring の規約）。
- Python 3 標準ライブラリのみ。Pillow / numpy 等の画像ライブラリ、Playwright / Selenium / Puppeteer / jsdom 等の外部テストツール、npm / pip パッケージの追加は禁止。
- 診断メッセージは日本語。既存テストは診断文字列の完全一致で検証するため、既存文言の変更は対応するテスト・selftest 期待値の更新を伴う。
- テストは必ず `skills/visual-explain/scripts/` から `python3 -m pytest tests -q` で実行する（`ve_components` を cwd 経由で import するため）。
- コミットは conventional commits ＋ `(ve)` スコープ（例: `feat(ve): ...`）。1 タスク 1 コミット以上。ファイル変更とコミットを必ず対応させる。
- 予約 data 属性・予約 class は Phase 2 までの一覧を維持する。Phase 3 で新設する `data-ve-provenance-source` / `data-ve-provenance-reason` / `data-ve-line` / `data-ve-line-ref` / `data-ve-annotated` / `data-ve-language` はすべて既存の予約プレフィックス `data-ve-*` に収まるため一覧の追加は不要。
- profile 制約（spec 70 行目）: `code` は両 profile、`image` は **extended のみ**、freeform は **extended のみ**。strict 文書への混入は IR 段階でビルド拒否し、生成物段階でも検査群③が拒否する（Phase 1 の `_EXTENDED_ONLY_KINDS` を活用）。
- 色規律: 新規 component CSS（`code.css` / `image.css`）はモノクロ（意味色トークン・生 hex 禁止。`test_skeleton_audit.py` の ColorDiscipline 監査が全 component CSS に自動適用されるよう対象リストへ追加する）。
- YAGNI: シンタックスカラー、code 部品の自動レイアウト、コネクタの非隣接接続解放、宣言的グラフ部品、タブ・サイドバー目次は実装しない（spec スコープ外）。
- canonical IR の禁止キー（`FORBIDDEN_AUTHORING_KEYS`: `style` / `width` / `height` / `path` 等）に抵触するフィールド名を新 payload に導入しない（本計画の payload キーは `language` / `lines` / `annotations` / `alt` / `dataUri` で全て非抵触）。
- 数値上限（spec 85 行目の verbatim 値＋本計画の補完値）:
  - 警告基準（spec）: 1 画像 500KB（512,000 バイト）・文書合計 2MB（2,097,152 バイト）
  - 絶対拒否上限（spec）: 1 画像 2MB（2,097,152 バイト）・文書合計 8MB（8,388,608 バイト)
  - 寸法上限（spec は「上限を置く」のみ・値は本計画で確定）: 1 辺 4096px・総ピクセル 16,777,216（4096×4096）
  - code 上限（本計画で確定）: 80 行・1 行 160 文字・注記 8 件

## ファイル構成（新規/変更の全体地図）

- 新規 `scripts/ve_components/image_contract.py` — image 入力契約の純関数群（data URI 厳密 decode・magic bytes 照合・寸法解析・バイト/ピクセル上限・警告判定）。1 責務: バイト列→契約判定。
- 新規 `scripts/ve_components/freeform_checks.py` — freeform 許可リスト検査（HTML / SVG の要素**と要素別属性**・インライン style プロパティ・URL を取り得る属性値・文書内参照整合・禁止群・SVG 理由コメント義務）。**IR 段階と生成物段階の両方から同じ関数を呼ぶ**（spec 72 行目「同じ判定を再現」）。
- 新規 `scripts/ve_components/renderers/code.py` / `renderers/image.py` — 信頼レンダラ。
- 新規 `assets/components/code.css` / `assets/components/image.css` — component CSS（モノクロ）。
- 変更 `references/component-vocabulary.json` — `code` / `image` の語彙登録（relationshipKind / capabilities）。
- 変更 `assets/components/registry.json` — `code@1` / `image@1` の registry 登録（asset digest 含む）。
- 変更 `scripts/ve_components/model.py` — `CodePayload` / `CodeAnnotation` / `ImagePayload` / `FreeformSection` の dataclass 追加、`CanonicalIR` への payload 追加。
- 変更 `scripts/ve_components/validation.py` — 新 payload の検証、freeform セクションの検証（extended 限定・予約属性禁止）、image の extended 限定、文書合計バイトの拒否。
- 変更 `scripts/ve_components/checker.py` — data: URI の scoped 許可（image wrapper 内のみ）、freeform wrapper 内の style 緩和（検査群④の profile 依存）、SVG 許可リスト拡張、`_check_code_artifact` / `_check_image_artifact` の追加。
- 変更 `scripts/ve_components/assembly.py` — `process_freeform_section`（許可リスト検査＋ provenance wrapper 付与）。
- 変更 `scripts/ve_components/document_checks.py` — freeform wrapper の provenance 自己表明検査、strict 文書での `data-ve-component="image"` 拒否。
- 変更 `scripts/build_explainer.py` — freeform の dispatch・TOC 参加・image 警告の stderr 出力。
- 変更 `scripts/check.sh` — selftest ケース追加（data: URI 越境・strict への freeform / image 混入・freeform 生成物改竄 6 種）。
- 変更 `assets/skeleton.html` — CSP 1 行のみ（**Task 8 のみ**）。
- 変更 `scripts/tests/test_skeleton_audit.py` — CSP 完全一致テスト・component CSS 監査対象の追加。
- 再生成 `scripts/tests/*.html` fixture 一式（resplice）。
- 新規 `examples/example-extended.assembly.json` / `examples/example-extended.html` — extended 見本（code ＋ image ＋ freeform を含む research 型）。
- 改訂 `SKILL.md` / `references/patterns.md` / `references/assembly.schema.json` / `references/component-ir.schema.json` / `references/design-system.md` / `scripts/tests/fixtures.md` / リポジトリ `CLAUDE.md`。

---

### Task 1: code 部品の IR（payload・validation・語彙登録）

**Files:**
- Modify: `scripts/ve_components/model.py`（`CodeAnnotation` / `CodePayload` 追加、`CanonicalIR.code` フィールドと `payload_kind` / `semantic_ids` への追加）
- Modify: `scripts/ve_components/validation.py`（`_IR_KEYS` に `"code"`、payload 検証関数）
- Modify: `references/component-vocabulary.json`（`code` 語彙）
- Modify: `references/component-ir.schema.json` / `references/assembly.schema.json`（schema 追記）
- Test: `scripts/tests/test_code_ir.py`（新規）

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class CodeAnnotation:
    id: str
    line: int          # 1 始まり。lines の範囲内
    text: str


@dataclass(frozen=True)
class CodePayload:
    language: str                       # 表示用言語名（非空）
    lines: tuple[str, ...]              # 1..80 行・各行 160 文字以下・全行空は拒否
    annotations: tuple[CodeAnnotation, ...] = ()   # 最大 8 件・行番号重複禁止
```

- IR キー: `"code": {"language": ..., "lines": [...], "annotations": [{"id","line","text"}]}`。takeaway caption は canonical 共通の `caption` を使う（専用フィールドを増やさない）。
- 語彙: `component-vocabulary.json` に `"code": {"relationshipKind": "annotated-code", "capabilities": ["line-annotation", "takeaway-caption"]}` を追加（`_KIND_TO_COMPONENT` / `_ALL_CAPABILITIES` は vocabulary から自動導出される）。
- 検証規則と診断文言: 言語非空（`"code.language は空にできません"`）、行数 1〜80（`"code.lines は1〜80行である必要があります"`）、1 行 160 文字以下（`"code の行が長すぎます（160文字以下）: 行 <n>"`）、全行空白のみ拒否（`"code.lines に内容がありません"`）、annotation の行範囲（`"code の注記が存在しない行を参照しています: <line>"`）、注記 8 件以下・行番号重複禁止・text 非空・id は semantic id 一意規則に参加。
- `CanonicalIR.semantic_ids()` に annotation の id を追加する（manifest 完全性検査が消費を強制する）。

- [ ] **Step 1: 失敗するテストを書く**（正常 IR が `validate_assembly` を通り `CodePayload` になる / annotation 範囲外 FAIL / 81 行 FAIL / language 空 FAIL / 行番号重複 FAIL。fixture は `component-valid-code.json` を新設し、既存 `component-valid-kpi.json` の envelope（document / first-screen / closing）に倣う）
- [ ] **Step 2: 失敗確認** — Run: `cd skills/visual-explain/scripts && python3 -m pytest tests/test_code_ir.py -q` / Expected: FAIL（`assembly に不正なフィールド 'code'` 系）
- [ ] **Step 3: 実装** — model / validation / vocabulary / schema を上記契約どおり追加。validation は既存 payload 検証（`_validate_kpi` 等）の形式に揃える。
- [ ] **Step 4: 全テストパス確認** — Run: `python3 -m pytest tests -q` / Expected: PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(ve): add code component IR with line annotations"`

**done_criteria:** `component-valid-code.json` が IR 検証を通過し、上記 6 種の contract violation がそれぞれ日本語診断で拒否される。既存全テスト PASS。

---

### Task 2: code レンダラ・CSS・registry・構造検査

**Files:**
- Create: `scripts/ve_components/renderers/code.py`
- Create: `assets/components/code.css`
- Modify: `scripts/ve_components/renderers/__init__.py`（`TRUSTED_RENDERERS` に `code@1`）
- Modify: `assets/components/registry.json`（`code@1` エントリ。asset digest は `shasum -a 256 assets/components/code.css` で採る）
- Modify: `scripts/ve_components/checker.py`（`_check_code_artifact` 追加＋ artifact 検査辞書へ登録）
- Test: `scripts/tests/test_code_renderer.py`（新規）＋ `scripts/tests/component-bad-code-*.json` / `component-bad-code-structure.html`

**Interfaces:**
- Consumes: `CodePayload`（Task 1）。
- Produces: `render_code(section, definition) -> RenderResult`。markup 契約（checker が完全一致で再検証する規範）:

```html
<figure data-ve-component="code" role="group" aria-label="<accessibility.label>"
 aria-describedby="<id>-summary">
<figcaption id="<id>-caption" class="ve-code-caption"><caption></figcaption>
<p id="<id>-summary" class="ve-code-summary"><accessibility.summary></p>
<pre class="ve-code" data-ve-language="<language>"><code><span class="ve-code-line" data-ve-line="1">escaped line
</span><span class="ve-code-line" data-ve-line="2" data-ve-annotated="<annotation-id>">…
</span></code></pre>
<ol class="ve-code-notes"><li data-ve-semantic-id="<annotation-id>" data-ve-line-ref="2">L2: <text></li></ol>
</figure>
```

- 行番号の表示は CSS counter で行う（`data-ve-line` は機械検証用。authored 番号を持たない＝決定的）。シンタックスカラーは実装しない: `<code>` 直下の子要素は `span.ve-code-line` のみ許可（構造検査で強制）。
- `_check_code_artifact(body, parser) -> list[Diagnostic]`: 行 span 数と `data-ve-line` の 1..N 連番一致、`data-ve-line-ref` が実在行を指す、`data-ve-annotated` と notes の対応、`data-ve-language` 非空、`code` 内に `ve-code-line` 以外の要素があれば拒否（診断: `"code に許可されない子要素があります"` — シンタックスカラー span の混入をここで塞ぐ）。既存 `_check_kpi_artifact`（`checker.py:1600`）の形式に揃え、`checker.py:1639` の辞書へ `"code"` を登録する。
- `code.css`: `.ve-code` は等幅・`overflow-x: auto`・counter による行番号・注記行の下線強調。モノクロ（`--text` / `--text-dim` / `--surface` / `--border` のみ）。spacing は `var(--space-*)`。

- [ ] **Step 1: 失敗するテストを書く**（component-valid-code.json のビルドで上記 markup 契約の各要素が出る / annotation なしでも成立 / `_check_code_artifact` が「行番号飛び」「未知 line-ref」「code 内の余分な span class」を拒否する。bad fixture: `component-bad-code-structure.html` は valid をビルド後に `data-ve-line="2"` を `"5"` へ改竄して保存し、fixture ヘッダコメントに破壊内容を記す）
- [ ] **Step 2: 失敗確認** — Run: `python3 -m pytest tests/test_code_renderer.py -q` / Expected: FAIL（ImportError / registry 未登録）
- [ ] **Step 3: 実装** — renderer は `renderers/kpi.py` の manifest 生成（`consumed_semantic_ids` / `asset_ids` / digest）に揃える。registry エントリの `checkerRules` は `["static-content", "semantic-ids", "code-structure", "escaping", "no-external-reference"]`。
- [ ] **Step 4: 全テストパス確認** — Run: `python3 -m pytest tests -q` と `bash check.sh --selftest` / Expected: PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(ve): add code component renderer with deterministic line annotations"`

**done_criteria:** code を含む assembly が build → check.sh PASS まで通り、構造改竄 fixture が component checker で FAIL する。CSS モノクロ監査（Task 8 で対象リストへ追加するまでは手元確認）に違反しない。

---

### Task 3: image 入力契約の純関数群（image_contract.py）

**Files:**
- Create: `scripts/ve_components/image_contract.py`
- Test: `scripts/tests/test_image_contract.py`（新規）

**Interfaces:**
- Produces（すべて純関数・標準ライブラリのみ）:

```python
ALLOWED_IMAGE_MIMES = frozenset({"image/png", "image/jpeg", "image/webp"})
WARN_IMAGE_BYTES = 500 * 1024          # spec: 警告 1 画像 500KB
WARN_DOCUMENT_BYTES = 2 * 1024 * 1024  # spec: 警告 文書合計 2MB
MAX_IMAGE_BYTES = 2 * 1024 * 1024      # spec: 拒否 1 画像 2MB
MAX_DOCUMENT_BYTES = 8 * 1024 * 1024   # spec: 拒否 文書合計 8MB
MAX_IMAGE_DIMENSION = 4096             # 本計画で確定（spec は「上限を置く」）
MAX_IMAGE_PIXELS = 4096 * 4096

@dataclass(frozen=True)
class ImageCheckResult:
    mime: str | None
    byte_size: int
    width: int | None
    height: int | None
    diagnostics: tuple[str, ...]   # 拒否（メッセージ文字列。呼び出し側が Diagnostic 化）
    warnings: tuple[str, ...]      # 警告（fail しない）

def decode_data_uri(uri: str) -> tuple[str, bytes] | str: ...
    # 成功: (宣言 MIME, decode 済みバイト列)。失敗: 診断メッセージ文字列。
    # ^data:image/(png|jpeg|webp);base64,<厳密 base64>$ 以外は全て拒否
    #（image/svg+xml は script を持ち得るため常に拒否。charset 等のパラメータ付きも拒否）。
    # base64 は base64.b64decode(data, validate=True) で厳密 decode。
def sniff_mime(raw: bytes) -> str | None: ...        # magic bytes から実 MIME を判定
def image_dimensions(mime: str, raw: bytes) -> tuple[int, int] | None: ...
def check_image(uri: str) -> ImageCheckResult: ...   # 上記を束ねた入口（1 画像分）
def collect_document_warnings(results: tuple[ImageCheckResult, ...]) -> tuple[str, ...]: ...
    # 文書順に各画像の warnings を連結し、decode 後バイト合計が WARN_DOCUMENT_BYTES を
    # 超えたら文書合計警告（"WARN: image の文書合計が 2MB を超えています（<bytes> バイト）"）を
    # 末尾に 1 件追加する。同一文言は初出のみ残す（重複排除）。
```

- 閾値の境界規則（警告・拒否とも共通）: **閾値ちょうどは許容、1 バイト超過で発火**（`>` 比較）。寸法・ピクセルも同じ（4096 は許容・4097 で拒否）。

- 診断文言: `"image の data URI は data:image/(png|jpeg|webp);base64 形式だけ使えます"` / `"image の base64 を decode できません"` / `"image の magic bytes が宣言 MIME と一致しません: 宣言 <mime> / 実体 <sniffed|不明>"` / `"image が大きすぎます（1 画像 2MB 以下）: <bytes> バイト"` / `"image の寸法を解析できません"` / `"image の寸法が上限を超えています（1 辺 4096px・総ピクセル 16,777,216 以下）: <w>x<h>"`。警告文言: `"WARN: image が 500KB を超えています（<bytes> バイト）。埋め込みサイズの削減を検討してください"`。
- サイズは **decode 後のバイト数**で計測する（spec 85 行目）。

- [ ] **Step 1: 失敗するテストを書く（RED）** — 実 fixture として最小の実画像バイトを使う: 1x1 PNG は `base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")`。JPEG / WebP はテスト内でヘッダを合成する（JPEG: `b"\xff\xd8\xff\xe0" + b"\x00\x10JFIF..." + SOF0 セグメント`、WebP: `b"RIFF" + size + b"WEBPVP8 "` ＋ 合成フレームタグ）。ケース: PNG 正常 decode と寸法 (1,1) / SVG data URI 拒否 / `data:image/png;base64,` に JPEG バイトで magic 不一致 / validate=True で壊れた base64 拒否 / 2MB ちょうど許容・2MB+1 バイトで拒否 / 500KB ちょうど警告なし・500KB+1 バイトで警告のみ / 4096px 許容・4097px 幅の合成 PNG（IHDR の width を書き換えた 24 バイト）で寸法拒否 / 総ピクセル超過 / `collect_document_warnings`: 合計 2MB ちょうど警告なし・+1 バイトで文書合計警告が末尾に付く・個別警告が文書順・同一文言の重複排除
- [ ] **Step 2: 失敗確認** — Run: `python3 -m pytest tests/test_image_contract.py -q` / Expected: FAIL（ImportError）
- [ ] **Step 3: 実装（GREEN）** — 寸法解析の実装:

```python
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def sniff_mime(raw: bytes) -> str | None:
    if raw.startswith(_PNG_MAGIC):
        return "image/png"
    if raw.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    return None


def _png_dimensions(raw: bytes) -> tuple[int, int] | None:
    if len(raw) < 24 or raw[12:16] != b"IHDR":
        return None
    return (int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big"))


def _jpeg_dimensions(raw: bytes) -> tuple[int, int] | None:
    # SOF マーカー（C0-CF、ただし C4/C8/CC を除く）を走査する。
    i = 2
    while i + 4 <= len(raw):
        if raw[i] != 0xFF:
            return None
        marker = raw[i + 1]
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        length = int.from_bytes(raw[i + 2:i + 4], "big")
        if length < 2:
            return None
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            if i + 9 > len(raw):
                return None
            height = int.from_bytes(raw[i + 5:i + 7], "big")
            width = int.from_bytes(raw[i + 7:i + 9], "big")
            return (width, height)
        i += 2 + length
    return None


def _webp_dimensions(raw: bytes) -> tuple[int, int] | None:
    if len(raw) < 30 or raw[:4] != b"RIFF" or raw[8:12] != b"WEBP":
        return None
    chunk = raw[12:16]
    if chunk == b"VP8X":
        return (int.from_bytes(raw[24:27], "little") + 1,
                int.from_bytes(raw[27:30], "little") + 1)
    if chunk == b"VP8L":
        if raw[20] != 0x2F:
            return None
        bits = int.from_bytes(raw[21:25], "little")
        return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
    if chunk == b"VP8 ":
        if raw[23:26] != b"\x9d\x01\x2a":
            return None
        return (int.from_bytes(raw[26:28], "little") & 0x3FFF,
                int.from_bytes(raw[28:30], "little") & 0x3FFF)
    return None
```

`decode_data_uri` は `re.fullmatch(r"data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/]+={0,2})", uri)` で形式を固定し、`base64.b64decode(payload, validate=True)` の例外を拒否診断へ変換する。`check_image` は decode → サイズ拒否/警告 → magic 照合 → 寸法解析 → 寸法拒否の順に束ねる。

- [ ] **Step 4: パス確認** — Run: `python3 -m pytest tests/test_image_contract.py -q` / Expected: PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(ve): add stdlib-only image input contract with magic byte and dimension gates"`

**done_criteria:** 3 MIME の正常系・SVG 拒否・magic 不一致・base64 破損・バイト/寸法/ピクセル上限（境界値: ちょうど許容・超過で発火）・警告閾値・文書合計集約（順序・重複排除）がすべて純関数テストで固定される。外部ライブラリ import なし。

---

### Task 4: data: URI の scoped 解放（checker 両層）

image 部品 wrapper 内**だけ**で `data:image/(png|jpeg|webp);base64` の `img src` を許す。narrative / compatibility / freeform / wrapper 外の CONTENT では従来どおり全拒否。

**Files:**
- Modify: `scripts/ve_components/checker.py`（`_ContentSafetyParser` にスコープ追跡と `_check_src` の分岐追加）
- Modify: `scripts/check.sh`（埋め込み checker の `ContentInspector.check_url` に同じ scoped 許可）
- Create: `scripts/tests/bad-data-uri-img.html`（image wrapper 外の data:image src を持つ legacy fixture）
- Modify: `scripts/check.sh` selftest cases（上記 fixture を期待診断つきで登録）
- Test: `scripts/tests/test_component_checker.py`（既存へケース追加）

**Interfaces:**
- Produces: 許可条件は **3 条件の AND** に限定する（r1 I1）:
  1. 要素が `img` で、属性が名前空間なしの `src` であること（`video` / `source` / 名前空間つき属性は対象外＝従来どおり拒否）。
  2. 値が `data:image/(png|jpeg|webp);base64,<厳密 base64>` に完全一致すること。
  3. 最も内側の開いているスコープが「**他の `data-ve-section-kind` wrapper に入れ子になっていない** `section[data-ve-section-kind="canonical"][data-ve-component="image"]`」の配下であること。スコープ追跡は wrapper 種別スタックで行い、compatibility / narrative / freeform wrapper が既に開いている間は image スコープを**開かない**（compatibility は予約属性を書けるため、`data-ve-component="image"` の偽装 wrapper を compatibility 内に置いても許可されない）。
- `_check_src` の呼出し契約を `_check_src(self, tag: str, name: str, v: str)` に変更する（呼び出し元 `_check` はタグ名と属性名を渡す）。
- 非許可時の診断: 形式が data:image に一致するがスコープ外 → `"data: URI は image 部品の中でだけ使えます: <値の先頭 40 文字>"`。それ以外の data: は従来どおり `"許可されない URL スキームです"`。
- narrative / compatibility 経路（`section_kind` 指定あり）は**変更なし**（IR 段階では常に全拒否）。scoped 許可が効くのは最終文書検査（`section_kind=None`）だけ。
- `check.sh` 埋め込み checker: `ContentInspector` は既にタグスタックを持つ（`check.sh:178`）。`handle_starttag` で wrapper 種別スタック（`data-ve-section-kind` 値）を同様に管理し、`check_url` の `<img> の src` 分岐で同じ 3 条件の data:image を許可する。

- [ ] **Step 1: 失敗するテストを書く**（手書き wrapper markup で: canonical image wrapper 内の `img src` data:image PASS / 同 wrapper 内でも `video src` の data:image FAIL / wrapper 内の data:image/svg+xml FAIL / wrapper 外 data:image FAIL / narrative 内 data:image FAIL / **compatibility wrapper の内側に置いた偽装 `section[data-ve-component="image"]` 内の data:image FAIL** / section を伴わない手書き `figure[data-ve-component="image"]` 単体 FAIL）
- [ ] **Step 2: 失敗確認** — Run: `python3 -m pytest tests/test_component_checker.py -k data_uri -q` / Expected: FAIL
- [ ] **Step 3: 実装** — `_ContentSafetyParser.__init__` に `self._stack: list[str] = []` / `self._wrapper_kinds: list[tuple[int, str]] = []`（開いた wrapper の (深さ, section-kind)）/ `self._image_scopes: list[int] = []` を追加。`handle_starttag` で非 void タグを push し、`data-ve-section-kind` を持つ `section` は `_wrapper_kinds` へ記録。**`_wrapper_kinds` が空のときに限り**、`section` かつ `data-ve-section-kind="canonical"` かつ `data-ve-component="image"` なら `_image_scopes.append(len(self._stack))`。`handle_endtag` で pop し、スタック長が開始深さより浅くなったら各スコープを閉じる。`_check_src`:

```python
    _DATA_IMAGE_RE = re.compile(r"^data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}$")

    def _check_src(self, tag: str, name: str, v: str) -> None:
        if v.lower().startswith("data:"):
            allowed_scope = (tag == "img" and name == "src" and bool(self._image_scopes))
            if self._DATA_IMAGE_RE.fullmatch(v):
                if allowed_scope:
                    return
                self.diagnostics.append(Diagnostic(
                    FORBIDDEN_CONTENT_MARKUP, f"data: URI は image 部品の中でだけ使えます: {v[:40]}"))
                return
        # 以降は既存の external / scheme 検査をそのまま適用
```

（`_check` は `local == "src"` の分岐で `self._check_src(tag, name, v)` を渡す。名前空間つき `src` は `name != "src"` となり scoped 許可の対象外）

- [ ] **Step 4: check.sh 側の実装と selftest 追加** — `bad-data-uri-img.html`（`valid-proposal.html` を複製し CONTENT に `<img src="data:image/png;base64,iVBORw0KG...">` を素で置く）を作り、期待診断 `("<img> の src: data: URI は image 部品の中でだけ使えます",)` 相当（埋め込み checker の文言に合わせる）で selftest へ登録。
- [ ] **Step 5: パス確認** — Run: `python3 -m pytest tests -q` と `bash check.sh --selftest` / Expected: PASS
- [ ] **Step 6: Commit** — `git commit -m "feat(ve): allow data image URIs only inside the image component scope"`

**done_criteria:** data:image が「img の src × 最上位 canonical image wrapper 内」でのみ両層（component checker / check.sh 埋め込み checker）を通過し、越境・非 img 要素・SVG data URI・narrative 混入・compatibility 内の偽装 wrapper がすべて FAIL として fixture 固定される。

---

### Task 5: image 部品（IR・extended 限定・レンダラ・registry・最終検査・警告出力）

**Files:**
- Modify: `scripts/ve_components/model.py`（`ImagePayload(alt, data_uri)` 追加、`CanonicalIR.image`）
- Modify: `scripts/ve_components/validation.py`（payload 検証＝`image_contract.check_image` 呼び出し・extended 限定・必須 caption / sources・文書合計バイト拒否）
- Create: `scripts/ve_components/renderers/image.py` / `assets/components/image.css`
- Modify: `references/component-vocabulary.json` / `assets/components/registry.json`（`image@1`）
- Modify: `scripts/ve_components/checker.py`（`_check_image_artifact`: 最終文書で decode・magic・上限を再検証）
- Modify: `scripts/ve_components/document_checks.py`（strict 文書の `data-ve-component="image"` 拒否を `_check_strict_excludes_extended` へ追加。診断: `"strict プロファイルに extended 限定部品は置けません: image"`）
- Modify: `scripts/build_explainer.py`（`collect_document_warnings` の結果を stderr へ出力・exit 0 のまま）
- Create: `scripts/tests/structure-bad-image-strict.html`＋ `scripts/check.sh` selftest 登録（生成物段階の profile 排他。r1 I4）
- Test: `scripts/tests/test_image_component.py`（新規）＋ `component-valid-image.json` / `component-bad-image-*.json`

**Interfaces:**
- Produces: `ImagePayload(alt: str, data_uri: str)`。IR キー: `"image": {"alt": ..., "dataUri": ...}`。caption（canonical 共通・takeaway）と `sources`（出所・**1 件以上必須**）は共通スロットを使う — spec 85 行目の「`alt`・caption・出所を必須フィールド」を共通スロット必須化で満たす。
- 語彙: `"image": {"relationshipKind": "evidential-image", "capabilities": ["image-evidence"]}`。
- validation: `document.profile != "extended"` で image payload を拒否（診断: `"image は extended プロファイル限定です"`）。`image_contract.check_image` の diagnostics を ContractError へ変換。assembly 内の全 image の decode 後バイト合計が 8MB 超で拒否（`"image の文書合計が上限を超えています（合計 8MB 以下）: <bytes> バイト"`）。**警告は validation の責務にしない**（r1 I2）: `build_explainer.build_document` が validation 通過後に全 image payload を文書順で `image_contract.check_image` にかけ、`image_contract.collect_document_warnings(results) -> tuple[str, ...]`（Task 3。文書順・重複排除・合計警告は末尾）の戻り値を stderr へ 1 行ずつそのまま出力する（各行は `WARN:` 接頭辞を含む。exit code は 0 のまま）。
- レンダラ markup 契約:

```html
<figure data-ve-component="image" role="group" aria-label="<accessibility.label>"
 aria-describedby="<id>-summary">
<img class="ve-image" src="<dataUri>" alt="<alt>" width="<w>" height="<h>">
<figcaption id="<id>-caption" class="ve-image-caption"><caption></figcaption>
<p id="<id>-summary" class="ve-image-summary"><accessibility.summary></p>
<ul class="ve-image-notes"><li data-ve-semantic-id="<source-id>"><strong>出典 <label></strong>（<detail>）</li></ul>
</figure>
```

`width` / `height` は decode 済み寸法から埋める（レイアウト安定・HTML 属性であり SVG 整数座標ゲートとは無関係）。`image.css`: `.ve-image { max-width: 100%; height: auto; }` ＋ figure の余白（モノクロ・`var(--space-*)`）。
- `_check_image_artifact`: 最終文書の wrapper 内 `img` に対し src の data URI を **`image_contract.check_image` で再検証**（IR と生成物の二重検査 — spec 72 行目の「同じ判定を再現」に揃える）し、alt 非空・width/height 属性と実寸法の一致・文書内全 image の合計バイト 8MB 以下を検査する。

- [ ] **Step 1: 失敗するテストを書く**（extended で 1x1 PNG がビルド PASS / strict で IR 拒否 / sources 空で拒否 / alt 空で拒否 / magic 不一致 IR 拒否 / 改竄 fixture（width 属性を実寸と変える）が最終検査 FAIL / **strict 改竄 fixture** `structure-bad-image-strict.html`（extended image 文書ビルド後に first-screen の `data-ve-profile` を `strict` へ改竄・ヘッダコメントに破壊内容を記す）が生成物段階で FAIL（診断: `"strict プロファイルに extended 限定部品は置けません: image"`）/ 500KB 超で stderr に WARN 行・500KB ちょうどで WARN なし〔`capsys` で捕捉〕）
- [ ] **Step 2: 失敗確認** — Run: `python3 -m pytest tests/test_image_component.py -q` / Expected: FAIL
- [ ] **Step 3: 実装** — renderer は `renderers/kpi.py` の manifest 形式に揃える。`component-valid-image.json` の dataUri には Task 3 の 1x1 PNG base64 を使う。
- [ ] **Step 4: selftest 登録と全テストパス確認** — `structure-bad-image-strict.html` を `check.sh` selftest の structure_cases へ期待診断つきで登録してから、Run: `python3 -m pytest tests -q` と `bash check.sh --selftest` / Expected: PASS（この時点で CSP は未改定だが、CSP はブラウザ表示のみに影響し検査には影響しない — 表示確認は Task 8 以降の QA で行う）
- [ ] **Step 5: Commit** — `git commit -m "feat(ve): add extended-only image component with strict data URI contract"`

**done_criteria:** extended 文書の image が build → check.sh PASS、strict 混入が IR 段階（診断）と生成物段階（`structure-bad-image-strict.html` の selftest / pytest 固定）の両方で拒否され、その他の契約違反 6 種も両段階で拒否される。警告が stderr に出て exit 0 のまま。

---

### Task 6: レンダラ用 SVG 許可リスト拡張（path / polyline / marker）

**Files:**
- Modify: `scripts/ve_components/checker.py:47-65`（`_SVG_ALLOWED_TAGS` / `_SVG_ATTR_ALLOWLIST` / 座標検査）
- Test: `scripts/tests/test_renderer_svg_gate.py`（既存へケース追加）

**Interfaces:**
- Produces: 許可タグに `path` / `polyline` / `marker` を追加。属性許可リスト:
  - `path`: `class`, `d`, `fill`, `marker-start`, `marker-end`
  - `polyline`: `class`, `points`, `fill`, `marker-start`, `marker-end`
  - `marker`: `id`, `class`, `markerWidth`, `markerHeight`, `refX`, `refY`, `orient`, `viewBox`
  - 既存 `line` にも `marker-start` / `marker-end` を追加（矢印表現の土台。marker 要素だけでは矢印が成立しないため、参照属性を同時に許可する）
- 値の検査（既存ゲート「整数座標・要素/属性完全一致」の維持・拡張。r1 I3: 正規表現の一致ではなく **arity つき parser** で完全一致を保証する）:
  - `d`: トークン化して検査する `parse_path_d(d: str) -> list[str]`（診断メッセージ列を返す純関数。`checker.py` 内）。許可コマンドと arity の閉じた表 `{"M": 2, "L": 2, "H": 1, "V": 1, "Z": 0}`（大文字＝絶対座標のみ。小文字・曲線 C/S/Q/T/A は不許可 — 必要になった時に明示追加する閉じた拡張）。各コマンドは**ちょうど arity 個**の整数を取り、SVG の暗黙繰り返し（`L 0 0 10 10`）は不許可。先頭は `M`。診断: `"レンダラ SVG の path d に許可されないコマンドがあります: <cmd>"` / `"レンダラ SVG の path d の座標数が不正です: <cmd> は <n> 個"` / `"レンダラ SVG の path d は整数座標だけ使えます: <token>"` / `"レンダラ SVG の path d は M で始まる必要があります"`。
  - `points`: 整数の偶数個列・最低 2 対（`"レンダラ SVG の polyline points は整数座標の対である必要があります"`）。
  - `marker` 要素の契約: `id` 必須・**SVG ルート内で一意**（診断: `"レンダラ SVG の marker id が重複しています: <id>"`）。`viewBox` は「整数 4 個・width / height は 1 以上」（`"レンダラ SVG の marker viewBox が不正です: <値>"`）。`markerWidth` / `markerHeight` は 1 以上の整数、`refX` / `refY` は整数、`orient` は `auto` または整数。
  - `marker-start` / `marker-end`: `url(#<id>)` 形式のみ・外部 URL 拒否（`"レンダラ SVG の marker 参照は文書内 id だけ使えます"`）。参照先 id は**同一 SVG ルート内の `marker` 要素**として解決できること（`"レンダラ SVG の marker 参照が解決できません: <id>"`）。
- `RENDERER_SVG_ALLOWLIST`（どのレンダラが SVG を出せるか: 現在 `slope@2` / `waterfall@2`）は**変更しない** — 語彙の拡張であり発行権の拡張ではない。

- [ ] **Step 1: 失敗するテストを書く**（`M 0 0 L 10 10 Z` の path が通る / 小数座標 d 拒否 / 曲線 C 拒否 / 小文字 `l` 拒否 / `L 0 0 10 10`（暗黙繰り返し・arity 過剰）拒否 / `L 5`（arity 不足）拒否 / `L` 始まり拒否 / points 奇数個拒否 / marker-end の外部 url 拒否 / 未知 id への marker 参照拒否 / marker id 重複拒否 / `viewBox="0 0 0 8"`（幅 0）拒否 / marker 属性の整数検査 / foreignObject・use・SMIL が引き続き拒否）
- [ ] **Step 2: 失敗確認** — Run: `python3 -m pytest tests/test_renderer_svg_gate.py -q` / Expected: FAIL
- [ ] **Step 3: 実装** → **Step 4: 全テストパス確認**（`python3 -m pytest tests -q`）→ **Step 5: Commit** — `git commit -m "feat(ve): extend renderer svg allowlist with path, polyline, and marker"`

**done_criteria:** 3 要素と参照属性が「arity つき parser・整数座標・閉じた値文法・参照解決・id 一意」で許可され、既存の禁止（SMIL / use / foreignObject / 小数座標 / 外部参照）が全て維持される。不正 arity・未知参照・重複 id・不正 viewBox がテスト固定される。

---

### Task 7: freeform セクション（IR・許可リスト検査・provenance wrapper・検査群④緩和）

**Files:**
- Create: `scripts/ve_components/freeform_checks.py`
- Modify: `scripts/ve_components/model.py`（`FreeformSection(id, markup, reason)`）
- Modify: `scripts/ve_components/validation.py`（`kind: "freeform"` の検証・extended 限定・構造不変条件への組込み）
- Modify: `scripts/ve_components/assembly.py`（`process_freeform_section` — 許可リスト検査＋**外部リンクのドメインマーカー挿入**＋ provenance wrapper 付与）
- Modify: `scripts/ve_components/checker.py`（最終文書層: freeform wrapper subtree の抽出と `freeform_checks` の**再適用**＋ style 属性のスコープ緩和）
- Modify: `scripts/ve_components/document_checks.py`（freeform wrapper の provenance 自己表明検査）
- Modify: `scripts/build_explainer.py`（dispatch と TOC 参加）
- Create: `scripts/tests/structure-bad-freeform-strict.html` / `structure-bad-freeform-tag.html` / `structure-bad-freeform-style.html` / `structure-bad-freeform-smil.html` / `structure-bad-freeform-reason.html` / `structure-bad-freeform-attr.html` / `structure-bad-freeform-linkdomain.html`＋ `scripts/check.sh` selftest 登録（生成物改竄の再検査。r1 C1）
- Test: `scripts/tests/test_freeform_section.py`（新規）

**Interfaces:**
- Produces: IR `{"kind": "freeform", "id": ..., "reason": "<canonical 12 形式で表せない理由・非空・200 文字以内>", "markup": ...}`。`FreeformSection(id: str, markup: str, reason: str)`。
- wrapper（レンダラ付与・モデルは書けない）: `<section data-ve-section-kind="freeform" data-ve-provenance-source="model-freeform" data-ve-provenance-reason="<reason>" id="<instance-id>">`。provenance の source は定数 `model-freeform`。
- `freeform_checks.check_freeform_markup(markup: str) -> list[str]`（診断メッセージ列。呼び出し側で Diagnostic 化）。許可リスト（**閉集合**。拡張は明示追加のみ）:

```python
FREEFORM_HTML_TAGS = frozenset({
    "h2", "h3", "h4", "p", "ul", "ol", "li", "table", "thead", "tbody", "tr", "th", "td",
    "figure", "figcaption", "div", "span", "details", "summary", "blockquote", "dl", "dt", "dd",
    "strong", "em", "code", "pre", "br", "a", "small", "caption",
})
FREEFORM_SVG_TAGS = frozenset({
    "svg", "g", "defs", "rect", "circle", "ellipse", "line", "polyline", "polygon",
    "path", "text", "tspan", "title", "desc", "marker",
})
FREEFORM_STYLE_PROPERTIES = frozenset({
    "display", "grid-template-columns", "grid-column", "grid-row",
    "flex", "flex-direction", "flex-wrap", "align-items", "justify-content", "gap",
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "text-align", "max-width", "min-width", "border", "border-top", "border-bottom",
    "border-left", "border-right", "border-radius", "background", "color",
    "font-size", "font-weight", "white-space", "opacity",
})

# 要素別属性の閉じた許可リスト（r1 C3。列挙外の属性は全て拒否）
FREEFORM_GLOBAL_ATTRS = frozenset({"id", "class", "style"})
FREEFORM_HTML_ATTRS = {
    # キーにない許可タグはグローバル属性のみ。ping / target / download / rel 等は列挙しない＝拒否
    "a": frozenset({"href"}),
    "details": frozenset({"open"}),
    "th": frozenset({"scope", "colspan", "rowspan"}),
    "td": frozenset({"colspan", "rowspan"}),
    "ol": frozenset({"start"}),
}
FREEFORM_SVG_ATTRS = {
    # transform / filter / clip-path / mask / xlink:* は列挙しない＝拒否（URL 経路と座標偽装を閉じる）
    "svg": frozenset({"viewBox", "role", "aria-label"}),
    "g": frozenset(),
    "rect": frozenset({"x", "y", "width", "height", "rx", "ry", "fill", "stroke", "stroke-width"}),
    "circle": frozenset({"cx", "cy", "r", "fill", "stroke", "stroke-width"}),
    "ellipse": frozenset({"cx", "cy", "rx", "ry", "fill", "stroke", "stroke-width"}),
    "line": frozenset({"x1", "y1", "x2", "y2", "stroke", "stroke-width", "stroke-dasharray",
                       "marker-start", "marker-end"}),
    "polyline": frozenset({"points", "fill", "stroke", "stroke-width", "stroke-dasharray",
                           "marker-start", "marker-end"}),
    "polygon": frozenset({"points", "fill", "stroke", "stroke-width"}),
    "path": frozenset({"d", "fill", "stroke", "stroke-width", "stroke-dasharray",
                       "marker-start", "marker-end"}),
    "text": frozenset({"x", "y", "text-anchor", "font-size", "fill"}),
    "tspan": frozenset({"x", "y", "dx", "dy"}),
    "marker": frozenset({"markerWidth", "markerHeight", "refX", "refY", "orient", "viewBox"}),
    "defs": frozenset(),
    "title": frozenset(),
    "desc": frozenset(),
}
```

  - 検査規則（タグ）: 許可外タグ拒否（`"freeform に許可されないタグ <x> があります"`）。`script` / `style` タグ・イベント属性・外部参照（href は https:# のみ・src 全拒否＝ img も不可）・固定領域マーカー・予約 data 属性 / 予約 class は拒否（検査群①②の全適用。`scan_author_markup_bans(forbid_reserved=True)` を再利用）。
  - 検査規則（属性。r1 C3）: 各要素の属性は `FREEFORM_GLOBAL_ATTRS ∪ FREEFORM_HTML_ATTRS[tag]`（SVG 要素は `FREEFORM_SVG_ATTRS[tag]`）の**閉集合**に完全一致で限定する（`"freeform の <x> に許可されない属性 <y> があります"`）。URL を取り得る許可属性の値検査: `href` は https 絶対 URL と `#` アンカーのみ、`fill` / `stroke` は `none` / `currentColor` / `#rgb` / `#rrggbb` / `var(--<token>)` のみで **`url(` を含む値は拒否**（`"freeform の fill/stroke に url() は使えません"`）、`marker-start` / `marker-end` は `url(#<id>)` のみ。`id` は文書内一意（既存の全文書 id 一意検査に加え、freeform 内の `url(#…)` / marker 参照は**同一 freeform セクション内**の id へ解決できること — `"freeform の参照 id が見つかりません: <id>"`）。数値属性（`x` / `y` / `width` / `points` 等）は整数のみ。
  - 検査規則（style）: インライン `style` 属性はプロパティが `FREEFORM_STYLE_PROPERTIES` 内のみ・値に `url(` / `expression(` を含めば拒否・`position` はそもそも許可リスト外（既存の `position:absolute`＋複数 px 禁止はより強い形で維持）。
  - 検査規則（SVG）: `FREEFORM_SVG_TAGS` のみ・`foreignObject` / `use` / `animate` / `animateTransform` / `set` / `script` 拒否。`<svg>` があれば SVG 理由コメント必須（既存規則の踏襲。`check.sh` の理由コメント検査と同じ正規表現を使う）。
- validation: strict 文書に freeform があれば IR 拒否（`"freeform は extended プロファイル限定です"`）。構造不変条件（first-screen 先頭・closing 末尾）における freeform の位置は narrative と同じ「本文セクション」扱い。
- **外部リンクの可視ドメイン（r1 C2）**: `process_freeform_section` は許可リスト検査の通過後、narrative と**同一の** `insert_link_domain_markers`（Phase 1・`assembly.py:215`）を markup に適用してから wrapper を付与する（spec 78 行目の可視ドメイン表示は両 profile 共通・freeform も対象）。作者が `link-domain` class を自書きした markup は予約 class 検査（`scan_author_markup_bans`）が拒否するため偽装できない。最終文書では Phase 1 の検査群③ `_check_external_link_markers`（`document_checks.py:296` — flatten 後の全 content に適用済み）が freeform 内の外部 `<a>` にも hostname 一致を再検証する。テスト: IDN（`https://例え.jp/`）・port つき（`https://example.com:8443/x` → 表示は hostname のみ）・fragment つきの正常系と、マーカー hostname を改竄した生成物 fixture（`structure-bad-freeform-linkdomain.html` → 既存診断 `"外部リンクのドメインマーカーが不正です"`）。
- **最終文書層の再検査（r1 C1・検査群④の profile 依存)**: `check_final_document`（`check.sh` 単体経路からも実行される）で freeform wrapper subtree を抽出し、**IR 段階と同じ** `freeform_checks.check_freeform_markup` を再適用する（spec 72 行目「同じ判定を再現」— 生成後 HTML の改竄も同じ診断で FAIL する）。加えて `_ContentSafetyParser` に Task 4 と同型の `_freeform_scopes` 追跡を追加し、freeform wrapper 内に限りインライン `style` を `freeform_checks.validate_inline_style(value) -> list[str]` で検査して許可する（wrapper 外は従来どおり一律拒否）。検査群①②③（script / イベント属性 / 外部参照 / 自己完結 / h1 禁止 / 確度語彙 / ドメインマーカー）は freeform 内にも全適用。
- 検査群③追加（document_checks）: freeform wrapper は `data-ve-provenance-source="model-freeform"` と非空の `data-ve-provenance-reason` を持つ（診断: `"freeform に provenance の自己表明がありません"`）。strict 文書での freeform 拒否は Phase 1 の `_EXTENDED_ONLY_KINDS` が既に担う（テストで再確認する）。
- TOC: freeform は「見出しを持つ本文セクション」として参加する。`build_explainer._collect_toc_entries` に `FreeformSection` 分岐を追加し `extract_first_h2_h3(markup)` を使う。

- [ ] **Step 1: 失敗するテストを書く**（extended で表＋インライン SVG＋style 付き freeform がビルド PASS し wrapper に provenance が付く / **外部リンクにドメインマーカーが挿入される — IDN・port つき・fragment つきの 3 正常系** / strict で IR 拒否 / script・イベント属性・`<style>`・img src・予約 data 属性・`url(` 入り style・許可外プロパティ・foreignObject がそれぞれ拒否 / **`a ping` 等の許可外属性拒否・`fill="url(#x)"` 拒否・未解決の `url(#…)` 参照拒否** / SVG 理由コメント欠落拒否 / freeform の h2 が TOC entries に入る / **最終文書の freeform 改竄（許可外タグ挿入）が `check_final_document` で IR 段階と同じ診断になる**）
- [ ] **Step 2: 失敗確認** — Run: `python3 -m pytest tests/test_freeform_section.py -q` / Expected: FAIL（ImportError）
- [ ] **Step 3: 実装** → **Step 4: structure-bad fixture 7 種と selftest** — extended 見本（または最小 extended IR）をビルド後に複製・改竄して作る（各 fixture のヘッダコメントに破壊内容を記す）:
  1. `structure-bad-freeform-strict.html`（first-screen の `data-ve-profile` を `strict` へ改竄）→ `"strict プロファイルに extended 限定要素は置けません: freeform"`
  2. `structure-bad-freeform-tag.html`（freeform 内へ `<video>` を挿入）→ `"freeform に許可されないタグ video があります"`
  3. `structure-bad-freeform-style.html`（`style="position:fixed"` へ改竄）→ `"freeform の style に許可されないプロパティがあります: position"`
  4. `structure-bad-freeform-smil.html`（SVG 内へ `<animate>` を挿入）→ `"freeform に許可されないタグ animate があります"`
  5. `structure-bad-freeform-reason.html`（SVG 理由コメントを削除）→ 理由コメント必須の診断
  6. `structure-bad-freeform-attr.html`（`<a>` に `ping` 属性を追加）→ `"freeform の a に許可されない属性 ping があります"`
  7. `structure-bad-freeform-linkdomain.html`（ドメインマーカーの hostname を改竄）→ `"外部リンクのドメインマーカーが不正です"`（既存診断）
  7 件すべてを `check.sh` selftest へ期待診断つきで登録する（生成物段階の再検査が check.sh 単体で再現されることの固定。r1 C1）。
- [ ] **Step 5: 全テストパス確認** — Run: `python3 -m pytest tests -q` と `bash check.sh --selftest` / Expected: PASS
- [ ] **Step 6: Commit** — `git commit -m "feat(ve): add extended-only freeform sections with a closed allowlist contract"`

**done_criteria:** freeform が extended 文書でのみビルドでき、provenance がレンダラ付与で偽装不能、外部リンクに narrative と同一のドメインマーカーが付き、要素・属性・style・SVG・参照整合の許可リスト外の全パターンが日本語診断で拒否される。同じ判定が IR 段階と生成物段階（`check.sh` 単体・改竄 fixture 7 種の selftest）の両方で再現されることがテストで固定される。

---

### Task 8: skeleton CSP 改定（img-src data:）と fixture 一括 resplice

skeleton の固定領域ハッシュが変わる Phase 3 唯一のタスク。CSP 1 行だけを変え、全 fixture を再生成する。

**Files:**
- Modify: `assets/skeleton.html:6`（CSP の `img-src 'none'` → `img-src data:`。他は 1 バイトも変えない）
- Modify: `scripts/tests/test_skeleton_audit.py`（CSP 行の完全一致テスト追加・component CSS 監査対象に `code.css` / `image.css` を追加）
- Modify: `scripts/tests/*.html`（resplice 一括再生成）＋ KEEP_AS_IS 6 fixture（同一編集のテキスト適用）
- Test: 全既存テスト＋ selftest

**Interfaces:**
- Produces: CSP 改定後の行（完全一致・テストで固定）:

```html
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; base-uri 'none'; object-src 'none'; form-action 'none'">
```

- CSP は固定領域 1（`TITLE:BEGIN` より前）にあるため、全 fixture の固定領域 1 が変わる。resplice が扱わない KEEP_AS_IS 6 件（`bad-closing.html` / `bad-system-closing.html` / `bad-fixed-region.html` / `bad-nesting.html` / `bad-title-missing.html` / `component-bad-fixed-region.html`）には同一の 1 行置換をテキスト適用する（マーカー破壊・固定領域の故意相違は保存する）。

- [ ] **Step 1: 失敗するテストを書く** — `test_skeleton_audit.py` に追加:

```python
class CspAuditTest(unittest.TestCase):
    def test_csp_allows_data_images_only(self):
        self.assertIn(
            'content="default-src \'none\'; style-src \'unsafe-inline\'; '
            'script-src \'unsafe-inline\'; img-src data:; base-uri \'none\'; '
            'object-src \'none\'; form-action \'none\'"',
            SKELETON)

    def test_component_css_audit_covers_new_components(self):
        names = [name for name, _ in COMPONENT_CSS_NAMED]
        self.assertIn("code.css", names)
        self.assertIn("image.css", names)
```

（`COMPONENT_CSS` の読み込みを `(name, text)` のリスト `COMPONENT_CSS_NAMED` へ拡張し、`code.css` / `image.css` を含める。ColorDiscipline / SpacingGrid 監査のループも同リストを回すよう更新する）

- [ ] **Step 2: 失敗確認** — Run: `python3 -m pytest tests/test_skeleton_audit.py -q` / Expected: FAIL
- [ ] **Step 3: skeleton の CSP 1 行を変更**（上記の完全一致行へ）
- [ ] **Step 4: fixture 一括 resplice** — Run: `cd skills/visual-explain/scripts && python3 tests/tools/resplice.py`。続いて KEEP_AS_IS 6 件へ `img-src 'none'` → `img-src data:` の 1 行置換を適用。
- [ ] **Step 5: 全数回帰** — Run: `python3 -m pytest tests -q` と `bash check.sh --selftest` / Expected: 全 PASS（期待診断は不変。変わる場合は Step 4 の適用漏れ）
- [ ] **Step 6: Commit**（分割可）

```bash
git commit -m "feat(ve): open skeleton CSP to data: images for the image component"
git commit -m "test(ve): resplice fixtures onto the data-image CSP skeleton"
```

**done_criteria:** skeleton 差分が CSP 1 行のみ（`git diff` で目視確認）、CSP 完全一致テストと新 CSS の監査参加が固定され、全 fixture resplice 済みで全テスト・selftest PASS。

---

### Task 9: 見本・ドキュメント一括改訂（extended 見本の新設を含む）

**Files:**
- Create: `examples/example-extended.assembly.json` → ビルドで `examples/example-extended.html`（research 型・extended。narrative ＋ code ＋ image（1x1 PNG 等の小さな実画像）＋ freeform（理由コメント付きの小さな SVG 図）＋ closing「限界・反証・確度」）
- Modify: `SKILL.md`（canonical の節へ code を追加・extended の使い分け（strict が既定・弱モデルは extended へ逃げない）・freeform の使用条件（canonical 12 形式で表せないことが条件・同型の繰り返しは部品昇格を検討）・image の入力契約の要点・data: URI と CSP の注意）
- Modify: `references/patterns.md`（code / image / freeform の完全な JSON 例と選択ガイド）
- Modify: `references/assembly.schema.json` / `references/component-ir.schema.json`（Task 1 / 5 / 7 で追記済みの整合を最終確認）
- Modify: `references/design-system.md`（code の 1 画面規範・image の出所表示・freeform の目視 QA 義務）
- Modify: `scripts/tests/fixtures.md`（新規 fixture の記載）
- Modify: リポジトリ `CLAUDE.md`（canonical 語彙を「12 形式＋code（両 profile）＋image（extended 限定）」へ、freeform・検査群④の profile 依存・CSP 改定を反映）
- Test: 既存全テスト＋両見本の check.sh

- [ ] **Step 1: extended 見本を作ってビルド** — すべてリポジトリルート起点:

```bash
cd ~/workspace/visual-explain
python3 skills/visual-explain/scripts/build_explainer.py \
  --assembly skills/visual-explain/examples/example-extended.assembly.json \
  --output skills/visual-explain/examples/example-extended.html
bash skills/visual-explain/scripts/check.sh skills/visual-explain/examples/example-extended.html
```

Expected: PASS。生成 HTML に `data-ve-component="code"` / `data-ve-component="image"` / `data-ve-section-kind="freeform"`（provenance 付き）が出ることを grep で確認。
- [ ] **Step 2: 既存見本の回帰** — `bash skills/visual-explain/scripts/check.sh skills/visual-explain/examples/example-proposal.html` / Expected: PASS（strict 見本は変更不要。Task 8 の resplice 影響のみ）
- [ ] **Step 3: ドキュメント改訂**（上記 7 文書。「v1 では実装しない」項目 — シンタックスカラー・code 自動レイアウト — を実装済みかのように書かないこと）
- [ ] **Step 4: 全テストパス確認** — Run: `python3 -m pytest tests -q` / Expected: PASS
- [ ] **Step 5: Commit**（分割可: `docs(ve): add extended example exercising code, image, and freeform` ＋ `docs(ve): document phase 3 expression vocabulary`）

**done_criteria:** extended 見本が build → check.sh PASS し、SKILL.md / patterns.md / schema / CLAUDE.md が Phase 3 の挙動と一致する。strict 既定・extended 限定機能の縮退規則が SKILL.md に明記される。

---

### Task 10: 全体検証（Phase 3 完了ゲート）

- [ ] **Step 1: 全テスト** — Run: `cd skills/visual-explain/scripts && python3 -m pytest tests -q` / Expected: 全件 PASS（Phase 2 完了時基準＋Phase 3 追加分）
- [ ] **Step 2: selftest** — Run: `bash skills/visual-explain/scripts/check.sh --selftest` / Expected: `selftest: N passed, 0 failed`（Phase 2 完了時基準＋ Phase 3 の追加 9 件以上: data: URI 越境 1・image strict 1・freeform 改竄 7）
- [ ] **Step 3: 両見本検証** — `check.sh` で `example-proposal.html`（strict）と `example-extended.html`（extended）の両方が PASS。
- [ ] **Step 4: strict 排他の実証** — extended 限定機能の strict 混入を IR 段階（`image は extended プロファイル限定です` / `freeform は extended プロファイル限定です`）と生成物段階（`structure-bad-freeform-strict.html` が FAIL）の両方で確認。
- [ ] **Step 5: skeleton 差分の意図確認** — Run: `git diff main -- skills/visual-explain/assets/skeleton.html` を目視し、差分が CSP の `img-src` 1 箇所のみであることを確認。
- [ ] **Step 6: 目視 QA（人間実行）** — `example-extended.html` を file:// で開き、①image が CSP 下で表示される ②code の行番号・注記対応が読める ③freeform の SVG・表が骨格スタイルと調和する ④横スクロールがない、を確認。記録を `.runs/decision-doc-v3-p3/qa/2026-MM-DD-visual-qa.md`（実施日・ブラウザ・commit hash 付き）へ保存。
- [ ] **Step 7: Commit / PR** — draft PR を作成し、完了報告（テスト件数・selftest 件数・両見本 PASS・skeleton 差分の要約・QA 記録パス）を添えてレビューへ回す。

**done_criteria:** Step 1-6 の全証跡が揃い、draft PR が作成されている。

---

## 開放質問（採用済み解釈の記録 — 転送不要）

spec が値・語彙を確定していない点は以下のとおり本計画で確定した。いずれも定数・語彙の変更で済み、人間が別値を望む場合は plan 修正のみで反映できる。**Pi への転送が必要な未解決事項はない。**

1. **relationship.kind の語彙**（spec 未定義）: `code` = `annotated-code`、`image` = `evidential-image`。registry の既存命名（kebab・関係を表す）に揃えた。
2. **画像寸法・総ピクセル上限の具体値**（spec は「上限を置く」のみ）: 1 辺 4096px・総ピクセル 16,777,216（4096×4096）。バイト上限（spec verbatim）とは独立に、decode 爆弾（高圧縮巨大画像）を防ぐ。
3. **code の分量上限**（spec 未定義）: 80 行・1 行 160 文字・注記 8 件。「概ね 1 画面」規範（SKILL.md）と決定的レンダリングのための保守値。
4. **警告の出力チャネル**（fail しない警告は現行アーキテクチャに存在しない）: `build_explainer.py` が stderr に `WARN:` 行を出して exit 0。`check.sh` は警告を出さない（警告はビルド時の作者向け情報であり、検証の合否ではないため）。
5. **freeform の provenance 形式**: IR は `reason`（非空・200 字以内）のみを受け、`data-ve-provenance-source` はレンダラが定数 `model-freeform` を付与する（compatibility 節の provenance 慣例に揃えつつ、モデルによる出自偽装を構造的に不能にする）。
6. **freeform の style プロパティ・要素別属性の許可リスト初期値**: Task 7 の `FREEFORM_STYLE_PROPERTIES` / `FREEFORM_HTML_ATTRS` / `FREEFORM_SVG_ATTRS`（レイアウト系中心・`position` / `transform` / `filter` / `clip-path` / `ping` / `target` / `rel` を含めない保守的な閉集合。`fill` / `stroke` は `url(` を含む値を拒否）。spec の「拡張は許可リストへの明示追加で行う」に従い、不足時は追加 PR で広げる。
7. **SVG marker 参照属性**: 要素 `marker` の追加だけでは矢印が成立しないため、`marker-start` / `marker-end`（`url(#文書内id)` のみ）を `path` / `polyline` / `line` に許可した。spec の「矢印表現の土台」を成立させる最小の属性追加。
8. **TOC への freeform 参加**: spec 55 行目「見出しを持つ本文セクション」に freeform も含まれると解釈し、narrative と同じ規則（最初の h2/h3）で参加させる。

## Self-Review 済みメモ

- spec の Phase 3 項目（code 部品・image 部品と入力契約・CSP 改定・SVG 許可リスト拡張・freeform の閉じた許可リスト・検査群④の profile 依存・provenance のレンダラ付与・目視 QA 義務）は Task 1-10 で全て対応する。非隣接コネクタ解放・シンタックスカラー・自動レイアウト・宣言的グラフ部品は spec スコープ外であり**含めない**。T07 エッジケースは Phase 2 で完結済みのため含めない。
- 型・名前の整合を確認済み: `image_contract.check_image` / `ImageCheckResult` / `collect_document_warnings`（Task 3 定義 → Task 5 の validation・`_check_image_artifact`・`build_explainer` で使用）、`freeform_checks.check_freeform_markup` / `validate_inline_style` / `FREEFORM_STYLE_PROPERTIES` / `FREEFORM_HTML_ATTRS` / `FREEFORM_SVG_ATTRS`（Task 7 で定義、IR 段階と `check_final_document` の両方から呼ぶ）、`insert_link_domain_markers`（Phase 1 定義 → Task 7 の freeform で再利用）、`parse_path_d`（Task 6）、`_check_src(tag, name, v)` の新契約（Task 4）、wrapper 属性 `data-ve-provenance-source` / `data-ve-provenance-reason`（Task 7 レンダラ → document_checks）、`data-ve-line` / `data-ve-line-ref` / `data-ve-annotated`（Task 2 レンダラ → `_check_code_artifact`）、scoped 許可の wrapper 種別スタック（Task 4 checker → Task 5 レンダラ出力、Task 7 の `_freeform_scopes` が同型）。
- 依存順: Task 1→2（code IR→レンダラ）、Task 3→4→5（画像契約→scoped 解放→image 部品。Task 4 の fixture は手書き wrapper markup で先行できる）、Task 6 は独立、Task 7 は Task 4 のスコープ追跡機構を再利用（`_freeform_scopes` は `_image_scopes` と同型）、Task 8 は全機能確定後の skeleton 一回改定、Task 9-10 が締め。image のブラウザ表示だけは Task 8 の CSP 改定まで確認できない（検査は CSP 非依存で先に固定できる）ことを Task 5 に明記済み。
- 診断文言は例示であり、実装時に既存文言のトーン（です・ます調の指示形）へ揃える。文言変更はテスト・selftest 期待値の同時更新を伴う。
- 検査の二重化（spec 72 行目「IR 段階と生成物段階で同じ判定を再現」）: image は `image_contract` を両段階から呼び、code は IR 検証＋`_check_code_artifact`、freeform は `freeform_checks` を IR 段階で・スコープ緩和つき safety parser を生成物段階で適用する。
- `FORBIDDEN_AUTHORING_KEYS`（`validation.py:121`）との衝突を確認済み: 新 payload キー（`language` / `lines` / `annotations` / `line` / `text` / `alt` / `dataUri` / `reason` / `markup`※freeform は narrative と同じ markup セクションであり canonical IR ではない）はいずれも禁止キーに該当しない。
- 検証アーティファクトの置き場: Phase 3 の追加分はすべて `.runs/decision-doc-v3-p3/`（QA 記録は `qa/`）。Phase 1 / Phase 2 の `.runs/` と既存 fixture・検証証拠は保持し変更しない（Task 8 の resplice による固定領域更新のみが既存 fixture に触る）。

---

## レビュー r1 反映記録

ADOPTED:
- C1: freeform の閉じた許可リスト契約を生成物段階でも再検査する — `check_final_document`（check.sh 単体経路）が freeform wrapper subtree へ IR 段階と同一の `freeform_checks.check_freeform_markup` を再適用し、生成後 HTML の改竄 fixture 7 種（許可外タグ・許可外 style・SMIL・理由コメント欠落・許可外属性・strict 改竄・マーカー改竄）を selftest へ登録（Task 7 改訂）
- C2: freeform の外部リンクに narrative と同一の `insert_link_domain_markers`（Phase 1・assembly.py:215）を `process_freeform_section` で適用し、検査群③の `_check_external_link_markers` が freeform 内も再検証することを明記。IDN・port・fragment の正常系とマーカー改竄の生成物検査を追加（Task 7 改訂）
- C3: freeform に要素別属性の閉じた許可リスト（`FREEFORM_HTML_ATTRS` / `FREEFORM_SVG_ATTRS`・グローバル属性 id/class/style のみ共通）、URL を取り得る属性（href / fill / stroke / marker 参照）の値検査、`url(` 拒否、id 一意と `url(#…)` の同一セクション内参照解決を追加。`ping` / `transform` / `filter` / `clip-path` / `xlink:*` は列挙外＝拒否（Task 7 改訂）
- I1: data URI の scoped 許可を「`img` の名前空間なし `src` × 他 wrapper に入れ子でない最上位 canonical image wrapper 内」の 3 条件 AND に限定し、`_check_src(tag, name, v)` の呼出し契約を明示。非 img 要素・compatibility 内の偽装 wrapper・section を伴わない figure 単体の負例を追加（Task 4 改訂）
- I2: 警告の返却・伝播を `image_contract.collect_document_warnings(results) -> tuple[str, ...]`（文書順・重複排除・合計警告は末尾）として定義し、validation は拒否のみ・build_explainer が stderr へ出力と役割を分離。境界値（閾値ちょうど許容・1 バイト超過で発火）の aggregate test を追加（Task 3 / 5 改訂）
- I3: SVG 拡張の値文法を arity つき path parser（`{M:2, L:2, H:1, V:1, Z:0}`・絶対座標のみ・暗黙繰り返し禁止・M 始まり）、marker の viewBox / 正寸法契約、marker id の SVG ルート内一意と参照解決へ精密化。不正 arity・未知参照・重複 id・不正 viewBox のテストを追加（Task 6 改訂)
- I4: extended image 文書の profile を strict へ改竄した `structure-bad-image-strict.html` を component checker（pytest）と `check.sh --selftest` の両方へ登録し、生成物段階の profile 排他を固定（Task 5 改訂）

REJECTED:
- なし

STATUS: complete
