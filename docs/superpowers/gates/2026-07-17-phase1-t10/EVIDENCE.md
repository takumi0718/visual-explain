# Phase 1 完了ゲート証拠（Task 10 / 2026-07-17）

検証対象コミット: `271f5c7`（作業開始時点）＋本ディレクトリの証拠追加。

## Step 1: 全テスト

```
cd skills/visual-explain/scripts && python3 -m pytest tests -q
→ 672 passed, 152 subtests passed
pytest_exit:0
```

ログ: `step1-2-5-summary.log`

## Step 2: selftest

```
bash skills/visual-explain/scripts/check.sh --selftest
→ selftest: 29 passed, 0 failed
selftest_exit:0
```

付帯: `bash check.sh skills/visual-explain/examples/example-proposal.html` → `PASS`

## Step 3: すり抜け再現

### 3a. IR 段階拒否（ビルド失敗・HTML 未出力）

| fixture | 診断 | exit |
|---|---|---|
| `ir-bad-no-first-screen.json` | `first-screen は先頭にちょうど1個必要です` | 1 |
| `ir-bad-no-closing.json` | `closing は最後にちょうど1個必要です` | 1 |
| `ir-bad-duplicate-h1.json` | `narrative に <h1> は置けません（h1 は first-screen 専有）` | 1 |
| `ir-bad-title-mismatch.json` | 同上（IR では title≠h1 を独立表現できないため、別 h1 投入で拒否） | 1 |

ログ: `step3-ir-reject.log`

注: `title ≠ h1` の HTML 検査はレンダラが同一 `document.title` から両側を生成するため IR では再現不能。静的 fixture（3b）で捕捉する。

### 3b. 静的 HTML が check.sh で FAIL

| fixture | 診断 | exit |
|---|---|---|
| `structure-bad-no-first-screen.html` | `文書型の自己表明がありません` | 1 |
| `structure-bad-duplicate-h1.html` | `h1 は first-screen 内にちょうど1個必要です` | 1 |
| `structure-bad-title-mismatch.html` | `title と h1 が一致しません` | 1 |
| `structure-bad-no-closing.html` | `closing セクションがありません` | 1 |

ログ: `step3-static-fail.log`

## Step 4: 外部リンク実証（調査報告型）

- IR: `ir-research-external-link.json`（`type=research`、出典 `https://docs.example.org/page`）
- ビルド: OK → `research-external-link.html`（および `.visual-explain/phase1-gate-research-external-link.html`）
- `check.sh` → `PASS`
- ドメインマーカー: `<span class="link-domain">‹docs.example.org›</span>`

ログ: `step4-build-check.log`

## Step 5: skeleton 不変

```
git diff --stat main -- skills/visual-explain/assets/skeleton.html
→ （空・差分なし）
```

## Step 6: Commit / draft PR

- 本証拠ディレクトリをタスクブランチへ commit する。
- **draft PR 作成は worker 禁止**（push / PR / merge は人間ゲート）。PR 本文ドラフトは下記。

### PR 本文ドラフト（人間が `gh pr create` するとき用）

```markdown
## Summary
- Phase 1（decision-document v3）完了ゲート証拠を追加
- pytest 672 / selftest 29 / 旧すり抜け 4 種の IR 拒否＋check.sh FAIL / 調査報告出典リンク＋ドメインマーカー / skeleton 差分なし を確認

## Test plan
- [ ] `cd skills/visual-explain/scripts && python3 -m pytest tests -q`
- [ ] `bash skills/visual-explain/scripts/check.sh --selftest`
- [ ] `docs/superpowers/gates/2026-07-17-phase1-t10/EVIDENCE.md` の Step 3–4 を追試
- [ ] 統括レビュアー（claude Opus）の GO/NO-GO を本 PR に追記

## Notes
- マージはしない（draft）
- 統括レビューの GO/NO-GO はクロスレビュー後に記載
```
