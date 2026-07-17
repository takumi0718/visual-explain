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

    def test_ask_id_with_quote_character_is_detected_as_unsafe(self) -> None:
        """A decision ask id ends up as the DOM ``.id`` property and is
        spliced into a CSS attribute selector by the fixed decision-panel
        binder script (``panel.querySelector(`[data-ve-panel-ask="${ask.id}"]`)``).
        A quote in the id breaks that selector's syntax at runtime.
        ``validate_assembly`` already rejects this id shape for freshly
        authored IR, but a hand-crafted final document must be caught here
        too, fail-closed, instead of only matching digests blindly.
        """
        digest = compute_ask_digest_from_pairs((('sec-ask"decision', ("opt-a", "opt-b")),))
        content = (
            _FIRST_BLOCK
            + _ask_block(section_id="sec-ask&quot;decision")
            + _CLOSING_BLOCK
            + _panel_block(digest)
        )
        msgs = _msgs(check_document_structure(content, title=None))
        self.assertNotEqual(msgs, [])

    def test_option_id_with_quote_character_is_detected_as_unsafe(self) -> None:
        """An option id is read by the fixed decision-panel binder script via
        ``item.dataset.askOptionId`` and used as a selection-state key; the
        same safe-token contract that protects the ask wrapper id must also
        cover option ids. A hand-crafted final document can carry a
        tampered, unsafe option id alongside a digest recomputed to match it
        exactly — a checker that only re-derives the digest from whatever
        option ids it collected, without validating their shape, would wave
        this through. It must fail closed instead.
        """
        digest = compute_ask_digest_from_pairs((("sec-ask-decision", ('opt"a', "opt-b")),))
        content = (
            _FIRST_BLOCK
            + _ask_block(option_ids=("opt&quot;a", "opt-b"))
            + _CLOSING_BLOCK
            + _panel_block(digest)
        )
        msgs = _msgs(check_document_structure(content, title=None))
        self.assertNotEqual(msgs, [])

    def test_ask_id_with_trailing_newline_is_detected_as_unsafe(self) -> None:
        """Python's ``$`` anchor matches just before a string-final newline
        under ``re.match``, so a naive safe-token check using ``match``
        would accept 'sec-ask-decision\\n' as if the trailing newline were
        not there. A hand-crafted final document can render that newline as
        ``&#10;`` inside the id attribute; the checker must reject it.
        """
        digest = compute_ask_digest_from_pairs((("sec-ask-decision\n", ("opt-a", "opt-b")),))
        content = (
            _FIRST_BLOCK
            + _ask_block(section_id="sec-ask-decision&#10;")
            + _CLOSING_BLOCK
            + _panel_block(digest)
        )
        msgs = _msgs(check_document_structure(content, title=None))
        self.assertNotEqual(msgs, [])

    def test_option_id_with_trailing_newline_is_detected_as_unsafe(self) -> None:
        """Same trailing-newline gap as the ask id, but on an option id."""
        digest = compute_ask_digest_from_pairs((("sec-ask-decision", ("opt-a\n", "opt-b")),))
        content = (
            _FIRST_BLOCK
            + _ask_block(option_ids=("opt-a&#10;", "opt-b"))
            + _CLOSING_BLOCK
            + _panel_block(digest)
        )
        msgs = _msgs(check_document_structure(content, title=None))
        self.assertNotEqual(msgs, [])

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

    def test_option_id_on_section_tag_is_detected_as_tampering(self) -> None:
        """An option element renamed from <li> to <section> must still count
        toward the enclosing decision ask's digest — a parser that returns
        early on tag == "section" before scanning for
        ``data-ask-option-id`` would silently drop it, letting a forged
        panel digest (computed as if the option never existed) pass.
        """
        html = build_document(
            _decision_assembly(),
            REGISTRY,
            TRUSTED_RENDERERS,
            SKELETON,
            COMPONENTS,
            document_path="doc.html",
        )
        self.assertIn(
            '<li data-ask-option data-ask-option-id="opt-adopt" data-ask-default>',
            html,
        )
        tampered = html.replace(
            '<li data-ask-option data-ask-option-id="opt-adopt" data-ask-default>',
            '<section data-ask-option data-ask-option-id="opt-adopt" data-ask-default>',
            1,
        ).replace(
            '</span></li><li data-ask-option data-ask-option-id="opt-hold">',
            '</span></section><li data-ask-option data-ask-option-id="opt-hold">',
            1,
        )
        # Panel digest forged to match a document where opt-adopt never
        # existed — exactly what a parser blind to <section>-tagged
        # options would (wrongly) compute as "expected".
        stale_digest = compute_ask_digest_from_pairs(
            (("sec-ask-decision", ("opt-hold",)),)
        )
        marker = 'data-ve-ask-digest="'
        start = tampered.index(marker) + len(marker)
        end = tampered.index('"', start)
        tampered = tampered[:start] + stale_digest + tampered[end:]
        msgs = _msgs(check_final_document(tampered, SKELETON, REGISTRY, components_dir=COMPONENTS))
        self.assertEqual(msgs, ["回収パネルの ask 契約ダイジェストが一致しません"])

    def test_empty_option_id_attribute_still_counts_toward_digest(self) -> None:
        """``data-ask-option-id=""`` is attribute *presence*, not absence —
        a parser using truthiness (``if option_id:``) instead of
        ``"data-ask-option-id" in attr_map`` would silently drop it,
        letting a forged digest computed without that option pass. (The
        blank id is also, separately, an unsafe id shape — that diagnostic
        is expected too and is not what this test is about.)
        """
        ask = (
            '<section data-ve-section-kind="ask" data-ve-ask-type="decision" id="sec-ask-decision">\n'
            '<div class="ask" data-ask="decision">\n'
            '  <ul class="ask-options">'
            '<li data-ask-option data-ask-option-id=""><span>blank</span></li>'
            '<li data-ask-option data-ask-option-id="opt-b"><span>opt-b</span></li>'
            '</ul>\n'
            '</div>\n</section>\n'
        )
        # Digest recorded in the panel reflects only opt-b, as a checker
        # that treats the empty value as "no attribute" would compute.
        stale_digest = compute_ask_digest_from_pairs((("sec-ask-decision", ("opt-b",)),))
        content = _FIRST_BLOCK + ask + _CLOSING_BLOCK + _panel_block(stale_digest)
        msgs = _msgs(check_document_structure(content, title=None))
        self.assertIn("回収パネルの ask 契約ダイジェストが一致しません", msgs)

    def test_self_closing_fake_ask_section_is_rejected(self) -> None:
        """A self-closing ``<section .../>`` is invisible to a naive HTMLParser
        subclass whose ``handle_startendtag`` is a no-op, yet real browsers do
        NOT self-close non-void elements: they open the section and keep it
        open. A ``no-op`` parser would report this document as clean (no
        decision ask, no panel needed) while a browser actually materializes
        a genuine ask-decision section. The checker must fail closed instead.
        """
        fake_ask = (
            '<section data-ve-section-kind="ask" data-ve-ask-type="decision"'
            ' id="sec-ask-fake"/>\n'
        )
        content = _FIRST_BLOCK + fake_ask + _CLOSING_BLOCK
        msgs = _msgs(check_document_structure(content, title=None))
        self.assertNotEqual(msgs, [])

    def test_self_closing_fake_panel_section_is_rejected(self) -> None:
        """A genuine, correctly-closed decision panel is present and valid,
        but an extra self-closing ``<section data-ve-section-kind=
        "decision-panel" .../>`` is smuggled in alongside it. Browsers would
        materialize two decision-panel sections (violating the ``ちょうど1個``
        cardinality rule); a parser that no-ops self-closing tags never sees
        the extra one and would wrongly report the document as clean.
        """
        digest = compute_ask_digest_from_pairs((("sec-ask-decision", ("opt-a", "opt-b")),))
        fake_panel = (
            '<section data-ve-section-kind="decision-panel" id="sec-fake-panel"'
            ' data-ve-document-id="x" data-ve-schema-version="1"'
            ' data-ve-ask-digest="deadbeefdeadbeef" data-ve-document-path="x"/>\n'
        )
        content = (
            _FIRST_BLOCK + _ask_block() + _CLOSING_BLOCK + _panel_block(digest) + fake_panel
        )
        msgs = _msgs(check_document_structure(content, title=None))
        self.assertNotEqual(msgs, [])

    def test_self_closing_fake_panel_fails_final_check(self) -> None:
        """End-to-end: a genuinely built decision document (real ask + real
        panel, all group-3 checks clean) must still FAIL check_final_document
        once a self-closing spoofed decision-panel is smuggled into the
        markup, even though it carries no children and never appears in a
        naive parser's section list.
        """
        html = build_document(
            _decision_assembly(), REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS,
            document_path="doc.html",
        )
        fake_panel = (
            '<section data-ve-section-kind="decision-panel" id="sec-fake-panel"'
            ' data-ve-document-id="x" data-ve-schema-version="1"'
            ' data-ve-ask-digest="deadbeefdeadbeef" data-ve-document-path="x"/>\n'
        )
        tampered = html.replace(CONTENT_END, fake_panel + CONTENT_END, 1)
        msgs = _msgs(check_final_document(tampered, SKELETON, REGISTRY, components_dir=COMPONENTS))
        self.assertNotEqual(msgs, [])


if __name__ == "__main__":
    unittest.main()