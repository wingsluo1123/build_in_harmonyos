#!/usr/bin/env python3
"""Conan test_package for clreflect 0.5.11 — real consumer test.

Consumer use-case (R34/PF3): a downstream C++ application that links the
installed clReflectCpp static library via its exported public headers and calls
a business-meaningful public API (clcpp::internal::HashNameString — the basis
of clReflect's constant-time, stringless type lookup) and observes its result.

The binary must exit 0 only if the hashes match the expected constants,
proving compile + link + run against the packaged library.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ClreflectTestConan(ConanFile):
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
        bin_dir = os.path.join(self.build_folder, self.cpp.build.bindirs[0] if hasattr(self.cpp, "build") else "")
        exe = os.path.join(self.build_folder, "test_consumer")
        if not os.path.exists(exe):
            # cmake_layout puts the binary under build/<config>/
            for root, _, files in os.walk(self.build_folder):
                if "test_consumer" in files:
                    exe = os.path.join(root, "test_consumer")
                    break
        self.run(exe, env="conanrun")
