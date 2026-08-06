#!/usr/bin/env python3
"""Conan test_package — icoutils 0.32.3

Verifies that the installed icoutils binaries (icotool, wrestool) work correctly
by running the test_icoutils.sh script which checks --version output.
"""
import os

from conan import ConanFile


class IcoutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # R34: Test must actually execute the installed binary
        script_path = os.path.join(self.recipe_folder, "test_icoutils.sh")
        self.run(f"sh {script_path}", env="conanrun")
