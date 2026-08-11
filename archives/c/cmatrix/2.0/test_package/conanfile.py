#!/usr/bin/env python3
"""Conan test_package for cmatrix 2.0 - binary smoke test.

Builds and runs test_cmatrix (test.c) which calls the cmatrix binary
via popen() to verify version output, usage, color validation, and
screensaver mode. R34: test substantively depends on the tested
package binary.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CmatrixTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["cmatrix"]
        cmatrix_bin = "cmatrix"
        for bindir in dep.cpp_info.bindirs:
            candidate = os.path.join(bindir, "cmatrix")
            if os.path.isfile(candidate):
                cmatrix_bin = candidate
                break

        os.environ["CMATRIX_BIN"] = cmatrix_bin

        test_bin = os.path.join(self.build_folder, "test_cmatrix")
        self.run(test_bin, env="conanrun")
