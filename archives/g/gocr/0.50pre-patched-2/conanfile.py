#!/usr/bin/env python3
"""Conan recipe for gocr 0.50pre-patched-2 — the OCR engine used by OSRA.

The tarball is the "patched" GOCR snapshot published by the OSRA project
(https://sourceforge.net/projects/osra/files/gocr-patched/).  It provides the
``libPgm2asc`` library that OSRA links against (``-lPgm2asc``) plus the ``gocr``
command line OCR tool.

Adaptation notes (HarmonyOS / OHOS, aarch64):

* ``make`` only builds the ``gocr`` CLI.  The library OSRA needs is built by the
  ``libs`` target (``libPgm2asc.a``); it is requested explicitly in build().
* netpbm is optional in GOCR and is only used by the CLI to convert PNG/JPEG
  input through ``pngtopnm``/``djpeg``.  OSRA feeds the library with its own
  bitmaps, so the package is configured with ``--without-netpbm`` and has no
  external dependency.
* ``configure`` probes ``setvbuf`` with ``AC_TRY_RUN``; for a cross build the
  cache variable is preset to ``no`` so configure does not try to run a target
  binary.
* E011 / HMDFS: autoconf's ``config.status`` creates its temporary directory
  with ``umask 077``.  On HMDFS such a 0700 directory is not writable by the
  build process (``can't create ./confstatXXXXXX/...``), which silently leaves
  ``Makefile`` / ``config.h`` half generated.  patches/0001-configure.patch
  relaxes it to ``umask 022``.
* Headers are installed flat into ``<prefix>/include`` because OSRA's configure
  includes them as ``<pgm2asc.h>`` / ``<gocr.h>`` (upstream's own install rule
  would put them into ``include/gocr``).
* HMDFS rejects symlink creation (E018) and may drop the executable bit (E046),
  so package() copies the versioned shared object under a plain name and
  re-applies the executable mode to ``bin/gocr``.
"""
import os
import shutil
import stat

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

# AC_INIT() version of the upstream tarball -> libPgm2asc.0.50.so
_UPSTREAM_SO_VERSION = "0.50"

# Headers that consumers of libPgm2asc need (src/INCLUDEFILES upstream).
_PUBLIC_HEADERS = (
    "pgm2asc.h",
    "output.h",
    "list.h",
    "unicode.h",
    "gocr.h",
    "pnm.h",
)


class GocrConan(ConanFile):
    name = "gocr"
    version = "0.50pre-patched-2"
    description = ("GOCR/JOCR optical character recognition engine (OSRA's patched "
                   "snapshot); provides libPgm2asc and the gocr command line tool")
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/osra/files/gocr-patched/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: recipe settings.os checks must accept Linux and OHOS alike.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gocr is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        # gocr's hand-written Makefile.in has no VPATH / out-of-source support
        # (its rules reference `Makefile.in` relative to the build directory),
        # so build in-source as the upstream instructions do.
        basic_layout(self, build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R1: keep --prefix (added by the toolchain) and add only what is needed.
        tc.configure_args.append("--without-netpbm")
        # configure.in probes setvbuf with AC_TRY_RUN, which cannot run while
        # cross building; preset the cache variable (the POSIX answer).
        tc.configure_args.append("ac_cv_func_setvbuf_reversed=no")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # `make` builds the gocr CLI only, `make libs` builds libPgm2asc.a.
        autotools.make(args=["-j1"])
        autotools.make(target="libs", args=["-j1"])
        if self.options.shared:
            # The shared object rule lives in src/Makefile (the top level has no
            # such target); it also tries to create the libPgm2asc.so symlink,
            # but that step is prefixed with '-' upstream and fails harmlessly
            # on HMDFS (E018) - the versioned .so itself is produced.
            self.run(f"make -C src libPgm2asc.{_UPSTREAM_SO_VERSION}.so -j1",
                     env="conanbuild")

    def package(self):
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        src_dir = os.path.join(self.source_folder, "src")
        bin_dir = os.path.join(self.package_folder, "bin")
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include")

        copy(self, "gocr", src=src_dir, dst=bin_dir)
        gocr_bin = os.path.join(bin_dir, "gocr")
        if os.path.exists(gocr_bin):
            # E046: HMDFS may not preserve the executable bit.
            os.chmod(gocr_bin, 0o755)

        copy(self, "libPgm2asc.a", src=src_dir, dst=lib_dir)
        if self.options.shared:
            so_name = f"libPgm2asc.{_UPSTREAM_SO_VERSION}.so"
            copy(self, so_name, src=src_dir, dst=lib_dir)
            # E018: symlinks cannot be created on HMDFS -> install a real copy
            # under the plain linker name instead of a symlink.
            shutil.copyfile(os.path.join(lib_dir, so_name),
                            os.path.join(lib_dir, "libPgm2asc.so"))

        for header in _PUBLIC_HEADERS:
            copy(self, header, src=src_dir, dst=inc_dir)
        # configure generates include/config.h; pnm.h and pgm2asc.h include it.
        copy(self, "config.h", src=os.path.join(self.source_folder, "include"), dst=inc_dir)

    def package_info(self):
        self.cpp_info.libs = ["Pgm2asc"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
