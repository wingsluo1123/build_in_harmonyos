#!/usr/bin/env python3
"""Conan test_package — rmlint v2.10.3 L1 test.

Verifies that the rmlint binary is installed and functional.
"""

import os
from conan import ConanFile
from conan.tools.build import can_run


class RmlintTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Test 1: rmlint --help
            self.run("rmlint --help", env="conanrun")

            # Test 2: rmlint --version
            self.run("rmlint --version", env="conanrun")