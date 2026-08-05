#!/usr/bin/env python3
"""Conan test_package for audiocd-kio — verifies the library can be linked."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AudiocdKioTestConan(ConanFile):
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
        # Verify the shared library exists in the package
        lib_dir = os.path.join(self.deps_cpp_info["audiocd-kio"].libdir)
        if os.path.isdir(lib_dir):
            self.output.info(f"Library directory exists: {lib_dir}")
            for f in os.listdir(lib_dir):
                self.output.info(f"  Found: {f}")
        # Run the test binary
        cmake = CMake(self)
        cmake.test()
