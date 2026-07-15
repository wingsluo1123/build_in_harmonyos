#!/usr/bin/env python3
"""Conan test_package for colordiff.

Tests that colordiff is installed correctly and can execute.
This test substantively depends on the colordiff package (R34).
"""
import os

from conan import ConanFile


class ColordiffTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # R34: Test substantively depends on the tested package.
        # Verify colordiff binary executes and reports its version.
        # This confirms the Perl script is installed and the shebang is correct.
        self.run("colordiff --version", env="conanrun")
