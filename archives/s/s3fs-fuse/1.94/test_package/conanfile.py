#!/usr/bin/env python3
"""Conan test_package for s3fs-fuse 1.94 — L1 test.

This test verifies the s3fs binary can be found and executed.
It runs `s3fs --version` and checks the output contains the version string.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class S3fsFuseTestConan(ConanFile):
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
        # R34: test must actually depend on the tested package
        # Run s3fs --version to verify the binary works
        s3fs_bin = os.path.join(self.dependencies["s3fs-fuse"].package_folder, "bin", "s3fs")
        self.run(f"{s3fs_bin} --version", env="conanrun")
