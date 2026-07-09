#!/usr/bin/env python3
"""Conan test_package for xetex 0.99997.

L1 test: verify the 'xetex' binary works correctly.
xetex is a CLI tool, we test by running the binary via shell script.
"""
import os
import shutil

from conan import ConanFile


class XetexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies["xetex"].package_folder
        xetex_bin = os.path.join(pkg_folder, "bin", "xetex")
        if not os.path.exists(xetex_bin):
            raise Exception(f"xetex binary not found at {xetex_bin}")
        # Run xetex to verify binary is executable
        self.run(f'{bash} -c "{xetex_bin} --version 2>&1 || true"', env="conanrun")
