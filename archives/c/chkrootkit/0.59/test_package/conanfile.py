#!/usr/bin/env python3
"""Conan test_package — chkrootkit 0.59 (L1 test: verify binary works)"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ChkrootkitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["chkrootkit"]
            bin_path = os.path.join(dep.package_folder, "bin", "chkrootkit")
            # R34: test must actually invoke the tested package's binary
            # chkrootkit -V uses die() which exits with code 1, so we pipe
            # through grep to verify output contains the expected version
            self.run(f'"{bin_path}" -V 2>&1 | grep -q "chkrootkit version"', env="conanrun")
