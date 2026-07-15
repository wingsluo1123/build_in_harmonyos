#!/usr/bin/env python3
"""Conan test_package — pdfcrack 0.21

L1 test: verify the pdfcrack binary is installed and can show version.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class PdfcrackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the pdfcrack binary in the package folder
        pkg_folder = self.dependencies["pdfcrack"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "pdfcrack")
        if can_run(self):
            # R34: test must actually use the tested package's binary
            self.run(f'"{bin_path}" --version', env="conanrun")
