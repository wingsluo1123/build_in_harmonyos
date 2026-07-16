#!/usr/bin/env python3
"""Conan test_package for knock 0.8.2-r2 — binary tool smoke test.

Verifies that the knock binary is installed and runs correctly.
"""
import os

from conan import ConanFile


class KnockTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(self.dependencies["knock"].package_folder, "bin", "knock")
        if not os.path.exists(bin_path):
            for root, dirs, files in os.walk(self.dependencies["knock"].package_folder):
                if "knock" in files:
                    bin_path = os.path.join(root, "knock")
                    break
        self.run(f'"{bin_path}" --version', env="conanrun")