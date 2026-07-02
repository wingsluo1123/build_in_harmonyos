#!/usr/bin/env python3
"""Conan test_package for checkbashisms — verifies the Perl script tool works.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile


class CheckbashismsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the checkbashisms binary path from the dependency package
        dep = self.dependencies["checkbashisms"]
        bin_path = os.path.join(str(dep.package_folder), "bin", "checkbashisms")

        # Test 1: --version should work
        self.run(f'"{bin_path}" --version', env="conanrun")

        # Test 2: --help should work
        self.run(f'"{bin_path}" --help', env="conanrun")

        # Test 3: Check a clean script (no bashisms, exit 0)
        clean_script = os.path.join(self.source_folder, "clean_script.sh")
        self.run(f'"{bin_path}" "{clean_script}"', env="conanrun")

        # Test 4: Check a script with bashisms (exit 1 is expected, use || true)
        bashism_script = os.path.join(self.source_folder, "bashism_script.sh")
        self.run(f'"{bin_path}" "{bashism_script}" || true', env="conanrun")
