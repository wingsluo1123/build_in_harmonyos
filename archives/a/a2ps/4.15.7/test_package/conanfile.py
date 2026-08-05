#!/usr/bin/env python3
"""Conan test_package for a2ps — tests the a2ps binary functionality.

This test verifies that the a2ps binary is installed and can report its version.
The test depends on the a2ps package (R34): without it, the binary won't be found.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class A2psTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Test: a2ps --version must succeed (fails without package installed)
            self.run("a2ps --version", env="conanrun")
