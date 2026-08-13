"""Task 13 visual-stage assertion/narrative overlap checks."""
from __future__ import annotations

from html import escape

from ve_components.assembly import ExpectedCanonicalRecord
from ve_components.document_checks import check_document_structure
from ve_components.model import Assertion


def _record(
    assertion_texts: tuple[tuple[str, str], ...],
    *,
    instance_id: str = "sec-map",
) -> ExpectedCanonicalRecord:
    assertions = tuple(
        Assertion(assertion_id, text, ("node-a",))
        for assertion_id, text in assertion_texts
    )
    return ExpectedCanonicalRecord(
        component_id="flow",
        instance_id=instance_id,
        payload_semantic_ids=frozenset({"node-a"}),
        claim=assertions[0].text,
        assertions=assertions,
        sequence=None,
    )


def _content(
    narratives: tuple[str, ...],
    records: tuple[ExpectedCanonicalRecord, ...],
    *,
    closing_body: str = "",
) -> str:
    canonicals = "".join(
        '<section data-ve-section-kind="canonical" data-ve-component="flow" '
        f'data-ve-instance="{record.instance_id}">'
        f'<p class="ve-claim">{escape(record.claim or "")}</p>'
        '<figure data-ve-component="flow"></figure></section>'
        for record in records
    )
    narrative_markup = "".join(
        '<section data-ve-section-kind="narrative" '
        f'data-ve-instance="n-{index}">\n{markup}\n</section>'
        for index, markup in enumerate(narratives, 1)
    )
    return (
        '<section data-ve-section-kind="first-screen" '
        'data-ve-document-type="proposal" data-ve-profile="visual-stage">'
        '<h1>Title</h1><p class="subtitle">Summary</p></section>'
        f'{canonicals}{narrative_markup}'
        '<section data-ve-section-kind="closing"><h2>リスクと弱い前提</h2>'
        f'<h2>不確かな点</h2>{closing_body}</section>'
    )


def _overlap_messages(
    narratives: tuple[str, ...],
    records: tuple[ExpectedCanonicalRecord, ...],
    *,
    closing_body: str = "",
) -> list[str]:
    return [
        diagnostic.message
        for diagnostic in check_document_structure(
            _content(narratives, records, closing_body=closing_body),
            title="Title",
            expected=records,
        )
        if "語句重複" in diagnostic.message
    ]


def test_overlap_threshold_allows_nine_and_rejects_ten_normalized_codepoints() -> None:
    record = _record((("claim", "abcdefghij"),))

    assert _overlap_messages(("abcdefghi",), (record,)) == []
    messages = _overlap_messages(("abcdefghij",), (record,))

    assert len(messages) == 1
    assert "10文字" in messages[0]


def test_overlap_decodes_entities_and_applies_nfkc_to_fullwidth_text() -> None:
    record = _record((
        ("claim", "short"),
        ("normalized", "ＡＢＣＤＥ&amp;ＦＧＨＩＪ"),
    ))

    messages = _overlap_messages(("&#65;&#66;&#67;&#68;&#69;＆ＦＧＨＩＪ",), (record,))

    assert len(messages) == 1
    assert "normalized" in messages[0]


def test_overlap_removes_whitespace_punctuation_and_symbols_including_emoji() -> None:
    record = _record((("claim", "a b,c😀d-e+f=g/h|i★j"),))

    assert len(_overlap_messages(("abcdefghij",), (record,))) == 1


def test_non_contiguous_common_subsequence_is_not_a_common_substring() -> None:
    record = _record((("claim", "a0b0c0d0e0f0g0h0i0j"),))

    assert _overlap_messages(("abcdefghij",), (record,)) == []


def test_every_assertion_of_every_canonical_is_compared() -> None:
    first = _record((("first-claim", "unrelated"),), instance_id="first")
    second = _record(
        (("second-claim", "also unrelated"), ("inventory-item", "inventoryphrase")),
        instance_id="second",
    )

    messages = _overlap_messages(("inventoryphrase",), (first, second))

    assert len(messages) == 1
    assert "second" in messages[0]
    assert "inventory-item" in messages[0]


def test_narrative_to_narrative_and_closing_overlap_are_ignored() -> None:
    record = _record((("claim", "closingphrase"),))

    assert _overlap_messages(
        ("sharednarrative", "sharednarrative"),
        (record,),
        closing_body="<p>closingphrase</p>",
    ) == []


def test_empty_normalized_text_does_not_overlap() -> None:
    record = _record((("claim", " \t。！？😀★+-"),))

    assert _overlap_messages(("。！？😀★+-",), (record,)) == []


def test_only_narrative_plain_text_is_compared_not_markup_or_opaque_text() -> None:
    record = _record((("claim", "hiddenphrase"),))

    assert _overlap_messages((
        '<div data-copy="hiddenphrase"><script>hiddenphrase</script>'
        '<style>.hiddenphrase{color:red}</style>visible</div>',
    ), (record,)) == []


def test_overlap_diagnostics_are_stable_and_bounded() -> None:
    record = _record(tuple(
        (f"assertion-{index:02d}", f"abcdefghij{index:02d}")
        for index in range(40)
    ))

    first = _overlap_messages(("abcdefghij",), (record,))
    second = _overlap_messages(("abcdefghij",), (record,))

    assert first == second
    assert len(first) == 32
    assert "assertion-00" in first[0]
    assert "assertion-31" in first[-1]
