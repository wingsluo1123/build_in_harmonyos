#!/usr/bin/env python3
"""Conan recipe for postgresql-orafce 4.16.0

PostgreSQL extension providing Oracle compatibility functions.
Built with PGXS (PostgreSQL Extension Building Infrastructure).

This recipe is self-contained: if pg_config is not found on the system,
it downloads and configures PostgreSQL 17.0 source to provide the
required development files (headers, pg_config, PGXS makefiles).
"""
import os
import shutil
import glob
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

# PostgreSQL source for bootstrapping pg_config when not available on system
PG_VERSION = "17.0"
PG_SOURCE_URL = "https://github.com/postgres/postgres/archive/refs/tags/REL_17_0.tar.gz"


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
        result = shutil.which("pg_config", path=path)
        if result:
            return result
        home = os.environ.get("HOME", "")
        for p in [
            os.path.join(home, "usr", "local", "bin"),
            "/usr/local/bin",
            "/usr/bin",
        ]:
            candidate = os.path.join(p, "pg_config")
            if os.path.isfile(candidate):
                os.environ["PATH"] = p + os.pathsep + path
                return candidate
        return None

    def _bootstrap_postgresql(self):
        """Download and configure PostgreSQL to provide pg_config and headers"""
        self.output.info("pg_config not found - bootstrapping PostgreSQL from source...")

        pg_src_dir = os.path.join(self.build_folder, "postgresql-src")
        os.makedirs(pg_src_dir, exist_ok=True)

        # Download PostgreSQL source
        pg_tarball = os.path.join(self.build_folder, f"postgresql-{PG_VERSION}.tar.gz")
        if not os.path.isfile(pg_tarball):
            self.output.info(f"Downloading PostgreSQL {PG_VERSION} source...")
            self.run(f'curl -fSL -o "{pg_tarball}" "{PG_SOURCE_URL}"')

        # Extract
        if not os.path.isfile(os.path.join(pg_src_dir, "configure")):
            self.output.info("Extracting PostgreSQL source...")
            self.run(f'tar xzf "{pg_tarball}" -C "{pg_src_dir}" --strip-components=1')

        # Patch config.guess for HarmonyOS/OHOS
        config_guess = os.path.join(pg_src_dir, "config", "config.guess")
        if os.path.isfile(config_guess):
            with open(config_guess, "r") as f:
                content = f.read()
            if "HarmonyOS" not in content:
                # Add __OHOS__ libc detection
                content = content.replace(
                    '#if defined(__ANDROID__)\n\tLIBC=android',
                    '#if defined(__ANDROID__)\n\tLIBC=android\n#elif defined(__OHOS__)\n\tLIBC=ohos'
                )
                # Add HarmonyOS case after the case statement
                content = content.replace(
                    'case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in',
                    'case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n'
                    '    *:HarmonyOS:*:*)\n'
                    '\tcase "$UNAME_MACHINE" in\n'
                    '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                    '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                    '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                    '\tesac\n'
                    '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                    '\t;;\n'
                )
                with open(config_guess, "w") as f:
                    f.write(content)
                self.output.info("Patched config.guess for HarmonyOS")

        # Patch config.sub for linux-ohos
        config_sub = os.path.join(pg_src_dir, "config", "config.sub")
        if os.path.isfile(config_sub):
            with open(config_sub, "r") as f:
                content = f.read()
            if "ohos" not in content:
                # Add ohos-linux handling
                content = content.replace(
                    'basic_os=linux-android',
                    'basic_os=linux-android\n\t\t\t;;\n\t\tohos-linux)\n\t\t\t\tbasic_machine=$field1-unknown\n\t\t\t\tbasic_os=linux-ohos'
                )
                # Add ohos* to system types
                content = content.replace(
                    'gnu* | android* | bsd*',
                    'gnu* | android* | ohos* | bsd*'
                )
                # Add linux-ohos* to kernel validation
                content = content.replace(
                    '| linux-relibc*- | linux-uclibc*- )',
                    '| linux-relibc*- | linux-uclibc*- | linux-ohos*- )'
                )
                with open(config_sub, "w") as f:
                    f.write(content)
                self.output.info("Patched config.sub for linux-ohos")

        # Patch configure for TMPDIR
        configure_script = os.path.join(pg_src_dir, "configure")
        if os.path.isfile(configure_script):
            with open(configure_script, "r") as f:
                content = f.read()
            if "TMPDIR" not in content[content.find("Create a (secure) tmp"):content.find("Create a (secure) tmp")+500]:
                content = content.replace(
                    'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                    '_tmp_dir="${TMPDIR:-$HOME/tmp}"\n  tmp=`(umask 000 && mktemp -d "$_tmp_dir/confXXXXXX") 2>/dev/null`'
                )
                content = content.replace(
                    'tmp=./conf$$-$RANDOM',
                    'tmp="$_tmp_dir/conf$$-$RANDOM"'
                )
                content = content.replace(
                    'cannot create a temporary directory in .',
                    'cannot create a temporary directory in $TMPDIR'
                )
                with open(configure_script, "w") as f:
                    f.write(content)
                self.output.info("Patched configure for TMPDIR")

        # Configure PostgreSQL
        prefix = os.path.join(self.build_folder, "postgresql-install")
        tmpdir = os.environ.get("TMPDIR", os.path.join(os.environ.get("HOME", "/tmp"), "tmp"))
        os.makedirs(tmpdir, exist_ok=True)

        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.output.info("Configuring PostgreSQL...")
        self.run(
            f'cd "{pg_src_dir}" && '
            f'TMPDIR="{tmpdir}" '
            f'CONFIG_SHELL="{config_shell}" '
            f'./configure --prefix="{prefix}" '
            f'--without-readline --without-zlib --without-icu'
        )

        # Install pg_config and headers
        self.output.info("Installing PostgreSQL development files...")
        self.run(f'cd "{pg_src_dir}" && make -C src/bin/pg_config install')
        self.run(f'cd "{pg_src_dir}" && make -C src/include install')
        self.run(f'cd "{pg_src_dir}" && make -C src/common install')
        self.run(f'cd "{pg_src_dir}" && make -C src/port install')

        # Install PGXS makefiles
        pgxs_src = os.path.join(pg_src_dir, "src")
        pgxs_dest = os.path.join(prefix, "lib", "postgresql", "pgxs", "src")
        os.makedirs(pgxs_dest, exist_ok=True)

        # Copy all Makefile* files
        for f in os.listdir(pgxs_src):
            if f.startswith("Makefile"):
                shutil.copy2(os.path.join(pgxs_src, f), os.path.join(pgxs_dest, f))

        # Copy makefiles directory
        mk_src = os.path.join(pgxs_src, "makefiles")
        mk_dest = os.path.join(pgxs_dest, "makefiles")
        if os.path.isdir(mk_src):
            os.makedirs(mk_dest, exist_ok=True)
            for f in os.listdir(mk_src):
                shutil.copy2(os.path.join(mk_src, f), os.path.join(mk_dest, f))

        # Copy config directory (install-sh etc.)
        cfg_src = os.path.join(pg_src_dir, "config")
        cfg_dest = os.path.join(prefix, "lib", "postgresql", "pgxs", "config")
        if os.path.isdir(cfg_src):
            os.makedirs(cfg_dest, exist_ok=True)
            for f in os.listdir(cfg_src):
                shutil.copy2(os.path.join(cfg_src, f), os.path.join(cfg_dest, f))

        # Add to PATH
        os.environ["PATH"] = os.path.join(prefix, "bin") + os.pathsep + os.environ.get("PATH", "")

        pg_config = shutil.which("pg_config")
        if pg_config:
            self.output.info(f"PostgreSQL bootstrapped successfully: {pg_config}")
            return pg_config
        return None

    def build(self):
        apply_conandata_patches(self)

        # Find or bootstrap pg_config
        pg_config = self._find_pg_config()
        if not pg_config:
            pg_config = self._bootstrap_postgresql()

        if not pg_config:
            raise Exception("Failed to obtain pg_config after bootstrap. "
                            "PostgreSQL development files are required to build orafce.")

        self.output.info(f"Using pg_config: {pg_config}")

        # PGXS build: make uses pg_config to find PostgreSQL build settings
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Find orafce.so - it should be in the source folder after make
        so_files = []
        for pattern in ["orafce.so", "**/orafce.so"]:
            so_files.extend(glob.glob(os.path.join(self.source_folder, pattern)))

        if not so_files:
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

        # Copy SQL files
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
        self.cpp_info.libs = ["orafce"]
        self.cpp_info.libdirs = ["lib/postgresql"]
