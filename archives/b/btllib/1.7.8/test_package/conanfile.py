#!/usr/bin/env python3
"""Conan test_package for btllib — L1 smoke test.

Tests that the btllib library can be linked against and its API used.
Uses CMake to build a simple C++ test that creates an NtHash object.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class BtllibTestConan(ConanFile):
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
        # Set LD_LIBRARY_PATH to include libomp.so location
        libomp_dir = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = libomp_dir + ":" + current_ld
        # Run the test binary directly
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_btllib"), env="conanrun")
