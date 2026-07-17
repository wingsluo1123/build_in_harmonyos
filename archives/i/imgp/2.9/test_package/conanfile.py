#!/usr/bin/env python3
"""Conan test_package for imgp — Python-based verification.

Tests that imgp can be imported and its CLI command works.
Includes a real image processing test to verify functionality.
"""
import os
from conan import ConanFile


class ImgpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Run test.py (source file for CI L0c compliance)
        self.run("python3 test.py", env="conanrun")