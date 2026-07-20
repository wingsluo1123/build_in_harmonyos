"""Conan test_package for fwupd 2.1.6

CI runs this automatically via `conan create`.
R34: Test must call actual fwupd API (done in test.c).
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FwupdTestConan(ConanFile):
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
        # R34: Run the test binary that calls fwupd API
        cmake = CMake(self)
        cmake.test()
