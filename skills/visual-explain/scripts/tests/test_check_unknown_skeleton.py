"""The embedded checker rejects documents that declare an unknown skeleton version."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
CHECK = TESTS.parent / "check.sh"


class UnknownSkeletonVersionTest(unittest.TestCase):
    def test_unknown_version_is_rejected(self) -> None:
        text = (TESTS / "chevron-doc.html").read_text("utf-8")
        self.assertIn('<html lang="ja"', text)
        text = text.replace('<html lang="ja"', '<html lang="ja" data-ve-skeleton="9"', 1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.html"
            path.write_text(text, "utf-8")
            proc = subprocess.run(["bash", str(CHECK), str(path)], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("未知の skeleton 版です: 9", proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
