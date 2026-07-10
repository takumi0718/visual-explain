# R04 round 2 FIX

## 修正
- 中心図直前の claim から、削除済み connector と矛盾する「公開後の撤回を同じ経路で確認」を削除しました。
- 現存する `根拠・顧客影響 → 共同承認 → 限定対象で公開` の connector に合わせて、共同承認での照合と限定公開を記述しました。

## 検証
- `skills/visual-explain/scripts/check.sh "$(pwd)/skills/visual-explain/examples/example-proposal.html" --type proposal` — PASS
- `skills/visual-explain/scripts/check.sh --selftest` — 20 passed, 0 failed
- `git diff --check` — PASS
