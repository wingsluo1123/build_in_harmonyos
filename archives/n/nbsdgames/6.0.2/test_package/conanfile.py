#!/usr/bin/env python3
"""Conan test_package — nbsdgames 6.0.2."""

import os

from conan import ConanFile
from conan.tools.build import can_run


class NbsdgamesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["nbsdgames"]
            bin_path = os.path.join(dep.cpp_info.bindirs[0], "sudoku")
            self.run(f'test -x "{bin_path}"', env="conanrun")
            self.run(f'"{bin_path}" -h >/dev/null 2>&1 || true', env="conanrun")
