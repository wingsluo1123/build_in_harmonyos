#!/usr/bin/env python3
"""Conan test_package — crypto-algorithms cfbde48414 (source redistribution).

The installed package ships headers + algorithm .c sources under include/;
the consumer compiles the .c file(s) it needs. This test compiles the
packaged sha256.c together with test.c (a real known-answer SHA-256 check,
R34) and runs it.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class CryptoalgorithmsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, build_folder="$TMP")

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.user_presets_path = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindir, "test_crypto-algorithms"),
                 env="conanrun")
