"""Task 3 tests: controlled skeleton slots and fail-closed safety checks."""
from __future__ import annotations

import unittest
from pathlib import Path

from ve_components.checker import (
    check_final_document,
    extract_controlled_slots,
    normalized_fixed_regions,
    validate_content_markup,
    validate_controlled_assets,
)
from ve_components.registry import Registry, load_registry

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "visual-explain"
SKELETON = (SKILL / "assets" / "skeleton.html").read_text("utf-8")
REGISTRY = load_registry(SKILL / "assets" / "components" / "registry.json")
TESTS = SKILL / "scripts" / "tests"

STYLES_BEGIN = "<!-- VE-CONTROLLED:COMPONENT-STYLES:BEGIN -->"


def codes(diags) -> set[str]:
    return {d.code for d in diags}


class SkeletonMarkerTest(unittest.TestCase):
    def test_three_pairs_present_empty_and_ordered(self) -> None:
        slots, diags = extract_controlled_slots(SKELETON)
        self.assertEqual(diags, [])
        self.assertEqual(set(slots), {"styles", "content", "scripts"})
        for name in ("styles", "content", "scripts"):
            self.assertEqual(slots[name].strip(), "")

    def test_style_markers_are_in_head(self) -> None:
        head_end = SKELETON.index("</head>")
        self.assertLess(SKELETON.index(STYLES_BEGIN), head_end)

    def test_missing_marker_is_reported(self) -> None:
        broken = SKELETON.replace(STYLES_BEGIN, "", 1)
        _, diags = extract_controlled_slots(broken)
        self.assertIn("missing_controlled_marker", codes(diags))


class FixedRegionTest(unittest.TestCase):
    def test_change_inside_slot_is_allowed(self) -> None:
        cb = "<!-- VE-CONTROLLED:CONTENT:BEGIN -->"
        ce = "<!-- VE-CONTROLLED:CONTENT:END -->"
        b, e = SKELETON.index(cb) + len(cb), SKELETON.index(ce)
        candidate = SKELETON[:b] + "\n    <section>本文</section>\n    " + SKELETON[e:]
        self.assertEqual(normalized_fixed_regions(candidate, SKELETON), [])

    def test_change_outside_slot_fails(self) -> None:
        candidate = SKELETON.replace("AI が生成した資料", "改竄済み")
        self.assertIn("fixed_region_mismatch", codes(normalized_fixed_regions(candidate, SKELETON)))


class ContentMarkupTest(unittest.TestCase):
    def bad(self, markup: str) -> None:
        self.assertIn("forbidden_content_markup", codes(validate_content_markup(markup)))

    def test_style_tag(self) -> None:
        self.bad("<style>.x{}</style>")

    def test_script_tag(self) -> None:
        self.bad("<script>alert(1)</script>")

    def test_link_tag(self) -> None:
        self.bad('<link rel="stylesheet" href="x.css">')

    def test_base_tag(self) -> None:
        self.bad('<base href="/">')

    def test_iframe_tag(self) -> None:
        self.bad('<iframe src="x"></iframe>')

    def test_inline_style_attr(self) -> None:
        self.bad('<p style="color:red">x</p>')

    def test_event_handler(self) -> None:
        self.bad('<button onclick="x()">x</button>')

    def test_https_href_allowed(self) -> None:
        self.assertEqual(
            validate_content_markup('<a href="https://example.invalid/x">x</a>'),
            [],
        )

    def test_http_href_rejected(self) -> None:
        diags = validate_content_markup('<a href="http://example.invalid/x">x</a>')
        self.assertIn("forbidden_content_markup", codes(diags))
        self.assertIn(
            "外部リンクは https の絶対 URL か # アンカーだけ使えます: http://example.invalid/x",
            diags[0].message,
        )

    def test_javascript_url(self) -> None:
        diags = validate_content_markup('<a href="javascript:alert(1)">x</a>')
        self.assertIn("forbidden_content_markup", codes(diags))
        self.assertIn(
            "外部リンクは https の絶対 URL か # アンカーだけ使えます: javascript:alert(1)",
            diags[0].message,
        )

    def test_src_https_still_rejected(self) -> None:
        self.bad('<img src="https://example.invalid/x.png" alt="">')

    def test_nested_controlled_marker(self) -> None:
        self.bad("<section><!-- VE-CONTROLLED:CONTENT:BEGIN --></section>")

    def test_clean_markup_passes(self) -> None:
        self.assertEqual(validate_content_markup('<section data-ve-section-kind="canonical"><p>本文</p></section>'), [])


