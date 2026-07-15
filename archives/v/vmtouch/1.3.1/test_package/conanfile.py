#!/usr/bin/env python3
"""Conan test_package — vmtouch 1.3.1

L1 test: verify the vmtouch binary is installed and can inspect a file's cache status.
"""
import os
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class VmtouchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the vmtouch binary in the package folder
        pkg_folder = self.dependencies["vmtouch"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "vmtouch")
        if can_run(self):
            # Create a temp file and run vmtouch on it to verify the binary works
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write("vmtouch test content\n")
                tmpfile = f.name
            try:
                self.run(f'"{bin_path}" "{tmpfile}"', env="conanrun")
            finally:
                os.unlink(tmpfile)
