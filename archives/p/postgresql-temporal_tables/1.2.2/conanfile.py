#!/usr/bin/env python3
"""Conan recipe for postgresql-temporal_tables 1.2.2.

PostgreSQL extension for system-period temporal tables (SQL:2011 standard).
Uses PGXS (PostgreSQL Extension Build Infrastructure) — no configure step.
If pg_config is not available, PostgreSQL is built from source as a build step.
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
        path = shutil.which("pg_config")
        if path and os.path.isfile(path):
            return path
        return None

    def _ensure_pg_config(self):
        """Ensure pg_config is available. Build PostgreSQL from source if needed."""
        pg_config = self._find_pg_config()
        if pg_config:
            return pg_config

        # Build PostgreSQL from source to get pg_config and headers
        pg_version = "18.3"
        pg_url = f"https://github.com/postgres/postgres/archive/refs/tags/REL_18_3.tar.gz"
        pg_dir = os.path.join(self.build_folder, "postgresql-build")
        pg_install = os.path.join(self.build_folder, "pg-install")

        self.output.info("pg_config not found, building PostgreSQL from source...")

        # Download PostgreSQL source
        get(self, pg_url, strip_root=True, destination=pg_dir)

        # Fix config.guess for HarmonyOS
        config_guess = os.path.join(pg_dir, "config", "config.guess")
        if os.path.isfile(config_guess):
            with open(config_guess, 'r') as f:
                content = f.read()
            if "HarmonyOS" not in content:
                # Add HarmonyOS detection
                content = content.replace(
                    "aarch64:Linux:*:*)",
                    "aarch64:HarmonyOS:*:*)\n\tGUESS=$UNAME_MACHINE-unknown-linux-ohos\n\t;;\n    aarch64:Linux:*:*)"
                )
                # Fix umask for hmdfs
                content = content.replace("umask 077", "umask 022")
                with open(config_guess, 'w') as f:
                    f.write(content)

        # Configure PostgreSQL (generates pg_config.h and Makefile.global)
        os.environ["TMPDIR"] = os.environ.get("TMPDIR", "/tmp")
        os.environ["CC"] = shutil.which("clang") or "clang"
        os.environ["SHELL"] = shutil.which("bash") or "/bin/sh"

        # Fix umask 077 -> 022 for hmdfs filesystem compatibility
        import glob as _glob
        for f in _glob.glob(os.path.join(pg_dir, "**", "configure"), recursive=True):
            with open(f, 'r') as fh:
                content = fh.read()
            content = content.replace("umask 077", "umask 022")
            with open(f, 'w') as fh:
                fh.write(content)

        build_dir = os.path.join(pg_dir, "build-ohos")
        os.makedirs(build_dir, exist_ok=True)

        self.run(
            f'umask 022 && ../configure --prefix="{pg_install}" '
            f'--without-icu --without-readline --without-zlib --without-openssl',
            cwd=build_dir
        )

        # Build minimal components: common, port, pg_config, headers, pgxs
        for target in ["src/common", "src/port", "src/bin/pg_config"]:
            self.run(f"make -C {target}", cwd=build_dir)

        # Install minimal PostgreSQL (pg_config, headers, pgxs)
        self.run("make -C src/bin/pg_config install", cwd=build_dir)
        self.run("make -C src/include install", cwd=build_dir)
        self.run("make -C src/common install", cwd=build_dir)
        self.run("make -C src/port install", cwd=build_dir)
        # Install PGXS makefiles
        self.run("make -C src/makefiles install", cwd=build_dir)

        pg_config_path = os.path.join(pg_install, "bin", "pg_config")
        if os.path.isfile(pg_config_path):
            self.output.info(f"PostgreSQL built, pg_config at {pg_config_path}")
            return pg_config_path

        raise RuntimeError("Failed to build pg_config from PostgreSQL source")

    def build(self):
        apply_conandata_patches(self)
        pg_config = self._ensure_pg_config()
        # PGXS builds in the source directory (GNUmakefile is there)
        self.run(f'make PG_CONFIG="{pg_config}"', cwd=self.source_folder)

    def package(self):
        pg_config = self._ensure_pg_config()
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
