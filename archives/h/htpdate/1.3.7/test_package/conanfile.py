#!/usr/bin/env python3
"""Conan test_package for htpdate — verifies the binary is installed and functional."""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class HtpdateTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Test must substantively depend on the tested package
        # Run htpdate -v to verify the binary is installed and reports its version
        self.run("htpdate -v", env="conanrun")
