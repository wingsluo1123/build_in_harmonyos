#!/usr/bin/env python3
"""Conan consumer test for libmaxminddb 1.11.0."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibmaxminddbTestConan(ConanFile):
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
        if can_run(self):
            binary = os.path.join(
                self.cpp.build.bindirs[0], "test_libmaxminddb"
            )
            self.run(binary, env="conanrun", cwd=self.build_folder)
