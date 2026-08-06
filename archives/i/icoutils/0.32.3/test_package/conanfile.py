#!/usr/bin/env python3
"""Test package for icoutils 0.32.3 (Autotools) — smoke test for command-line tools."""
import os
from conan import ConanFile


class IcoutilsTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["icoutils"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: exercise the packaged binary to verify it works
        self.run(f"sh {os.path.join(self.source_folder, 'test_icoutils.sh')} {bin_dir}", env="conanrun")
        self.output.info("icoutils: OK")
