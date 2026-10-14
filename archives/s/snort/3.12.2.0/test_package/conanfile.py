#!/usr/bin/env python3
"""Conan test_package — snort 3.12.2.0 (consumer end-to-end tests).

Runs the consumer E2E executor (tests/run_e2e.sh) against the packaged
snort binary.  The executor drives real consumer workflows:

  1. version output
  2. --help
  3. configuration validation (-T) with an inline rule
  4. end-to-end detection run over a crafted pcap (positive case)
  5. the same run with a non-matching rule (negative control)
  6. the embedded Catch2 suite (snort --catch-test all)

Each case is judged independently by the executor (one TEST PASS/FAIL line
per case), followed by a TEST SUMMARY line; any failure exits non-zero and
fails test_package.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class SnortTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["snort"]
        snort_bin = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0],
                                 "snort")
        tests_dir = os.path.join(self.source_folder, "tests")
        self.run(f'bash "{os.path.join(tests_dir, "run_e2e.sh")}" '
                 f'"{snort_bin}" "{tests_dir}"',
                 env="conanrun")
