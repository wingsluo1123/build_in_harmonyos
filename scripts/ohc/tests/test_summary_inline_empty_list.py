#!/usr/bin/env python3
"""Persistent regression test for inline empty YAML list parsing (summary.py).

Project has no established pytest/unittest harness, so this is the smallest
repository-consistent unittest harness for scripts/ohc/summary.py.
Trigger shape (from archives/q/qpdf/12.3.2/manifest.yaml):
    knowledge_gained: []      # inline empty list stored as str
    knowledge_gained:         # later repeated list key -> .append on str
      - "item"
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ohc.summary import _parse_yaml_simple  # noqa: E402


class SummaryInlineEmptyListTest(unittest.TestCase):
    SAMPLE = (
        "manifest_version: 1\n"
        "name: qpdf\n"
        "version: 12.3.2\n"
        "knowledge_gained: []\n"
        "requires:\n"
        "  - zlib/1.3.1.1\n"
        "knowledge_gained:\n"
        '  - "dep zlib static"\n'
    )

    def _parse(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(self.SAMPLE)
            path = f.name
        try:
            return _parse_yaml_simple(Path(path))
        finally:
            os.unlink(path)

    def test_inline_empty_list_is_list(self):
        data = self._parse()
        kg = data.get("knowledge_gained")
        self.assertIsInstance(kg, list, f"knowledge_gained should be list, got {type(kg).__name__}: {kg!r}")
        self.assertIn('"dep zlib static"', kg, f"later list item missing: {kg!r}")

    def test_scalar_controls_remain_str(self):
        data = self._parse()
        self.assertIsInstance(data["manifest_version"], str)
        self.assertIsInstance(data["name"], str)
        self.assertIsInstance(data["version"], str)


if __name__ == "__main__":
    unittest.main()
