#!/usr/bin/env python3
"""Conan test_package for imgp — Python-based verification.

Tests that imgp can be imported and its CLI command works.
"""
import os
from conan import ConanFile


class ImgpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test 1: Verify imgp can be imported as a Python module
        self.run("python3 -c \"import imgp; print(f'imgp version: {imgp._VERSION_}')\"", env="conanrun")

        # Test 2: Verify imgp CLI works
        self.run("imgp --help", env="conanrun")