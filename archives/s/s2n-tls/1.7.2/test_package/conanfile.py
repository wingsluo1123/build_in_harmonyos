#!/usr/bin/env python3
"""Conan test_package for s2n-tls — verifies library links and initializes correctly."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class S2nTlsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        # s2n-config.cmake calls find_dependency(crypto) which needs
        # crypto-config.cmake with AWS::crypto target
        deps = CMakeDeps(self)
        deps.set_property("openssl", "cmake_file_name", "crypto")
        deps.set_property("openssl", "cmake_target_name", "AWS::crypto")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # R34: explicitly run the binary to prove real API linkage
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_s2n"), env="conanrun")
