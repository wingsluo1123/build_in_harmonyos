#!/usr/bin/env python3
"""Conan test_package for xmlrpc-c — verifies the core XML-RPC API.

This is the L1 test: build a simple program that calls xmlrpc-c's API
and verify it links and runs correctly.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class XmlrpcCTestConan(ConanFile):
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
        # Run the test binary directly to verify the xmlrpc-c API works
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_xmlrpc_c"),
            env="conanrun",
        )
