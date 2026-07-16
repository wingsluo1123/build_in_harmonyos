#!/usr/bin/env python3
"""Conan test_package — graphqlite SQLite extension smoke test.

Tests that the graphqlite.so extension library is loadable via dlopen.
"""
import os
from conan import ConanFile


class GraphqliteTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Build and run the test C program that uses dlopen to verify the .so
        lib_dir = os.path.join(self.dependencies["graphqlite"].package_folder, "lib")
        self.run(f"ls -la {lib_dir}/*.so", env="conanrun")
        # Verify the extension library exists
        so_path = os.path.join(lib_dir, "libgraphqlite.so")
        if not os.path.exists(so_path):
            so_path = os.path.join(lib_dir, "graphqlite.so")
        assert os.path.exists(so_path), f"graphqlite.so not found in {lib_dir}"
        # Compile a minimal test program that loads the .so via dlopen
        test_src = os.path.join(self.source_folder, "test.c")
        test_bin = os.path.join(self.build_folder, "test_graphqlite")
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")
        self.run(f"{cc} -o {test_bin} {test_src} -ldl", env="conanrun")
        self.run(test_bin, env="conanrun")