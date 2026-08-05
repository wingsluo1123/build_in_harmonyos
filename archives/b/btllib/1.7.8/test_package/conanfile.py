#!/usr/bin/env python3
"""Conan test_package for btllib — L1 smoke test.

Tests that the btllib library can be linked against and its API used.
Uses CMake to build a simple C++ test that creates an NtHash object.
"""
import os
import subprocess

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
        # Locate libomp.so using the compiler's own search path
        cpp = "/data/service/hnp/bin/clang++"
        comp_exes = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(comp_exes, dict) and "cpp" in comp_exes:
            cpp = comp_exes["cpp"]
        try:
            result = subprocess.run(
                [cpp, "-print-file-name=libomp.so"],
                capture_output=True, text=True, timeout=10
            )
            libomp_path = result.stdout.strip()
            if libomp_path and libomp_path != "libomp.so":
                libomp_dir = os.path.dirname(os.path.abspath(libomp_path))
                current_ld = os.environ.get("LD_LIBRARY_PATH", "")
                os.environ["LD_LIBRARY_PATH"] = libomp_dir + ":" + current_ld
        except Exception:
            pass
        # Run the test binary directly
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_btllib"), env="conanrun")
