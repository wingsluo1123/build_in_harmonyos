#!/usr/bin/env python3
"""Conan test_package for aws-c-compression 0.3.2 — Conan L1 official test."""
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class AwsccompressionTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        prefix_paths = [d.package_folder for d in self.dependencies.values() if hasattr(d, 'package_folder') and d.package_folder]
        vars_dict = {"CMAKE_PREFIX_PATH": ";".join(prefix_paths)} if prefix_paths else {}
        cmake.configure(variables=vars_dict)
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
