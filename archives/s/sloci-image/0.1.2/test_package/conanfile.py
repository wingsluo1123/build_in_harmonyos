#!/usr/bin/env python3
"""Conan test_package for sloci-image.

Verifies that the installed sloci-image script is executable and
can display its version and help text.
"""
from conan import ConanFile


class SlociImageTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("sloci-image --version", env="conanrun")
        self.run("sloci-image --help", env="conanrun")
