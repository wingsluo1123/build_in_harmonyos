#!/usr/bin/env python3
"""Conan recipe for sn 0.3.8 -- a small Usenet news system (article
fetcher, NNTP server and spool administration tools) for small sites.

Upstream: Patrik Faltstrom, <http://www.iki.fi/patrik/sn/> (project of
the early 2000s).  The 0.3.8 release is no longer served from the origin
site; it is reliably available as the pristine upstream tarball in the
Debian pool, used per R39 (same precedent as jpegpixi 1.1.1).

Build system is the upstream's own make(1): `make all` builds
lib/libstuff.a and sn.a, 14 binaries, 3 shell scripts and the man pages
(sed over *.in).  The optional article-body compression (USE_ZLIB) is
enabled by pointing the Makefile's ZLIB variable at the ohpcd zlib/1.3.1
recipe; the zlib headers are copied into the build tree's lib/ directory,
which is already on the include path (cc-flags adds -I./lib), so no
source patch is needed.  The Makefile hard-codes `ar`/`ranlib`/`strip`
(no $(AR)/$(RANLIB) variables): the OHOS aarch64 objects are handled
correctly by the host GNU binutils (ar only packs, ranlib indexes,
strip is multi-arch).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class SnConan(ConanFile):
    name = "sn"
    version = "0.3.8"
    description = ("sn: a small news system for small sites (Usenet "
                   "article fetcher + NNTP server + spool tools)")
    license = "GPL-2.0-or-later"
    homepage = "http://www.iki.fi/patrik/sn/"
    url = "https://deb.debian.org/debian/pool/main/s/sn/sn_0.3.8.orig.tar.gz"
    topics = ("news", "nntp", "usenet")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # Standard OHC patch entry point (G1); the recipe does not patch
        # the upstream tree (conandata.yml has no patches).
        export_conandata_patches(self)

    def requirements(self):
        # The only external dependency: article-body compression (USE_ZLIB).
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must accept both Linux and OHOS.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sn supports Linux and OHOS targets only")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        return compilers.get("c", "clang") if compilers else "clang"

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        cc = self._cc()
        zinfo = self.dependencies["zlib"].cpp_info.aggregated_components()

        # 1) Make the zlib headers visible without touching the source:
        #    lib/ is already on the include path (cc-flags adds -I./lib).
        for inc in zinfo.includedirs:
            copy(self, "zlib.h", inc, os.path.join(src, "lib"))
            copy(self, "zconf.h", inc, os.path.join(src, "lib"))
        zlib_lib = "-L" + " -L".join(zinfo.libdirs)

        # 2) Build everything: libs, 14 binaries, scripts, man pages.
        #    R9: -j1.  CC/LD are overridden for the OHOS cross; a
        #    non-empty ZLIB makes cc-flags add -DUSE_ZLIB automatically,
        #    and the ZLIB variable carries the zlib link flag.
        self.run("make -j1 CC={0} LD={0} ZLIB='{1} -lz'".format(cc, zlib_lib),
                 cwd=src)

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        # Exact upstream BINS list from the Makefile (14 binaries).
        progs = ("snprimedb snntpd snfetch snexpire snsend snmail snget "
                 "sngetd snscan sndumpdb snnewgroup sndelgroup snlockf "
                 "sn" "split").split()
        for p in progs:
            copy(self, p, src, bindir)
        for s in ("dot-outgoing.ex", "SNHELLO", "SNPOST"):
            copy(self, s, src, bindir)
        # Re-create the upstream symlinks inside the package.
        for link, target in (("sncat", "snscan"),
                             ("sncancel", "snscan"),
                             ("snstore", "snsend")):
            os.symlink(target, os.path.join(bindir, link))
        man8 = os.path.join(self.package_folder, "share", "man", "man8")
        copy(self, "*.8", src, man8)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
