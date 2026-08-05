#!/usr/bin/env python3
"""Conan test_package — aws-c-http 0.11.0 (CMake).

L1 test: verifies aws-c-http library loads and API can be called.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwsCHttpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("aws-c-common/0.14.3")
        self.requires("aws-c-io/0.27.5")
        self.requires("aws-c-compression/0.3.2")
        self.requires("aws-c-cal/0.9.15")
        self.requires("aws-lc/5.4.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        test_binary = os.path.join(self.cpp.build.bindir, "test_aws_c_http")
        self.run(test_binary, env="conanrun")
