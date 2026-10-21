#!/usr/bin/env python3
"""Unit self-test for the kf6-relative-needed knowledge pack.

Runs entirely on fixtures: no network, no conan, no registry.  The sample
library (archives/b/baloo-widgets/26.04.0) provides the end-to-end evidence via
repro.sh, this file only guards the detection logic itself.
"""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name: str):
    path = os.path.join(HERE, name)
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


detect = load("detect-relative-needed.py")


class RequiredMirrorTest(unittest.TestCase):
    def test_relative_entry_resolves_against_cwd(self):
        runtime = "/tmp/build/autotests"
        self.assertEqual(
            detect.required_mirror(runtime, "../../bin/libKF6ConfigCore.so"),
            "/tmp/bin/libKF6ConfigCore.so",
        )

    def test_single_level_relative_entry(self):
        runtime = "/tmp/build/autotests"
        self.assertEqual(
            detect.required_mirror(runtime, "../lib/libKF6CoreAddons.so"),
            "/tmp/build/lib/libKF6CoreAddons.so",
        )

    def test_absolute_entry_resolves_to_itself(self):
        needed = "/storage/x/.cache/conan2/p/kcore/p/lib/libKF6CoreAddons.so"
        self.assertEqual(
            detect.required_mirror("/tmp/build/autotests", needed), needed)


class LogScanTest(unittest.TestCase):
    def test_relative_loader_error_is_detected(self):
        report = detect.scan_log(os.path.join(HERE, "fixtures", "log-relative.log"))
        self.assertGreaterEqual(report["count"], 1)
        names = [hit["lib"] for hit in report["hits"]]
        self.assertTrue(any("/" in n for n in names), names)

    def test_plain_missing_library_is_not_reported(self):
        report = detect.scan_log(os.path.join(HERE, "fixtures", "log-plain.log"))
        self.assertEqual(report["count"], 0)

    def test_clean_log_is_not_reported(self):
        report = detect.scan_log(os.path.join(HERE, "fixtures", "log-clean.log"))
        self.assertEqual(report["count"], 0)


class ScanReportShapeTest(unittest.TestCase):
    def test_scan_without_packages_returns_empty_report(self):
        report = detect.scan([], [], [])
        self.assertEqual(report["count"], 0)
        self.assertEqual(report["libs"], [])
        self.assertEqual(report["runtime"], [])

    def test_runtime_section_marks_missing_mirror(self):
        with tempfile.TemporaryDirectory() as tmp:
            rdir = os.path.join(tmp, "proj", "build", "autotests")
            os.makedirs(rdir)
            expected = detect.required_mirror(rdir, "../../bin/libKF6ConfigCore.so")
            self.assertEqual(expected, os.path.join(tmp, "proj", "bin",
                                                    "libKF6ConfigCore.so"))
            self.assertFalse(os.path.exists(expected))


if __name__ == "__main__":
    unittest.main(verbosity=2)
