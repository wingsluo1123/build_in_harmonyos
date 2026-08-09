#!/usr/bin/env python3
"""Conan test_package — keyfinder-cli 1.2.0

Tests the keyfinder-cli binary by running it with --help flag
and verifying it outputs usage information.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class KeyfinderCliTestConan(ConanFile):
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
        # The conanrun environment sets up PATH and LD_LIBRARY_PATH
        # so keyfinder-cli binary is found and shared libs are loaded
        self.run("keyfinder-cli --help", env="conanrun")