class ControlledAssetTest(unittest.TestCase):
    def test_style_asset_without_provenance_fails(self) -> None:
        slots = {"styles": "<style>.x{}</style>", "scripts": ""}
        self.assertIn("invalid_controlled_asset", codes(validate_controlled_assets(slots, REGISTRY, None)))

    def test_unknown_component_asset_fails(self) -> None:
        slots = {"styles": '<style data-ve-component="matrix" data-ve-contract-version="1" '
                            'data-ve-asset="matrix.css" data-ve-digest="%s">.x{}</style>' % ("0" * 64),
                 "scripts": ""}
        self.assertIn("invalid_controlled_asset", codes(validate_controlled_assets(slots, REGISTRY, None)))

    def test_any_script_asset_fails_with_empty_registry(self) -> None:
        slots = {"styles": "", "scripts": '<script data-ve-component="matrix" data-ve-contract-version="1" '
                                          'data-ve-asset="x.js" data-ve-digest="%s">x</script>' % ("0" * 64)}
        self.assertIn("invalid_controlled_asset", codes(validate_controlled_assets(slots, REGISTRY, None)))

    def test_raw_javascript_in_scripts_slot_fails(self) -> None:
        slots = {"styles": "", "scripts": "\n  var x = 1; alert(2);\n  "}
        self.assertIn("invalid_controlled_asset", codes(validate_controlled_assets(slots, REGISTRY, None)))

    def test_arbitrary_html_in_styles_slot_fails(self) -> None:
        slots = {"styles": "<div>任意のHTML</div>", "scripts": ""}
        self.assertIn("invalid_controlled_asset", codes(validate_controlled_assets(slots, REGISTRY, None)))

    def test_stray_css_text_in_styles_slot_fails(self) -> None:
        slots = {"styles": ".x{color:red}", "scripts": ""}
        self.assertIn("invalid_controlled_asset", codes(validate_controlled_assets(slots, REGISTRY, None)))

    def test_whitespace_only_slots_pass(self) -> None:
        slots = {"styles": "\n  ", "scripts": "\n  "}
        self.assertEqual(validate_controlled_assets(slots, REGISTRY, None), [])

    def test_raw_javascript_document_fails_check_final(self) -> None:
        sb = "<!-- VE-CONTROLLED:COMPONENT-SCRIPTS:BEGIN -->"
        se = "<!-- VE-CONTROLLED:COMPONENT-SCRIPTS:END -->"
        b, e = SKELETON.index(sb) + len(sb), SKELETON.index(se)
        doc = SKELETON[:b] + "\n  alert('x');\n  " + SKELETON[e:]
        diags = check_final_document(doc, SKELETON, REGISTRY, components_dir=SKILL / "assets" / "components")
        self.assertIn("invalid_controlled_asset", codes(diags))

    def test_unclosed_script_slot_fails_closed(self) -> None:
        slots = {"styles": "", "scripts": "<script>alert(1);/*"}
        self.assertIn("invalid_controlled_asset", codes(validate_controlled_assets(slots, REGISTRY, None)))

    def test_unclosed_style_slot_fails_closed(self) -> None:
        slots = {"styles": "<style>.x{color:red}", "scripts": ""}
        self.assertIn("invalid_controlled_asset", codes(validate_controlled_assets(slots, REGISTRY, None)))

    def test_mismatched_end_tag_fails_closed(self) -> None:
        slots = {"styles": "", "scripts": "<script></style>"}
        self.assertIn("invalid_controlled_asset", codes(validate_controlled_assets(slots, REGISTRY, None)))

    def test_stray_close_tag_fails_closed(self) -> None:
        slots = {"styles": "</style>", "scripts": ""}
        self.assertIn("invalid_controlled_asset", codes(validate_controlled_assets(slots, REGISTRY, None)))

    def test_unclosed_script_document_fails_check_final(self) -> None:
        sb = "<!-- VE-CONTROLLED:COMPONENT-SCRIPTS:BEGIN -->"
        se = "<!-- VE-CONTROLLED:COMPONENT-SCRIPTS:END -->"
        b, e = SKELETON.index(sb) + len(sb), SKELETON.index(se)
        doc = SKELETON[:b] + "\n  <script>alert(1);/*\n  " + SKELETON[e:]
        diags = check_final_document(doc, SKELETON, REGISTRY, components_dir=SKILL / "assets" / "components")
        self.assertIn("invalid_controlled_asset", codes(diags))


class BadFixtureTest(unittest.TestCase):
    """The four Task 3 bad fixtures fail the safety layer where required."""

    def check(self, name: str) -> set[str]:
        raw = (TESTS / name).read_text("utf-8")
        return codes(check_final_document(raw, SKELETON, REGISTRY, components_dir=SKILL / "assets" / "components"))

    def test_bad_fixed_region(self) -> None:
        self.assertIn("fixed_region_mismatch", self.check("component-bad-fixed-region.html"))

    def test_bad_content_style(self) -> None:
        self.assertIn("forbidden_content_markup", self.check("component-bad-content-style.html"))

    def test_bad_content_script(self) -> None:
        self.assertIn("forbidden_content_markup", self.check("component-bad-content-script.html"))

    def test_bad_asset_hash(self) -> None:
        self.assertIn("invalid_controlled_asset", self.check("component-bad-asset-hash.html"))

    def test_skeleton_itself_passes_safety(self) -> None:
        # Empty skeleton matches itself on fixed regions / assets. Group-3
        # structure checks still fire on the blank CONTENT slot.
        diags = check_final_document(SKELETON, SKELETON, REGISTRY)
        self.assertTrue(diags)
        self.assertTrue(all(d.code == "document_structure_violation" for d in diags))
        msgs = {d.message for d in diags}
        self.assertIn("文書型の自己表明がありません", msgs)
        self.assertIn("closing セクションがありません", msgs)


if __name__ == "__main__":
    unittest.main()
