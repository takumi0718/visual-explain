# visual-explain

visual-explain is an open Agent Skill for turning complex explanations into clear, self-contained HTML documents.
It supports proposal decisions, system walkthroughs, and research reports.
Every document is a single HTML file with inline CSS and JavaScript.
The workflow is static-first and adds interaction only when change over time is essential.
A stable skeleton provides reusable layouts, responsive behavior, and accessibility basics.
Generated content stays inside a constrained editable region.
External assets and build dependencies are not required.
A local checker validates structure, safety rules, and required sections.
The skill follows the portable Agent Skills directory convention.
The project is under active development and is not yet released publicly.

## 概要

visual-explain は、複雑な提案・仕組み・調査結果を、判断しやすい単一 HTML 資料へ変換する Agent Skill です。
モデルにレイアウト計算を任せず、固定された骨格と図フォーマットへ内容を埋めることで、生成品質の下限を安定させます。

主な方針:

- 静的な表現を優先し、時間・順序・状態変化が核心の場合だけ操作部品を使う
- 提案資料では、第一画面に推奨・読者が決めること・判断条件を明示する
- リスク、弱い前提、不確かな点を隠さない
- 外部リソース、ビルド、追加パッケージを必要としない
- 機械チェックと目視チェックを組み合わせる

## 構成

```text
skills/visual-explain/
├── SKILL.md
├── assets/
├── examples/
├── references/
└── scripts/
```

実装は `skills/visual-explain/` 以下に置きます。スキル名と親ディレクトリ名は同じ `visual-explain` です。

## Attribution

Design ideas are informed by [nicobailon/visual-explainer](https://github.com/nicobailon/visual-explainer), licensed under the MIT License.
The proposal-gating and skill-workflow concepts are informed by [obra/superpowers](https://github.com/obra/superpowers).

## License

MIT. See [LICENSE](LICENSE).
