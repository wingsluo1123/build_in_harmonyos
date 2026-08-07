#!/usr/bin/env python3
"""Conan recipe for postgresql-orafce 4.16.0

PostgreSQL extension providing Oracle compatibility functions.
Built with PGXS (PostgreSQL Extension Building Infrastructure).
Requires pg_config from a system PostgreSQL installation.
"""
import os
import shutil
import glob
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class PostgresqlOrafceConan(ConanFile):
    name = "postgresql-orafce"
    version = "4.16.0"
    description = "Oracle compatibility functions for PostgreSQL"
    license = "PostgreSQL"
    homepage = "https://github.com/orafce/orafce"
    url = ""  # CI fills this

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_pg_config(self):
        """Find pg_config in PATH or common locations"""
        path = os.environ.get("PATH", "")
        # Check if pg_config is already in PATH
        result = shutil.which("pg_config", path=path)
        if result:
            return result
        # Check common locations
        home = os.environ.get("HOME", "")
        for p in [
            os.path.join(home, "usr", "local", "bin"),
            "/usr/local/bin",
            "/usr/bin",
            "/usr/pgsql-17/bin",
            "/usr/pgsql-16/bin",
        ]:
            candidate = os.path.join(p, "pg_config")
            if os.path.isfile(candidate):
                os.environ["PATH"] = p + os.pathsep + path
                return candidate
        return None

    def build(self):
        apply_conandata_patches(self)

        pg_config = self._find_pg_config()
        if not pg_config:
            raise Exception("pg_config not found - PostgreSQL development files required. "
                            "Install PostgreSQL or ensure pg_config is in PATH.")

        self.output.info(f"Using pg_config: {pg_config}")

        # PGXS build: make uses pg_config to find PostgreSQL build settings
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Find orafce.so - it should be in the source folder after make
        so_files = []
        for pattern in ["orafce.so", "**/orafce.so"]:
            so_files.extend(glob.glob(os.path.join(self.source_folder, pattern)))

        if not so_files:
            # Also check build folder
            for pattern in ["orafce.so", "**/orafce.so"]:
                so_files.extend(glob.glob(os.path.join(self.build_folder, pattern)))

        if so_files:
            dst_lib = os.path.join(self.package_folder, "lib", "postgresql")
            os.makedirs(dst_lib, exist_ok=True)
            shutil.copy2(so_files[0], os.path.join(dst_lib, "orafce.so"))
            self.output.info(f"Packaged orafce.so from: {so_files[0]}")

        # Copy .control file
        for pattern in ["orafce.control", "**/orafce.control"]:
            controls = glob.glob(os.path.join(self.source_folder, pattern))
            if controls:
                dst_ext = os.path.join(self.package_folder, "share", "postgresql", "extension")
                os.makedirs(dst_ext, exist_ok=True)
                shutil.copy2(controls[0], os.path.join(dst_ext, "orafce.control"))
                break

        # Copy SQL files (*.sql)
        dst_ext = os.path.join(self.package_folder, "share", "postgresql", "extension")
        os.makedirs(dst_ext, exist_ok=True)
        for sql_file in glob.glob(os.path.join(self.source_folder, "orafce--*.sql")):
            shutil.copy2(sql_file, os.path.join(dst_ext, os.path.basename(sql_file)))

        # Copy doc files
        dst_doc = os.path.join(self.package_folder, "share", "doc", "postgresql", "extension")
        os.makedirs(dst_doc, exist_ok=True)
        for doc_file in ["README.asciidoc", "COPYRIGHT.orafce", "INSTALL.orafce"]:
            doc_path = os.path.join(self.source_folder, doc_file)
            if os.path.isfile(doc_path):
                shutil.copy2(doc_path, os.path.join(dst_doc, doc_file))

    def package_info(self):
        # orafce is a PostgreSQL extension (.so loaded by PostgreSQL server)
        self.cpp_info.libs = ["orafce"]
        self.cpp_info.libdirs = ["lib/postgresql"]
