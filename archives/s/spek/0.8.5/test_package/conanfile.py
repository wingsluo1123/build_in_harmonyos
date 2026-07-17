#!/usr/bin/env python3
"""test_package for spek-cli - L1 test."""
from conan import ConanFile

class SpekTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("spek-cli --help", env="conanrun")
