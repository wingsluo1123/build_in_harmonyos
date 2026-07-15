#!/usr/bin/env python3
"""Conan test_package for symlinks 1.4.3 — binary tool smoke test.

Verifies that the symlinks binary is installed and runs correctly.
"""
import os
import tempfile

from conan import ConanFile


class SymlinksTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the symlinks binary in the package
        bin_path = os.path.join(self.dependencies["symlinks"].package_folder, "bin", "symlinks")
        if not os.path.exists(bin_path):
            for root, dirs, files in os.walk(self.dependencies["symlinks"].package_folder):
                if "symlinks" in files:
                    bin_path = os.path.join(root, "symlinks")
                    break

        # symlinks requires a directory argument; create a temp dir and scan it
        with tempfile.TemporaryDirectory() as tmpdir:
            self.run(f'"{bin_path}" -v {tmpdir}', env="conanrun")
