"""回収パネル（decision-panel）: closing 後挿入・静的サマリー・digest 埋め込み。"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from build_explainer import build_document
from ve_components.diagnostics import ContractError
from ve_components.document_sections import compute_ask_digest, render_decision_panel
from ve_components.model import AskOption, AskSection, AskStep, DocumentMetadata
from ve_components.registry import load_registry
from ve_components.renderers import TRUSTED_RENDERERS
from ve_components.validation import validate_assembly

SKILL_DIR = Path(__file__).resolve().parents[2]
SKELETON = (SKILL_DIR / "assets" / "skeleton.html").read_text("utf-8")
COMPONENTS_DIR = SKILL_DIR / "assets" / "components"
REGISTRY = load_registry(COMPONENTS_DIR / "registry.json")
BUILD = SKILL_DIR / "scripts" / "build_explainer.py"

_DOC = DocumentMetadata(id="doc-1", title="料金改定は限定対象で段階公開する",
                        summary="要約文。", type="proposal", profile="strict")

_DECISION_ASK = AskSection(
    id="ask-1", ask_type="decision", question="どちらにしますか。",
    options=(AskOption("opt-a", "案A", "早いが粗い"), AskOption("opt-b", "案B", "遅いが確実")),
    default_id="opt-b",
)

_REQUEST_ASK = AskSection(
    id="ask-2", ask_type="request",
    steps=(AskStep("user", "あなた", "確認する"),),
)


def _assembly(*, decision_ask: bool) -> dict:
    sections = [{"kind": "first-screen", "id": "sec-first", "decision": "決めます。"}]
    if decision_ask:
        sections.append({
            "kind": "ask",
            "id": "sec-ask-decision",
            "askType": "decision",
            "question": "どちらにしますか。",
            "options": [
                {"id": "opt-a", "label": "案A", "tradeoff": "早いが粗い"},
                {"id": "opt-b", "label": "案B", "tradeoff": "遅いが確実"},
            ],
            "defaultId": "opt-b",
        })
    sections.append({
        "kind": "closing",
        "id": "sec-closing",
        "blocks": [
            {"heading": "リスクと弱い前提", "items": ["前提Aが弱い"]},
            {"heading": "不確かな点", "items": ["未確認の利用状況"]},
        ],
    })
    return {
        "schemaVersion": 1,
        "document": {
            "id": "doc-1",
            "title": "料金改定は限定対象で段階公開する",
            "summary": "要約文。",
            "type": "proposal",
            "profile": "strict",
        },
        "sections": sections,
    }


class RenderDecisionPanelTest(unittest.TestCase):
    def test_renders_panel_for_one_decision_ask(self) -> None:
        panel = render_decision_panel((_DECISION_ASK,), _DOC, 1, "examples/demo.html")
        self.assertIsNotNone(panel)
        self.assertIn('data-ve-section-kind="decision-panel"', panel.markup)
        self.assertIn('data-ve-document-id="doc-1"', panel.markup)
        self.assertIn('data-ve-schema-version="1"', panel.markup)
        self.assertIn(f'data-ve-ask-digest="{compute_ask_digest((_DECISION_ASK,))}"', panel.markup)
        self.assertIn('data-ve-document-path="examples/demo.html"', panel.markup)
        self.assertIn('id="sec-decision-panel"', panel.markup)
        self.assertIn('class="decision-panel"', panel.markup)
        self.assertIn('aria-label="判断の回収"', panel.markup)
        self.assertIn("<h2>判断の回収</h2>", panel.markup)
        self.assertIn('data-ve-panel-ask="ask-1"', panel.markup)
        self.assertIn('class="panel-question"', panel.markup)
        self.assertIn("どちらにしますか。", panel.markup)
        self.assertIn('data-ve-panel-status', panel.markup)
        self.assertIn("未選択（既定案: 案B）", panel.markup)
        self.assertIn('data-ve-panel-memo hidden', panel.markup)
        self.assertIn('<textarea data-ve-panel-global-memo></textarea>', panel.markup)

    def test_status_reports_no_default_when_absent(self) -> None:
        ask = AskSection(
            id="ask-nd", ask_type="decision", question="どちらにしますか。",
            options=(AskOption("a", "案A", "t"), AskOption("b", "案B", "t")),
            no_default_reason="判断材料が拮抗しているため",
        )
        panel = render_decision_panel((ask,), _DOC, 1, "out.html")
        self.assertIsNotNone(panel)
        self.assertIn("未選択（既定案なし）", panel.markup)

    def test_returns_none_for_zero_decision_asks(self) -> None:
        self.assertIsNone(render_decision_panel((), _DOC, 1, "out.html"))
        self.assertIsNone(render_decision_panel((_REQUEST_ASK,), _DOC, 1, "out.html"))

    def test_avoids_occupied_instance_id(self) -> None:
        panel = render_decision_panel(
            (_DECISION_ASK,), _DOC, 1, "out.html",
            occupied_ids=frozenset({"sec-decision-panel"}),
        )
        self.assertIsNotNone(panel)
        self.assertNotEqual(panel.instance_id, "sec-decision-panel")
        self.assertTrue(panel.instance_id.startswith("sec-decision-panel"))

    def test_escapes_html_in_question_and_labels(self) -> None:
        ask = AskSection(
            id="ask-x", ask_type="decision", question="<script>alert(1)</script>",
            options=(AskOption("a", "<b>A</b>", "t"), AskOption("b", "B", "t")),
            default_id="a",
        )
        panel = render_decision_panel((ask,), _DOC, 1, "out.html")
        self.assertIn("&lt;script&gt;", panel.markup)
        self.assertIn("&lt;b&gt;A&lt;/b&gt;", panel.markup)
        self.assertNotIn("<script>alert", panel.markup)


class BuildDocumentDecisionPanelTest(unittest.TestCase):
    def test_panel_inserted_after_closing_when_decision_ask_present(self) -> None:
        doc = build_document(
            _assembly(decision_ask=True), REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS_DIR,
            document_path="examples/demo.html",
        )
        i_closing = doc.index('data-ve-section-kind="closing"')
        i_panel = doc.index('data-ve-section-kind="decision-panel"')
        self.assertLess(i_closing, i_panel)
        self.assertIn('data-ve-document-path="examples/demo.html"', doc)
        self.assertIn('data-ve-document-id="doc-1"', doc)

    def test_no_panel_when_no_decision_ask(self) -> None:
        doc = build_document(
            _assembly(decision_ask=False), REGISTRY, TRUSTED_RENDERERS, SKELETON, COMPONENTS_DIR,
            document_path="out.html",
        )
        # The skeleton's fixed decision-collection JS embeds this attribute string
        # inside a querySelector call regardless of panel presence (Task 5), so the
        # section-tag assertion checks the opening tag rather than a bare substring.
        self.assertNotIn('<section data-ve-section-kind="decision-panel"', doc)


class BuildCliDocumentPathTest(unittest.TestCase):
    def test_cli_embeds_relative_output_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            assembly_path = tmp / "assembly.json"
            import json
            assembly_path.write_text(json.dumps(_assembly(decision_ask=True)), "utf-8")
            proc = subprocess.run(
                ["python3", str(BUILD), "--assembly", "assembly.json", "--output", "out/demo.html"],
                cwd=str(tmp), capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            html = (tmp / "out" / "demo.html").read_text("utf-8")
            self.assertIn('data-ve-document-path="out/demo.html"', html)


class NarrativeRejectsDecisionPanelClassTest(unittest.TestCase):
    def test_narrative_with_decision_panel_class_rejected(self) -> None:
        raw = {
            "schemaVersion": 1,
            "document": {
                "id": "d", "title": "t", "summary": "s",
                "type": "proposal", "profile": "strict",
            },
            "sections": [
                {"kind": "first-screen", "id": "sec-first", "decision": "決めます。"},
                {
                    "kind": "narrative",
                    "id": "sec-fake-panel",
                    "markup": '<div class="decision-panel"><p>偽装</p></div>',
                },
                {
                    "kind": "closing",
                    "id": "sec-closing",
                    "blocks": [
                        {"heading": "リスクと弱い前提", "items": ["前提Aが弱い"]},
                        {"heading": "不確かな点", "items": ["未確認の利用状況"]},
                    ],
                },
            ],
        }
        with self.assertRaises(ContractError) as ctx:
            validate_assembly(raw)
        messages = " ".join(str(d) for d in ctx.exception.diagnostics)
        self.assertIn("narrative に予約 class decision-panel は置けません", messages)


if __name__ == "__main__":
    unittest.main()
