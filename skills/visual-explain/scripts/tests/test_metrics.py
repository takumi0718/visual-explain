from __future__ import annotations

import unittest

from ve_components.metrics import TextMetrics, format_metrics, text_metrics, visible_chars

DOC = (
    "<html><body><!-- VE-CONTROLLED:CONTENT:BEGIN -->"
    '<section data-ve-section-kind="first-screen"><h1>題名です</h1></section>'
    '<section data-ve-section-kind="narrative"><p>前置き<br/>です</p></section>'
    '<section data-ve-section-kind="canonical"><p>図の中</p></section>'
    '<section data-ve-section-kind="narrative"><p>本文 です。</p></section>'
    '<section data-ve-section-kind="decision-panel"><p>回収<br/><br/>パネルは数えない</p></section>'
    "<!-- VE-CONTROLLED:CONTENT:END --></body></html>"
)


class MetricsTest(unittest.TestCase):
    def test_counts(self) -> None:
        # h1 counts toward the body but not toward "before the first figure".
        self.assertEqual(text_metrics(DOC),
                         TextMetrics(body_chars=4 + 5 + 3 + 5, chars_before_figure=5, figures=1))

    def test_self_closing_void_tags_do_not_pop_the_parent(self) -> None:
        self.assertEqual(visible_chars("<p>a b<br/>c<br/></p><p>d</p>"), 4)

    def test_screen_reader_only_text_is_not_counted(self) -> None:
        markup = '<p>見える</p><ul class="ve-gd-relations visually-hidden"><li>読み上げ</li></ul>'
        self.assertEqual(visible_chars(markup), 3)

    def test_format(self) -> None:
        self.assertEqual(format_metrics(TextMetrics(1400, 80, 3)), "本文 1400 字 / 図より前 80 字 / 図 3 点")


if __name__ == "__main__":
    unittest.main()
