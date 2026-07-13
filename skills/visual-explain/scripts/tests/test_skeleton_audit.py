import re
import unittest
from pathlib import Path

SKELETON = (Path(__file__).resolve().parents[2] / "assets" / "skeleton.html").read_text("utf-8")
COMPONENT_CSS = [
    (Path(__file__).resolve().parents[2] / "assets" / "components" / name).read_text("utf-8")
    for name in ("matrix.css", "flow.css")
]

_HEX = re.compile(r"^#([0-9a-fA-F]{6})$")


def _luminance(hex_color):
    def channel(v):
        v = v / 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    m = _HEX.match(hex_color)
    r, g, b = (int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def tokens_of(block_text):
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", block_text))


def _blocks():
    light = SKELETON.split(":root {", 1)[1].split("}", 1)[0]
    dark = SKELETON.split(':root[data-theme="dark"]', 1)[1].split("}", 1)[0]
    return {"light": tokens_of(light), "dark": tokens_of(dark)}


def mix(fg_hex, bg_hex, percent):
    """color-mix(in srgb, fg P%, bg) の sRGB 近似（チャネル線形補間）。"""
    m_f = _HEX.match(fg_hex); m_b = _HEX.match(bg_hex)
    f = [int(m_f.group(1)[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(m_b.group(1)[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(fv * percent + bv * (1 - percent)):02x}" for fv, bv in zip(f, b))


# CSS で実際に使う前景/背景の対応表を網羅する。
# (前景トークン, 背景, 最低比, 用途)。背景が ("mix", 色, 面, 比率) のときは color-mix 後の実背景。
PAIRS = [
    ("text", "bg", 4.5, "本文/ページ背景"),
    ("text", "surface", 4.5, "本文/面"),
    ("text-dim", "bg", 4.5, "補助本文/ページ背景"),
    ("text-dim", "surface", 4.5, "補助本文/面"),
    ("text-faint", "bg", 4.5, "メタ情報(13px)/ページ背景"),
    ("text-faint", "surface", 4.5, "メタ情報(13px)/面"),
    ("accent", "bg", 4.5, "選択/背景"),
    ("accent", "surface", 4.5, "選択/面"),
    ("accent-strong", "bg", 4.5, "選択強/背景"),
    ("accent-strong", ("mix", "accent", "surface", 0.12), 4.5, "選択チップ文字/淡青面"),
    ("positive", "bg", 4.5, "推奨/背景"),
    ("positive", ("mix", "positive", "surface", 0.12), 4.5, "既定案マーク/淡緑面"),
    ("positive-strong", "bg", 4.5, "推奨強/背景"),
    ("warning", "bg", 4.5, "警告/背景"),
    ("warning", ("mix", "warning", "surface", 0.12), 4.5, "警告文字/淡橙面"),
    ("warning-strong", "bg", 4.5, "警告強/背景"),
    ("text", ("mix", "text", "surface", 0.08), 4.5, "takeaway対象セル内の本文"),
    ("border-strong", "bg", 3.0, "表見出し罫線(非文字)"),
    ("focus", "bg", 3.0, "フォーカスリング(非文字)"),
    ("text-dim", "surface", 3.0, "確度バッジ枠線(非文字)"),
]


def _resolve_bg(tokens, bg):
    if isinstance(bg, tuple):
        _, fg_token, base_token, percent = bg
        return mix(tokens[fg_token], tokens[base_token], percent)
    return tokens[bg]


class ContrastAuditTest(unittest.TestCase):
    def test_all_token_pairs_meet_wcag(self):
        for theme, tokens in _blocks().items():
            for fg, bg, minimum, purpose in PAIRS:
                with self.subTest(theme=theme, pair=f"{fg}/{bg}"):
                    self.assertIn(fg, tokens, f"{theme} に --{fg} がありません")
                    ratio = contrast(tokens[fg], _resolve_bg(tokens, bg))
                    self.assertGreaterEqual(ratio, minimum, f"{theme} {purpose}: {ratio:.2f} < {minimum}")


_SPACING_PROP = re.compile(
    r"(?:^|[;{])\s*(margin|padding|gap|margin-[a-z]+|padding-[a-z]+|margin-block|margin-inline|padding-inline|padding-block|row-gap|column-gap)\s*:\s*([^;}]+)", re.M)
_ALLOWED_VALUE = re.compile(
    r"^(0|var\(--space-[1-7]\)|auto|inherit)$")
# 二層幅の張り出し（design spec 2026-07-13）だけを 8px グリッド監査の明示的例外とする。
_BREAKOUT_MARGIN = "calc(-1 * min(10rem, (100vw - 60rem) / 2))"


class SpacingGridAuditTest(unittest.TestCase):
    def _audit(self, css, label):
        violations = []
        for prop, value in _SPACING_PROP.findall(css):
            value = value.strip()
            if prop == "margin-inline" and value == _BREAKOUT_MARGIN:
                continue
            for part in value.split():
                if not _ALLOWED_VALUE.match(part.strip()):
                    violations.append(f"{label}: {prop}: {value}")
                    break
        return violations

    def test_skeleton_spacing_on_grid(self):
        style = SKELETON.split("<style>", 1)[1].split("</style>", 1)[0]
        self.assertEqual(self._audit(style, "skeleton"), [])

    def test_component_css_spacing_on_grid(self):
        violations = []
        for css, label in zip(COMPONENT_CSS, ("matrix.css", "flow.css")):
            violations.extend(self._audit(css, label))
        self.assertEqual(violations, [])


class TypeScaleTest(unittest.TestCase):
    def test_five_step_scale_tokens_exist(self):
        for token in ("--fs-hero: 1.875rem", "--fs-h2: 1.25rem", "--fs-body: 1rem", "--fs-small: .8125rem", "--fs-figure: .875rem"):
            self.assertIn(token, SKELETON)


class ColorDisciplineAuditTest(unittest.TestCase):
    def test_component_css_is_monochrome(self):
        # 意味色トークンと生 hex は component CSS に現れない（色は判断状態専用で、
        # skeleton の data-tone / ask 規則だけが意味色を持てる）
        for css, label in zip(COMPONENT_CSS, ("matrix.css", "flow.css")):
            for token in ("--accent", "--positive", "--warning"):
                self.assertNotIn(token, css, f"{label} が意味色 {token} を参照しています")
            self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b", f"{label} に生の色指定があります")

    def test_semantic_colors_only_on_judgment_selectors(self):
        style = SKELETON.split("<style>", 1)[1].split("</style>", 1)[0]
        # 意味色を参照してよいセレクタ行の allowlist を検査する。
        # 各エントリは実在するルールにのみ対応させ、判断状態としての意味を明記する
        # （マッチしない項目は監査の抜け穴になるため置かない）。
        allowed = (
            # matrix/option-card の data-tone 属性: accent=選択, positive=推奨, warning=注意
            "data-tone",
            # ask ブロックの decision kind バッジと既定案マーカー（選択=accent, 既定案=positive）
            ".ask",
            # decision ask 内の強調文字（選択の強調 = accent-strong）
            ".decision",
            # 文書全体のリンク色（accent-strong = 選択・現在地の強調というリンクのアフォーダンス）
            "a ",
            # ステッパーの現在地インジケータ（accent = 現在地の強調、design-system.md の定義に合致）
            ".step-panel.is-current",
            # 接続線を描画できないときに JS が挿入する警告メッセージ（warning = 注意の意味）
            ".connector-warning",
        )
        for rule in style.split("}"):
            if "{" not in rule:
                continue
            selector, body = rule.rsplit("{", 1)
            if any(t in body for t in ("--accent", "--positive", "--warning")) \
                    and "--accent:" not in body and "--positive:" not in body and "--warning:" not in body:
                self.assertTrue(any(a in selector for a in allowed),
                                f"意味色が判断状態以外のセレクタに使われています: {selector.strip()[:80]}")


class ResponsiveLayoutTest(unittest.TestCase):
    """design spec 2026-07-13: 流体ルートスケールと二層幅の骨格規則を固定する。"""

    def test_fluid_root_type_scale(self):
        self.assertIn(
            "html { background: var(--bg); color: var(--text); "
            "font-size: clamp(1rem, 0.7rem + 0.5vw, 1.25rem); }",
            SKELETON)

    def test_two_tier_breakout_rules(self):
        gate = SKELETON.split("@media (min-width: 60rem) {", 1)
        self.assertEqual(len(gate), 2, "60rem の media gate がありません")
        block = gate[1].split("}\n\n", 1)[0]
        self.assertIn(
            ".figure:has(.flow, .matrix) { margin-inline: "
            "calc(-1 * min(10rem, (100vw - 60rem) / 2)); }",
            block)
        self.assertIn(
            'figure[data-ve-component="matrix"] .ve-matrix-scroll { margin-inline: '
            "calc(-1 * min(10rem, (100vw - 60rem) / 2)); max-width: none; }",
            block)
        self.assertIn(
            '.figure .matrix table, figure[data-ve-component="matrix"] table '
            "{ width: auto; margin-inline: auto; }",
            block)
        # 張り出しの適格列挙は2ルールで閉じる（値の再利用による黙った拡張を拒否する）
        self.assertEqual(SKELETON.count(_BREAKOUT_MARGIN), 2)

    def test_ask_options_stack_on_mobile(self):
        mobile = SKELETON.split("@media (max-width: 42rem) {", 1)[1]
        self.assertIn(
            ".ask-options [data-ask-option] { grid-template-columns: 1fr; "
            "gap: var(--space-1); }",
            mobile)


if __name__ == "__main__":
    unittest.main()
