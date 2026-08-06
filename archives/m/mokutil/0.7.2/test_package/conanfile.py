#!/usr/bin/env python3
"""Conan test_package for mokutil — smoke test the installed binary.

Verifies that mokutil is installed, executable, and outputs the
correct version string when run with --version.
"""
import os

from conan import ConanFile


class MokutilTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["mokutil"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: exercise the packaged artifact — run mokutil --version
        script = os.path.join(os.path.dirname(__file__), "test_mokutil.sh")
        self.run(f"bash {script} {bin_dir}", env="conanrun")
        self.output.info("mokutil: smoke test passed")
