"""Build-time table of contents: threshold, anchors, narrative ids."""
from __future__ import annotations

import re
from pathlib import Path

from build_explainer import build_document
from ve_components.document_sections import TocEntry, build_toc
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS

SKILL_DIR = Path(__file__).resolve().parents[2]
SKELETON = (SKILL_DIR / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS_DIR = SKILL_DIR / "assets" / "components"
REGISTRY = load_registry(COMPONENTS_DIR / "registry.json")

BASE = {
    "schemaVersion": 1,
    "document": {
        "id": "doc",
        "title": "長い資料の目次検証",
        "summary": "目次生成の検証。",
        "type": "system",
        "profile": "strict",
    },
}
FIRST = {"kind": "first-screen", "id": "sec-first", "decision": "決めます。"}
CLOSING = {
    "kind": "closing",
    "id": "sec-closing",
    "blocks": [{"heading": "限界・確度", "items": ["推論を含む"]}],
}


def _narr(sec_id: str, heading: str | None) -> dict:
    if heading is None:
        return {"kind": "narrative", "id": sec_id, "markup": "<p>見出しなし本文</p>"}
    return {
        "kind": "narrative",
        "id": sec_id,
        "markup": f"<h2>{heading}</h2><p>本文</p>",
    }


def _assembly(*middle: dict) -> dict:
    return {**BASE, "sections": [FIRST, *middle, CLOSING]}


def test_build_toc_returns_none_when_fewer_than_five_entries():
    entries = tuple(TocEntry(f"sec-{i}", f"見出し{i}") for i in range(4))
    assert build_toc(entries) is None


def test_build_toc_returns_flat_ol_with_instance_id_anchors():
    entries = tuple(TocEntry(f"sec-{i}", f"見出し{i}") for i in range(5))
    toc = build_toc(entries)
    assert toc is not None
    assert 'data-ve-section-kind="toc"' in toc.markup
    assert '<nav aria-label="目次">' in toc.markup
    assert "<ol>" in toc.markup
    # Flat one-level list: li directly under ol, no nested ol.
    assert re.search(r"<ol>\s*<li>", toc.markup) is not None
    assert toc.markup.count("<ol>") == 1
    for i in range(5):
        assert f'<li><a href="#sec-{i}">見出し{i}</a></li>' in toc.markup


def test_build_document_inserts_toc_after_first_screen_with_narrative_ids():
    # 4 headed narratives + closing = 5 → TOC fires.
    raw = _assembly(
        _narr("sec-a", "論点A"),
        _narr("sec-b", "論点B"),
        _narr("sec-c", "論点C"),
        _narr("sec-d", "論点D"),
    )
    doc = build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS_DIR, document_path="doc.html")

    i_first = doc.index('data-ve-section-kind="first-screen"')
    i_toc = doc.index('data-ve-section-kind="toc"')
    i_a = doc.index('data-ve-instance="sec-a"')
    assert i_first < i_toc < i_a

    assert 'href="#sec-a"' in doc
    assert 'href="#sec-b"' in doc
    assert 'href="#sec-c"' in doc
    assert 'href="#sec-d"' in doc
    assert 'href="#sec-closing"' in doc
    assert ">論点A<" in doc
    assert ">限界・確度<" in doc

    # Anchors are wrapper ids (= instance ids).
    assert re.search(
        r'<section[^>]*data-ve-section-kind="narrative"[^>]*\bid="sec-a"',
        doc,
    )
    assert re.search(
        r'<section[^>]*data-ve-section-kind="narrative"[^>]*\bid="sec-d"',
        doc,
    )
    assert 'id="sec-closing"' in doc


def test_build_document_no_toc_and_no_narrative_id_when_under_threshold():
    # 3 headed narratives + closing = 4 → no TOC; narrative wrappers stay id-less.
    raw = _assembly(
        _narr("sec-a", "論点A"),
        _narr("sec-b", "論点B"),
        _narr("sec-c", "論点C"),
    )
    doc = build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS_DIR, document_path="doc.html")

    assert 'data-ve-section-kind="toc"' not in doc
    assert 'data-ve-instance="sec-a"' in doc
    # No id= on narrative wrappers (existing fixture non-destructive).
    narrative_open = re.findall(
        r'<section\b[^>]*data-ve-section-kind="narrative"[^>]*>',
        doc,
    )
    assert len(narrative_open) == 3
    for tag in narrative_open:
        assert re.search(r'\bid="', tag) is None


def test_headingless_narrative_excluded_from_toc_entries():
    # 4 headed + 1 headingless + closing = 5 headed → TOC fires, but
    # the headingless section must not appear as a TOC link.
    raw = _assembly(
        _narr("sec-a", "論点A"),
        _narr("sec-plain", None),
        _narr("sec-b", "論点B"),
        _narr("sec-c", "論点C"),
        _narr("sec-d", "論点D"),
    )
    doc = build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS_DIR, document_path="doc.html")

    assert 'data-ve-section-kind="toc"' in doc
    assert 'href="#sec-plain"' not in doc
    assert 'href="#sec-a"' in doc
    assert 'href="#sec-d"' in doc
    assert 'href="#sec-closing"' in doc
    assert 'data-ve-instance="sec-plain"' in doc


def test_build_toc_avoids_occupied_instance_id():
    entries = tuple(TocEntry(f"sec-{i}", f"見出し{i}") for i in range(5))
    toc = build_toc(entries, occupied_ids=frozenset({"sec-toc", "sec-toc-2"}))
    assert toc is not None
    assert toc.instance_id not in {"sec-toc", "sec-toc-2"}
    assert toc.instance_id.startswith("sec-toc")


def test_build_document_succeeds_when_user_section_id_is_sec_toc():
    # User may legitimately use id="sec-toc"; TOC must not collide on compose.
    raw = _assembly(
        _narr("sec-toc", "論点TOC"),
        _narr("sec-a", "論点A"),
        _narr("sec-b", "論点B"),
        _narr("sec-c", "論点C"),
    )
    doc = build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS_DIR, document_path="doc.html")

    assert 'data-ve-section-kind="toc"' in doc
    assert 'data-ve-instance="sec-toc"' in doc
    assert 'href="#sec-toc"' in doc
    assert ">論点TOC<" in doc
