"""Check the upstream TAP result contract without running target binaries."""

import importlib.util
import unittest
from pathlib import Path


RUNNER = Path(__file__).resolve().parents[1] / "run_upstream_tests.py"
spec = importlib.util.spec_from_file_location("mblaze_tap_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class TapAccountingTests(unittest.TestCase):
    def test_complete_pass_is_accepted(self):
        self.assertEqual(runner.parse_tap("1..2\nok - first\nok - second\n", 0), (2, 2, True))

    def test_skip_cannot_be_reported_as_pass(self):
        self.assertEqual(
            runner.parse_tap("1..2\nok - first\nok - unavailable # SKIP target feature\n", 0),
            (2, 1, False),
        )

    def test_missing_assertion_and_not_ok_are_rejected(self):
        self.assertFalse(runner.parse_tap("1..2\nok - first\n", 0)[2])
        self.assertFalse(runner.parse_tap("1..2\nok - first\nnot ok - second\n", 0)[2])


if __name__ == "__main__":
    unittest.main()
