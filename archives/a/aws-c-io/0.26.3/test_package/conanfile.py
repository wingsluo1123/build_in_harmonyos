#!/usr/bin/env python3
"""Conan test_package for aws-c-io 0.26.3 — Conan L1 test."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwscioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("aws-c-common/0.12.6")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run(os.path.join(self.cpp.build.bindir, "test_aws-c-io"), env="conanrun")
