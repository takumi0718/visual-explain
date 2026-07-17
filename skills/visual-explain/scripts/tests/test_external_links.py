"""Task 7: https source links with renderer-generated domain markers."""
from __future__ import annotations

import unittest
from pathlib import Path

from build_explainer import build_document
from ve_components.assembly import process_compatibility_section, process_narrative_section
from ve_components.checker import validate_content_markup
from ve_components.diagnostics import ContractError
from ve_components.model import CompatibilityProvenance, CompatibilitySection, NarrativeSection
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = REPO_ROOT / "skills" / "visual-explain"
SKELETON = (SKILL_DIR / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS_DIR = SKILL_DIR / "assets" / "components"
REGISTRY = load_registry(COMPONENTS_DIR / "registry.json")

_DIAG = "外部リンクは https の絶対 URL か # アンカーだけ使えます"


def _msgs(exc: ContractError) -> str:
    return " ".join(d.message for d in exc.diagnostics)


def _diags(markup: str, **kwargs) -> list:
    return validate_content_markup(markup, **kwargs)


def _compat(markup: str) -> CompatibilitySection:
    return CompatibilitySection(
        id="sec-compat",
        markup=markup,
        provenance=CompatibilityProvenance(
            source="legacy-html-insertion",
            reason="unmigrated-format",
            format="layers",
        ),
    )


class NarrativeHttpsHrefTest(unittest.TestCase):
    def test_https_href_allowed_in_narrative(self) -> None:
        diags = _diags(
            '<p><a href="https://example.com/doc">出典</a></p>',
            section_kind="narrative",
        )
        self.assertEqual(diags, [])

    def test_hash_anchor_allowed(self) -> None:
        diags = _diags('<p><a href="#sec-body">節へ</a></p>', section_kind="narrative")
        self.assertEqual(diags, [])

    def test_http_href_rejected(self) -> None:
        diags = _diags(
            '<p><a href="http://example.com/x">x</a></p>',
            section_kind="narrative",
        )
        self.assertTrue(diags)
        self.assertIn(f"{_DIAG}: http://example.com/x", diags[0].message)

    def test_relative_url_rejected(self) -> None:
        diags = _diags('<p><a href="docs/page.html">x</a></p>', section_kind="narrative")
        self.assertTrue(diags)
        self.assertIn(f"{_DIAG}: docs/page.html", diags[0].message)

    def test_javascript_href_rejected(self) -> None:
        diags = _diags(
            '<p><a href="javascript:alert(1)">x</a></p>',
            section_kind="narrative",
        )
        self.assertTrue(diags)
        self.assertIn(f"{_DIAG}: javascript:alert(1)", diags[0].message)

    def test_protocol_relative_rejected(self) -> None:
        diags = _diags('<p><a href="//example.com/x">x</a></p>', section_kind="narrative")
        self.assertTrue(diags)
        self.assertIn(f"{_DIAG}: //example.com/x", diags[0].message)

    def test_data_href_rejected(self) -> None:
        diags = _diags(
            '<p><a href="data:text/html,hi">x</a></p>',
            section_kind="narrative",
        )
        self.assertTrue(diags)
        self.assertIn(f"{_DIAG}: data:text/html,hi", diags[0].message)

    def test_file_href_rejected(self) -> None:
        diags = _diags(
            '<p><a href="file:///etc/passwd">x</a></p>',
            section_kind="narrative",
        )
        self.assertTrue(diags)
        self.assertIn(f"{_DIAG}: file:///etc/passwd", diags[0].message)

    def test_src_https_still_rejected(self) -> None:
        diags = _diags(
            '<img src="https://example.com/a.png" alt="">',
            section_kind="narrative",
        )
        self.assertTrue(diags)
        self.assertIn("外部参照は禁止です: https://example.com/a.png", diags[0].message)

    def test_malformed_ipv6_https_rejected_as_diagnostic(self) -> None:
        """urlsplit ValueError must become the standard href diagnostic, not a crash."""
        diags = _diags('<p><a href="https://[">x</a></p>', section_kind="narrative")
        self.assertTrue(diags)
        self.assertIn(f"{_DIAG}: https://[", diags[0].message)

    def test_fullwidth_at_in_netloc_rejected_as_diagnostic(self) -> None:
        url = "https://example＠evil.com/x"
        diags = _diags(f'<p><a href="{url}">x</a></p>', section_kind="narrative")
        self.assertTrue(diags)
        self.assertIn(f"{_DIAG}: {url}", diags[0].message)

    def test_non_integer_port_rejected(self) -> None:
        url = "https://example.com:bad/x"
        diags = _diags(f'<p><a href="{url}">x</a></p>', section_kind="narrative")
        self.assertTrue(diags)
        self.assertIn(f"{_DIAG}: {url}", diags[0].message)

    def test_port_out_of_range_rejected(self) -> None:
        url = "https://example.com:99999/x"
        diags = _diags(f'<p><a href="{url}">x</a></p>', section_kind="narrative")
        self.assertTrue(diags)
        self.assertIn(f"{_DIAG}: {url}", diags[0].message)

    def test_self_closing_anchor_rejected(self) -> None:
        diags = _diags(
            '<p><a href="https://example.com/x"/></p>',
            section_kind="narrative",
        )
        self.assertTrue(diags)
        self.assertIn("self-closing の <a> は使えません", diags[0].message)

    def test_unclosed_anchor_rejected(self) -> None:
        diags = _diags(
            '<p><a href="https://example.com/x">x</p>',
            section_kind="narrative",
        )
        self.assertTrue(diags)
        self.assertIn("未閉鎖の <a> は使えません", diags[0].message)


class CompatibilityKeepsLegacyTest(unittest.TestCase):
    def test_compatibility_still_rejects_https_href(self) -> None:
        diags = _diags(
            '<p><a href="https://example.com/x">x</a></p>',
            section_kind="compatibility",
        )
        self.assertTrue(diags)
        self.assertIn("外部参照は禁止です: https://example.com/x", diags[0].message)

    def test_process_compatibility_rejects_https(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            process_compatibility_section(
                _compat('<p><a href="https://example.com/x">x</a></p>')
            )
        self.assertIn("外部参照は禁止です", _msgs(ctx.exception))


class DomainMarkerTest(unittest.TestCase):
    def test_process_narrative_inserts_domain_marker(self) -> None:
        sec = NarrativeSection(
            id="sec-src",
            markup='<p><a href="https://example.com/path">Anthropic 公式</a></p>',
        )
        wrapped = process_narrative_section(sec)
        self.assertIn('href="https://example.com/path"', wrapped.markup)
        span = '<span class="link-domain">‹example.com›</span>'
        self.assertIn(span, wrapped.markup)
        a_open = wrapped.markup.index("<a ")
        a_close = wrapped.markup.index("</a>", a_open)
        self.assertIn(span, wrapped.markup[a_open:a_close])

    def test_idn_hostname_preserved(self) -> None:
        sec = NarrativeSection(
            id="sec-idn",
            markup='<p><a href="https://日本語.jp/x">記事</a></p>',
        )
        wrapped = process_narrative_section(sec)
        self.assertIn('<span class="link-domain">‹日本語.jp›</span>', wrapped.markup)

    def test_hash_anchor_gets_no_marker(self) -> None:
        sec = NarrativeSection(
            id="sec-hash",
            markup='<p><a href="#sec-body">節へ</a></p>',
        )
        wrapped = process_narrative_section(sec)
        self.assertNotIn("link-domain", wrapped.markup)

    def test_model_fake_marker_rejected(self) -> None:
        sec = NarrativeSection(
            id="sec-fake",
            markup=(
                '<p><a href="https://evil.example/">x'
                '<span class="link-domain">‹trusted.example›</span></a></p>'
            ),
        )
        with self.assertRaises(ContractError) as ctx:
            process_narrative_section(sec)
        self.assertIn("予約 class link-domain", _msgs(ctx.exception))

    def test_build_document_passes_with_https_source_link(self) -> None:
        raw = {
            "schemaVersion": 1,
            "document": {
                "id": "doc",
                "title": "出典リンク検証",
                "summary": "https 出典を含む。",
                "type": "research",
                "profile": "strict",
            },
            "sections": [
                {"kind": "first-screen", "id": "sec-first", "decision": "出典を確認する。"},
                {
                    "kind": "narrative",
                    "id": "sec-body",
                    "markup": (
                        "<p>根拠は"
                        '<a href="https://docs.example.org/guide">公式ガイド</a>'
                        "。</p>"
                    ),
                },
                {
                    "kind": "closing",
                    "id": "sec-closing",
                    "blocks": [{"heading": "限界・反証・確度", "items": ["一次資料のみ"]}],
                },
            ],
        }
        doc = build_document(raw, REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS_DIR)
        self.assertIn('href="https://docs.example.org/guide"', doc)
        self.assertIn('<span class="link-domain">‹docs.example.org›</span>', doc)


class T07EdgeCaseTest(unittest.TestCase):
    def test_lone_cr_before_lf_does_not_shift_marker(self) -> None:
        # HTMLParser は \n だけを行として数えるが、splitlines は \r も分割する。
        # 単独 CR を含む markup でマーカーが </a> の直前に入ることを固定する。
        from ve_components.assembly import insert_link_domain_markers

        markup = '<p>\rfoo\n<a href="https://example.com">x</a></p>'
        result = insert_link_domain_markers(markup)
        self.assertEqual(
            result,
            '<p>\rfoo\n<a href="https://example.com">x'
            '<span class="link-domain">‹example.com›</span></a></p>',
        )

    def test_namespaced_external_href_rejected_in_narrative(self) -> None:
        from ve_components.checker import validate_content_markup

        markup = '<svg viewBox="0 0 10 10"><a xlink:href="https://example.com">x</a></svg>'
        diags = validate_content_markup(markup, section_kind="narrative")
        self.assertTrue(any("名前空間つき href では外部リンクを使えません" in d.message for d in diags))

    def test_namespaced_anchor_href_still_allowed(self) -> None:
        from ve_components.checker import validate_content_markup

        markup = '<svg viewBox="0 0 10 10"><a xlink:href="#sec-a">x</a></svg>'
        diags = validate_content_markup(markup, section_kind="narrative")
        self.assertFalse(any("名前空間つき" in d.message for d in diags))
