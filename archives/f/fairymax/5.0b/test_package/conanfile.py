#!/usr/bin/env python3
"""Conan test_package for fairymax 5.0b.

R34: Test must actually exercise the tested package's binary.
fairymax is a chess engine — the test runs the binary via test_fairymax.sh.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class FairymaxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["fairymax"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        test_script = os.path.join(self.source_folder, "test_fairymax.sh")
        if can_run(self):
            self.run(f'sh "{test_script}" "{bin_dir}/"', env="conanrun")
