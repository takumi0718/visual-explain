import re
import unittest
from pathlib import Path

SKELETON = (Path(__file__).resolve().parents[2] / "assets" / "skeleton.html").read_text("utf-8")
COMPONENT_CSS = [
    (Path(__file__).resolve().parents[2] / "assets" / "components" / name).read_text("utf-8")
    for name in ("matrix.css", "flow.css")
]

def _style():
    return SKELETON.split("<style>", 1)[1].split("</style>", 1)[0]


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
    ("accent-strong", "surface", 4.5, "指摘の番号札/面"),
    ("bg", "accent", 4.5, "主ボタン文字/accent 面"),
    ("bg", "accent-strong", 4.5, "主ボタン文字/hover 面"),
    ("text-dim", ("mix", "text-dim", "surface", 0.12), 4.5, "要望・仮説チップ文字/淡灰面"),
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
    ("dg-on-primary", "dg-primary", 4.5, "図表プライマリ上の文字"),
    ("text", "dg-primary-light", 4.5, "図表ライト面の本文"),
    ("dg-negative", "#ffffff", 4.5, "図表ネガティブ/白背景"),
]


def _resolve_bg(tokens, bg):
    if isinstance(bg, str) and bg.startswith("#"):
        return bg
    if isinstance(bg, tuple):
        _, fg_token, base_token, percent = bg
        return mix(tokens[fg_token], tokens[base_token], percent)
    return tokens[bg]


DG_TOKENS = [
    "--dg-primary:", "--dg-primary-mid:", "--dg-primary-light:",
    "--dg-highlight:", "--dg-negative:", "--dg-neutral:",
    "--dg-line:", "--dg-emphasis:", "--dg-on-primary:", "--radius:",
]


class DiagramTokenTest(unittest.TestCase):
    def test_skeleton_defines_diagram_tokens_in_all_theme_blocks(self):
        for token in DG_TOKENS:
            self.assertGreaterEqual(SKELETON.count(token), 3, f"{token} は light / @media dark / [data-theme=dark] に必要")

    def test_skeleton_defines_dg_em_rule(self):
        self.assertIn(".dg-em", SKELETON)
        self.assertIn("var(--dg-emphasis)", SKELETON)


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
        for token in ("--fs-hero: 1.953rem", "--fs-h2: 1.563rem", "--fs-h3: 1.25rem", "--fs-body: 1rem",
                      "--fs-small: .8rem", "--fs-figure: .8rem"):
            self.assertIn(token, SKELETON)

    def test_headings_and_captions_use_the_scale(self):
        style = _style()
        self.assertIn("h1 { margin: 0; font-size: var(--fs-hero);", style)
        self.assertIn("h3 { font-size: var(--fs-h3); font-weight: 700; line-height: var(--lh-heading);", style)
        self.assertIn(".claim { margin-bottom: var(--space-2); font-size: var(--fs-h3); font-weight: 400; }", style)
        self.assertIn("[data-ve-section-kind] figure[data-ve-component] > figcaption[class] "
                      "{ font-size: var(--fs-h3); }", style)


