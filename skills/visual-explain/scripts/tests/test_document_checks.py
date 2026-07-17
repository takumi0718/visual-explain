"""検査群③: 最終文書の構造検査（check_document_structure）。"""
from __future__ import annotations

import unittest
from pathlib import Path

from build_explainer import build_document
from ve_components.checker import CONTENT_BEGIN, CONTENT_END, check_final_document, extract_controlled_slots
from ve_components.document_checks import check_document_structure
from ve_components.document_sections import compute_ask_digest_from_pairs
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


def _decision_assembly(**doc_extra) -> dict:
    """A valid document with one decision ask, whose panel is built by the real pipeline."""
    assembly = _valid_assembly(**doc_extra)
    assembly["sections"].insert(-1, {
        "kind": "ask",
        "id": "sec-ask-decision",
        "askType": "decision",
        "question": "この提案を採択しますか。",
        "options": [
            {"id": "opt-adopt", "label": "採択する", "tradeoff": "初期コストがかかる"},
            {"id": "opt-hold", "label": "見送る", "tradeoff": "機会を逃す"},
        ],
        "defaultId": "opt-adopt",
    })
    return assembly


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

    def test_panel_missing_reports_decision_ask_without_panel(self) -> None:
        msgs = _msgs(self._structure_diags("structure-bad-panel-missing.html"))
        self.assertEqual(msgs, ["decision ask があるのに回収パネルがありません"])

    def test_panel_digest_tampered_reports_digest_mismatch(self) -> None:
        msgs = _msgs(self._structure_diags("structure-bad-panel-digest.html"))
        self.assertEqual(msgs, ["回収パネルの ask 契約ダイジェストが一致しません"])


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

    def test_duplicate_first_screen_is_rejected(self) -> None:
        # Second first-screen has conflicting type/profile and no h1 — must not be ignored.
        content = (
            '<section data-ve-section-kind="first-screen"'
            ' data-ve-document-type="proposal" data-ve-profile="strict" id="sec-first">\n'
            '<section class="first-screen" aria-label="最初に伝えること">\n'
            '  <h1>タイトル</h1>\n'
            '  <p class="subtitle decision"><strong>あなたが決めること:</strong> 決めます。</p>\n'
            '  <p class="subtitle">要約。</p>\n'
            '</section>\n</section>\n'
            '<section data-ve-section-kind="first-screen"'
            ' data-ve-document-type="research" data-ve-profile="extended" id="sec-first-2">\n'
            '<section class="first-screen" aria-label="最初に伝えること">\n'
            '  <p class="subtitle">別の要約。</p>\n'
            '</section>\n</section>\n'
            '<section data-ve-section-kind="closing" id="sec-closing">\n'
            '<section class="closing-section" aria-label="判断材料">\n'
            '  <h2>リスクと弱い前提</h2>\n  <ul><li>a</li></ul>\n'
            '  <h2>不確かな点</h2>\n  <ul><li>b</li></ul>\n'
            '</section>\n</section>\n'
        )
        msgs = _msgs(check_document_structure(content, title="タイトル"))
        self.assertIn("first-screen はちょうど1個必要です", msgs)


