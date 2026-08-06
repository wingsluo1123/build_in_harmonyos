#!/usr/bin/env python3
"""Conan test_package — geckodriver 0.36.0

L1 test: verifies the geckodriver binary runs and reports its version.
R34: test must execute the actual binary from the package.
"""
from conan import ConanFile
from conan.tools.layout import basic_layout


class GeckodriverTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # R34: Execute the actual binary from the package
        # geckodriver --version prints version info and exits 0
        self.run("geckodriver --version", env="conanrun")
