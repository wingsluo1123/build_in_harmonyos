#!/usr/bin/env python3
"""Conan test_package — datamash 1.9

Tests datamash's core data processing operations (sum, count, max).
"""
import os

from conan import ConanFile


class DatamashTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        bin_path = os.path.join(self.dependencies["datamash"].package_folder, "bin", "datamash")
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(f'sh "{test_script}" "{bin_path}"')
