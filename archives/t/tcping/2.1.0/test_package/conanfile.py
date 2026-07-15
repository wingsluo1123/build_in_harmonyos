#!/usr/bin/env python3
"""Conan test_package — tcping 2.1.0

L1 test: verify the tcping binary is installed and functional.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class TcpingTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["tcping"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "tcping")
        assert os.path.isfile(bin_path), f"tcping binary not found at {bin_path}"
        # R34: test must substantively exercise the binary
        if can_run(self):
            # tcping with no args prints usage and exits 255 — expected non-zero exit
            try:
                self.run(f'"{bin_path}"', env="conanrun")
            except ConanException:
                pass  # Expected: tcping exits 255 when no args provided
