#!/usr/bin/env python3
"""Consumer test for klystrack 0.20171212 — verify binary works."""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy


class KlystrackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Copy test source to build folder
        copy(self, "test.c", src=self.source_folder, dst=self.build_folder)

    def generate(self):
        # Minimal CMakeLists for test binary
        with open(os.path.join(self.build_folder, "CMakeLists.txt"), "w") as f:
            f.write("""cmake_minimum_required(VERSION 3.5)
project(test_klystrack C)
add_executable(test_klystrack test.c)
""")

    def test(self):
        # Build and run test binary
        self.run("cmake . -DCMAKE_BUILD_TYPE=Release", cwd=self.build_folder)
        self.run("cmake --build . --config Release", cwd=self.build_folder)
        if can_run(self):
            self.run("./test_klystrack", cwd=self.build_folder, env=["PATH=" + os.path.join(self.dependencies["klystrack"].package_folder, "bin") + os.pathsep + os.environ.get("PATH", "")])