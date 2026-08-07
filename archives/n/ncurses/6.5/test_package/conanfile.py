#!/usr/bin/env python3
"""ncurses/6.5 test_package — Conan L1 官方测试 (R34: 实质调用 ncurses API)."""
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
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_ncurses")
        if os.path.exists(bin_path):
            self.run(bin_path, env="conanrun")
        else:
            cmake = CMake(self)
            cmake.test()
