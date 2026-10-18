#!/usr/bin/env python3
"""Conan test_package — L1 consumer test for libvdeplug 4.0.1 on OHOS.

Runs the compiled consumer binary directly (self.run) so the test exercises
the real packaged library + plugin dlopen path instead of printing strings.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibvdeplugTestConan(ConanFile):
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
        # Real consumer execution: opens null:// via plugin dlopen, sends a
        # frame, checks descriptors, closes, and asserts failure on unknown
        # schemes (see test.c). rc != 0 fails the test.
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libvdeplug")
        self.run(f'"{bin_path}"', env="conanrun")
