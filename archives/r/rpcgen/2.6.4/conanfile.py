#!/usr/bin/env python3
"""Conan recipe — rpcgen 2.6.4 (Sun/TIRPC RPC protocol compiler).

``rpcgen`` translates an RPC interface definition (``.x``) into C source
headers, client stubs, server stubs and XDR routines.  Upstream has no release
of its own: the maintained copy is ``tools/rpcgen/`` inside the nfs-utils
source tree (Olaf Kirch's clean-up of the Sun TIRPC rpcgen.new), so version
2.6.4 is the nfs-utils version and the source is the official nfs-utils
release tarball.  Distribution packages named ``rpcgen`` (e.g. Alpine's
subpackage of nfs-utils) are built from exactly this directory.

Shipped artifact:

  bin/rpcgen, share/man/man1/rpcgen.1

Dependencies (all published in the ohpcd repository, see notes.md for the
``conan download`` / ``conan install`` evidence):

  * libtirpc  -- ``rpc/rpc.h`` + ``PKG_CHECK_MODULES([TIRPC], [libtirpc])``
  * uuid      -- ``AC_CHECK_HEADER(uuid/uuid.h)``
  * libevent  -- ``AC_LIBEVENT``
  * sqlite3   -- ``AC_SQLITE3_VERS``

  Those four are unconditional gates of the nfs-utils *top level* configure,
  which this package has to run because ``tools/rpcgen`` is built through the
  tree's autotools setup.  None of them is linked into rpcgen
  (``rpcgen_LDADD = $(LIBINTL)``): they are consumed by configure's header and
  library probes, exactly like sqlite3 in the sibling libnfsidmap-ldap/2.6.4
  package of the same source tree.

OHOS platform adaptations (see notes.md for commands, logs and evidence):

  * ``config.guess``/``config.sub`` carry the ``aarch64-unknown-linux-ohos``
    triplet (E007/E122) instead of passing --build/--host, which would make
    configure misdetect a cross build and skip every run test.
  * ``configure``: the tree-wide hard gate requiring getrpcbynumber(_r) is
    downgraded to a warning.  Neither the OHOS libc nor libtirpc provides the
    symbol and its only user (support/nfs/svc_socket.c, part of libnfs.la) is
    outside this package's build scope.
  * ``-D_LARGEFILE64_SOURCE``: rpc_main.c uses the LFS64 API (``struct
    stat64``/``stat64()``) unconditionally.  The OHOS libc exposes those
    aliases only when that POSIX feature-test macro is defined (sys/stat.h:
    ``#if defined(_LARGEFILE64_SOURCE) || defined(_GNU_SOURCE)``), while glibc
    exposes them by default - which is why upstream never needed a guard.  The
    flag is a standard feature-test macro, no platform macro and no source
    edit; the translation unit then compiles against the plain 64-bit ``stat``
    that both libcs provide.
  * ``--disable-gss``: the gssd client is the only user of the default-on GSS
    path, which would otherwise pull in krb5 for a binary that never links it.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# Environment for every configure/make invocation:
#   CONFIG_SHELL/SHELL=/bin/sh -- the OHOS bash injected through the profile's
#     [buildenv] fails getcwd() on HMDFS directories (DRAFT-6487), which breaks
#     autoconf's internal config.guess/config.sub/config.status calls.
#   ACLOCAL/AUTOMAKE/AUTOCONF/AUTOHEADER=true -- HMDFS timestamp granularity
#     lets make believe the autotools files are stale and re-run
#     "config.status --recheck" (i.e. configure again) inside the build; the
#     shipped Makefile.in are valid, so regeneration is neutralized
#     (libmirage / dbus-glib precedent).
BUILD_ENV = ("CONFIG_SHELL=/bin/sh SHELL=/bin/sh "
             "ACLOCAL=true AUTOMAKE=true AUTOCONF=true AUTOHEADER=true")

CONFIGURE_ARGS = [
    # No system rpcgen on OHOS: build the internal one shipped in tools/rpcgen
    # (without this, configure fails with "Please install rpcgen or use
    # --with-rpcgen").  It also puts tools/rpcgen into tools/Makefile SUBDIRS.
    "--with-rpcgen=internal",
    # gssd is the only consumer of the default-on GSS path (kerberos5.m4).
    "--disable-gss",
    # Libraries of these gates are outside this package's build scope; the
    # switches only affect nfsv41/blkmapd, mount.nfs and nfsrahead.
    "--disable-nfsv41",
    "--disable-uuid",
    "--disable-nfsrahead",
]


class RpcgenConan(ConanFile):
    name = "rpcgen"
    version = "2.6.4"
    description = ("RPC protocol compiler from the nfs-utils tree: generates C "
                   "headers, client/server stubs and XDR routines from .x "
                   "interface definitions")
    license = "BSD-3-Clause"
    homepage = "https://linux-nfs.org/"
    # Upstream project home (rpcgen has no repository of its own: it is part of
    # the nfs-utils tree, which is where it is maintained and released from).
    url = "https://linux-nfs.org/"

    # A command line tool: the package ships bin/rpcgen (R38 -> commands.json).
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Unconditional gates of the nfs-utils top level configure; none of
        # them is linked by the shipped binary (see the docstring).
        self.requires("libtirpc/1.3.7")
        self.requires("uuid/2.40.1")
        self.requires("libevent/2.1.13")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _dependency_flags(self):
        """Include/library search paths of every dependency, for configure.

        AutotoolsToolchain does not add them on its own (the autotools flow
        normally relies on pkg-config/AutotoolsDeps), but nfs-utils probes its
        dependencies with AC_CHECK_HEADER/AC_CHECK_LIB.
        """
        cflags, ldflags = [], []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                # transitive dependencies whose binary is not needed here
                continue
            components = dep.cpp_info.aggregated_components()
            cflags.extend("-I" + inc for inc in components.includedirs)
            ldflags.extend("-L" + lib for lib in components.libdirs)
        return cflags, ldflags

    def generate(self):
        tc = AutotoolsToolchain(self)
        cflags, ldflags = self._dependency_flags()
        # LFS64 API of rpc_main.c: see the docstring (POSIX feature-test macro,
        # needed by the OHOS libc, implicit on glibc).
        tc.extra_cflags = cflags + ["-D_LARGEFILE64_SOURCE"]
        tc.extra_ldflags = ldflags
        tc.generate()
        # AC_LIBTIRPC uses PKG_CHECK_MODULES([TIRPC], [libtirpc]).
        PkgConfigDeps(self).generate()

    def build(self):
        src = self.source_folder
        args = " ".join(CONFIGURE_ARGS)
        # In-tree build: cd is done inside the shell on purpose (DRAFT-6487).
        self.run(f'cd "{src}" && {BUILD_ENV} ./configure '
                 f'--prefix="{self.package_folder}" {args}', env="conanbuild")
        self.run(f'cd "{src}" && {BUILD_ENV} make -C tools/rpcgen',
                 env="conanbuild")
        # Upstream ships no automated test suite for tools/rpcgen (proved by
        # the census over every Makefile.am, see notes.md / MANIFEST.yml), so
        # `make check` is a no-op; it is still run so that the absence is
        # visible in the build log.  The functional verification is done by
        # test_package against the installed binary.
        self.run(f'cd "{src}" && {BUILD_ENV} make -C tools/rpcgen check',
                 env="conanbuild")

    def package(self):
        src = self.source_folder
        self.run(f'cd "{src}" && {BUILD_ENV} make -C tools/rpcgen install',
                 env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
