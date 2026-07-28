#!/usr/bin/env python3
"""Conan test_package for Decker — verifies lilt binary runs correctly.

Tests that the lilt standalone interpreter binary was properly installed
and can execute a basic Lil script.

Path resolution: decker is an application package (cpp_info.bindirs=["bin"]).
We pass the bindir to CMake in two complementary ways:
  1. CMakeToolchain defines `DECKER_BIN_DIRS` (from cpp_info.bindirs) so
     CMakeLists.txt can bake LILT_DEFAULT_BIN into the test binary.
  2. At test() time we set the LILT_BIN environment variable so the test
     binary can also read it at runtime (belt-and-suspenders).
"""
import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class DeckerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Hand the decker bindir to CMake as a plain variable so CMakeLists.txt
        # can turn it into the LILT_DEFAULT_BIN compile-time macro.
        decker = self.dependencies["decker"]
        bin_dirs = decker.cpp_info.aggregated_components().bindirs
        if bin_dirs:
            tc = CMakeToolchain(self)
            tc.variables["DECKER_BIN_DIRS"] = bin_dirs[0]
            tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Resolve the installed lilt binary and pass it to CTest via LILT_BIN.
        decker = self.dependencies["decker"]
        bin_dirs = decker.cpp_info.aggregated_components().bindirs
        lilt_path = os.path.join(bin_dirs[0], "lilt") if bin_dirs else "lilt"

        env_vars = {"LILT_BIN": lilt_path}
        cmake = CMake(self)
        cmake.test(env=env_vars)
