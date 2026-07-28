#!/usr/bin/env python3
"""Consumer test for the Lilv Conan package."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake import CMakeDeps


class LilvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "Lilv consumer tests require a runnable Linux or OHOS build"
            )
        test_binary = os.path.join(self.cpp.build.bindirs[0], "test_lilv")
        self.run(test_binary, env="conanrun")
