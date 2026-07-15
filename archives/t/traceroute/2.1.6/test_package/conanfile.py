#!/usr/bin/env python3
"""Conan test_package — traceroute 2.1.6

Verifies the traceroute binary is installed and runs correctly.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class TracerouteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # R34: Test must actually use the tested package
        # Run traceroute --version to verify the binary works
        self.run("traceroute --version", env="conanrun")
