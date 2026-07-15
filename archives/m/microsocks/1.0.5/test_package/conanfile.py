#!/usr/bin/env python3
"""Conan test_package for microsocks — runs the binary to verify it works.

microsocks is a command-line application, so the test runs the binary
directly with --help to verify it was built correctly and is functional.
microsocks --help exits with code 1 (normal behavior), so we use a
shell script wrapper to handle the non-zero exit code.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class MicrosocksTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # Run microsocks with --help via shell script wrapper
        # microsocks --help exits with code 1 (normal), script handles it
        binary = os.path.join(self.dependencies["microsocks"].package_folder, "bin", "microsocks")
        script = os.path.join(self.source_folder, "test_microsocks.sh")
        self.run(f'sh "{script}" "{binary}"', env="conanrun")
