#!/usr/bin/env python3
"""Conan test_package — postgresql-orafce 4.16.0

Tests that orafce.so is a valid ELF shared library for AArch64.
Also verifies that extension control/SQL files are packaged correctly.

A full dlopen test is not possible because PostgreSQL extensions have
undefined symbols that are resolved by the PostgreSQL server at runtime.
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

        # Test 1: Verify orafce.so is a valid ELF shared library (C test)
        self.run(f'"{exe}" "{so_path}"', env="conanrun")

        # Test 2: Verify extension control file exists
        control_path = os.path.join(
            dep.package_folder, "share", "postgresql", "extension", "orafce.control")
        if not os.path.exists(control_path):
            raise AssertionError("orafce.control not found in package")

        # Test 3: Verify SQL definition file exists
        sql_path = os.path.join(
            dep.package_folder, "share", "postgresql", "extension", "orafce--4.16.sql")
        if not os.path.exists(sql_path):
            raise AssertionError("orafce--4.16.sql not found in package")

        # Test 4: Verify .so file size is reasonable (> 100KB)
        so_size = os.path.getsize(so_path)
        if so_size < 100000:
            raise AssertionError(f"orafce.so too small: {so_size} bytes")

        print("All postgresql-orafce package tests passed")
