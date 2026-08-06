#!/usr/bin/env python3
"""Conan test_package — iftop 1.0_pre4-r0.

iftop is a command-line tool (not a library), so the test verifies
the binary is installed and runs correctly by checking its help output.

R34: Test must exercise the tested package's binary.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class IftopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Test must exercise the tested package's binary
        # iftop -h prints help (including version) and exits with code 0
        if can_run(self):
            self.run("iftop -h 2>&1 | grep 'iftop, version'", env="conanrun")
