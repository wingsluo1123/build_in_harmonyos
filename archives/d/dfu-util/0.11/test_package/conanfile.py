#!/usr/bin/env python3
"""Conan test_package — dfu-util 0.11

Verifies the dfu-util package ships a runnable dfu-util executable.
The bundled test_package.c is a trivial placeholder compiled directly.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class DfuUtilTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Compile the trivial placeholder program directly with the host C compiler.
        cc = os.environ.get("CC", "cc")
        src = os.path.join(self.source_folder, "test_package.c")
        self.run(f'"{cc}" "{src}" -o test_dfu_util')

    def test(self):
        # Run the trivial placeholder binary when not cross-building.
        if not cross_building(self):
            self.run(os.path.join(self.build_folder, "test_dfu_util"))
        # Verify the shipped dfu-util executable runs and reports its version.
        self.run("dfu-util --version", env="conanrun")
