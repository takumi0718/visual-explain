"""check.sh --selftest が v1 / v2 / v3 の構造ケースを含めて全件通る。"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

CHECK = Path(__file__).resolve().parents[1] / "check.sh"


class SelftestTest(unittest.TestCase):
    def test_selftest_passes_with_v3_cases(self) -> None:
        proc = subprocess.run(["bash", str(CHECK), "--selftest"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("selftest: 36 passed, 0 failed", proc.stdout)


if __name__ == "__main__":
    unittest.main()
