#!/usr/bin/env python3
"""Conan recipe for postgresql-orafce 4.16.0

PostgreSQL extension providing Oracle compatibility functions.
Built with PGXS (PostgreSQL Extension Building Infrastructure).
Requires pg_config from a system PostgreSQL installation.
"""
import os
import shutil
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
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

    def _ensure_pg_config(self):
        """Ensure pg_config is in PATH"""
        if shutil.which("pg_config"):
            return
        home = os.environ.get("HOME", "")
        for p in [
            os.path.join(home, "usr", "local", "bin"),
            "/usr/local/bin",
            "/usr/bin",
        ]:
            if os.path.isfile(os.path.join(p, "pg_config")):
                os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
                return

    def build(self):
        apply_conandata_patches(self)

        # PGXS uses pg_config to find build settings (compiler, flags, include dirs)
        self._ensure_pg_config()

        # R9: Always use -j1
        # R32: Support both Linux and OHOS
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Copy built .so from source folder
        so_path = os.path.join(self.source_folder, "orafce.so")
        if os.path.isfile(so_path):
            dst_lib = os.path.join(self.package_folder, "lib", "postgresql")
            os.makedirs(dst_lib, exist_ok=True)
            shutil.copy2(so_path, os.path.join(dst_lib, "orafce.so"))

        # Copy .control file
        control_path = os.path.join(self.source_folder, "orafce.control")
        if os.path.isfile(control_path):
            dst_ext = os.path.join(self.package_folder, "share", "postgresql", "extension")
            os.makedirs(dst_ext, exist_ok=True)
            shutil.copy2(control_path, os.path.join(dst_ext, "orafce.control"))

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
