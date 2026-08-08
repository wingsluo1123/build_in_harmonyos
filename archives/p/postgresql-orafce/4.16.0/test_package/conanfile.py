#!/usr/bin/env python3
"""Conan test_package — postgresql-orafce 4.16.0

Verifies that orafce.so is a valid ELF shared library with the expected
PostgreSQL extension entry-point symbols. Since orafce.so depends on
PostgreSQL server symbols that are only available when loaded by a running
PostgreSQL server, we cannot dlopen it in the test environment. Instead:
  1. The C test program reads the ELF header to verify format validity
  2. nm -D checks for exported symbols (_PG_init, Pg_magic_func)
  3. Extension control and SQL files are verified to exist
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
        exe = os.path.join(self.cpp.build.bindirs[0], "test_orafce")
        dep = self.dependencies["postgresql-orafce"]
        so_path = os.path.join(dep.package_folder, "lib", "postgresql", "orafce.so")

        # Test 1: Verify orafce.so is a valid ELF shared library
        self.run(f"{exe} {so_path}", env="conanrun")

        # Test 2: Verify expected PostgreSQL extension symbols are exported
        self.run(f"nm -D {so_path} | grep -q _PG_init", env="conanrun")
        self.run(f"nm -D {so_path} | grep -q Pg_magic_func", env="conanrun")

        # Test 3: Verify extension control and SQL files exist
        ext_dir = os.path.join(dep.package_folder, "share", "postgresql", "extension")
        self.run(f"test -f {ext_dir}/orafce.control", env="conanrun")
        self.run(f"test -f {ext_dir}/orafce--4.16.sql", env="conanrun")
