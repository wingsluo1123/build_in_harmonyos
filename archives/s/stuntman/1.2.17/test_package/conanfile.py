#!/usr/bin/env python3
"""Conan test_package — stuntman 1.2.17

L1 test: verify the stunclient binary is installed and is a valid ELF.
Note: On OHOS, unsigned binaries cannot be executed (ELF signing required).
The test verifies binary existence and ELF header instead of execution.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.errors import ConanException


class StuntmanTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the stunclient binary in the package folder
        pkg_folder = self.dependencies["stuntman"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "stunclient")
        # Verify binary exists
        if not os.path.exists(bin_path):
            raise Exception(f"stunclient binary not found at {bin_path}")
        # Verify it's a valid ELF file (check magic bytes)
        with open(bin_path, "rb") as f:
            magic = f.read(4)
            if magic != b"\x7fELF":
                raise Exception(f"stunclient is not a valid ELF file (magic: {magic})")
        self.output.info("stunclient binary verified: exists and is valid ELF")
        # Try to run it (may fail on OHOS due to ELF signing - not a recipe issue)
        if can_run(self):
            try:
                self.run(f'"{bin_path}" --help', env="conanrun")
            except ConanException as e:
                if "Permission denied" in str(e) or "126" in str(e):
                    self.output.info("Binary execution skipped (OHOS ELF signing limitation)")
                else:
                    raise
