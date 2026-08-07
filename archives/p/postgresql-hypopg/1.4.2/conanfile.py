#!/usr/bin/env python3
"""Conan recipe for postgresql-hypopg 1.4.2 — HypoPG.

HypoPG is a PostgreSQL extension that adds hypothetical indexes to PostgreSQL.
It uses PGXS (PostgreSQL Extension Build System) which requires pg_config from
a PostgreSQL installation.

Build: make PG_CONFIG=<path-to-pg_config>
Install: make install PG_CONFIG=<path-to-pg_config> DESTDIR=<staging>

The package provides:
  - hypopg.so (PostgreSQL extension shared library)
  - hypopg.control (extension control file)
  - hypopg--*.sql (version migration SQL files)
"""
from conan import ConanFile
from conan.tools.files import get
import os
import subprocess
import shutil
import glob


class PostgresqlHypopgConan(ConanFile):
    name = "postgresql-hypopg"
    version = "1.4.2"
    description = "PostgreSQL extension for hypothetical indexes"
    license = "PostgreSQL"
    homepage = "https://github.com/HypoPG/hypopg"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("postgresql/18.3")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_pg_config(self):
        """Get pg_config path from the PostgreSQL dependency."""
        pg_dep = self.dependencies["postgresql"]
        if pg_dep.cpp_info.bindirs:
            bin_dir = pg_dep.cpp_info.bindirs[0]
            pg_config = os.path.join(bin_dir, "pg_config")
            if os.path.exists(pg_config):
                return pg_config
        return "pg_config"

    def _get_pg_config_var(self, varname):
        """Get a pg_config variable value."""
        pg_config = self._get_pg_config()
        result = subprocess.run(
            [pg_config, f"--{varname}"],
            capture_output=True, text=True
        )
        return result.stdout.strip()

    def build(self):
        pg_config = self._get_pg_config()
        self.run(f'make PG_CONFIG="{pg_config}"')

    def package(self):
        pg_config = self._get_pg_config()
        # Install to staging using DESTDIR
        staging = os.path.join(self.build_folder, "staging")
        if os.path.exists(staging):
            shutil.rmtree(staging)

        self.run(f'make install PG_CONFIG="{pg_config}" DESTDIR="{staging}"')

        # Find and copy all installed files from staging
        for root, dirs, files in os.walk(staging):
            for f in files:
                src = os.path.join(root, f)
                rel = os.path.relpath(src, staging)
                # Remove the prefix part to get relative path
                # The staging structure is: staging/<prefix>/<rel_path>
                # We want to keep only the <rel_path> part
                parts = rel.split(os.sep)
                # Find where "lib" or "share" starts
                for i, part in enumerate(parts):
                    if part in ("lib", "share", "bin"):
                        rel_final = os.path.join(*parts[i:])
                        dst = os.path.join(self.package_folder, rel_final)
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                        break

    def package_info(self):
        self.cpp_info.libs = ["hypopg"]
        self.cpp_info.libdirs = ["lib/postgresql"]
