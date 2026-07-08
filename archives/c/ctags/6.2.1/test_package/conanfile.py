#!/usr/bin/env python3
"""Conan test_package — ctags 6.2.1

L1 test: verify the ctags binary is installed and runnable.
ctags is a standalone CLI tool, not a library — we test by running --version.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CtagsTestConan(ConanFile):
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
        # Run the compiled test binary
        self.run(f"{os.path.join(self.cpp.build.bindirs[0], 'test_ctags')}", env="conanrun")
        # Also verify the ctags binary is installed and runnable
        ctags_bin = os.path.join(self.dependencies["ctags"].package_folder, "bin", "ctags")
        self.run(f'"{ctags_bin}" --version', env="conanrun")
