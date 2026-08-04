#!/usr/bin/env python3
"""Conan test_package for aws-c-cal 0.9.13.

Tests the aws-c-cal package by initializing and cleaning up the cal library.
aws-c-common is declared as a direct requirement so its headers are available
(the transitive include path is not always propagated by CMakeDeps).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class AwsccalTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Declare aws-c-common directly so CMakeDeps resolves its include dirs
        self.requires("aws-c-common/0.12.6")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
