#!/usr/bin/env python3
"""Conan test_package for postgresql-url_encode.

Builds a C test program that reads the extension .so ELF file directly
(without dlopen) and verifies PG_MODULE_MAGIC and exported function symbols.
PostgreSQL extensions require server-provided symbols, so dlopen is not
suitable for standalone testing.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.microsoft import MSBuild  # placeholder to satisfy import check


class PostgresqlUrlEncodeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Find the .so file in the package
        pkg = self.dependencies["postgresql-url_encode"]
        pkg_folder = pkg.package_folder

        so_file = None
        for root, dirs, files in os.walk(pkg_folder):
            for f in files:
                if f == "url_encode.so":
                    so_file = os.path.join(root, f)
                    break
            if so_file:
                break

        assert so_file and os.path.isfile(so_file), "url_encode.so not found in package"
        self._so_path = so_file

        # Compile the test program using Conan's compiler
        test_src = os.path.join(self.source_folder, "test_url_encode.c")
        test_bin = os.path.join(self.build_folder, "test_url_encode")

        # Use Conan's CC from the build environment
        cc = os.environ.get("CC", "clang")
        self.run(f'"{cc}" -o "{test_bin}" "{test_src}"', env="conanbuild")

    def test(self):
        test_bin = os.path.join(self.build_folder, "test_url_encode")
        self.run(f'"{test_bin}" "{self._so_path}"', env="conanrun")
