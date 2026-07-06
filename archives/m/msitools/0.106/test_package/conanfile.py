#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/{letter}/msitools/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MsitoolsTestConan(ConanFile):
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
        # Run the test binary with proper library path (both package deps and own libs)
        lib_dir = os.path.join(self.dependencies["msitools"].package_folder, "lib")
        old_ld = os.environ.get("LD_LIBRARY_PATH", "")
        new_ld = f"{lib_dir}:{old_ld}" if old_ld else lib_dir
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_msitools")
        self.run(f"LD_LIBRARY_PATH={new_ld} {bin_path}")
