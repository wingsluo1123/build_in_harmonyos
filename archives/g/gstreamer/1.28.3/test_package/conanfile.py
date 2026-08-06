#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/g/gstreamer/1.28.3/test_package/conanfile.py

Test: includes gst/gst.h and calls gst_init() to verify the library
links and initializes correctly.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GstreamerTestConan(ConanFile):
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
        import os
        exe = os.path.join(self.cpp.build.bindirs[0], "test_gstreamer")
        self.run(exe, env="conanrun")
