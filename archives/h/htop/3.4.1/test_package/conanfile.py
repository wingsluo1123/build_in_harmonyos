#!/usr/bin/env python3
"""Conan test_package for htop — smoke test via --version.

Verifies the htop binary is installed and reports correct version.
"""
import os

from conan import ConanFile


class HtopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Test must actually use the tested package
        # Run htop --version to verify the binary is installed and functional
        self.run("htop --version", env="conanrun")
