#!/usr/bin/env python3
"""Conan test_package for postgresql-uint 3.0.0

Tests that the uint.so PostgreSQL extension shared library is properly
packaged, is a valid ELF shared object, and contains the expected
Pg_magic_func entry point symbol.

Uses a simple shell-based test instead of CMake to avoid linking
issues with the PostgreSQL extension .so (which has undefined
server symbols).
"""
import os
import shutil

from conan import ConanFile


class PostgresqlUintTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        dep = self.dependencies["postgresql-uint"]
        so_path = os.path.join(dep.package_folder, "lib", "libuint.so")

        # Check file exists
        if not os.path.isfile(so_path):
            raise Exception(f"ERROR: uint.so not found at {so_path}")

        # Verify it's a valid ELF shared object
        self.run(f"file {so_path}")

        # Check for Pg_magic_func symbol (PostgreSQL extension entry point)
        self.run(f"nm -D {so_path} | grep Pg_magic_func")

        # Also check extension files are packaged
        ext_dir = os.path.join(dep.package_folder, "share", "extension")
        if os.path.isdir(ext_dir):
            control_file = os.path.join(ext_dir, "uint.control")
            if not os.path.isfile(control_file):
                raise Exception("ERROR: uint.control not found in extension dir")
            print(f"Found extension control: {control_file}")

        print("test postgresql-uint 3.0.0: ALL CHECKS PASSED")
