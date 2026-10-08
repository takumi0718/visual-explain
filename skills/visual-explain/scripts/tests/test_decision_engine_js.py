"""回収エンジン純関数の検証（node 標準のみ・npm 依存なし）。"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

NODE = shutil.which("node")
RUNTIME = Path(__file__).resolve().parent / "runtime"
DRIVER = RUNTIME / "decision_engine_driver.js"
SKELETON = RUNTIME.parents[2] / "assets" / "skeleton.html"

CHIPS = ["わからない", "図にしてほしい", "もっと詳しく", "短くする", "削る", "言い換える", "事実を確認", "ここは良い"]
CLOSING = "上の回答を反映して作業を続けてください。お任せの項目は推奨案で確定してください。"

CONTRACT = {
    "documentId": "doc-1", "schemaVersion": 2, "digest": "0123456789abcdef",
    "title": "料金改定は限定対象で段階公開する", "documentPath": "examples/demo.html", "blockCount": 12,
    "asks": [
        {"id": "ask-1", "question": "対象範囲をどちらにしますか？", "defaultId": "opt-b",
         "options": [{"id": "opt-a", "label": "案A", "withdrawn": False},
                     {"id": "opt-b", "label": "案B", "withdrawn": False},
                     {"id": "opt-w", "label": "案W", "withdrawn": True}]},
        {"id": "ask-2", "question": "開始時期はいつにしますか？", "defaultId": "opt-c",
         "options": [{"id": "opt-c", "label": "今月", "withdrawn": False},
                     {"id": "opt-d", "label": "来月", "withdrawn": False}]},
    ],
}
HEADER = [
    "[visual-explain 回答]",
    "資料: 料金改定は限定対象で段階公開する",
    "(examples/demo.html / id: doc-1 / schema: 2 / asks: 0123456789abcdef)",
]
NO_ASKS = dict(CONTRACT, asks=[], digest="fedcba9876543210")
CONTRACT_PROTO = dict(CONTRACT, asks=[
    {"id": "__proto__", "question": "汚染に耐えますか？", "defaultId": "opt-p",
     "options": [{"id": "opt-p", "label": "はい", "withdrawn": False},
                 {"id": "opt-q", "label": "いいえ", "withdrawn": False}]}])
CONTRACT_DELIM = dict(CONTRACT, asks=[
    {"id": "ask,1", "question": "境界文字でも動きますか？", "defaultId": "opt=1",
     "options": [{"id": "opt=1", "label": "動く", "withdrawn": False},
                 {"id": "opt=2", "label": "動かない", "withdrawn": False}]}])


def run_calls(calls: list[dict]) -> list:
    proc = subprocess.run([NODE, str(DRIVER)], input=json.dumps(calls).encode("utf-8"),
                          capture_output=True, timeout=30)
    assert proc.returncode == 0, proc.stderr.decode("utf-8")
    return json.loads(proc.stdout)


@unittest.skipUnless(NODE, "node が無い環境ではスキップ（完了ゲートでは非スキップ実行が必須）")
class ReviewEngineJsTest(unittest.TestCase):
    def test_chips_are_the_eight_kinds_in_order(self) -> None:
        self.assertEqual(run_calls([{"fn": "CHIPS"}]), [CHIPS])

    def test_storage_key_tracks_digest_and_block_count(self) -> None:
        key, other = run_calls([{"fn": "storageKey", "args": [CONTRACT]},
                                {"fn": "storageKey", "args": [dict(CONTRACT, blockCount=13)]}])
        self.assertEqual(key, "ve-review:doc-1:2:0123456789abcdef:12")
        self.assertNotEqual(key, other)

    def test_selecting_twice_returns_to_omakase(self) -> None:
        once, twice = run_calls([
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-a", CONTRACT], "assign": True},
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-a", CONTRACT], "assign": True},
        ])
        self.assertEqual(once["selections"], {"ask-1": "opt-a"})
        self.assertEqual(twice["selections"], {})

    def test_withdrawn_option_cannot_be_selected_or_restored(self) -> None:
        (state,) = run_calls([{"fn": "selectOption", "args": ["$state", "ask-1", "opt-w", CONTRACT]}])
        self.assertEqual(state["selections"], {})
        raw = json.dumps({"selections": {"ask-1": "opt-w"}})
        (restored,) = run_calls([{"fn": "restoreState", "args": [raw, CONTRACT]}])
        self.assertEqual(restored["selections"], {})

    def test_restore_drops_stale_entries(self) -> None:
        raw = json.dumps({
            "selections": {"ask-1": "opt-z", "ask-9": "opt-a", "ask-2": "opt-d"},
            "memos": {"ask-9": "古い"}, "globalMemo": "残す",
            "annotations": [
                {"blk": 3, "chip": "削る", "quote": "q", "note": "n"},
                {"blk": 13, "chip": "削る", "quote": "", "note": ""},
                {"blk": 2, "chip": "その他", "quote": "", "note": ""},
                {"blk": "2", "chip": "削る", "quote": "", "note": ""},
                "broken",
            ],
        })
        (restored,) = run_calls([{"fn": "restoreState", "args": [raw, CONTRACT]}])
        self.assertEqual(restored["selections"], {"ask-2": "opt-d"})
        self.assertEqual(restored["memos"], {})
        self.assertEqual(restored["globalMemo"], "残す")
        self.assertEqual(restored["annotations"], [{"blk": 3, "chip": "削る", "quote": "q", "note": "n"}])

    def test_restore_tolerates_broken_input(self) -> None:
        empty = {"selections": {}, "memos": {}, "globalMemo": "", "annotations": []}
        for raw in [None, "not json", "[]", "42"]:
            (restored,) = run_calls([{"fn": "restoreState", "args": [raw, CONTRACT]}])
            self.assertEqual(restored, empty)

    def test_serialize_restore_roundtrip(self) -> None:
        results = run_calls([
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-a", CONTRACT], "assign": True},
            {"fn": "addAnnotation", "args": ["$state", 5, "短くする", "引用", "長い", CONTRACT], "assign": True},
            {"fn": "serializeState", "args": ["$state"]},
        ])
        (restored,) = run_calls([{"fn": "restoreState", "args": [results[-1], CONTRACT]}])
        self.assertEqual(restored["selections"], {"ask-1": "opt-a"})
        self.assertEqual(restored["annotations"], [{"blk": 5, "chip": "短くする", "quote": "引用", "note": "長い"}])

    def test_add_annotation_rejects_unknown_chip_and_out_of_range_block(self) -> None:
        a, b, c = run_calls([
            {"fn": "addAnnotation", "args": ["$state", 0, "削る", "", "", CONTRACT]},
            {"fn": "addAnnotation", "args": ["$state", 13, "削る", "", "", CONTRACT]},
            {"fn": "addAnnotation", "args": ["$state", 1, "その他", "", "", CONTRACT]},
        ])
        for state in (a, b, c):
            self.assertEqual(state["annotations"], [])

    def test_quote_is_normalized_to_40_code_points(self) -> None:
        emoji = "\U0001F600" * 41
        flat, long = run_calls([
            {"fn": "normalizeQuote", "args": ["  限定対象で\n\n段階  公開する  "]},
            {"fn": "normalizeQuote", "args": [emoji]},
        ])
        self.assertEqual(flat, "限定対象で 段階 公開する")
        self.assertEqual(long, "\U0001F600" * 40)

    def test_remove_annotation_and_annotations_for(self) -> None:
        results = run_calls([
            {"fn": "addAnnotation", "args": ["$state", 4, "削る", "", "", CONTRACT], "assign": True},
            {"fn": "addAnnotation", "args": ["$state", 4, "言い換える", "", "x", CONTRACT], "assign": True},
            {"fn": "addAnnotation", "args": ["$state", 7, "ここは良い", "", "", CONTRACT], "assign": True},
            {"fn": "annotationsFor", "args": ["$state", 4]},
            {"fn": "removeAnnotation", "args": ["$state", 0], "assign": True},
            {"fn": "removeAnnotation", "args": ["$state", 9]},
        ])
        self.assertEqual(results[3], [{"index": 0, "chip": "削る", "quote": "", "note": ""},
                                      {"index": 1, "chip": "言い換える", "quote": "", "note": "x"}])
        self.assertEqual([a["chip"] for a in results[4]["annotations"]], ["言い換える", "ここは良い"])
        self.assertEqual(results[5], results[4])

    def test_card_status(self) -> None:
        unselected, selected = run_calls([
            {"fn": "cardStatus", "args": [CONTRACT["asks"][0], "$state"]},
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-a", CONTRACT], "assign": True},
        ])
        (after,) = run_calls([{"fn": "cardStatus", "args": [CONTRACT["asks"][0], selected]}])
        self.assertEqual(unselected, "お任せ（推奨: 案B）")
        self.assertEqual(after, "選択: 案A")

    def test_next_chip_index(self) -> None:
        calls = [{"fn": "nextChipIndex", "args": args} for args in (
            [0, "ArrowRight", 8], [7, "ArrowRight", 8], [0, "ArrowLeft", 8], [3, "ArrowDown", 8],
            [3, "ArrowUp", 8], [3, "Home", 8], [3, "End", 8], [3, "a", 8])]
        self.assertEqual(run_calls(calls), [1, 0, 7, 4, 2, 0, 7, -1])

    def test_copy_text_full_format(self) -> None:
        calls = [
            {"fn": "selectOption", "args": ["$state", "ask-1", "opt-a", CONTRACT], "assign": True},
            {"fn": "setMemo", "args": ["$state", "ask-1", "  撤回条件を先に固める  "], "assign": True},
            {"fn": "setMemo", "args": ["$state", "ask-2", "   "], "assign": True},
            {"fn": "setGlobalMemo", "args": ["$state", "全体の所感"], "assign": True},
            {"fn": "addAnnotation", "args": ["$state", 12, "図にしてほしい", "  限定対象で\n段階公開する  ", "表にしてほしい", CONTRACT], "assign": True},
            {"fn": "addAnnotation", "args": ["$state", 3, "ここは良い", "", "", CONTRACT], "assign": True},
            {"fn": "formatCopyText", "args": [CONTRACT, "$state"]},
        ]
        expected = "\n".join(HEADER + [
            "Q1. 対象範囲をどちらにしますか？: 案A / 補足: 撤回条件を先に固める",
            "Q2. 開始時期はいつにしますか？: (未選択 = お任せ)",
            "全体メモ: 全体の所感",
            "## 指摘",
            "#3 [ここは良い]",
            "#12 [図にしてほしい] 「限定対象で 段階公開する」 表にしてほしい",
            "---",
            CLOSING,
        ])
        self.assertEqual(run_calls(calls)[-1], expected)

    def test_copy_text_minimal_has_no_empty_sections(self) -> None:
        (text,) = run_calls([{"fn": "formatCopyText", "args": [CONTRACT, "$state"]}])
        self.assertEqual(text, "\n".join(HEADER + [
            "Q1. 対象範囲をどちらにしますか？: (未選択 = お任せ)",
            "Q2. 開始時期はいつにしますか？: (未選択 = お任せ)",
            "---",
            CLOSING,
        ]))

    def test_copy_text_keeps_supplement_on_unselected_ask(self) -> None:
        calls = [
            {"fn": "setMemo", "args": ["$state", "ask-2", "一行目\n二行目"], "assign": True},
            {"fn": "formatCopyText", "args": [CONTRACT, "$state"]},
        ]
        self.assertIn("Q2. 開始時期はいつにしますか？: (未選択 = お任せ) / 補足: 一行目\n二行目",
                      run_calls(calls)[-1])

    def test_copy_text_without_asks_lists_only_annotations(self) -> None:
        calls = [
            {"fn": "addAnnotation", "args": ["$state", 1, "削る", "", "  ", NO_ASKS], "assign": True},
            {"fn": "formatCopyText", "args": [NO_ASKS, "$state"]},
        ]
        self.assertEqual(run_calls(calls)[-1], "\n".join([
            "[visual-explain 回答]",
            "資料: 料金改定は限定対象で段階公開する",
            "(examples/demo.html / id: doc-1 / schema: 2 / asks: fedcba9876543210)",
            "## 指摘",
            "#1 [削る]",
            "---",
            CLOSING,
        ]))

    def test_proto_ask_id_survives_select_memo_and_restore(self) -> None:
        results = run_calls([
            {"fn": "selectOption", "args": ["$state", "__proto__", "opt-p", CONTRACT_PROTO], "assign": True},
            {"fn": "setMemo", "args": ["$state", "__proto__", "懸念あり"], "assign": True},
            {"fn": "serializeState", "args": ["$state"]},
            {"fn": "formatCopyText", "args": [CONTRACT_PROTO, "$state"]},
        ])
        self.assertEqual(results[1]["selections"], {"__proto__": "opt-p"})
        (restored,) = run_calls([{"fn": "restoreState", "args": [results[2], CONTRACT_PROTO]}])
        self.assertEqual(restored["memos"], {"__proto__": "懸念あり"})
        self.assertIn("Q1. 汚染に耐えますか？: はい / 補足: 懸念あり", results[3])

    def test_delimiter_char_ids_round_trip(self) -> None:
        results = run_calls([
            {"fn": "selectOption", "args": ["$state", "ask,1", "opt=1", CONTRACT_DELIM], "assign": True},
            {"fn": "serializeState", "args": ["$state"]},
        ])
        (restored,) = run_calls([{"fn": "restoreState", "args": [results[-1], CONTRACT_DELIM]}])
        self.assertEqual(restored["selections"], {"ask,1": "opt=1"})

    def test_find_panel_row_matches_by_dataset_value(self) -> None:
        rows = [
            {"dataset": {"vePanelAsk": "決定\"1"}, "marker": "row-quote-japanese"},
            {"dataset": {"vePanelAsk": " 2ask"}, "marker": "row-leading-space-digit"},
        ]
        first, second, none = run_calls([
            {"fn": "findPanelRow", "args": [rows, "決定\"1"]},
            {"fn": "findPanelRow", "args": [rows, " 2ask"]},
            {"fn": "findPanelRow", "args": [rows, "b"]},
        ])
        self.assertEqual(first["marker"], "row-quote-japanese")
        self.assertEqual(second["marker"], "row-leading-space-digit")
        self.assertIsNone(none)

    def test_copy_text_treats_withdrawn_option_in_state_as_omakase(self) -> None:
        (text,) = run_calls([{"fn": "formatCopyText", "args": [CONTRACT, {
            "selections": {"ask-1": "opt-w"}, "memos": {}, "globalMemo": "", "annotations": []}]}])
        self.assertIn("Q1. 対象範囲をどちらにしますか？: (未選択 = お任せ)", text)
        self.assertNotIn("案W", text)

    def test_engine_sources_pass_node_check(self) -> None:
        for name in ("decision_engine.js", "decision_engine_driver.js"):
            proc = subprocess.run([NODE, "--check", str(RUNTIME / name)], capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))

    def test_skeleton_inline_scripts_pass_node_check(self) -> None:
        bodies = re.findall(r"<script>(.*?)</script>", SKELETON.read_text("utf-8"), re.S)
        self.assertGreaterEqual(len(bodies), 3)
        with tempfile.TemporaryDirectory() as tmp:
            for index, body in enumerate(bodies):
                path = Path(tmp) / f"inline-{index}.js"
                path.write_text(body, "utf-8")
                proc = subprocess.run([NODE, "--check", str(path)], capture_output=True)
                self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
