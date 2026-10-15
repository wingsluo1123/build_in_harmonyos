#!/usr/bin/env python3
"""Conan test_package for pbbam 2.4.0 — Conan L1 official test.

Builds test_pbbam with CMake and runs it. The test binary exercises
real pbbam APIs (LibraryVersionString + FastaSequence) and prints
HMBS_TEST_PACKAGE_RESULT itself with self-counted results.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PbbamTestConan(ConanFile):
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
        if can_run(self):
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            self.run("{} -c './test_pbbam'".format(bash), env="conanrun")
