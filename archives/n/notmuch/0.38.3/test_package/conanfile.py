#!/usr/bin/env python3
"""Conan test_package for notmuch 0.38.3 — L1 official test.

CI runs this automatically via `conan create` (which invokes test_package).
File location: archives/n/notmuch/0.38.3/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NotmuchTestConan(ConanFile):
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
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_notmuch")
        self.run(test_bin, env="conanrun")
