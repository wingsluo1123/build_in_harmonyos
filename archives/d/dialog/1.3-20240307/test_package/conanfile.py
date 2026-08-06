#!/usr/bin/env python3
"""Conan test_package — dialog 1.3-20240307.

R34: test executes the dialog binary to verify functionality.
The test compiles test_dialog.c and runs `dialog --version`.
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class DialogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        pass

    def build(self):
        # Compile the test source file
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")
        src = os.path.join(self.source_folder, "test_dialog.c")
        out = os.path.join(self.build_folder, "test_dialog")
        self.run(f'{cc} -o "{out}" "{src}"')

    def test(self):
        # R34: Execute the dialog binary to verify the package works
        # dialog --version prints "Version: 1.3-20240307"
        bin_path = os.path.join(self.dependencies["dialog"].package_folder, "bin", "dialog")
        self.run(f'"{bin_path}" --version', env="conanrun")
        # Also run the compiled test binary
        test_bin = os.path.join(self.build_folder, "test_dialog")
        self.run(f'"{test_bin}"', env="conanrun")
