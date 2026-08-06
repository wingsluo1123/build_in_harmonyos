#!/usr/bin/env python3
"""Test package for gphoto2 — runs the installed binary."""
import os
from conan import ConanFile
from conan.tools.layout import basic_layout


class Gphoto2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # R34: test must exercise the actual binary
        # gphoto2 --version verifies the binary is functional
        self.run("gphoto2 --version", env="conanrun")
