#!/usr/bin/env python3
"""Conan test_package for Boost 1.90.0.1 compiled components."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class BoostCompiledTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_boost_compiled") + " --name ohos --count 3", env="conanrun")
