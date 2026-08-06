#!/usr/bin/env python3
"""Conan test_package for extract-dtb.

Verifies that the extract-dtb tool is properly installed and functional.
Tests:
  1. extract-dtb --version returns "1.2"
  2. extract-dtb --help shows usage
  3. Functional test: extract DTB from a dummy kernel image
"""
import os

from conan import ConanFile


class ExtractDtbTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test 1: extract-dtb --version
        self.run("extract-dtb --version", env="conanrun")

        # Test 2: extract-dtb --help
        self.run("extract-dtb --help", env="conanrun")

        # Test 3: Functional test — extract DTB from dummy kernel image
        test_script = os.path.join(os.path.dirname(__file__), "test_extract_dtb.py")
        self.run(f"python3 {test_script}", env="conanrun")
