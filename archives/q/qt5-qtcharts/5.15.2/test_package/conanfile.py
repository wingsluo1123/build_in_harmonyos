#!/usr/bin/env python3
"""Conan test_package for qt5-qtcharts — verifies Qt5Charts library linkage."""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class Qt5QtchartsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindir, "qt5charts_test"), env="conanrun")