class FirstScreenFoldTest(unittest.TestCase):
    """v4: h1, conclusion, overview figure and markers fit the first 900px at 1280px."""

    def test_sections_use_space_5(self):
        style = _style()
        self.assertIn("section { min-width: 0; margin-block: var(--space-5); }", style)
        self.assertNotIn("var(--space-7)", style)

    def test_no_leading_whitespace_above_h1(self):
        style = _style()
        self.assertIn("main { width: min(100% - var(--space-4), var(--w-narrative)); margin: 0 auto; "
                      "padding: var(--space-2) 0 var(--space-6); }", style)
        self.assertIn('[data-ve-section-kind="first-screen"] { margin-block: 0 var(--space-3); }', style)
        self.assertIn(".first-screen { display: grid; gap: var(--space-2); padding: 0; margin-block: 0;", style)

    def test_overview_figure_hugs_its_markers(self):
        style = _style()
        self.assertIn('[data-ve-section-kind="canonical"]:has(+ [data-ve-section-kind="overview-nav"]) '
                      "{ margin-bottom: var(--space-2); }", style)
        self.assertIn(".overview-markers ol { list-style: none; margin: 0; padding: 0; display: flex; "
                      "flex-wrap: wrap; gap: var(--space-1) var(--space-3); }", style)

    def test_surface_is_only_under_the_overview_figure(self):
        style = _style()
        self.assertIn('[data-ve-section-kind="canonical"]:has(+ [data-ve-section-kind="overview-nav"]) > figure '
                      "{ margin-block: 0; padding: var(--space-3); background: var(--surface); "
                      "border-radius: var(--radius); }", style)
        for selector in (".ask {", ".decision-panel {", "details.deep-dive {", ".figure {"):
            rule = next(line for line in style.splitlines() if line.strip().startswith(selector))
            self.assertNotIn("var(--surface)", rule, selector)
            self.assertIn("1px solid var(--border)", rule, selector)

    def test_no_layout_rule_targets_main_by_name(self):
        # The visual-stage 1212px audit treats any selector naming main/html/body/:root
        # as main sizing; component overrides must use the [data-ve-section-kind] prefix.
        for chunk in _style().split("}"):
            if "{" not in chunk:
                continue
            selector = chunk.rsplit("{", 1)[0].split("{")[-1].strip()
            if selector in {"main", "html", "body", ":root", "*", "*, *::before, *::after"} \
                    or selector.startswith((":root", "@media")):
                continue
            self.assertIsNone(re.search(r"(?<![-\w])(main|html|body)(?![-\w])|:root", selector), selector)

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
            # first-screen の結論ブロック（accent = 結論という選択済み判断の強調）
            ".conclusion",
            # 概観ナビの番号マーカー（accent = 現在地を示す番号の強調）
            ".marker-n",
            # 指摘層の選択チップと番号札（accent = 読者が指した場所・選んだ種類の強調）
            ".review-tag",
            ".review-chip[aria-checked",
            # 指摘済みブロックの左縦線（accent = 読者が指した場所）
            "[data-ve-annotated]",
            # 主ボタン（accent = この資料で最初に押す操作。コピーだけに付ける）
            ".button-primary",
        )
        for rule in style.split("}"):
            if "{" not in rule:
                continue
            selector, body = rule.rsplit("{", 1)
            if any(t in body for t in ("--accent", "--positive", "--warning")) \
                    and "--accent:" not in body and "--positive:" not in body and "--warning:" not in body:
                self.assertTrue(any(a in selector for a in allowed),
                                f"意味色が判断状態以外のセレクタに使われています: {selector.strip()[:80]}")


class DecisionEngineEmbedTest(unittest.TestCase):
    def test_skeleton_embeds_engine_core_verbatim(self):
        core = (Path(__file__).resolve().parent / "runtime" / "decision_engine.js").read_text("utf-8")
        begin = "/* FIXED DECISION ENGINE CORE:BEGIN"
        end = "/* FIXED DECISION ENGINE CORE:END */"
        self.assertIn(begin, SKELETON)
        embedded = SKELETON.split(begin, 1)[1].split("*/", 1)[1].split(end, 1)[0]
        self.assertEqual(embedded.strip(), core.strip())

    def test_skeleton_has_decision_collection_block(self):
        self.assertIn("/* FIXED DECISION COLLECTION JS: DO NOT MODIFY. */", SKELETON)


