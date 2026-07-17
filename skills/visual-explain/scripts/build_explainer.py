#!/usr/bin/env python3
"""Build one self-contained explainer document from an assembly request.

The CLI loads the assembly request and registry, processes canonical and
compatibility branches through the single composer/flattener, passes the
CompositionResult as ``expected`` to final checking, and writes the output only
after all checks pass — using a temp file plus atomic rename so a failed build
never leaves a partial HTML document. Contract failures print bounded
diagnostics without a traceback.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ve_components.assembly import (  # noqa: E402
    CompositionResult,
    compose_sections,
    process_canonical_section,
    process_compatibility_section,
    process_narrative_section,
)
from ve_components.checker import check_final_document  # noqa: E402
from ve_components.diagnostics import ContractError, Diagnostic, FINAL_CHECK_FAILURE  # noqa: E402
from ve_components.document_sections import (  # noqa: E402
    TocEntry,
    build_toc,
    extract_first_h2_h3,
    render_ask,
    render_closing,
    render_decision_panel,
    render_first_screen,
)
from ve_components.flatten import flatten_document  # noqa: E402
from ve_components.model import (  # noqa: E402
    AskSection,
    CanonicalSection,
    ClosingSection,
    FirstScreenSection,
    NarrativeSection,
)
from ve_components.registry import Registry, load_registry  # noqa: E402
from ve_components.renderers import TRUSTED_RENDERERS  # noqa: E402
from ve_components.validation import validate_assembly  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
SKELETON_PATH = SCRIPT_DIR.parent / "assets" / "skeleton.html"
REGISTRY_PATH = SCRIPT_DIR.parent / "assets" / "components" / "registry.json"


@dataclass(frozen=True)
class BuildPaths:
    skeleton: Path
    registry: Path
    components_dir: Path
    output: Path


@dataclass(frozen=True)
class BuildResult:
    html: str
    diagnostics: tuple[Diagnostic, ...]
    output_path: Path | None


def _section_instance_id(section) -> str:
    """Compose instance id for any validated section kind."""
    if isinstance(section, CanonicalSection):
        return section.ir.id
    return section.id


def _collect_toc_entries(sections) -> tuple[TocEntry, ...]:
    """Headed body sections only: narrative first h2/h3, and closing (first block)."""
    entries: list[TocEntry] = []
    for section in sections:
        if isinstance(section, NarrativeSection):
            heading = extract_first_h2_h3(section.markup)
            if heading is not None:
                entries.append(TocEntry(anchor_id=section.id, heading=heading))
        elif isinstance(section, ClosingSection):
            entries.append(TocEntry(anchor_id=section.id, heading=section.blocks[0].heading))
    return tuple(entries)


def build_document(raw_assembly, registry: Registry, renderers, skeleton_text: str,
                   components_dir: Path, *, document_path: str) -> CompositionResult | str:
    """Validate, compose, flatten, and finally check. Raises on any failure."""
    request = validate_assembly(raw_assembly)
    occupied_ids = frozenset(_section_instance_id(section) for section in request.sections)
    toc = build_toc(_collect_toc_entries(request.sections), occupied_ids=occupied_ids)
    include_narrative_ids = toc is not None
    items = []
    for section in request.sections:
        if isinstance(section, CanonicalSection):
            items.append(process_canonical_section(section, registry, renderers))
        elif isinstance(section, NarrativeSection):
            items.append(process_narrative_section(
                section, include_anchor_id=include_narrative_ids))
        elif isinstance(section, FirstScreenSection):
            items.append(render_first_screen(section, request.document))
        elif isinstance(section, ClosingSection):
            items.append(render_closing(section))
        elif isinstance(section, AskSection):
            items.append(render_ask(section))
        else:
            items.append(process_compatibility_section(section))
    panel = render_decision_panel(
        tuple(s for s in request.sections if isinstance(s, AskSection)),
        request.document, request.schema_version, document_path,
        occupied_ids=occupied_ids | ({toc.instance_id} if toc is not None else frozenset()))
    if panel is not None:
        items.append(panel)
    if toc is not None:
        # Insert immediately after first-screen (always at index 0).
        items.insert(1, toc)
    composition = compose_sections(items)
    document = flatten_document(composition, skeleton_text, components_dir, request.document.title)
    diagnostics = check_final_document(document, skeleton_text, registry, expected=composition,
                                       components_dir=components_dir)
    if diagnostics:
        raise ContractError(diagnostics)
    return document


def build_to_path(raw_assembly, paths: BuildPaths, renderers=TRUSTED_RENDERERS) -> BuildResult:
    registry = load_registry(paths.registry)
    skeleton_text = paths.skeleton.read_text("utf-8")
    document = build_document(raw_assembly, registry, renderers, skeleton_text, paths.components_dir,
                              document_path=str(paths.output))
    # Atomic write: temp file in the output directory, then rename.
    paths.output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(paths.output.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(document)
        os.replace(tmp, paths.output)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return BuildResult(html=document, diagnostics=(), output_path=paths.output)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="build_explainer.py")
    parser.add_argument("--assembly", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--skeleton", default=str(SKELETON_PATH))
    parser.add_argument("--registry", default=str(REGISTRY_PATH))
    args = parser.parse_args(argv)

    try:
        raw_assembly = json.loads(Path(args.assembly).read_text("utf-8"), parse_float=Decimal)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: アセンブリを読めません: {exc}", file=sys.stderr)
        return 1

    registry_path = Path(args.registry)
    paths = BuildPaths(
        skeleton=Path(args.skeleton),
        registry=registry_path,
        components_dir=registry_path.parent,
        output=Path(args.output),
    )
    try:
        build_to_path(raw_assembly, paths)
    except ContractError as exc:
        for diagnostic in exc.diagnostics:
            print(f"FAIL: {diagnostic}", file=sys.stderr)
        return 1
    print(f"OK: {paths.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
