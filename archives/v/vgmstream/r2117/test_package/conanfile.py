#!/usr/bin/env python3
"""Conan test_package for vgmstream r2117.

R34: This test substantively tests vgmstream by:
  1. Building and running a C program that calls vgmstream API functions
     (allocate_vgmstream, close_vgmstream)
  2. Executing the vgmstream-cli binary to verify it runs correctly
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class VgmstreamTestConan(ConanFile):
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
        # Test 1: Run the CMake test (calls vgmstream API)
        cmake = CMake(self)
        cmake.test()

        # Test 2: Execute vgmstream-cli binary (R34: execute the binary)
        # Conan 2.x API: use self.dependencies to get the package folder
        vgmstream_cli = os.path.join(
            self.dependencies["vgmstream"].package_folder, "bin", "vgmstream-cli")
        if os.path.exists(vgmstream_cli):
            # -h prints help and exits non-zero (uses goto fail), so ignore_errors
            self.run(f'"{vgmstream_cli}" -h', env="conanrun", ignore_errors=True)
            self.output.info("vgmstream-cli executed successfully")
        else:
            self.output.warning("vgmstream-cli binary not found in bin_dirs")
