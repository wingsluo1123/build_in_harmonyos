#!/usr/bin/env python3
"""Conan recipe for postgresql-temporal_tables 1.2.2.

PostgreSQL extension for system-period temporal tables (SQL:2011 standard).
Uses PGXS (PostgreSQL Extension Build Infrastructure) — no configure step.
Requires pg_config from a system or Conan-managed PostgreSQL installation.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PostgresqlTemporalTablesConan(ConanFile):
    name = "postgresql-temporal_tables"
    version = "1.2.2"
    description = "PostgreSQL extension for system-period temporal tables (SQL:2011 standard)"
    license = "PostgreSQL"
    homepage = "https://github.com/arkhipov/temporal_tables"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_pg_config(self):
        """Find pg_config binary from PATH or PG_CONFIG env var."""
        pg_config = os.environ.get("PG_CONFIG")
        if pg_config and os.path.isfile(pg_config):
            return pg_config
        # Try pg_config from PATH
        path = shutil.which("pg_config")
        if path and os.path.isfile(path):
            return path
        raise RuntimeError(
            "pg_config not found. Install PostgreSQL or set PG_CONFIG env var."
        )

    def build(self):
        apply_conandata_patches(self)
        pg_config = self._find_pg_config()
        # PGXS builds in the source directory (GNUmakefile is there)
        self.run(f'make PG_CONFIG="{pg_config}"', cwd=self.source_folder)

    def package(self):
        pg_config = self._find_pg_config()
        # PGXS install with DESTDIR puts files under $DESTDIR/$PREFIX/...
        self.run(
            f'make install PG_CONFIG="{pg_config}" DESTDIR="{self.package_folder}"',
            cwd=self.source_folder,
        )

    def package_info(self):
        # The shared library is installed to lib/postgresql/
        self.cpp_info.libs = ["temporal_tables"]
        self.cpp_info.libdirs = ["lib/postgresql", "lib"]
        # Extension control and SQL files are in share/postgresql/extension/
        self.cpp_info.resdirs = ["share/postgresql/extension"]
        # Set CMake-friendly names (hyphens are not valid in CMake target names)
        self.cpp_info.set_property("cmake_file_name", "postgresql_temporal_tables")
        self.cpp_info.set_property("cmake_target_name", "postgresql_temporal_tables::postgresql_temporal_tables")
