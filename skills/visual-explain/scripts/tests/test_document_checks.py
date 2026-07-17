"""検査群③: 最終文書の構造検査（check_document_structure）。"""
from __future__ import annotations

import unittest
from pathlib import Path

from build_explainer import build_document
from ve_components.checker import CONTENT_BEGIN, CONTENT_END, check_final_document, extract_controlled_slots
from ve_components.document_checks import check_document_structure
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS

SKILL = Path(__file__).resolve().parents[2]
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS = SKILL / "assets" / "components"
REGISTRY = load_registry(COMPONENTS / "registry.json")
TESTS = Path(__file__).resolve().parent

TITLE = "構造検査用の見本タイトル"


def _msgs(diags) -> list[str]:
    return [d.message for d in diags]


def _content_and_title(html: str) -> tuple[str, str]:
    slots, _ = extract_controlled_slots(html)
    # TITLE is outside controlled slots; parse markers directly.
    tb, te = "<!-- TITLE:BEGIN -->", "<!-- TITLE:END -->"
    title_body = html[html.index(tb) + len(tb):html.index(te)]
    # Strip <title>...</title> wrappers if present.
    t = title_body.strip()
    if t.lower().startswith("<title>") and t.lower().endswith("</title>"):
        t = t[7:-8].strip()
    return slots["content"], t


def _valid_assembly(**doc_extra) -> dict:
    document = {
        "id": "structure-ok",
        "title": TITLE,
        "summary": "要約テキストです。",
        "type": "proposal",
        "profile": "strict",
    }
    document.update(doc_extra)
    return {
        "schemaVersion": 1,
        "document": document,
        "sections": [
            {
                "kind": "first-screen",
                "id": "sec-first",
                "decision": "この提案を採択するか決めます。",
                "conditions": ["前提を共有できること"],
            },
            {
                "kind": "narrative",
                "id": "sec-body",
                "markup": (
                    '<h2>本文</h2><p>根拠を示します。'
                    '<a href="https://docs.example.org/page">出典</a></p>'
                ),
            },
            {
                "kind": "closing",
                "id": "sec-closing",
                "blocks": [
                    {"heading": "リスクと弱い前提", "items": ["前提が弱い"]},
                    {"heading": "不確かな点", "items": ["未確認の利用状況"]},
                ],
            },
        ],
    }


class DocumentStructureBadFixtureTest(unittest.TestCase):
    def _structure_diags(self, name: str):
        html = (TESTS / name).read_text("utf-8")
        content, title = _content_and_title(html)
        return check_document_structure(content, title=title)

    def test_no_first_screen_reports_missing_type_declaration(self) -> None:
        msgs = _msgs(self._structure_diags("structure-bad-no-first-screen.html"))
        self.assertIn("文書型の自己表明がありません", msgs)

    def test_duplicate_h1_reports_h1_cardinality(self) -> None:
        msgs = _msgs(self._structure_diags("structure-bad-duplicate-h1.html"))
        self.assertIn("h1 は first-screen 内にちょうど1個必要です", msgs)

    def test_title_mismatch_reports_title_h1_mismatch(self) -> None:
        msgs = _msgs(self._structure_diags("structure-bad-title-mismatch.html"))
        self.assertIn("title と h1 が一致しません", msgs)

    def test_no_closing_reports_missing_closing(self) -> None:
        msgs = _msgs(self._structure_diags("structure-bad-no-closing.html"))
        self.assertIn("closing セクションがありません", msgs)


class DocumentStructureParserHardeningTest(unittest.TestCase):
    """Group-3 must not trust raw regex against comment-spoofed markup."""

    def test_comment_spoofed_first_screen_does_not_satisfy_declaration(self) -> None:
        # Fake first-screen / closing only inside HTML comments — real body has neither.
        content = (
            '<!-- <section data-ve-section-kind="first-screen"'
            ' data-ve-document-type="proposal" data-ve-profile="strict"> -->\n'
            '<section data-ve-section-kind="narrative" data-ve-instance="sec-body">\n'
            '<section class="first-screen" aria-label="最初に伝えること">\n'
            '  <h1>T</h1>\n'
            '  <p class="subtitle decision"><strong>あなたが決めること:</strong> 決めます。</p>\n'
            '  <p class="subtitle">要約。</p>\n'
            '</section>\n'
            '</section>\n'
            '<!-- </section> -->\n'
            '<!-- <section data-ve-section-kind="closing" id="sec-closing">'
            '<h2>リスクと弱い前提</h2><h2>不確かな点</h2></section> -->\n'
        )
        msgs = _msgs(check_document_structure(content, title="T"))
        self.assertIn("文書型の自己表明がありません", msgs)
        self.assertIn("closing セクションがありません", msgs)

    def test_title_and_h1_charrefs_compare_equal_after_dom_normalize(self) -> None:
        content = (
            '<section data-ve-section-kind="first-screen"'
            ' data-ve-document-type="proposal" data-ve-profile="strict" id="sec-first">\n'
            '<section class="first-screen" aria-label="最初に伝えること">\n'
            '  <h1>A &amp; B</h1>\n'
            '  <p class="subtitle decision"><strong>あなたが決めること:</strong> 決めます。</p>\n'
            '  <p class="subtitle">要約。</p>\n'
            '</section>\n</section>\n'
            '<section data-ve-section-kind="closing" id="sec-closing">\n'
            '<section class="closing-section" aria-label="判断材料">\n'
            '  <h2>リスクと弱い前提</h2>\n  <ul><li>a</li></ul>\n'
            '  <h2>不確かな点</h2>\n  <ul><li>b</li></ul>\n'
            '</section>\n</section>\n'
        )
        # title slot text still contains the entity; both sides must decode alike.
        self.assertEqual(check_document_structure(content, title="A &amp; B"), [])


