"""Task 17 git-backed regression gate for baseline test/example immutability."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[4]
BRANCH_BASE = "af74036928087ef55dc57d08ee50a9519a97b30a"
SCOPES = (
    "skills/visual-explain/scripts/tests",
    "skills/visual-explain/examples",
)
ALLOWED_METHOD_CHANGES = {
    "skills/visual-explain/scripts/tests/test_component_checker.py": (
        "test_registry_declares_no_script_assets",
        "test_only_flow_declares_the_opt_in_path_spotlight_script_asset",
    ),
    "skills/visual-explain/scripts/tests/test_chevron_renderer.py": (
        "test_registry_entry_is_complete",
        "test_registry_entry_is_complete",
    ),
    "skills/visual-explain/scripts/tests/test_enumeration_renderer.py": (
        "test_registry_entry_is_complete",
        "test_registry_entry_is_complete",
    ),
    "skills/visual-explain/scripts/tests/test_logic_tree_renderer.py": (
        "test_registry_entry_is_complete",
        "test_registry_entry_is_complete",
    ),
    "skills/visual-explain/scripts/tests/test_matrix_renderer.py": (
        "test_registry_entry_is_complete",
        "test_registry_entry_is_complete",
    ),
    "skills/visual-explain/scripts/tests/test_pyramid_renderer.py": (
        "test_registry_entry_is_complete",
        "test_registry_entry_is_complete",
    ),
    "skills/visual-explain/scripts/tests/test_stairs_renderer.py": (
        "test_registry_entry_is_complete",
        "test_registry_entry_is_complete",
    ),
    "skills/visual-explain/scripts/tests/test_waterfall_renderer.py": (
        "test_registry_entry_is_complete",
        "test_registry_entry_is_complete",
    ),
}


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=REPOSITORY,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _method_span(source: str, method_name: str) -> tuple[int, int]:
    tree = ast.parse(source)
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == method_name
    ]
    assert len(matches) == 1, f"expected one {method_name}, found {len(matches)}"
    node = matches[0]
    assert node.end_lineno is not None
    return node.lineno, node.end_lineno


def _without_allowed_method(source: str, method_name: str) -> str:
    lines = source.splitlines(keepends=True)
    start, end = _method_span(source, method_name)
    lines[start - 1 : end] = ["<allowed method change>\n"]
    return "".join(lines)


def _parse_name_status(output: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in output.splitlines():
        fields = line.split("\t")
        assert len(fields) == 2, f"unsupported name-status row: {line!r}"
        rows.append((fields[0], fields[1]))
    return rows


def _parse_numstat(output: str) -> dict[str, tuple[str, str]]:
    rows: dict[str, tuple[str, str]] = {}
    for line in output.splitlines():
        added, deleted, path = line.split("\t", 2)
        rows[path] = (added, deleted)
    return rows


def audit_baseline_immutability(head: str = "HEAD") -> list[str]:
    """Return stable failures for prohibited baseline mutations."""

    revision = f"{BRANCH_BASE}..{head}"
    name_status = _parse_name_status(
        _git("diff", "--name-status", revision, "--", *SCOPES)
    )
    numstat = _parse_numstat(_git("diff", "--numstat", revision, "--", *SCOPES))
    failures: list[str] = []

    status_paths = {path for _status, path in name_status}
    if status_paths != set(numstat):
        failures.append("name-status and numstat path sets differ")

    for status, path in name_status:
        if status == "A":
            if _git("ls-tree", "--name-only", BRANCH_BASE, "--", path):
                failures.append(f"{path}: status A but path exists at branch base")
            if not _git("ls-tree", "--name-only", head, "--", path):
                failures.append(f"{path}: status A but path is absent at head")
            continue
        if status != "M":
            failures.append(f"{path}: prohibited git status {status}")
            continue
        method_names = ALLOWED_METHOD_CHANGES.get(path)
        if method_names is None:
            failures.append(f"{path}: existing baseline file changed outside allowlist")
            continue
        before_method, after_method = method_names
        before = _git("show", f"{BRANCH_BASE}:{path}")
        after = _git("show", f"{head}:{path}")
        try:
            unchanged_before = _without_allowed_method(before, before_method)
            unchanged_after = _without_allowed_method(after, after_method)
        except (AssertionError, SyntaxError) as error:
            failures.append(f"{path}: cannot verify allowed method: {error}")
            continue
        if unchanged_before != unchanged_after:
            failures.append(
                f"{path}: content changed outside {before_method}->{after_method}"
            )

    return sorted(failures)


def test_only_new_files_and_named_registry_expectations_change_from_branch_base() -> None:
    assert audit_baseline_immutability() == []
