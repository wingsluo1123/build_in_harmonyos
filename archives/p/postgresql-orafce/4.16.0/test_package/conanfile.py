#!/usr/bin/env python3
"""Test package for postgresql-orafce 4.16.0

Tests that the orafce extension shared library is a valid ELF
and can be loaded with dlopen. Compiles test.c directly without CMake.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class PostgresqlOrafceTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Compile test.c directly - no CMake needed
        cc = "clang"
        test_src = os.path.join(self.source_folder, "test.c")
        test_bin = os.path.join(self.build_folder, "test_postgresql_orafce")
        self.run(f'{cc} -o "{test_bin}" "{test_src}" -ldl')

    def test(self):
        # Get the path to orafce.so from the package
        dep = self.dependencies["postgresql-orafce"]
        pkg_folder = dep.package_folder
        so_path = os.path.join(pkg_folder, "lib", "postgresql", "orafce.so")

        # Verify the .so file exists
        assert os.path.isfile(so_path), f"orafce.so not found at {so_path}"

        # Run the test binary with the .so path as argument
        test_bin = os.path.join(self.build_folder, "test_postgresql_orafce")
        self.run(f'"{test_bin}" "{so_path}"')