class DecisionOptionCardInteractionTest(unittest.TestCase):
    """選択肢の枠全体を選択操作面にする改修。旧・個別「この案を選ぶ」ボタン方式を廃止する。"""

    def _collection_block(self):
        begin = "/* FIXED DECISION COLLECTION JS: DO NOT MODIFY. */"
        end = "</script>"
        return SKELETON.split(begin, 1)[1].split(end, 1)[0]

    def test_no_legacy_select_button_is_created(self):
        block = self._collection_block()
        self.assertNotIn("この案を選ぶ", block)
        self.assertNotIn("'data-ask-select'", block)
        self.assertNotIn("'ask-select'", block)

    def test_option_item_responds_to_enter_and_space(self):
        block = self._collection_block()
        self.assertIn("item.addEventListener('keydown'", block)
        self.assertIn("event.key !== 'Enter'", block)
        self.assertIn("event.key !== ' '", block)
        self.assertIn("event.preventDefault()", block)

    def test_option_item_is_a_radio(self):
        block = self._collection_block()
        self.assertIn("list.setAttribute('role', 'radiogroup')", block)
        self.assertIn("item.setAttribute('role', 'radio')", block)
        self.assertIn("item.setAttribute('tabindex', '0')", block)
        self.assertIn("item.addEventListener('click', select)", block)

    def test_aria_checked_syncs_on_the_item_itself(self):
        block = self._collection_block()
        self.assertIn("item.setAttribute('aria-checked', String(selected))", block)
        self.assertNotIn("aria-pressed", block)

    def test_withdrawn_option_is_not_interactive(self):
        self.assertIn("item.setAttribute('aria-disabled', 'true')", self._collection_block())

    def test_copy_button_label(self):
        self.assertIn("copyButton.textContent = '回答と指摘をコピー';", self._collection_block())

    def test_manual_copy_fallback_is_wired(self):
        block = self._collection_block()
        self.assertIn("fallback.hidden = false;", block)
        self.assertIn("クリップボードを使えないため、以下を手動でコピーしてください。", block)

    def test_option_focus_style_extends_to_the_option_card(self):
        style = SKELETON.split("<style>", 1)[1].split("</style>", 1)[0]
        self.assertIn(".ask-options [data-ask-option]:focus-visible", style)
        self.assertNotIn(".ask-select {", style)

    def test_selected_ring_never_competes_with_the_focus_ring(self):
        """``[data-ask-option]:focus-visible`` and
        ``[data-ask-option][data-ask-selected]`` share equal specificity
        (class + attribute + pseudo-class/attribute, 0-3-0 either way), so a
        card that is both selected and keyboard-focused would have only one
        of the two ``outline`` declarations survive the cascade — whichever
        is declared later wins, silently hiding the focus ring on an
        already-selected card. Pinning the selected rule to a different
        property (``box-shadow``, not ``outline``) makes both rings render
        at once regardless of source order or any future specificity
        change, instead of relying on a fragile tie-break.
        """
        style = SKELETON.split("<style>", 1)[1].split("</style>", 1)[0]
        selected_rule = re.search(
            r"\.ask-options \[data-ask-option\]\[data-ask-selected\] \{([^}]*)\}", style)
        self.assertIsNotNone(selected_rule, "selected 状態のルールが見つかりません")
        self.assertNotIn("outline", selected_rule.group(1))
        self.assertIn("box-shadow", selected_rule.group(1))
        focus_rule = re.search(
            r"\.ask-options \[data-ask-option\]:focus-visible \{([^}]*)\}", style)
        self.assertIsNotNone(focus_rule, "option card の focus-visible ルールが見つかりません")
        self.assertIn("outline", focus_rule.group(1))


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
            "{ width: min(var(--w-narrative), 100%); margin-inline: auto; }",
            block)
        # 張り出しの適格列挙は2ルールで閉じる（値の再利用による黙った拡張を拒否する）
        self.assertEqual(SKELETON.count(_BREAKOUT_MARGIN), 2)

    def test_component_css_must_not_fight_breakout(self):
        # component CSS は skeleton の後に注入され同点なら後勝ちするため、
        # 二層幅の張り出しが設定するプロパティ（scroll の max-width、table の
        # 幅キャップと中央寄せ）を弱い値で再宣言すると張り出しが壊れる。
        matrix_css = COMPONENT_CSS[0]
        scroll_rule = re.search(
            r'figure\[data-ve-component="matrix"\] \.ve-matrix-scroll \{([^}]*)\}',
            matrix_css).group(1)
        self.assertNotIn("max-width", scroll_rule)
        table_rule = re.search(
            r'figure\[data-ve-component="matrix"\] table \{([^}]*)\}',
            matrix_css).group(1)
        self.assertIn("width: min(var(--w-narrative), 100%)", table_rule)
        self.assertIn("margin-inline: auto", table_rule)

    def test_ask_options_stack_on_mobile(self):
        mobile = SKELETON.split("@media (max-width: 42rem) {", 1)[1]
        self.assertIn(
            ".ask-options [data-ask-option] { grid-template-columns: 1fr; "
            "gap: var(--space-1); }",
            mobile)


