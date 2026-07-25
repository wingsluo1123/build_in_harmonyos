#!/usr/bin/env python3
"""Conan test_package for PDAL — L1 official test.

Verifies that the PDAL library can be linked and the test binary builds and runs.
On HarmonyOS, shared libraries need to be in the same directory as the binary
due to musl dynamic linker limitations (E088).
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import copy


class PdalTestConan(ConanFile):
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
        # Copy PDAL shared library next to test binary (HarmonyOS musl workaround)
        for dep in self.dependencies.values():
            if dep.ref.name == "pdal":
                libdir = dep.cpp_info.libdir
                copy(self, "*.so*", libdir, self.cpp.build.bindirs[0])

    def test(self):
        # Run the test binary to verify PDAL library linkage
        binary = os.path.join(self.cpp.build.bindirs[0], "test_pdal")
        self.run(binary, env="conanrun")
