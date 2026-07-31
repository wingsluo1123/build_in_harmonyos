#!/usr/bin/env python3
"""Conan test_package for libusb 1.0.27 — verify the installed library.

L1 smoke test: builds a small C consumer that links against the packaged
libusb-1.0 and calls libusb_get_version() to verify the library is
linkable and callable on OHOS.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibusbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            executable = os.path.join(self.cpp.build.bindirs[0], "test_package")
            self.run(executable, env="conanrun")