class DocumentStructureValidTest(unittest.TestCase):
    def test_built_typed_document_has_no_structure_diagnostics(self) -> None:
        html = build_document(
            _valid_assembly(),
            REGISTRY,
            TRUSTED_RENDERERS,
            SKELETON,
            COMPONENTS,
        )
        content, title = _content_and_title(html)
        self.assertEqual(check_document_structure(content, title=title), [])
        self.assertEqual(
            check_final_document(html, SKELETON, REGISTRY, components_dir=COMPONENTS),
            [],
        )

    def test_external_link_marker_mismatch_is_diagnosed(self) -> None:
        html = build_document(
            _valid_assembly(),
            REGISTRY,
            TRUSTED_RENDERERS,
            SKELETON,
            COMPONENTS,
        )
        b = html.index(CONTENT_BEGIN) + len(CONTENT_BEGIN)
        e = html.index(CONTENT_END)
        content = html[b:e]
        # Break the hostname marker while keeping the https href.
        broken = content.replace(
            '<span class="link-domain">‹docs.example.org›</span>',
            '<span class="link-domain">‹evil.example›</span>',
        )
        self.assertIn("‹evil.example›", broken)
        msgs = _msgs(check_document_structure(broken, title=TITLE))
        self.assertTrue(
            any("外部リンクのドメインマーカーが不正です" in m for m in msgs),
            msgs,
        )

    def test_missing_summary_is_diagnosed(self) -> None:
        html = build_document(
            _valid_assembly(),
            REGISTRY,
            TRUSTED_RENDERERS,
            SKELETON,
            COMPONENTS,
        )
        content, title = _content_and_title(html)
        # Remove the summary paragraph (plain subtitle, not .decision).
        broken = content.replace(
            '<p class="subtitle">要約テキストです。</p>',
            "",
            1,
        )
        msgs = _msgs(check_document_structure(broken, title=title))
        self.assertIn("first-screen に summary がありません", msgs)

    def test_invalid_type_vocabulary_is_diagnosed(self) -> None:
        html = build_document(
            _valid_assembly(),
            REGISTRY,
            TRUSTED_RENDERERS,
            SKELETON,
            COMPONENTS,
        )
        content, title = _content_and_title(html)
        broken = content.replace(
            'data-ve-document-type="proposal"',
            'data-ve-document-type="memo"',
            1,
        )
        msgs = _msgs(check_document_structure(broken, title=title))
        self.assertIn("文書型の自己表明が不正です: memo", msgs)

    def test_check_final_document_runs_group3_on_component_docs(self) -> None:
        html = (TESTS / "structure-bad-no-first-screen.html").read_text("utf-8")
        msgs = _msgs(check_final_document(html, SKELETON, REGISTRY, components_dir=COMPONENTS))
        self.assertIn("文書型の自己表明がありません", msgs)

    def test_legacy_document_without_markers_is_not_structure_checked(self) -> None:
        # pre-migration legacy: no VE-CONTROLLED / data-ve → check_final_document 素通し
        legacy = "<!doctype html><html><head><title>t</title></head><body><p>x</p></body></html>"
        self.assertEqual(check_final_document(legacy, SKELETON, REGISTRY, components_dir=COMPONENTS), [])

    def test_example_proposal_passes_group3_when_typed_migration_present(self) -> None:
        # TODO(Task 9): example-proposal.html を型付き IR で再生成したら、このテストは
        # SKIP せずに常時実行される。移行前は first-screen 自己表明が無いため skip。
        example = SKILL / "examples" / "example-proposal.html"
        if not example.is_file():
            self.skipTest("example-proposal.html is missing")
        html = example.read_text("utf-8")
        if 'data-ve-section-kind="first-screen"' not in html:
            self.skipTest(
                "example-proposal.html not yet migrated to typed first-screen (Task 9)"
            )
        self.assertEqual(
            check_final_document(html, SKELETON, REGISTRY, components_dir=COMPONENTS),
            [],
        )


if __name__ == "__main__":
    unittest.main()