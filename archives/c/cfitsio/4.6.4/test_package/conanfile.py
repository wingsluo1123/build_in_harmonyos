#!/usr/bin/env python3
"""Conan test_package for cfitsio 4.6.4.

Consumer-side functional smoke test (L1). Builds test.c, which exercises the
real cfitsio API (fits_create_file, fits_create_img, fits_write_key_*,
fits_open_file, fits_read_key_*, ffvers) and asserts a write→reopen→read
round-trip. Run via `conan create` (which invokes test_package automatically).
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CfitsioTestConan(ConanFile):
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
        cmake = CMake(self)
        # Run the registered CTest case, which executes test_cfitsio and
        # checks its exit code. Falls back to a direct run if ctest is absent.
        cmake.test()
