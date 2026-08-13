"""Task 17 regressions found by the real-browser 1212px acceptance pass."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VISUAL_STAGE_CSS = (ROOT / "assets" / "components" / "visual-stage.css").read_text("utf-8")


def _declarations_for(selector: str) -> str:
    match = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>[^}}]*)\}}", VISUAL_STAGE_CSS)
    assert match is not None, f"missing controlled selector: {selector}"
    return match.group("body")


def test_spotlight_svg_connector_does_not_inherit_the_node_focus_rectangle() -> None:
    path_declarations = _declarations_for(
        '[data-stepper][data-ve-sequence-mode="path-spotlight"] '
        '[data-ve-component="flow"] .ve-flow-connector-layer path.ve-seq-spot'
    )
    node_declarations = _declarations_for('.ve-seq-spot:not(path)')

    assert "outline:" in node_declarations
    assert "box-shadow:" in node_declarations
    assert "outline:" not in path_declarations
    assert "box-shadow:" not in path_declarations


def test_controlled_flow_runtime_is_not_rendered_as_component_content() -> None:
    declarations = _declarations_for(
        'script[data-ve-asset~="visual-stage-flow"]'
    )

    assert re.search(r"(?:^|;)\s*display\s*:\s*none\s*(?:;|$)", declarations)


def test_semantic_edge_rows_do_not_render_focus_rectangles_behind_drawn_paths() -> None:
    declarations = _declarations_for(
        '[data-stepper][data-ve-sequence-mode="path-spotlight"] '
        '[data-ve-component="flow"] .ve-flow-connectors .ve-flow-link.ve-seq-spot'
    )

    assert re.search(r"(?:^|;)\s*outline\s*:\s*none\s*(?:;|$)", declarations)
    assert re.search(r"(?:^|;)\s*box-shadow\s*:\s*none\s*(?:;|$)", declarations)
