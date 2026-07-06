#!/usr/bin/env python3
"""Conan test_package — kopia L1 smoke test.

Verifies that the kopia binary was installed and runs correctly.
"""
import os

from conan import ConanFile


class KopiaTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Smoke test: run kopia --version
        self.run("kopia --version", env="conanrun")
        # Verify help works
        self.run("kopia --help", env="conanrun")
