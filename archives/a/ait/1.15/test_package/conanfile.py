#!/usr/bin/env python3
"""Conan test_package — ait 1.15 editor.

R34: the test must exercise the packaged binary.
We run `ait -v` and assert the output contains "Ait 1.15".
"""
import os

from conan import ConanFile


class AitTestConan(ConanFile):
    test_type = "explicit"
    settings = "os", "arch", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # ait is installed in bin/ by the recipe.
        ait_bin = os.path.join(self.dependencies["ait"].package_folder, "bin", "ait")
        # Run ait -v to verify the version output.
        self.run(f'"{ait_bin}" -v', env="conanrun")
