#!/usr/bin/env python3
"""Conan recipe - rstatd 4.0.1 (ONC RPC remote statistics daemon, autotools).

Upstream is the rpc.rstatd 4.0.1 release from the rstatd SourceForge project
(http://rstatd.sourceforge.net/).  The tarball builds three programs:

  * rpc.rstatd - the ONC RPC program 100001 daemon that serves load, paging,
    context-switch, disk, network and uptime counters collected from /proc
  * rup        - the RSTATVERS_USERS client
  * rsysinfo   - the RSTATVERS_TIME client

Adaptation notes live in notes.md; every source change is a registered patch
under patches/ so the recipe stays reproducible.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RstatdConan(ConanFile):
    name = "rstatd"
    version = "4.0.1"
    description = (
        "rstatd: ONC RPC remote statistics daemon (rpc.rstatd, program 100001) "
        "plus the rup and rsysinfo clients"
    )
    license = "GPL-2.0-or-later"
    homepage = "http://rstatd.sourceforge.net/"
    url = ""  # CI fills this
    topics = ("rpc", "oncrpc", "tirpc", "sysstat", "daemon", "monitoring", "procfs")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def configure(self):
        # Pure C package: the C++-only settings would only add noise.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def requirements(self):
        # <rpc/rpc.h>, <rpc/pmap_clnt.h>, <rpc/clnt.h> and every xdr_*/svc_*/
        # clnt_* symbol come from SunRPC.  OHOS does not ship SunRPC in libc,
        # so the recipe builds against the portable TI-RPC implementation -
        # the same choice archives/l/libnsl/2.0.1 makes.
        self.requires("libtirpc/1.3.7")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # The release tarball ships a pre-generated configure and the Makefile
        # it produces hardcodes "srcdir = .", so this is an in-tree build:
        # configure and make must run inside the source folder.
        basic_layout(self, src_folder="src")
        self.folders.build = self.folders.source

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _tirpc_flags(self):
        """Return (cppflags, ldflags, libs) that make <rpc/rpc.h> resolvable.

        The libtirpc/1.3.7 recipe does declare
        ``cpp_info.includedirs = ["include", "include/tirpc"]`` and
        ``cpp_info.libs = ["tirpc"]``, but the *published binary* carries no
        cpp_info at all: its conaninfo.txt contains only [settings] and
        [options], so a consumer gets neither the include roots nor -ltirpc and
        every source file dies with

            fatal error: 'rpc/rpc.h' file not found

        (archives/l/libnsl/2.0.1 hit exactly the same wall and works around it
        the same way.)  Resolve the dependency's package folder directly and
        hand the flags to configure.  The paths come from the Conan package
        folder, never from a shared /usr/local (R49).
        """
        dep = self.dependencies["libtirpc"]
        package_folder = dep.package_folder
        if not package_folder:
            raise ConanException(
                "libtirpc/1.3.7 has no package folder: the published binary "
                "does not expose its headers.")
        include_tirpc = os.path.join(package_folder, "include", "tirpc")
        include_root = os.path.join(package_folder, "include")
        libdir = os.path.join(package_folder, "lib")
        if not os.path.isfile(os.path.join(include_tirpc, "rpc", "rpc.h")):
            raise ConanException(
                "libtirpc/1.3.7 headers not found under %s" % include_tirpc)
        cppflags = " ".join("-I%s" % p for p in (include_tirpc, include_root))
        ldflags = "-L%s" % libdir
        return cppflags, ldflags, "-ltirpc"

    def _configure_args(self):
        """The one true configure argument list, used by generate() and build()."""
        # The 2005 configure carries an autoconf 2.59 config.guess/config.sub
        # that does not know the HarmonyOS uname, and would abort with
        # "cannot guess build type".  Passing an explicit native triplet for
        # both --build and --host skips config.guess entirely (same treatment
        # as the merged libtirpc/1.3.7, classads/1.0.10 and cityhash/1.1.1
        # recipes); the compiler still comes from the profile.
        triplet = {
            "armv8": "aarch64",
            "armv7": "armv7",
            "x86_64": "x86_64",
        }.get(str(self.settings.arch), str(self.settings.arch))
        cppflags, ldflags, libs = self._tirpc_flags()
        return [
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
            f"--build={triplet}-unknown-linux-ohos",
            f"--host={triplet}-unknown-linux-ohos",
            f"CPPFLAGS={cppflags}",
            f"LDFLAGS={ldflags}",
            f"LIBS={libs}",
        ]

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def build(self):
        # Autoconf's configure/config.status create their scratch directory with
        # `(umask 077 && mktemp -d ...)`.  On the HMDFS/hmdfs mount a 0700
        # directory created below a setgid directory is not writable by the very
        # next process and config.status dies with
        # "can't create ./confXXXXXX/...: Permission denied"
        # "config.status: error could not setup config files machinery".
        # Relaxing the scratch umask to 022 fixes it; same treatment as
        # archives/s/sysstat/12.7.9 and archives/l/libnsl/2.0.1.
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022", strict=False)

        # Upstream's Makefile regenerates rstat.h, rstat_svc.c, rstat_clnt.c and
        # rstat_xdr.c from rstat.x with rpcgen, and lists rstat.h in
        # BUILT_SOURCES, so the build cannot start without it.  The release
        # tarball ships the three .c files pre-generated but not rstat.h, and
        # OHOS has no rpcgen (no conan package provides one either - see
        # notes.md), so patches/0007 vendors exactly the rstat.h that rpcgen
        # emits for the unmodified rstat.x.  Touching the four generated files
        # after extraction makes them newer than rstat.x so make never fires
        # the regeneration rules.
        generated = ("rstat.h", "rstat_svc.c", "rstat_clnt.c", "rstat_xdr.c")
        for name in generated:
            path = os.path.join(self.source_folder, name)
            if os.path.isfile(path):
                os.utime(path, None)

        # configure is invoked explicitly instead of Autotools.configure().
        #
        # ci/conan/profiles/ohos-aarch64 exports CONFIG_SHELL and SHELL pointing
        # at /data/service/hnp/bin/bash.  Autoconf honours a pre-set
        # CONFIG_SHELL instead of probing for a shell and re-exec'ing itself;
        # when it does re-exec through bash on HarmonyOS PC, bash cannot resolve
        # a non-root working directory (pwd/getcwd() fail on the hmfs/hmdfs
        # mount) and configure dies in its prologue without printing anything -
        # exactly what CI build #69692 showed.  CONFIG_SHELL=/bin/sh skips both
        # the search and the re-exec.  archives/l/libnsl/2.0.1 documents and
        # works around the same thing on this CI.
        #
        # `cd`ing inside the command (rather than passing cwd=) also avoids the
        # getcwd storm a conan-provided cwd triggers on HMDFS.
        configure_args = " ".join(shlex.quote(a) for a in self._configure_args())
        self.run(f'cd "{self.source_folder}" && umask 022 && '
                 f'CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
                 f'sh "./configure" {configure_args}',
                 env="conanbuild")
        # Upstream ships no test suite at all: Makefile.am declares no TESTS and
        # no check_PROGRAMS, and the tarball has no test directory, so there is
        # nothing to run here.  The functional coverage lives in test_package/,
        # which drives the installed daemon over real ONC RPC.  Evidence is
        # recorded in test_package/MANIFEST.yml.
        self.run(f'cd "{self.source_folder}" && make -j1', env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Upstream's man pages are declared in Makefile.am but AUTOMAKE_OPTIONS
        # contains "no-installman", so `make install` never installs them.
        for man in ("rpc.rstatd.8", "rstatd.8", "rup.1", "rsysinfo.1"):
            src = os.path.join(self.source_folder, man)
            if os.path.isfile(src):
                copy(self, man, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "share", "man", "man8")
                     if man.endswith(".8") else
                     os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # Program-only package: three executables, no library, no headers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share/man"]
