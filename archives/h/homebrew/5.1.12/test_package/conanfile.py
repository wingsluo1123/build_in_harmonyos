#!/usr/bin/env python3
"""Conan test_package for homebrew — verify brew --version works."""
import os
from conan import ConanFile


class HomebrewTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify brew binary exists and runs
        self.run("brew --version", env="conanrun")
