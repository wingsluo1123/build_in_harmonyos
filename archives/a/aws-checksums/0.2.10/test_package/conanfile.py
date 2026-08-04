#!/usr/bin/env python3
"""Test package for aws-checksums 0.2.10 — verifies CRC32/CRC32C/CRC64 API calls."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class AwsChecksumsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmd = f"{self.build_folder}/test_aws_checksums"
        self.run(cmd, env="conanrun")
