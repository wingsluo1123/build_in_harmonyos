#!/usr/bin/env python3
from conan import ConanFile
from conan.tools.build import can_run
import os


class CmatrixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Test that the cmatrix binary exists and runs
        cmatrix_bin = os.path.join(self.dependencies["cmatrix"].package_folder, "bin", "cmatrix")
        self.output.info(f"Testing cmatrix binary at: {cmatrix_bin}")
        
        if not os.path.exists(cmatrix_bin):
            raise Exception(f"cmatrix binary not found at {cmatrix_bin}")
        
        if can_run(self):
            self.run(f"{cmatrix_bin} -V", env="conanrun")
        else:
            self.output.info("Cross-compilation mode: binary exists check passed")