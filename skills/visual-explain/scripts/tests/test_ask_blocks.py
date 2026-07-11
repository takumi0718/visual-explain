import unittest

from ve_components.checker import validate_ask_blocks

VALID_DECISION = """
<div class="ask" data-ask="decision">
  <p class="ask-kind">判断してください</p>
  <p class="ask-question">注釈を今回に含めますか？</p>
  <ul class="ask-options">
    <li data-ask-option data-ask-default><span>含める</span><span class="ask-tradeoff">変更量が増える</span></li>
    <li data-ask-option><span>次フェーズ</span><span class="ask-tradeoff">効果が遅れる</span></li>
  </ul>
</div>
"""

VALID_REQUEST = """
<div class="ask" data-ask="request">
  <p class="ask-kind">お願いする動作</p>
  <ol class="ask-steps">
    <li data-ask-role="user" data-ask-role-label="あなた">specをレビューする</li>
    <li data-ask-role="agent" data-ask-role-label="Claude">planを執筆する</li>
  </ol>
</div>
"""

VALID_HYPOTHESIS = """
<div class="ask" data-ask="hypothesis">
  <p class="ask-kind">検証待ちの仮説</p>
  <p class="ask-claim">見出しだけで判断できる <span class="certainty inferred">推論</span></p>
  <p class="ask-verify">検証方法: 見出し列のみで判断内容を言えるか確認する</p>
</div>
"""


class AskBlockTest(unittest.TestCase):
    def test_valid_blocks_pass(self):
        for markup in (VALID_DECISION, VALID_REQUEST, VALID_HYPOTHESIS):
            self.assertEqual(validate_ask_blocks(markup), [])

    def test_unknown_kind_fails(self):
        diags = validate_ask_blocks('<div class="ask" data-ask="poll"><p class="ask-question">?</p></div>')
        self.assertEqual([d.code for d in diags], ["ask_contract_violation"])

    def test_decision_needs_two_options(self):
        markup = VALID_DECISION.replace(
            '<li data-ask-option><span>次フェーズ</span><span class="ask-tradeoff">効果が遅れる</span></li>', "")
        self.assertTrue(validate_ask_blocks(markup))

    def test_decision_two_defaults_fail(self):
        markup = VALID_DECISION.replace("<li data-ask-option><span>次フェーズ", "<li data-ask-option data-ask-default><span>次フェーズ")
        self.assertTrue(validate_ask_blocks(markup))

    def test_decision_zero_default_requires_reason(self):
        markup = VALID_DECISION.replace(" data-ask-default", "")
        self.assertTrue(validate_ask_blocks(markup))
        with_reason = markup.replace("</ul>", '</ul><p class="ask-no-default-reason">判断材料が拮抗しているため</p>')
        self.assertEqual(validate_ask_blocks(with_reason), [])

    def test_request_role_must_be_semantic(self):
        markup = VALID_REQUEST.replace('data-ask-role="user"', 'data-ask-role="あなた"')
        self.assertTrue(validate_ask_blocks(markup))

    def test_hypothesis_needs_certainty_and_verify(self):
        markup = VALID_HYPOTHESIS.replace('<span class="certainty inferred">推論</span>', "")
        self.assertTrue(validate_ask_blocks(markup))
        markup2 = VALID_HYPOTHESIS.replace('class="ask-verify"', 'class="other"')
        self.assertTrue(validate_ask_blocks(markup2))

    def test_content_without_ask_is_ignored(self):
        self.assertEqual(validate_ask_blocks("<p>ふつうの本文</p>"), [])

    def test_empty_question_fails(self):
        markup = VALID_DECISION.replace("注釈を今回に含めますか？", "")
        self.assertTrue(validate_ask_blocks(markup))

    def test_option_without_tradeoff_fails(self):
        markup = VALID_DECISION.replace('<span class="ask-tradeoff">変更量が増える</span>', "")
        self.assertTrue(validate_ask_blocks(markup))

    def test_unknown_certainty_class_fails(self):
        markup = VALID_HYPOTHESIS.replace("certainty inferred", "certainty nonsense")
        self.assertTrue(validate_ask_blocks(markup))

    def test_certainty_outside_claim_fails(self):
        markup = VALID_HYPOTHESIS.replace(' <span class="certainty inferred">推論</span></p>', "</p>")
        markup = markup.replace('<p class="ask-verify">', '<span class="certainty inferred">推論</span><p class="ask-verify">')
        self.assertTrue(validate_ask_blocks(markup))

    def test_empty_request_step_fails(self):
        markup = VALID_REQUEST.replace("specをレビューする", "")
        self.assertTrue(validate_ask_blocks(markup))


if __name__ == "__main__":
    unittest.main()
