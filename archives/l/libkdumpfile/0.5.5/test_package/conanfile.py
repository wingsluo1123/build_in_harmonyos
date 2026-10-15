#!/usr/bin/env python3
"""libkdumpfile 0.5.5 test_package — Conan L1 consumer test.

Builds test_libkdumpfile (calls kdump_new/kdump_strerror/kdump_free and
addrxlat_ctx_new/addrxlat_ctx_decref) and runs it via CTest.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibkdumpfileTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        # Alternatively, run the binary directly:
        # self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_libkdumpfile')}", env="conanrun")
