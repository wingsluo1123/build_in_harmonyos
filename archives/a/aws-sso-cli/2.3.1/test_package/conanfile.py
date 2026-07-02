#!/usr/bin/env python3
"""Conan test_package — aws-sso-cli 2.3.1 smoke test."""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AwsSsoCliTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "build"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bin_path = os.path.join(
                self.dependencies["aws-sso-cli"].cpp_info.bindir, "aws-sso"
            )
            self.run(f'"{bin_path}" version', env="conanrun")
