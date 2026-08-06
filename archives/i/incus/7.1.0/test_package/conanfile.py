#!/usr/bin/env python3
"""Conan test_package for incus — verifies built binaries are functional.

Tests that the incus client binary can report its version.
"""
import os

from conan import ConanFile


class IncusTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the incus binary in the package
        bin_path = os.path.join(self.cpp_info.bindirs[0], "incus")
        # Use the bin directory from the dependency
        bindir = None
        for dep in self.dependencies.values():
            if hasattr(dep, "cpp_info") and dep.cpp_info.bindirs:
                bindir = os.path.join(dep.cpp_info.bindirs[0])
                break

        # Try to run incus version
        self.run("incus version", env="conanrun")
