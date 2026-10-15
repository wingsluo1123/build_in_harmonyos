#!/usr/bin/env python3
"""Conan recipe for xtrs 4.9d - TRS-80 Model I/III/4/4P emulator.

xtrs is a Z80-based TRS-80 emulator (the CPU core ``z80.c`` is a pure C
interpreter).  Upstream is a hand-written ``Makefile`` + ``Makefile.local``
that builds four programs:

  xtrs     the emulator itself (X11 client; links libX11)
  mkdisk   create blank TRS-80 disk images
  hex2cmd  Intel-HEX -> TRS-80 CMD converter
  cmddump  dump a TRS-80 CMD file

OHOS notes (see notes.md):

* The OHOS clang target defines ``__linux`` / ``__linux__`` / ``linux``, so
  vendor ``#if __linux`` feature blocks switch on and pull in Linux-only
  headers that do not exist on OHOS (``<sys/soundcard.h>`` OSS via
  ``HAVE_OSS``, and ``<linux/fd.h>`` / ``<linux/fdreg.h>`` for the physical
  floppy controller).  Rather than keying on a platform-identity macro, the
  portability patch guards those blocks by capability -
  ``#if defined(__linux) && __has_include(<...>)`` - so they compile only
  where the required headers really exist; the software paths (disk images,
  cassette files, Z80 core) are unaffected.
* The X11 interface (``trs_xinterface.c`` / ``trs_keyboard.c``) needs both
  libX11 and the X protocol headers from xorgproto (``X11/keysym.h`` etc.),
  so include dirs of all transitive deps are aggregated for the build.
* The emulator itself needs an X display at runtime; only the CLI tools can
  run headless (the consumer test drives those and checks that ``xtrs`` loads
  and reports the missing display).
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
from conan.tools.layout import basic_layout

PROGS = ["xtrs", "mkdisk", "hex2cmd", "cmddump"]
MANPAGES = ["xtrs", "cassette", "mkdisk", "cmddump", "hex2cmd"]


class XtrsConan(ConanFile):
    name = "xtrs"
    version = "4.9d"
    description = "xtrs: TRS-80 Model I/III/4/4P emulator for X11"
    license = "Clarendon-Hill"
    homepage = "http://www.tim-mann.org/xtrs"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libx11/1.8.13")
        # X11 protocol headers come from xorgproto (X11/keysym.h, keysymdef.h,
        # X.h).  It is a transitive dependency of libx11 but Conan treats
        # header-only packages as "skipped binaries" and does not expose their
        # include dirs to transitive consumers, so depend on it directly.
        self.requires("xorgproto/2025.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "xtrs OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_dirs(self, attr):
        out = []
        for dep in self.dependencies.host.values():
            cpp = dep.cpp_info.aggregated_components()
            for d in getattr(cpp, attr):
                out.append(d if os.path.isabs(d)
                           else os.path.join(dep.package_folder, d))
        return sorted(set(out))

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"
        iflags = " ".join("-I" + d for d in self._dep_dirs("includedirs"))
        lflags = " ".join("-L" + d for d in self._dep_dirs("libdirs"))
        self.run(
            'make -j1 CC="%s" DEBUG="-O2" IFLAGS="%s" LDFLAGS="%s" '
            'XLIB="-lX11" READLINE= READLINELIBS= %s'
            % (cc, iflags, lflags, " ".join(PROGS)),
            env="conanbuild", cwd=self.source_folder)
        for prog in PROGS:
            if not os.path.isfile(os.path.join(self.source_folder, prog)):
                raise ConanInvalidConfiguration("program not built: " + prog)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for prog in PROGS:
            copy(self, prog, src=self.source_folder, dst=bindir)
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        for page in MANPAGES:
            src = os.path.join(self.source_folder, page + ".man")
            if os.path.isfile(src):
                os.makedirs(mandir, exist_ok=True)
                copy(self, page + ".man", src=self.source_folder, dst=mandir,
                     keep_path=False)
                os.replace(os.path.join(mandir, page + ".man"),
                           os.path.join(mandir, page + ".1"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
