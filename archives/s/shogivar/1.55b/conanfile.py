#!/usr/bin/env python3
"""Conan recipe — shogivar 1.55b (C port, GTK+ 3 front end) for HarmonyOS PC.

ShogiVar is a referee/playing program for 17 ancient and modern Shogi variants
(the original 1.55a was a 16-bit Visual Basic application; H.G. Muller ported
the game logic to C and added a GTK front end adapted from GNU XBoard).

Package content: ``bin/shogivar`` (GTK+ 3 application), the 1000+ board/piece/
title/help assets under ``share/games/shogivar`` that the binary loads at run
time, and the man page ``share/man/man6/shogivar.6``.

Build notes (all of them encoded in patches/, see conandata.yml):
  * the shipped config.guess/config.sub (2014) do not know HarmonyOS/OHOS,
  * upstream asks for GTK+ 2; the OHOS registry only publishes GTK+ 3, so the
    front end is ported to the GTK3 API,
  * librsvg (required by configure, included by draw.c) is never called —
    the dead dependency is dropped instead of pulling in an extra library,
  * ``makeinfo`` must not abort configure: shogivar ships no Texinfo manual,
  * the OHOS worker has no automake, so maintainer-mode rules are neutralised,
  * ``-v/--version`` and ``-h/--help`` are answered before ``gtk_init()``,
    which gives a display-less smoke entry point for CI.

Upstream ships no automated test suite (no tests/ directory, no TESTS or
check_PROGRAMS in Makefile.am, no test sources in the tarball); ``make check``
is therefore executed but registers zero cases — see test_package/ for the
HarmonyOS consumer tests that are run instead.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class ShogivarConan(ConanFile):
    name = "shogivar"
    version = "1.55b"
    description = ("ShogiVar — referee and playing program for 17 Shogi variants, "
                   "with a built-in computer player and a GTK+ 3 board")
    license = "GPL-3.0-or-later"
    homepage = "https://hgm.nubati.net/"
    url = ""

    package_type = "application"

    # L0p: the four OHOS profile settings.
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: platform checks must accept both Linux and OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"shogivar/{self.version} supports Linux/OHOS only, "
                f"got os={self.settings.os}")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # The front end is a GTK+ 3 application (the source is ported from
        # GTK+ 2 by patches/0008).  gtk pulls glib/pango/cairo/gdk-pixbuf/atk/
        # fribidi/libepoxy transitively; cairo is declared directly because
        # draw.c and gtk/*.c include cairo headers themselves.
        #
        # librsvg is deliberately absent: upstream configure requires it and
        # draw.c includes its headers, but the source contains no rsvg_* call
        # at all (patch 0003 drops the requirement, patch 0005 the includes).
        # Pulling it in would also force cairo-gobject/1.18.4.3, which is
        # binary-incompatible with the published gtk/3.24.43 build (that one
        # is compiled against cairo-gobject/1.18.4.2) — the two pins cannot
        # coexist in one graph.
        self.requires("gtk/3.24.43")
        self.requires("cairo/1.18.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The worker has no xdg-* helpers; keep install from trying them.
        tc.configure_args.append("--disable-update-mimedb")
        tc.configure_args.append("--disable-silent-rules")
        tc.generate()
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # E490: the autotools helper scripts are executable programs, and some
        # extraction/adaptation paths on OHOS drop their mode bits; restore
        # them explicitly instead of hoping the tarball modes survived.
        for script in ("configure", "config.guess", "config.sub", "install-sh",
                       "missing", "depcomp", "compile"):
            path = os.path.join(self.source_folder, script)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
        autotools = Autotools(self)
        autotools.configure()
        # `make -jN` is unusable on the OHOS worker: GNU make's jobserver tries
        # to create a FIFO under $TMPDIR and fails with "jobserver mkfifo:
        # Operation not permitted".  Same convention as the rest of the repo.
        autotools.make(args=["-j1"])
        # Upstream test entry point.  shogivar has no test suite at all (no
        # tests/ directory, no TESTS/check_PROGRAMS in Makefile.am, no test
        # sources in the tarball), so this target is automake's empty `check`
        # rule and registers 0 cases; it is run so that the entry point is
        # exercised for real rather than assumed to be absent.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "Copyright.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # Board/piece/title/help assets; the binary resolves them through the
        # DATADIR compiled in at build time (see notes.md).
        self.cpp_info.resdirs = ["share/games/shogivar"]
