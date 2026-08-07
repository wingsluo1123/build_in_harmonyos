#!/usr/bin/env python3
"""Conan recipe — pgimportdoc 0.1.4 (PGXS application).

pgimportdoc is a PostgreSQL command-line utility for importing XML, JSON,
and BYTEA documents to PostgreSQL. It uses the PGXS (PostgreSQL Extension
Build System) which requires pg_config from a PostgreSQL build tree.

Build strategy:
  1. Require libpq/18.1 from conan (runtime dependency)
  2. Download PostgreSQL 18.1 source for frontend headers + support libs
  3. Configure PostgreSQL (generates pg_config.h, Makefile.global, pgxs.mk)
  4. Build libpgport.a, libpgcommon.a, and pg_config from PostgreSQL source
  5. Build pgimportdoc using PGXS with the local pg_config
  6. Package the pgimportdoc binary
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout

# PostgreSQL 18.1 source (same as libpq/18.1 conan package)
PG_SOURCE_URL = "https://ftp.postgresql.org/pub/source/v18.1/postgresql-18.1.tar.bz2"
PG_SOURCE_SHA256 = "ff86675c336c46e98ac991ebb306d1b67621ece1d06787beaade312c2c915d54"


class PgimportdocConan(ConanFile):
    name = "pgimportdoc"
    version = "0.1.4"
    description = "PostgreSQL command-line utility for importing XML, JSON, BYTEA documents"
    license = "PostgreSQL"
    homepage = "https://github.com/okbob/pgimportdoc"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpq/18.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Set up build environment for OHOS
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)

        env = Environment()
        env.define_path("TMPDIR", tmpdir)

        if str(self.settings.os) == "OHOS":
            shell = "/data/service/hnp/bin/bash"
            env.define_path("CONFIG_SHELL", shell)
            env.define_path("SHELL", shell)
            env.prepend_path("PATH", "/data/service/hnp/bin")
        else:
            shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh")
            if shell:
                env.define_path("CONFIG_SHELL", shell)

        env.vars(self).save_script("pgimportdoc_build_env")

    def build(self):
        apply_conandata_patches(self)

        # Create configure wrapper (PGXS projects don't have configure)
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            save(self, configure_path,
                 "#!/bin/sh\n"
                 "# Minimal configure wrapper for PGXS-based pgimportdoc\n"
                 "echo pgimportdoc configure: Using PGXS build system\n"
                 "echo Configuration complete. Run make to build.\n"
                 "exit 0\n")

        # 1. Download PostgreSQL source for headers and support libraries
        pg_src_dir = os.path.join(self.build_folder, "pgsrc")
        os.makedirs(pg_src_dir, exist_ok=True)

        # Try to use a local copy of the PostgreSQL tarball first (speeds up local dev)
        pg_tarball_name = "postgresql-18.1.tar.bz2"
        pg_extracted = os.path.join(pg_src_dir, "postgresql-18.1", "configure")
        if not os.path.isfile(pg_extracted):
            local_found = False
            for local_path in [
                os.path.join(os.environ.get("HOME", ""), "tmp", pg_tarball_name),
                os.path.join(os.environ.get("TMPDIR", ""), pg_tarball_name),
            ]:
                if os.path.isfile(local_path):
                    # Verify SHA256 before using
                    import hashlib
                    with open(local_path, "rb") as f:
                        actual_sha = hashlib.sha256(f.read()).hexdigest()
                    if actual_sha == PG_SOURCE_SHA256:
                        # Copy and extract
                        dest_tarball = os.path.join(pg_src_dir, pg_tarball_name)
                        shutil.copy2(local_path, dest_tarball)
                        self.run(f'tar xf "{dest_tarball}" -C "{pg_src_dir}"')
                        local_found = True
                        break
            if not local_found:
                # Download from remote
                get(self, url=PG_SOURCE_URL, sha256=PG_SOURCE_SHA256,
                    strip_root=True, destination=pg_src_dir)

        pgsrc = os.path.join(pg_src_dir, "postgresql-18.1")
        if not os.path.isdir(pgsrc):
            # strip_root might extract differently
            items = os.listdir(pg_src_dir)
            if len(items) == 1:
                pgsrc = os.path.join(pg_src_dir, items[0])

        # 2. Fix config.guess/config.sub for OHOS platform detection
        self._fix_platform_detection(pgsrc)

        # 3. Configure PostgreSQL (generates pg_config.h, Makefile.global, pgxs.mk)
        self._configure_postgresql(pgsrc)

        # 4. Build support libraries and pg_config
        self._build_pg_support(pgsrc)

        # 5. Build pgimportdoc using PGXS
        self._build_pgimportdoc(pgsrc)

    def _fix_platform_detection(self, pgsrc):
        """Fix config.guess, config.sub, and TMPDIR/umask issues for OHOS."""
        config_sub = os.path.join(pgsrc, "config", "config.sub")
        config_guess = os.path.join(pgsrc, "config", "config.guess")
        configure = os.path.join(pgsrc, "configure")

        # Fix config.sub for OHOS
        if os.path.isfile(config_sub):
            with open(config_sub, "r") as f:
                content = f.read()
            if "ohos-linux" not in content:
                content = content.replace(
                    "| linux-gnu* | linux-dietlibc | ",
                    "| linux-gnu* | linux-dietlibc | linux-ohos* | "
                )
                with open(config_sub, "w") as f:
                    f.write(content)

        # Fix config.guess for HarmonyOS
        if os.path.isfile(config_guess):
            with open(config_guess, "r") as f:
                content = f.read()
            if "HarmonyOS" not in content and "ohos" not in content.lower():
                content = content.replace(
                    '    GNU/*)',
                    '    HarmonyOS) echo "${UNAME_MACHINE}-unknown-linux-ohos"; exit ;;\n    GNU/*)'
                )
                with open(config_guess, "w") as f:
                    f.write(content)

        # Fix TMPDIR and umask in configure (same as libpq 0003 patch)
        # HMDFS: umask 077 creates non-executable temp files -> Permission denied
        if os.path.isfile(configure):
            with open(configure, "r") as f:
                content = f.read()
            if 'umask 077' in content:
                content = content.replace(
                    'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                    '_tmp_dir="${TMPDIR:-$HOME/tmp}"\n  tmp=`(umask 000 && mktemp -d "$_tmp_dir/confXXXXXX") 2>/dev/null`'
                )
                content = content.replace(
                    'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
                    'tmp="$_tmp_dir/conf$$-$RANDOM"\n  (umask 000 && mkdir "$tmp")'
                )
                content = content.replace(
                    'cannot create a temporary directory in .',
                    'cannot create a temporary directory in $TMPDIR'
                )
                with open(configure, "w") as f:
                    f.write(content)

    def _configure_postgresql(self, pgsrc):
        """Run PostgreSQL configure to generate build system files."""
        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")

        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(config_shell):
            config_shell = shutil.which("bash") or shutil.which("sh") or "/bin/sh"

        pg_install = os.path.join(self.build_folder, "pginstall")
        os.makedirs(pg_install, exist_ok=True)

        # Use explicit triplet to avoid platform detection issues on OHOS
        configure_cmd = (
            f'cd "{pgsrc}" && '
            f'"{config_shell}" ./configure '
            f'--prefix="{pg_install}" '
            f'--build=aarch64-unknown-linux-musl '
            f'--host=aarch64-unknown-linux-musl '
            f'CC="{cc}" '
            f'--without-icu '
            f'--without-readline '
            f'--without-zlib '
            f'--without-openssl '
            f'--without-libxml '
            f'--without-libxslt '
            f'--without-ldap '
            f'--without-gssapi '
            f'--without-pam '
            f'--without-systemd '
            f'--without-lz4 '
            f'--without-zstd'
        )
        self.run(configure_cmd)

    def _build_pg_support(self, pgsrc):
        """Build libpgport, libpgcommon, pg_config, and install PGXS from PostgreSQL source."""
        # Build pg_config (needed for PGXS)
        self.run(f'cd "{pgsrc}" && make -C src/bin/pg_config -j1')

        # Build frontend port library (libpgport)
        self.run(f'cd "{pgsrc}" && make -C src/port -j1')

        # Build frontend common library (libpgcommon)
        self.run(f'cd "{pgsrc}" && make -C src/common -j1')

        # Build libpq from source (PGXS needs it for linking)
        self.run(f'cd "{pgsrc}" && make -C src/interfaces/libpq -j1')

        # Install PostgreSQL (needed for PGXS makefiles to be in correct location)
        self.run(f'cd "{pgsrc}" && make install -j1')

    def _build_pgimportdoc(self, pgsrc):
        """Build pgimportdoc using PGXS with the local pg_config."""
        pg_config = os.path.join(pgsrc, "src", "bin", "pg_config", "pg_config")
        if not os.path.isfile(pg_config):
            raise ConanException(f"pg_config not found at {pg_config}")

        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "clang")
        cxx = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("cpp", "clang++")

        # Use PGXS to build pgimportdoc
        # PG_CONFIG env var overrides the default pg_config used by the Makefile
        self.run(
            f'cd "{self.source_folder}" && '
            f'make PG_CONFIG="{pg_config}" CC="{cc}" -j1'
        )

    def package(self):
        # Copy the pgimportdoc binary
        copy(self, "pgimportdoc", self.source_folder,
             os.path.join(self.package_folder, "bin"))

        # Copy license
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # Runtime dependency on libpq is handled by conan dependency graph
        self.cpp_info.requires = ["libpq::libpq"]
