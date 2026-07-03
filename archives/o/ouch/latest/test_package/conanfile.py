#!/usr/bin/env python3
"""Conan test_package — ouch (Rust CLI binary).

L1 test: verify the ouch binary is installed and functional.
Runs `ouch --version` to confirm the binary works.
"""
import os

from conan import ConanFile


class OuchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the ouch binary in the package folder
        pkg_folder = self.dependencies["ouch"].package_folder
        ouch_bin = os.path.join(pkg_folder, "bin", "ouch")
        if os.path.exists(ouch_bin):
            self.run(f'"{ouch_bin}" --version')
        else:
            raise Exception(f"ouch binary not found at {ouch_bin}")
