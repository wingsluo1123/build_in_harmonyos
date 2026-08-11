#!/usr/bin/env python3
"""Conan recipe for PostgreSQL 18.3 on HarmonyOS.

PostgreSQL provides both client libraries (libpq, libecpg) and command-line
tools (pg_dump, psql, pg_config, initdb, etc.).

OHOS adaptations applied via 13 patches:
  1. config.guess/config.sub — HarmonyOS platform detection
  2. configure — umask 077 → 022 for hmdfs permission (OHOS only)
  3. sysv_shmem.c — mmap when shmget broken (HAVE_BROKEN_SHMGET)
  4. miscinit.c — relaxed ownership/permission checks (HAVE_BROKEN_UMASK)
  5. initdb.c — mmap DSM + chmod after mkdir (HAVE_BROKEN_SHM_OPEN/UMASK)
  6. file_perm.c — disable mode mask (HAVE_BROKEN_UMASK)
  7. username.c — getpwuid fallback (HAVE_BROKEN_GETPWUID)
  8. pg_config_manual.h — disable Unix sockets (HAVE_NO_UNIX_SOCKETS)
  9. dsm_impl.h — mmap DSM when shm_open broken (HAVE_BROKEN_SHM_OPEN)
  10. fe-auth.c — getpwuid fallback (HAVE_BROKEN_GETPWUID)
  11. pgmkdirp.c — mkdir permission fix (HAVE_BROKEN_UMASK)
  12. pg_regress.c — TCP/IP when no Unix sockets (HAVE_NO_UNIX_SOCKETS)
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PostgresqlConan(ConanFile):
    name = "postgresql"
    version = "18.3"
    description = "PostgreSQL database server and client tools (pg_dump, psql, libpq)"
    license = "PostgreSQL"
    homepage = "https://www.postgresql.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # All optional dependencies disabled via --without-* flags
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Check for local source cache to avoid slow remote downloads
        import os
        local_src = os.path.join(os.path.expanduser("~"),
                                 ".opendesk/apps/skills/resources/openharmony-compile-agent/sources",
                                 "postgresql-18.3.tar.bz2")
        if os.path.exists(local_src):
            from conan.tools.files import unzip
            unzip(self, local_src, self.source_folder, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-icu",
            "--without-readline",
            "--without-zlib",
            "--without-openssl",
        ])
        # Feature macros for platform limitations (R8: semantic macros, not platform macros)
        if str(self.settings.os) == "OHOS":
            tc.extra_defines.extend([
                "HAVE_BROKEN_SHMGET",
                "HAVE_BROKEN_SHM_OPEN",
                "HAVE_BROKEN_GETPWUID",
                "HAVE_BROKEN_UMASK",
                "HAVE_NO_UNIX_SOCKETS",
            ])
        tc.generate()

    def build(self):
        # Ensure TMPDIR exists (OHOS /tmp is read-only, E002)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        # Apply conandata patches (all OHOS adaptations)
        # Note: 0003-configure.patch changes umask 077→022; on Linux this
        # makes configure's temp files group/other readable (minor security
        # regression, acceptable since temp files are in private build dir)
        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # Copy license
        copy(self, "COPYRIGHT", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # libpq — primary client library
        self.cpp_info.libs = ["pq"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        # Additional system libs needed by libpq on OHOS/Linux
        self.cpp_info.system_libs = ["m"]
