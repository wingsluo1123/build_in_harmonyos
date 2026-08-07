#!/usr/bin/env python3
"""Test package for postgresql-orafce 4.16.0

Tests that the orafce extension shared library is a valid ELF
and can be loaded with dlopen. Uses a C test program that links
against dl and checks for PostgreSQL extension symbols.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PostgresqlOrafceTestConan(ConanFile):
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
