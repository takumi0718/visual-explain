#!/usr/bin/env python3
"""Four-layer component checker CLI, invoked by check.sh after the legacy checks.

Usage: check_component_html.py <document> <skeleton> <registry>

A pre-migration legacy document (no controlled markers or data-ve attributes)
passes unchanged. Component documents are held to the fixed-region, content
safety, and trusted-asset contracts. Exit 0 on pass, 1 on any diagnostic.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ve_components.checker import check_final_document
from ve_components.diagnostics import ContractError
from ve_components.registry import load_registry


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: check_component_html.py <document> <skeleton> <registry>", file=sys.stderr)
        return 2
    document_path, skeleton_path, registry_path = (Path(a) for a in argv)
    try:
        raw = document_path.read_bytes()
    except OSError as exc:
        print(f"FAIL: 生成HTMLを読めません: {exc}")
        return 1
    try:
        skeleton = skeleton_path.read_bytes()
    except OSError as exc:
        print(f"FAIL: skeleton.htmlを読めません: {exc}")
        return 1
    try:
        registry = load_registry(registry_path)
    except ContractError as exc:
        for diagnostic in exc.diagnostics:
            print(f"FAIL: {diagnostic}")
        return 1
    diagnostics = check_final_document(raw, skeleton, registry, components_dir=registry_path.parent)
    if diagnostics:
        for diagnostic in diagnostics:
            print(f"FAIL: {diagnostic}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
