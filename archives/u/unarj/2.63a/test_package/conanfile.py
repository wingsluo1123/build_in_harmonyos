#!/usr/bin/env python3
"""Conan test_package for unarj 2.63a — CLI tool test.

Verifies that the unarj binary is functional by running it
with no arguments (should print usage info).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class UnarjTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            unarj_bin = os.path.join(
                self.dependencies["unarj"].cpp_info.bindirs[0],
                "unarj"
            )
            # Test 1: Run unarj with no args — should print usage and exit
            test_script = os.path.join(self.source_folder, "test_unarj.sh")
            self.run(f'bash "{test_script}" "{unarj_bin}"', env="conanrun")
