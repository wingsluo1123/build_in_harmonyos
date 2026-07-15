#!/usr/bin/env python3
"""Conan test_package for hashcat 7.1.2 — binary tool smoke test.

Verifies that the hashcat binary is installed and runs correctly.
hashcat --version should print the version string.
"""
import os

from conan import ConanFile


class HashcatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the hashcat binary in the package
        bin_path = os.path.join(self.dependencies["hashcat"].package_folder, "bin", "hashcat")
        if not os.path.exists(bin_path):
            # Try alternate path
            for root, dirs, files in os.walk(self.dependencies["hashcat"].package_folder):
                if "hashcat" in files:
                    bin_path = os.path.join(root, "hashcat")
                    break
        self.run(f'"{bin_path}" --version', env="conanrun")
