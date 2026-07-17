#!/usr/bin/env python3
"""Conan test_package — COIN-OR CoinUtils.

Tests that CoinPackedVector can be created, elements inserted, and
values retrieved. This substantively depends on the coinutils library.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CoinutilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Override compiler paths: profile may point to paths that don't
        # exist on all machines. Append overrides to conan_toolchain.cmake.
        clang = shutil.which("clang") or "clang"
        clangxx = shutil.which("clang++") or "clang++"
        conan_toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.exists(conan_toolchain):
            with open(conan_toolchain, "a") as f:
                f.write(f'\nset(CMAKE_C_COMPILER "{clang}")\n')
                f.write(f'\nset(CMAKE_CXX_COMPILER "{clangxx}")\n')
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_coinutils")
        self.run(cmd, env="conanrun")
