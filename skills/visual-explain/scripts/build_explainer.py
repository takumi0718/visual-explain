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
from dataclasses import dataclass, replace
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
from ve_components.diagnostics import ContractError, Diagnostic, FINAL_CHECK_FAILURE, FIXED_REGION_MISMATCH  # noqa: E402
from ve_components.skeletons import LATEST_SKELETON_VERSION, declared_skeleton_version  # noqa: E402
from ve_components.document_sections import (  # noqa: E402
    build_overview_nav,
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
from ve_components.metrics import format_metrics, text_metrics  # noqa: E402
from ve_components.registry import Registry, load_registry  # noqa: E402
from ve_components.review_blocks import stamp_review_sections  # noqa: E402
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


def build_document(raw_assembly, registry: Registry, renderers, skeleton_text: str,
                   components_dir: Path, *, document_path: str) -> CompositionResult | str:
    """Validate, compose, flatten, and finally check. Raises on any failure."""
    declared = declared_skeleton_version(skeleton_text)
    if declared != LATEST_SKELETON_VERSION:
        raise ContractError([Diagnostic(
            FIXED_REGION_MISMATCH,
            f"ビルドは最新の skeleton 版（{LATEST_SKELETON_VERSION}）だけを使えます: {declared}",
        )])
    request = validate_assembly(raw_assembly)
    occupied_ids = frozenset(_section_instance_id(section) for section in request.sections)
    first = request.sections[0]
    nav = build_overview_nav(first, occupied_ids=occupied_ids)
    marked = {m.target for m in first.overview.markers} if first.overview is not None else set()
    items = []
    for section in request.sections:
        if isinstance(section, CanonicalSection):
            items.append(process_canonical_section(section, registry, renderers))
        elif isinstance(section, NarrativeSection):
            items.append(process_narrative_section(
                section, include_anchor_id=section.id in marked))
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
        occupied_ids=occupied_ids | ({nav.instance_id} if nav is not None else frozenset()))
    items.append(panel)
    if nav is not None:
        # first-screen [0], overview canonical [1], then the marker list.
        items.insert(2, nav)
    composition = compose_sections(items)
    composition = replace(composition, sections_markup=stamp_review_sections(composition.sections_markup))
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
        result = build_to_path(raw_assembly, paths)
    except ContractError as exc:
        for diagnostic in exc.diagnostics:
            print(f"FAIL: {diagnostic}", file=sys.stderr)
        return 1
    print(f"OK: {paths.output}")
    print(format_metrics(text_metrics(result.html)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
