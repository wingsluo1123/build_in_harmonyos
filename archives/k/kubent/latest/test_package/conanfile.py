#!/usr/bin/env python3
"""Conan test_package for kubent — smoke test.

Verifies that the kubent binary is installed and can report its version.
"""
import os

from conan import ConanFile


class KubentTestConan(ConanFile):
    settings = "os", "arch", "build_type", "compiler"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # In Conan 2.x, access dependency via self.dependencies
        dep = self.dependencies["kubent"]
        bin_path = os.path.join(dep.package_folder, "bin", "kubent")
        if not os.path.exists(bin_path):
            # Fallback: search in package folder
            for root, dirs, files in os.walk(dep.package_folder):
                if "kubent" in files:
                    bin_path = os.path.join(root, "kubent")
                    break
        # Smoke test: run kubent --version
        self.run(f'"{bin_path}" --version', env="conanrun")
