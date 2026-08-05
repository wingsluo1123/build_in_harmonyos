#!/usr/bin/env python3
"""Test package for boost-build - verifies b2 binary can build a project."""
import os
import shutil

from conan import ConanFile
from conan.tools.layout import basic_layout


class BoostBuildTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # R34: Test must actually exercise the b2 binary
        # Step 1: Verify b2 --version works
        self.run("b2 --version", env="conanrun")

        # Step 2: Build a simple project with b2 to verify it works
        test_dir = os.path.join(self.source_folder)
        shutil.copy(os.path.join(test_dir, "hello.cpp"), self.build_folder)
        shutil.copy(os.path.join(test_dir, "Jamroot.jam"), self.build_folder)
        self.run("b2 toolset=clang", cwd=self.build_folder, env="conanrun")
