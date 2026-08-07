#!/usr/bin/env python3
"""Conan recipe — postgresql-orafce 4.16.0 (PGXS)

PostgreSQL extension providing Oracle compatibility functions.
Built using PGXS (PostgreSQL Extension Build Infrastructure).

Since PostgreSQL server development files (pg_config, server headers, PGXS)
are not available as a separate conan package, this recipe downloads PostgreSQL
18.1 source as the main source (so HarmonyOS patches apply via
apply_conandata_patches), builds the required dev files, then downloads
orafce source and builds it using PGXS.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PostgresqlOrafceConan(ConanFile):
    name = "postgresql-orafce"
    version = "4.16.0"
    description = "Oracle compatibility functions for PostgreSQL"
    license = "PostgreSQL"
    homepage = "https://github.com/orafce/orafce"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Download PostgreSQL source as main source (patches apply to it)
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download orafce source to subdirectory
        get(self, **self.conan_data["orafce_sources"], strip_root=True,
            destination=os.path.join(self.source_folder, "orafce"))

    def build(self):
        # Apply HarmonyOS patches (config.guess, config.sub) to PostgreSQL source
        apply_conandata_patches(self)

        pg_prefix = os.path.join(self.build_folder, "pg_prefix")

        # Fix configure: use TMPDIR instead of cwd, and umask 000 instead of 077
        # (HarmonyOS media filesystem: umask 077 strips group write permission,
        #  and /tmp may be read-only)
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        # Replace tmpdir creation to use $TMPDIR and umask 000
        text = text.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            '_tmp_dir="${TMPDIR:-$HOME/tmp}"\n  tmp=`(umask 000 && mktemp -d "$_tmp_dir/confXXXXXX") 2>/dev/null`'
        )
        text = text.replace(
            'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
            'tmp="$_tmp_dir/conf$$-$RANDOM"\n  (umask 000 && mkdir "$tmp")'
        )
        text = text.replace(
            'cannot create a temporary directory in .',
            'cannot create a temporary directory in $TMPDIR'
        )
        # Fix any remaining umask 077
        text = text.replace("umask 077", "umask 022")
        with open(configure_path, "w", encoding="utf-8") as f:
            f.write(text)

        # Configure PostgreSQL (minimal, no optional deps)
        self.run(
            f"cd {self.source_folder} && ./configure --prefix={pg_prefix} "
            f"--without-readline --without-zlib --without-icu "
            f"--without-openssl --without-libxml --without-gssapi "
            f"--without-pam --without-systemd --without-lz4 --without-zstd",
            env="conanbuild"
        )

        # Build pg_config and prerequisite libraries
        self.run(f"cd {self.source_folder} && make -C src/port -j1", env="conanbuild")
        self.run(f"cd {self.source_folder} && make -C src/common -j1", env="conanbuild")
        self.run(f"cd {self.source_folder} && make -C src/bin/pg_config -j1", env="conanbuild")

        # Install pg_config, server headers, and PGXS infrastructure
        self.run(f"cd {self.source_folder} && make -C src/bin/pg_config install", env="conanbuild")
        self.run(f"cd {self.source_folder} && make -C src/include install", env="conanbuild")
        self.run(f"cd {self.source_folder} && make -C src/makefiles install", env="conanbuild")
        self.run(f"cd {self.source_folder} && make -C config install", env="conanbuild")
        self.run(f"cd {self.source_folder} && make -C src/port install", env="conanbuild")

        # Install Makefile.global and support files for PGXS
        # Makefile.port is a symlink created by configure (→ Makefile.linux),
        # shutil.copy2 follows symlinks to copy the actual file content
        pgxs_dir = os.path.join(pg_prefix, "lib", "postgresql", "pgxs", "src")
        os.makedirs(pgxs_dir, exist_ok=True)
        for fname in ["Makefile.global", "Makefile.port", "Makefile.shlib", "nls.mk"]:
            src_file = os.path.join(self.source_folder, "src", fname)
            dst_file = os.path.join(pgxs_dir, fname)
            if os.path.islink(src_file) or os.path.isfile(src_file):
                shutil.copy2(src_file, dst_file)
            elif fname == "Makefile.port":
                # Fallback: Makefile.port symlink not created, use Makefile.linux
                linux_mk = os.path.join(self.source_folder, "src", "makefiles", "Makefile.linux")
                if os.path.exists(linux_mk):
                    shutil.copy2(linux_mk, dst_file)

        # Install postgres_ext.h and pg_config_ext.h
        inc_dir = os.path.join(pg_prefix, "include")
        for fname in ["postgres_ext.h", "pg_config_ext.h"]:
            src_file = os.path.join(self.source_folder, "src", "include", fname)
            if os.path.exists(src_file):
                copy(self, fname, os.path.dirname(src_file), inc_dir)

        # Build orafce using PGXS
        orafce_dir = os.path.join(self.source_folder, "orafce")
        pg_config_bin = os.path.join(pg_prefix, "bin", "pg_config")
        self.run(
            f"cd {orafce_dir} && make PG_CONFIG={pg_config_bin}",
            env="conanbuild"
        )

    def package(self):
        orafce_dir = os.path.join(self.source_folder, "orafce")
        # Copy orafce.so (shared library)
        copy(self, "orafce.so", orafce_dir,
             os.path.join(self.package_folder, "lib", "postgresql"))
        # Copy extension control and SQL files
        copy(self, "orafce.control", orafce_dir,
             os.path.join(self.package_folder, "share", "postgresql", "extension"))
        copy(self, "orafce--*.sql", orafce_dir,
             os.path.join(self.package_folder, "share", "postgresql", "extension"))
        # Copy documentation
        for doc_file in ["README.asciidoc", "COPYRIGHT.orafce", "INSTALL.orafce"]:
            copy(self, doc_file, orafce_dir,
                 os.path.join(self.package_folder, "share", "doc", "postgresql", "extension"))

    def package_info(self):
        self.cpp_info.libs = ["orafce"]
        self.cpp_info.libdirs = ["lib/postgresql"]
        self.cpp_info.set_property("cmake_file_name", "postgresql-orafce")
        self.cpp_info.set_property("cmake_target_name", "postgresql-orafce::orafce")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
