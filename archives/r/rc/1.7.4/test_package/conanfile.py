#!/usr/bin/env python3
"""Conan test_package — rc L1 test.

R34: test_package must make substantive use of the tested package's API.
rc is a command-line shell tool; this test compiles a C program that
invokes the rc binary and checks its output.
"""
import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class RcTestConan(ConanFile):
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
        if not can_run(self):
            self.output.info("Skipping test: cross-building build platform cannot run target binaries")
            return
        test_bin = os.path.join(self.cpp.build.bindir, "test_rc")
        rc_bin = os.path.join(self.dependencies["rc"].package_folder, "bin", "rc")
        self.run(f"{test_bin} {rc_bin}", env="conanrun")
