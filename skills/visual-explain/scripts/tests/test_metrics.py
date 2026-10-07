from __future__ import annotations

import unittest

from ve_components.metrics import TextMetrics, format_metrics, text_metrics

DOC = (
    "<html><body><!-- VE-CONTROLLED:CONTENT:BEGIN -->"
    '<section data-ve-section-kind="first-screen"><h1>題名です</h1></section>'
    '<section data-ve-section-kind="canonical"><p>図の中</p></section>'
    '<section data-ve-section-kind="narrative"><p>本文 です。</p></section>'
    '<section data-ve-section-kind="decision-panel"><p>回収パネルは数えない</p></section>'
    "<!-- VE-CONTROLLED:CONTENT:END --></body></html>"
)


class MetricsTest(unittest.TestCase):
    def test_counts(self) -> None:
        self.assertEqual(text_metrics(DOC), TextMetrics(body_chars=4 + 3 + 5, chars_before_figure=4, figures=1))

    def test_format(self) -> None:
        self.assertEqual(format_metrics(TextMetrics(1400, 80, 3)), "本文 1400 字 / 図より前 80 字 / 図 3 点")


if __name__ == "__main__":
    unittest.main()
