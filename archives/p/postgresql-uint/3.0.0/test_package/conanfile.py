#!/usr/bin/env python3
"""Conan test_package for postgresql-uint 3.0.0

Tests that the uint.so PostgreSQL extension shared library is properly
packaged, is a valid ELF shared object, and contains the expected
Pg_magic_func entry point symbol.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PostgresqlUintTestConan(ConanFile):
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
        # Set the package root so the C test can find the .so
        dep = self.dependencies["postgresql-uint"]
        os.environ["CONAN_PACKAGE_ROOT"] = dep.package_folder

        # Verify the .so is a valid ELF and contains expected symbols
        so_path = os.path.join(dep.package_folder, "lib", "libuint.so")
        if not os.path.isfile(so_path):
            raise Exception(f"ERROR: uint.so not found at {so_path}")
        self.run(f"file {so_path}")
        self.run(f"nm -D {so_path} | grep Pg_magic_func")

        # Run CMake test (reads .so and verifies ELF + Pg_magic_func)
        cmake = CMake(self)
        cmake.test()
