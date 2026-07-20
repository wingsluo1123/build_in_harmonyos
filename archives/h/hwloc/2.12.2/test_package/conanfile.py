#!/usr/bin/env python3
"""Conan test_package for hwloc/2.12.2 — L1 official test.

R34: substantively depends on the tested package's API.
test.c calls hwloc_topology_init/load/get_depth/get_root_obj/destroy
to verify the library links and exports its core symbols.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class HwlocTestConan(ConanFile):
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
        # Run the test binary directly to verify hwloc API works
        bin_dir = os.path.join(self.cpp.build.bindirs[0]) if self.cpp.build.bindirs else self.build_folder
        self.run(f"{os.path.join(bin_dir, 'test_hwloc')}", env="conanrun")
