#!/usr/bin/env python3
"""Conan test_package — nkf 2.1.5

L1 test: verify the nkf binary is installed and can perform encoding conversion.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class NkfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Find the nkf binary in the package folder
            pkg_folder = self.dependencies["nkf"].package_folder
            bin_path = os.path.join(pkg_folder, "bin", "nkf")
            # Test 1: version check — verifies binary is executable
            self.run(f'"{bin_path}" --version', env="conanrun")
            # Test 2: encoding conversion — create a file and convert from Shift_JIS to UTF-8
            test_input = os.path.join(self.build_folder, "nkf_test_input.txt")
            # Shift_JIS encoded "test" (0x83 0x65 0x83 0x58 0x83 0x67 = テスト)
            with open(test_input, "wb") as f:
                f.write(b"\x83\x65\x83\x58\x83\x67\n")
            self.run(f'"{bin_path}" -w "{test_input}"', env="conanrun")