class ReviewLayerSkeletonTest(unittest.TestCase):
    """Review layer: add/pick buttons, the editor below a block and number tags are built by fixed JS."""

    _collection_block = DecisionOptionCardInteractionTest._collection_block

    def test_review_layer_hooks_exist(self):
        block = self._collection_block()
        for needle in (
            "block.setAttribute('tabindex', '0')",
            "if (event.target !== block || event.key !== 'Enter') return;",
            "chip.setAttribute('role', 'radio')",
            "chips.setAttribute('role', 'radiogroup')",
            "makeButton('review-add', '＋')",
            "makeButton('review-pick', '指摘')",
            "document.addEventListener('selectionchange'",
            "engine.addAnnotation(state, n, editor.chip, editor.quote, note.value, contract)",
            "      renderReview();\n",
            "if (event.key !== 'Enter' || event.isComposing || event.keyCode === 229) return;",
            "const target = left[at] || left[at - 1] || editor.root.querySelector('.review-chip');",
            "    const render = () => {\n      fallback.hidden = true;\n      copyStatus.textContent = '';\n",
            "if (block.tagName === 'LI') block.append(root);",
            "else block.after(root);",
        ):
            self.assertIn(needle, block)

    def test_annotated_block_uses_accent_line(self):
        style = SKELETON.split("<style>", 1)[1].split("</style>", 1)[0]
        self.assertIn(
            "[data-ve-blk][data-ve-annotated] { border-left: 3px solid var(--accent); "
            "padding-left: var(--space-1); }", style)
        self.assertIn(
            '.review-chip[aria-checked="true"] { border-color: var(--accent); color: var(--accent-strong); '
            "background: color-mix(in srgb, var(--accent) 12%, var(--surface)); }", style)


class ControlsV4Test(unittest.TestCase):
    _collection_block = DecisionOptionCardInteractionTest._collection_block

    def test_primary_and_secondary_buttons(self):
        style = _style()
        self.assertIn("button { font: inherit; color: inherit; background: transparent; "
                      "border: 1px solid var(--border); border-radius: var(--radius);", style)
        self.assertIn(".button-primary { background: var(--accent); border-color: var(--accent); "
                      "color: var(--bg); font-weight: 700; }", style)
        self.assertIn(".button-primary:hover:not(:disabled) { background: var(--accent-strong); "
                      "border-color: var(--accent-strong); }", style)
        self.assertIn("copyButton.className = 'button-primary';", self._collection_block())

    def test_option_hover_and_selected(self):
        style = _style()
        self.assertIn(".ask-options [data-ask-option]:not([data-ask-withdrawn]):not([data-ask-selected]):hover "
                      "{ border-color: var(--text-faint); }", style)
        self.assertIn(".ask-options [data-ask-option][data-ask-selected] { border-color: var(--accent); "
                      "box-shadow: inset 0 0 0 1px var(--accent);", style)

    def test_dead_no_default_reason_selector_removed(self):
        self.assertNotIn("ask-no-default-reason", _style())

    def test_js_only_note_hidden_after_init(self):
        self.assertIn("panel.querySelectorAll('.panel-note').forEach((note) => { note.hidden = true; });",
                      self._collection_block())

    def test_transitions_respect_reduced_motion(self):
        style = _style()
        self.assertEqual(style.count("transition:"), 1)
        gate = style.split("@media (prefers-reduced-motion: no-preference) {", 1)
        self.assertEqual(len(gate), 2)
        self.assertIn("transition: background-color 150ms ease, border-color 150ms ease, "
                      "color 150ms ease, box-shadow 150ms ease;", gate[1].split("\n    }", 1)[0])
        self.assertNotIn("infinite", style)

    def test_request_and_hypothesis_chips_have_visible_pill(self):
        style = _style()
        pill = "background: color-mix(in srgb, var(--text-dim) 12%, var(--surface)); }"
        self.assertIn('.ask[data-ask="request"] .ask-kind { color: var(--text-dim); ' + pill, style)
        self.assertIn('.ask[data-ask="hypothesis"] .ask-kind { color: var(--text-dim); ' + pill, style)