class DocumentStructureValidTest(unittest.TestCase):
    def test_built_decision_document_with_panel_has_no_structure_diagnostics(self) -> None:
        html = build_document(
            _decision_assembly(),
            REGISTRY,
            TRUSTED_RENDERERS,
            SKELETON,
            COMPONENTS,
            document_path="doc.html",
        )
        self.assertIn('data-ve-section-kind="decision-panel"', html)
        content, title = _content_and_title(html)
        self.assertEqual(check_document_structure(content, title=title), [])
        self.assertEqual(
            check_final_document(html, SKELETON, REGISTRY, components_dir=COMPONENTS),
            [],
        )

    def test_built_typed_document_has_no_structure_diagnostics(self) -> None:
        html = build_document(
            _valid_assembly(),
            REGISTRY,
            TRUSTED_RENDERERS,
            SKELETON,
            COMPONENTS,
            document_path="doc.html",
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
            document_path="doc.html",
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
            document_path="doc.html",
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
            document_path="doc.html",
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

    def test_blank_content_component_document_still_runs_group3(self) -> None:
        # Whitespace-only CONTENT must not skip structure checks (canonical bypass).
        # The empty skeleton is a component document with blank content slots.
        msgs = _msgs(check_final_document(SKELETON, SKELETON, REGISTRY, components_dir=COMPONENTS))
        self.assertIn("文書型の自己表明がありません", msgs)
        self.assertIn("closing セクションがありません", msgs)

    def test_example_proposal_passes_group3(self) -> None:
        example = SKILL / "examples" / "example-proposal.html"
        self.assertTrue(example.is_file(), "example-proposal.html is missing")
        html = example.read_text("utf-8")
        self.assertIn('data-ve-section-kind="first-screen"', html)
        msgs = _msgs(check_final_document(html, SKELETON, REGISTRY, components_dir=COMPONENTS))
        self.assertEqual(msgs, [])


_FIRST_BLOCK = (
    '<section data-ve-section-kind="first-screen"'
    ' data-ve-document-type="proposal" data-ve-profile="strict" id="sec-first">\n'
    '<section class="first-screen" aria-label="最初に伝えること">\n'
    '  <h1>T</h1>\n'
    '  <p class="subtitle decision"><strong>あなたが決めること:</strong> 決めます。</p>\n'
    '  <p class="subtitle">要約。</p>\n'
    '</section>\n</section>\n'
)
_CLOSING_BLOCK = (
    '<section data-ve-section-kind="closing" id="sec-closing">\n'
    '<section class="closing-section" aria-label="判断材料">\n'
    '  <h2>リスクと弱い前提</h2>\n  <ul><li>a</li></ul>\n'
    '  <h2>不確かな点</h2>\n  <ul><li>b</li></ul>\n'
    '</section>\n</section>\n'
)


def _ask_block(section_id: str = "sec-ask-decision", option_ids=("opt-a", "opt-b")) -> str:
    options = "".join(
        f'<li data-ask-option data-ask-option-id="{oid}"><span>{oid}</span></li>'
        for oid in option_ids
    )
    return (
        f'<section data-ve-section-kind="ask" data-ve-ask-type="decision" id="{section_id}">\n'
        '<div class="ask" data-ask="decision">\n'
        f'  <ul class="ask-options">{options}</ul>\n'
        '</div>\n</section>\n'
    )


def _panel_block(
    digest: str,
    *,
    document_id: str | None = "doc-1",
    schema_version: str | None = "1",
    document_path: str | None = "out.html",
    instance_id: str = "sec-decision-panel",
) -> str:
    attrs = ""
    if document_id is not None:
        attrs += f' data-ve-document-id="{document_id}"'
    if schema_version is not None:
        attrs += f' data-ve-schema-version="{schema_version}"'
    attrs += f' data-ve-ask-digest="{digest}"'
    if document_path is not None:
        attrs += f' data-ve-document-path="{document_path}"'
    return (
        f'<section data-ve-section-kind="decision-panel"{attrs} id="{instance_id}">\n'
        '<section class="decision-panel" aria-label="判断の回収"><h2>判断の回収</h2></section>\n'
        '</section>\n'
    )


class DecisionPanelStructureTest(unittest.TestCase):
    """検査群③拡張: decision ask ↔ 回収パネルの存在・位置・digest 整合。"""

    def test_no_decision_ask_no_panel_is_clean(self) -> None:
        content = _FIRST_BLOCK + _CLOSING_BLOCK
        self.assertEqual(check_document_structure(content, title=None), [])

    def test_decision_ask_without_panel_reports_missing(self) -> None:
        content = _FIRST_BLOCK + _ask_block() + _CLOSING_BLOCK
        msgs = _msgs(check_document_structure(content, title=None))
        self.assertEqual(msgs, ["decision ask があるのに回収パネルがありません"])

    def test_panel_without_decision_ask_reports_forbidden(self) -> None:
        digest = compute_ask_digest_from_pairs(())
        content = _FIRST_BLOCK + _CLOSING_BLOCK + _panel_block(digest)
        msgs = _msgs(check_document_structure(content, title=None))
        self.assertEqual(msgs, ["decision ask がないのに回収パネルがあります"])

    def test_multiple_panels_reports_cardinality(self) -> None:
        digest = compute_ask_digest_from_pairs((("sec-ask-decision", ("opt-a", "opt-b")),))
        content = (
            _FIRST_BLOCK + _ask_block() + _CLOSING_BLOCK
            + _panel_block(digest, instance_id="sec-decision-panel")
            + _panel_block(digest, instance_id="sec-decision-panel-2")
        )
        msgs = _msgs(check_document_structure(content, title=None))
        self.assertEqual(msgs, ["回収パネルはちょうど1個必要です"])

    def test_panel_before_closing_reports_position(self) -> None:
        digest = compute_ask_digest_from_pairs((("sec-ask-decision", ("opt-a", "opt-b")),))
        content = _FIRST_BLOCK + _ask_block() + _panel_block(digest) + _CLOSING_BLOCK
        msgs = _msgs(check_document_structure(content, title=None))
        self.assertEqual(msgs, ["回収パネルは closing の後に必要です"])

    def test_digest_mismatch_reports_diagnostic(self) -> None:
        content = _FIRST_BLOCK + _ask_block() + _CLOSING_BLOCK + _panel_block("0" * 16)
        msgs = _msgs(check_document_structure(content, title=None))
        self.assertEqual(msgs, ["回収パネルの ask 契約ダイジェストが一致しません"])

    def test_panel_missing_self_declaration_attrs_reports_diagnostic(self) -> None:
        digest = compute_ask_digest_from_pairs((("sec-ask-decision", ("opt-a", "opt-b")),))
        content = _FIRST_BLOCK + _ask_block() + _CLOSING_BLOCK + _panel_block(
            digest, document_path=None,
        )
        msgs = _msgs(check_document_structure(content, title=None))
        self.assertEqual(msgs, ["回収パネルの自己表明属性が不足しています"])

    def test_valid_panel_after_closing_is_clean(self) -> None:
        digest = compute_ask_digest_from_pairs((("sec-ask-decision", ("opt-a", "opt-b")),))
        content = _FIRST_BLOCK + _ask_block() + _CLOSING_BLOCK + _panel_block(digest)
        self.assertEqual(check_document_structure(content, title=None), [])

    def test_option_id_hidden_in_nested_section_is_detected_as_tampering(self) -> None:
        """An option tucked inside a plain nested <section> must still count
        toward the enclosing decision ask's digest — otherwise an option
        smuggled into a nested wrapper evades digest verification entirely.
        """
        nested_ask = (
            '<section data-ve-section-kind="ask" data-ve-ask-type="decision" id="sec-ask-decision">\n'
            '<div class="ask" data-ask="decision">\n'
            '  <ul class="ask-options">'
            '<li data-ask-option data-ask-option-id="opt-a"><span>opt-a</span></li>'
            '</ul>\n'
            '<section class="ask-option-group">\n'
            '  <ul class="ask-options">'
            '<li data-ask-option data-ask-option-id="opt-b"><span>opt-b</span></li>'
            '</ul>\n'
            '</section>\n'
            '</div>\n</section>\n'
        )
        # Digest recorded in the panel reflects only the un-nested option,
        # as a checker that ignores nested-section options would compute.
        stale_digest = compute_ask_digest_from_pairs((("sec-ask-decision", ("opt-a",)),))
        content = _FIRST_BLOCK + nested_ask + _CLOSING_BLOCK + _panel_block(stale_digest)
        msgs = _msgs(check_document_structure(content, title=None))
        self.assertEqual(msgs, ["回収パネルの ask 契約ダイジェストが一致しません"])


if __name__ == "__main__":
    unittest.main()