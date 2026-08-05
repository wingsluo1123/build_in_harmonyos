#!/usr/bin/env python3
"""Conan test_package for aws-c-auth — verifies library initialization."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwscauthTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("aws-c-common/0.14.3")
        self.requires("aws-c-cal/0.9.15")
        self.requires("aws-c-sdkutils/0.2.7")
        self.requires("aws-c-io/0.27.5")
        self.requires("aws-c-http/0.11.0")
        self.requires("aws-c-compression/0.3.2")
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
        test_binary = os.path.join(self.cpp.build.bindir, "test_aws-c-auth")
        self.run(test_binary, env="conanrun")
