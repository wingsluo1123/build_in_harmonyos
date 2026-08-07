#!/usr/bin/env python3
"""Conan recipe for postgresql-url_encode — PostgreSQL URL encoding extension.

Build system: PGXS (PostgreSQL Extension Build System)
Uses pg_config from the postgresql dependency to compile the extension.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class PostgresqlUrlEncodeConan(ConanFile):
    name = "postgresql-url_encode"
    version = "1.2.3"
    description = "URL encoding and decoding functions for PostgreSQL"
    license = "PostgreSQL"
    homepage = "https://api.pgxn.org/dist/url_encode/"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # PGXS needs make to run from source root, so build = source
        self.folders.source = "."
        self.folders.build = "."

    def requirements(self):
        self.requires("postgresql/18.3")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # PGXN zip has double nesting (url_encode-1.2.3/url_encode-1.2.3/)
        # Move inner directory contents up to source root
        inner = os.path.join(self.source_folder, "url_encode-1.2.3")
        if os.path.isdir(inner):
            for item in os.listdir(inner):
                src = os.path.join(inner, item)
                dst = os.path.join(self.source_folder, item)
                if os.path.exists(dst):
                    shutil.rmtree(dst) if os.path.isdir(dst) else os.remove(dst)
                shutil.move(src, dst)
            os.rmdir(inner)

    def build(self):
        apply_conandata_patches(self)

        # PGXS build: use pg_config from the postgresql dependency
        pg_config = self._get_pg_config()
        self.run(f'make USE_PGXS=1 PG_CONFIG="{pg_config}"', env="conanbuild")

    def package(self):
        # Extension .so goes to lib/postgresql/
        copy(self, "url_encode.so",
             src=os.path.join(self.build_folder, "src"),
             dst=os.path.join(self.package_folder, "lib", "postgresql"))
        # SQL files go to share/postgresql/extension/
        copy(self, "url_encode--*.sql",
             src=os.path.join(self.build_folder, "sql"),
             dst=os.path.join(self.package_folder, "share", "postgresql", "extension"))
        # Control file goes to share/postgresql/extension/
        copy(self, "url_encode.control",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "postgresql", "extension"))

    def package_info(self):
        self.cpp_info.libs = ["url_encode"]
        self.cpp_info.libdirs = ["lib/postgresql"]
        self.cpp_info.resdirs = ["share/postgresql/extension"]

    def _get_pg_config(self):
        """Find pg_config from the postgresql dependency or system PATH."""
        # Try postgresql dependency first
        try:
            dep = self.dependencies["postgresql"]
            for bindir in dep.cpp_info.bindirs:
                candidate = os.path.join(bindir, "pg_config")
                if os.path.isfile(candidate):
                    return candidate
        except (KeyError, AttributeError):
            pass
        # Fall back to system PATH
        pg_config = shutil.which("pg_config")
        if pg_config:
            return pg_config
        raise RuntimeError("pg_config not found. Install postgresql or add it as a Conan dependency.")