class ThemeToggleTest(unittest.TestCase):
    def _theme_js(self):
        return SKELETON.split("/* FIXED THEME CONTROL JS: DO NOT MODIFY. */", 1)[1].split("</script>", 1)[0]

    def test_icon_only_round_button(self):
        button = re.search(r"<button[^>]*data-theme-toggle[^>]*>(.*?)</button>", SKELETON, re.S)
        self.assertIsNotNone(button)
        tag = button.group(0).split(">", 1)[0]
        for attr in ('class="theme-toggle"', 'aria-label="テーマを切り替える"',
                     'title="テーマを切り替える"', 'aria-pressed="false"'):
            self.assertIn(attr, tag)
        inner = button.group(1)
        self.assertEqual(re.sub(r"<[^>]+>", "", inner).strip(), "")
        self.assertIn('class="theme-icon-sun"', inner)
        self.assertIn('class="theme-icon-moon"', inner)
        self.assertEqual(inner.count('aria-hidden="true"'), 2)
        self.assertNotIn("#", inner)
        style = _style()
        self.assertIn(".theme-toggle { display: inline-grid; place-items: center; width: 32px; height: 32px; "
                      "padding: 0; border-radius: 50%; color: var(--text-dim); }", style)
        self.assertIn('.theme-toggle[aria-pressed="true"] .theme-icon-sun, '
                      '.theme-toggle[aria-pressed="false"] .theme-icon-moon { display: none; }', style)

    def test_label_describes_state_and_action(self):
        js = self._theme_js()
        self.assertIn("const text = `テーマ: ${label(current)}（${label(next)}に切替）`;", js)
        self.assertIn("button.setAttribute('aria-label', text);", js)
        self.assertIn("button.setAttribute('title', text);", js)
        self.assertIn("button.setAttribute('aria-pressed', String(current === 'dark'));", js)
        self.assertNotIn("textContent", js)

    def test_two_states_only_and_storage_key_kept(self):
        self.assertIn('data-theme-storage-key="visual-explain-theme"', SKELETON)
        js = self._theme_js()
        self.assertIn("window.localStorage.setItem(root.dataset.themeStorageKey, theme);", js)
        self.assertNotIn("auto", js)
        self.assertNotIn("removeItem", js)


class MobileV4Test(unittest.TestCase):
    _collection_block = DecisionOptionCardInteractionTest._collection_block

    def _mobile(self):
        return _style().split("@media (max-width: 42rem) {", 1)[1]

    def test_sixteen_pixel_gutter(self):
        style = _style()
        self.assertIn("main { width: min(100% - var(--space-4), var(--w-narrative));", style)
        self.assertNotIn("100% - var(--space-2)", style)

    def test_dense_matrix_becomes_cards(self):
        mobile = self._mobile()
        prefix = '[data-ve-section-kind] figure[data-ve-component="matrix"] .ve-matrix-scroll'
        for needle in (
            f"{prefix} {{ overflow-x: visible; }}",
            f"{prefix} :is(table, tbody, tr, th, td) {{ display: block; width: auto; min-width: 0; }}",
            f"{prefix} tr {{ margin: 0 0 var(--space-2); padding: var(--space-2); "
            "border: 1px solid var(--border); border-radius: var(--radius); }",
            f"{prefix} td[data-ve-col-label]::before {{ content: attr(data-ve-col-label); display: block; "
            "color: var(--text-dim); font-size: var(--fs-small); font-weight: 700; }",
        ):
            self.assertIn(needle, mobile)

    def test_text_blocks_reserve_room_for_the_add_button(self):
        gate = _style().split("@media (max-width: 52rem) {", 1)
        self.assertEqual(len(gate), 2)
        self.assertIn("[data-ve-section-kind] :is(p, li, h2, h3, blockquote)[data-ve-blk] "
                      "{ padding-right: var(--space-4); }", gate[1].split("\n    }", 1)[0])

    def test_add_button_never_covers_text(self):
        block = self._collection_block()
        for needle in (
            "const place = (button, rect, below, block) => {",
            "if (block && /^(FIGURE|TABLE|PRE)$/.test(block.tagName)) top = rect.top - button.offsetHeight - 4;",
            "left = Math.max(0, Math.min(left, document.documentElement.clientWidth - width));",
            "place(addButton, block.getBoundingClientRect(), false, block);",
        ):
            self.assertIn(needle, block)


