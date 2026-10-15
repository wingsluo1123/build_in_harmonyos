#!/usr/bin/env python3
"""Conan recipe — scrollz 2.2.3 (advanced IRC client, ncurses terminal UI).

ScrollZ is a scriptable IRC client derived from ircII; it builds a single
`scrollz` executable plus the optional `ircio`/`ircflush`/`wserv` helpers.
Build system: autotools (pre-generated `configure`, no automake).

OHOS portability notes (see notes.md):
  - In-source build. Upstream `Makefile.in` hardcodes `srcdir = .` and the
    root Makefile recurses into `source/`; an out-of-source Conan build would
    leave `source/Makefile` unable to find its inputs.
  - Terminal capability library: `configure` probes for `tgetent` in
    `-ltermcap/-ltinfo/-ltermlib/-lcurses/-lncurses/-lxtermcap`. OHOS has no
    system libncurses and the published ncurses recipe is static + wide-char
    (`libncursesw.a`), so a patch rewrites the `-lncurses` probe/entry to
    `-lncursesw` (patches/0001-configure.patch).
  - Upstream ships no test suite whatsoever (no test sources, no `check`
    target in Makefile.in); consumer verification is done in test_package/.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ScrollzConan(ConanFile):
    name = "scrollz"
    version = "2.2.3"
    description = "ScrollZ — advanced, scriptable IRC client (ircII derivative, ncurses)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/scrollz/scrollz"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ncurses provides the terminal capability database and the wide-char
        # static library (libncursesw.a) that scrollz links against on OHOS.
        self.requires("ncurses/6.5")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"scrollz supports Linux and OHOS only, not {self.settings.os}"
            )

    def layout(self):
        # Upstream Makefile.in hardcodes `srcdir = .` and the root Makefile
        # recurses into `source/` with relative paths, so this project must be
        # built in-source (same approach as the adjtimex/at recipes).
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Feed the ncurses package into configure's link tests (the tgetent
        # probe) and into the final link. AutotoolsToolchain supplies the
        # compiler/flags from the profile conf; only the dependency search
        # paths are added explicitly from the dependency package folder.
        ncurses = self.dependencies["ncurses"]
        inc = os.path.join(ncurses.package_folder, "include")
        lib = os.path.join(ncurses.package_folder, "lib")
        # configure's header probes (AC_CHECK_HEADERS termcap.h and the
        # AC_EGREP_CPP curses.h test) run under $CPP, which only sees
        # $CPPFLAGS — not $CFLAGS. Without the include dir in CPPFLAGS those
        # probes fail, INCLUDE_CURSES_H/HAVE_TERMCAP_H stay undefined and the
        # implicit-int tgetstr/tgetnum declarations break the build. Set it
        # in the build environment before tc.generate() (AutotoolsToolchain
        # has no extra_cppflags attribute; this project's configure is old
        # autoconf 2.13 and rejects `VAR=value` command-line assignments).
        self.buildenv.define("CPPFLAGS", f"-I{inc}")
        tc.extra_ldflags.append(f"-L{lib}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # OHOS sandbox umask 077 creates 0700 directories that config.status
        # cannot write into; build with umask 022 (librrd/alpine precedent).
        old = os.umask(0o022)
        try:
            autotools = Autotools(self)
            autotools.configure()
            # -j1: the OHOS sandbox does not support the make jobserver (mkfifo)
            autotools.make(args=["-j1"])
        finally:
            os.umask(old)
        # Upstream has no test/check target (no tests of any kind in-tree);
        # consumer-side verification is performed by test_package/.

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "scrollz")
