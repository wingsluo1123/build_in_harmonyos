#!/usr/bin/env python3
"""Conan test_package — ax25-apps 0.0.8-rc5.

R34: Test must actually execute the packaged binary.
This test runs `ax25ipd --version` to verify the binary works.
"""
import os

from conan import ConanFile


class Ax25AppsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Execute the actual binary to verify the package
        # CI profile sets sbindir=${prefix}/bin, so all binaries are in bin/
        pkg_folder = self.dependencies["ax25-apps"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "ax25ipd")
        self.run(f'"{bin_path}" --version', env="conanrun")
