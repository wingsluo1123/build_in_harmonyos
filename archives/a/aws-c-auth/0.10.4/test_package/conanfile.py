#!/usr/bin/env python3
"""Conan test_package — aws-c-auth 0.10.4 (CMake).

L1 test: verifies aws-c-auth library loads and API can be called.

Note: aws-c-http (a transitive dependency) references aws_tls_handler_protocol
which is not compiled in aws-c-io (built with BYO_CRYPTO=ON). The test_package
provides a stub.c that defines this symbol, and uses --export-dynamic +
--allow-shlib-undefined to make it available for dynamic linking.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwsCauthTestConan(ConanFile):
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
        cmake = CMake(self)
        cmake.test()
        test_binary = os.path.join(self.cpp.build.bindir, "test_aws_c_auth")
        self.run(test_binary, env="conanrun")
