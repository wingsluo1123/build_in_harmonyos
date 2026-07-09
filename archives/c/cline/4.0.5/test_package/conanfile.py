#!/usr/bin/env python3
"""Conan test_package for cline 4.0.5 — JavaScript module verification.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

Tests:
1. Verify the CLI entry point (dist/index.js) exists and is a valid JS file
2. Verify SDK package dist directories exist
3. Verify package.json files are present with correct version
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class ClineTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            cline_root = self.dependencies["cline"].package_folder
            test_script = os.path.join(os.path.dirname(__file__), "test_cline.py")
            self.run(f'{sys.executable} "{test_script}" "{cline_root}"')
