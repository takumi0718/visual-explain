"""Shared renderer behavior for visual-stage markup and assets."""
from __future__ import annotations

import html
import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from html.parser import HTMLParser
from typing import Callable

from ..model import CanonicalIR, RenderResult, SequenceDeclaration, SequenceStep
from ..registry import AssetDefinition
from ..validation import SEQUENCE_MODES, SEQUENCE_REFERENCE_ATTRIBUTES

_VISUAL_STAGE_ASSET_ID = "visual-stage"


@dataclass(frozen=True)
class SequencePanel:
    """One static panel: overview has no step, later panels map 1:1 to steps."""

    number: int
    step: SequenceStep | None
    highlight_ids: frozenset[str]


PathEdgeResolver = Callable[[SequenceDeclaration, int], Iterable[str]]
PanelRenderer = Callable[[SequencePanel], RenderResult]

_URL_ID_RE = re.compile(r"url\(\s*#([^\s)'\"#]+)\s*\)")
_PRESERVED_ATTRIBUTE_CASE = {
    "viewbox": "viewBox",
    "preserveaspectratio": "preserveAspectRatio",
}


class _PanelIdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.ids: set[str] = set()

    def _collect(self, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name.lower() == "id" and value is not None:
                self.ids.add(value)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._collect(attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._collect(attrs)


class _PanelNamespaceParser(HTMLParser):
    def __init__(self, panel_number: int, dom_ids: set[str]) -> None:
        super().__init__(convert_charrefs=False)
        self.suffix = f"--p{panel_number}"
        self.dom_ids = dom_ids
        self.parts: list[str] = []

    def _suffix_id(self, value: str) -> str:
        return value + self.suffix if value in self.dom_ids else value

    def _rewrite_urls(self, value: str) -> str:
        def replace(match: re.Match[str]) -> str:
            target = match.group(1)
            if target not in self.dom_ids:
                return match.group(0)
            return match.group(0).replace(f"#{target}", f"#{target}{self.suffix}")

        return _URL_ID_RE.sub(replace, value)

    def _rewrite(self, name: str, value: str) -> str:
        kind = SEQUENCE_REFERENCE_ATTRIBUTES.get(name.lower())
        if kind == "dom-id":
            return value + self.suffix
        if kind == "fragment":
            return f"#{self._suffix_id(value[1:])}" if value.startswith("#") else value
        if kind == "single-idref":
            return self._suffix_id(value)
        if kind == "idref-list":
            return " ".join(self._suffix_id(token) for token in value.split())
        if kind in {"url-reference", "inline-url-reference"}:
            return self._rewrite_urls(value)
        return value

    def _start(self, tag: str, attrs: list[tuple[str, str | None]], closed: bool) -> None:
        self.parts.append(f"<{tag}")
        for name, value in attrs:
            output_name = _PRESERVED_ATTRIBUTE_CASE.get(name.lower(), name)
            if value is None:
                self.parts.append(f" {output_name}")
            else:
                rewritten = self._rewrite(name, value)
                self.parts.append(f' {output_name}="{html.escape(rewritten, quote=True)}"')
        self.parts.append("/>" if closed else ">")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag, attrs, False)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._start(tag, attrs, True)

    def handle_endtag(self, tag: str) -> None:
        self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.parts.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self.parts.append(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        self.parts.append(f"<!{decl}>")

    def handle_pi(self, data: str) -> None:
        self.parts.append(f"<?{data}>")


def _namespace_panel_markup(markup: str, panel_number: int) -> str:
    """Suffix DOM IDs and only allowlisted references resolving in this panel."""
    collector = _PanelIdCollector()
    collector.feed(markup)
    collector.close()
    parser = _PanelNamespaceParser(panel_number, collector.ids)
    parser.feed(markup)
    parser.close()
    return "".join(parser.parts)


def sequence_panels(
    sequence: SequenceDeclaration,
    *,
    path_edges: PathEdgeResolver | None = None,
) -> tuple[SequencePanel, ...]:
    """Centralize overview/state/delta/path highlight semantics."""
    if sequence.mode not in SEQUENCE_MODES:
        raise ValueError(f"unsupported sequence mode: {sequence.mode}")
    if sequence.mode == "path-spotlight" and path_edges is None:
        raise ValueError("path-spotlight requires a path edge resolver")

    panels = [SequencePanel(number=1, step=None, highlight_ids=frozenset())]
    accumulated: set[str] = set()
    for step_index, step in enumerate(sequence.steps):
        if sequence.mode == "delta-accumulate":
            accumulated.update(step.target_ids)
            highlights = frozenset(accumulated)
        else:
            highlights = frozenset(step.target_ids)
        if sequence.mode == "path-spotlight":
            assert path_edges is not None
            highlights = highlights.union(path_edges(sequence, step_index))
        panels.append(SequencePanel(
            number=step_index + 2,
            step=step,
            highlight_ids=frozenset(highlights),
        ))
    return tuple(panels)


def expand_sequence(
    sequence: SequenceDeclaration | None,
    render_panel: PanelRenderer,
    *,
    path_edges: PathEdgeResolver | None = None,
) -> RenderResult:
    """Render and statically expand a complete figure for every sequence panel."""
    if sequence is None:
        return render_panel(SequencePanel(number=1, step=None, highlight_ids=frozenset()))

    panels = sequence_panels(sequence, path_edges=path_edges)
    rendered = tuple(render_panel(panel) for panel in panels)
    panel_markup: list[str] = []
    for panel, result in zip(panels, rendered):
        body = _namespace_panel_markup(result.markup, panel.number)
        if panel.number <= len(sequence.steps):
            label = html.escape(sequence.steps[panel.number - 1].label)
            forecast = f'<p class="ve-seq-next">次の段階: {label}</p>'
        else:
            forecast = '<p class="ve-seq-next">これで全段階です</p>'
        panel_markup.append(
            f'<div data-step="{panel.number}">{body}{forecast}</div>'
        )

    controls = (
        '<div class="ve-stepper-controls">'
        '<button type="button" data-step-action="previous">前へ</button>'
        '<button type="button" data-step-action="next"'
        ' data-next-label="次へ: 次の段階を強調表示">次へ: 次の段階を強調表示</button>'
        '<button type="button" data-step-action="all">全体表示</button>'
        '</div>'
    )
    markup = (
        f'<div data-stepper data-ve-sequence-mode="{html.escape(sequence.mode, quote=True)}"'
        f' data-total-steps="{len(panels)}">'
        f'{"".join(panel_markup)}{controls}</div>'
    )
    first = rendered[0]
    manifest = replace(
        first.manifest,
        generated_landmark_ids=tuple(
            f"{landmark_id}--p{panel.number}"
            for panel, result in zip(panels, rendered)
            for landmark_id in result.manifest.generated_landmark_ids
        ),
        svg_root_ids=tuple(
            f"{svg_id}--p{panel.number}"
            for panel, result in zip(panels, rendered)
            for svg_id in result.manifest.svg_root_ids
        ),
    )
    return RenderResult(
        markup=markup,
        style_asset_ids=first.style_asset_ids,
        script_asset_ids=first.script_asset_ids,
        manifest=manifest,
        diagnostics=tuple(item for result in rendered for item in result.diagnostics),
    )


def claim_before_body(ir: CanonicalIR, body_markup: str) -> str:
    """Return an optional escaped claim immediately before an unchanged body."""
    if ir.claim is None:
        return body_markup
    return f'<p class="ve-claim">{html.escape(ir.claim)}</p>{body_markup}'


def select_style_assets(
    ir: CanonicalIR,
    assets: Iterable[AssetDefinition],
) -> tuple[AssetDefinition, ...]:
    """Select style assets, gating only the shared visual-stage asset."""
    has_stage_fields = any(
        value is not None for value in (ir.claim, ir.sequence, ir.assertions)
    )
    return tuple(
        asset for asset in assets
        if asset.slot == "styles"
        and (asset.id != _VISUAL_STAGE_ASSET_ID or has_stage_fields)
    )
