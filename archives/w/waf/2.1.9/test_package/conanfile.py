#!/usr/bin/env python3
"""Conan test_package for waf — verifies the waf script is installed and functional.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).
"""
from conan import ConanFile


class WafTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify waf is available and reports its version
        self.run("waf --version", env="conanrun")
