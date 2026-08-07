#!/usr/bin/env python3
"""Conan test_package for openimageio.

This test verifies that the OpenImageIO package provides usable headers and
libraries. It includes OpenImageIO headers and uses the OIIO API to create
an ImageSpec, exercising the library linkage.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class OpenImageIOTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        # R34: test must actually depend on the package
        self.requires(self.tested_reference_str)
        # OpenImageIO headers include <fmt/format.h> and <Imath/...> without prefix.
        # Add these deps explicitly so CMakeDeps generates their include dirs.
        self.requires("fmt/8.1.1")
        self.requires("imath/3.2.2")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("Cross-building: skip runtime test")
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_openimageio")
        self.run(test_bin, env="conanrun")
