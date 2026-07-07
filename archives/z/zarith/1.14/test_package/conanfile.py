#!/usr/bin/env python3
"""Conan test_package -- ZArith 1.14

Verifies that zarith library is installed and can perform big integer arithmetic.
Test: 42 + 1 = 43 (big integer addition).
"""
import os

from conan import ConanFile


class ZarithTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        self.run("sh test_zarith.sh", env="conanrun")
