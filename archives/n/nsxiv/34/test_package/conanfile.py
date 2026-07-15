#!/usr/bin/env python3
"""Conan test_package — nsxiv 34

Compiles a test program that verifies the nsxiv binary exists and is a
valid ELF executable. Also attempts to run nsxiv -v for runtime check.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class NsxivTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Set NSXIV_BIN environment variable for CTest
        bin_dir = self.dependencies["nsxiv"].cpp_info.bindirs[0]
        nsxiv_bin = os.path.join(bin_dir, "nsxiv")
        env = os.environ.copy()
        env["NSXIV_BIN"] = nsxiv_bin
        import json
        with open(os.path.join(self.build_folder, "env.json"), "w") as f:
            json.dump(env, f)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        # Set NSXIV_BIN for the test
        bin_dir = self.dependencies["nsxiv"].cpp_info.bindirs[0]
        nsxiv_bin = os.path.join(bin_dir, "nsxiv")
        os.environ["NSXIV_BIN"] = nsxiv_bin
        cmake.test()
