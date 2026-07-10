# Task 8 fixed fixture matrix

These are known facts to reproduce exactly. Do not invent facts. Each output must state certainty next to claims and must pass `../check.sh`.

## A. Proposal approval — ctx self-healing wrapper

Source: `agent-stack` commit `b799a3f` (`fix: ctx ラッパーを自己修復型にし stale/欠落 shim を自動再生成`).

Required facts:
- A missing or stale `ctx` console-script shim can make direct execution fail after a fresh clone, git pull, or a `project.scripts` change.
- When a venv already exists, the fast path runs `uv pip install --python "$venv/bin/python" -e "$proj" --force-reinstall --no-deps --quiet` to regenerate console scripts without dependency churn.
- When no venv exists, it creates one with `uv venv` and performs a full editable install.
- Decision: approve the self-healing wrapper versus retaining a direct shim invocation.

## B. System explanation — agent-stack Nix wiring

Required facts:
- The public dotfiles flake imports the private overlay only when `DOTFILES_PRIVATE_ROOT` points to it.
- `mkOutOfStoreSymlink` links mutable sources edit-in-place rather than copying them through the Nix store.
- `crossRuntimeSkill` declares four runtime links: `.agents`, `.codex`, `.claude`, and `.hermes`.
- Antigravity settings are seed-on-missing through a Home Manager activation step because its runtime rewrites the live settings file.

## C. Research report — visual-explain design findings

Required facts:
- Congruence principle: use movement only when the change itself is the content; otherwise prefer static explanation.
- A premortem works by asking readers to generate causal reasons for a hypothetical failure, rather than merely listing risks.
- `~/.agents/skills` is a de facto skill discovery convention; Claude Code has its own discovery-path exception.

## Evaluation contract

For every generated document, evaluate: required-fact reproduction, zero unsupported claims or arrows, correct certainty labels, and readability. The first screen alone must answer what the material concerns and what decision is requested.
