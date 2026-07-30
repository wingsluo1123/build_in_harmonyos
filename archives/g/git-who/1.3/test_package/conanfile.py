#!/usr/bin/env python3
"""Conan test_package — git-who 1.3 smoke test."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class GitWhoTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_path = os.path.join(self.dependencies["git-who"].package_folder,
                                "bin", "git-who")
        if not os.path.exists(bin_path):
            raise Exception(f"git-who binary not found: {bin_path}")
        if can_run(self):
            self.run(f'"{bin_path}" --help', env="conanrun")
