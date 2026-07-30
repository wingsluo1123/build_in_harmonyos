#!/usr/bin/env python3
"""Conan test_package for cmatrix — Conan L1 official test.

Verifies that cmatrix binary can be executed and reports version.
"""
import os

from conan import ConanFile


class CmatrixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("cmatrix --version", env="conanrun")