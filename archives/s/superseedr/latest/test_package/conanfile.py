#!/usr/bin/env python3
"""Conan test_package — superseedr (Rust binary tool).

L1 test: verify the installed superseedr binary runs and reports version.
"""
import os

from conan import ConanFile


class SuperseedrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use VirtualRunEnv to find the binary in PATH
        self.run("superseedr --version", env=["conanrun"])
