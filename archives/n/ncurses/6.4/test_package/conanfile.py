#!/usr/bin/env python3
"""Conan test_package — ncurses 6.4.

Compiles a small C program that uses ncurses to verify the
library is linkable and basic symbols are available.
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NcursesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_ncurses")
        self.run(f"{test_bin}", env="conanrun")