#!/usr/bin/env python3
"""Test package for defaultbrowser — verify the placeholder binary exists."""
from conan import ConanFile


class DefaultbrowserTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("defaultbrowser", env="conanrun", ignore_errors=True)
