#!/usr/bin/env python3
"""Conan test_package — bmake: verify the binary works."""
import os

from conan import ConanFile


class BmakeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find bmake binary path from the dependency
        bmake_dep = self.dependencies["bmake"]
        bmake_bin_dir = bmake_dep.cpp_info.bindirs[0]
        bmake_bin = os.path.join(bmake_bin_dir, "bmake")
        self.run(f"{bmake_bin} -r -V MAKE_VERSION")