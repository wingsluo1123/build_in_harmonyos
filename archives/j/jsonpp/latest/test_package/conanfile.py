#!/usr/bin/env python3
"""Conan test_package — jsonpp smoke test.

Tests that the jsonpp binary is installed and can pretty-print JSON.
Uses Conan 2.x API with VirtualRunEnv generator.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class JsonppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        # Get jsonpp binary path from the dependency's package folder
        jsonpp_bin = os.path.join(self.dependencies["jsonpp"].package_folder, "bin", "jsonpp")
        # Smoke test: pipe JSON through jsonpp and verify output
        self.run(f'echo \'{{"test":123}}\' | "{jsonpp_bin}"', env="conanrun")
