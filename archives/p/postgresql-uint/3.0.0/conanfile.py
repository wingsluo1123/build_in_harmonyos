#!/usr/bin/env python3
"""Conan recipe for postgresql-uint 3.0.0

PostgreSQL unsigned integer type extension (uint1, uint2, uint4).
Uses PGXS (PostgreSQL Extension Building Infrastructure) for building.
Requires pg_config from a PostgreSQL installation.
"""
import os
import shutil
import subprocess
import glob

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PostgresqlUintConan(ConanFile):
    name = "postgresql-uint"
    version = "3.0.0"
    description = "PostgreSQL unsigned integer type extension - provides uint1, uint2, and uint4 data types"
    license = "PostgreSQL"
    homepage = "https://github.com/nad2000/postgresql-contrib-uint"
    url = ""  # CI fills this

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_pg_config(self):
        return os.environ.get("PG_CONFIG", "pg_config")

    def build(self):
        apply_conandata_patches(self)

        pg_config = self._get_pg_config()

        # Verify pg_config is available
        self.run(f"{pg_config} --version", env="conanbuild")

        # Build using PGXS - source is in self.source_folder
        # R9: Always use -j1
        self.run(f"make -C {self.source_folder} PG_CONFIG={pg_config} -j1", env="conanbuild")

    def package(self):
        pg_config = self._get_pg_config()
        pkgdir = self.package_folder

        # Install using DESTDIR - run from source folder
        self.run(f"make -C {self.source_folder} install DESTDIR={pkgdir} PG_CONFIG={pg_config}", env="conanbuild")

        # PGXS installs to <DESTDIR>/<prefix>/lib/postgresql/uint.so
        # and <DESTDIR>/<prefix>/share/postgresql/extension/*
        # Find uint.so anywhere in the package and move to lib/
        so_files = glob.glob(os.path.join(pkgdir, "**", "uint.so"), recursive=True)

        dst_lib = os.path.join(pkgdir, "lib")
        os.makedirs(dst_lib, exist_ok=True)

        for so_file in so_files:
            # Rename to libuint.so for standard conan library naming
            dst = os.path.join(dst_lib, "libuint.so")
            shutil.move(so_file, dst)

        # Find and move extension files (*.control, *.sql, *.out)
        for pattern in ["*.control", "*.sql", "*.out"]:
            ext_files = glob.glob(os.path.join(pkgdir, "**", pattern), recursive=True)
            dst_ext = os.path.join(pkgdir, "share", "extension")
            os.makedirs(dst_ext, exist_ok=True)
            for f in ext_files:
                dst = os.path.join(dst_ext, os.path.basename(f))
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(f, dst)

    def package_info(self):
        self.cpp_info.libs = ["uint"]
        self.cpp_info.includedirs = []
