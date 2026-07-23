#!/usr/bin/env python3
"""Conan test_package — mcpp 2.7.2

L1 test: verify the mcpp binary can preprocess C source files.
"""
import os
from conan import ConanFile
from conan.tools.build import can_run


class McppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        # Get the dependency's bindir
        dep = self.dependencies["mcpp"]
        bin_path = os.path.join(dep.package_folder, "bin", "mcpp")

        # Test 1: mcpp -v shows version string and include directories
        self.run(f"{bin_path} -v", env="conanrun")

        # Test 2: mcpp can preprocess a simple C source (macro expansion)
        test_input = os.path.join(self.source_folder, "test_input.c")
        self.run(f"{bin_path} {test_input}", env="conanrun")