class ChevronV4Test(unittest.TestCase):
    def test_horizontal_steps_share_one_row_and_equal_heights(self):
        gate = _style().split("@media (width > 42rem) {", 1)
        self.assertEqual(len(gate), 2)
        block = gate[1].split("\n    }", 1)[0]
        prefix = '[data-ve-section-kind] figure[data-ve-component="chevron"] .ve-chevron-horizontal'
        for needle in (
            f"{prefix} {{ display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); "
            "grid-template-rows: auto auto auto; }",
            f"{prefix} .ve-chevron-step {{ display: grid; grid-row: span 3; grid-template-rows: subgrid; "
            "align-items: stretch; min-width: 0; max-width: none; }",
            f"{prefix} .ve-chv-box {{ align-content: center; }}",
            f"{prefix} .ve-chevron-description {{ padding-inline-end: var(--space-2); }}",
        ):
            self.assertIn(needle, block)
        self.assertNotIn("flex-wrap", block)


class NestedSectionMarginTest(unittest.TestCase):
    def test_outer_lanes_drop_the_section_margin(self):
        # Inner lanes keep the section margin: the fixed connector script picks
        # vertical anchors only when lanes sit farther apart than nodes do sideways.
        css = _style()
        self.assertIn(
            "[data-ve-section-kind] .layers > [data-lane]:first-child { margin-block-start: 0; }", css)
        self.assertIn(
            "[data-ve-section-kind] .layers > [data-lane]:last-child { margin-block-end: 0; }", css)

    def test_nested_sections_drop_the_section_margin(self):
        # The global `section { margin-block }` rule leaks into sections nested inside
        # content (Before/After frames). Inside a grid those margins do not collapse
        # and open ~100px bands; only direct children of a wrapper keep it.
        self.assertIn(
            "[data-ve-section-kind] section:not([data-ve-section-kind] > section, [data-lane]) "
            "{ margin-block: 0; }", _style())

class QuestionFormLayoutTest(unittest.TestCase):
    def test_memo_label_sits_above_a_full_width_textarea(self):
        css = _style()
        self.assertIn(".ask-memo label { display: grid; gap: var(--space-1); color: var(--text-dim); "
                      "font-size: var(--fs-small); font-weight: 700; }", css)
        rule = next(line for line in css.splitlines()
                    if line.strip().startswith(".ask-memo textarea, .decision-panel textarea {"))
        self.assertIn("width: 100%;", rule)
        self.assertIn("font-size: var(--fs-body); font-weight: 400;", rule)

    def test_copy_button_has_top_spacing(self):
        self.assertIn(".decision-panel > .button-primary { margin-top: var(--space-2); }", _style())

    def test_card_status_reads_as_a_state_line(self):
        # The default ("お任せ") is a state, not a third option: it is shown as a
        # dashed slot aligned with the option cards and turns solid once chosen.
        css = _style()
        self.assertIn(".ask-card-status { display: flex; flex-wrap: wrap; align-items: baseline; "
                      "gap: 0 var(--space-1); margin: var(--space-1) 0 0; padding: var(--space-1) var(--space-2); "
                      "border: 1px dashed var(--text-faint); border-radius: var(--radius);", css)
        self.assertIn('.ask-card-status::before { content: "いまの回答";', css)
        self.assertIn(".ask:has([data-ask-selected]) .ask-card-status { border-style: solid; color: var(--text); }", css)
        self.assertIn('.ask:has([data-ask-selected]) .ask-card-status::after '
                      '{ content: "選んだ案をもう一度押すとお任せに戻る";', css)

    def test_panel_rows_stack_question_and_status(self):
        css = _style()
        self.assertIn(".panel-asks { display: grid; gap: var(--space-2); margin: 0; padding: 0; list-style: none; }", css)
        self.assertIn(".panel-asks li { display: grid; gap: 0; }", css)
        self.assertIn(".panel-status { color: var(--text-dim); font-size: var(--fs-small); }", css)

class ClosingCardTest(unittest.TestCase):
    def test_closing_uses_the_shared_card_frame(self):
        css = _style()
        self.assertIn(".closing-section { padding: var(--space-3); background: var(--bg); "
                      "border: 1px solid var(--border); border-radius: var(--radius); }", css)
        self.assertNotIn("border-top: 1px solid var(--border-strong)", css)
        self.assertIn(".closing-section h2 { margin-top: 0; font-size: var(--fs-h2); }", css)

if __name__ == "__main__":
    unittest.main()
