#!/usr/bin/env python3
"""Conan test_package for emqx homebrew.

The test validates the installed EMQX release layout and runs the actual
launcher help command when the target binary can execute on the build host.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class EmqxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["emqx"].package_folder
        expected = [
            os.path.join(pkg, "bin", "emqx"),
            os.path.join(pkg, "releases", "5.8.8"),
            os.path.join(pkg, "etc"),
            os.path.join(pkg, "lib"),
        ]
        for path in expected:
            if not os.path.exists(path):
                raise ConanException(f"missing expected EMQX release path: {path}")

        if can_run(self):
            script = os.path.join(self.source_folder, "test_emqx.sh")
            self.run(f'bash "{script}" "{pkg}"', env="conanrun")
