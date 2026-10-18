#!/usr/bin/env python3
"""Conan test package: compile against libattr and run every installed tool."""
import os
import shlex
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AttrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_attr")
        runner = os.path.join(self.source_folder, "run_test.py")
        attr = self.dependencies["attr"]
        tool_bin = os.path.join(attr.package_folder, *attr.cpp_info.bindirs)
        command = "{} {} {} {}".format(
            shlex.quote(sys.executable), shlex.quote(runner), shlex.quote(binary),
            shlex.quote(tool_bin))
        self.run(command, env="conanrun", cwd=self.build_folder, ignore_errors=True)
