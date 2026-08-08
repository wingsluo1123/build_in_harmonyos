#!/usr/bin/env python3
"""Conan test_package for retawq 0.2.6c — verifies the binary works."""
import os

from conan import ConanFile


class RetawqTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run the retawq binary with --version to verify it works
        bin_path = os.path.join(self.dependencies["retawq"].cpp_info.bindirs[0], "retawq")
        self.run(f'"{bin_path}" --version', env="conanrun")
