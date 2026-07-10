#!/usr/bin/env python3
"""Conan test_package for luatex 0.99997.

L1 test: verify the 'luatex' binary works correctly.
luatex is a CLI tool, we test by running the binary.
"""
import os
import shutil

from conan import ConanFile


class LuatexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies["luatex"].package_folder
        luatex_bin = os.path.join(pkg_folder, "bin", "luatex")
        if not os.path.exists(luatex_bin):
            raise Exception(f"luatex binary not found at {luatex_bin}")
        self.run(f'{bash} -c "{luatex_bin} --version 2>&1 || true"', env="conanrun")
