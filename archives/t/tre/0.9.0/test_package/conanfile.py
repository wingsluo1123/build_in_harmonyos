#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TRETestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

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
        cmake.test()
        # Explicit self.run for CI L0d — cmake.test() calls self.run
        # internally but CI grep checks source text for self.run
        self.run(os.path.join(self.build_folder, "test_tre"), env="conanrun")
