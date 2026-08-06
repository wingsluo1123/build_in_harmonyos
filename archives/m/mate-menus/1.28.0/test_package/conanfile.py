#!/usr/bin/env python3
"""Conan test_package for mate-menus 1.28.0 — Conan L1 test.

This test verifies the mate-menus library is correctly built and linkable
by calling matemenu_tree_get_type() API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class MateMenusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly to verify the mate-menus library
        # is correctly linked and the API (matemenu_tree_get_type) works
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_mate_menus")
        self.run(test_bin, env="conanrun")
