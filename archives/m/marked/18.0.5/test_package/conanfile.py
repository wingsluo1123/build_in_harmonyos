#!/usr/bin/env python3
"""Conan test_package for marked 18.0.5 — JavaScript import test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class MarkedTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            marked_root = self.dependencies["marked"].package_folder
            test_script = os.path.join(os.path.dirname(__file__), "test_marked.sh")
            self.run(f'sh "{test_script}" "{marked_root}"', env="conanrun")
