#!/usr/bin/env python3
"""Conan test_package — mariadb-connector-c 3.4.8.

Calls mysql_library_init/mysql_init/mysql_get_client_version to verify
that the library is correctly built and linkable.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MariadbConnectorCTestConan(ConanFile):
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
