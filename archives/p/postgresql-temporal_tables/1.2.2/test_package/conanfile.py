#!/usr/bin/env python3
"""Conan test_package for postgresql-temporal_tables 1.2.2.

Verifies that the packaged PostgreSQL extension shared library:
1. Exists in the package output as a valid ELF shared object
2. Exports expected PostgreSQL extension symbols (Pg_magic_func, versioning, _PG_init)

Note: PostgreSQL extensions cannot be dlopen'd outside a PostgreSQL server
context because their symbols (palloc0, SPI_connect, etc.) are resolved by
the server at load time. This test uses ELF inspection and nm to verify
the package contents without requiring a running PostgreSQL server.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class PostgresqlTemporalTablesTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _find_lib(self):
        """Find temporal_tables.so in the package output."""
        # Check dependency cpp_info libdirs (resolve relative to package folder)
        for dep in self.dependencies.values():
            pkg_folder = str(dep.package_folder) if dep.package_folder else ""
            for libdir in getattr(dep.cpp_info, "libdirs", []):
                libdir = str(libdir)
                # Resolve relative libdir against package folder
                if not os.path.isabs(libdir) and pkg_folder:
                    libdir = os.path.join(pkg_folder, libdir)
                candidate = os.path.join(libdir, "temporal_tables.so")
                if os.path.isfile(candidate):
                    return candidate
        return None

    def build(self):
        lib_path = self._find_lib()
        if not lib_path:
            raise RuntimeError("temporal_tables.so not found in package output")
        cmake = CMake(self)
        cmake.configure(variables={"TEMPORAL_TABLES_LIB_PATH": lib_path})
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # Verify the test binary exists and is executable
        test_bin = os.path.join(self.build_folder, "test_temporal_tables")
        self.run(f'test -x "{test_bin}"', env="conanrun")
