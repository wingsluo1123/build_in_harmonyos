#!/usr/bin/env python3
"""Installed-package API tests for libXaw 1.0.14 (libXaw6 + libXaw7)."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = (
    "libxaw7_widget_set_contract",
    "libxaw6_widget_set_contract",
)


class LibxawTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("libxaw target consumers are not runnable")
        for name in TEST_EXECUTABLES:
            executable = os.path.join(self.cpp.build.bindir, name)
            self.run(f'"{executable}"', env="conanrun")
