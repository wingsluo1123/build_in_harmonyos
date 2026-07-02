#!/usr/bin/env python3
"""Conan test_package — checkmake 0.3.2 (L1 smoke test).

checkmake is a standalone Go binary (linter for Makefiles).
This test verifies the binary is functional by running --version.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class CheckmakeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "build"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bin_path = os.path.join(
                self.dependencies["checkmake"].cpp_info.bindir, "checkmake"
            )
            self.run(f'"{bin_path}" --version', env="conanrun")
