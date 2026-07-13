"""Integration fixtures under .visual-explain/ must keep agent-specific content on the new skeleton."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
VISUAL_EXPLAIN = REPO_ROOT / ".visual-explain"

EXPECTED_TITLES = {
    "fixture-claude-proposal.html": "ctx 自己修復ラッパーの承認",
    "fixture-pi-proposal.html": "agent-stack ctx 自己修復ラッパーの提案",
    "fixture-claude-system.html": "agent-stack の Nix 配線の仕組み",
    "fixture-pi-system.html": "agent-stack Nix wiring の仕組み",
    "fixture-claude-research.html": "visual-explain 設計調査の発見",
    "fixture-pi-research.html": "visual-explain 設計原則の調査",
}


class VisualExplainAgentFixtureTest(unittest.TestCase):
    def test_agent_fixtures_use_expected_titles_not_valid_stubs(self) -> None:
        for name, title in EXPECTED_TITLES.items():
            with self.subTest(fixture=name):
                text = (VISUAL_EXPLAIN / name).read_text("utf-8")
                self.assertIn(f"<title>{title}</title>", text)
                self.assertNotIn("有効な提案フィクスチャ", text)
                self.assertNotIn("有効な仕組みフィクスチャ", text)
                self.assertNotIn("有効な調査フィクスチャ", text)

    def test_agent_fixtures_use_new_skeleton_not_72rem(self) -> None:
        for name in EXPECTED_TITLES:
            with self.subTest(fixture=name):
                text = (VISUAL_EXPLAIN / name).read_text("utf-8")
                self.assertNotIn("72rem", text)
                self.assertIn("--w-narrative", text)

    def test_claude_and_pi_proposal_fixtures_differ(self) -> None:
        claude = (VISUAL_EXPLAIN / "fixture-claude-proposal.html").read_text("utf-8")
        pi = (VISUAL_EXPLAIN / "fixture-pi-proposal.html").read_text("utf-8")
        claude_title = re.search(r"<title>([^<]+)</title>", claude)
        pi_title = re.search(r"<title>([^<]+)</title>", pi)
        self.assertIsNotNone(claude_title)
        self.assertIsNotNone(pi_title)
        self.assertNotEqual(claude_title.group(1), pi_title.group(1))
