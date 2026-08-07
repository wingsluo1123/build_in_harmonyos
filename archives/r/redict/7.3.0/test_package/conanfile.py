#!/usr/bin/env python3
"""Conan test_package for redict 7.3.0.

Runs redict-server --version to verify the binary is functional.
"""
import os

from conan import ConanFile


class RedictTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build needed, we test the binary directly

    def test(self):
        # R34: Test must actually exercise the package's binary
        binary = os.path.join(self.dependencies["redict"].cpp_info.bindirs[0], "redict-server")
        self.run(f"{binary} --version", env="conanrun")
