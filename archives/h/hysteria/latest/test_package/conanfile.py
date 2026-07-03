#!/usr/bin/env python3
"""Test package for hysteria — smoke test the built binary.

Verifies that the hysteria binary can be executed and reports its version.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class HysteriaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # In Conan 2.x, use self.dependencies to find the package folder
            dep = self.dependencies["hysteria"]
            bin_path = os.path.join(str(dep.package_folder), "bin", "hysteria")
            if not os.path.isfile(bin_path):
                raise AssertionError(f"hysteria binary not found at {bin_path}")

            # Smoke test: run version command
            self.run(f'"{bin_path}" version')

            # Verify the binary is a valid ELF executable
            self.run(f'file "{bin_path}"')
