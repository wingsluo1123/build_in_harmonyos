#!/usr/bin/env python3
"""Conan test_package — libzmf 0.0.2 L1 test.

CI runs this automatically via `conan create` (which invokes test_package).
The test links against libzmf-0.0 and calls the public ZMF parser API to
verify the package is functional (R34: test must substantively depend on
the tested package).
"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibzmfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Fix: profile sets generator=Make, but CMake needs "Unix Makefiles"
        tc.generator = "Unix Makefiles"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
