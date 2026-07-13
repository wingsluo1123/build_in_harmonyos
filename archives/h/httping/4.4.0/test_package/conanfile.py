#!/usr/bin/env python3
"""Conan test_package for httping — L1 smoke test.

Verifies httping binary is installed and runs --version successfully.
"""
import os

from conan import ConanFile


class HttpingTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify binary exists and --version works
        self.run("httping --version", env="conanrun")

        # Verify help output
        self.run("httping --help 2>&1", env="conanrun")
