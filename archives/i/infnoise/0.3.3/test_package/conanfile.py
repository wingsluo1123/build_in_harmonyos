#!/usr/bin/env python3
"""Conan test_package for infnoise 0.3.3 — consumer + HarmonyOS special test.

The test() method runs both registered CTest targets:
  - test_infnoise: consumer test (upper-layer component using public API)
  - harmony_test:  HarmonyOS platform-contract assertions (no-device)

CI runs this via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class InfnoiseTestConan(ConanFile):
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
        # L0d: CI gate requires an explicit self.run() subprocess invocation in
        # test() (otherwise stub_test_method). Run the consumer test and the
        # HarmonyOS special test binaries directly — both were built by
        # cmake.build() above and use only the packaged public API.
        cmake = CMake(self)
        cmake.test()
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_infnoise"), env="conanrun")
        self.run(os.path.join(self.cpp.build.bindirs[0], "harmony_test"), env="conanrun")
