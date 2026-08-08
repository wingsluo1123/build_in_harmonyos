#!/usr/bin/env python3
"""Conan recipe for postgresql-shared_ispell — PostgreSQL shared ispell dictionary extension.

Package version 1.1.0 = upstream PGXN 1.0.0 source + 9.6-update branch code
+ PostgreSQL 18 API compatibility fixes (FALSE→false, lowerstr→str_tolower,
reg.regex→reg.pregex). The source is downloaded from PGXN 1.0.0 release and
patches are applied to bring it to the 9.6-update + PG18 compatible version.

This extension uses PGXS (PostgreSQL Extension Build System) which requires
pg_config and server headers. Since postgresql/18.3 is not in the conan remote,
this recipe builds PostgreSQL 18.3 from source with OHOS harmony patches, then
builds the shared_ispell extension using PGXS.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PostgresqlSharedIspellConan(ConanFile):
    name = "postgresql-shared_ispell"
    version = "1.1.0"
    description = "PostgreSQL shared ispell dictionary extension"
    license = "PostgreSQL"
    homepage = "https://github.com/tvondra/shared_ispell"
    url = "https://github.com/tvondra/shared_ispell"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # PostgreSQL source (not in conan remote, built from source)
    PG_VERSION = "18.3"
    PG_SOURCE_URL = "https://mirrors.aliyun.com/postgresql/source/v18.3/postgresql-18.3.tar.bz2"
    PG_SOURCE_SHA256 = "d95663fbbf3a80f81a9d98d895266bdcb74ba274bcc04ef6d76630a72dee016f"

    def export_sources(self):
        export_conandata_patches(self)
        # Also manually copy patches directory (fallback if export_conandata_patches fails)
        recipe_dir = self.recipe_folder if hasattr(self, 'recipe_folder') and self.recipe_folder else os.path.dirname(os.path.abspath(__file__))
        patches_dir = os.path.join(recipe_dir, "patches")
        if os.path.isdir(patches_dir) and hasattr(self, 'export_folder') and self.export_folder:
            copy(self, "*.patch", patches_dir, os.path.join(self.export_folder, "patches"))
            copy(self, "*", os.path.join(patches_dir, "9.6-update"), os.path.join(self.export_folder, "patches", "9.6-update"))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        src_dir = self.source_folder
        export_dir = os.path.dirname(os.path.abspath(__file__))

        # Apply shared_ispell compatibility patch via Conan's built-in mechanism
        apply_conandata_patches(self)

        # --- Build PostgreSQL from source ---
        pg_build_dir = os.path.join(self.build_folder, "postgresql_build")
        pg_src_dir = pg_build_dir
        pg_install_dir = os.path.join(pg_build_dir, "pg_install")
        os.makedirs(pg_build_dir, exist_ok=True)

        self.output.info("Downloading PostgreSQL source...")
        get(self, url=self.PG_SOURCE_URL, sha256=self.PG_SOURCE_SHA256,
            destination=pg_build_dir, strip_root=True)

        # Apply PostgreSQL harmony patches (some hunks may fail, non-critical)
        harmony_patch = os.path.join(export_dir, "patches", "postgresql_harmony.patch")
        if os.path.exists(harmony_patch):
            self.output.info("Applying PostgreSQL harmony patches...")
            self.run(f'patch -d "{pg_src_dir}" -p1 --fuzz=3 < "{harmony_patch}" || true')
        else:
            self.output.info("PostgreSQL harmony patch not found, building without OHOS patches")

        # Copy config.sub/config.guess for HarmonyOS platform detection
        config_dir = os.path.join(pg_src_dir, "config")
        config_sub_src = "/data/service/hnp/autoconf.org/autoconf_2.72/share/autoconf/build-aux/config.sub"
        config_guess_src = "/data/service/hnp/autoconf.org/autoconf_2.72/share/autoconf/build-aux/config.guess"
        if os.path.isdir(config_dir):
            if os.path.exists(config_sub_src):
                shutil.copy2(config_sub_src, os.path.join(config_dir, "config.sub"))
            if os.path.exists(config_guess_src):
                shutil.copy2(config_guess_src, os.path.join(config_dir, "config.guess"))

        # Fix umask 077 -> 067 for hmdfs (some configure scripts may not have it)
        for root, dirs, files in os.walk(pg_src_dir):
            for fname in files:
                if fname == "configure":
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, 'r') as f:
                            content = f.read()
                        content = content.replace("umask 077", "umask 067")
                        with open(fpath, 'w') as f:
                            f.write(content)
                    except Exception:
                        pass  # Some configure scripts may not contain umask 077

        # Configure and build PostgreSQL
        pg_build_subdir = os.path.join(pg_src_dir, "aarch64-build")
        os.makedirs(pg_build_subdir, exist_ok=True)

        # Get compiler from Conan conf (R33: don't use naked shell env vars)
        cc = "clang"
        cxx = "clang++"
        compilers = self.conf.get("tools.build:compiler_executables", None, check_type=dict)
        if compilers:
            cc = compilers.get("c", "clang")
            cxx = compilers.get("cpp", "clang++")

        # Set up build environment
        tmpdir = os.environ.get("TMPDIR", os.path.join(os.path.expanduser("~"), "tmp"))
        os.makedirs(tmpdir, exist_ok=True)

        self.output.info("Configuring PostgreSQL...")
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f'cd "{pg_build_subdir}" && '
            f'CC={cc} CXX={cxx} CFLAGS="-fPIC -O2 -D__OHOS__" '
            f'CXXFLAGS="-fPIC -O2 -D__OHOS__" TMPDIR="{tmpdir}" '
            f'{config_shell} ../configure --build=aarch64-unknown-linux-gnu '
            f'--host=aarch64-unknown-linux-gnu '
            f'--prefix="{pg_install_dir}" '
            f'--without-icu --without-readline --without-zlib --without-openssl'
        )

        self.output.info("Building PostgreSQL...")
        self.run(f'cd "{pg_build_subdir}" && make -j2')

        self.output.info("Installing PostgreSQL...")
        self.run(f'cd "{pg_build_subdir}" && make install')

        # --- Build shared_ispell using PGXS ---
        pg_config = os.path.join(pg_install_dir, "bin", "pg_config")
        if not os.path.exists(pg_config):
            raise Exception(f"pg_config not found at {pg_config}")

        self.output.info(f"Using pg_config: {pg_config}")
        self.output.info("Building shared_ispell extension...")

        self.run(
            f'cd "{src_dir}" && '
            f'PATH="{os.path.join(pg_install_dir, "bin")}:$PATH" '
            f'make USE_PGXS=1 PG_CONFIG="{pg_config}" -j1'
        )

        self.output.info("Installing shared_ispell extension...")
        self.run(
            f'cd "{src_dir}" && '
            f'PATH="{os.path.join(pg_install_dir, "bin")}:$PATH" '
            f'make USE_PGXS=1 PG_CONFIG="{pg_config}" install'
        )

    def package(self):
        pg_build_dir = os.path.join(self.build_folder, "postgresql_build")
        pg_install_dir = os.path.join(pg_build_dir, "pg_install")

        # Copy .so from lib/ or lib/postgresql/
        for lib_subdir in ["lib", "lib/postgresql"]:
            lib_dir = os.path.join(pg_install_dir, lib_subdir)
            if os.path.isdir(lib_dir):
                copy(self, "shared_ispell*.so", lib_dir, os.path.join(self.package_folder, "lib"))

        # Copy extension SQL and control files
        for ext_subdir in ["share/extension", "share/postgresql/extension"]:
            ext_dir = os.path.join(pg_install_dir, ext_subdir)
            if os.path.isdir(ext_dir):
                copy(self, "shared_ispell*", ext_dir, os.path.join(self.package_folder, "share", "extension"))

        # Also copy from source directory
        src_dir = self.source_folder
        copy(self, "shared_ispell*.so", src_dir, os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "shared_ispell*.control", src_dir, os.path.join(self.package_folder, "share", "extension"), keep_path=False)
        copy(self, "shared_ispell*.sql", src_dir, os.path.join(self.package_folder, "share", "extension"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["shared_ispell"]
        self.cpp_info.includedirs = []
