#!/usr/bin/env python3
"""Conan test_package — vmtouch 1.3.1

L1 test: verify the vmtouch binary is installed and can inspect a file's cache status.
"""
import os

from conan import ConanFile


class VmtouchTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["vmtouch"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "vmtouch")
        self.run(f'sh test.sh "{bin_path}"', env="conanrun")
