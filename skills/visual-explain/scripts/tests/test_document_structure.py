"""構造不変条件: first-screen/closing の位置・個数、narrative の h1/予約属性禁止。"""
from __future__ import annotations

import unittest

from ve_components.diagnostics import ContractError
from ve_components.validation import validate_assembly

_DOC = {
    "id": "doc-1",
    "title": "料金改定は限定対象で段階公開する",
    "summary": "要約文。",
    "type": "proposal",
    "profile": "strict",
}

_FIRST = {"kind": "first-screen", "id": "sec-first", "decision": "決めます。"}
_CLOSING = {
    "kind": "closing",
    "id": "sec-closing",
    "blocks": [
        {"heading": "リスクと弱い前提", "items": ["前提Aが弱い"]},
        {"heading": "不確かな点", "items": ["未確認の利用状況"]},
    ],
}
_NARR = {"kind": "narrative", "id": "sec-body", "markup": "<p>本文です。</p>"}

# criteria / Global Constraints の予約トークン一覧（診断ラベル付き）。
_RESERVED_DATA_CASES = (
    ("data-ve-instance", "data-ve-*", 'data-ve-instance="x"'),
    ("data-connect", "data-connect", 'data-connect="a->b"'),
    ("data-connect-scope", "data-connect-scope", "data-connect-scope"),
    ("data-stepper", "data-stepper", 'data-stepper="1"'),
    ("data-step", "data-step", 'data-step="1"'),
    ("data-step-action", "data-step-action", 'data-step-action="next"'),
    ("data-ask", "data-ask", 'data-ask="decision"'),
    ("data-ask-option", "data-ask-*", "data-ask-option"),
    ("data-theme", "data-theme", 'data-theme="dark"'),
    ("data-theme-pref", "data-theme-*", 'data-theme-pref="system"'),
    ("data-lane", "data-lane", 'data-lane="input"'),
    ("data-tone", "data-tone", 'data-tone="warning"'),
)
_RESERVED_CLASS_CASES = (
    "first-screen",
    "closing-section",
    "ask",
    "link-domain",
    "decision-panel",
)


def _assembly(*sections: dict) -> dict:
    return {"schemaVersion": 1, "document": dict(_DOC), "sections": list(sections)}


def _messages(exc: ContractError) -> str:
    return " ".join(str(d) for d in exc.diagnostics)


class DocumentStructureTest(unittest.TestCase):
    def test_rejects_missing_first_screen(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_CLOSING))
        self.assertIn("first-screen は先頭にちょうど1個必要です", _messages(ctx.exception))

    def test_rejects_two_first_screens(self) -> None:
        second = {"kind": "first-screen", "id": "sec-first-2", "decision": "別の判断をします。"}
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_FIRST, second, _CLOSING))
        self.assertIn("first-screen は先頭にちょうど1個必要です", _messages(ctx.exception))

    def test_rejects_first_screen_not_at_front(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_NARR, _FIRST, _CLOSING))
        self.assertIn("first-screen は先頭にちょうど1個必要です", _messages(ctx.exception))

    def test_rejects_missing_closing(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_FIRST))
        self.assertIn("closing は最後にちょうど1個必要です", _messages(ctx.exception))

    def test_rejects_narrative_after_closing(self) -> None:
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_FIRST, _CLOSING, _NARR))
        self.assertIn("closing は最後にちょうど1個必要です", _messages(ctx.exception))

    def test_rejects_h1_in_narrative(self) -> None:
        narr = {"kind": "narrative", "id": "sec-bad-h1", "markup": "<h1>見出し</h1><p>本文</p>"}
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_FIRST, narr, _CLOSING))
        self.assertIn("narrative に <h1> は置けません（h1 は first-screen 専有）", _messages(ctx.exception))

    def test_rejects_duplicate_class_attr_hiding_reserved_class(self) -> None:
        # Duplicate class attrs: browsers may keep the first value (first-screen),
        # so collapsing to the last value would incorrectly allow this markup.
        narr = {
            "kind": "narrative",
            "id": "sec-dup-class",
            "markup": '<section class="first-screen" class="safe"><p>本文</p></section>',
        }
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_FIRST, narr, _CLOSING))
        self.assertIn("narrative に予約 class first-screen は置けません", _messages(ctx.exception))

    def test_valid_structure_accepted(self) -> None:
        req = validate_assembly(_assembly(_FIRST, _NARR, _CLOSING))
        self.assertEqual(len(req.sections), 3)

    def test_compatibility_allows_reserved_attrs(self) -> None:
        compat = {
            "kind": "compatibility",
            "id": "sec-compat",
            "markup": '<ol class="flow" data-connect="a->b"><li id="a">A</li><li id="b">B</li></ol>',
            "provenance": {
                "source": "legacy-html-insertion",
                "reason": "unmigrated-format",
                "format": "flow",
            },
        }
        req = validate_assembly(_assembly(_FIRST, compat, _CLOSING))
        self.assertEqual(len(req.sections), 3)

    def test_compatibility_rejects_h1(self) -> None:
        compat = {
            "kind": "compatibility",
            "id": "sec-compat-h1",
            "markup": "<h1>禁止</h1><p>legacy</p>",
            "provenance": {
                "source": "legacy-html-insertion",
                "reason": "unmigrated-format",
                "format": "freeform",
            },
        }
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(_assembly(_FIRST, compat, _CLOSING))
        self.assertIn("<h1>", _messages(ctx.exception))


class NarrativeReservedTokenCoverageTest(unittest.TestCase):
    """Parametrize reserved data attrs / classes so list/prefix regressions fail closed."""

    def test_reserved_data_attrs(self) -> None:
        for _name, label, attr_html in _RESERVED_DATA_CASES:
            with self.subTest(attr=label):
                narr = {
                    "kind": "narrative",
                    "id": f"sec-bad-{label}",
                    "markup": f"<div {attr_html}><p>本文</p></div>",
                }
                with self.assertRaises(ContractError) as ctx:
                    validate_assembly(_assembly(_FIRST, narr, _CLOSING))
                self.assertIn(
                    f"narrative に予約属性 {label} は置けません",
                    _messages(ctx.exception),
                )

    def test_reserved_classes(self) -> None:
        for cls in _RESERVED_CLASS_CASES:
            with self.subTest(cls=cls):
                narr = {
                    "kind": "narrative",
                    "id": f"sec-bad-cls-{cls}",
                    "markup": f'<div class="{cls}"><p>本文</p></div>',
                }
                with self.assertRaises(ContractError) as ctx:
                    validate_assembly(_assembly(_FIRST, narr, _CLOSING))
                self.assertIn(
                    f"narrative に予約 class {cls} は置けません",
                    _messages(ctx.exception),
                )
