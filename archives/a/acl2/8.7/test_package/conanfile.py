#!/usr/bin/env python3
"""Conan test_package — acl2 8.7

L1 test: verify the saved_acl2 binary is installed and can run a
simple ACL2 proof session.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class Acl2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["acl2"].package_folder
        bin_path = os.path.join(pkg, "bin", "saved_acl2")
        if can_run(self):
            self.run(f'sh {self.source_folder}/test.sh "{bin_path}"', env="conanrun")
