#!/usr/bin/env python3
"""Conan test_package for postgresql-pllua.

Tests that the pllua shared library is a valid ELF file and can be loaded
with dlopen, checking for the _PG_init symbol (PostgreSQL extension entry point).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PostgresqlPlluaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Get the pllua.so path from the package folder
        dep = self.dependencies["postgresql-pllua"]
        so_path = os.path.join(dep.package_folder, "lib", "pllua.so")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_pllua")
        self.run(f'"{test_bin}" "{so_path}"', env="conanrun")
