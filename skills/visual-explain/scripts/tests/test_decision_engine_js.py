"""回収エンジン純関数の検証（node 標準のみ・npm 依存なし。spec 逸脱の Playwright 代替）。"""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

NODE = shutil.which("node")
RUNTIME = Path(__file__).resolve().parent / "runtime"
DRIVER = RUNTIME / "decision_engine_driver.js"

CONTRACT = {
    "documentId": "doc-1", "schemaVersion": 1, "digest": "0123456789abcdef",
    "title": "料金改定は限定対象で段階公開する",
    "documentPath": "examples/demo.html",
    "riskHeadings": ["リスクと弱い前提", "不確かな点"],
    "asks": [
        {"id": "ask-1", "question": "対象範囲をどちらにしますか。", "defaultId": "opt-b",
         "options": [{"id": "opt-a", "label": "案A", "tradeoff": "早いが粗い"},
                     {"id": "opt-b", "label": "案B", "tradeoff": "遅いが確実"}]},
        {"id": "ask-2", "question": "開始時期はいつにしますか。", "defaultId": None,
         "options": [{"id": "opt-c", "label": "今月", "tradeoff": "準備が薄い"},
                     {"id": "opt-d", "label": "来月", "tradeoff": "機会損失"}]},
    ],
}

HEADER = [
    "[visual-explain 判断結果]",
    "資料: 料金改定は限定対象で段階公開する",
    "(examples/demo.html / id: doc-1 / schema: 1 / asks: 0123456789abcdef)",
]


def run_calls(calls: list[dict]) -> list:
    proc = subprocess.run([NODE, str(DRIVER)], input=json.dumps(calls).encode("utf-8"),
                          capture_output=True, timeout=30)
    assert proc.returncode == 0, proc.stderr.decode("utf-8")
    return json.loads(proc.stdout)


@unittest.skipUnless(NODE, "node が無い環境ではスキップ（Task 9 の完了ゲートでは非スキップ実行が必須）")
class DecisionEngineJsTest(unittest.TestCase):
    def test_storage_key_format(self) -> None:
        (key,) = run_calls([{"fn": "storageKey", "args": [CONTRACT]}])
        self.assertEqual(key, "ve-decision:doc-1:1:0123456789abcdef")

    def test_select_change_serialize_restore_roundtrip(self) -> None:
        results = run_calls([
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-a", CONTRACT], "assign": True},
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-b", CONTRACT], "assign": True},
            {"fn": "serializeState", "args": ["$state"]},
        ])
        (restored,) = run_calls([{"fn": "restoreState", "args": [results[-1], CONTRACT]}])
        self.assertEqual(restored["selections"], {"ask-1": "opt-b"})

    def test_restore_drops_unknown_ask_and_option(self) -> None:
        stale = json.dumps({"selections": {"ask-1": "opt-z", "ask-9": "opt-a"},
                            "memos": {"ask-9": "古いメモ"}, "globalMemo": "残す"})
        (restored,) = run_calls([{"fn": "restoreState", "args": [stale, CONTRACT]}])
        self.assertEqual(restored["selections"], {})
        self.assertEqual(restored["memos"], {})
        self.assertEqual(restored["globalMemo"], "残す")

    def test_restore_tolerates_broken_input(self) -> None:
        empty = {"selections": {}, "memos": {}, "globalMemo": ""}
        for raw in [None, "not json", "[]", "42"]:
            (restored,) = run_calls([{"fn": "restoreState", "args": [raw, CONTRACT]}])
            self.assertEqual(restored, empty)

    def test_select_option_ignores_unknown_option(self) -> None:
        (state,) = run_calls([{"fn": "selectOption", "args": ["$state", "ask-1", "opt-z", CONTRACT]}])
        self.assertEqual(state["selections"], {})

    def test_copy_text_full_selection_exact(self) -> None:
        calls = [
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-a", CONTRACT], "assign": True},
            {"fn": "selectOption", "args": ["$state", "ask-2", "opt-c", CONTRACT], "assign": True},
            {"fn": "setMemo", "args": ["$state", "ask-1", "撤回条件を先に固める"], "assign": True},
            {"fn": "setGlobalMemo", "args": ["$state", "全体の所感"], "assign": True},
            {"fn": "formatCopyText", "args": [CONTRACT, "$state"]},
        ]
        expected = "\n".join(HEADER + [
            "問い: 対象範囲をどちらにしますか。",
            "→ 選択: 案A（既定案から変更） — トレードオフ: 早いが粗い",
            "→ メモ: 撤回条件を先に固める",
            "問い: 開始時期はいつにしますか。",
            "→ 選択: 今月（既定案なし） — トレードオフ: 準備が薄い",
            "リスク要約: リスクと弱い前提 / 不確かな点",
            "全体メモ: 全体の所感",
        ])
        self.assertEqual(run_calls(calls)[-1], expected)

    def test_copy_text_preserves_memo_of_unselected_ask(self) -> None:
        # r1 C3: 未選択の ask もメモを欠落させない（spec 21 行目「各 ask の問い→選択→メモ」）
        calls = [
            {"fn": "setMemo", "args": ["$state", "ask-2", "まだ迷っている"], "assign": True},
            {"fn": "formatCopyText", "args": [CONTRACT, "$state"]},
        ]
        expected = "\n".join(HEADER + [
            "問い: 対象範囲をどちらにしますか。",
            "→ 選択: 未選択（既定案: 案B）",
            "問い: 開始時期はいつにしますか。",
            "→ 選択: 未選択（既定案: なし）",
            "→ メモ: まだ迷っている",
            "未選択: 対象範囲をどちらにしますか。（既定案: 案B） / 開始時期はいつにしますか。（既定案: なし）",
            "リスク要約: リスクと弱い前提 / 不確かな点",
        ])
        self.assertEqual(run_calls(calls)[-1], expected)

    def test_copy_text_keeps_multiline_japanese_memo_verbatim(self) -> None:
        memo = "一行目\r\n二行目：長文" + "あ" * 1200
        calls = [
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-b", CONTRACT], "assign": True},
            {"fn": "setMemo", "args": ["$state", "ask-1", memo], "assign": True},
            {"fn": "formatCopyText", "args": [CONTRACT, "$state"]},
        ]
        text = run_calls(calls)[-1]
        self.assertIn("→ メモ: " + memo, text)
        self.assertIn("→ 選択: 案B（既定案どおり） — トレードオフ: 遅いが確実", text)

    def test_blank_memo_emits_no_memo_line(self) -> None:
        calls = [
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-b", CONTRACT], "assign": True},
            {"fn": "setMemo", "args": ["$state", "ask-1", "  \n  "], "assign": True},
            {"fn": "formatCopyText", "args": [CONTRACT, "$state"]},
        ]
        self.assertNotIn("→ メモ:", run_calls(calls)[-1])

    def test_engine_sources_pass_node_check(self) -> None:
        for name in ("decision_engine.js", "decision_engine_driver.js"):
            proc = subprocess.run([NODE, "--check", str(RUNTIME / name)], capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))
