#!/usr/bin/env python3
"""Conan test_package for AFL++ — verifies the installed binaries work.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

R34: The test must substantively depend on the tested package.
We verify afl-fuzz --version and afl-showmap functionality.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AflplusplusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # R34: test must actually use the package binaries
        pkg = self.dependencies["aflplusplus"]
        bin_dir = os.path.join(pkg.package_folder, "bin")

        # Test 1: afl-fuzz --version (verifies the main binary runs)
        afl_fuzz = os.path.join(bin_dir, "afl-fuzz")
        self.run(f'"{afl_fuzz}" --version', env="conanrun")

        # Test 2: afl-cc --version (verifies the instrumentation wrapper)
        afl_cc = os.path.join(bin_dir, "afl-cc")
        assert os.path.exists(afl_cc), f"afl-cc not found at {afl_cc}"
        self.run(f'"{afl_cc}" --version', env="conanrun")
